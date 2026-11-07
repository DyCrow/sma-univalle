# Informe ejecutivo · servicio al ciudadano / PQR

**Desarrollado por:** ANDRES SANCHEZ Y SAMUEL MORA — Universidad del Valle  
**Asignatura:** Proyecto Integrador Multidisciplinar  

_Archivo: B_pqr_texto_libre.csv · motor: motor determinista (sin LLM)_

## Resumen ejecutivo
Sentimiento y temas en el texto libre: En el campo de texto «descripcion» el 62,2% de los mensajes es negativo (1.245 de 2.000), el 14,5% positivo y el 23,2% neutro. Tema más frecuente: Tiempos de respuesta / demoras (34,2%). Se analizaron 2.000 registros y 8 variables, del 2025-01-01 al 2025-11-26. Dominio inferido: servicio al ciudadano / PQR (confianza alta). «Soporte técnico» tiene el mayor porcentaje de mensajes negativos (72,2%) frente a «Atención al usuario» (45,0%). El promedio de dias respuesta es mayor en «Logística» (14,28) y menor en «Jurídica» (6,87); promedio general 8,32. Calidad de datos alta (96/100).

## Recomendaciones priorizadas
1. **Atacar primero el tema dominante en las comunicaciones negativas y publicar un compromiso de tiempos de respuesta.** — Sentimiento y temas en el texto libre (impacto alto; evidencia texto:descripcion) (plazo: 30 días)
2. **Intervenir primero en «Soporte técnico» con un plan de 30 días y medir el cambio del indicador.** — Dónde se concentra la insatisfacción (area responsable) (impacto alto; evidencia textodim:descripcion|area_responsable) (plazo: 30 días)
3. **Investigar qué practica o condición diferencia al mejor grupo y evaluar si es replicable en el peor.** — Diferencias de dias respuesta entre area responsable (impacto alto; evidencia inter:dias_respuesta|area_responsable) (plazo: 30 días)
4. **Validar los casos extremos con la fuente antes de usarlos en metas o pronósticos.** — Valores extremos en dias respuesta (impacto medio; evidencia num:dias_respuesta) (plazo: 60-90 días)
5. **Revisar el registro original: puede ser un error de captura o un evento real relevante.** — Anomalía a verificar (impacto medio; evidencia anom:dias_respuesta:1378) (plazo: 60-90 días)

## Hallazgos de negocio
- **Sentimiento y temas en el texto libre** [riesgo, impacto alto]: En el campo de texto «descripcion» el 62,2% de los mensajes es negativo (1.245 de 2.000), el 14,5% positivo y el 23,2% neutro. Tema más frecuente: Tiempos de respuesta / demoras (34,2%). _(evidencia: texto:descripcion)_
- **Dónde se concentra la insatisfacción (area responsable)** [riesgo, impacto alto]: «Soporte técnico» tiene el mayor porcentaje de mensajes negativos (72,2%) frente a «Atención al usuario» (45,0%). _(evidencia: textodim:descripcion|area_responsable)_
- **Diferencias de dias respuesta entre area responsable** [riesgo, impacto alto]: El promedio de dias respuesta es mayor en «Logística» (14,28) y menor en «Jurídica» (6,87); promedio general 8,32. _(evidencia: inter:dias_respuesta|area_responsable)_
- **Diferencias de dias respuesta entre tipo solicitud** [riesgo, impacto medio]: El promedio de dias respuesta es mayor en «Queja» (8,50) y menor en «Petición» (7,70); promedio general 8,32. _(evidencia: inter:dias_respuesta|tipo_solicitud)_
- **Valores extremos en dias respuesta** [riesgo, impacto medio]: Hay 60 valores atípicos (3,5%); la media (8,32) y la mediana (7) difieren, por lo que conviene usar medidas robustas. _(evidencia: num:dias_respuesta)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en dias respuesta: valor 40 (z=5,7), identificador PQR-2025-001379. _(evidencia: anom:dias_respuesta:1378)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en dias respuesta: valor 37 (z=5,2), identificador PQR-2025-000414. _(evidencia: anom:dias_respuesta:413)_
- **Area responsable como factor explicativo** [neutro, impacto medio]: La variable area responsable explica una parte alta de la variación de dias respuesta (η²=0,233). Es asociación, no causa. _(evidencia: inter:dias_respuesta|area_responsable)_
- **Dinámica temporal** [neutro, impacto medio]: Dias respuesta cayó 0,5% en el último periodo completo frente al previo. La pendiente promedio es 1,0% por mes (R²=0,29). Mejor periodo: 2025-07 (9,13); menor: 2025-01 (7,66). _(evidencia: tiempo:fecha_radicacion)_
- **Asociación entre categorías** [neutro, impacto medio]: area responsable y tipo solicitud están asociadas (V de Cramér=0,20); la combinación más frecuente es «Facturación» con «Queja» (20,2%). _(evidencia: asoc:area_responsable|tipo_solicitud)_
- **Patrón semanal** [oportunidad, impacto bajo]: El día con mayor actividad es el miércoles (15,3% de los registros). _(evidencia: tiempo:fecha_radicacion)_

