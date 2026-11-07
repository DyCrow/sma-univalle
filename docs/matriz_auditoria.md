# Matriz de Auditoría y Control de Testeo (Fase 4)

_Generada automáticamente por `tests/run_tests.py` el 2026-11-07 11:27. Huella prompts: `a45d5620b6f0d837`._

## 1. Registro de fallas detectadas y ajustes aplicados

Cada fila es una falla **real** observada durante las pruebas (primera ejecución), el ajuste aplicado y la **re-verificación automática** de la prueba que la cubre.

| # | Dataset de prueba | Agente auditado | Esperado vs. Obtenido (primera ejecución) | Ajuste aplicado | Regla de prompt | Re-verificación |
|---|---|---|---|---|---|---|
| F-01 | G · muestra diminuta | Agente 1 (Auditor) | **Esperado:** Columna 'region' con valores N/S clasificada como categoría.<br>**Obtenido:** tipo = booleano (las letras sueltas N/S se leyeron como Sí/No). | Vocabulario booleano sin letras sueltas; el Agente 1 solo acepta pares semánticos explícitos. | AJ-01 (R4 del Auditor) | ✅ G-01 |
| F-02 | D · producción JSON | Agente 1 (Auditor) | **Esperado:** 'operario_antiguedad_anios' = medida (duración).<br>**Obtenido:** rol = dimensión: la subcadena 'anio' se interpretó como calendario. | Las pistas de calendario (año, mes, semana…) se buscan por token exacto, no por subcadena. | AJ-02 (R5 del Auditor) | ✅ D-02 |
| F-03 | F · base sorpresa sin encabezado | Agente 2 (Analista) | **Esperado:** Medida principal = costo de la atención (columna_8).<br>**Obtenido:** columna_5 (edad del paciente) por orden de aparición. | Con nombres no informativos se elige la variable aditiva de mayor magnitud acumulada y se declara la limitación en el informe. | AJ-03 (R7 del Analista) | ✅ F-03, F-05 |
| F-04 | A · ventas | Agente 2 (Analista) | **Esperado:** Variación '-11,8%' reconocida como cifra verificada (hecho: -11,75).<br>**Obtenido:** Marcada '[cifra no verificada]': diferencia 0,05000000000000071 > tolerancia 0,05 (error de punto flotante en el redondeo). | Tolerancia del guardrail = redondeo de impresión + 0,0051 (redondeo de los hechos a 2 decimales). | — (guardrail de código) | ✅ A-08 |
| F-05 | A · ventas | Agente 4 (Informe) | **Esperado:** Plazos de recomendaciones ('60-90 días') no tratados como afirmaciones sobre los datos.<br>**Obtenido:** '90' marcado como cifra no verificada en 4 lugares. | Los campos 'plazo' (compromisos de plan, no hechos) se excluyen del escrutinio numérico. | — (guardrail de código) | ✅ A-09 |
| F-06 | A · ventas | Agente 2 (Analista) | **Esperado:** Dimensión principal de gestión (sucursal) priorizada.<br>**Obtenido:** 'medio_pago' ocupaba el primer lugar por tener menos categorías, y el primer hallazgo trataba del método de pago. | Las dimensiones se ordenan por la posición de su pista de gestión (sucursal, región, categoría… antes que medio/canal) y luego por cardinalidad. | — (herramienta de selección) | ✅ A-11 |
| F-07 | A · ventas (y C, E) | Agente 3 (Intérprete) | **Esperado:** Hallazgo de concentración sin redundancia.<br>**Obtenido:** 'Centro concentra 30,4%… El 20% superior aporta 30,4%': con 5 categorías el 20% superior es la categoría líder (misma cifra duplicada). | La métrica de Pareto solo se emite con ≥10 categorías. | — (herramienta de cómputo) | ✅ A-12 |
| F-08 | D · producción JSON | Agente 3 (Intérprete) | **Esperado:** 'cayó 15,2%' verificado contra el hecho -15,2.<br>**Obtenido:** 'cayó [cifra no verificada]': el texto cita la magnitud (positiva) y el hecho es negativo. | La lista blanca incluye valores absolutos; el sentido lo da el verbo y se verifica la magnitud. | — (guardrail de código) | ✅ D-04 |
| F-09 | B · PQR texto libre | Agente 2 (Analista) | **Esperado:** Exactitud de sentimiento ≥ 85% y % negativo ≈ real (62,3%).<br>**Obtenido:** Exactitud 82,8% y 52,85% negativos: omitía 'retrasó', 'incompleto', 'cobraron/exijo/reembolso'; trataba 'mejor/mejorar' de las sugerencias como positivo. | Léxico ampliado con vocabulario general de reclamo; 'mejor/mejorar' excluido del léxico positivo. | AJ-04 (R8 del Analista) | ✅ B-03, B-04 |
| F-10 | B · PQR texto libre | Agente 4 (Informe) | **Esperado:** 'Calidad 96/100' aceptado.<br>**Obtenido:** '100' (denominador de la escala) marcado como cifra no verificada. | El guardrail ignora denominadores de escala (token precedido por '/'). | — (guardrail de código) | ✅ B-08 |
| F-11 | Sonda B + LLM simulado | Agente 1 (Auditor) | **Esperado:** Rechazar la propuesta del LLM de usar 'canal' (texto) como medida.<br>**Obtenido:** Rol 'medida' aceptado sin validar el tipo → excepción 'could not convert string to float' en el cómputo y caída de toda la cadena. | Matriz de compatibilidad tipo↔rol en la validación; el cómputo además filtra por dtype numérico (defensa en profundidad). | — (validador de esquema) | ✅ I-07 |
| F-12 | A · ventas | Agente 5 (Consejero) | **Esperado:** 'Voy a cerrar la sucursal Centro, vende poco.' enlaza la entidad 'Centro' y muestra su 30% de las ventas en contra.<br>**Obtenido:** Entidad no encontrada (la coma pegada, 'centro,', impedía la coincidencia); la respuesta citaba un hallazgo genérico. | Normalización de frases sin puntuación interna (norm_text) para el enlace de entidades. | — (señales del consejero) | ✅ H-04 |
| F-13 | B · PQR texto libre | Agente 5 (Consejero) | **Esperado:** Rol 'director de servicio al ciudadano' → lente de servicio.<br>**Obtenido:** Lente 'educación': la palabra 'rector' coincidió dentro de 'di-rector'. | Coincidencia de palabras clave por inicio de palabra (\b) y se añade 'ciudadan' al lente de servicio. | — (señales del consejero) | ✅ H-05 |
| F-14 | F · base hospitalaria | Agente 5 (Consejero) | **Esperado:** Detectar evidencia anecdótica ('un médico me dijo') y optimismo ('no tiene riesgos').<br>**Obtenido:** Solo detectó 'Exceso de certeza'. | Patrones generalizados: 'me dijo/comentó/contó…' y 'no tiene/habrá riesgos'. | — (léxico de sesgos) | ✅ H-07 |
| F-15 | D · producción JSON | Agente 5 (Consejero) | **Esperado:** '¿Qué máquina tiene más defectos?' responde con M-03.<br>**Obtenido:** Respondió con otra agrupación ('En turno, lidera Tarde en unidades producidas'): no vinculaba palabras de la pregunta con columnas. | Vinculación pregunta↔columnas por raíz de 5 letras y precálculo de la agrupación pedida (sin reglas por dominio). | — (señales del consejero) | ✅ H-08 |
| F-16 | Todos | Agente 5 (Consejero) | **Esperado:** Memorandos del consejero sin cifras 'no verificadas'.<br>**Obtenido:** '1,5' (multiplicador del umbral de reversión), '100' (cita del usuario) y '90 días' (plantilla) marcados como no verificados en los 11 memorandos de la batería. | El multiplicador entra como constante en las señales; las plantillas evitan cifras que no sean datos. | — (señales del consejero) | ✅ H-14 |
| F-17 | Sonda B + LLM simulado | Agente 2 (Analista) | **Esperado:** Si el LLM inventa estadísticos, variables o refs, el sistema corrige.<br>**Obtenido:** Falla inducida: media=999,99, variable fantasma, ref inexistente y 9 categorías cualitativas. | Guardrail: sobrescribe con el valor medido, descarta variables/refs inexistentes y recorta a 5 categorías. | AJ-05 (R4 del Analista) | ✅ I-03 |
| F-18 | Sonda B + LLM simulado | Agente 3 (Intérprete) | **Esperado:** Cero alucinaciones de cifras y alertas de nulos completas.<br>**Obtenido:** Falla inducida: '87,5%' y '12.345.678' inventados, hallazgo sin evidencia y alertas de nulos omitidas. | Enmascarado de cifras no verificadas, descarte de hallazgos sin 'ref' y restitución de alertas de nulos como N/A. | AJ-06 (R2 del Intérprete) | ✅ I-04, I-05 |
| F-19 | Sonda B + LLM simulado | Agente 4 (Informe) | **Esperado:** Resumen ≤120 palabras y solo gráficos válidos.<br>**Obtenido:** Falla inducida: resumen de 200 palabras, gráfico con columna inexistente y tipo 'radar' no permitido. | Recorte a 120 palabras y descarte de directivas de visualización inválidas. | AJ-07 (R3 del Informe) | ✅ I-06 |
| F-20 | H · recursos humanos (base inédita) | Agente 5 (Consejero) | **Esperado:** Ante «voy a congelar los aumentos en Soporte porque seguro es el clima, un jefe me dijo…» (2 sesgos), no avalar la decisión sin condiciones.<br>**Obtenido:** postura = 'proceder', confianza 'alta', pese a 2 sesgos detectados y 3 objeciones. | 'Proceder' a secas pasa a ser excepcional (sin sesgos, sin objeciones y con evidencia a favor); la confianza 'alta' exige ausencia de sesgos. | AJ-08 (R8 del Consejero) | ✅ H-15 |
| F-21 | H · recursos humanos (base inédita) | Agente 3 (Intérprete) | **Esperado:** Hallazgo sobre la tasa de renuncia (columna Sí/No) por cargo, con Soporte como el más alto.<br>**Obtenido:** Los indicadores binarios no se analizaban: ningún hallazgo sobre renuncia; el consejero no podía confrontar la decisión con ese dato. | Nueva herramienta: tasa del estado positivo de cada indicador binario por dimensión (hechos 'indicadores'), usada por el Intérprete y por el Consejero para cuestionar la medida frente al indicador crítico. | — (herramienta de cómputo) | ✅ K-02, H-15 |
| F-22 | H · recursos humanos (base inédita) | Agente 3 (Intérprete) | **Esperado:** Una serie por fecha de ingreso (~9 registros/mes) no se presenta como tendencia.<br>**Obtenido:** «Salario mensual cayó 19,7% en el último periodo completo» presentado como hallazgo de dinámica temporal (ruido muestral). | El cómputo reporta registros por periodo y confiabilidad (≥20 en los dos últimos periodos); si no, el hallazgo se marca 'no concluyente' con impacto bajo. | AJ-09 (R6 del Intérprete) | ✅ K-03 |
| F-23 | I · una sola columna de texto | Agente 1 (Limpiador) | **Esperado:** Archivo de una columna con comas dentro de los comentarios: 1 columna.<br>**Obtenido:** Delimitador ',' inventado: 2 columnas ('muy_mala_la_atencion', 'nunca_responden') y encabezado perdido. | El delimitador solo se acepta si el encabezado también lo contiene; por defecto se asume una sola columna. | — (herramienta de ingesta) | ✅ K-04 |
| F-24 | I · una sola columna de texto | Agente 1 (Limpiador) | **Esperado:** Conservar los 80 comentarios (varias personas escriben lo mismo).<br>**Obtenido:** 80 → 33 filas: se eliminaron como 'duplicados' comentarios legítimos idénticos. | Los duplicados exactos solo se eliminan con identificador (o ≥5 columnas con fecha); si no, se reportan y se conservan. | AJ-10 (R8 del Auditor) | ✅ K-04, C-03 |
| F-25 | A · ventas (interfaz del Simulador) | Agente 6 (Simulador) · UI | **Esperado:** Al responder un emparejamiento, el contador «N de 8 respondidas» se actualiza sin alterar otros textos.<br>**Obtenido:** Verificado en el navegador: el contador se escribía en el primer elemento con clase 'hint', que era el resumen «Datos clave y supuestos del ejercicio» (mostraba «1 de 8 respondidas» ahí) mientras el contador real seguía en 0. | El contador recibe su propio id (#sim-count) y el selector deja de depender de una clase compartida. | — (interfaz) | ✅ L-09 |
| F-26 | A · ventas (95/100 de calidad) | Agente 6 (Simulador) | **Esperado:** Las causas de crisis del emparejamiento son coherentes con los datos.<br>**Obtenido:** Planteaba «Datos con vacíos (calidad 95/100)» como causa de la crisis, algo que los datos desmienten. | La causa de calidad solo aparece si el puntaje es < 85; con calidad alta se sustituye por «decisiones sin métrica de seguimiento». | AJ-11 (R8 del Simulador) | ✅ L-10 |

**Fallas registradas: 26** · todas con re-verificación: 26/26 aprobadas.

## 2. Resultados de la batería completa (estado actual)

| ID | Dataset | Agente auditado | Resultado esperado | Estado |
|---|---|---|---|---|
| A-01 | A | Agente 1 (Limpiador) | Fechas en 2 formatos (ISO y DD/MM/AAAA) estandarizadas a AAAA-MM-DD, idénticas a la verdad de terreno en el 100% de las filas | ✅ PASA |
| A-02 | A | Agente 1 (Limpiador) | Suma de 'total' idéntica a la verdad de terreno | ✅ PASA |
| A-03 | A | Agente 2 (Analista) | Identifica la sucursal y la categoría líderes en ventas | ✅ PASA |
| A-04 | A | Agente 2 (Analista) | Detecta las 3 transacciones atípicas plantadas (x40) | ✅ PASA |
| A-05 | A | Agente 2 (Analista) | Mes pico de ventas = 2024-12 | ✅ PASA |
| A-06 | A | Agente 2 (Analista) | Descubre la relación aritmética total ≈ cantidad × precio × (1 − descuento) sin conocerla de antemano | ✅ PASA |
| A-07 | A | Agente 2 (Analista) | Máximo 5 categorías con frecuencia numérica explícita (n y %) | ✅ PASA |
| A-08 | A | Agente 3 (Intérprete) | Dominio comercial inferido y 0 cifras no verificadas en toda la cadena | ✅ PASA |
| A-09 | A | Agente 4 (Informe) | Resumen ≤120 palabras, ≥4 gráficos renderizados y sin marcas de cifra no verificada | ✅ PASA |
| A-11 | A | Agente 2 (Analista) | La primera dimensión analizada es de gestión (sucursal), no el método de pago | ✅ PASA |
| A-12 | A | Agente 3 (Intérprete) | Sin redundancias: con <10 categorías no repite el '20% superior' como segunda cifra de concentración | ✅ PASA |
| A-10 | A | Agente 4 (Informe) | Recomendaciones priorizadas, sin duplicados | ✅ PASA |
| B-01 | B | Agente 1 (Limpiador) | Variantes de escritura (queja/QUEJA/'Queja '/Quejá…) unificadas en 4 tipos de solicitud | ✅ PASA |
| B-02 | B | Agente 1 (Limpiador) | Detecta 'descripcion' como texto libre y 'dias_respuesta' como medida con nulos reportados como N/A (sin imputar) | ✅ PASA |
| B-03 | B | Agente 2 (Analista) | Exactitud del sentimiento ≥ 85% frente a las etiquetas reales | ✅ PASA |
| B-04 | B | Agente 2 (Analista) | % de mensajes negativos dentro de ±8 puntos de la realidad | ✅ PASA |
| B-05 | B | Agente 2 (Analista) | Salida cualitativa concisa: ≤5 categorías y ≤5 temas con frecuencia numérica | ✅ PASA |
| B-06 | B | Agente 3 (Intérprete) | Área con más insatisfacción = Soporte técnico | ✅ PASA |
| B-07 | B | Agente 3 (Intérprete) | Área más lenta en responder = Logística | ✅ PASA |
| B-08 | B | Agente 3 (Intérprete) | Dominio PQR inferido y 0 cifras no verificadas | ✅ PASA |
| B-09 | B | Agente 4 (Informe) | Gráficos de sentimiento y temas generados | ✅ PASA |
| C-01 | C | Agente 1 (Auditor) | % de nulos reportado por columna dentro de ±1,5 puntos del inyectado (incluye marcadores N/A, -, ?, 'sin dato', NULL) | ✅ PASA |
| C-02 | C | Agente 1 (Auditor) | Columnas sin nombre ('', 'Unnamed: 12') nombradas sin perder datos | ✅ PASA |
| C-03 | C | Agente 1 (Limpiador) | 60 duplicados exactos detectados y eliminados | ✅ PASA |
| C-04 | C | Agente 1 (Limpiador) | 4 formatos de fecha mixtos (incl. '5 de marzo de 2024') unificados con ≥99% de parseo | ✅ PASA |
| C-05 | C | Agente 1 (Limpiador) | Importes con '$', miles con punto y ',00' normalizados: suma idéntica a la original | ✅ PASA |
| C-06 | C | Agente 1 (Limpiador) | Variantes 'NORTE'/'norte ' unificadas: sucursal ≤ 5 categorías | ✅ PASA |
| C-07 | C | Agente 1 (Auditor) | Reporta negativos incoherentes, nulos ocultos, formato mixto, duplicados y columnas sin nombre | ✅ PASA |
| C-08 | C | Agente 1 (Auditor) | Puntaje de calidad bajo (<75) y menor que el de la base limpia (A) | ✅ PASA |
| C-09 | C | Agente 3 (Intérprete) | Alerta de datos faltantes por cada columna con ≥5% de nulos, sin imputar valores | ✅ PASA |
| C-10 | C | Agente 3 (Intérprete) | Nulos no imputados: los nulos de 'cantidad' siguen siendo nulos (≈ inyectados) | ✅ PASA |
| C-11 | C | Agente 3 (Intérprete) | 0 alucinaciones de cifras en el informe de la base ruidosa | ✅ PASA |
| C-12 | C | Agente 4 (Informe) | El informe declara explícitamente la baja calidad y las limitaciones | ✅ PASA |
| D-01 | D | Agente 1 (Limpiador) | Aplana el JSON anidado y ubica los registros bajo 'registros' (1500 filas, columnas orden_planta, operario_nombre…) | ✅ PASA |
| D-02 | D | Agente 1 (Auditor) | 'operario_antiguedad_anios' es una MEDIDA (duración), no una dimensión de calendario | ✅ PASA |
| D-03 | D | Agente 2 (Analista) | Identifica la máquina con más unidades defectuosas (M-03) | ✅ PASA |
| D-04 | D | Agente 3 (Intérprete) | Dominio 'producción' inferido sin que ningún prompt lo mencione; sin '[cifra no verificada]' en los hallazgos | ✅ PASA |
| E-01 | E | Agente 1 (Limpiador) | Omite la fila de título, elige la hoja principal y lee 48 filas × 8 columnas | ✅ PASA |
| E-02 | E | Agente 1 (Limpiador) | Porcentajes con coma decimal y signo % ('12,5%') convertidos a número (pobreza media entre 10 y 60) | ✅ PASA |
| E-03 | E | Agente 3 (Intérprete) | Dominio social/territorial inferido | ✅ PASA |
| E-04 | E | Agente 1 (Auditor) | 'ano' tratado como dimensión de periodo (código numérico), no como medida | ✅ PASA |
| F-01 | F | Agente 1 (Limpiador) | Detecta ausencia de encabezado, codificación cp1252 y delimitador ';' | ✅ PASA |
| F-02 | F | Agente 1 (Auditor) | Infiere ≥1 fecha, ≥3 numéricas y ≥3 categóricas sin nombres de columna | ✅ PASA |
| F-03 | F | Agente 2 (Analista) | Elige como medida principal la variable de costo (mayor magnitud acumulada), no la edad | ✅ PASA |
| F-04 | F | Agente 3 (Intérprete) | Infiere dominio salud/hospitalario SOLO a partir de los valores de las categorías | ✅ PASA |
| F-05 | F | Agente 4 (Informe) | Declara la limitación de nombres de columna no informativos | ✅ PASA |
| G-01 | G | Agente 1 (Auditor) | 'region' con valores N/S se trata como categoría (no como booleano) | ✅ PASA |
| G-02 | G | Agente 3 (Intérprete) | Advierte explícitamente el tamaño de muestra pequeño | ✅ PASA |
| K-01 | H | Agente 1 (Limpiador) | RR. HH. (latin-1, ';', encabezados con tildes y '¿?', '$ 3.200.000', fechas DD/MM/AAAA): esquema correcto y salario medio coherente (2,5-4 millones) | ✅ PASA |
| K-02 | H | Agente 3 (Intérprete) | Dominio 'recursos humanos' inferido y hallazgo de la tasa de renuncia por cargo con Soporte como el más alto | ✅ PASA |
| K-03 | H | Agente 3 (Intérprete) | Una serie por fecha de ingreso con ~9 registros/periodo se marca como NO concluyente (impacto bajo), no como hallazgo de alto impacto | ✅ PASA |
| K-04 | I | Agente 1 (Limpiador) | Archivo de UNA columna con comas internas: no inventa delimitador y conserva los 80 comentarios (comentarios idénticos no son duplicados sin identificador) | ✅ PASA |
| K-05 | I | Agente 2 (Analista) | Sentimiento del archivo de una columna con exactitud ≥ 85% | ✅ PASA |
| H-01 | H | Agente 5 (Consejero) | CFO + subir precios 25%: modo decisión, lente finanzas, ≥3 sesgos, magnitud contrastada con la variación real, ≥3 cuestionamientos y NO responde 'proceder' | ✅ PASA |
| H-02 | H | Agente 5 (Consejero) | Propone alternativa tipo prueba A/B para una decisión de precios | ✅ PASA |
| H-03 | H | Agente 5 (Consejero) | Cerrar 'Occidente': enlaza la entidad con los datos, marca irreversibilidad y no recomienda 'proceder' | ✅ PASA |
| H-04 | H | Agente 5 (Consejero) | No complaciente: ante cerrar 'Centro' (30% de las ventas) muestra la evidencia en contra con su porcentaje | ✅ PASA |
| H-05 | H | Agente 5 (Consejero) | Sector PQR: rol detectado en el texto, lente servicio, entidad 'Logística' enlazada y preguntas de vuelta al administrador | ✅ PASA |
| H-06 | H | Agente 5 (Consejero) | Sector público: lente 'publico', entidad Cali enlazada, stakeholders de gobierno (ciudadanía/órganos de control) | ✅ PASA |
| H-07 | H | Agente 5 (Consejero) | Salud con datos sin encabezado: detecta exceso de certeza, optimismo y evidencia anecdótica; lente salud | ✅ PASA |
| H-08 | H | Agente 5 (Consejero) | Pregunta abierta sobre producción: la respuesta directa nombra la máquina con más unidades defectuosas (M-03) | ✅ PASA |
| H-09 | H | Agente 5 (Consejero) | Pregunta comercial: responde con la sucursal líder y además cuestiona la presuposición/calidad | ✅ PASA |
| H-10 | H | Agente 5 (Consejero) | Sin mensaje: modo exploración, propone decisiones sugeridas por los datos y las cuestiona | ✅ PASA |
| H-11 | H | Agente 5 (Consejero) | Seguimiento conversacional: recuerda la decisión previa (Occidente) al recibir un dato nuevo | ✅ PASA |
| H-12 | H | Agente 5 (Consejero) | Adaptabilidad al rol: misma decisión, distinto lente, stakeholders y comunicación según el rol | ✅ PASA |
| H-13 | H | Agente 5 (Consejero) | Sobre datos ruidosos: advierte la baja calidad de los datos como cuestionamiento de alta severidad | ✅ PASA |
| H-15 | H | Agente 5 (Consejero) | Base RR. HH. inédita: detecta el rol en el texto (lente talento), enlaza 'Soporte', marca ≥2 sesgos, confronta la tasa de renuncia de Soporte con la general y NO responde 'proceder' (antes lo hacía) | ✅ PASA |
| H-16 | H | Agente 5 (Consejero) | Pregunta sobre una base inédita: responde con la agrupación pedida (ausentismo por cargo) | ✅ PASA |
| H-14 | H | Agente 5 (Consejero) | Las 13 salidas del consejero cumplen el esquema JSON estricto y contienen 0 cifras no verificadas | ✅ PASA |
| L-01 | Agente 6 | Agente 6 | Para cada rol (Auxiliar, Asistente, Supervisor, Gerente) genera 8 preguntas con los 4 formatos; opción múltiple con A-D y una sola mejor respuesta; la vista pública NO filtra la clave | ✅ PASA |
| L-02 | Agente 6 | Agente 6 | Calificación aritmética: mejores respuestas = 100%, peores ≤ 25%, sin responder = 0% (4 roles) | ✅ PASA |
| L-03 | Agente 6 | Agente 6 | Calibración por rol: la mejor respuesta a la MISMA situación es distinta en los 4 roles y la ideal del Gerente puntúa 0 para un Auxiliar (excede su autoridad) | ✅ PASA |
| L-04 | Agente 6 | Agente 6 | Adaptativo: genera una simulación válida y sin cifras inventadas para los 9 datasets (el escenario automático elige 'quiebra' para ventas en caída y 'operativa' para PQR con 62% de mensajes negativos) | ✅ PASA |
| L-05 | Agente 6 | Agente 6 | La dinámica elegida (un solo formato) se respeta; el escenario elegido (inopia) también | ✅ PASA |
| L-06 | Agente 6 | Agente 6 | Reporte Final: puntaje 0-100, % de éxito de decisiones, diagnóstico por rol, competencias, recomendaciones y revisión pregunta por pregunta; coherente con el desempeño (best→Sobresaliente, worst→Requiere refuerzo con ≥2 recomendaciones) | ✅ PASA |
| L-07 | Agente 6 | Agente 6 | LLM defectuoso: descarta preguntas con 3 opciones o competencia inventada, conserva la válida, completa con preguntas de respaldo hasta 6 y enmascara las cifras inventadas del contexto | ✅ PASA |
| L-08 | Agente 6 | Agente 6 | Servidor HTTP real: la página incluye instrucciones, selector de rol y escenario; ciclo iniciar→evaluar funciona; rol inválido y simulación inexistente devuelven 400 | ✅ PASA |
| L-09 | Agente 6 | Agente 6 | Interfaz: el contador de respondidas tiene id propio (no pisa otros textos) y cada formato tiene control interactivo (radio, desplegable, completar inline) | ✅ PASA |
| L-10 | Agente 6 | Agente 6 | Coherencia con los datos: con calidad alta (95/100) ninguna pregunta plantea 'datos con vacíos' como causa de la crisis | ✅ PASA |
| I-01 | Sonda | Agente 2 | JSON inválido del LLM → reintento con retroalimentación del error y éxito en el 2.º intento | ✅ PASA |
| I-02 | Sonda | Orquestador | LLM caído (excepción) → respaldo determinista; la cadena completa termina | ✅ PASA |
| I-03 | Sonda | Agente 2 | Estadístico inventado (media=999,99), variable fantasma y 'ref' inexistente → corregidos con el valor medido o descartados | ✅ PASA |
| I-04 | Sonda | Agente 3 | Cifras inventadas (87,5%; 12.345.678) enmascaradas como '[cifra no verificada]'; hallazgo sin evidencia descartado | ✅ PASA |
| I-05 | Sonda | Agente 3 | Alertas de datos faltantes omitidas por el LLM → restituidas por el guardrail | ✅ PASA |
| I-06 | Sonda | Agente 4 | Gráficos con columna inexistente o tipo no permitido descartados; resumen de 200 palabras recortado a ≤120 | ✅ PASA |
| I-07 | Sonda | Agente 1 | El LLM tipifica 'canal' (texto) como numérico, falsea % de nulos y omite una columna → la herramienta rechaza el tipo, restituye lo medido y la columna omitida | ✅ PASA |
| J-01 | Todos | Arquitectura | 9 datasets de estructuras y dominios distintos procesados SIN modificar código ni prompts (huellas idénticas antes/después) | ✅ PASA |
| J-02 | Todos | Agente 3 (Intérprete) | Dominios inferidos distintos para ≥6 de los 9 datasets (no hay un dominio cableado) | ✅ PASA |
| J-03 | Todos | Orquestador | Cada dataset se procesa en <20 s | ✅ PASA |
| J-05 | Todos | Ingesta | Un archivo vacío produce un error claro en español (no una traza) | ✅ PASA |
| J-04 | Todos | Prompts | Ningún prompt menciona columnas ni dominios concretos de los datasets de prueba | ✅ PASA |

**Total: 91/91 verificaciones aprobadas.**

## 3. Tiempos de procesamiento

| Dataset | Segundos |
|---|---|
| A | 2.4 |
| B | 3.0 |
| C | 1.6 |
| D | 0.8 |
| E | 0.3 |
| F | 0.5 |
| G | 0.0 |
| H | 0.5 |
| I | 0.1 |