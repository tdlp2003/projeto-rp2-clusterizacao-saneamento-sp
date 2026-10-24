# Resumo da clusterização (K-means; regra Silhueta + Cotovelo)

- Matriz **A4**: Água (atend. total), Perdas na distribuição, Esgoto (atend. total), Tratamento do esgoto coletado.
- Pré-processamento: `completos_ambos|winsor_log|robust|conjunto` (referência).
- Instâncias: **1194** (municípios-ano), 597 municípios.
- Tratamento de valores: valores > 100 → **truncar**; perdas = 0 → **retirar** (12 células; ver `docs/decisao_vinhedo_perdas.md`).
- K-means: n_init = 50, random_state = 42. Grade k = 2..10.
- Critérios (`config.CRITERIOS_K`): silhueta > 0.25, estabilidade ≥ 0.85 (B = 100), menor cluster ≥ 5% das instâncias, reprodução por uma única variável < 0.9.

## 1. Candidatos

|   k |   silhueta_media |      sse |   menor_cluster |
|----:|-----------------:|---------:|----------------:|
|   2 |           0.4762 | 1806.45  |             230 |
|   3 |           0.3668 | 1276.26  |             216 |
|   4 |           0.3309 | 1046.73  |             216 |
|   5 |           0.3254 |  914.764 |             185 |
|   6 |           0.3259 |  797.604 |              43 |
|   7 |           0.321  |  699.726 |              37 |
|   8 |           0.3115 |  631.621 |              33 |
|   9 |           0.3096 |  577.09  |              32 |
|  10 |           0.3025 |  541.249 |              28 |

- Método da Silhueta: **k = 2** (maior silhueta média = 0.4762).
- Método do Cotovelo: **k = 3** (curva SSE × k de k = 1 a 10).

## 2. Avaliação dos candidatos e regra de escolha

|   k | indicado_por   | papel      |   silhueta |   estabilidade |   menor_cluster |   univariado | variavel_univariada   | admissivel   | ok_multivariado   |
|----:|:---------------|:-----------|-----------:|---------------:|----------------:|-------------:|:----------------------|:-------------|:------------------|
|   2 | silhueta       | descartado |      0.476 |          0.989 |           0.193 |        0.965 | tratamento            | True         | False             |
|   3 | cotovelo       | adotado    |      0.367 |          0.947 |           0.181 |        0.385 | tratamento            | True         | True              |

- k = 3 é o maior candidato admissível e multivariado.
- k = 2: não passa em: multivariado.
- k = 3: passa em todos os critérios.
- k = 2 também é admissível, mas, por decisão do grupo, só a solução adotada (k = 3) é apresentada.

**Solução adotada: k = 3.**

## Solução adotada (k = 3)

Perfis: mediana [Q1–Q3] em unidades originais.

|   cluster | Água (atend. total) (%)   | Perdas na distribuição (%)   | Esgoto (atend. total) (%)   | Tratamento do esgoto coletado (%)   |   n 2019 |   n 2024 |   silhueta média |   % silhueta < 0 |
|----------:|:--------------------------|:-----------------------------|:----------------------------|:------------------------------------|---------:|---------:|-----------------:|-----------------:|
|         1 | 86.4 [75.1–91.6]          | 21.7 [14.7–29.5]             | 79.8 [61.8–87.5]            | 100.0 [100.0–100.0]                 |      306 |      315 |            0.401 |              0   |
|         2 | 99.7 [97.5–100.0]         | 22.5 [14.5–34.3]             | 97.9 [94.9–99.7]            | 100.0 [100.0–100.0]                 |      176 |      181 |            0.31  |              5.6 |
|         3 | 96.8 [89.0–99.7]          | 33.8 [21.8–44.7]             | 90.0 [78.7–97.1]            | 51.4 [0.0–75.6]                     |      115 |      101 |            0.364 |              4.2 |

% de cada faixa de porte em cada cluster (municípios-ano, 2019 e 2024):

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

> Clusters numerados por tamanho (1 = maior) dentro de cada solução. Silhuetas entre 0,26 e 0,50 indicam estrutura fraca (Kaufman e Rousseeuw, 1990): os perfis devem ser lidos como tendências, não como grupos nitidamente separados.