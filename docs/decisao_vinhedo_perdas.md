# Decisão: Vinhedo (tratamento > 100%) e perdas zeradas em 2019

**Data:** 2026-10-24 · **Decisão do grupo** · **Matriz:** A4

| Problema | Decisão | Onde está no código |
|---|---|---|
| Vinhedo: tratamento do esgoto coletado (IES2004) = 129,42% em 2024 | **truncar em 100%** | `config.TRATAMENTOS["acima_100"] = "truncar"` |
| 11 municípios com perdas na distribuição (IN049) = 0% em 2019 | **retirar** os valores (os municípios saem dos casos completos) | `config.TRATAMENTOS["perdas_zero"] = "retirar"` |
| Variável perdas | **manter na matriz** (A4); a matriz sem perdas (A3) fica como análise de sensibilidade | `config.MATRIZ = "A4"` |

O tratamento é aplicado por `preprocess.tratar_valores()` antes do pré-processamento, em
`python -m src.preprocess` e `python -m src.clustering`. A análise exploratória (`src/eda.py`)
continua descrevendo os dados **brutos**, de propósito: é ela que mostra os problemas.

**Resultado:** a amostra principal passa de 607 para **597 municípios** (1.194 municípios-ano).

---

## 1. Como a decisão foi tomada

Código: [`src/cenarios.py`](../src/cenarios.py) (`python -m src.cenarios`, ~2,5 min).
Cópia das saídas usadas na decisão: [`docs/evidencias/cenarios/`](evidencias/cenarios/).

1. **Perfil dos casos** (`cenarios_perfil_casos.csv`): quem são os municípios afetados e o que os
   outros indicadores deles dizem.
2. **9 cenários** = 3 opções para Vinhedo (manter, truncar, retirar) × 3 para as perdas zeradas
   (manter, retirar, tirar a variável perdas). Cada cenário foi clusterizado com o método do
   trabalho (K-means, k escolhido pela maior silhueta média, k = 2..10) em **12 configurações de
   pré-processamento** (4 transformações × 3 escalas; casos completos; escala ajustada nos dois anos
   juntos), e comparado com o cenário "manter tudo" (`cenarios_resumo.csv`):
   - **ARI** entre as partições, nos municípios-ano em comum (1 = idênticas);
   - **% de municípios-ano que mudam de cluster**, com o mesmo k e os rótulos casados da melhor forma;
   - se o **k escolhido** muda.
3. **Verificação de cluster artificial** (`cenarios_cluster_artificial.csv`): onde os zeros de perdas
   caem na escala padronizada e se formam um grupo próprio.

**Critérios** (definidos antes de olhar os resultados):
- (a) o valor é fisicamente possível?
- (b) os outros dados do próprio município confirmam ou contradizem o valor?
- (c) quanto a decisão muda os agrupamentos?
- (d) quanto custa em municípios e se o custo cai sobre alguma faixa de porte.

---

## 2. Vinhedo → truncar em 100%

**Evidências**
- (a) **Impossível:** o indicador é a porcentagem do esgoto coletado que é tratada; não pode passar
  de 100%. É o único caso acima de 100% entre os oito indicadores da matriz.
- (b) Em 2019, o mesmo município tinha tratamento de 99,71%. Os demais indicadores de Vinhedo
  são normais (perdas de 33,6% em 2019 e 34,2% em 2024). O valor indica tratamento total, com erro
  de registro no numerador ou no denominador.
- (c) **A decisão quase não muda os agrupamentos.** Truncar ou retirar Vinhedo dá ARI ≥ 0,987 em
  relação a "manter" nas 12 configurações, com no máximo 0,5% dos municípios-ano mudando de
  cluster. O k só muda numa configuração (sem transformação, escala min-max: de 3 para 2), porque a
  escala min-max usa o valor máximo, e Vinhedo é o máximo. Com winsorização ou log, o valor já é
  limitado a 100 pelo próprio pré-processamento.
- (d) Truncar não exclui nenhum município; retirar excluiria um (79 mil habitantes).

**Por que truncar e não retirar:** os dois cenários dão o mesmo resultado (c), mas truncar mantém o
município na amostra e corrige o valor para o mais plausível (tratamento total, como em 2019).
**Por que não manter:** deixar um valor impossível na análise é difícil de justificar, e ele
distorce a escala min-max.

