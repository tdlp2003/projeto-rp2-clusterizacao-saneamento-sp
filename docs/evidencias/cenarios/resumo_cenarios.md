# Cenários de tratamento: Vinhedo (tratamento > 100%) e perdas zeradas em 2019

Base de comparação: **Vinhedo=manter | perdas0=manter**. Método: K-means, k pela maior silhueta média (k = 2..10), n_init = 20, seed = 42.

- **ARI** compara as partições nas instâncias em comum (1 = idênticas; perto de 0 = sem relação).
- **% mudam de cluster**: municípios-ano em grupo diferente da base, com o mesmo k e os rótulos casados da melhor forma.
- Em `sem_perdas` a matriz é outra (A3), então mudanças maiores são esperadas: o cenário mostra quanto a variável perdas pesa nos grupos.

Decisão atualmente registrada em `config.TRATAMENTOS`: valores > 100 → **truncar**; perdas = 0 → **retirar**.

## Perfil dos casos

| municipio                | problema           |   populacao | porte      | prestador_2019   |   ae19_IN049 |   ae19_IN051 (perdas por ligação) |   s24_IAG2013 |   ae19_IN016 |   s24_IES2004 | na_amostra_A4   |
|:-------------------------|:-------------------|------------:|:-----------|:-----------------|-------------:|----------------------------------:|--------------:|-------------:|--------------:|:----------------|
| Bady Bassitt             | perdas = 0% (2019) |       28909 | 20–50 mil  | LPU              |         0    |                              0    |        nan    |       100    |        nan    | não             |
| Campos Novos Paulista    | perdas = 0% (2019) |        4991 | até 20 mil | LPU              |         0    |                              0    |         12.32 |        31.98 |        100    | sim             |
| Conchal                  | perdas = 0% (2019) |       29034 | 20–50 mil  | LPU              |         0    |                              0    |          9.12 |        91.82 |        100    | sim             |
| Lavínia                  | perdas = 0% (2019) |        9909 | até 20 mil | LPU              |         0    |                              0    |         45.42 |       100    |         97.47 | sim             |
| Luís Antônio             | perdas = 0% (2019) |       12531 | até 20 mil | LPU              |         0    |                              0    |         35.3  |       100    |        100    | sim             |
| Novais                   | perdas = 0% (2019) |        4469 | até 20 mil | LPU              |         0    |                              0    |         38.86 |        69.23 |          0    | sim             |
| Rincão                   | perdas = 0% (2019) |        9145 | até 20 mil | LPU              |         0    |                              0    |          6.21 |         0    |          0    | sim             |
| Santa Cruz das Palmeiras | perdas = 0% (2019) |       29525 | 20–50 mil  | LPU              |         0    |                              0    |         47.44 |         0    |         22.08 | sim             |
| Severínia                | perdas = 0% (2019) |       14724 | até 20 mil | LPU              |         0    |                              0    |         10.72 |        97.73 |        100    | sim             |
| Taiúva                   | perdas = 0% (2019) |        6733 | até 20 mil | LPU              |         0    |                              0    |         25.24 |       100    |        100    | sim             |
| Taquaral                 | perdas = 0% (2019) |        2652 | até 20 mil | LPU              |         0    |                              0    |          5.15 |       100    |        100    | sim             |
| Vinhedo                  | tratamento > 100%  |       79235 | 50–100 mil | LPU              |        33.63 |                            292.74 |         34.23 |        99.71 |        129.42 | sim             |

## Os zeros de perdas formam um cluster artificial? (log ou winsor_log + z-score)

| config                                     |   perdas padronizada dos zeros (z) |   mediana de perdas padronizada |   k com zeros |   k sem zeros | cluster dos zeros   |   tamanho desse cluster |   % do cluster que são zeros |
|:-------------------------------------------|-----------------------------------:|--------------------------------:|--------------:|--------------:|:--------------------|------------------------:|-----------------------------:|
| completos_ambos|log|zscore|conjunto        |                              -4.6  |                            0.13 |             4 |             3 | 4 (todos os 10)     |                      52 |                         19.2 |
| completos_ambos|winsor_log|zscore|conjunto |                              -4.43 |                            0.13 |             4 |             3 | 4 (todos os 10)     |                      54 |                         18.5 |

|   cluster | config                                     |   demais |   perdas = 0 |
|----------:|:-------------------------------------------|---------:|-------------:|
|         1 | completos_ambos|log|zscore|conjunto        |      605 |            0 |
|         2 | completos_ambos|log|zscore|conjunto        |      367 |            0 |
|         3 | completos_ambos|log|zscore|conjunto        |      190 |            0 |
|         4 | completos_ambos|log|zscore|conjunto        |       42 |           10 |
|         1 | completos_ambos|winsor_log|zscore|conjunto |      605 |            0 |
|         2 | completos_ambos|winsor_log|zscore|conjunto |      365 |            0 |
|         3 | completos_ambos|winsor_log|zscore|conjunto |      190 |            0 |
|         4 | completos_ambos|winsor_log|zscore|conjunto |       44 |           10 |

