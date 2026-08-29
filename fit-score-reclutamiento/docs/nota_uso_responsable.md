# Nota de Uso Responsable

Este proyecto es un prototipo académico. Antes de cualquier uso en un proceso de selección real,
deben considerarse los siguientes límites de diseño:

## Sobre el módulo de auditoría de sesgos (`fairness.py`)

- **No infiere género, etnia, edad ni ninguna característica protegida** a partir del nombre,
  la foto o cualquier otro dato del CV. Hacerlo sería tanto poco fiable (los nombres no determinan
  identidad de forma confiable) como éticamente cuestionable (perfilado de características sensibles
  sin consentimiento).
- Audita únicamente **proxies estructurales** ya documentados en la literatura de sesgo en
  contratación: prestigio percibido de la universidad de origen y brechas de empleo. Estos proxies
  son imperfectos y deben interpretarse como una **señal de alerta para revisión humana**, no como
  una conclusión definitiva de discriminación.
- La clasificación de universidades en "tiers" (`features.py::UNIVERSIDADES_TIER`) es una
  simplificación ilustrativa para esta demo académica, no una jerarquía oficial ni una afirmación
  sobre la calidad real de ninguna institución.
- La regla del 80% (four-fifths rule) es un estándar simplificado ampliamente usado en auditorías
  de adverse impact, pero no sustituye un análisis legal o estadístico riguroso (tamaños de muestra
  pequeños pueden generar falsos positivos/negativos).

## Sobre el score de ajuste

- Entrenado con datos **sintéticos**; antes de producción real requeriría re-entrenamiento con
  datos históricos reales, validación externa y monitoreo continuo de deriva y sesgo.
- El score es una **ayuda a la decisión**, no un reemplazo del juicio humano. Nunca debería usarse
  como único criterio de descarte automático sin revisión.

## Transparencia

Todo el pipeline es auditable: código abierto en este repositorio, sin caja negra de un proveedor
externo de LLM. Cada score viene acompañado de su explicación (SHAP + texto) y de las alertas de
auditoría correspondientes.
