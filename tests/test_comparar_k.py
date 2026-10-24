"""Testes do src/comparar_k.py (rode na raiz com: pytest)."""
import numpy as np
import pandas as pd
from sklearn.datasets import make_blobs

from src.comparar_k import cores_alinhadas, estabilidade_bootstrap


def _X(n=150, centros=3, seed=0):
    X, _ = make_blobs(n_samples=n, centers=centros, cluster_std=0.5, random_state=seed)
    idx = pd.MultiIndex.from_product([range(n // 2), (2019, 2024)], names=["cod_mun6", "ano"])
    return pd.DataFrame(X[: len(idx)], index=idx)


def test_bootstrap_estavel_em_grupos_bem_separados():
    aris = estabilidade_bootstrap(_X(), 3, B=10, seed=1, n_init=5)
    assert len(aris) == 10 and aris.mean() > 0.95


def test_cores_alinhadas_mantem_cor_do_grupo_que_continua():
    k2 = pd.Series([1, 1, 1, 1, 2, 2])
    k3 = pd.Series([1, 1, 2, 2, 3, 3])          # cluster 1 de k=2 se divide; o 2 vira o 3
    c = cores_alinhadas({2: k2, 3: k3})
    assert c[3][3] == c[2][2] and c[3][1] == c[2][1] and c[3][2] not in c[2].values()
