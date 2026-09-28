"""
preprocess.py — Pré-processamento parametrizado do painel SNIS 2019 x SINISA 2024 (SP).

Cada decisão é um parâmetro explícito (dataclass `Cfg`), as funções são puras
(recebem um DataFrame, devolvem outro; nunca alteram a entrada) e tudo o que é
feito fica registrado em `info`, de onde sai a tabela de decisões da metodologia.

Decisões parametrizadas
    inclusao       completos_ambos | completos_ano | imp_mediana | imp_knn
    transformacao  nenhuma | winsor | log | winsor_log
    escala         zscore | robust | minmax
    escopo         conjunto (mesmo espaço 2019+2024) | por_ano

Uso (na raiz do repositório):
    python preprocess.py                 # grade completa + sensibilidade
    python preprocess.py --ks 3,4,5      # outros k para a sonda de sensibilidade
    python preprocess.py --sem-sensibilidade

Como biblioteca (para clustering.py):
    from preprocess import Cfg, para_longo, executar
    L = para_longo(pd.read_csv("painel_sp_2019_2024.csv", encoding="utf-8-sig"))
    X, info = executar(L, Cfg(inclusao="completos_ambos", transformacao="winsor_log"))

Nenhum algoritmo, k ou pipeline final é escolhido aqui. K-means e Ward só são
usados como SONDA de sensibilidade (quanto a partição muda quando UMA decisão
de pré-processamento muda), não como resultado do artigo.
"""
from __future__ import annotations

import argparse
import itertools
import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import seaborn as sns
import sklearn
from scipy import stats
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.impute import KNNImputer
from sklearn.metrics import adjusted_rand_score

try:  # config.py do projeto, se definir a semente
    from config import RANDOM_STATE  # type: ignore
except Exception:  # noqa: BLE001
    RANDOM_STATE = 42

# ------------------------------------------------------------------ indicadores
# nome_harmonizado: (coluna 2019, coluna 2024, tipo)
CORE = {
    "agua":   ("ae19_IN055", "s24_IAG0001", "pct"),
    "esgoto": ("ae19_IN056", "s24_IES0001", "pct"),
    "coleta": ("rs19_IN015", "s24_IRS0001", "pct"),
    "massa":  ("rs19_IN028", "s24_IRS1004", "massa"),  # kg/hab/dia
}
FEATURES = tuple(CORE)
ANOS = (2019, 2024)

INCLUSAO = ("completos_ambos", "completos_ano", "imp_mediana", "imp_knn")
TRANSF = ("nenhuma", "winsor", "log", "winsor_log")
ESCALA = ("zscore", "robust", "minmax")
ESCOPO = ("conjunto", "por_ano")
FATORES = ("inclusao", "transformacao", "escala", "escopo")

DESCRICAO = {
    "inclusao": {
        "completos_ambos": "Só municípios com todos os indicadores nos dois anos (painel balanceado; permite matriz de transição).",
        "completos_ano": "Cada ano usa os municípios completos naquele ano (painel desbalanceado).",
        "imp_mediana": "Municípios com >= min_obs indicadores observados; ausentes recebem a mediana do ano.",
        "imp_knn": "Idem, ausentes imputados por KNN (k=knn_k) dentro do ano, em espaço min-max.",
    },
    "transformacao": {
        "nenhuma": "Valores originais.",
        "winsor": "Corta cada indicador nos quantis winsor_q (limites estimados conforme o escopo).",
        "log": "Percentuais: -log(100-x+log_c) (abre o teto de 100%, mantém a direção); massa: log1p(x).",
        "winsor_log": "Winsorização seguida da transformação log.",
    },
    "escala": {
        "zscore": "(x - média) / desvio-padrão.",
        "robust": "(x - mediana) / IQR (fallback: desvio-padrão se IQR = 0).",
        "minmax": "(x - mín) / (máx - mín).",
    },
    "escopo": {
        "conjunto": "Um único ajuste (limites e escala) sobre 2019+2024 empilhados: mesmo espaço nos dois anos.",
        "por_ano": "Ajuste separado em cada ano (remove o deslocamento médio entre anos por construção).",
    },
}


