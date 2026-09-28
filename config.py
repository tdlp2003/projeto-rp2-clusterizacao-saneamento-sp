"""Caminhos e constantes. Ajuste apenas RAW se mover as pastas."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("SANEAMENTO_RAW", ROOT / "data" / "raw"))
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"

UF = "SP"

# --- Estrutura esperada em data/raw (descompacte os ZIPs aqui) -------------
# raw/snis_ae_2019/       <- conteúdo de Planilhas_AE2019.zip (após descompactar os ZIPs internos)
# raw/snis_rs_2019/       <- conteúdo de DiagRS2019_XLS.zip
# raw/sinisa_2024/        <- conteúdo dos 3 ZIPs SINISA (Água, Esgoto, Resíduos)
# raw/ias/                <- municipiose_saneamento_export_27_09_2026.csv (opcional, só p/ população)
AE2019 = {  # arquivo (glob) -> fonte do prestador
    "SABESP": "snis_ae_2019/**/Planilha_AE_Indicadores_SABESP-35503000.xls*",
    "LPU":    "snis_ae_2019/**/Planilha_LPU_Indicadores.xls*",
    "LPR":    "snis_ae_2019/**/Planilha_LPR_Indicadores.xls*",
    "LEP":    "snis_ae_2019/**/Planilha_LEP_Indicadores.xls*",
}
RS2019 = "snis_rs_2019/**/Planilha_Indicadores_RS_2019.xlsx"
SINISA2024 = {
    "agua":   "sinisa_2024/**/*Base Municipal*/*AGUA_Indicadores_Base*.xlsx",
    "esgoto": "sinisa_2024/**/Esgoto - Base Municipal/*ESGOTO_Indicadores*.xlsx",
    "res":    "sinisa_2024/**/SINISA_RESIDUOS_Indicadores_2024.xlsx",
}
