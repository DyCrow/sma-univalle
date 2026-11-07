# Informe ejecutivo · genérico (no determinado)

**Desarrollado por:** ANDRES SANCHEZ Y SAMUEL MORA — Universidad del Valle  
**Asignatura:** Proyecto Integrador Multidisciplinar  

_Archivo: I_encuesta_una_columna.csv · motor: motor determinista (sin LLM)_

## Resumen ejecutivo
Sentimiento y temas en el texto libre: En el campo de texto «comentario» el 82,5% de los mensajes es negativo (66 de 80), el 3,8% positivo y el 13,8% neutro. Tema más frecuente: Tiempos de respuesta / demoras (35,0%). Se analizaron 80 registros y 1 variables. Dominio inferido: genérico (no determinado) (confianza baja). Calidad de datos alta (100/100).

## Recomendaciones priorizadas
1. **Priorizar el tema dominante en los comentarios negativos y medir su evolución mensual.** — Sentimiento y temas en el texto libre (impacto alto; evidencia texto:comentario) (plazo: 30 días)

## Hallazgos de negocio
- **Sentimiento y temas en el texto libre** [riesgo, impacto alto]: En el campo de texto «comentario» el 82,5% de los mensajes es negativo (66 de 80), el 3,8% positivo y el 13,8% neutro. Tema más frecuente: Tiempos de respuesta / demoras (35,0%). _(evidencia: texto:comentario)_

## Contexto y alcance
Se analizaron 80 registros y 1 variables. Dominio inferido: genérico (no determinado) (confianza baja).

Método: cuatro agentes especializados en cadena (auditoría → estadística → interpretación → informe), con herramientas deterministas para el cálculo exacto y verificación automática de cifras.

## Hallazgos clave
1. **Sentimiento y temas en el texto libre** — En el campo de texto «comentario» el 82,5% de los mensajes es negativo (66 de 80), el 3,8% positivo y el 13,8% neutro. Tema más frecuente: Tiempos de respuesta / demoras (35,0%). _(impacto alto; evidencia: texto:comentario)_

## Riesgos y oportunidades
**Riesgos**
- Sentimiento y temas en el texto libre: En el campo de texto «comentario» el 82,5% de los mensajes es negativo (66 de 80), el 3,8% positivo y el 13,8% neutro. Tema más frecuente: …

**Oportunidades**
- Mejorar la calidad y granularidad del registro para habilitar análisis más finos.

## Calidad de datos y limitaciones
Puntaje de calidad: **100/100** (alta).
- [baja] (filas): 47 fila(s) idénticas → Conservadas: sin identificador no pueden distinguirse de casos repetidos legítimos.

**Limitaciones del análisis:**
- No se detectó columna de fecha: no se evaluaron tendencias ni estacionalidad.
- No hay variables cuantitativas utilizables: el análisis es solo de frecuencias.

## Visualizaciones sugeridas
- Sentimiento del texto libre (pastel; x=comentario, y=None, agregación sentimiento)
- Temas más frecuentes en el texto (barras; x=comentario, y=None, agregación temas)
- % de nulos por columna (barras; x=__nulos__, y=None, agregación nulos)