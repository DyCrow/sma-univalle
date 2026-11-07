# Informe ejecutivo · comercial / ventas

**Desarrollado por:** ANDRES SANCHEZ Y SAMUEL MORA — Universidad del Valle  
**Asignatura:** Proyecto Integrador Multidisciplinar  

_Archivo: A_ventas_transaccionales.csv · motor: motor determinista (sin LLM)_

## Resumen ejecutivo
Concentración de total por categoria: En categoria, «Electrónica» concentra 76,3% de total (6.378.963.830). Se analizaron 6.000 registros y 11 variables, del 2024-01-01 al 2025-06-30. Dominio inferido: comercial / ventas (confianza alta). Total cayó 11,8% en el último periodo completo frente al previo. La pendiente promedio es 2,9% por mes (R²=0,24). Mejor periodo: 2024-12 (874.098.095); menor: 2024-01 (192.290.190). Hay 817 valores atípicos (13,6%); la media (1.394.110) y la mediana (607.900) difieren, por lo que conviene usar medidas robustas. Calidad de datos alta (95/100).

## Recomendaciones priorizadas
1. **Proteger el segmento líder (inventario, servicio, retención) y definir un plan para desarrollar los segmentos rezagados.** — Concentración de total por categoria (impacto alto; evidencia inter:total|categoria) (plazo: 30 días)
2. **Confirmar con la fuente si el cambio es estructural y ajustar metas/capacidad en consecuencia.** — Dinámica temporal (impacto medio; evidencia tiempo:fecha) (plazo: 60-90 días)
3. **Validar los casos extremos con la fuente antes de usarlos en metas o pronósticos.** — Valores extremos en total (impacto medio; evidencia num:total) (plazo: 60-90 días)
4. **Revisar el registro original: puede ser un error de captura o un evento real relevante.** — Anomalía a verificar (impacto medio; evidencia anom:total:3869) (plazo: 60-90 días)
5. **Explorar con un análisis controlado si esta dimensión es un factor accionable.** — Categoria como factor explicativo (impacto medio; evidencia inter:total|categoria) (plazo: 60-90 días)

## Hallazgos de negocio
- **Concentración de total por categoria** [riesgo, impacto alto]: En categoria, «Electrónica» concentra 76,3% de total (6.378.963.830). _(evidencia: inter:total|categoria)_
- **Dinámica temporal** [riesgo, impacto medio]: Total cayó 11,8% en el último periodo completo frente al previo. La pendiente promedio es 2,9% por mes (R²=0,24). Mejor periodo: 2024-12 (874.098.095); menor: 2024-01 (192.290.190). _(evidencia: tiempo:fecha)_
- **Valores extremos en total** [riesgo, impacto medio]: Hay 817 valores atípicos (13,6%); la media (1.394.110) y la mediana (607.900) difieren, por lo que conviene usar medidas robustas. _(evidencia: num:total)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en total: valor 168.275.400 (z=60,3), identificador T003870. _(evidencia: anom:total:3869)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en total: valor 10.921.000 (z=3,4), identificador T005118. _(evidencia: anom:total:5117)_
- **Concentración de total por sucursal** [neutro, impacto medio]: En sucursal, «Centro» concentra 30,4% de total (2.543.221.115). _(evidencia: inter:total|sucursal)_
- **Categoria como factor explicativo** [neutro, impacto medio]: La variable categoria explica una parte alta de la variación de total (η²=0,269). Es asociación, no causa. _(evidencia: inter:total|categoria)_
- **Relación entre variables cuantitativas** [neutro, impacto medio]: precio unitario y total muestran correlación positiva (r=0,54); es consistente con una relación, no prueba causalidad. _(evidencia: corr:precio_unitario|total)_
- **Asociación entre categorías** [neutro, impacto medio]: categoria y producto están asociadas (V de Cramér=1,00); la combinación más frecuente es «Electrónica» con «Audífonos BT» (7,7%). _(evidencia: asoc:categoria|producto)_
- **Patrón semanal** [oportunidad, impacto bajo]: El día con mayor actividad es el sábado (17,1% de los registros). _(evidencia: tiempo:fecha)_
- **Consistencia aritmética entre variables** [neutro, impacto bajo]: La relación total ≈ cantidad × precio_unitario × (1 − descuento_pct) se cumple en 100,0% de las filas: los campos derivados son coherentes con sus componentes. _(evidencia: rel:total=cantidad*precio_unitario*(1-descuento_pct))_

