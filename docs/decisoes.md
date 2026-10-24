# Registro de decisões

Uma linha por decisão. Alimenta a seção de metodologia do artigo.

| Data | Autor | Decisão | Alternativas consideradas | Justificativa |
|---|---|---|---|---|
| 2026-09-27 | (preencher) | Chave de junção `cod_ibge7 // 10` | junção por nome do município | Códigos são únicos; nomes têm grafias diferentes |
| 2026-09-27 | (preencher) | Combinar prestadores de água e de esgoto de Mauá, Salto e Santa Maria da Serra numa linha | manter duplicado | Clusterização exige 1 linha por município |
| 2026-10-21 | Carol | **Matriz principal = A4**: atendimento de água (IN055↔IAG0001), perdas (IN049↔IAG2013), atendimento de esgoto (IN056↔IES0001), tratamento do esgoto coletado (IN016↔IES2004). N = 607 municípios completos nos dois anos. Definida em `src/config.py` (`MATRIZ = "A4"`) | R4 (água, esgoto, cobertura e massa de resíduos; N = 521) | Auditoria, §5–10: nenhum par de resíduos é comparável com segurança entre SNIS e SINISA (denominador, universo e teto mudam; massa per capita tem ρ = 0,18); R4 exclui 86 municípios, quase todos ≤ 100 mil hab., enviesando a análise por porte. A R4 continua em `config.MATRIZES` para análise de sensibilidade |
| 2026-10-21 | Carol | Escopo temático: "abastecimento de água e esgotamento sanitário" (resíduos só como sensibilidade e descrição a posteriori dos clusters) | manter "saneamento básico" completo | Consequência da matriz A4; título e objetivos devem refletir isso |
| 2026-10-21 | Carol | Porte **não entra** na clusterização; é cruzado a posteriori (cluster × faixa de porte). População do IAS (= DFE0001, ref. 2024) para os dois anos. Faixas: até 20 mil, 20–50, 50–100, 100–250, mais de 250 mil (391 / 116 / 58 / 46 / 34 municípios) | porte como variável de clusterização; população de 2019 para 2019 | Evita que o porte determine os grupos; uma única referência populacional evita confundir mudança de faixa com mudança de perfil. **Pendente:** citar a referência bibliográfica das faixas |
| | | Vinhedo: `IES2004` = 129,42% em 2024 (fisicamente impossível) | NaN × truncar em 100 | *pendente* (hoje o log trunca em 100; winsor/escala usam o valor bruto) |
| | | 11 municípios com perdas = 0 em 2019 (todos LPU; suspeita de dado inconsistente) | manter × NaN × sensibilidade com/sem | *pendente* |
| | | Regra de inclusão (casos completos × imputação) | | *pendente*. Obs.: na A4 a imputação (`min_obs=3`) não imputa nenhuma célula, então equivale a `completos_ano` (639 mun.) |
| | | Transformação e padronização | | *pendente* (ver `outputs/resumo_preproc.md`: transformação e escala são as decisões que mais mudam a partição) |
| 2026-10-24 | Carol | Algoritmo: **K-means** (n_init = 50, random_state = 42); k escolhido pelo **Método da Silhueta** (maior silhueta média sobre todas as instâncias, grade k = 2..10; empate → menor k). 2019 e 2024 clusterizados juntos no mesmo espaço | outros algoritmos (Ward, GMM); outros critérios de k | Definido pelo grupo |
| | | Configuração de pré-processamento usada na clusterização | | *pendente*. O k* muda com ela (completos_ambos, conjunto): sem transformação ou só winsor → k = 3 nas 3 escalas; log/winsor_log → k = 2 (robust), 3 (minmax), 4 (zscore). A referência provisória (winsor_log + robust) dá k = 2 |