## Configuração de referência (`completos_ambos|winsor_log|robust|conjunto`)

| cenario                              |   n_municipios |   k |   silhueta |   ARI_vs_base_mesmo_k |   %_mudam_de_cluster |   ARI_vs_base_k_proprio |
|:-------------------------------------|---------------:|----:|-----------:|----------------------:|---------------------:|------------------------:|
| Vinhedo=manter | perdas0=manter      |            607 |   2 |      0.469 |                 1     |                0     |                   1     |
| Vinhedo=manter | perdas0=retirar     |            597 |   2 |      0.476 |                 1     |                0     |                   1     |
| Vinhedo=manter | perdas0=sem_perdas  |            607 |   2 |      0.567 |                 0.951 |                1.071 |                   0.951 |
| Vinhedo=truncar | perdas0=manter     |            607 |   2 |      0.469 |                 1     |                0     |                   1     |
| Vinhedo=truncar | perdas0=retirar    |            597 |   2 |      0.476 |                 1     |                0     |                   1     |
| Vinhedo=truncar | perdas0=sem_perdas |            607 |   2 |      0.567 |                 0.951 |                1.071 |                   0.951 |
| Vinhedo=retirar | perdas0=manter     |            606 |   2 |      0.469 |                 1     |                0     |                   1     |
| Vinhedo=retirar | perdas0=retirar    |            596 |   2 |      0.476 |                 1     |                0     |                   1     |
| Vinhedo=retirar | perdas0=sem_perdas |            606 |   2 |      0.567 |                 0.951 |                1.073 |                   0.951 |

## Resumo nas 12 configurações de pré-processamento

| cenario                              |   n_municipios |   ARI_medio |   ARI_min |   pct_mudam_medio |   pct_mudam_max | mesmo_k_da_base   |
|:-------------------------------------|---------------:|------------:|----------:|------------------:|----------------:|:------------------|
| Vinhedo=manter | perdas0=manter      |            607 |       1     |     1     |             0     |           0     | 12 de 12          |
| Vinhedo=manter | perdas0=retirar     |            597 |       0.942 |     0.685 |             2.973 |          17.002 | 10 de 12          |
| Vinhedo=manter | perdas0=sem_perdas  |            607 |       0.88  |     0.458 |             7.084 |          37.397 | 10 de 12          |
| Vinhedo=truncar | perdas0=manter     |            607 |       0.999 |     0.987 |             0.041 |           0.494 | 11 de 12          |
| Vinhedo=truncar | perdas0=retirar    |            597 |       0.943 |     0.685 |             2.966 |          17.002 | 9 de 12           |
| Vinhedo=truncar | perdas0=sem_perdas |            607 |       0.88  |     0.458 |             7.084 |          37.397 | 9 de 12           |
| Vinhedo=retirar | perdas0=manter     |            606 |       0.997 |     0.987 |             0.083 |           0.495 | 11 de 12          |
| Vinhedo=retirar | perdas0=retirar    |            596 |       0.944 |     0.687 |             2.95  |          16.946 | 9 de 12           |
| Vinhedo=retirar | perdas0=sem_perdas |            606 |       0.88  |     0.459 |             7.068 |          37.294 | 9 de 12           |

## k escolhido por cenário e configuração

| cenario                              |   completos_ambos|log|minmax|conjunto |   completos_ambos|log|robust|conjunto |   completos_ambos|log|zscore|conjunto |   completos_ambos|nenhuma|minmax|conjunto |   completos_ambos|nenhuma|robust|conjunto |   completos_ambos|nenhuma|zscore|conjunto |   completos_ambos|winsor_log|minmax|conjunto |   completos_ambos|winsor_log|robust|conjunto |   completos_ambos|winsor_log|zscore|conjunto |   completos_ambos|winsor|minmax|conjunto |   completos_ambos|winsor|robust|conjunto |   completos_ambos|winsor|zscore|conjunto |
|:-------------------------------------|--------------------------------------:|--------------------------------------:|--------------------------------------:|------------------------------------------:|------------------------------------------:|------------------------------------------:|---------------------------------------------:|---------------------------------------------:|---------------------------------------------:|-----------------------------------------:|-----------------------------------------:|-----------------------------------------:|
| Vinhedo=manter | perdas0=manter      |                                     3 |                                     2 |                                     4 |                                         3 |                                         3 |                                         3 |                                            3 |                                            2 |                                            4 |                                        3 |                                        3 |                                        3 |
| Vinhedo=manter | perdas0=retirar     |                                     3 |                                     2 |                                     3 |                                         3 |                                         3 |                                         3 |                                            3 |                                            2 |                                            3 |                                        3 |                                        3 |                                        3 |
| Vinhedo=manter | perdas0=sem_perdas  |                                     3 |                                     2 |                                     3 |                                         3 |                                         3 |                                         3 |                                            3 |                                            2 |                                            3 |                                        3 |                                        3 |                                        3 |
| Vinhedo=truncar | perdas0=manter     |                                     3 |                                     2 |                                     4 |                                         2 |                                         3 |                                         3 |                                            3 |                                            2 |                                            4 |                                        3 |                                        3 |                                        3 |
| Vinhedo=truncar | perdas0=retirar    |                                     3 |                                     2 |                                     3 |                                         2 |                                         3 |                                         3 |                                            3 |                                            2 |                                            3 |                                        3 |                                        3 |                                        3 |
| Vinhedo=truncar | perdas0=sem_perdas |                                     3 |                                     2 |                                     3 |                                         2 |                                         3 |                                         3 |                                            3 |                                            2 |                                            3 |                                        3 |                                        3 |                                        3 |
| Vinhedo=retirar | perdas0=manter     |                                     3 |                                     2 |                                     4 |                                         2 |                                         3 |                                         3 |                                            3 |                                            2 |                                            4 |                                        3 |                                        3 |                                        3 |
| Vinhedo=retirar | perdas0=retirar    |                                     3 |                                     2 |                                     3 |                                         2 |                                         3 |                                         3 |                                            3 |                                            2 |                                            3 |                                        3 |                                        3 |                                        3 |
| Vinhedo=retirar | perdas0=sem_perdas |                                     3 |                                     2 |                                     3 |                                         2 |                                         3 |                                         3 |                                            3 |                                            2 |                                            3 |                                        3 |                                        3 |                                        3 |

