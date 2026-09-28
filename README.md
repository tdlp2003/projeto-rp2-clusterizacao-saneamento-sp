# Saneamento em SP — SNIS 2019 × SINISA 2024 (ref. 2024)

Este projeto só **prepara os dados**. Nenhuma análise, algoritmo ou número de clusters foi escolhido.

## 1. Onde estava a planilha SNIS-AE 2019 que faltava
Dentro do `Planilhas_AE2019.zip` que você enviou. Os dados são **por prestador**, então SP vem em 4 arquivos:
| arquivo | prestador | linhas SP |
|---|---|---|
| `Planilha_AE_Indicadores_SABESP-35503000.xls` | SABESP (regional) | 372 |
| `Planilha_LPU_Indicadores.xls` | local, direito público (SAAEs, prefeituras) | 228 |
| `Planilha_LEP_Indicadores.xls` | local, empresa privada | 25 |
| `Planilha_LPR_Indicadores.xls` | local, direito privado c/ adm. pública | 6 |

Total: 631 linhas → **628 municípios** (3 municípios têm um prestador só de água e outro só de esgoto: Mauá, Salto, Santa Maria da Serra; o script junta os dois).
Os **17 municípios de SP sem nenhum dado de água/esgoto em 2019** (ausentes também na Pesquisa Simplificada): Aramina, Ariranha, Boa Esperança do Sul, Borebi, Canitar, Cedral, Dumont, Ibitinga, Júlio Mesquita, Monte Castelo, Nova Castilho, Pacaembu, Paraíso, São João de Iracema, Tejupá, Uchoa, Vera Cruz.

## 2. Estrutura
```
projeto_saneamento_sp/
├── data/raw/            <- descompacte aqui (ver src/config.py)
│   ├── snis_ae_2019/    (Planilhas_AE2019.zip + ZIPs internos descompactados)
│   ├── snis_rs_2019/    (DiagRS2019_XLS.zip)
│   └── sinisa_2024/     (3 ZIPs SINISA: água, esgoto, resíduos)
├── data/processed/      <- saída do passo 1 (já incluída)
├── src/
│   ├── config.py        caminhos; SANEAMENTO_RAW sobrescreve data/raw
│   ├── io_utils.py      leitura + localização automática da linha de códigos
│   ├── build_panel.py   PASSO 1 (pronto e testado)
│   └── (a criar) eda.py, preprocess.py, clustering.py, validation.py
├── notebooks/           (a criar) 01_eda.ipynb ...
└── outputs/             figuras e tabelas do artigo
```
Rodar: `pip install -r requirements.txt` e depois `python -m src.build_panel` (na raiz).

## 3. Arquivos gerados (`data/processed/`)
- `painel_sp_2019_2024.csv` — **645 linhas** (universo IAS), colunas com prefixo `ae19_`, `rs19_`, `s24_`.
- `snis_ae_2019_sp.csv`, `snis_rs_2019_sp.csv`, `sinisa_2024_sp.csv` — bases separadas.
- `snis_ae_2019_sp_por_prestador.csv` — 631 linhas brutas, com prestador e tipo de serviço.
- `dicionario_variaveis.csv` — código → nome → unidade → fonte.
- `cobertura_indicadores.csv` — N preenchido por indicador.

## 4. Armadilhas (já tratadas no código, mas guarde para a metodologia)
1. **Chave**: SNIS = IBGE sem dígito verificador (6 dígitos); SINISA = 7 dígitos. Join: `cod_ibge7 // 10 == cod_mun6`.
2. **Colisão de códigos**: `IN015` no SNIS-AE é *índice de coleta de esgoto*; no SNIS-RS é *cobertura de coleta de RDO*. Por isso o painel usa prefixos.
3. **Ano de referência**: a "edição SINISA 2024" é ref. 2023; os arquivos usados aqui (ref. 2024) são os publicados em 18/12/2025. A base de **água tem retificação (25/05/2026)**.
4. **Equivalências oficiais** (glossários): IN055=IAG0001, IN023=IAG0002, IN056=IES0001, IN009=IAG1003 (o SINISA também tem IAG2002 = IN044), IN049=IAG2013, IN046=IES2003, IN015=IRS0001, IN016=IRS0002, IN028=IRS1004, IN022=IRS1005. **IN056 é referido a municípios atendidos com água**; confira a base populacional antes de tratar IES0001 como idêntico.
5. **Não comparáveis**: IAG0004/IAG0005 não são calculados para SP no SINISA 2025.
6. **Resíduos 2024**: `respondeu_RS_2024` = "Não" em 29 municípios (indicador vazio, não zero).
7. **Comparabilidade temporal**: mudança SNIS→SINISA é mudança de metodologia/coleta; trate como limitação explícita.

## 5. Municípios completos por combinação (contagem mecânica, não é recomendação)
| combinação | N |
|---|---|
| 2024: água + esgoto + RS (IAG0001, IES0001, IRS0001, IRS1004) | 599 |
| 2019: IN055, IN056, RS IN015, RS IN028 | 551 |
| 2019 e 2024, os 4 indicadores acima nos dois anos | 521 |
| 2019 e 2024, só água + esgoto | 607 |

## 6. Como estruturar as próximas etapas (sem decidir nada antecipadamente)
**`eda.py`** — por indicador e por ano: N, % ausentes, quantis, assimetria, % no teto (100%) ou no zero, outliers (IQR e z robusto), matriz de correlação de **Spearman** dentro de cada ano, e mapa de ausência (`missingno`/heatmap) para ver se a falta é aleatória (por porte, por prestador).
**`preprocess.py`** — funções puras que recebem o painel e devolvem X, com cada decisão parametrizada e registrada: (a) regra de inclusão (casos completos vs. imputação — compare os dois); (b) tratamento de teto/assimetria (winsorização, log1p, ou nada); (c) padronização (Z, robust scaler, min-max); (d) **um scaler ajustado por ano ou conjunto?** — para comparar 2019×2024 use o mesmo scaler/mesmo espaço, senão os clusters não são comparáveis.
**`clustering.py`** — interface única `fit(X, algoritmo, k, seed)` que retorna rótulos. Rode **vários algoritmos com a mesma matriz** (ex.: k-means, aglomerativo com Ward/average, GMM, DBSCAN/HDBSCAN) e deixe os dados decidirem.
**`validation.py`** — para escolher k sem arbitrariedade: silhouette, Calinski–Harabasz, Davies–Bouldin, gap statistic e, para GMM, BIC/AIC, tudo em uma grade de k; **estabilidade** por bootstrap (ARI entre reamostras) e por perturbação de seed; sensibilidade ao pré-processamento (ARI entre pipelines). Reporte a curva inteira, não só o máximo.
**Comparação temporal** — cluster 2019 e 2024 no mesmo espaço padronizado (ou clusterize o empilhado) e analise a matriz de transição de municípios; discuta a limitação de metodologia.
**Reprodutibilidade** — `random_state` fixo em `config.py`, versões no `requirements.txt`, uma tabela de "decisões de pré-processamento" gerada automaticamente para a seção de metodologia.
