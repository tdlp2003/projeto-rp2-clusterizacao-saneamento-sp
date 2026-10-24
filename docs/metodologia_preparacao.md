# Preparação dos dados: saneamento em São Paulo, SNIS 2019 × SINISA 2024

> Documento de apoio ao relatório. Descreve o contexto, as decisões, o que foi feito, os resultados e as limitações da etapa de **preparação e verificação de viabilidade** da base.
> **Nenhuma análise estatística, algoritmo de clusterização ou número de clusters foi definido nesta etapa.**

---

## 1. Contexto e pergunta

O trabalho pretende **agrupar (clusterizar) os municípios do estado de São Paulo segundo seus indicadores de saneamento básico** (água, esgoto e resíduos sólidos) e **comparar dois momentos: 2019 e 2024**.

A prioridade declarada pelo grupo foi **verificar se é viável construir uma base comparável dos municípios de SP para os dois anos**, antes de definir título, objetivo, variáveis, algoritmos e metodologia. Ou seja, o escopo "São Paulo, 645 municípios" **não foi assumido como aprovado**: a decisão deve ser sustentada pela cobertura dos dados.

Etapas previstas depois desta: análise exploratória → tratamento dos dados → clusterização → resultados preliminares → atualização de metodologia, introdução, trabalhos correlatos, discussão e conclusão → artigo final em LaTeX.

## 2. Fontes de dados

| Base | Ano de referência | Sistema | Nível dos dados | Arquivos usados |
|---|---|---|---|---|
| Água e esgoto | 2019 | SNIS (Diagnóstico dos Serviços de Água e Esgotos 2019) | Por prestador de serviço, com município identificado | Planilhas de **Indicadores**: SABESP, LPU, LEP e LPR |
| Resíduos sólidos | 2019 | SNIS (Diagnóstico do Manejo de RSU 2019) | Municipal | `Planilha_Indicadores_RS_2019.xlsx` |
| Água | 2024 | SINISA (publicação 18/12/2025; base de água retificada em 25/05/2026) | Base Municipal | `SINISA_AGUA_Indicadores_Base Municipal_2024_Retificação.xlsx` |
| Esgoto | 2024 | SINISA (publicação 18/12/2025) | Base Municipal | `SINISA_ESGOTO_Indicadores_Base Municipal_2024.xlsx` |
| Resíduos | 2024 | SINISA (geração 18/12/2025) | Municipal | `SINISA_RESIDUOS_Indicadores_2024.xlsx` |
| Universo de municípios, população e porte | – | Exportação da plataforma IAS (`municipiose_saneamento_export_27_09_2026.csv`) | 645 municípios de SP | usado para definir o universo de 645 municípios |

Os PDFs (Diagnóstico SNIS-AE 2019 e glossários de indicadores do SINISA) foram usados como **documentação**: definição dos indicadores e correspondência entre códigos do SNIS e do SINISA. Não são lidos pelo código.

### 2.1 Observação sobre o "ano" do SINISA

Uma verificação feita nas etapas anteriores da conversa, com base nos relatórios oficiais, indicou que a edição denominada "SINISA 2024" tem **ano de referência 2023**, e que os dados com **ano de referência 2024** pertencem à edição publicada em dezembro de 2025. Os arquivos usados aqui trazem "Ano de referência 2024" no próprio cabeçalho (conferido nos arquivos de água e esgoto). No texto do artigo, convém sempre escrever "SINISA, ano de referência 2024" para evitar ambiguidade.

## 3. Histórico do que foi feito

### 3.1 Etapas anteriores (resumo, resultados já obtidos antes desta etapa)

Com o CSV do IAS, a planilha SNIS-RS 2019 e os microdados SINISA 2024, foi feito um primeiro cruzamento:

- O código de município do SNIS (6 dígitos) equivale ao código IBGE (7 dígitos) **sem o dígito verificador**. Chave de junção: `cod_ibge7 // 10 == cod_mun6`. Todos os 556 municípios de SP do SNIS-RS 2019 foram encontrados no universo de 645.
- Em 2024, **599 de 645 municípios** tinham valor simultâneo em água, esgoto e resíduos.
- Em resíduos, a correlação de Spearman entre 2019 e 2024 para o mesmo indicador nominal foi baixa (cobertura total da coleta ≈ 0,35; cobertura urbana ≈ 0,09; massa per capita ≈ 0,11). Esses valores foram calculados na etapa anterior e **não foram recalculados nesta etapa**. Sugerem que parte da variação pode decorrer da mudança de metodologia e de coleta entre SNIS e SINISA, o que deve constar como limitação.
- Ficou pendente a planilha municipal de **água e esgoto do SNIS 2019**, pois só havia o PDF narrativo.

