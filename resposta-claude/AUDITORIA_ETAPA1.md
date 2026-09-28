# Auditoria do repositório e definição da base — Etapa 1

**Convenção de rótulos** (regra fundamental do prompt):
**[ARQ]** veio dos arquivos/PDFs · **[CALC]** calculado por mim a partir dos arquivos brutos · **[INF]** inferência metodológica · **[REC]** recomendação.
Nada foi alterado no código do projeto. Nenhuma clusterização foi executada. Os scripts que usei estão em `scripts_auditoria/` e as tabelas em `tabelas/`.

---

## 1. Diagnóstico geral

- **[CALC] Reprodução independente.** Reconstruí SNIS-AE 2019, SNIS-RS 2019 e SINISA 2024 (água, esgoto, resíduos) direto dos brutos, com parser próprio, e comparei célula a célula com `painel_sp_2019_2024.csv`: **0 diferenças** nas 84 colunas IN (AE), 47 IN (RS) e 101 IAG/IES/IRS/IFR do painel. Os números preliminares foram todos reproduzidos: 631 linhas de prestador → 628 municípios; 599 / 551 / 521 / 607 completos.
- **[CALC] O núcleo de dados é confiável; o problema não está na extração, e sim nas decisões em cima dela** (o que comparar, o que é composição, o que é zero, o que é missing).
- **[ARQ] Estrutura entregue ≠ estrutura descrita.** O ZIP é *plano* (`build_panel.py`, `config.py`, `io_utils.py`, `test_painel.py`, CSVs e `.md` na raiz; ZIPs brutos ainda compactados em `dados/`). O código usa `from .config import ...`, `ROOT = parents[1]` e espera `data/raw/`, `src/`, `tests/`. **Como está no ZIP, `python -m src.build_panel` não roda**, e o `pyproject.toml` aponta `testpaths=["tests"]` que não existe. Também não estão no ZIP `snis_ae_2019_sp.csv`, `snis_rs_2019_sp.csv`, `sinisa_2024_sp.csv` e `snis_ae_2019_sp_por_prestador.csv`, que o README lista.
- **[REC]** A estrutura (raw → processed → src → docs) é adequada em desenho; falta consolidá-la de fato, adicionar `assert`s de integridade e uma coluna de porte/população ao painel.

---

## 2. Inventário dos arquivos

| Arquivo | Fonte | Ano ref. | Unidade | Municípios (SP) | Tipo | Uso |
|---|---|---|---|---|---|---|
| `Planilhas_AE2019.zip` (8 ZIPs internos) | SNIS-AE | 2019 | prestador | – | bruto | fonte primária 2019 (água/esgoto) |
| ↳ `Planilha_AE_Indicadores_SABESP-35503000.xls` | SNIS-AE | 2019 | **município** ("Desagregado") | 372 | bruto | usado |
| ↳ `Planilha_LPU_Indicadores.xls` | SNIS-AE | 2019 | prestador local ("Agregado") | 228 | bruto | usado |
| ↳ `Planilha_LEP_Indicadores.xls` | SNIS-AE | 2019 | prestador local | 25 | bruto | usado |
| ↳ `Planilha_LPR_Indicadores.xls` | SNIS-AE | 2019 | prestador local | 6 | bruto | usado |
| ↳ demais (Microrregionais, Resumo, Simplificada, *Informacoes*) | SNIS-AE | 2019 | – | – | bruto | não usados (Informações contém POP_TOT/G12A — útil p/ porte 2019) |
| `DiagRS2019_XLS.zip` → `Planilha_Indicadores_RS_2019.xlsx` | SNIS-RS | 2019 | município | **556** | bruto | usado |
| ↳ outras 9 planilhas RS 2019 | SNIS-RS | 2019 | – | – | bruto | não usadas |
| `SINISA_Resultados_Ref2024.zip` → `SINISA_AGUA_Indicadores_Base Municipal_2024_Retificação.xlsx` | SINISA | 2024 (pub. 18/12/2025; retif. 25/05/2026) | município consolidado | **629** | bruto | usado |
| `SINISA_ESGOTO_Planilhas_2024.zip` → `SINISA_ESGOTO_Indicadores_Base Municipal_2024.xlsx` | SINISA | 2024 (pub. 18/12/2025) | município consolidado | **624** | bruto | usado |
| `SINISA_RESIDUOS_planilhas_2024.zip` → `SINISA_RESIDUOS_Indicadores_2024.xlsx` | SINISA | 2024 | município | 645 (616 respondentes) | bruto | usado |
| demais planilhas SINISA (Informações, Locais+Regionais, UF/MR/BR) | SINISA | 2024 | – | – | bruto | não usadas |
| `municipiose_saneamento_export_27_09_2026.csv` | IAS (compila SINISA 2024, Censo 2022, MUNIC 2023 etc.) | misto, **sem coluna de ano** | município | 645 únicos, **646 linhas** | bruto (auxiliar) | população/porte; conferência |
| `Diagnstico_SNIS_AE_2019_Republicacao_31032021.pdf` (190 p.) | SNIS | 2019 | – | – | documentação | contexto |
| `Glossario_Indicadores_AE2019.pdf`, `Glossario_Indicadores_RS2019.pdf` | SNIS | 2019 | – | – | documentação | definições SNIS |
| `INDICADORES_SINISA_ABASTECIMENTO_DE_AGUA_2024_v2.pdf`, `..._ESGOTAMENTOSANITRIO_2024_V2.pdf`, `Glossario_Indicadores_SINISA_RESIDUOS.pdf` | SINISA | 2024 | – | – | documentação | definições SINISA |
| `build_panel.py`, `config.py`, `io_utils.py`, `test_painel.py` | projeto | – | – | – | código | auditados (§3) |
| `painel_sp_2019_2024.csv` | projeto | 2019+2024 | município | 645 | processado | auditado (§4) |
| `dicionario_variaveis.csv` (185 linhas), `cobertura_indicadores.csv` | projeto | – | – | – | processado | auditados |
| `README.md`, `METODOLOGIA_PREPARACAO_DOS_DADOS.md`, `decisoes.md`, `requirements.txt`, `pyproject.toml`, `.gitignore` | projeto | – | – | – | documentação/config | auditados |

