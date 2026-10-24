"""Testes de sanidade do painel processado (rode na raiz com: pytest)."""
import pandas as pd
import pytest

from src.config import INDICADORES, PAINEL, PORTE_ROTULOS


@pytest.fixture(scope="module")
def p():
    return pd.read_csv(PAINEL, encoding="utf-8-sig")


def test_645_municipios_sem_duplicata(p):
    assert len(p) == 645
    assert p["cod_ibge7"].is_unique


def test_chave_snis_e_ibge_sem_digito(p):
    assert (p["cod_ibge7"] // 10 == p["cod_mun6"]).all()


def test_cobertura_minima_2019_ae(p):
    assert p["ae19_IN055"].notna().sum() == 628


def test_populacao_e_porte_completos(p):
    assert p["municipio"].notna().all() and (p["populacao"] > 0).all()
    assert set(p["porte"]) == set(PORTE_ROTULOS)
    assert p.loc[p["municipio"] == "São Paulo", "porte"].item() == "mais de 250 mil"


def test_percentuais_entre_0_e_100(p):
    cols = [c for ind in INDICADORES.values() if ind.unidade == "%"
            for c in (ind.col_2019, ind.col_2024)] + ["s24_IRS0001"]
    for c in cols:
        fora = p.loc[~p[c].dropna().between(0, 100.01).reindex(p.index, fill_value=True), "municipio"]
        if c == "s24_IES2004":
            # caso conhecido: Vinhedo = 129,42 (tratamento pendente, ver docs/decisoes.md)
            assert fora.tolist() == ["Vinhedo"], c
        else:
            assert fora.empty, (c, fora.tolist())
