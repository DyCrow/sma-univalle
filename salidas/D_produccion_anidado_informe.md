# Informe ejecutivo · producción / operaciones

**Desarrollado por:** ANDRES SANCHEZ Y SAMUEL MORA — Universidad del Valle  
**Asignatura:** Proyecto Integrador Multidisciplinar  

_Archivo: D_produccion_anidado.json · motor: motor determinista (sin LLM)_

## Resumen ejecutivo
Concentración de unidades producidas por orden planta: En orden planta, «Cali» concentra 51,1% de unidades producidas (584.390). Se analizaron 1.500 registros y 10 variables, del 2025-02-01 al 2025-09-28. Dominio inferido: producción / operaciones (confianza alta). Unidades producidas cayó 15,2% en el último periodo completo frente al previo. La pendiente promedio es -0,6% por mes (R²=0,05). Mejor periodo: 2025-07 (156.625); menor: 2025-09 (125.795). Hay 189 valores atípicos (12,6%); la media (19,13) y la mediana (16) difieren, por lo que conviene usar medidas robustas. Calidad de datos alta (95/100).

## Recomendaciones priorizadas
1. **Priorizar mantenimiento y control de calidad en el recurso que concentra la producción.** — Concentración de unidades producidas por orden planta (impacto alto; evidencia inter:unidades_producidas|orden_planta) (plazo: 30 días)
2. **Confirmar con la fuente si el cambio es estructural y ajustar metas/capacidad en consecuencia.** — Dinámica temporal (impacto alto; evidencia tiempo:fecha) (plazo: 30 días)
3. **Validar los casos extremos con la fuente antes de usarlos en metas o pronósticos.** — Valores extremos en unidades defectuosas (impacto medio; evidencia num:unidades_defectuosas) (plazo: 60-90 días)
4. **Revisar el registro original: puede ser un error de captura o un evento real relevante.** — Anomalía a verificar (impacto medio; evidencia anom:unidades_producidas:721) (plazo: 60-90 días)
5. **Alinear turnos, inventario o atención con el día pico.** — Patrón semanal (impacto bajo; evidencia tiempo:fecha) (plazo: 60-90 días)

## Hallazgos de negocio
- **Concentración de unidades producidas por orden planta** [riesgo, impacto alto]: En orden planta, «Cali» concentra 51,1% de unidades producidas (584.390). _(evidencia: inter:unidades_producidas|orden_planta)_
- **Dinámica temporal** [riesgo, impacto alto]: Unidades producidas cayó 15,2% en el último periodo completo frente al previo. La pendiente promedio es -0,6% por mes (R²=0,05). Mejor periodo: 2025-07 (156.625); menor: 2025-09 (125.795). _(evidencia: tiempo:fecha)_
- **Valores extremos en unidades defectuosas** [riesgo, impacto medio]: Hay 189 valores atípicos (12,6%); la media (19,13) y la mediana (16) difieren, por lo que conviene usar medidas robustas. _(evidencia: num:unidades_defectuosas)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en unidades producidas: valor 1.228 (z=3,5), identificador OP-00722. _(evidencia: anom:unidades_producidas:721)_
- **Concentración de unidades producidas por turno** [neutro, impacto medio]: En turno, «Tarde» concentra 34,8% de unidades producidas (397.602). _(evidencia: inter:unidades_producidas|turno)_
- **Patrón semanal** [oportunidad, impacto bajo]: El día con mayor actividad es el martes (15,3% de los registros). _(evidencia: tiempo:fecha)_

## Contexto y alcance
Se analizaron 1.500 registros y 10 variables, del 2025-02-01 al 2025-09-28. Dominio inferido: producción / operaciones (confianza alta).

Método: cuatro agentes especializados en cadena (auditoría → estadística → interpretación → informe), con herramientas deterministas para el cálculo exacto y verificación automática de cifras.

## Hallazgos clave
1. **Concentración de unidades producidas por orden planta** — En orden planta, «Cali» concentra 51,1% de unidades producidas (584.390). _(impacto alto; evidencia: inter:unidades_producidas|orden_planta)_
2. **Dinámica temporal** — Unidades producidas cayó 15,2% en el último periodo completo frente al previo. La pendiente promedio es -0,6% por mes (R²=0,05). Mejor periodo: 2025-07 (156.625); menor: 2025-09 (125.795). _(impacto alto; evidencia: tiempo:fecha)_
3. **Valores extremos en unidades defectuosas** — Hay 189 valores atípicos (12,6%); la media (19,13) y la mediana (16) difieren, por lo que conviene usar medidas robustas. _(impacto medio; evidencia: num:unidades_defectuosas)_
4. **Anomalía a verificar** — Valor atípico en unidades producidas: valor 1.228 (z=3,5), identificador OP-00722. _(impacto medio; evidencia: anom:unidades_producidas:721)_
5. **Concentración de unidades producidas por turno** — En turno, «Tarde» concentra 34,8% de unidades producidas (397.602). _(impacto medio; evidencia: inter:unidades_producidas|turno)_
6. **Patrón semanal** — El día con mayor actividad es el martes (15,3% de los registros). _(impacto bajo; evidencia: tiempo:fecha)_

## Riesgos y oportunidades
**Riesgos**
- Concentración de unidades producidas por orden planta: En orden planta, «Cali» concentra 51,1% de unidades producidas (584.390).
- Dinámica temporal: Unidades producidas cayó 15,2% en el último periodo completo frente al previo. La pendiente promedio es -0,6% por mes (R²=0,05). Mejor peri…
- Valores extremos en unidades defectuosas: Hay 189 valores atípicos (12,6%); la media (19,13) y la mediana (16) difieren, por lo que conviene usar medidas robustas.
- Anomalía a verificar: Valor atípico en unidades producidas: valor 1.228 (z=3,5), identificador OP-00722.

**Oportunidades**
- Patrón semanal: El día con mayor actividad es el martes (15,3% de los registros).

## Calidad de datos y limitaciones
Puntaje de calidad: **95/100** (alta).
- [baja] unidades_defectuosas: 78 valor(es) extremos (>3×IQR) → Se conservan; las métricas robustas (mediana) se reportan junto a la media.
- [baja] tiempo_paro_min: Estilos numéricos mezclados: plano, punto_dec → Unificado a número decimal.

**Limitaciones del análisis:**
- La cobertura temporal es de 239 días (< 1 año): no se puede separar estacionalidad de tendencia.

## Visualizaciones sugeridas
- Unidades producidas por mes (linea; x=fecha, y=unidades_producidas, agregación suma)
- Unidades producidas por turno (barras; x=turno, y=unidades_producidas, agregación suma)
- Distribución de unidades producidas (histograma; x=unidades_producidas, y=None, agregación conteo)
- Composición por orden planta (pastel; x=orden_planta, y=None, agregación conteo)
- % de nulos por columna (barras; x=__nulos__, y=None, agregación nulos)