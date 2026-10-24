"""Testes do src/cenarios.py (rode na raiz com: pytest)."""
import numpy as np
import pandas as pd
import pytest

from src.cenarios import COL_PERDAS_19, COL_TRAT_24, aplicar_cenario, pct_mudam
from src.config import MATRIZES, PAINEL


@pytest.fixture(scope="module")
def painel():
    return pd.read_csv(PAINEL, encoding="utf-8-sig")


def _vinhedo(p):
    return p.loc[p["municipio"] == "Vinhedo", COL_TRAT_24].item()


def test_base_nao_muda_nada(painel):
    p, feats = aplicar_cenario(painel, "manter", "manter")
    pd.testing.assert_frame_equal(p, painel)
    assert feats == list(MATRIZES["A4"])


def test_vinhedo_truncar_e_retirar(painel):
    assert _vinhedo(aplicar_cenario(painel, "truncar", "manter")[0]) == 100
    assert np.isnan(_vinhedo(aplicar_cenario(painel, "retirar", "manter")[0]))
    assert _vinhedo(painel) == pytest.approx(129.42)        # entrada intacta


def test_perdas_zero_retirar_e_sem_perdas(painel):
    p, _ = aplicar_cenario(painel, "manter", "retirar")
    assert (painel[COL_PERDAS_19] == 0).sum() == 11 and (p[COL_PERDAS_19] == 0).sum() == 0
    assert p[COL_PERDAS_19].isna().sum() == painel[COL_PERDAS_19].isna().sum() + 11
    _, feats = aplicar_cenario(painel, "manter", "sem_perdas")
    assert feats == list(MATRIZES["A3"]) and "perdas" not in feats


def test_pct_mudam_ignora_numeracao_dos_rotulos():
    a = np.array([0, 0, 1, 1, 2, 2])
    assert pct_mudam(a, np.array([5, 5, 7, 7, 9, 9])) == 0           # mesma partição, outros nomes
    assert pct_mudam(a, np.array([5, 5, 7, 7, 9, 7])) == pytest.approx(100 / 6)