@dataclass(frozen=True)
class Cfg:
    inclusao: str = "completos_ambos"
    transformacao: str = "nenhuma"
    escala: str = "robust"
    escopo: str = "conjunto"
    winsor_q: tuple = (0.01, 0.99)
    knn_k: int = 5
    min_obs: int = 3  # mínimo de indicadores observados p/ imputar
    log_c: float = 1.0  # offset do log dos percentuais: -log(100 - x + log_c)

    def __post_init__(self):
        assert self.inclusao in INCLUSAO, self.inclusao
        assert self.transformacao in TRANSF, self.transformacao
        assert self.escala in ESCALA, self.escala
        assert self.escopo in ESCOPO, self.escopo

    @property
    def nome(self) -> str:
        return "|".join(getattr(self, f) for f in FATORES)


def grade(**extra) -> list[Cfg]:
    return [Cfg(*c, **extra) for c in itertools.product(INCLUSAO, TRANSF, ESCALA, ESCOPO)]


# Referência PROVISÓRIA só para desenvolver clustering.py; não é decisão final.
REFERENCIA = Cfg("completos_ambos", "winsor_log", "robust", "conjunto")


# ------------------------------------------------------------------ dados
def para_longo(df: pd.DataFrame, features=FEATURES) -> pd.DataFrame:
    """Painel largo -> longo (cod_mun6, ano) x indicadores harmonizados."""
    partes = []
    for i, ano in enumerate(ANOS):
        p = pd.DataFrame({"cod_mun6": df["cod_mun6"].to_numpy(), "ano": ano})
        for f in features:
            p[f] = df[CORE[f][i]].to_numpy(dtype=float)
        partes.append(p)
    return pd.concat(partes, ignore_index=True).set_index(["cod_mun6", "ano"]).sort_index()


def _grupos(L: pd.DataFrame, escopo: str):
    anos = L.index.get_level_values("ano").to_numpy()
    if escopo == "por_ano":
        return [(int(a), anos == a) for a in ANOS]
    return [("todos", np.ones(len(L), dtype=bool))]


# ------------------------------------------------------------------ (a) inclusão
def incluir(L: pd.DataFrame, cfg: Cfg, features) -> tuple[pd.DataFrame, dict]:
    features = list(features)
    obs = L[features].notna()
    info = {"n_linhas_entrada": int(len(L))}

    if cfg.inclusao == "completos_ano":
        out = L[obs.all(axis=1)].copy()
        info["n_celulas_imputadas"] = 0
    elif cfg.inclusao == "completos_ambos":
        completo = obs.all(axis=1)
        n = completo.groupby(level="cod_mun6").sum()
        muns = n[n == len(ANOS)].index
        out = L[completo & L.index.get_level_values("cod_mun6").isin(muns)].copy()
        info["n_celulas_imputadas"] = 0
    else:  # imputação
        elegivel = obs.sum(axis=1) >= cfg.min_obs
        out = L[elegivel].copy()
        falt_antes = int(out[features].isna().sum().sum())
        anos = out.index.get_level_values("ano").to_numpy()
        for ano in ANOS:
            m = anos == ano
            bloco = out.loc[m, features]
            if cfg.inclusao == "imp_mediana":
                bloco = bloco.fillna(bloco.median())
            else:  # imp_knn, em espaço min-max do próprio ano
                lo, hi = bloco.min(), bloco.max()
                rng = (hi - lo).replace(0, 1.0)
                z = (bloco - lo) / rng
                zi = KNNImputer(n_neighbors=cfg.knn_k).fit_transform(z.to_numpy())
                bloco = pd.DataFrame(zi, index=bloco.index, columns=features) * rng + lo
            out.loc[m, features] = bloco.to_numpy()
        info["n_celulas_imputadas"] = falt_antes
        info["min_obs"] = cfg.min_obs

    info["n_linhas"] = int(len(out))
    info["n_municipios"] = int(out.index.get_level_values("cod_mun6").nunique())
    return out, info