### 3.2 Esta etapa

**a) Localização da planilha pendente.** O arquivo `Planilhas_AE2019.zip`, já enviado pelo grupo, continha a planilha municipal de água e esgoto do SNIS 2019. Não foi necessária nova busca externa.

**b) Entendimento da estrutura.** Os dados de água e esgoto do SNIS 2019 são organizados **por prestador de serviço**, não por município. Para SP, quatro arquivos de "Indicadores" cobrem todos os prestadores:

| Arquivo | Tipo de prestador | Linhas de SP |
|---|---|---|
| Regionais: SABESP | Regional (SABESP) | 372 |
| LPU | Local, direito público (SAAEs, prefeituras) | 228 |
| LEP | Local, empresa privada | 25 |
| LPR | Local, direito privado com administração pública | 6 |

Os arquivos são `.xls` (formato antigo) e têm cabeçalho em várias linhas (títulos, nome do indicador, unidade e código do indicador). A linha dos códigos (`IN055`, `IN056` etc.) é localizada **automaticamente por padrão de texto**, em vez de posição fixa.

**c) Conversão de formato.** Como a biblioteca `xlrd` não estava disponível no ambiente de trabalho, os quatro `.xls` foram convertidos para `.xlsx` com o LibreOffice. O código prefere `.xlsx` quando existir e usa `.xls` (exigindo `xlrd`) caso contrário.

**d) Consolidação para 1 linha por município.**
- Total de 631 linhas de prestadores em SP, correspondendo a **628 municípios distintos**.
- Três municípios (**Mauá, Salto e Santa Maria da Serra**) têm um prestador só de água e outro só de esgoto. As duas linhas foram **combinadas** (primeiro valor não nulo por coluna), de modo que cada município tenha uma única linha com água e esgoto.

**e) Checagem de cobertura contra o universo de 645 municípios.**
- **17 municípios de SP não aparecem em nenhum arquivo de água e esgoto de 2019**, nem na Planilha de Pesquisa Simplificada: Aramina, Ariranha, Boa Esperança do Sul, Borebi, Canitar, Cedral, Dumont, Ibitinga, Júlio Mesquita, Monte Castelo, Nova Castilho, Pacaembu, Paraíso, São João de Iracema, Tejupá, Uchoa e Vera Cruz.
- Nenhum município do SNIS 2019 ficou fora do universo de 645.

**f) Construção do código reprodutível** (`src/build_panel.py`, com `config.py` e `io_utils.py`), que lê as oito planilhas de indicadores, filtra SP, padroniza chaves e gera as saídas descritas na seção 5.

**g) Verificação.** O código foi executado com sucesso e as contagens foram conferidas (seção 4).

## 4. Resultados da verificação de viabilidade

### 4.1 Cobertura por indicador (município com valor, entre os municípios de cada base)

| Indicador | Base | N com valor |
|---|---|---|
| Atendimento de água, total (IN055 / IAG0001) | SNIS-AE 2019 / SINISA 2024 | 628 / 626 |
| Atendimento de esgoto, total (IN056 / IES0001) | SNIS-AE 2019 / SINISA 2024 | 628 / 618 |
| Perdas na distribuição (IN049 / IAG2013) | SNIS-AE 2019 / SINISA 2024 | 628 / 629 |
| Cobertura da coleta de resíduos (IN015-RS / IRS0001) | SNIS-RS 2019 / SINISA 2024 | 556 / 616 |
| Massa coletada per capita (IN028-RS / IRS1004) | SNIS-RS 2019 / SINISA 2024 | 556 / 616 |
| Coleta seletiva (IN030-RS / IRS0006, 2019 porta a porta) | SNIS-RS 2019 / SINISA 2024 | 299 / 616 |

Os totais do SINISA 2024 são contados sobre os 645 municípios do painel. Em resíduos 2024, 616 municípios responderam ao módulo e 29 não (o indicador fica vazio, não zero).

### 4.2 Municípios com dados completos (contagem mecânica, **não é recomendação de matriz**)

| Combinação | Municípios completos |
|---|---|
| 2024: água + esgoto + resíduos (cobertura e massa per capita) | 599 |
| 2019: água + esgoto + resíduos (os mesmos quatro) | 551 |
| 2019 e 2024, os quatro indicadores nos dois anos | 521 |
| 2019 e 2024, somente água + esgoto | 607 |

Leitura: **é viável construir uma base comparável**, mas o tamanho da amostra depende de incluir ou não resíduos. Incluir resíduos custa cerca de 86 municípios (607 → 521). A escolha da matriz final cabe ao grupo e deve ser justificada na metodologia.

## 5. Produtos gerados (`data/processed/`)

