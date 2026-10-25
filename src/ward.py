"""
ward.py — Agrupamento hierárquico aglomerativo de Ward (Ward, 1963), com a mesma regra de escolha do
número de clusters usada no k-means (src/clustering.py) e comparação com a solução do k-means.

Como funciona o Ward:
  - começa com cada instância (município-ano) num cluster próprio;
  - a cada passo, junta os dois clusters cuja fusão MENOS aumenta a soma dos quadrados dentro dos
    clusters (o SSE), até restar um único cluster;
  - o resultado é uma árvore (dendrograma). Cortar a árvore em k grupos dá a partição com k clusters.
  Como o k-means, o Ward minimiza o SSE, mas de forma hierárquica e determinística (não depende de
  sementes nem de centroides iniciais) e sem refazer as partições anteriores: a solução com k + 1
  grupos é sempre a de k grupos com um grupo dividido em dois.

Escolha de k (mesma regra e mesmos critérios de config.CRITERIOS_K):
  - candidatos: maior silhueta média (k = 2..10) e cotovelo da curva SSE × k (k = 1..10), ambos
    calculados sobre os cortes da árvore de Ward;
  - critérios: (a) silhueta > 0,25; (b) estabilidade bootstrap >= 0,85; (c) menor cluster >= 5%;
    (d) não ser reproduzido pelo agrupamento de uma única variável (< 0,90);
  - adotado: maior candidato que passa nos quatro.
  Estabilidade no Ward: reamostra municípios com reposição, refaz a árvore, corta em k, calcula os
  centroides dos grupos e atribui cada instância original ao centroide mais próximo; ARI com a partição
  dos dados completos (o Ward não tem "predict", então a atribuição ao centroide é o equivalente usual).

Comparação com o k-means: ARI e tabela de contingência entre a solução do Ward e a do k-means
(com o k adotado por cada um e, se forem diferentes, também com o mesmo k).

Estabilidade por cluster (Hennig, 2007): em cada reamostragem, cada cluster original é comparado com o
cluster mais parecido da partição reamostrada pelo índice de Jaccard (|A ∩ B| / |A ∪ B|, nas instâncias
originais); a média sobre as reamostragens mostra QUAIS grupos são estáveis. Referência de leitura de
Hennig: < 0,5 grupo "dissolvido"; 0,6–0,75 indica um padrão, mas com pertença incerta; > 0,75 estável.
É calculada para o Ward e para o k-means com o mesmo k, para localizar onde os dois divergem.

Uso (na raiz do repositório):
    python -m src.ward

Saídas: outputs/tabelas/ward_*.csv, outputs/figuras/ward_*.png, outputs/resumo_ward.md
"""
from __future__ import annotations

import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from sklearn.metrics import adjusted_rand_score, silhouette_samples, silhouette_score

from .clustering import (CORES, NEUTRO, TEXTO, TEXTO_2, _estilo, escolher_k, escolher_solucoes,
                         fig_cotovelo, fig_curva, k_cotovelo, renumerar_por_tamanho,
                         reproducao_univariada, solucao_kmeans)
from .comparar_k import fig_perfis, perfis, por_porte, transicao
from .config import CRITERIOS_K, INDICADORES, OUT, PAINEL, RANDOM_STATE
from .preprocess import REFERENCIA, executar, para_longo, tratar_valores


# ------------------------------------------------------------------ Ward
def arvore_ward(X: pd.DataFrame) -> np.ndarray:
    """Matriz de ligação (dendrograma) do Ward, distância euclidiana."""
    return linkage(X.to_numpy(), method="ward")


def cortar(Z: np.ndarray, k: int, index=None) -> np.ndarray | pd.Series:
    """Corta a árvore em k clusters; rótulos 1..k com 1 = maior cluster."""
    lab = renumerar_por_tamanho(fcluster(Z, k, criterion="maxclust"))
    return lab if index is None else pd.Series(lab, index=index)


