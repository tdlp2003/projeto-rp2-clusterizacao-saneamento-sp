"""
Passo 1 — Constrói as bases MUNICIPAIS de SP (2019 SNIS e 2024 SINISA) sem nenhuma análise.
Saídas em data/processed/:
  snis_ae_2019_sp.csv        1 linha/município (628 mun.), todas as colunas IN...
  snis_rs_2019_sp.csv        1 linha/município, todas as colunas IN...
  sinisa_2024_sp.csv         1 linha/município, IAG/IES/IRS... (join externo das 3 dimensões)
  dicionario_variaveis.csv   código -> nome -> unidade -> fonte
  cobertura_indicadores.csv  N preenchido por indicador (para decidir a matriz)
Rodar da raiz do projeto:  python -m src.build_panel
"""
import re
import pandas as pd, numpy as np
from .config import AE2019, RS2019, SINISA2024, UF, PROC
from .io_utils import find_one, read_raw, locate_code_row

def _s(x):
    return "" if pd.isna(x) else str(x).strip()

def _num(df, cols):
    for c in cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def load_snis_ae_2019():
    partes, dic = [], {}
    for fonte, pat in AE2019.items():
        raw = read_raw(find_one(pat))
        r = locate_code_row(raw, r"^IN\d{3}$")           # linha dos códigos
        nomes, unid = raw.iloc[r - 2], raw.iloc[r - 1]   # nome / unidade ficam acima
        codes = raw.iloc[r].fillna('').astype(str).str.strip().tolist()
        head = raw.iloc[r - 2].fillna('').astype(str).str.strip().tolist()
        cols = [c if c.startswith("IN") else h for c, h in zip(codes, head)]
        cols[9] = "Tipo de serviço"
        for c, n, u in zip(codes, nomes, unid):
            if str(c).startswith("IN"):
                dic[c] = (_s(n), _s(u), "SNIS-AE 2019")
        d = raw.iloc[r + 1:].copy(); d.columns = cols
        d = d[d["UF"] == UF].copy(); d["fonte_prestador"] = fonte
        partes.append(d)
    ae = pd.concat(partes, ignore_index=True)
    ae["cod_mun6"] = ae["Código do município"].astype(int)
    ae["Tipo de serviço"] = ae["Tipo de serviço"].astype(str).str.strip()
    in_cols = [c for c in ae.columns if re.match(r"^IN\d{3}$", str(c))]
    ae = _num(ae, in_cols)
    # 3 municípios têm um prestador só de água e outro só de esgoto: coalescer por município
    meta = ["Município", "Sigla", "Tipo de serviço", "fonte_prestador"]
    ae = (ae.groupby("cod_mun6", as_index=False)
            .agg({**{c: "first" for c in in_cols},
                  "Município": "first",
                  "Sigla": lambda s: " | ".join(map(str, s)),
                  "Tipo de serviço": lambda s: " | ".join(sorted(set(s))),
                  "fonte_prestador": lambda s: " | ".join(sorted(set(s)))}))
    ae["cod_ibge7_prefixo"] = ae["cod_mun6"]
    return ae, dic

def load_snis_rs_2019():
    raw = read_raw(find_one(RS2019))
    r = locate_code_row(raw, r"^IN\d{3}$")
    codes = raw.iloc[r].fillna('').astype(str).str.strip().tolist()
    nomes = raw.iloc[r - 3].fillna('').astype(str).tolist(); unid = raw.iloc[r - 2].fillna('').astype(str).tolist()  # RS2019: nome em r-3, unidade em r-2
    dic = {c: (_s(n), _s(u), "SNIS-RS 2019") for c, n, u in zip(codes, nomes, unid) if c.startswith("IN")}
    cols = [c if c.startswith("IN") else f"meta_{i}" for i, c in enumerate(codes)]
    cols[0], cols[1], cols[2] = "cod_mun6", "Município", "UF"
    d = raw.iloc[r + 1:].copy(); d.columns = cols
    d = d[d["UF"] == UF].copy(); d["cod_mun6"] = d["cod_mun6"].astype(int)
    in_cols = [c for c in d.columns if c.startswith("IN")]
    d = _num(d, in_cols)
    d = d.groupby("cod_mun6", as_index=False).first()      # segurança contra duplicatas
    return d[["cod_mun6", "Município"] + in_cols], dic

def _sinisa(pat, code_regex, prefix):
    """SINISA 2024: em água/esgoto a linha de códigos é a própria linha 'cod_IBGE';
    em resíduos os códigos IRS/IFR ficam 2 linhas acima da linha 'Cod_IBGE'."""
    raw = read_raw(find_one(pat))
    r = locate_code_row(raw, code_regex)                       # linha com os códigos de indicador
    id_row = next(i for i in range(max(r - 1, 0), r + 4)
                  if raw.iloc[i].fillna("").astype(str).str.lower().str.strip().eq("cod_ibge").any())
    codes = raw.iloc[id_row].fillna("").astype(str).str.strip().tolist()
    ind = raw.iloc[r].fillna("").astype(str).str.strip().tolist()
    codes = [i if re.match(code_regex, i) else c for c, i in zip(codes, ind)]      # sobrepõe códigos de indicador
    nomes = raw.iloc[r + 1 if id_row != r else r - 2].fillna("").astype(str).tolist()
    unid = raw.iloc[r - 1].fillna("").astype(str).tolist()
    dic = {c: (_s(n), _s(u), f"SINISA 2024 ({prefix})") for c, n, u in zip(codes, nomes, unid)
           if re.match(code_regex, c)}
    d = raw.iloc[id_row + 1:].copy(); d.columns = codes
    d = d[d["UF"] == UF].copy()
    idcol = next(c for c in codes if c.lower() == "cod_ibge")     # 'cod_IBGE' (água/esgoto) ou 'Cod_IBGE' (resíduos)
    d["cod_ibge7"] = pd.to_numeric(d[idcol], errors="coerce")
    d = d[d["cod_ibge7"].notna()].copy(); d["cod_ibge7"] = d["cod_ibge7"].astype(int)
    keep = ["cod_ibge7"] + [c for c in codes if re.match(code_regex, c)]
    d = _num(d[keep].copy(), keep[1:])
    d = d.groupby("cod_ibge7", as_index=False).first()
    return d, dic