# ------------------------------------------------------------------ (b) teto / assimetria
def winsorizar(L: pd.DataFrame, features, q, escopo: str) -> tuple[pd.DataFrame, dict]:
    features = list(features)
    L = L.copy()
    lim = {}
    for chave, m in _grupos(L, escopo):
        bloco = L.loc[m, features]
        lo, hi = bloco.quantile(q[0]), bloco.quantile(q[1])
        L.loc[m, features] = bloco.clip(lower=lo, upper=hi, axis=1).to_numpy()
        lim[str(chave)] = {f: [round(float(lo[f]), 4), round(float(hi[f]), 4)] for f in features}
    return L, lim


def logar(L: pd.DataFrame, features, c: float = 1.0) -> pd.DataFrame:
    """pct: -log(100 - x + c), c=1 equivale a -log1p(100-x) (monotônica crescente); massa: log1p(x).

    Cuidado: com c pequeno, 99% vs 100% vira uma distância grande (0,69 com c=1);
    c maior suaviza a expansão do teto.
    """
    L = L.copy()
    for f in features:
        if CORE[f][2] == "pct":
            L[f] = -np.log(100.0 - L[f].clip(0, 100) + c)
        else:
            L[f] = np.log1p(L[f].clip(lower=0))
    return L


# ------------------------------------------------------------------ (c)+(d) escala e escopo
def escalar(L: pd.DataFrame, features, metodo: str, escopo: str) -> tuple[pd.DataFrame, dict]:
    features = list(features)
    L = L.copy()
    par, fallback = {}, []
    for chave, m in _grupos(L, escopo):
        b = L.loc[m, features]
        if metodo == "zscore":
            c, s = b.mean(), b.std(ddof=0)
        elif metodo == "robust":
            c, s = b.median(), b.quantile(.75) - b.quantile(.25)
            zero = s <= 0
            if zero.any():
                fallback += [f"{chave}:{f}" for f in s.index[zero]]
                s = s.where(~zero, b.std(ddof=0))
        else:  # minmax
            c, s = b.min(), b.max() - b.min()
        s = s.where(s > 0, 1.0)
        L.loc[m, features] = ((b - c) / s).to_numpy()
        par[str(chave)] = {f: {"centro": round(float(c[f]), 4), "escala": round(float(s[f]), 4)} for f in features}
    if fallback:
        par["fallback_std"] = fallback
    return L, par


# ------------------------------------------------------------------ pipeline
def executar(L: pd.DataFrame, cfg: Cfg, features=FEATURES) -> tuple[pd.DataFrame, dict]:
    """Aplica inclusão -> (winsor) -> (log) -> escala. Devolve (X, info)."""
    features = list(features)
    X, info = incluir(L, cfg, features)
    info["cfg"] = {**asdict(cfg), "nome": cfg.nome}
    if cfg.transformacao in ("winsor", "winsor_log"):
        X, info["winsor_limites"] = winsorizar(X, features, cfg.winsor_q, cfg.escopo)
    if cfg.transformacao in ("log", "winsor_log"):
        X = logar(X, features, cfg.log_c)
    X, info["escala_parametros"] = escalar(X, features, cfg.escala, cfg.escopo)
    return X[features], info


# ------------------------------------------------------------------ diagnósticos
def diagnosticos(X: pd.DataFrame) -> dict:
    sk = X.apply(lambda s: stats.skew(s))
    ku = X.apply(lambda s: stats.kurtosis(s))
    q1, q3 = X.quantile(.25), X.quantile(.75)
    iqr = q3 - q1
    fora = (((X < q1 - 1.5 * iqr) | (X > q3 + 1.5 * iqr)).mean() * 100).where(iqr > 0)
    anos = X.index.get_level_values("ano")
    d = (X[anos == 2024].mean() - X[anos == 2019].mean()) / X.std(ddof=0)
    C = X.corr()
    off = C.to_numpy()[np.triu_indices(len(X.columns), 1)]
    return {
        "assim_media_abs": float(sk.abs().mean()),
        "curtose_media": float(ku.mean()),
        "fora_iqr_pct": float(np.nanmean(fora)),
        "desloc_2019_2024": float(np.linalg.norm(d)),
        "corr_pearson_agua_esgoto": float(C.loc["agua", "esgoto"]) if {"agua", "esgoto"} <= set(X.columns) else np.nan,
        "corr_abs_media": float(np.abs(off).mean()),
    }


