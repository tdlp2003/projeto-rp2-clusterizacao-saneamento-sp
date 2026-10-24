"""
clustering.py — Etapa 4: K-means, com o número de clusters definido por uma regra explícita que
combina o Método da Silhueta e o Método do Cotovelo. Os critérios ficam em config.CRITERIOS_K.
Decisão do grupo (2026-10-24): apresentar somente a solução adotada (hoje, k = 3).

1) Método da Silhueta (Rousseeuw, 1987). Coeficiente de silhueta de uma instância i:
       a(i) = distância média de i às outras instâncias do seu próprio cluster
       b(i) = menor distância média de i às instâncias de um outro cluster
       s(i) = (b(i) - a(i)) / max(a(i), b(i))          (-1 <= s(i) <= 1)
   Para cada k da grade, S(k) = média de s(i) sobre TODAS as instâncias. Candidato: k = argmax S(k)
   (empate: menor k). A silhueta só existe para k >= 2.

2) Método do Cotovelo (Nainggolan et al., 2019). Erro Quadrático Total
       SSE(k) = soma, sobre todas as instâncias, da distância euclidiana ao quadrado até o centroide
                do seu cluster   (no scikit-learn: KMeans.inertia_)
   de k = 1 (um único grupo; SSE = soma total dos quadrados) até o k máximo da grade. O cotovelo é
   o ponto a partir do qual aumentar k reduz pouco o SSE. Regra objetiva: com k e SSE normalizados
   para [0, 1], é o k mais distante da reta que liga o primeiro e o último ponto da curva. Depende
   da grade de k testada.

3) Regra de escolha. Os k indicados pelos dois métodos são os CANDIDATOS. Cada um é avaliado:
     (a) silhueta média > silhueta_min                     -> há estrutura de grupos
     (b) estabilidade bootstrap (ARI médio) >= estabilidade_min -> a partição se repete em reamostragens
     (c) menor cluster >= menor_cluster_min das instâncias  -> nenhum grupo pequeno demais
     (d) reprodução por uma única variável < univariado_max -> é um perfil multivariado
   Um candidato é ADMISSÍVEL se passa em (a), (b) e (c), e é MULTIVARIADO se também passa em (d).
     - Solução adotada: o maior k entre os candidatos admissíveis e multivariados (mais detalhe
       quando ambos servem). Se nenhum for multivariado, o maior admissível. Se nenhum for
       admissível, o k da silhueta, com aviso.
     - Os demais candidatos aparecem só na tabela de avaliação, como descartados. Com
       CRITERIOS_K["apresentar_complementar"] = True, o outro candidato admissível também é gerado
       como "nível geral" (não é o caso no trabalho, por decisão do grupo).
   Se silhueta e cotovelo concordarem, há uma única solução.

Entrada: a matriz X de src/preprocess.py (configuração REFERENCIA), já com os tratamentos de
config.TRATAMENTOS. Com o escopo "conjunto", 2019 e 2024 são padronizados no mesmo espaço e
clusterizados juntos (cada município-ano é uma instância), então os rótulos são comparáveis entre anos.

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
from sklearn.metrics import adjusted_rand_score, silhouette_samples, silhouette_score

from .config import ANOS, CRITERIOS_K, INDICADORES, MATRIZ, OUT, PAINEL, PORTE_ROTULOS, RANDOM_STATE
from .preprocess import (ESCALA, ESCOPO, INCLUSAO, REFERENCIA, TRANSF, Cfg, executar, para_longo,
                         tratar_valores)

N_INIT = 50   # reinícios do k-means (fica a melhor inércia)

# Paleta categórica (ordem fixa) para identificar clusters nas figuras.
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
NEUTRO, TEXTO, TEXTO_2 = "#6b6a63", "#1f1f1e", "#5f5e58"


# ------------------------------------------------------------------ k-means, silhueta e cotovelo
def ajustar_kmeans(X: pd.DataFrame, k: int, seed: int = RANDOM_STATE, n_init: int = N_INIT) -> KMeans:
    return KMeans(n_clusters=k, n_init=n_init, random_state=seed).fit(X.to_numpy())


def curva_silhueta(X: pd.DataFrame, ks=range(2, 11), seed: int = RANDOM_STATE,
                   n_init: int = N_INIT) -> pd.DataFrame:
    """Para cada k: silhueta média sobre todas as instâncias, SSE (Erro Quadrático Total) e
    tamanho do menor cluster."""
    linhas = []
    for k in ks:
        if not 2 <= k <= len(X) - 1:
            raise ValueError(f"silhueta exige 2 <= k <= n-1 (k={k}, n={len(X)})")
        km = ajustar_kmeans(X, k, seed, n_init)
        linhas.append({
            "k": k,
            "silhueta_media": silhouette_score(X.to_numpy(), km.labels_),
            "sse": km.inertia_,
            "menor_cluster": int(np.bincount(km.labels_).min()),
        })
    return pd.DataFrame(linhas)


def escolher_k(curva: pd.DataFrame) -> int:
    """Método da Silhueta: k com a maior silhueta média; em empate (diferença < 1e-12), o menor k."""
    melhor = curva["silhueta_media"].max()
    return int(curva.loc[curva["silhueta_media"] >= melhor - 1e-12, "k"].min())


def curva_cotovelo(X: pd.DataFrame, curva: pd.DataFrame) -> pd.DataFrame:
    """Curva SSE × k para o Método do Cotovelo: acrescenta k = 1 à curva da silhueta.
    Com um único grupo o centroide é a média, então SSE(1) = soma total dos quadrados."""
    sse1 = float(((X - X.mean()) ** 2).to_numpy().sum())
    return pd.concat([pd.DataFrame({"k": [1], "sse": [sse1]}), curva[["k", "sse"]]], ignore_index=True)


def k_cotovelo(curva: pd.DataFrame) -> int:
    """Método do Cotovelo: k de maior distância à reta entre o primeiro e o último ponto da curva
    SSE × k, com os dois eixos normalizados para [0, 1]."""
    c = curva.sort_values("k")
    x = (c["k"] - c["k"].min()) / (c["k"].max() - c["k"].min())
    y = (c["sse"] - c["sse"].min()) / (c["sse"].max() - c["sse"].min())
    # reta de (0, 1) a (1, 0) no espaço normalizado (SSE decrescente): distância ∝ |x + y - 1|
    dist = (x + y - 1).abs() / np.sqrt(2)
    return int(c["k"].iloc[int(np.argmax(dist.to_numpy()))])


def renumerar_por_tamanho(labels: np.ndarray) -> np.ndarray:
    """Rótulos 1..k, com 1 = maior cluster (o k-means numera em ordem arbitrária)."""
    ordem = pd.Series(labels).value_counts().index          # do maior para o menor
    mapa = {antigo: novo for novo, antigo in enumerate(ordem, start=1)}
    return np.array([mapa[x] for x in labels])


# ------------------------------------------------------------------ avaliação dos candidatos
def estabilidade_bootstrap(X: pd.DataFrame, k: int, B: int, seed: int = RANDOM_STATE,
                           n_init: int = 10) -> np.ndarray:
    """Reamostra municípios com reposição (os dois anos de cada município juntos), reajusta o
    K-means, classifica todas as instâncias originais pelo modelo reamostrado e mede o ARI com a
    partição dos dados completos. Devolve os B valores de ARI."""
    rng = np.random.default_rng(seed)
    base = ajustar_kmeans(X, k, seed, n_init).labels_
    muns = X.index.get_level_values("cod_mun6").unique().to_numpy()
    aris = []
    for b in range(B):
        amostra = rng.choice(muns, size=len(muns), replace=True)
        Xb = pd.concat([X.xs(m, level="cod_mun6", drop_level=False) for m in amostra])
        km = ajustar_kmeans(Xb, k, seed + b + 1, n_init)
        aris.append(adjusted_rand_score(base, km.predict(X.to_numpy())))
    return np.array(aris)


def reproducao_univariada(X: pd.DataFrame, labels: np.ndarray, seed: int = RANDOM_STATE) -> tuple[float, str]:
    """O quanto a partição é reproduzida agrupando UMA variável sozinha: para cada variável, K-means
    com o mesmo k só nela; devolve (maior ARI com a partição, variável correspondente)."""
    k = len(np.unique(labels))
    melhor = (-1.0, "")
    for f in X.columns:
        u = KMeans(n_clusters=k, n_init=20, random_state=seed).fit_predict(X[[f]].to_numpy())
        ari = adjusted_rand_score(labels, u)
        if ari > melhor[0]:
            melhor = (ari, f)
    return melhor


def avaliar_candidato(X: pd.DataFrame, k: int, criterios: dict = CRITERIOS_K,
                      seed: int = RANDOM_STATE) -> dict:
    """Mede os quatro critérios da regra de escolha para um k."""
    lab = ajustar_kmeans(X, k, seed).labels_
    boot = estabilidade_bootstrap(X, k, criterios["B"], seed)
    ari_uni, var_uni = reproducao_univariada(X, lab, seed)
    av = {
        "k": k,
        "silhueta": silhouette_score(X.to_numpy(), lab),
        "estabilidade": float(boot.mean()),
        "menor_cluster": float(np.bincount(lab).min() / len(lab)),
        "univariado": float(ari_uni),
        "variavel_univariada": var_uni,
    }
    av["ok_silhueta"] = av["silhueta"] > criterios["silhueta_min"]
    av["ok_estabilidade"] = av["estabilidade"] >= criterios["estabilidade_min"]
    av["ok_menor_cluster"] = av["menor_cluster"] >= criterios["menor_cluster_min"]
    av["ok_multivariado"] = av["univariado"] < criterios["univariado_max"]
    av["admissivel"] = av["ok_silhueta"] and av["ok_estabilidade"] and av["ok_menor_cluster"]
    return av


def escolher_solucoes(avaliacoes: list[dict], k_sil: int) -> tuple[int, int | None, list[str]]:
    """Aplica a regra: devolve (k principal, k complementar ou None, justificativa em frases)."""
    porque = []
    adm = [a for a in avaliacoes if a["admissivel"]]
    multi = [a for a in adm if a["ok_multivariado"]]
    if multi:
        principal = max(a["k"] for a in multi)
        porque.append(f"k = {principal} é o maior candidato admissível e multivariado.")
    elif adm:
        principal = max(a["k"] for a in adm)
        porque.append(f"Nenhum candidato é multivariado; k = {principal} é o maior admissível.")
    else:
        principal = k_sil
        porque.append(f"AVISO: nenhum candidato é admissível; usa-se o k da silhueta ({k_sil}).")
    for a in avaliacoes:
        falhas = [n for n, ok in (("silhueta", a["ok_silhueta"]), ("estabilidade", a["ok_estabilidade"]),
                                  ("menor cluster", a["ok_menor_cluster"]),
                                  ("multivariado", a["ok_multivariado"])) if not ok]
        porque.append(f"k = {a['k']}: " + ("passa em todos os critérios." if not falhas
                                            else "não passa em: " + ", ".join(falhas) + "."))
    outros = [a["k"] for a in adm if a["k"] != principal]
    complementar = outros[0] if outros else None
    return principal, complementar, porque


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


def fig_cotovelo(curva: pd.DataFrame, k_cot: int, caminho):
    fig, ax = plt.subplots(figsize=(5.6, 3.4))
    ax.plot(curva.k, curva.sse, color=NEUTRO, lw=2, marker="o", ms=6, zorder=2)
    ini, fim = curva.iloc[0], curva.iloc[-1]
    ax.plot([ini.k, fim.k], [ini.sse, fim.sse], color="#c9c8c1", lw=1, ls="--", zorder=1)
    s = curva.set_index("k").loc[k_cot, "sse"]
    ax.plot([k_cot], [s], marker="o", ms=10, color=CORES[0], mec="white", mew=2, zorder=3)
    ax.annotate(f"cotovelo: k = {k_cot}", (k_cot, s), xytext=(10, 6), textcoords="offset points",
                fontsize=8, color=TEXTO)
    ax.set_xticks(curva.k)
    ax.set_xlabel("número de clusters (k)", color=TEXTO_2, fontsize=9)
    ax.set_ylabel("SSE (Erro Quadrático Total)", color=TEXTO_2, fontsize=9)
    ax.set_title("Método do Cotovelo — K-means", color=TEXTO, fontsize=10, loc="left")
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
    from .comparar_k import fig_perfis, perfis, por_porte, transicao   # import local: evita ciclo

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
    feats = list(INDICADORES)

    # 1) candidatos: silhueta e cotovelo
    curva = curva_silhueta(X, range(a.kmin, a.kmax + 1), a.seed)
    k_sil = escolher_k(curva)
    cot = curva_cotovelo(X, curva)
    k_cot = k_cotovelo(cot)
    curva.round(4).to_csv(TAB / "kmeans_silhueta_por_k.csv", index=False)
    cot.round(4).to_csv(TAB / "kmeans_cotovelo.csv", index=False)
    fig_curva(curva, k_sil, FIG / "kmeans_silhueta_por_k.png")
    fig_cotovelo(cot, k_cot, FIG / "kmeans_cotovelo.png")

    # 2) avaliação dos candidatos e regra de escolha
    candidatos = sorted({k_sil, k_cot})
    avs = [avaliar_candidato(X, k, CRITERIOS_K, a.seed) for k in candidatos]
    k_pri, k_comp, porque = escolher_solucoes(avs, k_sil)
    if not CRITERIOS_K.get("apresentar_complementar", False):
        if k_comp is not None:
            porque.append(f"k = {k_comp} também é admissível, mas, por decisão do grupo, só a solução "
                          f"adotada (k = {k_pri}) é apresentada.")
        k_comp = None
    elif k_comp is not None:
        porque.append(f"k = {k_comp} é admissível e é apresentado como solução complementar (nível geral).")
    tab_av = pd.DataFrame(avs)
    tab_av.insert(1, "indicado_por", ["silhueta e cotovelo" if k == k_sil == k_cot else
                                      "silhueta" if k == k_sil else "cotovelo" for k in tab_av.k])
    tab_av.insert(2, "papel", ["adotado" if k == k_pri else "complementar" if k == k_comp else "descartado"
                               for k in tab_av.k])
    tab_av.round(4).to_csv(TAB / "kmeans_avaliacao_candidatos.csv", index=False)

    # 3) partições finais (principal e complementar)
    solucoes = [k for k in (k_pri, k_comp) if k is not None]
    labs = {k: pd.Series(renumerar_por_tamanho(ajustar_kmeans(X, k, a.seed).labels_), index=X.index)
            for k in solucoes}
    fig_silhueta_instancias(X, labs[k_pri].to_numpy(), FIG / "kmeans_silhueta_instancias.png")
    fig_perfis(L, {k: labs[k] for k in sorted(solucoes)}, FIG / "kmeans_perfis.png")

    # 4) rótulos por município-ano (as duas soluções), com valores originais e porte
    ident = painel.set_index("cod_mun6")[["cod_ibge7", "municipio", "populacao", "porte"]]
    rot = L.loc[X.index].reset_index().join(ident, on="cod_mun6")
    rot[f"cluster_k{k_pri}"] = labs[k_pri].to_numpy()
    rot["silhueta"] = silhouette_samples(X.to_numpy(), labs[k_pri].to_numpy())
    if k_comp is not None:
        rot[f"cluster_complementar_k{k_comp}"] = labs[k_comp].to_numpy()
    cols_cl = [c for c in rot.columns if c.startswith(("cluster_", "silhueta"))]
    rot = rot[["cod_ibge7", "cod_mun6", "municipio", "populacao", "porte", "ano"] + cols_cl + feats]
    rot.round(4).to_csv(TAB / "kmeans_rotulos.csv", index=False)

    # 5) perfis, porte e transição de cada solução; correspondência entre as duas
    porte = painel.set_index("cod_mun6")["porte"]
    blocos = {}
    for k in solucoes:
        sil = silhouette_samples(X.to_numpy(), labs[k].to_numpy())
        pf, pp, tr = perfis(L, labs[k], sil), por_porte(labs[k], porte), transicao(labs[k])
        pf.to_csv(TAB / f"kmeans_perfis_k{k}.csv", index=False)
        pp.to_csv(TAB / f"kmeans_porte_k{k}.csv")
        tr.to_csv(TAB / f"kmeans_transicao_k{k}.csv")
        blocos[k] = (pf, pp, tr)
    corresp = None
    if k_comp is not None:
        corresp = pd.crosstab(labs[k_pri].rename(f"adotada (k={k_pri})"),
                              labs[k_comp].rename(f"complementar (k={k_comp})"))
        corresp.to_csv(TAB / "kmeans_correspondencia_solucoes.csv")

    # 6) resumo
    R = ["# Resumo da clusterização (K-means; regra Silhueta + Cotovelo)\n"]
    R.append(f"- Matriz **{MATRIZ}**: {', '.join(INDICADORES[f].rotulo for f in feats)}.")
    R.append(f"- Pré-processamento: `{cfg.nome}` "
             f"({'referência' if cfg == REFERENCIA else 'escolhido na linha de comando'}).")
    R.append(f"- Instâncias: **{len(X)}** (municípios-ano), {info['n_municipios']} municípios.")
    R.append(f"- Tratamento de valores: valores > 100 → **{reg_trat['acima_100']}**; perdas = 0 → "
             f"**{reg_trat['perdas_zero']}** ({len(reg_trat['alteracoes'])} células; ver "
             "`docs/decisao_vinhedo_perdas.md`).")
    R.append(f"- K-means: n_init = {N_INIT}, random_state = {a.seed}. Grade k = {a.kmin}..{a.kmax}.")
    R.append(f"- Critérios (`config.CRITERIOS_K`): silhueta > {CRITERIOS_K['silhueta_min']}, "
             f"estabilidade ≥ {CRITERIOS_K['estabilidade_min']} (B = {CRITERIOS_K['B']}), "
             f"menor cluster ≥ {100 * CRITERIOS_K['menor_cluster_min']:.0f}% das instâncias, "
             f"reprodução por uma única variável < {CRITERIOS_K['univariado_max']}.")
    R.append(f"\n## 1. Candidatos\n\n{curva.round(4).to_markdown(index=False)}\n")
    R.append(f"- Método da Silhueta: **k = {k_sil}** (maior silhueta média = {curva.silhueta_media.max():.4f}).")
    R.append(f"- Método do Cotovelo: **k = {k_cot}** (curva SSE × k de k = 1 a {a.kmax}).\n")
    R.append("## 2. Avaliação dos candidatos e regra de escolha\n")
    R.append(tab_av[["k", "indicado_por", "papel", "silhueta", "estabilidade", "menor_cluster", "univariado",
                     "variavel_univariada", "admissivel", "ok_multivariado"]].round(3).to_markdown(index=False))
    R.append("")
    R.extend(f"- {p}" for p in porque)
    R.append(f"\n**Solução adotada: k = {k_pri}.**" +
             (f" **Solução complementar: k = {k_comp}.**" if k_comp is not None else "") + "\n")
    if corresp is not None:
        R.append(f"## 3. Correspondência entre as soluções (instâncias)\n\n{corresp.to_markdown()}\n")
    for k in solucoes:
        pf, pp, tr = blocos[k]
        papel = "adotada" if k == k_pri else "complementar"
        R.append(f"## Solução {papel} (k = {k})\n")
        R.append("Perfis: mediana [Q1–Q3] em unidades originais.\n")
        R.append(pf.to_markdown(index=False))
        R.append("\n% de cada faixa de porte em cada cluster (municípios-ano, 2019 e 2024):\n")
        R.append(pp.to_markdown())
        R.append("\nTransição 2019 → 2024 (nº de municípios):\n")
        R.append(tr.to_markdown())
        R.append("")
    R.append("> Clusters numerados por tamanho (1 = maior) dentro de cada solução. Silhuetas entre 0,26 e "
             "0,50 indicam estrutura fraca (Kaufman e Rousseeuw, 1990): os perfis devem ser lidos como "
             "tendências, não como grupos nitidamente separados.")
    (OUT / "resumo_clustering.md").write_text("\n".join(R), encoding="utf-8")
    print("\n".join(R))


if __name__ == "__main__":
    main()
