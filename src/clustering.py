"""
clustering.py — Etapa 4: K-means com o número de clusters escolhido pelo Método da Silhueta.

Coeficiente de silhueta de uma instância i (distância euclidiana):
    a(i) = distância média de i às outras instâncias do seu próprio cluster
    b(i) = menor distância média de i às instâncias de um outro cluster
    s(i) = (b(i) - a(i)) / max(a(i), b(i))          (-1 <= s(i) <= 1)
Método da Silhueta: para cada k da grade, S(k) = média de s(i) sobre TODAS as instâncias;
escolhe-se k* = argmax S(k). Em empate, fica o menor k. A silhueta só existe para k >= 2.

Entrada: a matriz X de src/preprocess.py (por padrão, a configuração REFERENCIA). Com o escopo
"conjunto", 2019 e 2024 são padronizados no mesmo espaço e clusterizados juntos (cada
município-ano é uma instância), então os rótulos dos dois anos são comparáveis.

Uso (na raiz do repositório):
    python -m src.clustering                         # REFERENCIA, k = 2..10
    python -m src.clustering --kmin 2 --kmax 8
    python -m src.clustering --transformacao nenhuma --escala zscore

Saídas: outputs/tabelas/kmeans_*.csv, outputs/figuras/kmeans_*.png, outputs/resumo_clustering.md
"""
from __future__ import annotations

import argparse
from dataclasses import replace

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score

from .config import ANOS, INDICADORES, MATRIZ, OUT, PAINEL, PORTE_ROTULOS, RANDOM_STATE
from .preprocess import (ESCALA, ESCOPO, INCLUSAO, REFERENCIA, TRANSF, Cfg, executar, para_longo,
                         tratar_valores)

N_INIT = 50   # reinícios do k-means (fica a melhor inércia)

# Paleta categórica (ordem fixa) para identificar clusters nas figuras.
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
NEUTRO, TEXTO, TEXTO_2 = "#6b6a63", "#1f1f1e", "#5f5e58"


# ------------------------------------------------------------------ k-means e silhueta
def ajustar_kmeans(X: pd.DataFrame, k: int, seed: int = RANDOM_STATE, n_init: int = N_INIT) -> KMeans:
    return KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X.to_numpy())


def curva_silhueta(X: pd.DataFrame, ks=range(2, 11), seed: int = RANDOM_STATE,
                   n_init: int = N_INIT) -> pd.DataFrame:
    """Para cada k: silhueta média sobre todas as instâncias, inércia e tamanho do menor cluster."""
    linhas = []
    for k in ks:
        if not 2 <= k <= len(X) - 1:
            raise ValueError(f"silhueta exige 2 <= k <= n-1 (k={k}, n={len(X)})")
        km = ajustar_kmeans(X, k, seed, n_init)
        linhas.append({
            "k": k,
            "silhueta_media": silhouette_score(X.to_numpy(), km.labels_),
            "inercia": km.inertia_,
            "menor_cluster": int(np.bincount(km.labels_).min()),
        })
    return pd.DataFrame(linhas)


def escolher_k(curva: pd.DataFrame) -> int:
    """k com a maior silhueta média; em empate (diferença < 1e-12), o menor k."""
    melhor = curva["silhueta_media"].max()
    return int(curva.loc[curva["silhueta_media"] >= melhor - 1e-12, "k"].min())


def renumerar_por_tamanho(labels: np.ndarray) -> np.ndarray:
    """Rótulos 1..k, com 1 = maior cluster (o k-means numera em ordem arbitrária)."""
    ordem = pd.Series(labels).value_counts().index          # do maior para o menor
    mapa = {antigo: novo for novo, antigo in enumerate(ordem, start=1)}
    return np.array([mapa[x] for x in labels])


