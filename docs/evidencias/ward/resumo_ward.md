# Agrupamento hierárquico de Ward

- Dados: matriz A4, 597 municípios × 2 anos = 1194 instâncias; pré-processamento `completos_ambos|winsor_log|robust|conjunto`; tratamentos truncar / retirar.
- Ward com distância euclidiana (`scipy.cluster.hierarchy.linkage`, method='ward'); determinístico.
- Mesma regra e critérios do k-means (`config.CRITERIOS_K`), B = 100.

## 1. Candidatos (cortes da árvore)

|   k |   silhueta_media |      sse |   menor_cluster |
|----:|-----------------:|---------:|----------------:|
|   1 |         nan      | 2929.06  |            1194 |
|   2 |           0.461  | 1828.2   |             247 |
|   3 |           0.3185 | 1347.41  |             247 |
|   4 |           0.2725 | 1174.3   |             229 |
|   5 |           0.2726 | 1026.85  |             168 |
|   6 |           0.2693 |  898.505 |              41 |
|   7 |           0.263  |  804.876 |              41 |
|   8 |           0.2606 |  737.672 |              41 |
|   9 |           0.2673 |  670.476 |              41 |
|  10 |           0.2719 |  617.298 |              41 |

- Silhueta: **k = 2**; Cotovelo: **k = 3**.

## 2. Avaliação e regra

|   k | indicado_por   | papel      |   silhueta |   estabilidade |   menor_cluster |   univariado | variavel_univariada   | admissivel   | ok_multivariado   |
|----:|:---------------|:-----------|-----------:|---------------:|----------------:|-------------:|:----------------------|:-------------|:------------------|
|   2 | silhueta       | adotado    |      0.461 |          0.926 |           0.207 |        0.924 | tratamento            | True         | False             |
|   3 | cotovelo       | descartado |      0.319 |          0.621 |           0.207 |        0.366 | tratamento            | False        | True              |

- Nenhum candidato é multivariado; k = 2 é o maior admissível.
- k = 2: não passa em: multivariado.
- k = 3: não passa em: estabilidade.

**Pela regra aplicada ao Ward isoladamente: k = 2.**

> Decisão do grupo (2026-10-25): a solução do trabalho é a do k-means com k = 3; o Ward é usado como verificação com o mesmo k (seção 3), com a ressalva de que a divisão por acesso é menos estável no Ward. Ver `docs/decisoes.md`.

## 3. Comparação com o k-means

| comparação                                     |   ARI |
|:-----------------------------------------------|------:|
| Ward k = 2 × k-means k = 3 (soluções adotadas) | 0.405 |
| Ward k = 3 × k-means k = 3 (mesmo k)           | 0.625 |

Contingência (instâncias):

|   k-means (k=3) |   1 |   2 |
|----------------:|----:|----:|
|               1 | 607 |  14 |
|               2 | 340 |  17 |
|               3 |   0 | 216 |

### Estabilidade por cluster com k = 3 (Jaccard médio, Hennig 2007; B = 100)

Mediana [Q1–Q3] dos indicadores em %. Jaccard > 0,75 = estável; 0,6–0,75 = padrão com pertença incerta; < 0,5 = dissolvido.

| algoritmo   |   cluster |   jaccard | agua              | esgoto           | tratamento          |
|:------------|----------:|----------:|:------------------|:-----------------|:--------------------|
| k-means k=3 |         1 |     0.973 | 86.4 [75.1–91.6]  | 79.8 [61.8–87.5] | 100.0 [100.0–100.0] |
| k-means k=3 |         2 |     0.947 | 99.7 [97.5–100.0] | 97.9 [94.9–99.7] | 100.0 [100.0–100.0] |
| k-means k=3 |         3 |     0.983 | 96.8 [89.0–99.7]  | 90.0 [78.7–97.1] | 51.4 [0.0–75.6]     |
| Ward k=3    |         1 |     0.76  | 83.2 [71.9–89.1]  | 76.0 [57.7–85.1] | 100.0 [100.0–100.0] |
| Ward k=3    |         2 |     0.683 | 98.4 [95.5–100.0] | 96.0 [91.8–99.1] | 100.0 [100.0–100.0] |
| Ward k=3    |         3 |     0.897 | 96.8 [89.3–99.7]  | 90.8 [78.6–97.2] | 57.1 [4.1–84.9]     |

## 4. Perfis do Ward (k = 2): mediana [Q1–Q3]

|   cluster | Água (atend. total) (%)   | Perdas na distribuição (%)   | Esgoto (atend. total) (%)   | Tratamento do esgoto coletado (%)   |   n 2019 |   n 2024 |   silhueta média |   % silhueta < 0 |
|----------:|:--------------------------|:-----------------------------|:----------------------------|:------------------------------------|---------:|---------:|-----------------:|-----------------:|
|         1 | 92.1 [82.3–98.3]          | 21.7 [14.6–30.4]             | 87.5 [73.1–95.5]            | 100.0 [100.0–100.0]                 |      461 |      486 |            0.495 |              0.1 |
|         2 | 96.8 [89.3–99.7]          | 32.4 [21.1–43.4]             | 90.8 [78.6–97.2]            | 57.1 [4.1–84.9]                     |      136 |      111 |            0.332 |              8.5 |

% de cada faixa de porte em cada cluster:

| porte           |    1 |    2 |
|:----------------|-----:|-----:|
| até 20 mil      | 88.9 | 11.1 |
| 20–50 mil       | 75   | 25   |
| 50–100 mil      | 66.1 | 33.9 |
| 100–250 mil     | 58   | 42   |
| mais de 250 mil | 42.6 | 57.4 |

Transição 2019 → 2024:

|   2019 |   1 |   2 |
|-------:|----:|----:|
|      1 | 437 |  24 |
|      2 |  49 |  87 |
