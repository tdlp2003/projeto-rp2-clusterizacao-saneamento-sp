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
python -m src.cenarios        # compara tratamentos de Vinhedo e das perdas zeradas (~2,5 min) -> outputs/
python -m src.comparar_k      # compara as soluções k = 2 (silhueta) e k = 3 (cotovelo) (~1 min) -> outputs/
python -m src.ward            # agrupamento hierárquico de Ward + comparação com o k-means (~1 min) -> outputs/
python -m src.gmm             # modelo de mistura gaussiana + comparação com k-means e Ward (~2 min) -> outputs/
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
  clustering.py        etapa 4 — K-means; k pelo Método da Silhueta, com o Método do Cotovelo como complemento
  cenarios.py          compara cenários de tratamento de Vinhedo (>100%) e das perdas = 0 em 2019
  comparar_k.py        compara soluções com k diferentes (usado na decisão por k = 3)
  ward.py              agrupamento hierárquico de Ward, mesma regra de k, comparação com o k-means
  gmm.py               modelo de mistura gaussiana: escolha da covariância, mesma regra de k, comparação
tests/                 testes do painel, do pré-processamento, da clusterização, dos cenários, da comparação de k, do Ward e do GMM
paper/
  artigo.tex, referencias.bib   artigo (modelo SBC), revisado para a matriz A4
  figuras/             figuras do artigo (cópias de outputs/figuras/)
docs/
  decisoes.md          registro de decisões (alimenta a metodologia) ← atualizar a cada decisão
  decisao_vinhedo_perdas.md   justificativa completa do tratamento de Vinhedo e das perdas zeradas
  evidencias/cenarios/ cópia das saídas de src/cenarios.py usadas nessa decisão
  comparacao_k2_k3.md  comparação entre k = 2 e k = 3 que fundamentou a escolha de k = 3
  evidencias/comparar_k/ cópia das saídas de src/comparar_k.py
  evidencias/ward/     cópia das saídas de src/ward.py
  evidencias/gmm/      cópia das saídas de src/gmm.py
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

**Tratamento de valores** (`TRATAMENTOS` em `config.py`, aplicado por `preprocess.tratar_valores`):
Vinhedo (tratamento 129,42%) é truncado em 100 e os 11 zeros de perdas de 2019 viram ausentes, o que
deixa **597 municípios** na análise principal. Justificativa: `docs/decisao_vinhedo_perdas.md`.

Matrizes de sensibilidade: **A3** (A4 sem perdas, a variável de correspondência mais fraca) e **R4**
(com resíduos, N = 521). Justificativa em
`docs/decisoes.md` e `docs/auditoria_etapa1/AUDITORIA_ETAPA1.md` (§5–10). Para trocar de matriz, mude
`MATRIZ` em `config.py`.

## Clusterização (`src/clustering.py`)

K-means (n_init = 50, `RANDOM_STATE` = 42) sobre a matriz X do `preprocess.py` (configuração
`REFERENCIA`, com os tratamentos de `config.TRATAMENTOS`). 2019 e 2024 são clusterizados **juntos,
no mesmo espaço** (cada município-ano é uma instância), então o cluster de um município é comparável
entre os anos. Os clusters são numerados por tamanho (1 = maior).

**Escolha do número de clusters**

1. **Candidatos:**
   - **Método da Silhueta:** k de maior silhueta média, a média de s(i) = (b − a) / max(a, b) sobre
     todas as instâncias, em k = 2..10.
   - **Método do Cotovelo** (Nainggolan et al., 2019): curva do Erro Quadrático Total
     (SSE = `KMeans.inertia_`) de k = 1 a 10. O cotovelo é o ponto da curva normalizada mais distante
     da reta que liga as pontas.
2. **Avaliação de cada candidato** (limiares em `config.CRITERIOS_K`):
   - (a) silhueta > 0,25;
   - (b) estabilidade bootstrap (ARI médio de 100 reamostragens de municípios) ≥ 0,85;
   - (c) menor cluster ≥ 5% das instâncias;
   - (d) não ser reproduzido pelo K-means de uma única variável (ARI < 0,90).
3. **Escolha:** é adotado o maior candidato que passa nos quatro critérios; os outros ficam só na tabela
   de avaliação, como descartados. Por decisão do grupo, `CRITERIOS_K["apresentar_complementar"] = False`.
   Com `True`, o outro candidato admissível seria gerado como "nível geral".

Resultado atual: silhueta → k = 2, cotovelo → k = 3. k = 2 não passa em (d), porque equivale ao
agrupamento do tratamento do esgoto (ARI 0,965). Assim, **o trabalho usa somente k = 3**.
Justificativa: `docs/decisoes.md` e `docs/comparacao_k2_k3.md`.