def sse(X: pd.DataFrame, labels) -> float:
    """Soma dos quadrados das distâncias de cada instância ao centroide do seu cluster."""
    A = X.to_numpy()
    lab = np.asarray(labels)
    return float(sum(((A[lab == c] - A[lab == c].mean(axis=0)) ** 2).sum() for c in np.unique(lab)))


def curva_ward(X: pd.DataFrame, Z: np.ndarray, ks=range(2, 11)) -> pd.DataFrame:
    """Para cada corte k: silhueta média, SSE e menor cluster; inclui k = 1 (só SSE) para o cotovelo."""
    linhas = [{"k": 1, "silhueta_media": np.nan, "sse": sse(X, np.ones(len(X))), "menor_cluster": len(X)}]
    for k in ks:
        lab = cortar(Z, k)
        linhas.append({"k": k, "silhueta_media": silhouette_score(X.to_numpy(), lab),
                       "sse": sse(X, lab), "menor_cluster": int(np.bincount(lab)[1:].min())})
    return pd.DataFrame(linhas)


def estabilidade_ward(X: pd.DataFrame, k: int, B: int, seed: int = RANDOM_STATE) -> np.ndarray:
    """ARI entre a partição dos dados completos e as de B reamostragens de municípios (cada
    instância original vai para o centroide mais próximo dos grupos da reamostragem)."""
    rng = np.random.default_rng(seed)
    base = cortar(arvore_ward(X), k)
    muns = X.index.get_level_values("cod_mun6").unique().to_numpy()
    A = X.to_numpy()
    aris = []
    for _ in range(B):
        amostra = rng.choice(muns, size=len(muns), replace=True)
        Xb = pd.concat([X.xs(m, level="cod_mun6", drop_level=False) for m in amostra])
        lb = cortar(arvore_ward(Xb), k)
        cent = np.vstack([Xb.to_numpy()[lb == c].mean(axis=0) for c in range(1, k + 1)])
        atrib = np.argmin(((A[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2), axis=1)
        aris.append(adjusted_rand_score(base, atrib))
    return np.array(aris)


def atribuir_ward(Xb: pd.DataFrame, k: int, X: pd.DataFrame) -> np.ndarray:
    """Ward na reamostragem Xb, cortado em k; cada instância de X vai para o centroide mais próximo."""
    lb = cortar(arvore_ward(Xb), k)
    cent = np.vstack([Xb.to_numpy()[lb == c].mean(axis=0) for c in range(1, k + 1)])
    A = X.to_numpy()
    return np.argmin(((A[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2), axis=1)


def jaccard_por_cluster(X: pd.DataFrame, base, atribuir, B: int, seed: int = RANDOM_STATE) -> pd.Series:
    """Estabilidade por cluster (Hennig, 2007): média, sobre B reamostragens de municípios, do maior
    Jaccard entre cada cluster original e os clusters da partição reamostrada (instâncias originais).
    `atribuir(Xb)` devolve os rótulos de todas as instâncias de X segundo o modelo ajustado em Xb."""
    rng = np.random.default_rng(seed)
    base = np.asarray(base)
    muns = X.index.get_level_values("cod_mun6").unique().to_numpy()
    acum = {c: [] for c in np.unique(base)}
    for _ in range(B):
        amostra = rng.choice(muns, size=len(muns), replace=True)
        Xb = pd.concat([X.xs(m, level="cod_mun6", drop_level=False) for m in amostra])
        nova = np.asarray(atribuir(Xb))
        for c in acum:
            A = base == c
            acum[c].append(max(np.sum(A & (nova == d)) / np.sum(A | (nova == d)) for d in np.unique(nova)))
    return pd.Series({c: float(np.mean(v)) for c, v in acum.items()}, name="jaccard_medio")


def avaliar_candidato_ward(X: pd.DataFrame, Z: np.ndarray, k: int, criterios: dict = CRITERIOS_K,
                           seed: int = RANDOM_STATE) -> dict:
    """Os mesmos quatro critérios do k-means (clustering.avaliar_candidato), para o Ward."""
    lab = cortar(Z, k)
    boot = estabilidade_ward(X, k, criterios["B"], seed)
    ari_uni, var_uni = reproducao_univariada(X, lab, seed)
    av = {"k": k, "silhueta": silhouette_score(X.to_numpy(), lab), "estabilidade": float(boot.mean()),
          "menor_cluster": float(np.bincount(lab)[1:].min() / len(lab)), "univariado": float(ari_uni),
          "variavel_univariada": var_uni}
    av["ok_silhueta"] = av["silhueta"] > criterios["silhueta_min"]
    av["ok_estabilidade"] = av["estabilidade"] >= criterios["estabilidade_min"]
    av["ok_menor_cluster"] = av["menor_cluster"] >= criterios["menor_cluster_min"]
    av["ok_multivariado"] = av["univariado"] < criterios["univariado_max"]
    av["admissivel"] = av["ok_silhueta"] and av["ok_estabilidade"] and av["ok_menor_cluster"]
    return av


# ------------------------------------------------------------------ figuras
def fig_dendrograma(Z: np.ndarray, k: int, caminho, k_extra: int | None = None, folhas: int = 30):
    """Dendrograma truncado (últimas `folhas` fusões) com a linha de corte em k grupos
    e, opcionalmente, outra linha em k_extra (ex.: o k do k-means)."""
    def altura(kk):                                          # entre a fusão que deixa kk e kk-1 grupos
        return (Z[-kk, 2] + Z[-kk + 1, 2]) / 2

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    # ramos em cinza: as cores dos grupos ficam reservadas às figuras de perfis (evita cores conflitantes)
    dendrogram(Z, truncate_mode="lastp", p=folhas, ax=ax, no_labels=True,
               link_color_func=lambda _: NEUTRO)
    linhas = [(k, ":", "regra aplicada ao Ward")] + (
        [(k_extra, "--", "solução adotada")] if k_extra and k_extra != k else [])
    for kk, estilo, nome in linhas:
        ax.axhline(altura(kk), color=CORES[1] if nome == "solução adotada" else TEXTO_2, lw=1.2, ls=estilo)
        ax.text(ax.get_xlim()[1], altura(kk), f"  k = {kk} ({nome})", va="center", fontsize=8, color=TEXTO)
    ax.set_ylabel("distância de Ward (aumento do SSE)", fontsize=9, color=TEXTO_2)
    ax.set_xlabel(f"últimas {folhas} fusões da árvore (1.194 municípios-ano)", fontsize=8, color=TEXTO_2)
    ax.set_title("Dendrograma — Ward", fontsize=10, color=TEXTO, loc="left")
    _estilo(ax)
    fig.tight_layout()
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kmax", type=int, default=10)
    ap.add_argument("--seed", type=int, default=RANDOM_STATE)
    a = ap.parse_args()

    TAB, FIG = OUT / "tabelas", OUT / "figuras"
    for d in (TAB, FIG):
        d.mkdir(parents=True, exist_ok=True)
    painel, reg = tratar_valores(pd.read_csv(PAINEL, encoding="utf-8-sig"))
    L = para_longo(painel)
    X, info = executar(L, REFERENCIA)

    # 1) árvore e candidatos
    Z = arvore_ward(X)
    curva = curva_ward(X, Z, range(2, a.kmax + 1))
    curva.round(4).to_csv(TAB / "ward_silhueta_sse_por_k.csv", index=False)
    cs = curva[curva.k >= 2].reset_index(drop=True)
    k_sil = escolher_k(cs)
    k_cot = k_cotovelo(curva[["k", "sse"]])
    fig_curva(cs, k_sil, FIG / "ward_silhueta_por_k.png")
    fig_cotovelo(curva[["k", "sse"]], k_cot, FIG / "ward_cotovelo.png")

    # 2) avaliação dos candidatos e regra
    avs = [avaliar_candidato_ward(X, Z, k, CRITERIOS_K, a.seed) for k in sorted({k_sil, k_cot})]
    k_w, _, porque = escolher_solucoes(avs, k_sil)
    tab_av = pd.DataFrame(avs)
    tab_av.insert(1, "indicado_por", ["silhueta e cotovelo" if k == k_sil == k_cot else
                                      "silhueta" if k == k_sil else "cotovelo" for k in tab_av.k])
    tab_av.insert(2, "papel", ["adotado" if k == k_w else "descartado" for k in tab_av.k])
    tab_av.round(4).to_csv(TAB / "ward_avaliacao_candidatos.csv", index=False)

    lab_w = cortar(Z, k_w, X.index)
    sil_w = silhouette_samples(X.to_numpy(), lab_w.to_numpy())

    # 3) comparação com o k-means
    k_km, lab_km = solucao_kmeans(X, range(2, a.kmax + 1), a.seed)
    fig_dendrograma(Z, k_w, FIG / "ward_dendrograma.png", k_extra=k_km)
    comp = [{"comparação": f"Ward k = {k_w} × k-means k = {k_km} (soluções adotadas)",
             "ARI": adjusted_rand_score(lab_w, lab_km)}]
    ct = pd.crosstab(lab_km.rename(f"k-means (k={k_km})"), lab_w.rename(f"Ward (k={k_w})"))
    ct.to_csv(TAB / "ward_vs_kmeans.csv")
    if k_w != k_km:
        lab_w_mesmo = cortar(Z, k_km, X.index)
        comp.append({"comparação": f"Ward k = {k_km} × k-means k = {k_km} (mesmo k)",
                     "ARI": adjusted_rand_score(lab_w_mesmo, lab_km)})
    comp = pd.DataFrame(comp)
    comp.round(4).to_csv(TAB / "ward_vs_kmeans_ari.csv", index=False)

    # 3b) estabilidade por cluster, Ward e k-means com o k do k-means
    from .clustering import ajustar_kmeans
    lab_w_km = cortar(Z, k_km, X.index)
    B = CRITERIOS_K["B"]
    jw = jaccard_por_cluster(X, lab_w_km, lambda Xb: atribuir_ward(Xb, k_km, X), B, a.seed)
    jk = jaccard_por_cluster(X, lab_km, lambda Xb: ajustar_kmeans(Xb, k_km, a.seed, 10).predict(X.to_numpy()),
                             B, a.seed)
    pf_w_km = perfis(L, lab_w_km, silhouette_samples(X.to_numpy(), lab_w_km.to_numpy()))
    pf_km = perfis(L, lab_km, silhouette_samples(X.to_numpy(), lab_km.to_numpy()))
    jac = pd.concat([
        pf_km[["cluster"]].assign(algoritmo=f"k-means k={k_km}", jaccard=pf_km.cluster.map(jk).round(3),
                                  agua=pf_km.iloc[:, 1], esgoto=pf_km.iloc[:, 3], tratamento=pf_km.iloc[:, 4]),
        pf_w_km[["cluster"]].assign(algoritmo=f"Ward k={k_km}", jaccard=pf_w_km.cluster.map(jw).round(3),
                                    agua=pf_w_km.iloc[:, 1], esgoto=pf_w_km.iloc[:, 3], tratamento=pf_w_km.iloc[:, 4]),
    ])[["algoritmo", "cluster", "jaccard", "agua", "esgoto", "tratamento"]]
    jac.to_csv(TAB / "ward_kmeans_jaccard_por_cluster.csv", index=False)
    pf_w_km.to_csv(TAB / f"ward_perfis_k{k_km}.csv", index=False)

    # 4) perfis, porte, transição do Ward; rótulos
    pf, pp, tr = perfis(L, lab_w, sil_w), por_porte(lab_w, painel.set_index("cod_mun6")["porte"]), transicao(lab_w)
    pf.to_csv(TAB / f"ward_perfis_k{k_w}.csv", index=False)
    pp.to_csv(TAB / f"ward_porte_k{k_w}.csv")
    tr.to_csv(TAB / f"ward_transicao_k{k_w}.csv")
    ident = painel.set_index("cod_mun6")[["cod_ibge7", "municipio", "porte"]]
    rot = L.loc[X.index].reset_index().join(ident, on="cod_mun6")
    rot[f"cluster_ward_k{k_w}"] = lab_w.to_numpy()
    rot[f"cluster_kmeans_k{k_km}"] = lab_km.to_numpy()
    rot["silhueta_ward"] = sil_w
    rot.round(4).to_csv(TAB / "ward_rotulos.csv", index=False)
    sol = {f"K-means (k={k_km})": lab_km, f"Ward (k={k_km})": lab_w_km}
    if k_w != k_km:
        sol[f"Ward (k={k_w}, adotado)"] = lab_w
    fig_perfis(L, sol, FIG / "ward_vs_kmeans_perfis.png")

    # 5) resumo
    R = ["# Agrupamento hierárquico de Ward\n"]
    R.append(f"- Dados: matriz A4, {info['n_municipios']} municípios × 2 anos = {len(X)} instâncias; "
             f"pré-processamento `{REFERENCIA.nome}`; tratamentos {reg['acima_100']} / {reg['perdas_zero']}.")
    R.append("- Ward com distância euclidiana (`scipy.cluster.hierarchy.linkage`, method='ward'); determinístico.")
    R.append(f"- Mesma regra e critérios do k-means (`config.CRITERIOS_K`), B = {CRITERIOS_K['B']}.\n")
    R.append("## 1. Candidatos (cortes da árvore)\n")
    R.append(curva.round(4).to_markdown(index=False))
    R.append(f"\n- Silhueta: **k = {k_sil}**; Cotovelo: **k = {k_cot}**.\n")
    R.append("## 2. Avaliação e regra\n")
    R.append(tab_av[["k", "indicado_por", "papel", "silhueta", "estabilidade", "menor_cluster", "univariado",
                     "variavel_univariada", "admissivel", "ok_multivariado"]].round(3).to_markdown(index=False))
    R.append("")
    R.extend(f"- {p}" for p in porque)
    R.append(f"\n**Pela regra aplicada ao Ward isoladamente: k = {k_w}.**")
    R.append(f"\n> Decisão do grupo (2026-10-25): a solução do trabalho é a do k-means com k = {k_km}; o Ward é "
             f"usado como verificação com o mesmo k (seção 3), com a ressalva de que a divisão por acesso é "
             "menos estável no Ward. Ver `docs/decisoes.md`.\n")
    R.append("## 3. Comparação com o k-means\n")
    R.append(comp.round(3).to_markdown(index=False))
    R.append(f"\nContingência (instâncias):\n\n{ct.to_markdown()}\n")
    R.append(f"### Estabilidade por cluster com k = {k_km} (Jaccard médio, Hennig 2007; B = {B})\n")
    R.append("Mediana [Q1–Q3] dos indicadores em %. Jaccard > 0,75 = estável; 0,6–0,75 = padrão com pertença "
             "incerta; < 0,5 = dissolvido.\n")
    R.append(jac.to_markdown(index=False))
    R.append("")
    R.append(f"## 4. Perfis do Ward (k = {k_w}): mediana [Q1–Q3]\n")
    R.append(pf.to_markdown(index=False))
    R.append(f"\n% de cada faixa de porte em cada cluster:\n\n{pp.to_markdown()}\n")
    R.append(f"Transição 2019 → 2024:\n\n{tr.to_markdown()}\n")
    (OUT / "resumo_ward.md").write_text("\n".join(R), encoding="utf-8")
    print("\n".join(R))


if __name__ == "__main__":
    main()
