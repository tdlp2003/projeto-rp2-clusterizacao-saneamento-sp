"""
eda.py — Análise exploratória do painel SNIS 2019 x SINISA 2024 (SP).

Uso (na raiz do repositório):
    python -m src.eda                      # usa data/processed/painel_sp_2019_2024.csv
    python -m src.eda caminho/painel.csv   # caminho alternativo

Saídas:
    outputs/tabelas/*.csv
    outputs/figuras/*.png
    outputs/resumo_eda.md   (números prontos para o texto do artigo)

Nenhuma decisão de clusterização é tomada aqui: só descrição dos dados.
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from .config import DICIONARIO, INDICADORES, MATRIZ, MATRIZES, OUT, PAINEL as PAINEL_PADRAO, PORTE_ROTULOS

PAINEL = Path(sys.argv[1]) if len(sys.argv) > 1 else PAINEL_PADRAO
DICIO = DICIONARIO
TAB, FIG = OUT / "tabelas", OUT / "figuras"
for d in (TAB, FIG):
    d.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="paper")
plt.rcParams.update({"figure.dpi": 130, "savefig.bbox": "tight"})

# ---------------------------------------------------------------- dados
df = pd.read_csv(PAINEL, encoding="utf-8-sig")
dic = pd.read_csv(DICIO, encoding="utf-8-sig") if DICIO.exists() else None

# Indicadores centrais = matriz principal de config.py: rótulo -> (col 2019, col 2024, unidade)
CORE = {i.rotulo: (i.col_2019, i.col_2024, i.unidade) for i in INDICADORES.values()}
core_cols = [c for a, b, _ in CORE.values() for c in (a, b)]


def nome(col):
    if dic is None:
        return col
    cod = col.split("_", 1)[1]
    fonte = {"ae19": "SNIS-AE", "rs19": "SNIS-RS", "s24": "SINISA"}[col.split("_")[0]]
    m = dic[(dic.codigo == cod) & (dic.fonte.str.contains(fonte))]
    return m.nome.iloc[0] if len(m) else cod


# ---------------------------------------------------------------- 1. cobertura
def descreve(s):
    s = s.dropna()
    q = s.quantile([.05, .25, .5, .75, .95])
    iqr = q[.75] - q[.25]
    out = ((s < q[.25] - 1.5 * iqr) | (s > q[.75] + 1.5 * iqr)).sum()
    return pd.Series({
        "N": len(s), "ausentes_%": 100 * (1 - len(s) / len(df)),
        "media": s.mean(), "dp": s.std(), "min": s.min(),
        "p05": q[.05], "p25": q[.25], "mediana": q[.5], "p75": q[.75],
        "p95": q[.95], "max": s.max(), "assimetria": stats.skew(s),
        "no_teto_100_%": 100 * (s >= 99.999).mean(),
        "no_zero_%": 100 * (s <= 0).mean(),
        "outliers_IQR_n": out, "outliers_IQR_%": 100 * out / len(s),
    })


tab_core = pd.DataFrame({c: descreve(df[c]) for c in core_cols}).T
tab_core.insert(0, "indicador", [nome(c) for c in tab_core.index])
tab_core.round(2).to_csv(TAB / "descritivas_indicadores_centrais.csv", index_label="coluna")

num = [c for c in df.select_dtypes("number").columns if c.startswith(("ae19_", "rs19_", "s24_"))]
cob = pd.DataFrame({"N": df[num].notna().sum()})
cob["ausentes_%"] = 100 * (1 - cob.N / len(df))
cob["nome"] = [nome(c) for c in cob.index]
cob.sort_values("ausentes_%").round(1).to_csv(TAB / "cobertura_todas_variaveis.csv", index_label="coluna")

# ---------------------------------------------------------------- 2. completos
def n_completos(cols):
    return int(df[cols].notna().all(axis=1).sum())


comb = {}
for nome_m, m in MATRIZES.items():
    c19, c24 = [i.col_2019 for i in m.values()], [i.col_2024 for i in m.values()]
    comb[f"{nome_m} — 2019"] = c19
    comb[f"{nome_m} — 2024"] = c24
    comb[f"{nome_m} — 2019 e 2024"] = c19 + c24
pd.Series({k: n_completos(v) for k, v in comb.items()}, name="N_completos").to_csv(
    TAB / "municipios_completos_por_combinacao.csv")

# 2b. quem fica de fora, por porte (a perda de municípios não deve depender do porte)
completo = df[core_cols].notna().all(axis=1)
tab_porte = (pd.DataFrame({"porte": df["porte"], "completo": completo})
             .groupby("porte").completo.agg(total="size", completos="sum")
             .reindex(PORTE_ROTULOS))
tab_porte["completos_%"] = 100 * tab_porte.completos / tab_porte.total
for nome_m, m in MATRIZES.items():
    cols = [c for i in m.values() for c in (i.col_2019, i.col_2024)]
    tab_porte[f"completos_%_{nome_m}"] = (100 * df[cols].notna().all(axis=1)
                                          .groupby(df["porte"]).mean().reindex(PORTE_ROTULOS))
tab_porte = tab_porte.drop(columns="completos_%")
tab_porte.round(1).to_csv(TAB / "completos_por_porte.csv")

# ---------------------------------------------------------------- 3. 2019 x 2024
rows = []
for k, (a, b, u) in CORE.items():
    p = df[[a, b]].dropna()
    if len(p) < 10:
        continue
    d = p[b] - p[a]
    w = stats.wilcoxon(p[b], p[a]) if (d != 0).any() else None
    rho = stats.spearmanr(p[a], p[b])[0]
    rows.append({
        "indicador": k, "unidade": u, "N_pareado": len(p),
        "mediana_2019": p[a].median(), "mediana_2024": p[b].median(),
        "media_2019": p[a].mean(), "media_2024": p[b].mean(),
        "dif_mediana": d.median(), "dif_media": d.mean(),
        "%_aumentou": 100 * (d > 0).mean(), "%_diminuiu": 100 * (d < 0).mean(),
        "%_igual": 100 * (d == 0).mean(),
        "spearman_19_24": rho, "wilcoxon_p": w.pvalue if w else np.nan,
    })
tab_tempo = pd.DataFrame(rows)
tab_tempo.round(3).to_csv(TAB / "comparacao_2019_2024_pareada.csv", index=False)

# ---------------------------------------------------------------- 4. correlações
for ano, cols in (("2019", [a for a, _, _ in CORE.values()]),
                  ("2024", [b for _, b, _ in CORE.values()])):
    corr = df[cols].corr(method="spearman")
    corr.index = corr.columns = list(CORE)
    corr.round(3).to_csv(TAB / f"spearman_{ano}.csv")
    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1, ax=ax,
                cbar_kws={"label": "ρ de Spearman"})
    ax.set_title(f"Correlação de Spearman — {ano}")
    fig.savefig(FIG / f"correlacao_spearman_{ano}.png")
    plt.close(fig)

# ---------------------------------------------------------------- 5. figuras
# 5a. distribuições 2019 x 2024
fig, axes = plt.subplots(2, (len(CORE) + 1) // 2, figsize=(9, 6.4), squeeze=False)
for ax, (k, (a, b, u)) in zip(axes.ravel(), CORE.items()):
    for col, lab, cor in ((a, "2019 (SNIS)", "#4C78A8"), (b, "2024 (SINISA)", "#F58518")):
        sns.histplot(df[col].dropna(), bins=30, stat="density", alpha=.45, color=cor,
                     label=lab, ax=ax, edgecolor="white")
    ax.set_title(k)
    ax.set_xlabel(u)
    ax.set_ylabel("")
axes[0, 0].legend(frameon=False)
fig.suptitle("Distribuição dos indicadores centrais, 2019 × 2024", y=1.01)
fig.tight_layout()
fig.savefig(FIG / "distribuicoes_2019_2024.png")
plt.close(fig)

# 5b. boxplots lado a lado
fig, axes = plt.subplots(1, len(CORE), figsize=(2.75 * len(CORE), 3.4))
for ax, (k, (a, b, u)) in zip(axes, CORE.items()):
    long = pd.concat([
        pd.DataFrame({"ano": "2019", "v": df[a]}),
        pd.DataFrame({"ano": "2024", "v": df[b]}),
    ]).dropna()
    sns.boxplot(data=long, x="ano", y="v", ax=ax, palette=["#4C78A8", "#F58518"],
                hue="ano", legend=False, fliersize=2)
    ax.set_title(k, fontsize=9)
    ax.set_xlabel("")
    ax.set_ylabel(u)
fig.tight_layout()
fig.savefig(FIG / "boxplots_2019_2024.png")
plt.close(fig)

# 5c. dispersão 2019 x 2024 (pareado)
fig, axes = plt.subplots(1, len(CORE), figsize=(3 * len(CORE), 3.4))
for ax, (k, (a, b, u)) in zip(axes, CORE.items()):
    p = df[[a, b]].dropna()
    ax.scatter(p[a], p[b], s=8, alpha=.5, color="#4C78A8")
    lim = [0, max(p.max().max(), 1) * 1.02]
    ax.plot(lim, lim, "k--", lw=.8)
    ax.set_title(k, fontsize=9)
    ax.set_xlabel("2019")
    ax.set_ylabel("2024")
fig.tight_layout()
fig.savefig(FIG / "dispersao_2019_vs_2024.png")
plt.close(fig)

# 5d. mapa de ausência (indicadores centrais)
fig, ax = plt.subplots(figsize=(6, 5))
aus = df[core_cols].isna().sort_values(core_cols).astype(int)
sns.heatmap(aus, cbar=False, yticklabels=False, cmap=["#EEEEEE", "#D62728"], ax=ax)
ax.set_xticklabels(core_cols, rotation=45, ha="right")
ax.set_title("Padrão de ausência (vermelho = ausente)")
fig.savefig(FIG / "mapa_ausencia_centrais.png")
plt.close(fig)

# 5e. % ausente, todas as variáveis
fig, ax = plt.subplots(figsize=(7, 3.6))
sns.histplot(cob["ausentes_%"], bins=20, ax=ax, color="#54A24B")
ax.set_xlabel("% de municípios sem dado")
ax.set_ylabel("nº de variáveis")
ax.set_title(f"Ausência por variável ({len(cob)} variáveis)")
fig.savefig(FIG / "ausencia_por_variavel.png")
plt.close(fig)

# ---------------------------------------------------------------- 6. resumo .md
L = []
L.append("# Resumo da análise exploratória\n")
L.append(f"- Matriz principal: **{MATRIZ}** ({', '.join(CORE)}).")
L.append(f"- Municípios no painel: **{len(df)}**; variáveis numéricas: **{len(num)}** "
         f"(SNIS-AE 2019: {sum(c.startswith('ae19_') for c in num)}, "
         f"SNIS-RS 2019: {sum(c.startswith('rs19_') for c in num)}, "
         f"SINISA 2024: {sum(c.startswith('s24_') for c in num)}).")
if "respondeu_RS_2024" in df:
    L.append(f"- `respondeu_RS_2024`: {df.respondeu_RS_2024.value_counts(dropna=False).to_dict()}")
L.append("\n## Municípios completos por combinação\n")
for k, v in comb.items():
    L.append(f"- {k}: **{n_completos(v)}**")
L.append("\n## Municípios completos por porte (% da faixa)\n")
L.append(tab_porte.round(1).to_markdown())
L.append("\n## Indicadores centrais (descritivas)\n")
L.append(tab_core.drop(columns=["outliers_IQR_n"]).round(2).to_markdown())
L.append("\n## Comparação pareada 2019 × 2024\n")
L.append(tab_tempo.round(2).to_markdown(index=False))
L.append("\n> Atenção: SNIS→SINISA é mudança de metodologia; diferenças temporais "
         "misturam mudança real e mudança de coleta (limitação a declarar no artigo).")
(OUT / "resumo_eda.md").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))