---

## 3. Perdas = 0% em 2019 → retirar os 10 municípios

**Evidências**
- (a) **Implausível:** perda zero significaria que todo o volume de água distribuído foi medido como
  consumido, sem vazamentos nem erros de medição, o que não ocorre em sistemas reais. A
  mediana estadual é de 24%.
- (b) **Os outros dados contradizem o zero:**
  - os 11 municípios têm também **perdas por ligação (IN051) = 0**, o que indica campos de volume
    não preenchidos, e não uma medição real;
  - em 2024, os mesmos municípios têm perdas **normais, de 5,2% a 47,4%**;
  - todos são prestadores locais de direito público (LPU), o que sugere um padrão de preenchimento.
- (c) **Os zeros podem criar um grupo artificial.** Na configuração de referência
  (winsor_log + robust) e em 10 das 12 configurações, retirá-los quase não muda nada (ARI ≥ 0,98).
  Mas com transformação log (ou winsor_log) + z-score:
  - os zeros viram os pontos mais extremos da variável (z = −4,6; mediana 0,13);
  - a silhueta escolhe k = 4, e **os 10 zeros caem todos no mesmo cluster pequeno**, de 52
    municípios-ano (19% dele são os zeros);
  - sem os zeros, esse cluster deixa de existir: k = 3, e 17% dos municípios-ano mudam de cluster
    (ARI 0,69).

  Ou seja, dependendo do pré-processamento, valores provavelmente errados chegam a formar um perfil.
- (d) **Custo pequeno:** a amostra cai de 607 para 597 municípios (−1,6%). Dos 10 excluídos, 8 têm
  até 20 mil habitantes e 2 têm de 20 a 50 mil. A cobertura da faixa de até 20 mil vai de 92,8% para
  90,8%, e as outras faixas mudam no máximo 1,7 ponto. Bady Bassitt, o 11º, já estava fora por não
  ter perdas em 2024.

**Por que retirar e não manter:** manter valores quase certamente errados, que em parte das
configurações formam um cluster próprio, é mais difícil de defender do que perder 10 municípios.
**Por que não substituir por outro valor** (ex.: o de 2024 ou a mediana): seria inventar um dado
de 2019, e a comparação entre anos é justamente o objeto do trabalho.

---

## 4. Variável perdas → manter na matriz

**Evidências**
- Tirar a variável (matriz A3) é o cenário que **mais muda os grupos**: ARI médio de 0,88, chegando
  a 0,46, com até 37% dos municípios-ano mudando de cluster (log + z-score). Então perdas carrega
  informação própria.
- Isso é coerente com a análise exploratória: perdas é quase independente das demais variáveis
  (|ρ| ≤ 0,24), ou seja, representa uma dimensão diferente, a **eficiência** do serviço, que nenhuma
  outra variável da matriz cobre.
- O ponto fraco da variável é a comparabilidade entre SNIS e SINISA: a correspondência é declarada
  no glossário, mas a composição dos volumes muda um pouco, e a correlação 2019×2024 é a menor das
  quatro (0,48). Isso é declarado como limitação no artigo.

**Decisão:** manter perdas na matriz principal, porque tirá-la eliminaria a dimensão de eficiência e
mudaria o que está sendo medido. A matriz A3 fica registrada como **análise de sensibilidade**, para
mostrar no artigo o que muda nos perfis sem perdas.

---

## 5. Limitações desta decisão

- Retirar os zeros supõe que são erro de preenchimento. A evidência (IN051 = 0 e valores normais em
  2024) é forte, mas não foi confirmada com os prestadores.
- A exclusão recai sobre municípios pequenos (8 de 10 com até 20 mil habitantes), ainda que com
  efeito pequeno na cobertura por porte.
- As comparações usam K-means com a silhueta. Se o grupo incluir Ward e GMM, vale rodar os cenários
  também com eles.

## 6. Como reproduzir

```bash
python -m src.cenarios      # evidências (outputs/resumo_cenarios.md, tabelas e figuras cenarios_*)
pytest                      # inclui testes que garantem que a decisão está aplicada (597 municípios)
python -m src.clustering    # clusterização já com os tratamentos
```

Para testar outra decisão, mude `TRATAMENTOS` em `src/config.py` e rode de novo.
