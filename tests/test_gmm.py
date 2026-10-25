"""Testes do src/gmm.py (rode na raiz com: pytest)."""
import numpy as np
import pandas as pd
from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score

from src.gmm import (ajustar_gmm, covariancias_completas, degenerado, escolher_covariancia,
                     estabilidade_gmm, rotulos)


def _X(n=200, centros=3, seed=0, std=0.5):
    X, y = make_blobs(n_samples=n, centers=centros, cluster_std=std, random_state=seed)
    idx = pd.MultiIndex.from_product([range(n // 2), (2019, 2024)], names=["cod_mun6", "ano"])
    return pd.DataFrame(X, index=idx, columns=["a", "b"]), y


def test_covariancias_completas_tem_formato_k_d_d_em_todos_os_tipos():
    X, _ = _X()
    for cov in ("full", "tied", "diag", "spherical"):
        assert covariancias_completas(ajustar_gmm(X, 3, cov, n_init=2)).shape == (3, 2, 2)


def test_gmm_recupera_grupos_separados():
    X, y = _X(std=0.3)
    assert adjusted_rand_score(y, rotulos(ajustar_gmm(X, 3, "full", n_init=3), X)) == 1.0


def test_degenerado_detecta_componente_colapsado_num_ponto():
    X, _ = _X(std=0.5)
    X.iloc[:60, 0] = 5.0                       # massa de pontos num único valor (como o teto de 100%)
    X.iloc[:60, 1] = 5.0
    assert degenerado(ajustar_gmm(X, 3, "full", n_init=3), X)
    assert not degenerado(ajustar_gmm(_X()[0], 3, "full", n_init=3), _X()[0])


def test_escolher_covariancia_exclui_degenerados_e_usa_menor_bic():
    grade = pd.DataFrame({
        "covariancia": ["full", "full", "tied", "tied", "spherical", "spherical"],
        "k": [2, 3, 2, 3, 2, 3], "bic": [-50, -60, 10, 8, 20, 18],
        "degenerado": [True, True, False, False, False, False], "grupos_nao_vazios": [2, 3, 2, 3, 2, 3]})
    cov, porque = escolher_covariancia(grade)
    assert cov == "tied" and "full" in porque[0]


def test_estabilidade_alta_em_grupos_separados():
    X, _ = _X(std=0.3)
    assert estabilidade_gmm(X, 3, "spherical", B=5, seed=1).mean() > 0.95
