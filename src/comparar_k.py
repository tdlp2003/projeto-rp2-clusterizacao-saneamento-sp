"""
comparar_k.py — Compara soluções do K-means com números de clusters diferentes (padrão: k = 2,
indicado pelo Método da Silhueta, e k = 3, indicado pelo Método do Cotovelo).

Mesmos dados e pré-processamento do src/clustering.py (matriz A4, tratamentos de config.TRATAMENTOS,
configuração REFERENCIA). Critérios de comparação:
  1. Perfis: mediana e quartis de cada indicador por cluster, em unidades originais (%).
  2. Aninhamento: como os clusters do menor k se dividem no maior k.
  3. Separação: silhueta média por cluster e % de instâncias com silhueta negativa
     (instâncias mais próximas de outro cluster do que do seu).
  4. Estabilidade (bootstrap): reamostra municípios com reposição (os dois anos de cada município
     juntos), reajusta o K-means, classifica todas as instâncias originais pelo modelo reamostrado e
     mede o ARI com a partição dos dados completos. Média alta = partição estável.
  5. Relação com porte e ano: % de cada faixa de porte em cada cluster e matriz de transição 2019→2024.
  6. Corte numa única variável: para k = 2, o quanto a partição é reproduzida por uma regra do tipo
     "indicador >= limiar" (melhor limiar de cada indicador). Concordância muito alta significa que
     a solução separa por uma variável só, e não por um perfil multivariado.

Uso (na raiz do repositório):
    python -m src.comparar_k                 # k = 2 e 3, 200 reamostragens
    python -m src.comparar_k --ks 2,3,4 --B 100

Saídas: outputs/tabelas/comparar_k_*.csv, outputs/figuras/comparar_k_perfis.png,
        outputs/resumo_comparar_k.md
"""
from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, silhouette_samples

from .clustering import (CORES, TEXTO, TEXTO_2, ajustar_kmeans, estabilidade_bootstrap,
                         renumerar_por_tamanho)
from .config import ANOS, INDICADORES, OUT, PAINEL, PORTE_ROTULOS, RANDOM_STATE
from .preprocess import REFERENCIA, executar, para_longo, tratar_valores

FEATS = list(INDICADORES)


# ------------------------------------------------------------------ partições
def particao(X: pd.DataFrame, k: int, seed: int) -> pd.Series:
    """Rótulos 1..k (1 = maior cluster) indexados por (cod_mun6, ano)."""
    return pd.Series(renumerar_por_tamanho(ajustar_kmeans(X, k, seed).labels_), index=X.index, name=f"k{k}")


def corte_univariado(L: pd.DataFrame, lab: pd.Series) -> pd.DataFrame:
    """Para uma partição com 2 clusters: melhor regra 'indicador >= limiar' por indicador
    (limiares = percentis 1..99 do indicador), medida por ARI e % de concordância."""
    assert lab.nunique() == 2
    v = L.loc[lab.index, FEATS]
    linhas = []
    for f in FEATS:
        melhor = (-1.0, None, None)
        for lim in np.unique(np.quantile(v[f], np.linspace(.01, .99, 99))):
            regra = (v[f] >= lim).to_numpy()
            ari = adjusted_rand_score(lab.to_numpy(), regra)
            if ari > melhor[0]:
                conc = max(np.mean(regra == (lab.to_numpy() == 1)), np.mean(regra == (lab.to_numpy() == 2)))
                melhor = (ari, lim, conc)
        linhas.append({"indicador": INDICADORES[f].rotulo, "melhor limiar (%)": round(melhor[1], 2),
                       "ARI com a partição": round(melhor[0], 3), "% concordância": round(100 * melhor[2], 1)})
    return pd.DataFrame(linhas).sort_values("ARI com a partição", ascending=False)


def cores_alinhadas(labs: dict) -> dict:
    """Cor de cada cluster em cada k, mantendo a mesma cor para o 'mesmo' grupo entre k consecutivos
    (o cluster do k maior com maior sobreposição herda a cor do cluster do k menor)."""
    ks = list(labs)
    cores = {ks[0]: {c: CORES[c - 1] for c in range(1, ks[0] + 1)}}
    for k1, k2 in zip(ks, ks[1:]):
        ct = pd.crosstab(labs[k1], labs[k2])
        livres, mapa = list(CORES), {}
        for c1 in ct.index:                                   # herdeiro = maior sobreposição
            c2 = ct.loc[c1].idxmax()
            if c2 not in mapa:
                mapa[c2] = cores[k1][c1]
        for cor in mapa.values():
            livres.remove(cor)
        for c2 in range(1, k2 + 1):
            if c2 not in mapa:
                mapa[c2] = livres.pop(0)
        cores[k2] = mapa
    return cores