Confirmações pedidas: os três arquivos SINISA esperados **existem** nos ZIPs com os nomes indicados. Os quatro `.xls` do SNIS-AE **existem** (precisam de `xlrd` ou conversão; usei LibreOffice → `.xlsx`).

---

## 3. Auditoria do `build_panel.py` (+ `config.py`, `io_utils.py`)

### O que faz **[ARQ]**
`config.py` define caminhos/globs; `io_utils.py` lê a 1ª aba sem cabeçalho e localiza a linha de códigos por regex (≥5 células); `build_panel.py` (i) lê 4 planilhas AE por prestador, filtra `UF=="SP"`, concatena e colapsa a 1 linha/município; (ii) lê RS 2019; (iii) lê as 3 planilhas SINISA, filtra SP e faz *outer join*; (iv) monta o painel com `cod_mun6 = cod_ibge7 // 10` e prefixos `ae19_/rs19_/s24_`; (v) grava dicionário e cobertura.

### O que está correto **[CALC]**
1. **Chave `cod_ibge7 // 10`: correta.** Os 628 municípios do SNIS-AE e os 556 do SNIS-RS casam com o IAS **e os nomes coincidem 100%** (628/628 e 556/556); os 645 prefixos de 6 dígitos são únicos.
2. **Estrutura por prestador e contagens:** SABESP 372, LPU 228, LEP 25, LPR 6 = 631 linhas / 628 municípios (reproduzido). A planilha SABESP é "Desagregada" (uma linha por município); LPU/LEP/LPR são "Agregadas" por prestador local, e cada linha SP é um município (228/25/6 municípios distintos).
3. **Multi-prestador:** só 3 municípios (Mauá, Salto, Santa Maria da Serra); as 6 linhas são exatamente 3 "Água" + 3 "Esgoto". Nas colunas candidatas **não há conflito** (água só vem do prestador de água; esgoto, do de esgoto).
4. **Prefixos** evitam a colisão real de `IN015`/`IN016` (significam coisas diferentes em AE e RS). Bem visto.
5. **SINISA sem duplicatas em SP** (629/624/645 linhas, 0 duplicados de código); `respondeu_RS_2024` está corretamente alinhado por município (conferido) e coerente (Não ⇒ indicadores vazios: 0 exceções).