| Arquivo | Conteúdo |
|---|---|
| `painel_sp_2019_2024.csv` | 645 linhas (um município por linha), com colunas prefixadas `ae19_`, `rs19_` e `s24_` |
| `snis_ae_2019_sp.csv` | SNIS água e esgoto 2019, 628 municípios |
| `snis_rs_2019_sp.csv` | SNIS resíduos 2019, 556 municípios |
| `sinisa_2024_sp.csv` | SINISA 2024 (água, esgoto e resíduos), 645 municípios |
| `snis_ae_2019_sp_por_prestador.csv` | 631 linhas brutas, com prestador e tipo de serviço |
| `dicionario_variaveis.csv` | Código, nome, unidade e fonte de cada indicador |
| `cobertura_indicadores.csv` | Número de municípios com valor por indicador |

## 6. Decisões técnicas e por quê

1. **Chave de junção `cod_ibge7 // 10`**: os dois sistemas usam formatos diferentes de código de município.
2. **Prefixos de coluna (`ae19_`, `rs19_`, `s24_`)**: o código `IN015` significa coisas diferentes no SNIS-AE (índice de coleta de esgoto) e no SNIS-RS (cobertura da coleta de resíduos). Sem prefixo haveria colisão silenciosa.
3. **Localização automática da linha de códigos**: reduz a dependência de posições fixas de linha, que variam entre arquivos.
4. **Um município, uma linha**: exigência para a clusterização; os 3 casos com dois prestadores foram combinados.
5. **Sem imputação e sem descarte de variáveis**: as ausências foram preservadas para serem tratadas na etapa de tratamento de dados, de forma explícita e comparável.

## 7. Correspondência de indicadores SNIS × SINISA

Conforme os glossários oficiais do Ministério das Cidades: IN055 = IAG0001; IN023 = IAG0002; IN056 = IES0001; IN049 = IAG2013; IN046 = IES2003; IN015 (RS) = IRS0001; IN016 (RS) = IRS0002; IN028 (RS) = IRS1004; IN022 (RS) = IRS1005; IN030 (RS) = IRS0006. Para hidrometração, o glossário indica IN009 = IAG1003 e IN044 = IAG2002.

## 8. Limitações e cuidados (para a seção de limitações do artigo)

1. **Mudança de sistema e metodologia (SNIS → SINISA).** Diferenças entre 2019 e 2024 podem refletir mudanças de coleta e de método, e não apenas evolução real. A baixa correlação entre anos em resíduos (seção 3.1) reforça esse cuidado.
2. **IN056 e IES0001.** O IN056 é referido aos municípios atendidos com água; a equivalência exata com o IES0001 deve ser verificada quanto à base populacional antes de tratá-los como idênticos.
3. **IAG0004 e IAG0005** (atendimento de domicílios com rede de água) não são calculados para SP no SINISA 2025, segundo nota metodológica; não podem ser usados.
4. **17 municípios sem dados de água e esgoto em 2019** e 29 sem resposta em resíduos 2024. Verificar se a ausência está relacionada ao porte ou ao tipo de prestador, o que afetaria a representatividade.
5. **Autodeclaração.** Os dados são informados pelos próprios prestadores e municípios, com qualidade variável, especialmente em resíduos.
6. **Base de água 2024 retificada** em 25/05/2026: citar a versão usada.
7. **Dicionário de variáveis:** nomes e unidades foram extraídos por posição relativa das linhas de cabeçalho e **não foram revisados manualmente**. Revisar antes de usar em tabelas do artigo.
8. **Leitura de `.xls`.** Os testes foram feitos com `.xls` convertidos para `.xlsx`. A leitura direta com `xlrd` não foi testada.
9. **Números anteriores.** As correlações 2019 × 2024 (seção 3.1) vêm de etapa anterior e não foram recalculadas aqui.

## 9. Próximos passos sugeridos

1. **Análise exploratória:** distribuição, ausências, valores no teto de 100%, outliers e correlações dentro de cada ano.
2. **Tratamento:** decidir, com registro, regra de inclusão (casos completos × imputação), transformações e padronização, comparando alternativas.
3. **Clusterização:** testar vários algoritmos na mesma matriz e escolher o número de clusters por critérios de validação e estabilidade, apresentando a curva completa, sem escolha arbitrária.
4. **Comparação temporal:** clusterizar 2019 e 2024 no mesmo espaço de variáveis e analisar a transição de municípios entre grupos.
5. **Documentar** cada decisão de pré-processamento para alimentar a seção de metodologia.

## 10. Reprodução

```bash
pip install -r requirements.txt
python -m src.build_panel
```

Detalhes de pastas e arquivos brutos esperados estão no `README.md` da raiz do projeto.