# ------------------------------------------------------------------ tabelas
def perfis(L: pd.DataFrame, lab: pd.Series, sil: np.ndarray) -> pd.DataFrame:
    """Mediana [Q1–Q3] por cluster, tamanho por ano e silhueta."""
    d = L.loc[lab.index, FEATS].assign(cluster=lab.to_numpy(), silhueta=sil)
    linhas = []
    for c, g in d.groupby("cluster"):
        linha = {"cluster": c}
        for f in FEATS:
            q1, med, q3 = g[f].quantile([.25, .5, .75])
            linha[f"{INDICADORES[f].rotulo} (%)"] = f"{med:.1f} [{q1:.1f}–{q3:.1f}]"
        anos = g.index.get_level_values("ano")
        for a in ANOS:
            linha[f"n {a}"] = int((anos == a).sum())
        linha["silhueta média"] = round(g.silhueta.mean(), 3)
        linha["% silhueta < 0"] = round(100 * (g.silhueta < 0).mean(), 1)
        linhas.append(linha)
    return pd.DataFrame(linhas)


def por_porte(lab: pd.Series, porte: pd.Series) -> pd.DataFrame:
    """% de cada faixa de porte em cada cluster (municípios-ano, os dois anos juntos)."""
    p = porte.reindex(lab.index.get_level_values("cod_mun6")).to_numpy()
    t = pd.crosstab(pd.Series(p, name="porte"), pd.Series(lab.to_numpy(), name="cluster"), normalize="index") * 100
    return t.reindex(PORTE_ROTULOS).round(1)


def transicao(lab: pd.Series) -> pd.DataFrame:
    w = lab.unstack("ano").dropna().astype(int)
    return pd.crosstab(w[ANOS[0]], w[ANOS[1]], rownames=["2019"], colnames=["2024"])