### Problemas encontrados
| # | Problema | Gravidade | Evidência |
|---|---|---|---|
| P1 | Layout plano vs. código em pacote (`src/`, `data/raw`); pipeline não roda como entregue | Alta (reprodutibilidade) | [ARQ] listagem do ZIP |
| P2 | **`groupby().first()` nos 3 municípios mistos** mistura prestadores: das ~28 colunas preenchidas nos dois prestadores, 25–27 **divergem** e o `first` fica com a linha do prestador de água. Sem efeito nos candidatos, mas **enviesa qualquer outra coluna operacional/financeira** dessas 3 cidades | Média | [CALC] Mauá 27/28, Salto 27/27, S. M. da Serra 25/25 divergentes |
| P3 | `cols[9] = "Tipo de serviço"` com índice fixo, contradizendo a alegação de "sem posições fixas" | Baixa | [ARQ] código |
| P4 | **Missing indiferenciado.** `to_numeric(errors="coerce")` funde 3 situações: (a) município **ausente** da base SINISA (16 em água, 21 em esgoto); (b) **"Não calculado (condições não atendidas)"** (3 em IAG0001, 6 em IES0001, 3 em IES2004, 158 em IAG0004); (c) **não respondente** de resíduos (29). São mecanismos diferentes de ausência | Média-Alta | [CALC] contagem de textos nas colunas |
| P5 | **Dicionário com unidades erradas em resíduos:** a "unidade" lida é o *título do grupo* ("Indicadores de Cobertura", "Indicadores Operacionais"…) e IRS1004 sai `NaN`. (A unidade está na linha do `cod_IBGE`, 2 linhas abaixo do código.) O próprio METODOLOGIA já avisa que não foi revisado | Média | [CALC] `dicionario_variaveis.csv` |
| P6 | Painel **não traz população/porte** (o IAS só é citado em comentário do `config.py`, nunca lido) | Média | [ARQ] |
| P7 | Universo do painel = *outer join* SINISA; só dá 645 porque o arquivo de resíduos traz todos os municípios do país. Não é o IAS (como o README diz) | Baixa | [ARQ] |
| P8 | `find_one` escolhe silenciosamente o 1º arquivo se o glob casar vários; `groupby.first()` esconderia duplicatas em vez de falhar | Baixa | [ARQ] |
| P9 | `painel["respondeu_RS_2024"] = s24[...].values` é atribuição posicional (funciona hoje, frágil) | Baixa | [ARQ] |
| P10 | `test_painel.py` aceita até 100,01 e testa só 5 colunas; **não detecta** `IES2003` até 2.898% nem `IES2004` = 129,4% (§4) | Média | [CALC] |
| P11 | Documento cita correlações 2019×2024 "da etapa anterior, não recalculadas": recalculei; cob. total 0,354 ✔ e urbana 0,094 ✔, mas massa per capita **0,178** (IN028×IRS1004), não ≈0,11 (**não reproduzido**; talvez outro par de indicadores) | Baixa | [CALC] |
| P12 | README afirma que IAG0004/IAG0005 "não são calculados para SP". **Parcialmente falso:** têm 471 e 413 valores numéricos de 629 (75% e 66%); o que ocorre é bloqueio por condição. Continuam inutilizáveis aqui por falta de par em 2019 e cobertura parcial | Baixa | [CALC] |
| P13 | O CSV do IAS tem **646 linhas de dados**: São Paulo (3550308) aparece **duas vezes** (redes "RMSP" e "Capitais"); 645 únicos. O prompt (e o METODOLOGIA) contam "646 linhas = 645 + cabeçalho": **é 647 linhas com cabeçalho** | Média | [CALC] |
| P14 | Números do IAS vêm em formato BR ("35.642", "99,98") e como texto; qualquer leitura direta gera erro silencioso | Baixa | [ARQ] |

---

## 4. Auditoria do painel `painel_sp_2019_2024.csv` **[CALC]**

- **Forma:** 645 × 238 (3 chaves + 87 `ae19_` + 47 `rs19_` + 101 `s24_`). `cod_ibge7` único ✔; `cod_mun6 == cod_ibge7//10` para todos ✔; sem colunas duplicadas ✔; sem nomes duplicados (nomes vêm do IAS; o painel não tem coluna de nome).
- **Municípios:** os 645 do IAS estão todos no painel, nenhum a mais/menos.
- **Colunas não indicadoras:** `ae19_Sigla`, `ae19_Tipo de serviço`, `ae19_fonte_prestador` (texto) — não entram na análise.
- **Ambíguas por sufixo:** `ae19_IN015/IN016` (esgoto) × `rs19_IN015/IN016` (resíduos): ok graças aos prefixos, mas `s24_IRS*` e `s24_IFR*` misturam indicadores de domínios distintos.
- **Faixa 0–100:** todos os percentuais candidatos em [0,100] **exceto** `s24_IES2004` (**Vinhedo = 129,42**) e `s24_IES2003` (**179 municípios >100; máx. 2.897,79; 10 acima de 200**). Nenhum valor negativo.
- **Zeros:** `IN049` 2019 = 0 em **11** municípios (Bady Bassitt, Campos Novos Paulista, Conchal, Lavínia, Luís Antônio, Novais, Rincão, Santa Cruz das Palmeiras, Severínia, Taiúva, Taquaral; todos LPU) — perdas de 0,00% e `IN051`=0 são fisicamente implausíveis → suspeita de dado inconsistente truncado (**[INF]**). `IN016(AE)` = 0 em 43 (2019) e `IES2004` = 0 em 22 (2024), sempre com atendimento de esgoto >0 (mín. 21,4% e 39,5%) → **zero real** ("coleta sem tratamento"). `IRS0006` = 0 em **269** de 616 em 2024, enquanto `IN030` 2019 **não tem nenhum zero** (mín. 1,77): em 2019 quem não tem coleta seletiva porta a porta aparece como **vazio**, em 2024 como **0** → universos incompatíveis (**[INF]**).
- **Tetos (≥99,99):** água (IN055) 22,6% → 12,2% (IAG0001); esgoto tratado (IN016) 72,0% → 77,9%; cob. RS total 24,8% → 52,0%; cob. RS urbana 83,6% → 89,9%; `IN023` 65,6% → 69,4%.
- **Outliers de escala:** `IRS1004` = 12,43 kg/hab·dia em **São José dos Campos** (mediana 0,88; `IRS1005` = 7,04 nesse mesmo município → não é erro de um só campo); Cotia 4,03; Júlio Mesquita 4,58.
- **Inconsistências lógicas:** atendimento de esgoto > água (+0,01) em 17 municípios (2019) e 30 (2024). Não é impossível (IN056 tem base distinta), mas exige conferência.
- **Escalas:** todos os candidatos de matriz estão em % (0–100) — exceto massa (kg/hab·dia) — então a escala nativa é compartilhada; a variância difere (desvio-padrão 14 a 29 pontos).
- **Duplicatas de informação:** `IN055`≈`IN056` (Spearman 0,82/0,78); `IN023` e `IN055` medem o mesmo eixo; `ae19_IN016` e `ae19_IN046` estão em construtos próximos.

