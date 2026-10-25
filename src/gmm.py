"""
gmm.py — Modelo de Mistura Gaussiana (GMM), terceiro algoritmo do trabalho, com a mesma regra de
escolha do número de clusters do k-means e do Ward, e comparação com os dois.

Como funciona o GMM:
  - supõe que os dados vêm de uma mistura de k distribuições normais multivariadas (componentes),
    cada uma com média, matriz de covariância e peso próprios;
  - os parâmetros são estimados por máxima verossimilhança com o algoritmo EM (expectation-maximization);
  - cada instância recebe uma PROBABILIDADE de pertencer a cada componente; o cluster é o de maior
    probabilidade. Diferente do k-means e do Ward, o GMM é probabilístico: permite grupos com formatos
    e tamanhos diferentes e mede a incerteza da classificação de cada município.

Escolhas e por quê:
  1. Tipo de covariância (full, tied, diag, spherical): excluem-se os tipos que geram componentes
     DEGENERADOS (variância praticamente nula, < 0,1% da variância total da variável, em algum
     componente e algum k da grade: o componente colapsou sobre um ponto); entre os restantes, fica o
     de menor BIC na maior parte dos k. (Um limiar de 1% foi testado antes e descartado: excluía o tipo
     "tied", cuja menor variância, de 0,6% a 9%, reflete grupos bem separados, não colapso.) Motivo: nestes dados,
     75% dos valores de tratamento são exatamente 100%; com covariância livre por componente, o EM
     cria componentes com variância quase zero sobre esse ponto, o que infla a verossimilhança e
     produz grupos minúsculos sem sentido.
  2. Número de clusters: a MESMA regra do k-means e do Ward (candidatos pela silhueta e pelo cotovelo
     do SSE das partições; critérios (a)–(d) de config.CRITERIOS_K). O BIC, critério usual do GMM,
     é calculado e registrado, mas não é usado para escolher k porque diminui continuamente até o k
     máximo em todos os tipos de covariância (não tem mínimo na grade).
  3. Estabilidade: bootstrap de municípios; o GMM ajustado em cada reamostragem classifica todas as
     instâncias originais (predict). Estabilidade por cluster pelo Jaccard médio (Hennig, 2007).
  4. Incerteza: % de instâncias cuja maior probabilidade de pertença é < 0,8, por cluster.

Comparação: ARI entre GMM, k-means e Ward com o mesmo k; Jaccard por cluster nos três; perfis.

Uso (na raiz do repositório):
    python -m src.gmm

Saídas: outputs/tabelas/gmm_*.csv, outputs/figuras/gmm_*.png, outputs/resumo_gmm.md
"""
from __future__ import annotations

import argparse
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.metrics import adjusted_rand_score, silhouette_samples, silhouette_score
from sklearn.mixture import GaussianMixture

from .clustering import (CORES, NEUTRO, TEXTO, TEXTO_2, _estilo, ajustar_kmeans, escolher_k,
                         escolher_solucoes, fig_cotovelo, fig_curva, k_cotovelo,
                         renumerar_por_tamanho, reproducao_univariada, solucao_kmeans)
from .comparar_k import fig_perfis, perfis, por_porte, transicao
from .config import CRITERIOS_K, OUT, PAINEL, RANDOM_STATE
from .preprocess import REFERENCIA, executar, para_longo, tratar_valores
from .ward import arvore_ward, atribuir_ward, cortar, jaccard_por_cluster, sse

TIPOS_COV = ("full", "tied", "diag", "spherical")
N_INIT_GMM = 10
LIMIAR_DEGENERADO = 0.001     # variância de componente < 0,1% da variância total = praticamente nula
LIMIAR_INCERTEZA = 0.8        # maior probabilidade de pertença abaixo disso = classificação incerta

warnings.filterwarnings("ignore", category=ConvergenceWarning)


# ------------------------------------------------------------------ GMM
def ajustar_gmm(X: pd.DataFrame, k: int, cov: str, seed: int = RANDOM_STATE,
                n_init: int = N_INIT_GMM) -> GaussianMixture:
    return GaussianMixture(n_components=k, covariance_type=cov, n_init=n_init,
                           random_state=seed).fit(X.to_numpy())


