"""Testes do src/clustering.py (rode na raiz com: pytest)."""
import numpy as np
import pandas as pd
from sklearn.datasets import make_blobs
from sklearn.metrics import silhouette_score

from src.clustering import curva_silhueta, escolher_k, renumerar_por_tamanho


def _silhueta_manual(X, labels):
    """s(i) = (b - a) / max(a, b), média sobre todas as instâncias (definição do método)."""
    D = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
    s = []
    for i in range(len(X)):
        mesmo = (labels == labels[i]) & (np.arange(len(X)) != i)
        a = D[i, mesmo].mean()
        b = min(D[i, labels == c].mean() for c in set(labels) if c != labels[i])
        s.append((b - a) / max(a, b))
    return float(np.mean(s))


def test_silhueta_e_a_media_sobre_todas_as_instancias():
    X, y = make_blobs(n_samples=60, centers=3, random_state=0)
    assert np.isclose(silhouette_score(X, y), _silhueta_manual(X, y))


def test_metodo_da_silhueta_recupera_3_grupos():
    X, _ = make_blobs(n_samples=300, centers=3, cluster_std=0.6, random_state=1)
    curva = curva_silhueta(pd.DataFrame(X), range(2, 7), n_init=10)
    assert escolher_k(curva) == 3


def test_escolher_k_pega_maximo_e_menor_k_no_empate():
    curva = pd.DataFrame({"k": [2, 3, 4, 5], "silhueta_media": [0.30, 0.45, 0.45, 0.20]})
    assert escolher_k(curva) == 3


def test_renumerar_por_tamanho():
    lab = np.array([7, 7, 3, 3, 3, 9])
    assert renumerar_por_tamanho(lab).tolist() == [2, 2, 1, 1, 1, 3]