# ------------------------------------------------------------------ figuras
def _estilo(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#c9c8c1")
    ax.tick_params(colors=TEXTO_2, labelsize=8)
    ax.grid(axis="y", color="#e6e5df", lw=0.6)
    ax.set_axisbelow(True)


def fig_curva(curva: pd.DataFrame, k_escolhido: int, caminho):
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    ax.plot(curva.k, curva.silhueta_media, color=NEUTRO, lw=2, marker="o", ms=6, zorder=2)
    s = curva.set_index("k").loc[k_escolhido, "silhueta_media"]
    ax.plot([k_escolhido], [s], marker="o", ms=10, color=CORES[0], mec="white", mew=2, zorder=3)
    ax.annotate(f"k = {k_escolhido}  (S = {s:.3f})", (k_escolhido, s), xytext=(10, -4),
                textcoords="offset points", fontsize=8, color=TEXTO, va="top")
    ax.margins(y=0.12)
    ax.set_xticks(curva.k)
    ax.set_xlabel("número de clusters (k)", color=TEXTO_2, fontsize=9)
    ax.set_ylabel("silhueta média", color=TEXTO_2, fontsize=9)
    ax.set_title("Método da Silhueta — K-means", color=TEXTO, fontsize=10, loc="left")
    _estilo(ax)
    fig.tight_layout()
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_silhueta_instancias(X: pd.DataFrame, labels: np.ndarray, caminho):
    """Gráfico de silhueta clássico: s(i) de cada instância, agrupado por cluster."""
    s = silhouette_samples(X.to_numpy(), labels)
    media = s.mean()
    ks = sorted(set(labels))
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    gap = max(len(s) // 60, 4)                              # espaço entre clusters
    y = 0
    for j, c in enumerate(ks):
        sc = np.sort(s[labels == c])
        cor = CORES[j] if len(ks) <= len(CORES) else NEUTRO
        ax.fill_betweenx(np.arange(y, y + len(sc)), 0, sc, color=cor, lw=0)
        ax.text(-0.02, y + len(sc) / 2, f"cluster {c} (n={len(sc)})", ha="right", va="center",
                fontsize=8, color=TEXTO)
        y += len(sc) + gap
    ax.axvline(media, color=TEXTO, lw=1, ls="--")
    ax.text(media, y, f" média = {media:.3f}", fontsize=8, color=TEXTO, va="bottom")
    ax.set_yticks([])
    ax.set_xlabel("coeficiente de silhueta s(i)", color=TEXTO_2, fontsize=9)
    ax.set_title(f"Silhueta por instância (k = {len(ks)})", color=TEXTO, fontsize=10, loc="left")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(colors=TEXTO_2, labelsize=8)
    fig.tight_layout()
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kmin", type=int, default=2)
    ap.add_argument("--kmax", type=int, default=10)
    ap.add_argument("--inclusao", choices=INCLUSAO, default=REFERENCIA.inclusao)
    ap.add_argument("--transformacao", choices=TRANSF, default=REFERENCIA.transformacao)
    ap.add_argument("--escala", choices=ESCALA, default=REFERENCIA.escala)
    ap.add_argument("--escopo", choices=ESCOPO, default=REFERENCIA.escopo)
    ap.add_argument("--seed", type=int, default=RANDOM_STATE)
    a = ap.parse_args()

    TAB, FIG = OUT / "tabelas", OUT / "figuras"
    for d in (TAB, FIG):
        d.mkdir(parents=True, exist_ok=True)

    painel, reg_trat = tratar_valores(pd.read_csv(PAINEL, encoding="utf-8-sig"))  # config.TRATAMENTOS
    L = para_longo(painel)
    cfg = replace(REFERENCIA, inclusao=a.inclusao, transformacao=a.transformacao,
                  escala=a.escala, escopo=a.escopo)
    X, info = executar(L, cfg)

    # 1) curva da silhueta e escolha de k
    curva = curva_silhueta(X, range(a.kmin, a.kmax + 1), a.seed)
    k = escolher_k(curva)
    curva.round(4).to_csv(TAB / "kmeans_silhueta_por_k.csv", index=False)
    fig_curva(curva, k, FIG / "kmeans_silhueta_por_k.png")

    # 2) modelo final com k*
    km = ajustar_kmeans(X, k, a.seed)
    labels = renumerar_por_tamanho(km.labels_)
    fig_silhueta_instancias(X, labels, FIG / "kmeans_silhueta_instancias.png")

    # 3) rótulos por município-ano, com valores originais e porte
    ident = painel.set_index("cod_mun6")[["cod_ibge7", "municipio", "populacao", "porte"]]
    rot = (L.loc[X.index].reset_index()
           .assign(cluster=labels, silhueta=silhouette_samples(X.to_numpy(), labels))
           .join(ident, on="cod_mun6"))
    feats = list(INDICADORES)
    rot = rot[["cod_ibge7", "cod_mun6", "municipio", "populacao", "porte", "ano", "cluster",
               "silhueta"] + feats]
    rot.round(4).to_csv(TAB / "kmeans_rotulos.csv", index=False)

    # 4) perfil de cada cluster em unidades originais (mediana) e tamanho por ano
    perfil = rot.groupby("cluster")[feats].median().round(2)
    perfil.columns = [f"{INDICADORES[f].rotulo} (mediana, {INDICADORES[f].unidade})" for f in feats]
    n_ano = rot.pivot_table(index="cluster", columns="ano", values="cod_mun6", aggfunc="count", fill_value=0)
    n_ano.columns = [f"n_{c}" for c in n_ano.columns]
    perfil = perfil.join(n_ano).join(rot.groupby("cluster").silhueta.mean().round(3).rename("silhueta_media"))
    perfil.to_csv(TAB / "kmeans_perfis.csv")

    # 5) cluster × porte (% de cada faixa de porte em cada cluster), por ano
    porte = (pd.crosstab([rot.ano, rot.porte], rot.cluster, normalize="index") * 100).round(1)
    porte = porte.reindex(pd.MultiIndex.from_product([ANOS, PORTE_ROTULOS]), fill_value=0)
    porte.to_csv(TAB / "kmeans_cluster_por_porte.csv")

    # 6) transição 2019 -> 2024 (só faz sentido com o mesmo espaço e os mesmos municípios)
    trans = None
    if cfg.escopo == "conjunto":
        w = rot.pivot(index="cod_mun6", columns="ano", values="cluster").dropna().astype(int)
        trans = pd.crosstab(w[ANOS[0]], w[ANOS[1]], rownames=["cluster 2019"], colnames=["cluster 2024"])
        trans.to_csv(TAB / "kmeans_transicao_2019_2024.csv")

    # 7) resumo
    R = ["# Resumo da clusterização (K-means + Método da Silhueta)\n"]
    R.append(f"- Matriz **{MATRIZ}**: {', '.join(INDICADORES[f].rotulo for f in feats)}.")
    R.append(f"- Pré-processamento: `{cfg.nome}` "
             f"({'referência provisória' if cfg == REFERENCIA else 'escolhido na linha de comando'}).")
    R.append(f"- Instâncias: **{len(X)}** (municípios-ano), {info['n_municipios']} municípios.")
    R.append(f"- Tratamento de valores: valores > 100 → **{reg_trat['acima_100']}**; perdas = 0 → "
             f"**{reg_trat['perdas_zero']}** ({len(reg_trat['alteracoes'])} células; ver "
             "`docs/decisao_vinhedo_perdas.md`).")
    R.append(f"- K-means: n_init = {N_INIT}, random_state = {a.seed}. Grade k = {a.kmin}..{a.kmax}.")
    R.append(f"\n## Silhueta média por k\n\n{curva.round(4).to_markdown(index=False)}\n")
    R.append(f"**k escolhido = {k}** (maior silhueta média = {curva.silhueta_media.max():.4f}).\n")
    R.append(f"## Perfil dos clusters (medianas em unidades originais)\n\n{perfil.to_markdown()}\n")
    R.append(f"## Cluster × porte (% da faixa em cada cluster)\n\n{porte.to_markdown()}\n")
    if trans is not None:
        R.append(f"## Transição 2019 → 2024 (nº de municípios)\n\n{trans.to_markdown()}\n")
    R.append("> Os clusters estão numerados por tamanho (1 = maior). A silhueta mede separação "
             "geométrica; interpretar os perfis antes de nomear os grupos.")
    (OUT / "resumo_clustering.md").write_text("\n".join(R), encoding="utf-8")
    print("\n".join(R))


if __name__ == "__main__":
    main()