def covariancias_completas(g: GaussianMixture) -> np.ndarray:
    """Matrizes de covariância (k × d × d) de cada componente, qualquer que seja o tipo."""
    k, d = g.n_components, g.means_.shape[1]
    c = g.covariances_
    if g.covariance_type == "full":
        return c
    if g.covariance_type == "tied":
        return np.repeat(c[None, :, :], k, axis=0)
    if g.covariance_type == "diag":
        return np.array([np.diag(v) for v in c])
    return np.array([np.eye(d) * v for v in c])              # spherical


def degenerado(g: GaussianMixture, X: pd.DataFrame) -> bool:
    """Algum componente tem variância < LIMIAR_DEGENERADO × variância total em alguma variável?"""
    var_total = X.to_numpy().var(axis=0)
    diag = np.array([np.diag(m) for m in covariancias_completas(g)])
    return bool((diag < LIMIAR_DEGENERADO * var_total).any())


def rotulos(g: GaussianMixture, X: pd.DataFrame) -> np.ndarray:
    """Rótulos 1..k (1 = maior cluster) a partir da maior probabilidade."""
    return renumerar_por_tamanho(g.predict(X.to_numpy()))


def grade_covariancias(X: pd.DataFrame, ks, seed) -> pd.DataFrame:
    """BIC, AIC, degeneração, silhueta e SSE para cada tipo de covariância e k (k = 1 só BIC/AIC/SSE)."""
    linhas = []
    A = X.to_numpy()
    for cov in TIPOS_COV:
        for k in [1, *ks]:
            g = ajustar_gmm(X, k, cov, seed)
            lab = g.predict(A)
            n_grupos = len(np.unique(lab))
            linhas.append({"covariancia": cov, "k": k, "bic": g.bic(A), "aic": g.aic(A),
                           "degenerado": degenerado(g, X) if k > 1 else False,
                           "grupos_nao_vazios": n_grupos,
                           "silhueta_media": silhouette_score(A, lab) if n_grupos > 1 else np.nan,
                           "sse": sse(X, lab),
                           "menor_cluster": int(np.bincount(lab, minlength=k).min())})
    return pd.DataFrame(linhas)


def escolher_covariancia(grade: pd.DataFrame) -> tuple[str, list[str]]:
    """Exclui tipos com componente degenerado (ou grupo vazio) em algum k >= 2; entre os restantes,
    o que tem o menor BIC no maior número de k."""
    porque = []
    g2 = grade[grade.k >= 2]
    ruins = g2[(g2.degenerado) | (g2.grupos_nao_vazios < g2.k)].covariancia.unique().tolist()
    validos = [c for c in TIPOS_COV if c not in ruins]
    porque.append("Tipos excluídos por componentes degenerados ou vazios: " + (", ".join(ruins) or "nenhum") + ".")
    if not validos:
        porque.append("AVISO: todos os tipos degeneram; usa-se 'spherical'.")
        return "spherical", porque
    vitorias = (g2[g2.covariancia.isin(validos)].loc[lambda d: d.groupby("k").bic.idxmin()]
                .covariancia.value_counts())
    cov = vitorias.idxmax()
    porque.append(f"Entre {', '.join(validos)}, '{cov}' tem o menor BIC em {vitorias[cov]} dos "
                  f"{g2.k.nunique()} valores de k.")
    return cov, porque


def estabilidade_gmm(X: pd.DataFrame, k: int, cov: str, B: int, seed: int = RANDOM_STATE) -> np.ndarray:
    rng = np.random.default_rng(seed)
    base = ajustar_gmm(X, k, cov, seed).predict(X.to_numpy())
    muns = X.index.get_level_values("cod_mun6").unique().to_numpy()
    aris = []
    for b in range(B):
        amostra = rng.choice(muns, size=len(muns), replace=True)
        Xb = pd.concat([X.xs(m, level="cod_mun6", drop_level=False) for m in amostra])
        g = ajustar_gmm(Xb, k, cov, seed + b + 1, n_init=3)
        aris.append(adjusted_rand_score(base, g.predict(X.to_numpy())))
    return np.array(aris)


