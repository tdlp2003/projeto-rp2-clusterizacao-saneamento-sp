# Clusterização de municípios de SP por saneamento (água e esgoto) — SNIS 2019 × SINISA 2024

Agrupar os 645 municípios de São Paulo pelos indicadores de abastecimento de água e esgotamento
sanitário, comparar 2019 com 2024 e cruzar os grupos com o porte populacional.

## Como rodar

```bash
pip install -r requirements.txt
python -m src.build_panel     # etapa 1: planilhas brutas -> data/processed/painel_sp_2019_2024.csv
python -m src.eda             # etapa 2: análise exploratória -> outputs/
python -m src.preprocess      # etapa 3: grade de pré-processamento + sensibilidade -> outputs/
python -m src.clustering      # etapa 4: K-means, k escolhido pelo Método da Silhueta -> outputs/
pytest                        # testes
```

Sempre rodar **da raiz do repositório**. A etapa 1 extrai sozinha as planilhas necessárias dos ZIPs
para `data/raw/extraido/`.

## Fontes dos dados

Todos os arquivos já estão em `data/raw/`. Para baixar de novo, use o link **"Baixar Tabelas"** (SNIS) ou
**"Planilhas de Informações e Indicadores"** (SINISA) nas páginas oficiais:

| Base | Página oficial | Arquivo |
|---|---|---|
| SNIS água e esgoto 2019 | [Diagnóstico AE 2019 (MIDR)](https://www.gov.br/mdr/pt-br/assuntos/saneamento/snis/diagnosticos-anteriores-do-snis/agua-e-esgotos-1/2019) | `Planilhas_AE2019.zip` |
| SNIS resíduos 2019 | [Diagnóstico RS 2019 (MIDR)](https://www.gov.br/mdr/pt-br/assuntos/saneamento/snis/diagnosticos-anteriores-do-snis/residuos-solidos-1/2019) | `DiagRS2019_XLS.zip` |
| SINISA água, esgoto e resíduos, ano de referência 2024 | [Resultados SINISA 2025 (Ministério das Cidades)](https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa/resultados-sinisa/resultados-sinisa-2025) | `SINISA_Resultados_Ref2024.zip` (água), `SINISA_ESGOTO_Planilhas_2024.zip`, `SINISA_RESIDUOS_planilhas_2024.zip` |
| População, área, nome | export da plataforma "Municípios e Saneamento" (IAS) | `municipiose_saneamento_export_27_09_2026.csv` |

- O ano de referência 2024 está na página **"Resultados SINISA 2025"**. A página "Resultados SINISA 2024" é do ano de referência 2023.
- A população do IAS é idêntica à variável DFE0001 do SINISA 2024 (conferido nos 645 municípios). No artigo, cite "SINISA 2024 (DFE0001)".
- Os PDFs em `data/raw/` são os glossários de indicadores e o diagnóstico SNIS-AE 2019. São eles que definem a correspondência entre os códigos de 2019 e 2024.
- Ao baixar de novo, coloque os zips no mesmo lugar e rode `pytest`. Se as contagens mudarem, a base foi retificada.

## Estrutura

```
data/
  raw/                 dados brutos (ZIPs, planilhas, PDFs, CSV do IAS) — não editar
  processed/           painel_sp_2019_2024.csv, dicionario_variaveis.csv, cobertura_indicadores.csv
src/
  config.py            caminhos, RANDOM_STATE, faixas de porte e MATRIZES de indicadores (único lugar)
  io_utils.py          leitura das planilhas e extração dos ZIPs
  build_panel.py       etapa 1 — monta o painel (1 linha por município)
  eda.py               etapa 2 — análise exploratória
  preprocess.py        etapa 3 — pré-processamento parametrizado
  clustering.py        etapa 4 — K-means + Método da Silhueta (maior silhueta média sobre todas as instâncias)
tests/                 testes do painel, do pré-processamento e da clusterização
docs/
  decisoes.md          registro de decisões (alimenta a metodologia) ← atualizar a cada decisão
  metodologia_preparacao.md   descrição da etapa de preparação dos dados
  auditoria_etapa1/    auditoria independente do painel e recomendação da matriz
outputs/               figuras, tabelas e resumos gerados (fora do git)
```

## Painel (`data/processed/painel_sp_2019_2024.csv`)

645 linhas (um município por linha), 244 colunas:
- identificação e porte: `cod_ibge7`, `cod_mun6`, `municipio`, `populacao`, `populacao_urbana`,
  `area_km2`, `log10_pop`, `porte`
- indicadores com prefixo da base: `ae19_` (SNIS água/esgoto 2019), `rs19_` (SNIS resíduos 2019),
  `s24_` (SINISA 2024), mais `respondeu_RS_2024`

A população vem do export do IAS e é igual ao DFE0001 do SINISA 2024 (ano de referência 2024).

## Matriz de indicadores

Definida em `src/config.py`. Principal (**A4**, N = 607 municípios completos nos dois anos):

| indicador | 2019 (SNIS) | 2024 (SINISA) |
|---|---|---|
| atendimento total de água | IN055 | IAG0001 |
| perdas na distribuição | IN049 | IAG2013 |
| atendimento total de esgoto | IN056 | IES0001 |
| tratamento do esgoto coletado | IN016 | IES2004 |

A matriz com resíduos (**R4**, N = 521) fica só para análise de sensibilidade. Justificativa em
`docs/decisoes.md` e `docs/auditoria_etapa1/AUDITORIA_ETAPA1.md` (§5–10). Para trocar de matriz, mude
`MATRIZ` em `config.py`.

## Clusterização (`src/clustering.py`)

- **K-means** (n_init = 50, `RANDOM_STATE` = 42) sobre a matriz X do `preprocess.py`. Por padrão usa a
  configuração `REFERENCIA` (provisória); dá para trocar com `--inclusao`, `--transformacao`,
  `--escala` e `--escopo`.
- **Número de clusters pelo Método da Silhueta**: para cada k da grade (padrão 2..10, mude com
  `--kmin`/`--kmax`), calcula a silhueta média, isto é, a média de s(i) = (b − a) / max(a, b) sobre
  todas as instâncias. Escolhe o k de maior média; em empate, o menor k.
- 2019 e 2024 são clusterizados **juntos, no mesmo espaço** (cada município-ano é uma instância),
  então o cluster de um município é comparável entre os anos. Clusters numerados por tamanho
  (1 = maior).
- Saídas:
  - `outputs/resumo_clustering.md`: curva da silhueta, k escolhido, perfis, cluster × porte e transição
  - `outputs/tabelas/kmeans_silhueta_por_k.csv`: silhueta média, inércia e menor cluster por k
  - `outputs/tabelas/kmeans_rotulos.csv`: cluster e s(i) de cada município-ano, com porte e valores originais
  - `outputs/tabelas/kmeans_perfis.csv`: medianas dos indicadores por cluster
  - `outputs/tabelas/kmeans_cluster_por_porte.csv`: % de cada faixa de porte em cada cluster, por ano
  - `outputs/tabelas/kmeans_transicao_2019_2024.csv`: quantos municípios mudaram de cluster
  - `outputs/figuras/kmeans_silhueta_por_k.png` e `kmeans_silhueta_instancias.png`
- **Atenção**: o k escolhido depende do pré-processamento (k = 2, 3 ou 4 conforme transformação e
  escala; ver `docs/decisoes.md`).

## Armadilhas dos dados (já tratadas no código; guardar para a metodologia)

1. **Chave**: SNIS = IBGE sem dígito verificador (6 dígitos); SINISA = 7 dígitos. Join: `cod_ibge7 // 10 == cod_mun6`.
2. **Colisão de códigos**: `IN015`/`IN016` significam coisas diferentes no SNIS-AE (esgoto) e no SNIS-RS (resíduos). Por isso os prefixos.
3. **SNIS-AE 2019 é por prestador**: SABESP (372 linhas SP), LPU (228), LEP (25), LPR (6) = 631 linhas → 628 municípios (Mauá, Salto e Santa Maria da Serra têm prestadores separados de água e esgoto).
4. **17 municípios sem dado de água/esgoto em 2019**: Aramina, Ariranha, Boa Esperança do Sul, Borebi, Canitar, Cedral, Dumont, Ibitinga, Júlio Mesquita, Monte Castelo, Nova Castilho, Pacaembu, Paraíso, São João de Iracema, Tejupá, Uchoa, Vera Cruz.
5. **Ano do SINISA**: os arquivos usados são de referência 2024 (publicados em 18/12/2025); a base de **água foi retificada em 25/05/2026**. Escrever sempre "SINISA, ano de referência 2024".
6. **Valores impossíveis conhecidos**: Vinhedo `IES2004` = 129,42%; 11 municípios com perdas = 0 em 2019. Tratamento pendente (`docs/decisoes.md`).
7. **Comparabilidade temporal**: SNIS → SINISA é mudança de metodologia; diferenças entre 2019 e 2024 misturam mudança real e mudança de coleta. Declarar como limitação.

## Próximas etapas

- **Pré-processamento final**: o k escolhido pela silhueta muda com a transformação/escala (ver `docs/decisoes.md`); fixar a configuração antes de interpretar os clusters.
- **Interpretar e nomear os clusters** a partir dos perfis, depois de fixar o pré-processamento.
- **Porte**: a tabela cluster × porte já sai do `clustering.py`; falta o teste de associação
  (ex.: qui-quadrado/Cramér's V).
- **Comparação temporal**: a matriz de transição 2019 → 2024 já sai do `clustering.py`; falta
  discutir a limitação SNIS → SINISA ao interpretá-la.