## Onde ficam os casos (configuração de referência)

Cada célula: cluster em 2019 → cluster em 2024 (k do cenário). 'fora' = não entra na amostra. Os números dos clusters seguem o tamanho (1 = maior) dentro de cada cenário.

|                                      | Bady Bassitt   | Campos Novos Paulista   | Conchal     | Lavínia     | Luís Antônio   | Novais      | Rincão      | Santa Cruz das Palmeiras   | Severínia   | Taiúva      | Taquaral    | Vinhedo     |
|:-------------------------------------|:---------------|:------------------------|:------------|:------------|:---------------|:------------|:------------|:---------------------------|:------------|:------------|:------------|:------------|
| populacao                            | 28909          | 4991                    | 29034       | 9909        | 12531          | 4469        | 9145        | 29525                      | 14724       | 6733        | 2652        | 79235       |
| s24_IES2004                          | nan            | 100.0                   | 100.0       | 97.47       | 100.0          | 0.0         | 0.0         | 22.08                      | 100.0       | 100.0       | 100.0       | 129.42      |
| ae19_IN049                           | 0.0            | 0.0                     | 0.0         | 0.0         | 0.0            | 0.0         | 0.0         | 0.0                        | 0.0         | 0.0         | 0.0         | 33.63       |
| Vinhedo=manter | perdas0=manter      | fora           | 2 → 1 (k=2)             | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2)    | 2 → 2 (k=2) | 2 → 2 (k=2) | 2 → 2 (k=2)                | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) |
| Vinhedo=manter | perdas0=retirar     | fora           | fora                    | fora        | fora        | fora           | fora        | fora        | fora                       | fora        | fora        | fora        | 1 → 1 (k=2) |
| Vinhedo=manter | perdas0=sem_perdas  | fora           | 2 → 1 (k=2)             | 2 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2)    | 2 → 2 (k=2) | 2 → 2 (k=2) | 2 → 2 (k=2)                | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) |
| Vinhedo=truncar | perdas0=manter     | fora           | 2 → 1 (k=2)             | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2)    | 2 → 2 (k=2) | 2 → 2 (k=2) | 2 → 2 (k=2)                | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) |
| Vinhedo=truncar | perdas0=retirar    | fora           | fora                    | fora        | fora        | fora           | fora        | fora        | fora                       | fora        | fora        | fora        | 1 → 1 (k=2) |
| Vinhedo=truncar | perdas0=sem_perdas | fora           | 2 → 1 (k=2)             | 2 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2)    | 2 → 2 (k=2) | 2 → 2 (k=2) | 2 → 2 (k=2)                | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) |
| Vinhedo=retirar | perdas0=manter     | fora           | 2 → 1 (k=2)             | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2)    | 2 → 2 (k=2) | 2 → 2 (k=2) | 2 → 2 (k=2)                | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) | fora        |
| Vinhedo=retirar | perdas0=retirar    | fora           | fora                    | fora        | fora        | fora           | fora        | fora        | fora                       | fora        | fora        | fora        | fora        |
| Vinhedo=retirar | perdas0=sem_perdas | fora           | 2 → 1 (k=2)             | 2 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2)    | 2 → 2 (k=2) | 2 → 2 (k=2) | 2 → 2 (k=2)                | 1 → 1 (k=2) | 1 → 1 (k=2) | 1 → 1 (k=2) | fora        |

> Como ler: se um cenário tem ARI perto de 1 e poucos municípios mudando de cluster em todas as configurações, a decisão quase não afeta o resultado e pode ser tomada pelo critério mais defensável no texto. Se o ARI cai ou o k muda, a decisão importa e deve ser justificada e reportada como análise de sensibilidade.