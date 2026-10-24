import glob
import re
import zipfile
from pathlib import Path

import pandas as pd

from .config import EXTRAIDO, RAW, ZIPS


def extrair_zips() -> None:
    """Extrai de cada ZIP listado em config.ZIPS só a planilha necessária, para data/raw/extraido/."""
    EXTRAIDO.mkdir(parents=True, exist_ok=True)
    for zip_rel, nome in ZIPS:
        with zipfile.ZipFile(RAW / zip_rel) as z:
            membros = [m for m in z.namelist() if Path(m).name.startswith(nome)]
            if len(membros) != 1:
                raise FileNotFoundError(f"Esperava 1 arquivo '{nome}*' em {zip_rel}, achei {membros}")
            destino = EXTRAIDO / Path(membros[0]).name
            if not destino.exists():
                destino.write_bytes(z.read(membros[0]))


def find_one(pattern: str) -> str:
    hits = sorted(glob.glob(str(RAW / pattern), recursive=True))
    if not hits:
        raise FileNotFoundError(f"Nada encontrado para {pattern} em {RAW}")
    xlsx = [h for h in hits if h.endswith(".xlsx")]
    return (xlsx or hits)[0]   # prefere .xlsx (não exige xlrd)


def read_raw(path: str) -> pd.DataFrame:
    """Lê a aba de dados sem cabeçalho (os arquivos têm 3-6 linhas de título)."""
    engine = "xlrd" if path.endswith(".xls") else None   # .xls exige: pip install xlrd
    return pd.read_excel(path, header=None, sheet_name=0, engine=engine)


def locate_code_row(raw: pd.DataFrame, regex: str, max_rows: int = 20) -> int:
    """Índice da linha onde >=5 células casam com `regex` (linha dos códigos de indicador)."""
    pat = re.compile(regex)
    for i in range(min(max_rows, len(raw))):
        if raw.iloc[i].fillna("").astype(str).str.strip().str.match(pat).sum() >= 5:
            return i
    raise ValueError(f"Linha de códigos não encontrada (regex={regex})")
