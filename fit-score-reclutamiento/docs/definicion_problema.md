# Definición del Problema

## Contexto

En procesos de selección con alto volumen de postulaciones, un reclutador puede recibir cientos de
CVs para una sola vacante. Leer cada uno a fondo es inviable en el tiempo disponible, lo que lleva a
dos fallas sistemáticas: (1) descarte de buenos candidatos por fatiga, orden de lectura o azar, y
(2) decisiones difíciles de justificar objetivamente ante el candidato o ante Recursos Humanos.

## Impacto

- **Para la empresa**: costo de oportunidad de perder talento calificado, procesos de selección más
  lentos, decisiones no auditable's que exponen a la empresa a reclamos de discriminación.
- **Para el candidato**: rechazo sin retroalimentación, sin saber qué le faltó para calificar.

## Por qué una solución de IA (y no un script tradicional)

Un filtro por palabras clave (`if "python" in cv`) no distingue paráfrasis ("desarrollo de APIs
con Django" vs. "backend en Python"), no pondera la importancia relativa de cada requisito, y no
aprende de patrones sutiles que sí captura un modelo entrenado sobre features combinadas
(cobertura de skills + experiencia + educación + similitud semántica por embeddings).

## Justificación técnica del enfoque

1. **Extracción de habilidades**: taxonomía propia + fuzzy matching (rapidfuzz), tolerante a
   variaciones de escritura ("React.js" vs "React", errores tipográficos).
2. **Comprensión semántica**: embeddings locales (`sentence-transformers`) miden si la redacción
   del CV es semánticamente afín a la vacante, más allá de coincidencias literales de palabras.
3. **Modelo entrenado**: `GradientBoostingClassifier` (scikit-learn) combina las señales anteriores
   en un score probabilístico, evaluado con métricas reales (accuracy, F1, ROC-AUC) sobre un
   conjunto de prueba — no es una regla si/else disfrazada de IA.
4. **Explicabilidad**: SHAP expone qué features empujaron el score hacia arriba o abajo para
   cada candidato individual — necesario para que un reclutador pueda defender la decisión.
5. **Auditoría de sesgos**: detecta si el propio proceso de scoring favorece sistemáticamente a
   ciertos grupos estructurales (universidad, brecha laboral), aplicando la regla del 80% usada en
   auditorías reales de sesgo en contratación.
6. **Detección de anomalías**: un `IsolationForest` identifica CVs con densidad de palabras clave
   anormalmente alta (posible keyword-stuffing) para no premiar el "gaming" del sistema.
7. **Detección de duplicados**: similitud coseno entre embeddings de todos los CVs de un mismo lote,
   para exponer posibles reenvíos o plagio entre postulantes.

## Alcance y resultado que produce (según la guía del curso)

Esta solución cubre simultáneamente tres de las categorías de resultado válidas:

- **Predicción**: probabilidad de "fit" de un candidato frente a una vacante.
- **Toma de decisiones**: clasificación apto/no apto basada en evaluación probabilística.
- **Identificación de patrones**: detección de anomalías (keyword-stuffing) y de duplicados entre CVs.