def avaliar_candidato_gmm(X: pd.DataFrame, k: int, cov: str, criterios: dict = CRITERIOS_K,
                          seed: int = RANDOM_STATE) -> dict:
    """Os mesmos quatro critérios do k-means e do Ward."""
    g = ajustar_gmm(X, k, cov, seed)
    lab = g.predict(X.to_numpy())
    boot = estabilidade_gmm(X, k, cov, criterios["B"], seed)
    ari_uni, var_uni = reproducao_univariada(X, lab, seed)
    av = {"k": k, "silhueta": silhouette_score(X.to_numpy(), lab), "estabilidade": float(boot.mean()),
          "menor_cluster": float(np.bincount(lab, minlength=k).min() / len(lab)), "univariado": float(ari_uni),
          "variavel_univariada": var_uni}
    av["ok_silhueta"] = av["silhueta"] > criterios["silhueta_min"]
    av["ok_estabilidade"] = av["estabilidade"] >= criterios["estabilidade_min"]
    av["ok_menor_cluster"] = av["menor_cluster"] >= criterios["menor_cluster_min"]
    av["ok_multivariado"] = av["univariado"] < criterios["univariado_max"]
    av["admissivel"] = av["ok_silhueta"] and av["ok_estabilidade"] and av["ok_menor_cluster"]
    return av


