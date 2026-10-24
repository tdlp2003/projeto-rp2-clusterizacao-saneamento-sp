"""Testes do src/clustering.py (rode na raiz com: pytest)."""
import numpy as np
import pandas as pd
from sklearn.datasets import make_blobs
from sklearn.metrics import silhouette_score

from src.clustering import curva_silhueta, escolher_k, k_cotovelo, renumerar_por_tamanho


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


def test_cotovelo_em_curva_conhecida():
    # SSE cai muito até k = 4 e quase nada depois: cotovelo em 4
    curva = pd.DataFrame({"k": range(2, 9), "sse": [1000, 600, 200, 180, 165, 155, 150]})
    assert k_cotovelo(curva) == 4


def test_cotovelo_recupera_3_grupos():
    X, _ = make_blobs(n_samples=300, centers=3, cluster_std=0.6, random_state=1)
    curva = curva_silhueta(pd.DataFrame(X), range(2, 9), n_init=10)
    assert k_cotovelo(curva) == 3


def test_sse_e_soma_das_distancias_ao_quadrado():
    from src.clustering import ajustar_kmeans
    X, _ = make_blobs(n_samples=80, centers=3, random_state=2)
    km = ajustar_kmeans(pd.DataFrame(X), 3, n_init=5)
    sse_manual = sum(np.sum((X[km.labels_ == c] - km.cluster_centers_[c]) ** 2) for c in range(3))
    assert np.isclose(km.inertia_, sse_manual)


def test_curva_cotovelo_comeca_em_k1_com_soma_total_dos_quadrados():
    from src.clustering import ajustar_kmeans, curva_cotovelo
    X, _ = make_blobs(n_samples=60, centers=2, random_state=3)
    X = pd.DataFrame(X)
    cot = curva_cotovelo(X, curva_silhueta(X, range(2, 5), n_init=5))
    assert cot.k.tolist() == [1, 2, 3, 4]
    assert np.isclose(cot.sse.iloc[0], ajustar_kmeans(X, 1, n_init=1).inertia_)


# ------------------------------------------------------------------ regra de escolha (opção 3)
from src.clustering import escolher_solucoes, reproducao_univariada


def _av(k, sil=True, est=True, menor=True, multi=True):
    return {"k": k, "ok_silhueta": sil, "ok_estabilidade": est, "ok_menor_cluster": menor,
            "ok_multivariado": multi, "admissivel": sil and est and menor}


def test_decisao_do_grupo_so_a_solucao_adotada():
    from src.config import CRITERIOS_K
    assert CRITERIOS_K["apresentar_complementar"] is False


def test_regra_principal_e_o_maior_admissivel_multivariado():
    # caso do trabalho: k=2 admissível mas univariado; k=3 passa em tudo
    pri, comp, _ = escolher_solucoes([_av(2, multi=False), _av(3)], k_sil=2)
    assert (pri, comp) == (3, 2)


def test_regra_com_os_dois_multivariados_fica_o_maior_e_o_outro_complementa():
    assert escolher_solucoes([_av(2), _av(4)], k_sil=2)[:2] == (4, 2)


def test_regra_candidato_instavel_nao_entra():
    assert escolher_solucoes([_av(2), _av(3, est=False)], k_sil=2)[:2] == (2, None)


def test_regra_sem_admissivel_usa_silhueta():
    pri, comp, porque = escolher_solucoes([_av(2, sil=False), _av(3, est=False)], k_sil=2)
    assert (pri, comp) == (2, None) and porque[0].startswith("AVISO")


def test_reproducao_univariada_detecta_corte_numa_variavel():
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"a": rng.normal(size=200), "b": rng.normal(size=200)})
    lab = (X["a"] > 0).astype(int).to_numpy()            # partição = corte em "a"
    ari, var = reproducao_univariada(X, lab)
    assert var == "a" and ari > 0.9
