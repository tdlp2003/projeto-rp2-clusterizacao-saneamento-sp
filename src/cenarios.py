"""
cenarios.py — Compara cenários de tratamento de dois problemas da matriz A4 antes da clusterização:

  Vinhedo: tratamento do esgoto (IES2004) = 129,42% em 2024 (acima de 100%, fisicamente impossível)
      manter   valor original
      truncar  qualquer tratamento > 100 vira 100
      retirar  vira ausente -> o município sai da amostra (casos completos)

  Perdas zeradas: 11 municípios com perdas (IN049) = 0% em 2019 (implausível; todos com IN051 = 0)
      manter      valor original
      retirar     vira ausente -> os municípios saem da amostra
      sem_perdas  tira a variável perdas da matriz (matriz A3: água, esgoto, tratamento)

Os 9 cenários (3 × 3) são clusterizados com o mesmo método do src/clustering.py (K-means, k pelo
Método da Silhueta) em várias configurações de pré-processamento, e comparados com o cenário base
(manter, manter). Para cada um, mede-se:
  - quantos municípios ficam na amostra;
  - o k escolhido e a silhueta média;
  - o quanto a partição muda em relação à base, nas instâncias em comum:
      ARI (1 = partições idênticas) e % de municípios-ano que mudam de cluster (com o mesmo k da base).

Também gera dois diagnósticos usados na decisão:
  - perfil dos casos (os 11 municípios com perdas 0 e Vinhedo: prestador, IN051, valor em 2024...);
  - verificação de cluster artificial: com transformação log + z-score, onde ficam os zeros de perdas
    na escala e se eles formam um grupo próprio.

Este é o código que fundamentou a decisão registrada em config.TRATAMENTOS
(ver docs/decisao_vinhedo_perdas.md).

Uso (na raiz do repositório):
    python -m src.cenarios                 # 12 configurações (4 transformações × 3 escalas)
    python -m src.cenarios --so-referencia # só a configuração de referência (mais rápido)

Saídas: outputs/tabelas/cenarios_*.csv, outputs/figuras/cenarios_*.png, outputs/resumo_cenarios.md
"""
from __future__ import annotations

import argparse
import itertools

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score

from .clustering import ajustar_kmeans, curva_silhueta, escolher_k, renumerar_por_tamanho
from .config import MATRIZES, OUT, PAINEL, RANDOM_STATE, TRATAMENTOS
from .preprocess import ESCALA, REFERENCIA, TRANSF, Cfg, executar, para_longo, tratar_valores

COL_TRAT_24 = MATRIZES["A4"]["tratamento"].col_2024    # s24_IES2004
COL_PERDAS_19 = MATRIZES["A4"]["perdas"].col_2019      # ae19_IN049

OPCOES_VINHEDO = ("manter", "truncar", "retirar")
OPCOES_PERDAS = ("manter", "retirar", "sem_perdas")
BASE = ("manter", "manter")


# ------------------------------------------------------------------ cenários
def aplicar_cenario(painel: pd.DataFrame, vinhedo: str, perdas: str) -> tuple[pd.DataFrame, list[str]]:
    """Devolve (painel modificado, lista de variáveis da matriz). Não altera a entrada.

    Usa a mesma função do pipeline (preprocess.tratar_valores), então o cenário escolhido aqui é
    exatamente o que roda na clusterização."""
    assert vinhedo in OPCOES_VINHEDO and perdas in OPCOES_PERDAS
    p, _ = tratar_valores(painel, acima_100=vinhedo,
                          perdas_zero="retirar" if perdas == "retirar" else "manter")
    feats = list(MATRIZES["A3"]) if perdas == "sem_perdas" else list(MATRIZES["A4"])
    return p, feats


def nome_cenario(vinhedo: str, perdas: str) -> str:
    return f"Vinhedo={vinhedo} | perdas0={perdas}"


# ------------------------------------------------------------------ diagnósticos dos casos
def perfil_casos(painel: pd.DataFrame) -> pd.DataFrame:
    """Os 11 municípios com perdas 0 em 2019 e Vinhedo, com as informações usadas na decisão."""
    a4 = [c for i in MATRIZES["A4"].values() for c in (i.col_2019, i.col_2024)]
    m = (painel[COL_TRAT_24] > 100) | (painel[COL_PERDAS_19] == 0)
    d = painel.loc[m, ["municipio", "populacao", "porte", "ae19_fonte_prestador", COL_PERDAS_19,
                       "ae19_IN051", "s24_IAG2013", "ae19_IN016", COL_TRAT_24]].copy()
    d.insert(1, "problema", np.where(painel.loc[m, COL_TRAT_24] > 100, "tratamento > 100%",
                                     "perdas = 0% (2019)"))
    d["na_amostra_A4"] = painel.loc[m, a4].notna().all(axis=1).map({True: "sim", False: "não"})
    return d.rename(columns={"ae19_fonte_prestador": "prestador_2019",
                             "ae19_IN051": "ae19_IN051 (perdas por ligação)"})


