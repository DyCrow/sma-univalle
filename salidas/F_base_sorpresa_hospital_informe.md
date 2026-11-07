# Informe ejecutivo · salud / hospitalario

**Desarrollado por:** ANDRES SANCHEZ Y SAMUEL MORA — Universidad del Valle  
**Asignatura:** Proyecto Integrador Multidisciplinar  

_Archivo: F_base_sorpresa_hospital.csv · motor: motor determinista (sin LLM)_

## Resumen ejecutivo
Valores extremos en columna 8: Hay 11 valores atípicos (1,2%); la media (4.943.270) y la mediana (4.272.112) difieren, por lo que conviene usar medidas robustas. Se analizaron 900 registros y 9 variables, del 2025-03-01 al 2025-09-16. Dominio inferido: salud / hospitalario (confianza alta). Valor atípico en columna 8: valor 18.753.282 (z=3,9), identificador 100371. Valor atípico en columna 8: valor 16.612.410 (z=3,3), identificador 100017. Calidad de datos alta (100/100).

## Recomendaciones priorizadas
1. **Validar los casos extremos con la fuente antes de usarlos en metas o pronósticos.** — Valores extremos en columna 8 (impacto medio; evidencia num:columna_8) (plazo: 60-90 días)
2. **Revisar el registro original: puede ser un error de captura o un evento real relevante.** — Anomalía a verificar (impacto medio; evidencia anom:columna_8:371) (plazo: 60-90 días)
3. **Investigar qué practica o condición diferencia al mejor grupo y evaluar si es replicable en el peor.** — Diferencias de columna 8 entre columna 9 (impacto medio; evidencia inter:columna_8|columna_9) (plazo: 60-90 días)
4. **Confirmar con la fuente si el cambio es estructural y ajustar metas/capacidad en consecuencia.** — Dinámica temporal (impacto medio; evidencia tiempo:columna_2) (plazo: 60-90 días)
5. **Evaluar si palancas sobre una de las variables mueven la otra mediante una prueba piloto.** — Relación entre variables cuantitativas (impacto medio; evidencia corr:columna_7|columna_8) (plazo: 60-90 días)

## Hallazgos de negocio
- **Valores extremos en columna 8** [riesgo, impacto medio]: Hay 11 valores atípicos (1,2%); la media (4.943.270) y la mediana (4.272.112) difieren, por lo que conviene usar medidas robustas. _(evidencia: num:columna_8)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en columna 8: valor 18.753.282 (z=3,9), identificador 100371. _(evidencia: anom:columna_8:371)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en columna 8: valor 16.612.410 (z=3,3), identificador 100017. _(evidencia: anom:columna_8:17)_
- **Diferencias de columna 8 entre columna 9** [oportunidad, impacto medio]: El promedio de columna 8 es mayor en «Remisión» (5.718.820) y menor en «Alta» (4.908.860); promedio general 4.943.270. _(evidencia: inter:columna_8|columna_9)_
- **Diferencias de columna 8 entre columna 3** [oportunidad, impacto medio]: El promedio de columna 8 es mayor en «Cirugía» (5.115.563) y menor en «Medicina interna» (4.675.864); promedio general 4.943.270. _(evidencia: inter:columna_8|columna_3)_
- **Dinámica temporal** [oportunidad, impacto medio]: Columna 8 creció 5,1% en el último periodo completo frente al previo. La pendiente promedio es -1,8% por mes (R²=0,65). Mejor periodo: 2025-03 (5.171.274); menor: 2025-07 (4.619.678). _(evidencia: tiempo:columna_2)_
- **Relación entre variables cuantitativas** [neutro, impacto medio]: columna 7 y columna 8 muestran correlación positiva (r=0,96); es consistente con una relación, no prueba causalidad. _(evidencia: corr:columna_7|columna_8)_
- **Patrón semanal** [oportunidad, impacto bajo]: El día con mayor actividad es el sábado (15,7% de los registros). _(evidencia: tiempo:columna_2)_