def load_sinisa_2024():
    ag, d1 = _sinisa(SINISA2024["agua"],   r"^IAG\d{4}$", "água")
    es, d2 = _sinisa(SINISA2024["esgoto"], r"^IES\d{4}$", "esgoto")
    rs, d3 = _sinisa(SINISA2024["res"],    r"^(IRS|IFR)\d{4}$", "resíduos")
    # marcar se o município respondeu ao módulo de RS (col. 0 do arquivo de resíduos)
    raw = read_raw(find_one(SINISA2024["res"]))
    r = locate_code_row(raw, r"^IRS\d{4}$")
    resp = raw.iloc[r + 3:, [0, 1, 3]].copy(); resp.columns = ["respondeu_RS_2024", "cod_ibge7", "UF"]
    resp = resp[resp.UF == UF]; resp["cod_ibge7"] = pd.to_numeric(resp["cod_ibge7"], errors="coerce"); resp = resp[resp.cod_ibge7.notna()]; resp["cod_ibge7"] = resp["cod_ibge7"].astype(int)
    rs = rs.merge(resp[["cod_ibge7", "respondeu_RS_2024"]].drop_duplicates("cod_ibge7"), on="cod_ibge7", how="left")
    p = ag.merge(es, on="cod_ibge7", how="outer").merge(rs, on="cod_ibge7", how="outer")
    return p, {**d1, **d2, **d3}

def main():
    PROC.mkdir(parents=True, exist_ok=True)
    ae19, d_ae = load_snis_ae_2019()
    rs19, d_rs = load_snis_rs_2019()
    s24, d_s = load_sinisa_2024()
    ae19.to_csv(PROC / "snis_ae_2019_sp.csv", index=False, encoding="utf-8-sig")
    rs19.to_csv(PROC / "snis_rs_2019_sp.csv", index=False, encoding="utf-8-sig")
    s24.to_csv(PROC / "sinisa_2024_sp.csv", index=False, encoding="utf-8-sig")
    dic = pd.DataFrame([(k, *v) for k, v in {**d_ae, **d_rs, **d_s}.items()],
                       columns=["codigo", "nome", "unidade", "fonte"]).drop_duplicates(["codigo", "fonte"])
    dic.to_csv(PROC / "dicionario_variaveis.csv", index=False, encoding="utf-8-sig")
    cov = pd.concat([
        ae19.drop(columns=["cod_mun6","Município","Sigla","Tipo de serviço","fonte_prestador","cod_ibge7_prefixo"]).notna().sum().rename("N").to_frame().assign(base="SNIS-AE 2019"),
        rs19.drop(columns=["cod_mun6","Município"]).notna().sum().rename("N").to_frame().assign(base="SNIS-RS 2019"),
        s24.drop(columns=["cod_ibge7","respondeu_RS_2024"]).notna().sum().rename("N").to_frame().assign(base="SINISA 2024"),
    ]).reset_index().rename(columns={"index": "codigo"})
    cov.to_csv(PROC / "cobertura_indicadores.csv", index=False, encoding="utf-8-sig")
    # painel largo 2019 x 2024 (prefixos evitam colisão: IN015 existe em AE e em RS com significados diferentes!)
    s24["cod_mun6"] = s24["cod_ibge7"] // 10          # SNIS 6 dígitos = IBGE 7 dígitos sem o dígito verificador
    ae = ae19.drop(columns=["cod_ibge7_prefixo", "Município"]).add_prefix("ae19_").rename(columns={"ae19_cod_mun6": "cod_mun6"})
    rs = rs19.drop(columns=["Município"]).add_prefix("rs19_").rename(columns={"rs19_cod_mun6": "cod_mun6"})
    sn = s24.drop(columns=["respondeu_RS_2024"]).add_prefix("s24_").rename(columns={"s24_cod_mun6": "cod_mun6", "s24_cod_ibge7": "cod_ibge7"})
    painel = sn.merge(ae, on="cod_mun6", how="left").merge(rs, on="cod_mun6", how="left")
    painel["respondeu_RS_2024"] = s24["respondeu_RS_2024"].values
    painel.to_csv(PROC / "painel_sp_2019_2024.csv", index=False, encoding="utf-8-sig")
    print("AE2019:", len(ae19), "| RS2019:", len(rs19), "| SINISA2024:", len(s24))

if __name__ == "__main__":
    main()
