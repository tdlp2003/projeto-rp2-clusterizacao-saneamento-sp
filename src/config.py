"""Caminhos, constantes e a lista de indicadores do projeto (definida só aqui)."""
import os
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("SANEAMENTO_RAW", ROOT / "data" / "raw"))
EXTRAIDO = RAW / "extraido"          # arquivos tirados dos ZIPs (gerado, fora do git)
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
PAINEL = PROC / "painel_sp_2019_2024.csv"
DICIONARIO = PROC / "dicionario_variaveis.csv"

UF = "SP"
RANDOM_STATE = 42
ANOS = (2019, 2024)

# ------------------------------------------------------------------ arquivos brutos
# Planilhas que ficam dentro de ZIPs: (zip relativo a RAW, padrão do nome do arquivo interno).
# `python -m src.build_panel` extrai só estes arquivos para data/raw/extraido/.
ZIPS = [
    ("Planilhas_AE2019/Planilha_AE2019_Completa_Regionais.zip", "Planilha_AE_Indicadores_SABESP-35503000.xls"),
    ("Planilhas_AE2019/Planilhas_AE2019_Completa_LPU.zip", "Planilha_LPU_Indicadores.xls"),
    ("Planilhas_AE2019/Planilhas_AE2019_Completa_LEP.zip", "Planilha_LEP_Indicadores.xls"),
    ("Planilhas_AE2019/Planilhas_AE2019_Completa_LPR.zip", "Planilha_LPR_Indicadores.xls"),
    ("SINISA_Resultados_Ref2024.zip", "SINISA_AGUA_Indicadores_Base Municipal_2024"),
    ("SINISA_ESGOTO_Planilhas_2024.zip", "SINISA_ESGOTO_Indicadores_Base Municipal_2024"),
    ("SINISA_RESIDUOS_planilhas_2024.zip", "SINISA_RESIDUOS_Indicadores_2024"),
]

# Padrões (glob, relativos a RAW) usados pelo build_panel.
AE2019 = {  # fonte do prestador -> arquivo
    "SABESP": "extraido/Planilha_AE_Indicadores_SABESP-35503000.xls*",
    "LPU":    "extraido/Planilha_LPU_Indicadores.xls*",
    "LPR":    "extraido/Planilha_LPR_Indicadores.xls*",
    "LEP":    "extraido/Planilha_LEP_Indicadores.xls*",
}
RS2019 = "DiagRS2019_XLS/Planilha_Indicadores_RS_2019.xlsx"
SINISA2024 = {
    "agua":   "extraido/SINISA_AGUA_Indicadores_Base Municipal_2024*.xlsx",
    "esgoto": "extraido/SINISA_ESGOTO_Indicadores_Base Municipal_2024*.xlsx",
    "res":    "extraido/SINISA_RESIDUOS_Indicadores_2024.xlsx",
}
IAS = "municipiose_saneamento_export_27_09_2026.csv"   # população (= DFE0001 do SINISA 2024)

# Faixas de porte (habitantes). Ver docs/decisoes.md.
PORTE_CORTES = (0, 20_000, 50_000, 100_000, 250_000, float("inf"))
PORTE_ROTULOS = ("até 20 mil", "20–50 mil", "50–100 mil", "100–250 mil", "mais de 250 mil")


# ------------------------------------------------------------------ indicadores
class Indicador(NamedTuple):
    col_2019: str     # coluna no painel (SNIS)
    col_2024: str     # coluna no painel (SINISA)
    tipo: str         # "teto": % com acúmulo em 100 | "assimetrica": cauda à direita
    rotulo: str
    unidade: str


MATRIZES = {
    # Recomendada pela auditoria (docs/auditoria_etapa1, §10). Só água e esgoto.
    "A4": {
        "agua":       Indicador("ae19_IN055", "s24_IAG0001", "teto", "Água (atend. total)", "%"),
        "perdas":     Indicador("ae19_IN049", "s24_IAG2013", "assimetrica", "Perdas na distribuição", "%"),
        "esgoto":     Indicador("ae19_IN056", "s24_IES0001", "teto", "Esgoto (atend. total)", "%"),
        "tratamento": Indicador("ae19_IN016", "s24_IES2004", "teto", "Tratamento do esgoto coletado", "%"),
    },
    # Matriz usada antes (inclui resíduos). Mantida só para análise de sensibilidade.
    "R4": {
        "agua":   Indicador("ae19_IN055", "s24_IAG0001", "teto", "Água (atend. total)", "%"),
        "esgoto": Indicador("ae19_IN056", "s24_IES0001", "teto", "Esgoto (atend. total)", "%"),
        "coleta": Indicador("rs19_IN015", "s24_IRS0001", "teto", "Coleta RDO (cobertura)", "%"),
        "massa":  Indicador("rs19_IN028", "s24_IRS1004", "assimetrica", "Massa coletada per capita", "kg/hab/dia"),
    },
}
MATRIZ = "A4"                      # matriz principal do artigo
INDICADORES = MATRIZES[MATRIZ]