# ------------------------------------------------------------------ figura
def fig_bic(grade: pd.DataFrame, cov_escolhida: str, caminho):
    """BIC × k por tipo de covariância: mostra que o BIC não tem mínimo na grade.
    Um painel por tipo (escalas muito diferentes; não se usa eixo duplo)."""
    fig, axes = plt.subplots(1, len(TIPOS_COV), figsize=(2.9 * len(TIPOS_COV), 2.8))
    for ax, cov in zip(axes, TIPOS_COV):
        d = grade[grade.covariancia == cov]
        cor = CORES[0] if cov == cov_escolhida else NEUTRO
        ax.plot(d.k, d.bic, color=cor, lw=2, marker="o", ms=4)
        deg = d[d.degenerado]
        ax.plot(deg.k, deg.bic, ls="none", marker="x", ms=7, color=CORES[7], label="degenerado")
        ax.set_title(cov + (" (escolhida)" if cov == cov_escolhida else ""), fontsize=9, color=TEXTO)
        ax.set_xticks(range(1, int(d.k.max()) + 1, 3))
        ax.set_xlabel("k", fontsize=8, color=TEXTO_2)
        _estilo(ax)
    axes[0].set_ylabel("BIC (menor = melhor)", fontsize=8, color=TEXTO_2)
    if grade.degenerado.any():
        axes[0].legend(frameon=False, fontsize=7)
    fig.suptitle("GMM — BIC por tipo de covariância", x=0.01, ha="left", fontsize=10, color=TEXTO)
    fig.tight_layout()
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kmax", type=int, default=10)
    ap.add_argument("--seed", type=int, default=RANDOM_STATE)
    a = ap.parse_args()
    ks = range(2, a.kmax + 1)

    TAB, FIG = OUT / "tabelas", OUT / "figuras"
    for d in (TAB, FIG):
        d.mkdir(parents=True, exist_ok=True)
    painel, reg = tratar_valores(pd.read_csv(PAINEL, encoding="utf-8-sig"))
    L = para_longo(painel)
    X, info = executar(L, REFERENCIA)
    A = X.to_numpy()

    # 1) tipo de covariância
    grade = grade_covariancias(X, ks, a.seed)
    grade.round(4).to_csv(TAB / "gmm_grade_covariancias.csv", index=False)
    cov, porque_cov = escolher_covariancia(grade)
    fig_bic(grade, cov, FIG / "gmm_bic.png")
    bic_min = grade.loc[grade.groupby("covariancia").bic.idxmin(), ["covariancia", "k"]]

    # 2) candidatos e regra (mesma do k-means e do Ward)
    curva = grade[grade.covariancia == cov][["k", "silhueta_media", "sse", "menor_cluster"]].reset_index(drop=True)
    cs = curva[curva.k >= 2].reset_index(drop=True)
    k_sil, k_cot = escolher_k(cs), k_cotovelo(curva[["k", "sse"]])
    fig_curva(cs, k_sil, FIG / "gmm_silhueta_por_k.png")
    fig_cotovelo(curva[["k", "sse"]], k_cot, FIG / "gmm_cotovelo.png")
    avs = [avaliar_candidato_gmm(X, k, cov, CRITERIOS_K, a.seed) for k in sorted({k_sil, k_cot})]
    k_g, _, porque = escolher_solucoes(avs, k_sil)
    tab_av = pd.DataFrame(avs)
    tab_av.insert(1, "indicado_por", ["silhueta e cotovelo" if k == k_sil == k_cot else
                                      "silhueta" if k == k_sil else "cotovelo" for k in tab_av.k])
    tab_av.insert(2, "papel", ["adotado" if k == k_g else "descartado" for k in tab_av.k])
    tab_av.round(4).to_csv(TAB / "gmm_avaliacao_candidatos.csv", index=False)

    # 3) comparação com k-means e Ward no k do k-means
    k_km, lab_km = solucao_kmeans(X, ks, a.seed)
    g_km = ajustar_gmm(X, k_km, cov, a.seed)
    lab_g = pd.Series(rotulos(g_km, X), index=X.index)
    lab_w = cortar(arvore_ward(X), k_km, X.index)
    ari = pd.DataFrame([
        {"par": f"GMM × k-means (k={k_km})", "ARI": adjusted_rand_score(lab_g, lab_km)},
        {"par": f"GMM × Ward (k={k_km})", "ARI": adjusted_rand_score(lab_g, lab_w)},
        {"par": f"k-means × Ward (k={k_km})", "ARI": adjusted_rand_score(lab_km, lab_w)},
    ])
    ari.round(4).to_csv(TAB / "gmm_ari_tres_algoritmos.csv", index=False)

    # 3a) sensibilidade ao tipo de covariância, com o k do k-means
    sens = []
    for c in TIPOS_COV:
        gc = ajustar_gmm(X, k_km, c, a.seed)
        lc = pd.Series(rotulos(gc, X), index=X.index)
        sens.append({"covariancia": c, "usada": c == cov, "degenerado": degenerado(gc, X),
                     "BIC": round(gc.bic(A)), "silhueta": round(silhouette_score(A, lc), 3),
                     "ARI × k-means": round(adjusted_rand_score(lc, lab_km), 3),
                     "ARI × Ward": round(adjusted_rand_score(lc, lab_w), 3),
                     "separa por acesso?": "sim" if adjusted_rand_score(lc, lab_km) > 0.7 else "não"})
    sens = pd.DataFrame(sens)
    sens.to_csv(TAB / "gmm_sensibilidade_covariancia.csv", index=False)
    ct = pd.crosstab(lab_km.rename(f"k-means (k={k_km})"), lab_g.rename(f"GMM (k={k_km})"))
    ct.to_csv(TAB / "gmm_vs_kmeans.csv")

    B = CRITERIOS_K["B"]
    jg = jaccard_por_cluster(X, lab_g, lambda Xb: ajustar_gmm(Xb, k_km, cov, a.seed, 3).predict(A), B, a.seed)
    jk = jaccard_por_cluster(X, lab_km, lambda Xb: ajustar_kmeans(Xb, k_km, a.seed, 10).predict(A), B, a.seed)
    jw = jaccard_por_cluster(X, lab_w, lambda Xb: atribuir_ward(Xb, k_km, X), B, a.seed)

    # incerteza de pertença (probabilidade máxima)
    pmax = g_km.predict_proba(A).max(axis=1)
    inc = (pd.DataFrame({"cluster": lab_g.to_numpy(), "pmax": pmax})
           .groupby("cluster").pmax.agg(prob_media="mean",
                                        pct_incerta=lambda v: 100 * (v < LIMIAR_INCERTEZA).mean()))

    # perfis lado a lado, com os clusters do GMM e do Ward casados com os do k-means pela maior sobreposição
    pf_g = perfis(L, lab_g, silhouette_samples(A, lab_g.to_numpy()))
    pf_g.to_csv(TAB / f"gmm_perfis_k{k_km}.csv", index=False)
    por_porte(lab_g, painel.set_index("cod_mun6")["porte"]).to_csv(TAB / f"gmm_porte_k{k_km}.csv")
    transicao(lab_g).to_csv(TAB / f"gmm_transicao_k{k_km}.csv")

    def casar(lab):                                       # cluster do k-means correspondente
        t = pd.crosstab(lab_km, lab)
        return {c: int(t[c].idxmax()) for c in t.columns}

    mg, mw = casar(lab_g), casar(lab_w)
    jac = pd.DataFrame({"cluster k-means": jk.index, "Jaccard k-means": jk.round(3).to_numpy()})
    def por_cluster_km(serie, mapa, casas):
        """Valor do cluster correspondente a cada cluster do k-means; 'sem correspondente' se nenhum."""
        out = []
        for ck in jk.index:
            cs_ = [c for c, m in mapa.items() if m == ck]
            out.append(round(float(serie[cs_].max()), casas) if cs_ else "sem correspondente")
        return out

    jac["Jaccard Ward"] = por_cluster_km(jw, mw, 3)
    jac["Jaccard GMM"] = por_cluster_km(jg, mg, 3)
    jac["% incerta GMM"] = por_cluster_km(inc["pct_incerta"], mg, 1)
    jac.to_csv(TAB / "gmm_jaccard_tres_algoritmos.csv", index=False)

    ident = painel.set_index("cod_mun6")[["cod_ibge7", "municipio", "porte"]]
    rot = L.loc[X.index].reset_index().join(ident, on="cod_mun6")
    rot[f"cluster_gmm_k{k_km}"] = lab_g.to_numpy()
    rot["prob_max_gmm"] = pmax
    rot[f"cluster_kmeans_k{k_km}"] = lab_km.to_numpy()
    rot[f"cluster_ward_k{k_km}"] = lab_w.to_numpy()
    rot.round(4).to_csv(TAB / "gmm_rotulos.csv", index=False)
    fig_perfis(L, {f"K-means (k={k_km})": lab_km, f"Ward (k={k_km})": lab_w, f"GMM (k={k_km})": lab_g},
               FIG / "tres_algoritmos_perfis.png")

    # 4) resumo
    R = ["# Modelo de Mistura Gaussiana (GMM)\n"]
    R.append(f"- Dados: matriz A4, {info['n_municipios']} municípios × 2 anos = {len(X)} instâncias; "
             f"pré-processamento `{REFERENCIA.nome}`; tratamentos {reg['acima_100']} / {reg['perdas_zero']}.")
    R.append(f"- `sklearn.mixture.GaussianMixture`, EM, n_init = {N_INIT_GMM}, random_state = {a.seed}.\n")
    R.append("## 1. Tipo de covariância\n")
    R.extend(f"- {p}" for p in porque_cov)
    R.append(f"\n**Covariância usada: `{cov}`.**\n")
    R.append("k de menor BIC em cada tipo (o BIC cai até o fim da grade, sem mínimo interno):\n")
    R.append(bic_min.to_markdown(index=False))
    R.append("\nGrade completa (resumo):\n")
    R.append(grade.pivot(index="k", columns="covariancia", values="bic").round(0).to_markdown())
    R.append("\n## 2. Candidatos e regra (mesma do k-means e do Ward)\n")
    R.append(cs.round(4).to_markdown(index=False))
    R.append(f"\n- Silhueta: **k = {k_sil}**; Cotovelo do SSE: **k = {k_cot}**.\n")
    R.append(tab_av[["k", "indicado_por", "papel", "silhueta", "estabilidade", "menor_cluster", "univariado",
                     "variavel_univariada", "admissivel", "ok_multivariado"]].round(3).to_markdown(index=False))
    R.append("")
    R.extend(f"- {p}" for p in porque)
    R.append(f"\n**Pela regra aplicada ao GMM isoladamente: k = {k_g}.**")
    R.append(f"\n> A solução do trabalho é a do k-means com k = {k_km} (decisão do grupo); o GMM é usado como "
             "verificação com o mesmo k. Ver `docs/decisoes.md`.\n")
    R.append(f"## 3. Comparação dos três algoritmos (k = {k_km})\n")
    R.append(ari.round(3).to_markdown(index=False))
    R.append(f"\nk-means × GMM (instâncias):\n\n{ct.to_markdown()}\n")
    R.append(f"### Sensibilidade ao tipo de covariância (k = {k_km})\n")
    R.append("'separa por acesso?' = sim quando o ARI com o k-means passa de 0,7 (reproduz os três perfis).\n")
    R.append(sens.to_markdown(index=False))
    R.append("")
    R.append(f"Estabilidade por cluster (Jaccard médio, B = {B}) e incerteza de pertença no GMM "
             f"(% de instâncias com probabilidade máxima < {LIMIAR_INCERTEZA}); clusters do Ward e do GMM "
             "casados com os do k-means pela maior sobreposição:\n")
    R.append(jac.to_markdown(index=False))
    R.append(f"\n## 4. Perfis do GMM (k = {k_km}): mediana [Q1–Q3]\n")
    R.append(pf_g.to_markdown(index=False))
    (OUT / "resumo_gmm.md").write_text("\n".join(R), encoding="utf-8")
    print("\n".join(R))


if __name__ == "__main__":
    main()