---

## 5. Correspondência SNIS 2019 × SINISA 2024

Definições lidas em: `Glossario_Indicadores_AE2019/RS2019` (SNIS), PDFs SINISA e **abas "Nota metodológica"** dos arquivos de água e esgoto (que trazem as fórmulas exatas e as regras de bloqueio). Limitação: o texto extraído dos glossários SNIS traz a **lista de variáveis**, não a fórmula gráfica; onde a fórmula SNIS é citada abaixo como conhecimento externo, está sinalizado.

| Dimensão | 2019 | 2024 | Definição 2019 **[ARQ]** | Definição 2024 **[ARQ]** | Comp. | Observação |
|---|---|---|---|---|---|---|
| Água | IN055 | IAG0001 | AG001 (pop. total atendida) ÷ população total do município (POP_TOT/G12A, IBGE) | (GTA0001+GTA0002) ÷ DFE0001 (pop. total residente); bloqueia se CAD2003 = "apenas produção" ou numerador > DFE0001 | 🟢 | Mesmo construto; PDF SINISA lista IN055 como correspondente. **[INF]** A base populacional muda (estimativa IBGE 2019 × DFE0001 2024); o teto cai de 22,6% para 12,2% (**[CALC]**). ρ=0,63 |
| Água | IN049 | IAG2013 | Usa AG006, AG010, AG018, AG024 (volumes produzido, consumido, importado, de serviço) | [(GTA1001+GTA1009−GTA1207−GTA1211−GTA1203) ÷ (GTA1001+GTA1009)]×100; **bloqueia se numerador < 0** | 🟡 | Correspondência declarada no PDF SINISA, mas o **denominador do SINISA não subtrai o volume de serviço** e há tratamento explícito de exportação (GTA1203). **[INF]** o SNIS subtrai AG024 no denominador (conhecimento externo, confirmar no PDF). As 11 perdas = 0 em 2019 não existem em 2024. ρ=0,48 |
| Água | IN023 | IAG0002 | AG026 ÷ G06A/POP_URB | GTA0001 ÷ DFE0002 | 🟢 (definição) | Descartada por **teto** (65,6%/69,4% em 100) e ρ=0,32 |
| Água | IN009 / IN044 | IAG1003 / IAG2002 | hidrometração / micromedição sobre consumo | idem, com médias de ano atual e anterior (`_A`) | 🟢 | Operacionais; fora do escopo de "acesso" |
| Esgoto | IN056 | IES0001 | ES001 ÷ POP_TOT (referido aos municípios atendidos com água; G12A/G12B) | (GTE0001+GTE0002) ÷ DFE0001; rede coletora; bloqueia se numerador > DFE0001 ou "apenas tratamento" | 🟢 | PDF SINISA declara IN056 como correspondente. Solução individual/alternativa **não** entra em nenhum dos dois. **[INF]** no nível municipal o denominador coincide com a pop. total quando há água. ρ=0,75 |
| Esgoto | IN016 (AE) | IES2004 | (ES006+ES014+ES015) ÷ (ES005+ES013) — tratado ÷ coletado (variáveis do glossário) | (GTE1014+GTE1015+GTE1013) ÷ (GTE1002+GTE1009) | 🟢 | Construto equivalente. **Alerta de dado:** Vinhedo = 129,4 (>100) em 2024; bimodal (72–78% em 100; 43 e 22 zeros reais). ρ=0,67 |
| Esgoto | IN046 | IES2003 | Esgoto tratado ÷ água consumida (AG010−AG019) | [(GTE1014+GTE1013) ÷ GTA1211]×100 | 🔴 | Mesmo nome, mas depende da água consumida; **179 valores >100 e máx. 2.898%** em 2024 vs. nenhum em 2019; média 76→91. Não usar |
| Resíduos | IN015 (RS) | IRS0001 | Cobertura **regular** da coleta de RDO; CO164 (pop. atendida) ÷ POP_TOT (IBGE) | GTR0201 (pop. coberta por coleta indiferenciada direta ou indireta) ÷ DFE0001 | 🟡 | Construto próximo; mudam definição ("regular" × "direta ou indireta"), denominador e universo (556 × 616 respondentes). Teto 24,8% → 52,0%. ρ=0,35 |
| Resíduos | IN016 (RS) | IRS0002 | CO050 ÷ POP_URB | GTR0202 ÷ DFE0002 | 🔴 | Sem variância (84–90% no teto), ρ=0,09 |
| Resíduos | IN028 (RS) | IRS1004 | Massa RDO+RPU coletada **per capita da população *atendida*** (CO164) | GTR1028×1000 ÷ DFE0001 ÷ 365 — **população total residente** | 🔴 | O glossário SINISA lista IN028 como "similar", mas a fórmula usa DFE0001 (inclusive o texto do campo "correspondente" fala em "população atendida": **inconsistência interna do PDF**). Denominador muda; ρ=0,18; cauda extrema (12,4) |
| Resíduos | IN022 (RS) | IRS1005 | Massa RDO ÷ pop. atendida (CO164) | GTR1025 ÷ GTR0201 (pop. coberta) | 🟡 | Definição próxima, porém **só 213/645 (33%)** em 2019 — inviável |
| Resíduos | IN030 (RS) | IRS0006 | CS050 ÷ POP_URB (porta a porta, Prefeitura/SLU) | GTR0204 ÷ DFE0002 (seletiva direta) | 🔴 | 299 (46%) em 2019, vazios × 269 zeros em 2024 (universos incompatíveis) |

