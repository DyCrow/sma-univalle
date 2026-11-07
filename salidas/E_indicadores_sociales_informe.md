# Informe ejecutivo · social / territorial

**Desarrollado por:** ANDRES SANCHEZ Y SAMUEL MORA — Universidad del Valle  
**Asignatura:** Proyecto Integrador Multidisciplinar  

_Archivo: E_indicadores_sociales.xlsx · motor: motor determinista (sin LLM)_

## Resumen ejecutivo
Concentración de poblacion por municipio: En municipio, «Cali» concentra 42,8% de poblacion (9.256.800). El 20% superior de las categorías aporta 59,7% del total. Se analizaron 48 registros y 8 variables. Dominio inferido: social / territorial (confianza alta). En departamento, «Valle del Cauca» concentra 59,5% de poblacion (12.870.200). Hay 4 valores atípicos (8,3%); la media (450.829) y la mediana (319.650) difieren, por lo que conviene usar medidas robustas. Calidad de datos alta (95/100).

## Recomendaciones priorizadas
1. **Revisar la dependencia de la categoría dominante y definir un plan de mitigación.** — Concentración de poblacion por municipio (impacto alto; evidencia inter:poblacion|municipio) (plazo: 30 días)
2. **Validar los casos extremos con la fuente antes de usarlos en metas o pronósticos.** — Valores extremos en poblacion (impacto medio; evidencia num:poblacion) (plazo: 60-90 días)
3. **Revisar el registro original: puede ser un error de captura o un evento real relevante.** — Anomalía a verificar (impacto medio; evidencia anom:poblacion:3) (plazo: 60-90 días)
4. **Explorar con un análisis controlado si esta dimensión es un factor accionable.** — Municipio como factor explicativo (impacto medio; evidencia inter:poblacion|municipio) (plazo: 60-90 días)
5. **Evaluar si palancas sobre una de las variables mueven la otra mediante una prueba piloto.** — Relación entre variables cuantitativas (impacto medio; evidencia corr:pobreza_multidimensional|desempleo) (plazo: 60-90 días)

## Hallazgos de negocio
- **Concentración de poblacion por municipio** [riesgo, impacto alto]: En municipio, «Cali» concentra 42,8% de poblacion (9.256.800). El 20% superior de las categorías aporta 59,7% del total. _(evidencia: inter:poblacion|municipio)_
- **Concentración de poblacion por departamento** [riesgo, impacto alto]: En departamento, «Valle del Cauca» concentra 59,5% de poblacion (12.870.200). _(evidencia: inter:poblacion|departamento)_
- **Valores extremos en poblacion** [riesgo, impacto medio]: Hay 4 valores atípicos (8,3%); la media (450.829) y la mediana (319.650) difieren, por lo que conviene usar medidas robustas. _(evidencia: num:poblacion)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en poblacion: valor 2.348.400 (z=3,3), identificador fila 5. _(evidencia: anom:poblacion:3)_
- **Anomalía a verificar** [riesgo, impacto medio]: Valor atípico en poblacion: valor 2.325.600 (z=3,2), identificador fila 4. _(evidencia: anom:poblacion:2)_
- **Municipio como factor explicativo** [neutro, impacto medio]: La variable municipio explica una parte alta de la variación de poblacion (η²=1,000). Es asociación, no causa. _(evidencia: inter:poblacion|municipio)_
- **Departamento como factor explicativo** [neutro, impacto medio]: La variable departamento explica una parte alta de la variación de poblacion (η²=0,215). Es asociación, no causa. _(evidencia: inter:poblacion|departamento)_
- **Relación entre variables cuantitativas** [neutro, impacto medio]: pobreza multidimensional y desempleo muestran correlación positiva (r=0,97); es consistente con una relación, no prueba causalidad. _(evidencia: corr:pobreza_multidimensional|desempleo)_
- **Asociación entre categorías** [neutro, impacto medio]: municipio y departamento están asociadas (V de Cramér=1,00); la combinación más frecuente es «Buenaventura» con «Valle del Cauca» (8,3%). _(evidencia: asoc:municipio|departamento)_

## Contexto y alcance
Se analizaron 48 registros y 8 variables. Dominio inferido: social / territorial (confianza alta).

Método: cuatro agentes especializados en cadena (auditoría → estadística → interpretación → informe), con herramientas deterministas para el cálculo exacto y verificación automática de cifras.

## Hallazgos clave
1. **Concentración de poblacion por municipio** — En municipio, «Cali» concentra 42,8% de poblacion (9.256.800). El 20% superior de las categorías aporta 59,7% del total. _(impacto alto; evidencia: inter:poblacion|municipio)_
2. **Concentración de poblacion por departamento** — En departamento, «Valle del Cauca» concentra 59,5% de poblacion (12.870.200). _(impacto alto; evidencia: inter:poblacion|departamento)_
3. **Valores extremos en poblacion** — Hay 4 valores atípicos (8,3%); la media (450.829) y la mediana (319.650) difieren, por lo que conviene usar medidas robustas. _(impacto medio; evidencia: num:poblacion)_
4. **Anomalía a verificar** — Valor atípico en poblacion: valor 2.348.400 (z=3,3), identificador fila 5. _(impacto medio; evidencia: anom:poblacion:3)_
5. **Anomalía a verificar** — Valor atípico en poblacion: valor 2.325.600 (z=3,2), identificador fila 4. _(impacto medio; evidencia: anom:poblacion:2)_
6. **Municipio como factor explicativo** — La variable municipio explica una parte alta de la variación de poblacion (η²=1,000). Es asociación, no causa. _(impacto medio; evidencia: inter:poblacion|municipio)_
7. **Departamento como factor explicativo** — La variable departamento explica una parte alta de la variación de poblacion (η²=0,215). Es asociación, no causa. _(impacto medio; evidencia: inter:poblacion|departamento)_

## Riesgos y oportunidades
**Riesgos**
- Concentración de poblacion por municipio: En municipio, «Cali» concentra 42,8% de poblacion (9.256.800). El 20% superior de las categorías aporta 59,7% del total.
- Concentración de poblacion por departamento: En departamento, «Valle del Cauca» concentra 59,5% de poblacion (12.870.200).
- Valores extremos en poblacion: Hay 4 valores atípicos (8,3%); la media (450.829) y la mediana (319.650) difieren, por lo que conviene usar medidas robustas.
- Anomalía a verificar: Valor atípico en poblacion: valor 2.348.400 (z=3,3), identificador fila 5.
- Anomalía a verificar: Valor atípico en poblacion: valor 2.325.600 (z=3,2), identificador fila 4.

**Oportunidades**
- Mejorar la calidad y granularidad del registro para habilitar análisis más finos.

## Calidad de datos y limitaciones
Puntaje de calidad: **95/100** (alta).
- [baja] poblacion: 4 valor(es) extremos (>3×IQR) → Se conservan; las métricas robustas (mediana) se reportan junto a la media.
- [baja] homicidios_por_100_mil_hab: Estilos numéricos mezclados: plano, punto_dec → Unificado a número decimal.

**Limitaciones del análisis:**
- No se detectó columna de fecha: no se evaluaron tendencias ni estacionalidad.

## Visualizaciones sugeridas
- Poblacion por municipio (barras; x=municipio, y=poblacion, agregación suma)
- Distribución de poblacion (histograma; x=poblacion, y=None, agregación conteo)
- Composición por departamento (pastel; x=departamento, y=None, agregación conteo)
- % de nulos por columna (barras; x=__nulos__, y=None, agregación nulos)