Saídas:
- `outputs/resumo_clustering.md`: candidatos, avaliação, justificativa da regra, perfis, porte e transição
- `outputs/tabelas/kmeans_avaliacao_candidatos.csv`: os quatro critérios de cada candidato
- `outputs/tabelas/kmeans_rotulos.csv`: cluster (k = 3) e silhueta de cada município-ano, com porte e
  valores originais
- `outputs/tabelas/kmeans_perfis_k3.csv`, `kmeans_porte_k3.csv`, `kmeans_transicao_k3.csv`
- `outputs/figuras/`: `kmeans_silhueta_por_k.png`, `kmeans_cotovelo.png`, `kmeans_perfis.png` e
  `kmeans_silhueta_instancias.png`
- **Atenção:**
  - a silhueta de k = 3 (0,37) indica estrutura fraca (Kaufman e Rousseeuw, 1990), então os perfis são
    tendências, não grupos nitidamente separados;
  - o resultado também depende do pré-processamento (ver `docs/decisoes.md`).

## Ward (`src/ward.py`)

Agrupamento hierárquico aglomerativo de Ward (`scipy`, distância euclidiana): junta, passo a passo, os
dois grupos cuja fusão menos aumenta o SSE, formando uma árvore (dendrograma) que é cortada em k grupos.
É determinístico, e as partições são aninhadas: o corte em k + 1 divide um dos grupos do corte em k.

- Mesma matriz, pré-processamento, tratamentos, regra de escolha de k e critérios do k-means.
- Estabilidade: bootstrap de municípios; como o Ward não classifica pontos novos, cada instância
  original é atribuída ao centroide mais próximo dos grupos da reamostragem.
- Comparação com o k-means: ARI, tabela de contingência e estabilidade **por cluster** (Jaccard médio;
  Hennig, 2007), para localizar quais grupos coincidem e quais dependem do algoritmo.
- Saídas: `outputs/resumo_ward.md`, `outputs/tabelas/ward_*.csv`, `outputs/figuras/ward_dendrograma.png`,
  `ward_silhueta_por_k.png`, `ward_cotovelo.png` e `ward_vs_kmeans_perfis.png`.

Resultado atual: a regra adota k = 2 no Ward, porque k = 3 é instável (ARI 0,62). Cortado em k = 3, o
Ward encontra os mesmos três perfis do k-means. O grupo de tratamento parcial é estável nos dois; a
divisão por acesso, não. Ver `docs/decisoes.md`.

## GMM (`src/gmm.py`)

Modelo de mistura gaussiana (`sklearn.mixture.GaussianMixture`, EM): supõe uma mistura de k normais
multivariadas e dá a cada município-ano uma probabilidade de pertencer a cada grupo.

- **Covariância:** excluem-se os tipos com componente degenerado (variância < 0,1% da total, ou seja,
  componente colapsado sobre os valores iguais a 100%). Entre os demais, fica o de menor BIC → `tied`.
  `full` e `diag` degeneram.
- **k:** mesma regra do k-means e do Ward. O BIC é registrado, mas não escolhe k, porque cai até k = 10
  em todos os tipos.
- **Comparação:** ARI entre os três algoritmos no k = 3, estabilidade por cluster (Jaccard), incerteza de
  pertença (% com probabilidade máxima < 0,8) e sensibilidade aos quatro tipos de covariância.
- **Saídas:** `outputs/resumo_gmm.md`, `outputs/tabelas/gmm_*.csv`, `outputs/figuras/gmm_bic.png`,
  `gmm_silhueta_por_k.png`, `gmm_cotovelo.png` e `tres_algoritmos_perfis.png`.

Resultado atual: com `tied`, o GMM separa os municípios pelo tratamento, mas não pelo acesso (ARI 0,39
com o k-means). Com `spherical`, reproduz os três perfis (ARI 0,85). Ver `docs/decisoes.md`.

## Cenários de tratamento (`src/cenarios.py`)

Testa 9 cenários (3 × 3) em 12 configurações de pré-processamento e compara cada um com o cenário
"manter tudo" (ARI, % de municípios que mudam de cluster e k escolhido):

| Problema | Opções |
|---|---|
| Vinhedo: tratamento 2024 = 129,42% | `manter`, `truncar` (vira 100), `retirar` (município sai) |
| 11 municípios com perdas = 0% em 2019 | `manter`, `retirar` (municípios saem), `sem_perdas` (matriz A3) |

Saídas: `outputs/resumo_cenarios.md`, `outputs/tabelas/cenarios_resumo.csv` e `cenarios_casos.csv`,
`outputs/figuras/cenarios_ari.png` e `cenarios_k.png`.

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