---

## 6. Cobertura dos indicadores (N e % sobre 645) **[CALC]**

| Indicador | 2019 N | 2019 % | 2024 N | 2024 % | Ambos N | Ambos % |
|---|---|---|---|---|---|---|
| Água atend. total (IN055 / IAG0001) | 628 | 97,4 | 626 | 97,1 | 614 | 95,2 |
| Água perdas (IN049 / IAG2013) | 628 | 97,4 | 629 | 97,5 | 617 | 95,7 |
| Água atend. urbano (IN023 / IAG0002) | 628 | 97,4 | 626 | 97,1 | 614 | 95,2 |
| Esgoto atend. total (IN056 / IES0001) | 628 | 97,4 | 618 | 95,8 | **607** | 94,1 |
| Esgoto trat. do coletado (IN016 / IES2004) | 628 | 97,4 | 621 | 96,3 | 610 | 94,6 |
| Esgoto trat./água consumida (IN046 / IES2003) | 625 | 96,9 | 621 | 96,3 | 607 | 94,1 |
| RS cobertura total (IN015 / IRS0001) | 556 | 86,2 | 616 | 95,5 | 537 | 83,3 |
| RS cobertura urbana (IN016 / IRS0002) | 556 | 86,2 | 616 | 95,5 | 537 | 83,3 |
| RS massa RDO+RPU (IN028 / IRS1004) | 556 | 86,2 | 616 | 95,5 | 537 | 83,3 |
| RS massa RDO atendida (IN022 / IRS1005) | 213 | 33,0 | 616 | 95,5 | 207 | 32,1 |
| RS seletiva porta a porta (IN030 / IRS0006) | 299 | 46,4 | 616 | 95,5 | 289 | 44,8 |

Origem da ausência **[CALC]**: 2019 — os 17 municípios sem dado AE (Aramina, Ariranha, Boa Esperança do Sul, Borebi, Canitar, Cedral, Dumont, Ibitinga, Júlio Mesquita, Monte Castelo, Nova Castilho, Pacaembu, Paraíso, São João de Iracema, Tejupá, Uchoa, Vera Cruz — lista do projeto, **confirmada**: 645−628=17) e 89 sem resposta em RS. 2024 — 16 municípios ausentes da base de água (Bady Bassitt, Boa Esperança do Sul, Cajobi, Canitar, Colina, Dumont, Guapiaçu, Igaraçu do Tietê, Lindóia, Monte Castelo, Morro Agudo, Motuca, Nantes, Nova Castilho, Pompéia, Tambaú) e 21 da de esgoto; nenhum dos ausentes de esgoto 2024 é SABESP (todos os 371 SABESP têm IES0001); a falta se concentra em prestadores locais (20 de 225 LPU).

---

## 7. Comparação das matrizes **[CALC]**

Municípios completos = valor não-nulo em **todas** as variáveis, nos dois anos.

| Matriz | Variáveis | k | 2019 | 2024 | **Ambos** |
|---|---|---|---|---|---|
| **A2** — só atendimentos | atend. água, atend. esgoto | 2 | 628 | 618 | **607** |
| **C** — reduzida (maior cobertura) | atend. água, atend. esgoto, perdas | 3 | 628 | 618 | **607** |
| **A4** — água + esgoto | + trat. do coletado | 4 | 628 | 618 | **607** |
| B-cob | C + cob. RS | 4 | 551 | 599 | 521 |
| B5 | C + cob. RS + massa RS | 5 | 551 | 599 | 521 |
| B6 | A4 + cob. RS + massa RS | 6 | 551 | 599 | 521 |

