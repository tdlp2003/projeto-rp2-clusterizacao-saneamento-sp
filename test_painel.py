"""Testes de sanidade do painel processado. Rodar: pytest"""
import pandas as pd
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "data" / "processed"

def painel():
    return pd.read_csv(P / "painel_sp_2019_2024.csv")

def test_645_municipios_sem_duplicata():
    p = painel()
    assert len(p) == 645
    assert p["cod_ibge7"].is_unique

def test_chave_snis_e_ibge_sem_digito():
    p = painel()
    assert (p["cod_ibge7"] // 10 == p["cod_mun6"]).all()

def test_cobertura_minima_2019_ae():
    assert painel()["ae19_IN055"].notna().sum() == 628

def test_percentuais_entre_0_e_100():
    p = painel()
    for c in ["ae19_IN055", "ae19_IN056", "s24_IAG0001", "s24_IES0001", "s24_IRS0001"]:
        s = p[c].dropna()
        assert s.between(0, 100.01).all(), c
