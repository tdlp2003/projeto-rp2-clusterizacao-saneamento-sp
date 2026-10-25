# Modelo de Mistura Gaussiana (GMM)

- Dados: matriz A4, 597 municípios × 2 anos = 1194 instâncias; pré-processamento `completos_ambos|winsor_log|robust|conjunto`; tratamentos truncar / retirar.
- `sklearn.mixture.GaussianMixture`, EM, n_init = 10, random_state = 42.

## 1. Tipo de covariância

- Tipos excluídos por componentes degenerados ou vazios: full, diag.
- Entre tied, spherical, 'tied' tem o menor BIC em 9 dos 9 valores de k.

**Covariância usada: `tied`.**

k de menor BIC em cada tipo (o BIC cai até o fim da grade, sem mínimo interno):

| covariancia   |   k |
|:--------------|----:|
| diag          |   9 |
| full          |  10 |
| spherical     |  10 |
| tied          |  10 |

Grade completa (resumo):

|   k |   diag |   full |   spherical |   tied |
|----:|-------:|-------:|------------:|-------:|
|   1 |  10931 |   9693 |       11254 |   9693 |
|   2 |  -1156 |  -2341 |       10058 |   7984 |
|   3 |  -1957 |  -2914 |        9165 |   7115 |
|   4 |  -2358 |  -3893 |        8773 |   7110 |
|   5 |  -3824 |  -4376 |        8273 |   7140 |
|   6 |  -4003 |  -4678 |        7928 |   6497 |
|   7 |  -4227 |  -4763 |        7717 |   6491 |
|   8 |  -4545 |  -5060 |        7665 |   5990 |
|   9 |  -4770 |  -5443 |        7523 |   5976 |
|  10 |  -4645 |  -5738 |        7491 |   5599 |

## 2. Candidatos e regra (mesma do k-means e do Ward)

|   k |   silhueta_media |      sse |   menor_cluster |
|----:|-----------------:|---------:|----------------:|
|   2 |           0.4795 | 1810.91  |             227 |
|   3 |           0.3399 | 1738.68  |              93 |
|   4 |           0.3314 | 1251.9   |              92 |
|   5 |           0.3282 | 1160.42  |              21 |
|   6 |           0.2271 | 1194.63  |              60 |
|   7 |           0.2351 | 1096.2   |              18 |
|   8 |           0.2327 |  991.195 |              37 |
|   9 |           0.2022 | 1072.96  |              17 |
|  10 |           0.1977 | 1051.64  |              19 |

- Silhueta: **k = 2**; Cotovelo do SSE: **k = 4**.

|   k | indicado_por   | papel      |   silhueta |   estabilidade |   menor_cluster |   univariado | variavel_univariada   | admissivel   | ok_multivariado   |
|----:|:---------------|:-----------|-----------:|---------------:|----------------:|-------------:|:----------------------|:-------------|:------------------|
|   2 | silhueta       | adotado    |      0.48  |          0.985 |           0.19  |        0.984 | tratamento            | True         | False             |
|   4 | cotovelo       | descartado |      0.331 |          0.844 |           0.077 |        0.462 | tratamento            | False        | True              |

- Nenhum candidato é multivariado; k = 2 é o maior admissível.
- k = 2: não passa em: multivariado.
- k = 4: não passa em: estabilidade.

**Pela regra aplicada ao GMM isoladamente: k = 2.**

> A solução do trabalho é a do k-means com k = 3 (decisão do grupo); o GMM é usado como verificação com o mesmo k. Ver `docs/decisoes.md`.

## 3. Comparação dos três algoritmos (k = 3)

| par                  |   ARI |
|:---------------------|------:|
| GMM × k-means (k=3)  | 0.39  |
| GMM × Ward (k=3)     | 0.362 |
| k-means × Ward (k=3) | 0.625 |

k-means × GMM (instâncias):

|   k-means (k=3) |   1 |   2 |   3 |
|----------------:|----:|----:|----:|
|               1 | 609 |   0 |  12 |
|               2 | 339 |   0 |  18 |
|               3 |   0 | 153 |  63 |

### Sensibilidade ao tipo de covariância (k = 3)

'separa por acesso?' = sim quando o ARI com o k-means passa de 0,7 (reproduz os três perfis).

| covariancia   | usada   | degenerado   |   BIC |   silhueta |   ARI × k-means |   ARI × Ward | separa por acesso?   |
|:--------------|:--------|:-------------|------:|-----------:|----------------:|-------------:|:---------------------|
| full          | False   | True         | -2914 |      0.258 |           0.537 |        0.508 | não                  |
| tied          | True    | False        |  7115 |      0.34  |           0.39  |        0.362 | não                  |
| diag          | False   | True         | -1957 |      0.319 |           0.772 |        0.594 | sim                  |
| spherical     | False   | False        |  9165 |      0.347 |           0.847 |        0.58  | sim                  |

Estabilidade por cluster (Jaccard médio, B = 100) e incerteza de pertença no GMM (% de instâncias com probabilidade máxima < 0.8); clusters do Ward e do GMM casados com os do k-means pela maior sobreposição:

|   cluster k-means |   Jaccard k-means |   Jaccard Ward | Jaccard GMM        | % incerta GMM      |
|------------------:|------------------:|---------------:|:-------------------|:-------------------|
|                 1 |             0.973 |          0.76  | 0.726              | 0.0                |
|                 2 |             0.947 |          0.683 | sem correspondente | sem correspondente |
|                 3 |             0.983 |          0.897 | 0.698              | 3.2                |

## 4. Perfis do GMM (k = 3): mediana [Q1–Q3]

|   cluster | Água (atend. total) (%)   | Perdas na distribuição (%)   | Esgoto (atend. total) (%)   | Tratamento do esgoto coletado (%)   |   n 2019 |   n 2024 |   silhueta média |   % silhueta < 0 |
|----------:|:--------------------------|:-----------------------------|:----------------------------|:------------------------------------|---------:|---------:|-----------------:|-----------------:|
|         1 | 92.2 [82.4–98.3]          | 22.0 [14.7–30.5]             | 87.5 [73.1–95.4]            | 100.0 [100.0–100.0]                 |      459 |      489 |            0.384 |              0.2 |
|         2 | 96.8 [89.9–100.0]         | 33.4 [19.9–45.6]             | 88.9 [78.6–96.2]            | 22.9 [0.0–54.9]                     |       83 |       70 |            0.2   |              1.3 |
|         3 | 97.1 [85.1–99.5]          | 30.9 [18.9–40.6]             | 94.1 [77.3–97.9]            | 89.2 [80.8–92.9]                    |       55 |       38 |            0.119 |             10.8 |