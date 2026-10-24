# Comparação entre números de clusters (K-means)

- Dados: matriz A4, 597 municípios × 2 anos = 1194 instâncias; pré-processamento `completos_ambos|winsor_log|robust|conjunto`; tratamentos: truncar / retirar.
- k comparados: [2, 3]. Bootstrap: B = 200 reamostragens de municípios, seed = 42.

## Resumo

|   k |   silhueta média |   % silhueta < 0 |   menor cluster (inst.) |   estabilidade: ARI médio |   ARI p5 |   % reamostragens com ARI ≥ 0,9 |
|----:|-----------------:|-----------------:|------------------------:|--------------------------:|---------:|--------------------------------:|
|   2 |           0.4762 |              0.5 |                     230 |                     0.989 |    0.977 |                           100   |
|   3 |           0.3668 |              2.4 |                     216 |                     0.944 |    0.874 |                            88.5 |

## Como os clusters de k = 2 se distribuem em k = 3 (instâncias)

|   cluster (k=2) |   1 |   2 |   3 |
|----------------:|----:|----:|----:|
|               1 | 617 | 347 |   0 |
|               2 |   4 |  10 | 216 |

ARI entre as duas partições: 0.421

## k = 2 é um corte numa única variável?

Melhor regra 'indicador ≥ limiar' para reproduzir a partição com k = 2:

| indicador                     |   melhor limiar (%) |   ARI com a partição |   % concordância |
|:------------------------------|--------------------:|---------------------:|-----------------:|
| Tratamento do esgoto coletado |               95.73 |                0.965 |             99.2 |
| Perdas na distribuição        |               40.45 |                0.197 |             79.7 |
| Água (atend. total)           |               97.6  |                0.069 |             67.3 |
| Esgoto (atend. total)         |               95.51 |                0.039 |             67   |

## k = 2

Perfis: mediana [Q1–Q3] em unidades originais.

|   cluster | Água (atend. total) (%)   | Perdas na distribuição (%)   | Esgoto (atend. total) (%)   | Tratamento do esgoto coletado (%)   |   n 2019 |   n 2024 |   silhueta média |   % silhueta < 0 |
|----------:|:--------------------------|:-----------------------------|:----------------------------|:------------------------------------|---------:|---------:|-----------------:|-----------------:|
|         1 | 92.2 [82.4–98.3]          | 21.8 [14.6–30.5]             | 87.5 [73.1–95.5]            | 100.0 [100.0–100.0]                 |      472 |      492 |            0.499 |              0   |
|         2 | 96.9 [89.0–99.9]          | 33.2 [21.4–44.4]             | 90.8 [78.6–97.4]            | 54.9 [0.1–80.0]                     |      125 |      105 |            0.38  |              2.6 |

% de cada faixa de porte em cada cluster (municípios-ano):

| porte           |    1 |    2 |
|:----------------|-----:|-----:|
| até 20 mil      | 90   | 10   |
| 20–50 mil       | 75.9 | 24.1 |
| 50–100 mil      | 66.1 | 33.9 |
| 100–250 mil     | 62.5 | 37.5 |
| mais de 250 mil | 47.1 | 52.9 |

Transição 2019 → 2024 (nº de municípios):

|   2019 |   1 |   2 |
|-------:|----:|----:|
|      1 | 448 |  24 |
|      2 |  44 |  81 |

## k = 3

Perfis: mediana [Q1–Q3] em unidades originais.

|   cluster | Água (atend. total) (%)   | Perdas na distribuição (%)   | Esgoto (atend. total) (%)   | Tratamento do esgoto coletado (%)   |   n 2019 |   n 2024 |   silhueta média |   % silhueta < 0 |
|----------:|:--------------------------|:-----------------------------|:----------------------------|:------------------------------------|---------:|---------:|-----------------:|-----------------:|
|         1 | 86.4 [75.1–91.6]          | 21.7 [14.7–29.5]             | 79.8 [61.8–87.5]            | 100.0 [100.0–100.0]                 |      306 |      315 |            0.401 |              0   |
|         2 | 99.7 [97.5–100.0]         | 22.5 [14.5–34.3]             | 97.9 [94.9–99.7]            | 100.0 [100.0–100.0]                 |      176 |      181 |            0.31  |              5.6 |
|         3 | 96.8 [89.0–99.7]          | 33.8 [21.8–44.7]             | 90.0 [78.7–97.1]            | 51.4 [0.0–75.6]                     |      115 |      101 |            0.364 |              4.2 |

% de cada faixa de porte em cada cluster (municípios-ano):

| porte           |    1 |    2 |    3 |
|:----------------|-----:|-----:|-----:|
| até 20 mil      | 66.5 | 24.2 |  9.3 |
| 20–50 mil       | 41.7 | 36.1 | 22.2 |
| 50–100 mil      | 32.1 | 36.6 | 31.2 |
| 100–250 mil     | 19.3 | 44.3 | 36.4 |
| mais de 250 mil |  8.8 | 39.7 | 51.5 |

Transição 2019 → 2024 (nº de municípios):

|   2019 |   1 |   2 |   3 |
|-------:|----:|----:|----:|
|      1 | 243 |  50 |  13 |
|      2 |  54 | 110 |  12 |
|      3 |  18 |  21 |  76 |