# ------------------------------------------------------------------ sonda de sensibilidade
def rotular(X: pd.DataFrame, algoritmo: str, k: int, seed: int = RANDOM_STATE) -> np.ndarray:
    if algoritmo == "kmeans":
        return KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(X.to_numpy())
    return AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(X.to_numpy())


def pares_um_fator(cfgs):
    """Pares de pipelines que diferem em exatamente UM fator."""
    for f in FATORES:
        outros = [g for g in FATORES if g != f]
        grupos: dict = {}
        for c in cfgs:
            grupos.setdefault(tuple(getattr(c, g) for g in outros), []).append(c)
        for cs in grupos.values():
            for a, b in itertools.combinations(cs, 2):
                yield f, a, b


def sensibilidade(Xs: dict, cfgs, ks=(3, 4, 5, 6), algoritmos=("kmeans", "ward")) -> pd.DataFrame:
    """ARI entre partições de pipelines que diferem em um fator, nas linhas comuns."""
    comum = None
    for X in Xs.values():
        comum = X.index if comum is None else comum.intersection(X.index)
    rot = {}
    for c in cfgs:
        X = Xs[c.nome]
        for alg in algoritmos:
            for k in ks:
                lab = pd.Series(rotular(X, alg, k), index=X.index).loc[comum].to_numpy()
                rot[(c.nome, alg, k)] = lab
    linhas = []
    for f, a, b in pares_um_fator(cfgs):
        for alg in algoritmos:
            for k in ks:
                linhas.append({
                    "fator": f, "nivel_a": getattr(a, f), "nivel_b": getattr(b, f),
                    "algoritmo": alg, "k": k,
                    "ari": adjusted_rand_score(rot[(a.nome, alg, k)], rot[(b.nome, alg, k)]),
                })
    out = pd.DataFrame(linhas)
    out.attrs["n_linhas_comuns"] = len(comum)
    return out


# ------------------------------------------------------------------ tabela de decisões
def tabela_decisoes(cfg_ref: Cfg | None = None) -> pd.DataFrame:
    linhas = []
    for f in FATORES:
        for op, desc in DESCRICAO[f].items():
            linhas.append({"fator": f, "opcao": op, "descricao": desc,
                           "na_referencia_provisoria": bool(cfg_ref and getattr(cfg_ref, f) == op)})
    d = pd.DataFrame(linhas)
    return d


# ------------------------------------------------------------------ figuras
def fig_transformacoes(L: pd.DataFrame, out: Path):
    base = Cfg("completos_ambos")
    X0, _ = incluir(L, base, FEATURES)
    versoes = {
        "nenhuma": X0,
        "winsor": winsorizar(X0, FEATURES, base.winsor_q, "conjunto")[0],
        "log": logar(X0, FEATURES),
        "winsor_log": logar(winsorizar(X0, FEATURES, base.winsor_q, "conjunto")[0], FEATURES),
    }
    fig, axes = plt.subplots(len(FEATURES), len(versoes), figsize=(11, 8))
    for i, f in enumerate(FEATURES):
        for j, (nome, V) in enumerate(versoes.items()):
            ax = axes[i, j]
            anos = V.index.get_level_values("ano")
            for ano, cor in ((2019, "#4C78A8"), (2024, "#F58518")):
                sns.histplot(V.loc[anos == ano, f], bins=30, stat="density", alpha=.5,
                             color=cor, ax=ax, edgecolor="white", label=str(ano))
            sk = stats.skew(V[f])
            ax.set_title(f"{f} · {nome}\nassim.={sk:.2f}", fontsize=8)
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.tick_params(labelsize=7)
    axes[0, 0].legend(frameon=False, fontsize=7)
    fig.suptitle("Efeito das transformações (antes da escala; 2019 e 2024 sobrepostos)", y=1.0)
    fig.tight_layout()
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)


