# Informe ejecutivo · comercial / ventas

**Desarrollado por:** ANDRES SANCHEZ Y SAMUEL MORA — Universidad del Valle  
**Asignatura:** Proyecto Integrador Multidisciplinar  

_Archivo: C_ruido_nulos_formatos_mixtos.csv · motor: motor determinista (sin LLM)_

## Resumen ejecutivo
Concentración de total por categoria: En categoria, «Electrónica» concentra 74,1% de total (2.578.689.775). Se analizaron 3.000 registros y 14 variables, del 2024-01-01 al 2025-06-30. Dominio inferido: comercial / ventas (confianza alta). Calidad baja: usar con cautela (puntaje 59/100; nulos promedio 19,6%; 3000 filas). Total creció 20,5% en el último periodo completo frente al previo. La pendiente promedio es 2,4% por mes (R²=0,27). Mejor periodo: 2024-12 (344.538.110); menor: 2024-07 (149.635.530). Calidad de datos baja: usar con cautela (59/100).

## Recomendaciones priorizadas
1. **Proteger el segmento líder (inventario, servicio, retención) y definir un plan para desarrollar los segmentos rezagados.** — Concentración de total por categoria (impacto alto; evidencia inter:total|categoria) (plazo: 30 días)
2. **Corregir la captura en origen y reanalizar antes de tomar decisiones irreversibles.** — Confiabilidad de los datos (impacto alto; evidencia calidad) (plazo: 30 días)
3. **Confirmar con la fuente si el cambio es estructural y ajustar metas/capacidad en consecuencia.** — Dinámica temporal (impacto alto; evidencia tiempo:fecha) (plazo: 30 días)
4. **Validar los casos extremos con la fuente antes de usarlos en metas o pronósticos.** — Valores extremos en total (impacto medio; evidencia num:total) (plazo: 60-90 días)
5. **Revisar el registro original: puede ser un error de captura o un evento real relevante.** — Anomalía a verificar (impacto medio; evidencia anom:total:2346) (plazo: 60-90 días)

## Hallazgos de negocio
- **Concentración de total por categoria** [riesgo, impacto alto]: En categoria, «Electrónica» concentra 74,1% de total (2.578.689.775). _(evidencia: inter:total|categoria)_
- **Confiabilidad de los datos** [riesgo, impacto alto]: Calidad baja: usar con cautela (puntaje 59/100; nulos promedio 19,6%; 3000 filas). _(evidencia: calidad)_
- **Dinámica temporal** [oportunidad, impacto alto]: Total creció 20,5% en el último periodo completo frente al previo. La pendiente promedio es 2,4% por mes (R²=0,27). Mejor periodo: 2024-12 (344.538.110); menor: 2024-07 (149.635.530). _(evidencia: tiempo:fecha)_
- **Valores extremos en total** [riesgo, impacto medio]: Hay 374 valores atípicos (13,2%); la media (1.394.181) y la mediana (633.350) difieren, por lo que conviene usar medidas robustas. _(evidencia: num:total)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en total: valor 46.200.000 (z=23,2), identificador T000054. _(evidencia: anom:total:2346)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en total: valor 12.105.500 (z=5,5), identificador T000256. _(evidencia: anom:total:1770)_
- **Concentración de total por sucursal** [neutro, impacto medio]: En sucursal, «Norte» concentra 32,3% de total (897.193.015). _(evidencia: inter:total|sucursal)_
- **Categoria como factor explicativo** [neutro, impacto medio]: La variable categoria explica una parte alta de la variación de total (η²=0,498). Es asociación, no causa. _(evidencia: inter:total|categoria)_
- **Relación entre variables cuantitativas** [neutro, impacto medio]: precio unitario y total muestran correlación positiva (r=0,72); es consistente con una relación, no prueba causalidad. _(evidencia: corr:precio_unitario|total)_
- **Asociación entre categorías** [neutro, impacto medio]: categoria y producto están asociadas (V de Cramér=1,00); la combinación más frecuente es «Electrónica» con «Televisor 55» (7,8%). _(evidencia: asoc:categoria|producto)_
- **Patrón semanal** [oportunidad, impacto bajo]: El día con mayor actividad es el sábado (18,2% de los registros). _(evidencia: tiempo:fecha)_

## Contexto y alcance
Se analizaron 3.000 registros y 14 variables, del 2024-01-01 al 2025-06-30. Dominio inferido: comercial / ventas (confianza alta).

Método: cuatro agentes especializados en cadena (auditoría → estadística → interpretación → informe), con herramientas deterministas para el cálculo exacto y verificación automática de cifras.