## Contexto y alcance
Se analizaron 2.000 registros y 8 variables, del 2025-01-01 al 2025-11-26. Dominio inferido: servicio al ciudadano / PQR (confianza alta).

Método: cuatro agentes especializados en cadena (auditoría → estadística → interpretación → informe), con herramientas deterministas para el cálculo exacto y verificación automática de cifras.

## Hallazgos clave
1. **Sentimiento y temas en el texto libre** — En el campo de texto «descripcion» el 62,2% de los mensajes es negativo (1.245 de 2.000), el 14,5% positivo y el 23,2% neutro. Tema más frecuente: Tiempos de respuesta / demoras (34,2%). _(impacto alto; evidencia: texto:descripcion)_
2. **Dónde se concentra la insatisfacción (area responsable)** — «Soporte técnico» tiene el mayor porcentaje de mensajes negativos (72,2%) frente a «Atención al usuario» (45,0%). _(impacto alto; evidencia: textodim:descripcion|area_responsable)_
3. **Diferencias de dias respuesta entre area responsable** — El promedio de dias respuesta es mayor en «Logística» (14,28) y menor en «Jurídica» (6,87); promedio general 8,32. _(impacto alto; evidencia: inter:dias_respuesta|area_responsable)_
4. **Diferencias de dias respuesta entre tipo solicitud** — El promedio de dias respuesta es mayor en «Queja» (8,50) y menor en «Petición» (7,70); promedio general 8,32. _(impacto medio; evidencia: inter:dias_respuesta|tipo_solicitud)_
5. **Valores extremos en dias respuesta** — Hay 60 valores atípicos (3,5%); la media (8,32) y la mediana (7) difieren, por lo que conviene usar medidas robustas. _(impacto medio; evidencia: num:dias_respuesta)_
6. **Anomalía a verificar** — Valor atípico en dias respuesta: valor 40 (z=5,7), identificador PQR-2025-001379. _(impacto medio; evidencia: anom:dias_respuesta:1378)_
7. **Anomalía a verificar** — Valor atípico en dias respuesta: valor 37 (z=5,2), identificador PQR-2025-000414. _(impacto medio; evidencia: anom:dias_respuesta:413)_

## Riesgos y oportunidades
**Riesgos**
- Sentimiento y temas en el texto libre: En el campo de texto «descripcion» el 62,2% de los mensajes es negativo (1.245 de 2.000), el 14,5% positivo y el 23,2% neutro. Tema más fre…
- Dónde se concentra la insatisfacción (area responsable): «Soporte técnico» tiene el mayor porcentaje de mensajes negativos (72,2%) frente a «Atención al usuario» (45,0%).
- Diferencias de dias respuesta entre area responsable: El promedio de dias respuesta es mayor en «Logística» (14,28) y menor en «Jurídica» (6,87); promedio general 8,32.
- Diferencias de dias respuesta entre tipo solicitud: El promedio de dias respuesta es mayor en «Queja» (8,50) y menor en «Petición» (7,70); promedio general 8,32.
- Valores extremos en dias respuesta: Hay 60 valores atípicos (3,5%); la media (8,32) y la mediana (7) difieren, por lo que conviene usar medidas robustas.

**Oportunidades**
- Patrón semanal: El día con mayor actividad es el miércoles (15,3% de los registros).

## Calidad de datos y limitaciones
Puntaje de calidad: **96/100** (alta).
- [baja] dias_respuesta: 15.45% de valores ausentes → Se reportan como N/A; no se imputan valores.
- [baja] dias_respuesta: 5 valor(es) extremos (>3×IQR) → Se conservan; las métricas robustas (mediana) se reportan junto a la media.
- [baja] tipo_solicitud: 8 variante(s) de escritura de una misma categoría → Unificadas por forma canónica.

**Datos faltantes (reportados como N/A, sin imputar):**
- dias_respuesta: 15,4%

**Limitaciones del análisis:**
- La cobertura temporal es de 329 días (< 1 año): no se puede separar estacionalidad de tendencia.

## Visualizaciones sugeridas
- Dias respuesta por mes (linea; x=fecha_radicacion, y=dias_respuesta, agregación media)
- Dias respuesta por area responsable (barras; x=area_responsable, y=dias_respuesta, agregación media)
- Distribución de dias respuesta (histograma; x=dias_respuesta, y=None, agregación conteo)
- Sentimiento del texto libre (pastel; x=descripcion, y=None, agregación sentimiento)
- Temas más frecuentes en el texto (barras; x=descripcion, y=None, agregación temas)
- % de nulos por columna (barras; x=__nulos__, y=None, agregación nulos)