def cluster_artificial(painel: pd.DataFrame, ks, seed, n_init) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Com log/winsor_log + z-score: posição dos zeros de perdas na escala padronizada e
    distribuição deles nos clusters, antes e depois de retirá-los."""
    linhas, tabs = [], []
    for t in ("log", "winsor_log"):
        cfg = Cfg(REFERENCIA.inclusao, t, "zscore", REFERENCIA.escopo)
        X, _ = executar(para_longo(painel), cfg)
        zero = painel.set_index("cod_mun6")[COL_PERDAS_19].eq(0)
        e_zero = pd.Series([bool(zero.get(m, False)) and a == 2019 for m, a in X.index], index=X.index)
        k = escolher_k(curva_silhueta(X, ks, seed, n_init))
        lab = pd.Series(renumerar_por_tamanho(ajustar_kmeans(X, k, seed, n_init).labels_), index=X.index)
        p2, _ = aplicar_cenario(painel, "manter", "retirar")
        X2, _ = executar(para_longo(p2), cfg)
        k2 = escolher_k(curva_silhueta(X2, ks, seed, n_init))
        cl_zero = lab[e_zero]
        alvo = cl_zero.mode().iloc[0]
        linhas.append({
            "config": cfg.nome,
            "perdas padronizada dos zeros (z)": round(float(X.loc[e_zero, "perdas"].mean()), 2),
            "mediana de perdas padronizada": round(float(X["perdas"].median()), 2),
            "k com zeros": k, "k sem zeros": k2,
            "cluster dos zeros": f"{int(alvo)} (todos os {len(cl_zero)})" if cl_zero.nunique() == 1
                                 else ", ".join(map(str, sorted(cl_zero.unique()))),
            "tamanho desse cluster": int((lab == alvo).sum()),
            "% do cluster que são zeros": round(100 * len(cl_zero) / (lab == alvo).sum(), 1),
        })
        tab = pd.crosstab(lab.rename("cluster"), e_zero.map({True: "perdas = 0", False: "demais"}))
        tab.insert(0, "config", cfg.nome)
        tabs.append(tab.reset_index())
    return pd.DataFrame(linhas), pd.concat(tabs, ignore_index=True)


# ------------------------------------------------------------------ comparação de partições
def pct_mudam(a: np.ndarray, b: np.ndarray) -> float:
    """% de instâncias em clusters diferentes, depois de casar os rótulos de b com os de a
    da melhor forma possível (algoritmo húngaro). Exige o mesmo número de clusters."""
    ca, cb = np.unique(a), np.unique(b)
    m = np.array([[np.sum((a == i) & (b == j)) for j in cb] for i in ca])
    lin, col = linear_sum_assignment(-m)
    return 100 * (1 - m[lin, col].sum() / len(a))


def rodar(painel, cfg: Cfg, ks, seed, n_init):
    """Roda os 9 cenários numa configuração de pré-processamento."""
    res, rotulos = [], {}
    for vin, per in itertools.product(OPCOES_VINHEDO, OPCOES_PERDAS):
        p, feats = aplicar_cenario(painel, vin, per)
        X, info = executar(para_longo(p, feats), cfg, feats)
        curva = curva_silhueta(X, ks, seed, n_init)
        k = escolher_k(curva)
        rotulos[(vin, per)] = (X, k)
        res.append({"vinhedo": vin, "perdas0": per, "n_municipios": info["n_municipios"],
                    "k": k, "silhueta": curva.set_index("k").loc[k, "silhueta_media"],
                    **{f"S(k={kk})": s for kk, s in zip(curva.k, curva.silhueta_media)}})
    res = pd.DataFrame(res)

    # comparação com a base, nas instâncias em comum
    Xb, kb = rotulos[BASE]
    lab_base = pd.Series(ajustar_kmeans(Xb, kb, seed, n_init).labels_, index=Xb.index)
    ari_k_base, mudam, ari_k_proprio = [], [], []
    for _, r in res.iterrows():
        X, k = rotulos[(r.vinhedo, r.perdas0)]
        comum = X.index.intersection(Xb.index)
        a = lab_base.loc[comum].to_numpy()
        b = pd.Series(ajustar_kmeans(X, kb, seed, n_init).labels_, index=X.index).loc[comum].to_numpy()
        c = pd.Series(ajustar_kmeans(X, k, seed, n_init).labels_, index=X.index).loc[comum].to_numpy()
        ari_k_base.append(adjusted_rand_score(a, b))
        mudam.append(pct_mudam(a, b))
        ari_k_proprio.append(adjusted_rand_score(a, c))
    res["ARI_vs_base_mesmo_k"] = ari_k_base
    res["%_mudam_de_cluster"] = mudam
    res["ARI_vs_base_k_proprio"] = ari_k_proprio
    res.insert(0, "config", cfg.nome)
    res.insert(1, "cenario", [nome_cenario(v, p) for v, p in zip(res.vinhedo, res.perdas0)])
    return res


def casos(painel, cfg: Cfg, seed, n_init) -> pd.DataFrame:
    """Cluster de Vinhedo e dos municípios com perdas 0 em cada cenário (config dada):
    "c2019 → c2024 (k=...)" ou "fora" se o município não entra na amostra."""
    alvo = painel.loc[(painel[COL_TRAT_24] > 100) | (painel[COL_PERDAS_19] == 0),
                      ["cod_mun6", "municipio", "populacao", COL_TRAT_24, COL_PERDAS_19]]
    out = alvo.set_index("cod_mun6")
    for vin, per in itertools.product(OPCOES_VINHEDO, OPCOES_PERDAS):
        p, feats = aplicar_cenario(painel, vin, per)
        X, _ = executar(para_longo(p, feats), cfg, feats)
        k = escolher_k(curva_silhueta(X, range(2, 11), seed, n_init))
        lab = pd.Series(renumerar_por_tamanho(ajustar_kmeans(X, k, seed, n_init).labels_), index=X.index)
        def onde(m):
            if (m, 2019) not in lab.index:
                return "fora"
            return f"{lab.loc[(m, 2019)]} → {lab.loc[(m, 2024)]} (k={k})"
        out[nome_cenario(vin, per)] = [onde(m) for m in out.index]
    return out.reset_index()


# ------------------------------------------------------------------ figuras
def fig_heatmap(res: pd.DataFrame, valor: str, titulo: str, fmt: str, caminho, cmap, vmin=None, vmax=None):
    tab = res.pivot(index="cenario", columns="config", values=valor)
    tab = tab.loc[[nome_cenario(v, p) for v, p in itertools.product(OPCOES_VINHEDO, OPCOES_PERDAS)]]
    tab.columns = [c.split("|")[1] + " + " + c.split("|")[2] for c in tab.columns]   # transf + escala
    fig, ax = plt.subplots(figsize=(1.0 * tab.shape[1] + 3.6, 0.42 * tab.shape[0] + 1.6))
    sns.heatmap(tab, annot=True, fmt=fmt, cmap=cmap, vmin=vmin, vmax=vmax, ax=ax, cbar=False,
                linewidths=1, linecolor="white", annot_kws={"size": 8})
    ax.set_xlabel("pré-processamento (transformação + escala)", fontsize=9)
    ax.set_ylabel("")
    ax.set_title(titulo, fontsize=10, loc="left")
    ax.tick_params(labelsize=8)
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    fig.tight_layout()
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--so-referencia", action="store_true", help="roda só a configuração REFERENCIA")
    ap.add_argument("--kmin", type=int, default=2)
    ap.add_argument("--kmax", type=int, default=10)
    ap.add_argument("--n-init", type=int, default=20)
    ap.add_argument("--seed", type=int, default=RANDOM_STATE)
    a = ap.parse_args()
    ks = range(a.kmin, a.kmax + 1)

    TAB, FIG = OUT / "tabelas", OUT / "figuras"
    for d in (TAB, FIG):
        d.mkdir(parents=True, exist_ok=True)
    painel = pd.read_csv(PAINEL, encoding="utf-8-sig")

    cfgs = [REFERENCIA] if a.so_referencia else [
        Cfg(REFERENCIA.inclusao, t, e, REFERENCIA.escopo) for t in TRANSF for e in ESCALA]
    res = pd.concat([rodar(painel, c, ks, a.seed, a.n_init) for c in cfgs], ignore_index=True)
    res.round(4).to_csv(TAB / "cenarios_resumo.csv", index=False)
    cs = casos(painel, REFERENCIA, a.seed, a.n_init)
    cs.to_csv(TAB / "cenarios_casos.csv", index=False)
    perfil = perfil_casos(painel)
    perfil.to_csv(TAB / "cenarios_perfil_casos.csv", index=False)
    art, art_tab = cluster_artificial(painel, ks, a.seed, a.n_init)
    art.to_csv(TAB / "cenarios_cluster_artificial.csv", index=False)
    art_tab.to_csv(TAB / "cenarios_cluster_artificial_contagens.csv", index=False)

    if len(cfgs) > 1:
        fig_heatmap(res, "k", "k escolhido pela silhueta", "d", FIG / "cenarios_k.png", "Blues", 1, a.kmax)
        fig_heatmap(res, "ARI_vs_base_mesmo_k", "ARI em relação ao cenário base (mesmo k; 1 = igual)",
                    ".2f", FIG / "cenarios_ari.png", "Blues", 0, 1)

    # ---------------- resumo
    ref = res[res.config == REFERENCIA.nome].set_index("cenario")
    por = (res.groupby("cenario")
           .agg(n_municipios=("n_municipios", "first"),
                ARI_medio=("ARI_vs_base_mesmo_k", "mean"), ARI_min=("ARI_vs_base_mesmo_k", "min"),
                pct_mudam_medio=("%_mudam_de_cluster", "mean"), pct_mudam_max=("%_mudam_de_cluster", "max")))
    k_base = res[(res.vinhedo == "manter") & (res.perdas0 == "manter")].set_index("config").k
    por["mesmo_k_da_base"] = [
        f"{int((res[res.cenario == c].set_index('config').k == k_base).sum())} de {len(cfgs)}"
        for c in por.index]
    ordem = [nome_cenario(v, p) for v, p in itertools.product(OPCOES_VINHEDO, OPCOES_PERDAS)]
    por = por.loc[ordem]

    R = ["# Cenários de tratamento: Vinhedo (tratamento > 100%) e perdas zeradas em 2019\n"]
    R.append("Base de comparação: **Vinhedo=manter | perdas0=manter**. Método: K-means, k pela maior "
             f"silhueta média (k = {a.kmin}..{a.kmax}), n_init = {a.n_init}, seed = {a.seed}.\n")
    R.append("- **ARI** compara as partições nas instâncias em comum (1 = idênticas; perto de 0 = sem relação).")
    R.append("- **% mudam de cluster**: municípios-ano em grupo diferente da base, com o mesmo k e os rótulos "
             "casados da melhor forma.")
    R.append("- Em `sem_perdas` a matriz é outra (A3), então mudanças maiores são esperadas: o cenário mostra "
             "quanto a variável perdas pesa nos grupos.\n")
    R.append(f"Decisão atualmente registrada em `config.TRATAMENTOS`: valores > 100 → "
             f"**{TRATAMENTOS['acima_100']}**; perdas = 0 → **{TRATAMENTOS['perdas_zero']}**.\n")
    R.append("## Perfil dos casos\n")
    R.append(perfil.round(2).to_markdown(index=False))
    R.append("\n## Os zeros de perdas formam um cluster artificial? (log ou winsor_log + z-score)\n")
    R.append(art.to_markdown(index=False))
    R.append("")
    R.append(art_tab.to_markdown(index=False))
    R.append(f"\n## Configuração de referência (`{REFERENCIA.nome}`)\n")
    cols = ["n_municipios", "k", "silhueta", "ARI_vs_base_mesmo_k", "%_mudam_de_cluster", "ARI_vs_base_k_proprio"]
    R.append(ref.loc[ordem, cols].round(3).to_markdown())
    if len(cfgs) > 1:
        R.append(f"\n## Resumo nas {len(cfgs)} configurações de pré-processamento\n")
        R.append(por.round(3).to_markdown())
        R.append("\n## k escolhido por cenário e configuração\n")
        kt = res.pivot(index="cenario", columns="config", values="k").loc[ordem]
        R.append(kt.to_markdown())
    R.append("\n## Onde ficam os casos (configuração de referência)\n")
    R.append("Cada célula: cluster em 2019 → cluster em 2024 (k do cenário). 'fora' = não entra na amostra. "
             "Os números dos clusters seguem o tamanho (1 = maior) dentro de cada cenário.\n")
    R.append(cs.set_index("municipio").drop(columns=["cod_mun6"]).T.to_markdown())
    R.append("\n> Como ler: se um cenário tem ARI perto de 1 e poucos municípios mudando de cluster em todas as "
             "configurações, a decisão quase não afeta o resultado e pode ser tomada pelo critério mais "
             "defensável no texto. Se o ARI cai ou o k muda, a decisão importa e deve ser justificada e "
             "reportada como análise de sensibilidade.")
    (OUT / "resumo_cenarios.md").write_text("\n".join(R), encoding="utf-8")
    print("\n".join(R))


if __name__ == "__main__":
    main()