## Contexto y alcance
Se analizaron 900 registros y 9 variables, del 2025-03-01 al 2025-09-16. Dominio inferido: salud / hospitalario (confianza alta).

Método: cuatro agentes especializados en cadena (auditoría → estadística → interpretación → informe), con herramientas deterministas para el cálculo exacto y verificación automática de cifras.

## Hallazgos clave
1. **Valores extremos en columna 8** — Hay 11 valores atípicos (1,2%); la media (4.943.270) y la mediana (4.272.112) difieren, por lo que conviene usar medidas robustas. _(impacto medio; evidencia: num:columna_8)_
2. **Anomalía a verificar** — Valor atípico en columna 8: valor 18.753.282 (z=3,9), identificador 100371. _(impacto medio; evidencia: anom:columna_8:371)_
3. **Anomalía a verificar** — Valor atípico en columna 8: valor 16.612.410 (z=3,3), identificador 100017. _(impacto medio; evidencia: anom:columna_8:17)_
4. **Diferencias de columna 8 entre columna 9** — El promedio de columna 8 es mayor en «Remisión» (5.718.820) y menor en «Alta» (4.908.860); promedio general 4.943.270. _(impacto medio; evidencia: inter:columna_8|columna_9)_
5. **Diferencias de columna 8 entre columna 3** — El promedio de columna 8 es mayor en «Cirugía» (5.115.563) y menor en «Medicina interna» (4.675.864); promedio general 4.943.270. _(impacto medio; evidencia: inter:columna_8|columna_3)_
6. **Dinámica temporal** — Columna 8 creció 5,1% en el último periodo completo frente al previo. La pendiente promedio es -1,8% por mes (R²=0,65). Mejor periodo: 2025-03 (5.171.274); menor: 2025-07 (4.619.678). _(impacto medio; evidencia: tiempo:columna_2)_
7. **Relación entre variables cuantitativas** — columna 7 y columna 8 muestran correlación positiva (r=0,96); es consistente con una relación, no prueba causalidad. _(impacto medio; evidencia: corr:columna_7|columna_8)_

## Riesgos y oportunidades
**Riesgos**
- Valores extremos en columna 8: Hay 11 valores atípicos (1,2%); la media (4.943.270) y la mediana (4.272.112) difieren, por lo que conviene usar medidas robustas.
- Anomalía a verificar: Valor atípico en columna 8: valor 18.753.282 (z=3,9), identificador 100371.
- Anomalía a verificar: Valor atípico en columna 8: valor 16.612.410 (z=3,3), identificador 100017.

**Oportunidades**
- Diferencias de columna 8 entre columna 9: El promedio de columna 8 es mayor en «Remisión» (5.718.820) y menor en «Alta» (4.908.860); promedio general 4.943.270.
- Diferencias de columna 8 entre columna 3: El promedio de columna 8 es mayor en «Cirugía» (5.115.563) y menor en «Medicina interna» (4.675.864); promedio general 4.943.270.
- Dinámica temporal: Columna 8 creció 5,1% en el último periodo completo frente al previo. La pendiente promedio es -1,8% por mes (R²=0,65). Mejor periodo: 2025…
- Patrón semanal: El día con mayor actividad es el sábado (15,7% de los registros).

## Calidad de datos y limitaciones
Puntaje de calidad: **100/100** (alta).

**Limitaciones del análisis:**
- Los nombres de columna no son informativos: se asumió «columna_8» como medida principal por ser la variable aditiva de mayor magnitud acumulada.
- La cobertura temporal es de 199 días (< 1 año): no se puede separar estacionalidad de tendencia.

## Visualizaciones sugeridas
- Columna 8 por mes (linea; x=columna_2, y=columna_8, agregación media)
- Columna 8 por columna 9 (barras; x=columna_9, y=columna_8, agregación media)
- Distribución de columna 8 (histograma; x=columna_8, y=None, agregación conteo)
- Composición por columna 3 (pastel; x=columna_3, y=None, agregación conteo)
- % de nulos por columna (barras; x=__nulos__, y=None, agregación nulos)