# ------------------------------------------------------------------ figura
def fig_perfis(L: pd.DataFrame, labs: dict, caminho):
    """Uma linha por k, uma coluna por indicador: mediana (ponto) e Q1–Q3 (barra) de cada cluster.
    O mesmo grupo tem a mesma cor nos diferentes k."""
    ks = list(labs)
    cor = cores_alinhadas(labs)
    fig, axes = plt.subplots(len(ks), len(FEATS), figsize=(2.6 * len(FEATS), 1.0 + 0.55 * sum(ks)),
                             sharex="col", gridspec_kw={"height_ratios": ks})
    axes = np.atleast_2d(axes)
    for i, k in enumerate(ks):
        lab = labs[k]
        d = L.loc[lab.index, FEATS].assign(cluster=lab.to_numpy())
        for j, f in enumerate(FEATS):
            ax = axes[i, j]
            for c in range(1, k + 1):
                v = d.loc[d.cluster == c, f]
                q1, med, q3 = v.quantile([.25, .5, .75])
                y = k - c
                ax.plot([q1, q3], [y, y], color=cor[k][c], lw=3, solid_capstyle="round", alpha=.55)
                ax.plot([med], [y], marker="o", ms=8, color=cor[k][c], mec="white", mew=1.5)
            ax.set_yticks(range(k))
            ax.set_yticklabels([f"cluster {c} (n={int((d.cluster == c).sum())})" for c in range(k, 0, -1)]
                               if j == 0 else [], fontsize=8)
            ax.set_ylim(-0.6, k - 0.4)
            ax.grid(axis="x", color="#e6e5df", lw=.6)
            ax.spines[["top", "right", "left"]].set_visible(False)
            ax.tick_params(colors=TEXTO_2, labelsize=8, left=False)
            if i == 0:
                ax.set_title(INDICADORES[f].rotulo, fontsize=9, color=TEXTO)
            if i == len(ks) - 1:
                ax.set_xlabel("%", fontsize=8, color=TEXTO_2)
        if len(ks) > 1:
            axes[i, 0].annotate(f"k = {k}", xy=(-0.95, 0.5), xycoords="axes fraction", fontsize=10,
                                color=TEXTO, fontweight="bold", va="center")
    fig.tight_layout()
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ks", default="2,3")
    ap.add_argument("--B", type=int, default=200, help="número de reamostragens bootstrap")
    ap.add_argument("--seed", type=int, default=RANDOM_STATE)
    a = ap.parse_args()
    ks = [int(x) for x in a.ks.split(",")]

    TAB, FIG = OUT / "tabelas", OUT / "figuras"
    for d in (TAB, FIG):
        d.mkdir(parents=True, exist_ok=True)
    painel, reg = tratar_valores(pd.read_csv(PAINEL, encoding="utf-8-sig"))
    L = para_longo(painel)
    X, info = executar(L, REFERENCIA)
    porte = painel.set_index("cod_mun6")["porte"]

    labs, sils, R = {}, {}, ["# Comparação entre números de clusters (K-means)\n"]
    R.append(f"- Dados: matriz A4, {info['n_municipios']} municípios × 2 anos = {len(X)} instâncias; "
             f"pré-processamento `{REFERENCIA.nome}`; tratamentos: {reg['acima_100']} / {reg['perdas_zero']}.")
    R.append(f"- k comparados: {ks}. Bootstrap: B = {a.B} reamostragens de municípios, seed = {a.seed}.\n")

    resumo = []
    for k in ks:
        lab = particao(X, k, a.seed)
        sil = silhouette_samples(X.to_numpy(), lab.to_numpy())
        labs[k], sils[k] = lab, sil
        boot = estabilidade_bootstrap(X, k, a.B, a.seed)
        pd.DataFrame({"ari": boot}).to_csv(TAB / f"comparar_k_bootstrap_k{k}.csv", index=False)
        resumo.append({"k": k, "silhueta média": round(sil.mean(), 4),
                       "% silhueta < 0": round(100 * (sil < 0).mean(), 1),
                       "menor cluster (inst.)": int(lab.value_counts().min()),
                       "estabilidade: ARI médio": round(boot.mean(), 3),
                       "ARI p5": round(np.quantile(boot, .05), 3),
                       "% reamostragens com ARI ≥ 0,9": round(100 * (boot >= .9).mean(), 1)})
        pf = perfis(L, lab, sil)
        pf.to_csv(TAB / f"comparar_k_perfis_k{k}.csv", index=False)
        pp = por_porte(lab, porte)
        pp.to_csv(TAB / f"comparar_k_porte_k{k}.csv")
        tr = transicao(lab)
        tr.to_csv(TAB / f"comparar_k_transicao_k{k}.csv")
        R.append(f"## k = {k}\n")
        R.append("Perfis: mediana [Q1–Q3] em unidades originais.\n")
        R.append(pf.to_markdown(index=False))
        R.append("\n% de cada faixa de porte em cada cluster (municípios-ano):\n")
        R.append(pp.to_markdown())
        R.append("\nTransição 2019 → 2024 (nº de municípios):\n")
        R.append(tr.to_markdown())
        R.append("")

    resumo = pd.DataFrame(resumo)
    resumo.to_csv(TAB / "comparar_k_resumo.csv", index=False)
    R.insert(3, "## Resumo\n\n" + resumo.to_markdown(index=False) + "\n")

    # aninhamento entre k consecutivos
    for k1, k2 in zip(ks, ks[1:]):
        ct = pd.crosstab(labs[k1].rename(f"cluster (k={k1})"), labs[k2].rename(f"cluster (k={k2})"))
        ct.to_csv(TAB / f"comparar_k_aninhamento_k{k1}_k{k2}.csv")
        R.insert(4, f"## Como os clusters de k = {k1} se distribuem em k = {k2} (instâncias)\n\n"
                    f"{ct.to_markdown()}\n\nARI entre as duas partições: "
                    f"{adjusted_rand_score(labs[k1], labs[k2]):.3f}\n")

    if 2 in labs:
        cu = corte_univariado(L, labs[2])
        cu.to_csv(TAB / "comparar_k_corte_univariado_k2.csv", index=False)
        R.insert(5, "## k = 2 é um corte numa única variável?\n\nMelhor regra 'indicador ≥ limiar' para "
                    "reproduzir a partição com k = 2:\n\n" + cu.to_markdown(index=False) + "\n")
    fig_perfis(L, labs, FIG / "comparar_k_perfis.png")
    (OUT / "resumo_comparar_k.md").write_text("\n".join(R), encoding="utf-8")
    print("\n".join(R))


if __name__ == "__main__":
    main()