def fig_efeito_marginal(sens: pd.DataFrame, out: Path):
    ks = sorted(sens.k.unique())
    fig, axes = plt.subplots(1, len(ks), figsize=(3.2 * len(ks), 3.2), sharey=True)
    axes = np.atleast_1d(axes)
    m = sens.groupby(["k", "algoritmo", "fator"]).ari.mean().reset_index()
    for ax, k in zip(axes, ks):
        sns.barplot(data=m[m.k == k], y="fator", x="ari", hue="algoritmo", order=list(FATORES),
                    palette=["#4C78A8", "#F58518"], ax=ax)
        ax.set_title(f"k = {k}", fontsize=9)
        ax.set_xlim(0, 1)
        ax.set_xlabel("ARI médio")
        ax.set_ylabel("")
        if ax is not axes[-1]:
            ax.get_legend().remove()
    fig.suptitle("Sensibilidade da partição a cada decisão (ARI menor = decisão pesa mais)", y=1.03, fontsize=10)
    fig.tight_layout()
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("painel", nargs="?", default="painel_sp_2019_2024.csv")
    ap.add_argument("--ks", default="3,4,5,6")
    ap.add_argument("--sem-sensibilidade", action="store_true")
    ap.add_argument("--min-obs", type=int, default=3, help="mín. de indicadores observados para imputar")
    a = ap.parse_args()
    ks = tuple(int(x) for x in a.ks.split(","))

    OUT = Path("outputs")
    TAB, FIG, PRE = OUT / "tabelas", OUT / "figuras", OUT / "preproc"
    for d in (TAB, FIG, PRE):
        d.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", context="paper")

    df = pd.read_csv(a.painel, encoding="utf-8-sig")
    L = para_longo(df)
    cfgs = grade(min_obs=a.min_obs)

    # 1) roda a grade inteira
    Xs, infos, diag = {}, {}, []
    for c in cfgs:
        X, info = executar(L, c)
        assert not X.isna().any().any(), c.nome
        Xs[c.nome], infos[c.nome] = X, info
        diag.append({**{f: getattr(c, f) for f in FATORES},
                     "n_linhas": info["n_linhas"], "n_municipios": info["n_municipios"],
                     "n_celulas_imputadas": info["n_celulas_imputadas"], **diagnosticos(X)})
    diag = pd.DataFrame(diag)
    diag.round(4).to_csv(TAB / "preproc_diagnosticos.csv", index=False)

    # 2) tabela de decisões (metodologia)
    dec = tabela_decisoes(REFERENCIA)
    dec.to_csv(TAB / "preproc_decisoes.csv", index=False)

    # 3) referência provisória salva
    Xr, ir = executar(L, REFERENCIA)
    Xr.to_csv(PRE / "X_referencia_provisoria.csv")
    (PRE / "decisoes_referencia_provisoria.json").write_text(
        json.dumps(ir, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    fig_transformacoes(L, FIG / "preproc_transformacoes.png")

    # 4) sensibilidade
    sens = None
    if not a.sem_sensibilidade:
        sens = sensibilidade(Xs, cfgs, ks=ks)
        sens.round(4).to_csv(TAB / "preproc_sensibilidade_pares.csv", index=False)
        marg = (sens.groupby(["fator", "algoritmo", "k"]).ari.agg(["mean", "min", "count"])
                .rename(columns={"mean": "ari_medio", "min": "ari_min", "count": "n_pares"}))
        marg.round(3).to_csv(TAB / "preproc_sensibilidade_por_fator.csv")
        niveis = (sens.groupby(["fator", "nivel_a", "nivel_b"]).ari.agg(["mean", "min"])
                  .rename(columns={"mean": "ari_medio", "min": "ari_min"}))
        niveis.round(3).to_csv(TAB / "preproc_sensibilidade_por_niveis.csv")
        fig_efeito_marginal(sens, FIG / "preproc_efeito_marginal.png")


    # 4b) sensibilidade ao offset do log dos percentuais (fora da grade), na referência
    from dataclasses import replace
    cs = (1.0, 5.0, 10.0)
    Xc = {c: executar(L, replace(REFERENCIA, log_c=c, min_obs=a.min_obs))[0] for c in cs}
    linhas_c = []
    for alg in ("kmeans", "ward"):
        for k in ks:
            base = rotular(Xc[cs[0]], alg, k)
            for c in cs[1:]:
                linhas_c.append({"log_c": c, "vs_log_c": cs[0], "algoritmo": alg, "k": k,
                                 "ari": adjusted_rand_score(base, rotular(Xc[c], alg, k))})
    logc = pd.DataFrame(linhas_c)
    logc.round(4).to_csv(TAB / "preproc_sensibilidade_log_c.csv", index=False)

    # 5) resumo em markdown
    R = ["# Resumo do pré-processamento\n"]
    R.append(f"Grade: **{len(cfgs)}** pipelines = {len(INCLUSAO)} inclusões × {len(TRANSF)} transformações × "
             f"{len(ESCALA)} escalas × {len(ESCOPO)} escopos, sobre {len(FEATURES)} indicadores "
             f"({', '.join(FEATURES)}).\n")
    R.append("## Tabela de decisões\n")
    R.append(dec.drop(columns=["na_referencia_provisoria"]).to_markdown(index=False))
    R.append("\n## Municípios retidos por regra de inclusão\n")
    inc = (diag.groupby("inclusao")[["n_linhas", "n_municipios", "n_celulas_imputadas"]].first()
           .loc[list(INCLUSAO)])
    R.append(inc.to_markdown())
    R.append("\n## Forma das distribuições por transformação (média sobre demais fatores)\n")
    tt = diag.groupby("transformacao")[["assim_media_abs", "curtose_media", "fora_iqr_pct",
                                        "corr_pearson_agua_esgoto", "corr_abs_media"]].mean().loc[list(TRANSF)]
    R.append(tt.round(3).to_markdown())
    R.append("\n## Deslocamento médio 2019→2024 no espaço final (em desvios-padrão, norma do vetor)\n")
    dd = diag.pivot_table(index="escala", columns="escopo", values="desloc_2019_2024", aggfunc="mean").loc[list(ESCALA)]
    R.append(dd.round(3).to_markdown())
    R.append("\n> `por_ano` zera (ou quase) o deslocamento por construção: a mudança temporal deixa de ser "
             "visível no espaço em que se clusteriza.\n")
    if sens is not None:
        R.append(f"## Sensibilidade da partição (ARI, {sens.attrs['n_linhas_comuns']} linhas comuns)\n")
        R.append("ARI médio entre pares de pipelines que diferem em **um** fator (1 = partições idênticas). "
                 "K-means e Ward são só sondas; nenhum k foi escolhido.\n")
        pv = sens.pivot_table(index="fator", columns=["algoritmo", "k"], values="ari", aggfunc="mean").loc[list(FATORES)]
        R.append(pv.round(3).to_markdown())
        R.append("\n### Detalhe por par de níveis (média sobre algoritmos e k)\n")
        R.append(niveis.round(3).to_markdown())
    R.append("\n## Offset do log dos percentuais (referência; ARI vs log_c=1)\n")
    R.append(logc.pivot_table(index="log_c", columns=["algoritmo", "k"], values="ari").round(3).to_markdown())
    R.append("\n> Com log_c=1, 99% e 100% ficam a 0,69 de distância no espaço transformado (o mesmo que 80% vs 90%). "
             "Se a diferença entre 99% e 100% for ruído de arredondamento, use log_c maior.\n")
    R.append("\n## Referência provisória (só para desenvolver clustering.py)\n")
    R.append(f"`{REFERENCIA.nome}` — salva em `outputs/preproc/X_referencia_provisoria.csv` "
             f"({ir['n_linhas']} linhas, {ir['n_municipios']} municípios). **Não é a decisão final.**\n")
    R.append("## Reprodutibilidade\n")
    R.append(f"- `RANDOM_STATE = {RANDOM_STATE}`; Python {platform.python_version()}, numpy {np.__version__}, "
             f"pandas {pd.__version__}, scipy {scipy.__version__}, scikit-learn {sklearn.__version__}.\n"
             f"- Winsorização: quantis {REFERENCIA.winsor_q}; KNN: k={REFERENCIA.knn_k}; min_obs={a.min_obs}; log_c={REFERENCIA.log_c}.")
    (OUT / "resumo_preproc.md").write_text("\n".join(R), encoding="utf-8")
    print("\n".join(R))


if __name__ == "__main__":
    main()