## Hallazgos clave
1. **Concentración de total por categoria** — En categoria, «Electrónica» concentra 74,1% de total (2.578.689.775). _(impacto alto; evidencia: inter:total|categoria)_
2. **Confiabilidad de los datos** — Calidad baja: usar con cautela (puntaje 59/100; nulos promedio 19,6%; 3000 filas). _(impacto alto; evidencia: calidad)_
3. **Dinámica temporal** — Total creció 20,5% en el último periodo completo frente al previo. La pendiente promedio es 2,4% por mes (R²=0,27). Mejor periodo: 2024-12 (344.538.110); menor: 2024-07 (149.635.530). _(impacto alto; evidencia: tiempo:fecha)_
4. **Valores extremos en total** — Hay 374 valores atípicos (13,2%); la media (1.394.181) y la mediana (633.350) difieren, por lo que conviene usar medidas robustas. _(impacto medio; evidencia: num:total)_
5. **Anomalía a verificar** — Valor atípico en total: valor 46.200.000 (z=23,2), identificador T000054. _(impacto medio; evidencia: anom:total:2346)_
6. **Anomalía a verificar** — Valor atípico en total: valor 12.105.500 (z=5,5), identificador T000256. _(impacto medio; evidencia: anom:total:1770)_
7. **Concentración de total por sucursal** — En sucursal, «Norte» concentra 32,3% de total (897.193.015). _(impacto medio; evidencia: inter:total|sucursal)_

## Riesgos y oportunidades
**Riesgos**
- Concentración de total por categoria: En categoria, «Electrónica» concentra 74,1% de total (2.578.689.775).
- Confiabilidad de los datos: Calidad baja: usar con cautela (puntaje 59/100; nulos promedio 19,6%; 3000 filas).
- Valores extremos en total: Hay 374 valores atípicos (13,2%); la media (1.394.181) y la mediana (633.350) difieren, por lo que conviene usar medidas robustas.
- Anomalía a verificar: Valor atípico en total: valor 46.200.000 (z=23,2), identificador T000054.
- Anomalía a verificar: Valor atípico en total: valor 12.105.500 (z=5,5), identificador T000256.

**Oportunidades**
- Dinámica temporal: Total creció 20,5% en el último periodo completo frente al previo. La pendiente promedio es 2,4% por mes (R²=0,27). Mejor periodo: 2024-12 …
- Patrón semanal: El día con mayor actividad es el sábado (18,2% de los registros).

## Calidad de datos y limitaciones
Puntaje de calidad: **59/100** (baja: usar con cautela).
- [alta] notas: 80.5% de valores ausentes → Se reportan como N/A; no se imputan valores.
- [media] fecha: 4 formatos de fecha: DD/MM/AAAA, D de mes de AAAA, AAAA-MM-DD, DD-MM-AAAA → Estandarizado a AAAA-MM-DD.
- [media] sucursal: 30.23% de valores ausentes → Se reportan como N/A; no se imputan valores.
- [media] cantidad: 21.47% de valores ausentes → Se reportan como N/A; no se imputan valores.
- [media] cantidad: 8 valor(es) negativo(s) en variable que normalmente no lo es → Se conservan y se señalan; verificar si son devoluciones/errores.
- [media] precio_unitario: 25.3% de valores ausentes → Se reportan como N/A; no se imputan valores.
- [media] descuento_pct: 31.27% de valores ausentes → Se reportan como N/A; no se imputan valores.
- [media] columna_sin_nombre_12: 33.57% de valores ausentes → Se reportan como N/A; no se imputan valores.
- [media] columna_sin_nombre_12: Encabezado vacío o genérico → Nombre asignado: columna_sin_nombre_12.
- [media] columna_sin_nombre_13: Encabezado vacío o genérico → Nombre asignado: columna_sin_nombre_13.

**Datos faltantes (reportados como N/A, sin imputar):**
- fecha: 6,3%
- sucursal: 30,2%
- categoria: 12,5%
- cantidad: 21,5%
- precio_unitario: 25,3%
- descuento_pct: 31,3%
- total: 5,7%
- medio_pago: 18,6%
- vendedor: 8,5%
- columna_sin_nombre_12: 33,6%
- notas: 80,5%

**Limitaciones del análisis:**
- Calidad de datos baja: usar con cautela (puntaje 59/100): interpretar con cautela.

## Visualizaciones sugeridas
- Total por mes (linea; x=fecha, y=total, agregación suma)
- Total por sucursal (barras; x=sucursal, y=total, agregación suma)
- Distribución de total (histograma; x=total, y=None, agregación conteo)
- Composición por categoria (pastel; x=categoria, y=None, agregación conteo)
- % de nulos por columna (barras; x=__nulos__, y=None, agregación nulos)