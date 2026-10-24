# Comparação: k = 2 (Método da Silhueta) × k = 3 (Método do Cotovelo)

**Data:** 2026-10-24 · **Status:** **decidido — usar somente k = 3** (k = 2 descartado pelo critério multivariado; ver `docs/decisoes.md`). Este documento registra a comparação que fundamentou a decisão.

- **Código:** [`src/comparar_k.py`](../src/comparar_k.py) (`python -m src.comparar_k`, cerca de 1 minuto).
- **Saídas usadas:** [`docs/evidencias/comparar_k/`](evidencias/comparar_k/).
- **Dados:** matriz A4, 597 municípios × 2 anos = 1.194 instâncias, pré-processamento de referência
  (`winsor_log + robust`, escala ajustada nos dois anos juntos), tratamentos de
  `docs/decisao_vinhedo_perdas.md`.

## 1. Resumo

| Critério | k = 2 | k = 3 | Favorece |
|---|---|---|---|
| Silhueta média | **0,476** | 0,367 | k = 2 |
| % de instâncias com silhueta negativa | **0,5%** | 2,4% | k = 2 |
| Estabilidade (bootstrap, 200 reamostragens): ARI médio | **0,989** | 0,944 | k = 2 (os dois são estáveis) |
| % de reamostragens com ARI ≥ 0,9 | **100%** | 88,5% | k = 2 |
| Menor cluster | 230 instâncias | 216 instâncias | empate (nenhum grupo pequeno demais) |
| A partição é reproduzida por uma regra numa única variável? | **sim**: "tratamento ≥ 95,7%" reproduz 99,2% (ARI 0,965) | não (ARI ≤ 0,41) | k = 3 |
| Usa mais de uma dimensão (acesso, tratamento, perdas)? | só tratamento | acesso **e** tratamento | k = 3 |
| Relação com o porte | moderada | **forte e graduada** | k = 3 |

## 2. Perfis (mediana [Q1–Q3], em %)

**k = 2**

| Cluster | Água | Perdas | Esgoto | Tratamento | Leitura |
|---|---|---|---|---|---|
| 1 (964) | 92,2 [82,4–98,3] | 21,8 [14,6–30,5] | 87,5 [73,1–95,5] | 100 [100–100] | trata todo o esgoto coletado |
| 2 (230) | 96,9 [89,0–99,9] | 33,2 [21,4–44,4] | 90,8 [78,6–97,4] | 54,9 [0,1–80,0] | tratamento parcial ou ausente, perdas maiores |

**k = 3**

| Cluster | Água | Perdas | Esgoto | Tratamento | Leitura |
|---|---|---|---|---|---|
| 1 (621) | 86,4 [75,1–91,6] | 21,7 [14,7–29,5] | 79,8 [61,8–87,5] | 100 [100–100] | trata tudo, mas com **acesso intermediário** à rede |
| 2 (357) | 99,7 [97,5–100] | 22,5 [14,5–34,3] | 97,9 [94,9–99,7] | 100 [100–100] | **acesso quase universal** e tratamento total |
| 3 (216) | 96,8 [89,0–99,7] | 33,8 [21,8–44,7] | 90,0 [78,7–97,1] | 51,4 [0–75,6] | bom acesso, **tratamento parcial ou ausente**, perdas maiores |

**As duas soluções são aninhadas.** O cluster de tratamento parcial praticamente se mantém (216 das 230
instâncias), e o cluster "trata tudo" de k = 2 se divide em dois, por nível de acesso. Ou seja, k = 3
acrescenta a dimensão de **acesso** à separação por **tratamento** que já existe em k = 2.

## 3. Relação com o porte (% de cada faixa em cada cluster)

| Porte | k=2: 1 | k=2: 2 | k=3: 1 (acesso interm.) | k=3: 2 (acesso universal) | k=3: 3 (trat. parcial) |
|---|---|---|---|---|---|
| até 20 mil | 90,0 | 10,0 | 66,5 | 24,2 | 9,3 |
| 20–50 mil | 75,9 | 24,1 | 41,7 | 36,1 | 22,2 |
| 50–100 mil | 66,1 | 33,9 | 32,1 | 36,6 | 31,2 |
| 100–250 mil | 62,5 | 37,5 | 19,3 | 44,3 | 36,4 |
| mais de 250 mil | 47,1 | 52,9 | 8,8 | 39,7 | 51,5 |

Em k = 3, o grupo de acesso intermediário cai de 66,5% entre os municípios de até 20 mil habitantes
para 8,8% acima de 250 mil. Em k = 2, essa diferença de acesso por porte fica escondida dentro do
cluster 1.

## 4. Leitura

- **Pelos critérios internos** (silhueta e estabilidade), k = 2 é melhor. A silhueta é a regra de
  decisão registrada.
- **Pela interpretação,** k = 2 equivale quase exatamente a "trata ≥ 95% do esgoto coletado?". Isso
  é uma classificação por um único indicador, que dispensaria a clusterização multivariada. k = 3
  combina acesso e tratamento, e a separação por acesso está ligada ao porte, que é uma das
  perguntas do trabalho.
- **k = 3 também é aceitável pelos critérios internos:** silhueta de 0,37 (estrutura fraca na escala de Kaufman e Rousseeuw, 1990, assim como o 0,48 de k = 2),
  estabilidade alta (ARI médio 0,94, acima de 0,9 em 88,5% das reamostragens) e nenhum grupo pequeno.

## 5. Opções para o grupo

1. **Manter a regra da silhueta (k = 2)** e apresentar k = 3 como análise complementar. É coerente com
   o que está registrado, mas o resultado principal fica próximo de uma classificação por tratamento.
2. **Adotar k = 3**, justificando com o cotovelo, a interpretabilidade, a estabilidade alta e a
   constatação de que k = 2 é reproduzido por uma única variável. Nesse caso, a regra de escolha
   precisa ser reescrita na metodologia: por exemplo, "silhueta e cotovelo como candidatos; escolha
   entre os candidatos pela estabilidade e pela plausibilidade dos perfis", e não apenas "maior
   silhueta".
3. **Apresentar as duas soluções** como níveis de detalhe (a hierarquia é limpa), com k = 3 como
   principal para a discussão por porte.

Qualquer que seja a escolha, ela deve ser registrada em `docs/decisoes.md` **antes** de interpretar os
resultados por porte e por ano no texto.

## 6. Como reproduzir

```bash
python -m src.clustering                 # silhueta (k = 2) e cotovelo (k = 3)
python -m src.comparar_k                 # esta comparação
python -m src.comparar_k --ks 2,3,4      # incluir outros k
```
