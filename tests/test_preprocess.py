"""Testes de sanidade do src/preprocess.py (rode na raiz com: pytest)."""
import numpy as np
import pandas as pd
import pytest

from src.config import PAINEL
from src.preprocess import Cfg, FEATURES, executar, grade, para_longo


@pytest.fixture(scope="module")
def L():
    return para_longo(pd.read_csv(PAINEL, encoding="utf-8-sig"))


def test_completos_ambos_607(L):
    # matriz A4: 607 municípios completos nos dois anos (auditoria, §7)
    X, info = executar(L, Cfg(inclusao="completos_ambos"))
    assert info["n_municipios"] == 607 and len(X) == 2 * 607


def test_zscore_conjunto_media0_dp1(L):
    X, _ = executar(L, Cfg(escala="zscore", escopo="conjunto"))
    assert np.allclose(X.mean(), 0, atol=1e-9) and np.allclose(X.std(ddof=0), 1)


def test_zscore_por_ano_media0_em_cada_ano(L):
    X, _ = executar(L, Cfg(escala="zscore", escopo="por_ano"))
    for ano in (2019, 2024):
        assert np.allclose(X.xs(ano, level="ano").mean(), 0, atol=1e-9)


def test_minmax_em_0_1(L):
    X, _ = executar(L, Cfg(escala="minmax"))
    assert X.min().min() >= -1e-12 and X.max().max() <= 1 + 1e-12


def test_nao_altera_entrada(L):
    antes = L.copy()
    executar(L, Cfg(inclusao="imp_knn", transformacao="winsor_log", escala="robust", escopo="por_ano"))
    pd.testing.assert_frame_equal(L, antes)


def test_grade_sem_nan(L):
    for c in grade():
        X, _ = executar(L, c)
        assert not X.isna().any().any(), c.nome
        assert list(X.columns) == list(FEATURES)


def test_log_preserva_ordem(L):
    Xa, _ = executar(L, Cfg(transformacao="nenhuma", escala="minmax"))
    Xb, _ = executar(L, Cfg(transformacao="log", escala="minmax"))
    for f in FEATURES:
        # ordem nunca se inverte (empates são permitidos: o log corta >100, ex. Vinhedo)
        ordenado = Xb[f].loc[Xa[f].sort_values(kind="stable").index].to_numpy()
        assert (np.diff(ordenado) >= -1e-12).all(), f
