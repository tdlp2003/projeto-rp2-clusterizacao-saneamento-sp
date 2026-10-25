"""Testes do src/ward.py (rode na raiz com: pytest)."""
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.datasets import make_blobs
from sklearn.metrics import adjusted_rand_score

from src.ward import (arvore_ward, atribuir_ward, cortar, curva_ward, estabilidade_ward,
                      jaccard_por_cluster, sse)


def _X(n=120, centros=3, seed=0, std=0.5):
    X, y = make_blobs(n_samples=n, centers=centros, cluster_std=std, random_state=seed)
    idx = pd.MultiIndex.from_product([range(n // 2), (2019, 2024)], names=["cod_mun6", "ano"])
    return pd.DataFrame(X, index=idx), y


def test_ward_igual_ao_scikit_learn():
    X, _ = _X()
    nosso = cortar(arvore_ward(X), 3)
    sk = AgglomerativeClustering(n_clusters=3, linkage="ward").fit_predict(X.to_numpy())
    assert adjusted_rand_score(nosso, sk) == 1.0


def test_cortes_aninhados_e_renumerados_por_tamanho():
    X, _ = _X(seed=4)
    Z = arvore_ward(X)
    k2, k3 = cortar(Z, 2), cortar(Z, 3)
    assert set(k3) == {1, 2, 3} and np.bincount(k3)[1:].tolist() == sorted(np.bincount(k3)[1:], reverse=True)
    # hierarquia: cada grupo de k = 3 está inteiro dentro de um grupo de k = 2
    assert all(len(set(k2[k3 == c])) == 1 for c in (1, 2, 3))


def test_sse_k1_e_curva_decrescente():
    X, _ = _X()
    c = curva_ward(X, arvore_ward(X), range(2, 6))
    assert np.isclose(c.sse.iloc[0], ((X - X.mean()) ** 2).to_numpy().sum())
    assert (np.diff(c.sse) < 0).all()
    assert np.isclose(sse(X, np.ones(len(X))), c.sse.iloc[0])


def test_estabilidade_alta_em_grupos_separados():
    X, _ = _X(std=0.3)
    assert estabilidade_ward(X, 3, B=10, seed=1).mean() > 0.95


def test_jaccard_por_cluster_alto_em_grupos_separados():
    X, _ = _X(std=0.3)
    base = cortar(arvore_ward(X), 3)
    j = jaccard_por_cluster(X, base, lambda Xb: atribuir_ward(Xb, 3, X), B=10, seed=2)
    assert len(j) == 3 and (j > 0.9).all()