## Contexto y alcance
Se analizaron 6.000 registros y 11 variables, del 2024-01-01 al 2025-06-30. Dominio inferido: comercial / ventas (confianza alta).

Método: cuatro agentes especializados en cadena (auditoría → estadística → interpretación → informe), con herramientas deterministas para el cálculo exacto y verificación automática de cifras.

## Hallazgos clave
1. **Concentración de total por categoria** — En categoria, «Electrónica» concentra 76,3% de total (6.378.963.830). _(impacto alto; evidencia: inter:total|categoria)_
2. **Dinámica temporal** — Total cayó 11,8% en el último periodo completo frente al previo. La pendiente promedio es 2,9% por mes (R²=0,24). Mejor periodo: 2024-12 (874.098.095); menor: 2024-01 (192.290.190). _(impacto medio; evidencia: tiempo:fecha)_
3. **Valores extremos en total** — Hay 817 valores atípicos (13,6%); la media (1.394.110) y la mediana (607.900) difieren, por lo que conviene usar medidas robustas. _(impacto medio; evidencia: num:total)_
4. **Anomalía a verificar** — Valor atípico en total: valor 168.275.400 (z=60,3), identificador T003870. _(impacto medio; evidencia: anom:total:3869)_
5. **Anomalía a verificar** — Valor atípico en total: valor 10.921.000 (z=3,4), identificador T005118. _(impacto medio; evidencia: anom:total:5117)_
6. **Concentración de total por sucursal** — En sucursal, «Centro» concentra 30,4% de total (2.543.221.115). _(impacto medio; evidencia: inter:total|sucursal)_
7. **Categoria como factor explicativo** — La variable categoria explica una parte alta de la variación de total (η²=0,269). Es asociación, no causa. _(impacto medio; evidencia: inter:total|categoria)_

## Riesgos y oportunidades
**Riesgos**
- Concentración de total por categoria: En categoria, «Electrónica» concentra 76,3% de total (6.378.963.830).
- Dinámica temporal: Total cayó 11,8% en el último periodo completo frente al previo. La pendiente promedio es 2,9% por mes (R²=0,24). Mejor periodo: 2024-12 (8…
- Valores extremos en total: Hay 817 valores atípicos (13,6%); la media (1.394.110) y la mediana (607.900) difieren, por lo que conviene usar medidas robustas.
- Anomalía a verificar: Valor atípico en total: valor 168.275.400 (z=60,3), identificador T003870.
- Anomalía a verificar: Valor atípico en total: valor 10.921.000 (z=3,4), identificador T005118.

**Oportunidades**
- Patrón semanal: El día con mayor actividad es el sábado (17,1% de los registros).

## Calidad de datos y limitaciones
Puntaje de calidad: **95/100** (alta).
- [media] fecha: 2 formatos de fecha: AAAA-MM-DD, DD/MM/AAAA → Estandarizado a AAAA-MM-DD.
- [baja] total: 253 valor(es) extremos (>3×IQR) → Se conservan; las métricas robustas (mediana) se reportan junto a la media.

## Visualizaciones sugeridas
- Total por mes (linea; x=fecha, y=total, agregación suma)
- Total por sucursal (barras; x=sucursal, y=total, agregación suma)
- Distribución de total (histograma; x=total, y=None, agregación conteo)
- Composición por categoria (pastel; x=categoria, y=None, agregación conteo)
- % de nulos por columna (barras; x=__nulos__, y=None, agregación nulos)