- Somar perdas e tratamento **não custa nenhum município** (o gargalo é `IES0001` 2024 e a ausência SNIS 2019). Resíduos custa **86** (607→521; −14%).
- **Quem cai por causa de resíduos:** 61 de ≤20 mil (16,8% dessa faixa), 13 de 20–49 mil, 9 de 50–99 mil, 3 de 100–249 mil, e **nenhum** acima de 250 mil. Cobertura da amostra por faixa: A4 = 92,8% / 94,8% / 96,6% / 95,7% / 100% / 100% / 100%; B5 = 77,2% / 83,6% / 81,0% / 89,1% / 100% / 100% / 100%. **[INF]** A perda é **não aleatória em relação ao porte** — justamente a variável de interesse do artigo. Mediana populacional dos ausentes em RS 2019 = 10,1 mil × 14,5 mil dos presentes.
- **Redundância e distribuição (A4, amostra de 607) [CALC]:** VIF 3,2 / 1,08 / 3,2 / 1,07 (2019) e 3,3 / 1,05 / 3,3 / 1,05 (2024) — só o par atend. água/esgoto é colinear (ρ Spearman 0,82 e 0,78; Pearson 0,81 e 0,83); os autovalores (1,8 / 1,2 / 0,8 / 0,17) mostram **3 dimensões efetivas**; `perdas` e `trat. esgoto` são quase ortogonais às demais (|ρ|≤0,24). Assimetria: atend. água −1,6/−1,8; esgoto trat. −2,3/−2,7 (72–78% no teto, 43/22 zeros); perdas +0,7/+1,4.

---

## 8. Variáveis recomendadas **[REC]**

| Variável | Código 2019 → 2024 | Fonte | Definição | Cobertura (ambos) | Justificativa |
|---|---|---|---|---|---|
| Atendimento de água | IN055 → IAG0001 | SNIS-AE 2019 / SINISA 2024 água | % da pop. total atendida por rede de água | 614 (95,2%) | 🟢 correspondência documentada; alta cobertura; ρ 0,63; variância suficiente |
| Atendimento de esgoto | IN056 → IES0001 | SNIS-AE / SINISA esgoto | % da pop. total atendida por rede coletora | 607 (94,1%) | 🟢; **é o eixo que mais discrimina** (mediana 88, cauda até 12–17%) |
| Tratamento do esgoto coletado | IN016 → IES2004 | SNIS-AE / SINISA esgoto | tratado ÷ coletado | 610 (94,6%) | 🟢 dimensão quase independente (VIF 1,07); tratar >100 (Vinhedo) |
| Perdas na distribuição | IN049 → IAG2013 | SNIS-AE / SINISA água | % de perdas do volume de entrada | 617 (95,7%) | 🟡 única com variância real e independente do acesso; comparação temporal com **ressalva de fórmula**; testar sensibilidade sem ela (Matriz A2) |

---

## 9. Variáveis descartadas

| Variável | Motivo (evidência) |
|---|---|
| IN046 ↔ IES2003 | 🔴; 179 valores >100, máx. 2.898%; depende de água consumida; média 76→91 |
| IN023 ↔ IAG0002 | Teto em 65–69%, ρ 0,32; redundante com o total urbano+rural |
| IN015(RS) ↔ IRS0001 | 🟡 fraca: teto 25%→52%, ρ 0,35, 86% de cobertura em 2019 e perda seletiva por porte. **Reservada como análise de sensibilidade/descritiva**, não entra no espaço de clusterização |
| IN016(RS) ↔ IRS0002 | 🔴 sem variância (84–90% no teto), ρ 0,09 |
| IN028 ↔ IRS1004 | 🔴 denominador muda (pop. atendida × total residente); ρ 0,18; SJC = 12,4; 86,2% de cobertura em 2019 |
| IN022 ↔ IRS1005 | Construto melhor alinhado, mas 33% de cobertura em 2019 |
| IN030 ↔ IRS0006 | 46% em 2019; vazio (2019) × zero (2024) |
| IAG0004/0005/0006–0012 | Sem par SNIS 2019; 66–75% de cobertura em 2024 |
| Indicadores financeiros/operacionais (IN003…IN085, IFA/IFE) | Fora do escopo "acesso e desempenho de saneamento"; não são verificados aqui indicador a indicador |
| Índices compostos do IAS (coleta c/ e s/ tratamento, individual, sem atendimento) | **Composição verdadeira** (soma 100 em 645/645; zeros em 61/455/81/91), mas **fonte e ano não identificados no CSV** e **não coincidem** com IES0001 (ρ 0,60; diferença mediana 4,7 p.p.); só um ano → **não permite comparação 2019×2024**. Ver §11 |

---

## 10. Recomendação da matriz final **[REC]**

**Matriz A4 — água + esgoto (4 indicadores): atendimento de água, perdas, atendimento de esgoto e tratamento do esgoto coletado; N = 607 municípios (94,1%) nos dois anos.**

