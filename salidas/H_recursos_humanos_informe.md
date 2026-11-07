# Informe ejecutivo · recursos humanos

**Desarrollado por:** ANDRES SANCHEZ Y SAMUEL MORA — Universidad del Valle  
**Asignatura:** Proyecto Integrador Multidisciplinar  

_Archivo: H_recursos_humanos.csv · motor: motor determinista (sin LLM)_

## Resumen ejecutivo
Proporción de «renuncio» por cargo: La proporción de «Sí/verdadero» en renuncio es 24,9% en general, pero llega a 37,8% en «Soporte» frente a 15,9% en «Dirección». Se analizaron 800 registros y 8 variables, del 2018-01-14 al 2025-02-12. Dominio inferido: recursos humanos (confianza alta). Hay 8 valores atípicos (1,0%); la media (3,04) y la mediana (3) difieren, por lo que conviene usar medidas robustas. Valor atípico en salario mensual: valor 6.576.471 (z=3,7), identificador E0072. Calidad de datos alta (100/100).

## Recomendaciones priorizadas
1. **Entender por qué «Soporte» se separa del resto antes de tomar medidas generales.** — Proporción de «renuncio» por cargo (impacto alto; evidencia ind:renuncio|cargo) (plazo: 30 días)
2. **Validar los casos extremos con la fuente antes de usarlos en metas o pronósticos.** — Valores extremos en dias de ausentismo (impacto medio; evidencia num:dias_de_ausentismo) (plazo: 60-90 días)
3. **Revisar el registro original: puede ser un error de captura o un evento real relevante.** — Anomalía a verificar (impacto medio; evidencia anom:salario_mensual:72) (plazo: 60-90 días)
4. **Investigar qué practica o condición diferencia al mejor grupo y evaluar si es replicable en el peor.** — Diferencias de salario mensual entre ciudad (impacto medio; evidencia inter:salario_mensual|ciudad) (plazo: 60-90 días)
5. **Entender por qué «Bogotá» se separa del resto antes de tomar medidas generales.** — Proporción de «renuncio» por ciudad (impacto medio; evidencia ind:renuncio|ciudad) (plazo: 60-90 días)

## Hallazgos de negocio
- **Proporción de «renuncio» por cargo** [riesgo, impacto alto]: La proporción de «Sí/verdadero» en renuncio es 24,9% en general, pero llega a 37,8% en «Soporte» frente a 15,9% en «Dirección». _(evidencia: ind:renuncio|cargo)_
- **Valores extremos en dias de ausentismo** [riesgo, impacto medio]: Hay 8 valores atípicos (1,0%); la media (3,04) y la mediana (3) difieren, por lo que conviene usar medidas robustas. _(evidencia: num:dias_de_ausentismo)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en salario mensual: valor 6.576.471 (z=3,7), identificador E0072. _(evidencia: anom:salario_mensual:72)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en salario mensual: valor 6.067.477 (z=3,1), identificador E0620. _(evidencia: anom:salario_mensual:620)_
- **Diferencias de salario mensual entre ciudad** [oportunidad, impacto medio]: El promedio de salario mensual es mayor en «Medellín» (3.291.531) y menor en «Cali» (3.165.933); promedio general 3.209.463. _(evidencia: inter:salario_mensual|ciudad)_
- **Diferencias de salario mensual entre cargo** [oportunidad, impacto medio]: El promedio de salario mensual es mayor en «Logística» (3.368.984) y menor en «Contabilidad» (3.059.102); promedio general 3.209.463. _(evidencia: inter:salario_mensual|cargo)_
- **Proporción de «renuncio» por ciudad** [neutro, impacto medio]: La proporción de «Sí/verdadero» en renuncio es 24,9% en general, pero llega a 28,4% en «Bogotá» frente a 22,0% en «Cali». _(evidencia: ind:renuncio|ciudad)_
- **Dinámica temporal (no concluyente)** [neutro, impacto bajo]: Salario mensual cayó 19,7% en el último periodo completo frente al previo. La pendiente promedio es -0,0% por mes (R²=0,01). Mejor periodo: 2019-10 (3.900.012); menor: 2023-05 (2.473.384). Con solo 9,3 registros por mes en promedio, esta variación es ruido muestral y no debe usarse para decidir. _(evidencia: tiempo:fecha_de_ingreso)_
- **Patrón semanal** [oportunidad, impacto bajo]: El día con mayor actividad es el miércoles (15,9% de los registros). _(evidencia: tiempo:fecha_de_ingreso)_

