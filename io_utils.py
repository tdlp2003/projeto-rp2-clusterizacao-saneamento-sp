import re, glob
import pandas as pd
from .config import RAW

def find_one(pattern: str):
    hits = sorted(glob.glob(str(RAW / pattern), recursive=True))
    # prefere .xls original; cai para .xlsx convertido se xlrd não existir
    if not hits:
        raise FileNotFoundError(f"Nada encontrado para {pattern} em {RAW}")
    xlsx = [h for h in hits if h.endswith('.xlsx')]
    return (xlsx or hits)[0]   # prefere .xlsx (não exige xlrd)

def read_raw(path: str) -> pd.DataFrame:
    """Lê a aba de dados sem cabeçalho (os arquivos têm 3-6 linhas de título)."""
    engine = "xlrd" if path.endswith(".xls") else None   # .xls exige: pip install xlrd
    return pd.read_excel(path, header=None, sheet_name=0, engine=engine)

def locate_code_row(raw: pd.DataFrame, regex: str, max_rows: int = 20) -> int:
    """Índice da linha onde >=5 células casam com `regex` (linha dos códigos de indicador)."""
    pat = re.compile(regex)
    for i in range(min(max_rows, len(raw))):
        if raw.iloc[i].fillna('').astype(str).str.strip().str.match(pat).sum() >= 5:
            return i
    raise ValueError(f"Linha de códigos não encontrada (regex={regex})")