Argumentos além do número de municípios:
1. **Comparabilidade**: 3 dos 4 pares são 🟢 e 1 é 🟡 (perdas). Em resíduos, nenhum par é 🟢: 2 são 🟡 (cobertura total, com o teto dobrando; e massa RDO, esta com só 33% de cobertura em 2019) e 3 são 🔴. Colocar resíduos na matriz **importaria para o resultado a mudança SNIS→SINISA**, e o artigo passaria a medir método, não território.
2. **Viés por porte**: resíduos elimina municípios quase só ≤100 mil — a variável central do trabalho. Sem resíduos, a taxa de inclusão varia pouco entre faixas (93–100%).
3. **Custo temático (honesto)**: o escopo "saneamento" na Lei 11.445 inclui resíduos, drenagem e águas pluviais. A matriz A4 cobre água e esgoto; **o título e os objetivos devem dizer "abastecimento de água e esgotamento sanitário"** (ou "saneamento básico — água e esgoto"). Resíduos pode entrar como (i) **análise de sensibilidade** (matriz B-cob, N = 521) e (ii) **descrição a posteriori dos clusters** com IRS0001/IRS1004 de 2024 (616 respondentes), sem entrar na distância.
4. **Dimensionalidade**: 3 eixos efetivos em 4 variáveis é saudável para K-means/Ward/GMM (sem colinearidade extrema).

**Ressalvas que dependem de confirmação do grupo:** (a) manter `perdas` (🟡) ou rodar A2/C como controle; (b) tratamento de Vinhedo (>100) e dos 11 zeros de perdas 2019; (c) se aceitam reduzir o escopo temático.

---

## 11. Pré-processamento recomendado

| Tema | Recomendação **[REC]** | Base |
|---|---|---|
| **Missing** | Caso completo na análise principal (N=607). **Sem imputação.** Registrar os 38 excluídos e seu motivo (ausente da base × "não calculado" × não respondente). Sensibilidade: clusterização por ano isolado (2019: 628; 2024: 618) | Os excluídos são menores (mediana 10,0 mil × 14,0 mil): 28 em ≤20 mil, 6 em 20–49 mil, 2, 2 acima; **declarar como limitação** (MNAR provável **[INF]**) |
| **Zeros** | Manter zeros de tratamento (reais). Marcar os 11 zeros de perdas 2019 como *suspeitos* e testar com/sem (sensibilidade). **Não** converter missing em zero; **não** usar zero-replacement (só seria necessário com CLR) | [CALC] tratamento=0 com coleta >0; perdas=0 com IN051=0 |
| **Valores >100** | Vinhedo (IES2004 = 129,4): impossível físico → marcar e testar (NaN × truncar em 100); decisão registrada | [CALC] |
| **Outliers** | **Não remover.** Diagnóstico: perdas ≥85% em 6 municípios pequenos de 2024 (Analândia, Brodowski, Guarantã, Paulicéia, Sto. Antônio do Aracanguá, Monte Alegre do Sul) — **[INF]** possível erro/perímetro do prestador **ou** perda real; verificar `GTA1001/GTA1211` nas planilhas de Informações. Tetos 0/100 são **característica real** (censura), não erro | [CALC] |
| **Transformação** | Manter escala nativa 0–100 (as 4 já estão em %). Testar 3 pipelines e medir ARI entre eles: (1) z-score; (2) escalonamento robusto (mediana/IQR); (3) z-score + log1p em perdas. Evitar logit (exige épsilon arbitrário em 0/100) e ranking (apaga a massa no teto) | [INF] |
| **Padronização** | **Um único escalonador ajustado no empilhado 2019+2024** (mesmo espaço) — condição para comparar clusters entre anos | [INF] |
| **CLR?** | **Não.** Um CLR é adequado para *partes de um todo* (soma constante) com dependência composicional. As 4 variáveis A4 **não somam 100**, não são partes de um mesmo total e são medidas em bases distintas (pop., volume). Zeros abundantes exigiriam substituição arbitrária. A única composição real no material (as 4 colunas do IAS, soma 100 em 645/645) não é SNIS/SINISA, tem fonte/ano não rastreados e existe em um só corte | [CALC]+[INF] |

---

## 12. Estratégia de clusterização (executar só após confirmação da matriz)

- **Mesma matriz, mesma escala, mesmas sementes** para os três algoritmos.
- **K-means**: k = 2…10, `n_init` ≥ 50, sementes fixas. **Ward** (distância euclidiana, mesma matriz). **GMM**: k = 1…10, covariâncias `full/tied/diag/spherical`, BIC/AIC; atenção a componentes degenerados nas massas em 0/100.
- **Escolha de k**: Silhouette, Calinski–Harabasz, Davies–Bouldin (curva completa), **estabilidade** por *bootstrap* (ARI entre reamostras) e por semente; BIC/AIC no GMM; **ARI/AMI entre algoritmos** no mesmo k. Reportar a curva inteira, não só o máximo. O critério é combinado com interpretabilidade e tamanho mínimo de cluster; nenhum k é fixado *a priori*.
- Rodar **por ano isolado** e **no empilhado** (ver §12b).

