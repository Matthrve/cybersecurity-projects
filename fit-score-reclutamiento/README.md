# 🎯 Sistema Inteligente de Cribado y Auditoría de Talento

Proyecto final — Fundamentos de Inteligencia Artificial (AIE), Summer Camp 2026, CyberMinds EPN.

Un reclutador recibe cientos de CVs por vacante y no tiene tiempo de leerlos todos a fondo, por lo que
buenos candidatos se descartan por error o al azar. Este sistema no solo puntúa el ajuste CV↔vacante
con un modelo de Machine Learning **entrenado** (no un simple prompt a un LLM): también explica cada
score con SHAP, audita el proceso en busca de sesgos, detecta CVs duplicados/plagiados entre candidatos
y recomienda rutas de mejora a los candidatos casi aptos. Corre **100% local, sin API externa ni costes**.

## Arquitectura

Ver [`docs/arquitectura.md`](docs/arquitectura.md) para el diagrama completo del flujo de datos.

## Instalación

```bash
pip install -r requirements.txt
```

La primera vez que se use, `sentence-transformers` descargará el modelo de embeddings
`all-MiniLM-L6-v2` (~80 MB) desde Hugging Face. Después de esa descarga inicial, todo corre
sin conexión a internet.

## Cómo generar los datos y entrenar el modelo

El modelo se entrena con un dataset **sintético**, generado localmente (sin depender de datasets
externos ni cuentas de terceros). Ver la metodología de etiquetado en la cabecera de `src/synthetic_data.py`.

```bash
cd src
python synthetic_data.py   # genera data/synthetic_dataset.csv
python train_model.py      # entrena el modelo de fit-score y muestra métricas
python anomaly.py          # entrena el detector de CVs atípicos
```

## Cómo correr el dashboard

```bash
streamlit run app.py
```

Sube una vacante (predefinida por familia de puesto, o un puesto personalizado editando skills
obligatorias/deseables/experiencia/educación) y uno o varios CVs (PDF/DOCX/TXT) para ver: ranking
de candidatos, explicación SHAP por candidato, panel de auditoría de sesgos, alertas de CVs
duplicados entre sí, y un botón para descargar el ranking en CSV.

**Editar o crear una vacante requiere contraseña de administrador** (RRHH). La de demo es
`admin123` — cámbiala antes de cualquier uso real siguiendo las instrucciones en
[`docs/seguridad.md`](docs/seguridad.md). Usar los puestos predefinidos tal cual (sin editarlos)
no requiere contraseña.

## Cómo correr las pruebas

```bash
pip install pytest  # ya incluido en requirements.txt
pytest tests/ -v
```

Las pruebas corren el pipeline completo (no funciones aisladas) sobre los CVs reales de
`ejemplos/` y verifican que el sistema se comporta como se espera: scores altos/bajos según el
ajuste real, detección de anomalías y de duplicados, y que los proxies de auditoría (universidad,
brecha laboral) nunca entran como input del modelo.

## Estructura

```
data/               taxonomía de skills, dataset sintético, recursos de upskilling
models/             modelo de fit-score (GradientBoosting) + detector de anomalías (IsolationForest)
src/                pipeline: parsing, features, entrenamiento, explicabilidad, fairness, auth, etc.
tests/              pruebas de integración del pipeline y de seguridad (pytest)
app.py, ui.py       dashboard Streamlit (lógica y capa visual)
.streamlit/         config.toml (tema, versionado) y secrets.toml (contraseña, NO versionado)
docs/               documentación exigida por la rúbrica (problema, arquitectura, seguridad, registro de prompts)
```

## Seguridad

Ver [`docs/seguridad.md`](docs/seguridad.md): control de acceso para editar vacantes, protección
contra CSV injection y XSS, manejo seguro de archivos subidos, y no persistencia de datos de
candidatos.

## Limitaciones conocidas

- El dataset de entrenamiento es sintético; en producción real se recomendaría re-entrenar con
  decisiones históricas reales (respetando privacidad y con auditoría de sesgo continua).
- La extracción de años de experiencia y universidad usa heurísticas de texto (regex + keywords),
  no un parser de CV comercial — funciona bien con CVs bien estructurados, puede fallar con formatos
  muy atípicos.
- La autenticación de administrador usa una contraseña única compartida (adecuada para una demo
  académica, no para producción) — ver "Próximos pasos" en `docs/seguridad.md`.
- Ver [`docs/nota_uso_responsable.md`](docs/nota_uso_responsable.md) sobre los límites del módulo de auditoría de sesgos.