## Contexto y alcance
Se analizaron 800 registros y 8 variables, del 2018-01-14 al 2025-02-12. Dominio inferido: recursos humanos (confianza alta).

Método: cuatro agentes especializados en cadena (auditoría → estadística → interpretación → informe), con herramientas deterministas para el cálculo exacto y verificación automática de cifras.

## Hallazgos clave
1. **Proporción de «renuncio» por cargo** — La proporción de «Sí/verdadero» en renuncio es 24,9% en general, pero llega a 37,8% en «Soporte» frente a 15,9% en «Dirección». _(impacto alto; evidencia: ind:renuncio|cargo)_
2. **Valores extremos en dias de ausentismo** — Hay 8 valores atípicos (1,0%); la media (3,04) y la mediana (3) difieren, por lo que conviene usar medidas robustas. _(impacto medio; evidencia: num:dias_de_ausentismo)_
3. **Anomalía a verificar** — Valor atípico en salario mensual: valor 6.576.471 (z=3,7), identificador E0072. _(impacto medio; evidencia: anom:salario_mensual:72)_
4. **Anomalía a verificar** — Valor atípico en salario mensual: valor 6.067.477 (z=3,1), identificador E0620. _(impacto medio; evidencia: anom:salario_mensual:620)_
5. **Diferencias de salario mensual entre ciudad** — El promedio de salario mensual es mayor en «Medellín» (3.291.531) y menor en «Cali» (3.165.933); promedio general 3.209.463. _(impacto medio; evidencia: inter:salario_mensual|ciudad)_
6. **Diferencias de salario mensual entre cargo** — El promedio de salario mensual es mayor en «Logística» (3.368.984) y menor en «Contabilidad» (3.059.102); promedio general 3.209.463. _(impacto medio; evidencia: inter:salario_mensual|cargo)_
7. **Proporción de «renuncio» por ciudad** — La proporción de «Sí/verdadero» en renuncio es 24,9% en general, pero llega a 28,4% en «Bogotá» frente a 22,0% en «Cali». _(impacto medio; evidencia: ind:renuncio|ciudad)_

## Riesgos y oportunidades
**Riesgos**
- Proporción de «renuncio» por cargo: La proporción de «Sí/verdadero» en renuncio es 24,9% en general, pero llega a 37,8% en «Soporte» frente a 15,9% en «Dirección».
- Valores extremos en dias de ausentismo: Hay 8 valores atípicos (1,0%); la media (3,04) y la mediana (3) difieren, por lo que conviene usar medidas robustas.
- Anomalía a verificar: Valor atípico en salario mensual: valor 6.576.471 (z=3,7), identificador E0072.
- Anomalía a verificar: Valor atípico en salario mensual: valor 6.067.477 (z=3,1), identificador E0620.

**Oportunidades**
- Diferencias de salario mensual entre ciudad: El promedio de salario mensual es mayor en «Medellín» (3.291.531) y menor en «Cali» (3.165.933); promedio general 3.209.463.
- Diferencias de salario mensual entre cargo: El promedio de salario mensual es mayor en «Logística» (3.368.984) y menor en «Contabilidad» (3.059.102); promedio general 3.209.463.
- Patrón semanal: El día con mayor actividad es el miércoles (15,9% de los registros).

## Calidad de datos y limitaciones
Puntaje de calidad: **100/100** (alta).

## Visualizaciones sugeridas
- Salario mensual por mes (linea; x=fecha_de_ingreso, y=salario_mensual, agregación media)
- Salario mensual por ciudad (barras; x=ciudad, y=salario_mensual, agregación media)
- Distribución de salario mensual (histograma; x=salario_mensual, y=None, agregación conteo)
- Composición por cargo (pastel; x=cargo, y=None, agregación conteo)
- % de nulos por columna (barras; x=__nulos__, y=None, agregación nulos)