### 12b. Como comparar 2019 × 2024 (rótulos não são equivalentes)
| Alternativa | Como | Vantagem | Risco |
|---|---|---|---|
| **1. Ajuste independente por ano + alinhamento** | Clusterizar cada ano; casar clusters por distância de centroides (húngaro) em unidades originais; matriz de transição | Respeita "dois cortes independentes" | Os clusters podem não ser equivalentes; alinhamento é subjetivo |
| **2. Ajuste conjunto (empilhado, 2×607)** | Um só modelo, um só escalonador; cada município-ano é uma observação | **Perfis compartilhados**; transições legíveis | Observações repetidas (mesmo município) não independentes; pode "forçar" estrutura comum |
| **3. Modelo congelado** | Ajustar em 2019 e classificar 2024 com o mesmo modelo | Mede migração relativa a um padrão 2019 | Assimétrico; sensível a mudança de escala SNIS→SINISA |
| **4. Comparar estruturas** | ARI/AMI entre partições, comparação de centroides e de estabilidade | Não exige equivalência de rótulos | Descritivo |
| **5. Clusterizar Δ (variação)** | Espaço das diferenças 2024−2019 | Foca mudança | Diferenças de método pesam diretamente; ruído amplificado |

**[REC]** Fazer **1 e 2** (estrutura por ano + perfis comuns) e reportar **4**; usar **3** só como robustez. Registrar como limitação que 2019→2024 mistura mudança real e mudança de método SNIS→SINISA.

---

## 13. Porte populacional **[REC]**

- **Não entra como variável de clusterização.** Análise *a posteriori*: cruzar cluster × porte (tabela de contingência normalizada por linha e por coluna), **Cramér's V**, **NMI/ARI** cluster×porte, Kruskal–Wallis e Spearman de cada indicador com `log10(população)`. Isso evita contaminar a formação dos clusters.
- **Definição:** **[CALC]** a população do IAS é **idêntica ao DFE0001 do SINISA-RS 2024** (645/645; mediana da razão = 1,0) — portanto é uma população de **2024**, não de 2019. As faixas do IAS (≤20 mil, 20–50, 50–100, 100–250, 250–500, 500–1.000, >1.000 mil) têm 391/116/58/46/24/7/4 municípios (645); as três últimas são pequenas demais para testes. **[REC]** analisar 5 faixas: **≤20 mil, 20–50, 50–100, 100–250, >250 mil** — na amostra de 607: **363 / 110 / 56 / 44 / 34** — e manter `log10(pop)` como versão contínua. Cortes de 20/50/100 mil são usuais na literatura brasileira de porte municipal (**[INF]/conhecimento externo — o grupo deve citar a referência exata**).
- **Ponto aberto:** para 2019 usar a mesma população (2024) ou a de 2019 (`POP_TOT`, nas planilhas de Informações do SNIS, não usadas até aqui). Usar uma única referência evita que a mudança de faixa seja confundida com a de perfil; declarar a escolha.

---

## 14. Próximas etapas (após sua confirmação)

1. Você confirma (ou ajusta) a matriz **A4** e as ressalvas do §10 (perdas, Vinhedo, zeros de perdas, escopo água+esgoto).
2. Consolidar o repositório (`src/`, `data/raw`, `tests/`), corrigir P2, P4, P5, P10, P13, P14; adicionar população/porte e códigos de motivo de ausência ao painel; `assert` de unicidade.
3. Construir a base analítica (607 municípios × 4 variáveis × 2 anos + `porte`, `prestador`, `motivo_exclusao`).
4. EDA: histogramas, boxplots por ano e por porte, IQR/percentis, mapa de ausência.
5. Testar 3 pipelines de pré-processamento e medir sensibilidade (ARI).
6. Rodar K-means, Ward e GMM (curva de k, estabilidade, ARI entre algoritmos).
7. Interpretar clusters; cruzar com porte; comparar 2019×2024 (§12b).
8. Sensibilidades: A2/C (sem perdas), com/sem zeros suspeitos, com resíduos (B-cob, N=521), ano isolado.
9. Resultados preliminares → só depois, reescrever Título/Resumo, Metodologia, Introdução, Discussão e Conclusão no LaTeX com `\cite{}`.

---

### Resposta direta à pergunta central
> **Qual é a melhor matriz, comparável entre SNIS 2019 e SINISA 2024, para SP?**

**A4:** atendimento de água (IN055↔IAG0001), perdas (IN049↔IAG2013), atendimento de esgoto (IN056↔IES0001) e tratamento do esgoto coletado (IN016↔IES2004), com **607 municípios** nos dois anos. Resíduos fica de fora do espaço de clusterização porque nenhum par é comparável com segurança (denominador, universo e teto mudam), porque custa 86 municípios concentrados em municípios pequenos, e porque a mudança de método SNIS→SINISA passaria a dominar o resultado. É **recomendação metodológica**, não fato da base; depende de sua confirmação.
