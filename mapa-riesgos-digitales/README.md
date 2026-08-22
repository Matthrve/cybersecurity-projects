# 🛡️ Mapa de Riesgos Digitales (IA ligera)

Herramienta que evalúa hábitos digitales de una persona —**contraseñas,
actualizaciones, uso de redes, respaldo y seguridad física del
dispositivo**— y genera un mapa de riesgo visual con un **plan de acción
priorizado**, **historial de progreso** y, en Windows, contraste contra
**señales reales del equipo**. Combina un **motor de reglas explicable**
con un **modelo de Machine Learning ligero** entrenado sobre un dataset
sintético.

## Cómo ejecutarlo

```bash
cd mapa-riesgos-digitales
python -m venv venv
venv\Scripts\activate        # en Windows
pip install -r requirements.txt

python src/generar_dataset.py     # genera data/habitos_dataset.csv
python src/entrenar_modelo.py     # entrena y guarda models/modelo_riesgo.joblib

python server.py                  # abre http://localhost:5000
```

También existe una versión alternativa con Streamlit (`streamlit run app.py`,
puerto 8501) — se mantiene funcionando pero **la versión recomendada es la
de Flask** (`server.py`): tiene una interfaz propia con transiciones y
gráficos animados que Streamlit no puede ofrecer (cada interacción en
Streamlit recarga toda la página; acá no).

Opcional — recordatorio semanal para reevaluarte (crea una tarea en el
Programador de tareas de Windows; no se instala solo):

```bash
powershell -ExecutionPolicy Bypass -File scripts\instalar_recordatorio.ps1
# para quitarlo:
powershell -ExecutionPolicy Bypass -File scripts\desinstalar_recordatorio.ps1
```

## Arquitectura

```
mapa-riesgos-digitales/
├── server.py                     # Backend Flask: sirve la página y expone la API JSON
├── app.py                        # (alternativa) Interfaz Streamlit — misma lógica, otra UI
├── templates/index.html          # Página: header tipo expediente, tabs, formulario de 5 categorías
├── static/
│   ├── css/style.css              # Sistema de diseño (paleta, tipografía, animaciones)
│   └── js/app.js                  # Interactividad + gráficos SVG animados (sin librerías)
├── src/
│   ├── reglas.py                  # Motor de reglas (5 categorías, alertas con "cambios_sugeridos")
│   ├── generar_dataset.py         # Genera perfiles sintéticos etiquetados
│   ├── modelo.py                  # Entrenamiento/predicción con RandomForest
│   ├── entrenar_modelo.py         # Script para (re)entrenar el modelo
│   ├── plan_accion.py             # Simula el impacto de resolver cada alerta y prioriza
│   ├── historial.py               # Persistencia local en SQLite (data/historial.db)
│   ├── senales_sistema.py         # Puente Python -> PowerShell para leer el estado real del equipo
│   └── verificar_vencimiento.py   # CLI usado por el recordatorio programado
├── scripts/
│   ├── senales_sistema.ps1        # Lee Windows Update / Firewall / Defender / BitLocker / RDP (solo lectura)
│   ├── recordatorio.ps1           # Muestra un aviso si hace mucho que no te evaluás
│   ├── instalar_recordatorio.ps1  # Registra la tarea semanal (cambio persistente: se corre a mano)
│   └── desinstalar_recordatorio.ps1
├── data/
│   ├── habitos_dataset.csv        # Dataset sintético de entrenamiento
│   └── historial.db               # Tu historial local de evaluaciones (no se versiona)
└── models/modelo_riesgo.joblib
```

`server.py` es una capa delgada: valida el JSON entrante y llama a las
mismas funciones de `src/` que usa `app.py`. Ninguna lógica de negocio vive
en el backend web ni en el frontend — así ambas interfaces se mantienen
consistentes sin duplicar código.

### Las capas del sistema

1. **Reglas** (`src/reglas.py`): cada respuesta se compara con buenas
   prácticas de seguridad conocidas, en **5 categorías** (contraseñas,
   actualizaciones, redes, respaldo y **dispositivo** —bloqueo automático
   de pantalla, cifrado de disco, acceso remoto expuesto—, esta última
   cubre el riesgo de que alguien tenga el equipo en la mano, a
   diferencia de las otras 4 que son sobre amenazas remotas). Producen un
   puntaje 0-100 por categoría y alertas explicables, cada una con la
   recomendación **y el cambio concreto** (`cambios_sugeridos`) que la
   resolvería — es lo que usa el plan de acción para simular resultados.

2. **Modelo ML** (`src/modelo.py`): un `RandomForestClassifier` pequeño
   (150 árboles, profundidad 8 — entrena en segundos, sin GPU) que
   clasifica el riesgo global en **Bajo/Medio/Alto**. Se entrena con
   1200 perfiles sintéticos (`src/generar_dataset.py`), etiquetados con
   las mismas reglas más ruido aleatorio. Exactitud ~76% en el 20% de
   datos reservado.

3. **Plan de acción priorizado** (`src/plan_accion.py`): para cada
   alerta, simula "¿qué pasaría si la resolviera?" recalculando el
   puntaje con ese único hábito corregido, y prioriza por
   **impacto ÷ esfuerzo** — así el plan empieza siempre por los cambios
   de mayor retorno (ej. activar 2FA, bajo esfuerzo, antes que dejar de
   reutilizar contraseñas en todos lados, esfuerzo alto).

4. **Historial local** (`src/historial.py`): cada evaluación se guarda
   con fecha en `data/historial.db` (SQLite, sin dependencias externas).
   La pestaña "Historial" de la app muestra la tendencia del puntaje
   global y por categoría en el tiempo.

5. **Señales reales del sistema** (`src/senales_sistema.py` +
   `scripts/senales_sistema.ps1`, solo Windows): un script de PowerShell
   de solo lectura consulta el estado real de actualizaciones
   automáticas, firewall, Windows Defender, bloqueo de pantalla, cifrado
   de disco (BitLocker) y Escritorio remoto, y la app los usa para
   **prellenar el formulario** y **marcar discrepancias** si lo que
   respondiste no coincide con lo que se detecta en el equipo. Cada
   chequeo falla de forma aislada (ej. BitLocker suele requerir permisos
   de administrador): si uno no está disponible, el resto se sigue
   mostrando igual.

6. **Recordatorios proactivos** (`scripts/recordatorio.ps1` +
   `instalar_recordatorio.ps1`): una tarea semanal opcional del
   Programador de tareas de Windows que avisa (con un mensaje emergente)
   si pasaron muchos días desde la última evaluación. Es un cambio
   persistente del sistema, así que **no se instala automáticamente** —
   se activa corriendo el script vos mismo.

### El frontend (por qué Flask y no solo Streamlit)

Streamlit vuelve a ejecutar todo el script en cada interacción — eso lo hace
rápido de construir, pero le pone un techo duro a lo visual: no hay
transiciones suaves reales, y los controles (checkboxes, sliders, botones)
tienen un aspecto genérico difícil de "romper" con CSS. `server.py` +
`templates/index.html` resuelven esto con una página propia:

- **Diseño "expediente de seguridad"**: paleta tinta profunda / papel frío
  con un único acento petróleo (deliberadamente distinto de los colores
  semánticos de riesgo verde/ámbar/rojo, para no confundir "marca" con
  "alerta"). Tipografía en tres roles: IBM Plex Sans (títulos), Source
  Serif 4 (texto de lectura, recomendaciones), IBM Plex Mono (cifras,
  fechas, badges) — nada de Inter genérico ni iconos de emoji.
- **Sin recargas de página**: las 3 secciones (**Cómo funciona** —la
  pestaña con la que arranca la página—, **Evaluar** e **Historial**) son
  pestañas manejadas por JavaScript; el formulario se envía por
  `fetch()` a `/api/evaluar` y el resultado se inyecta en el DOM.
- **Gráficos SVG hechos a mano, sin librerías**: el velocímetro es un
  círculo con `stroke-dashoffset` animado, el radar es un polígono que
  crece desde el centro, la línea de tendencia del historial se "dibuja"
  con la misma técnica. Todo con `prefers-reduced-motion` respetado.
- **Tema claro/oscuro real**: toda la paleta está en variables CSS con dos
  juegos de valores (`prefers-color-scheme`), verificado con el navegador
  forzado a cada modo — no solo "probado en uno y asumido en el otro".

## Qué se probó

- Perfil de hábitos inseguros (incluyendo dispositivo sin bloqueo, sin
  cifrar y con RDP expuesto) → puntaje de reglas 90/100, ML predice
  **Alto**, plan de acción con 17 pasos ordenados por prioridad.
- Perfil de hábitos cuidadosos → puntaje de reglas 0/100, ML predice
  **Bajo** (99% confianza), sin alertas.
- Guardado y lectura del historial (SQLite) con las 5 categorías,
  gráfico de tendencia, borrado con confirmación.
- Detección real en el equipo de desarrollo: actualizaciones automáticas,
  firewall, Defender y RDP correctamente leídos; BitLocker degradó
  correctamente a "no disponible" por falta de permisos de administrador
  en vez de romper el diagnóstico completo.
- Detección correcta de discrepancias cuando el autoreporte no coincide
  con la señal real del sistema.
- Generación del reporte descargable como documento Word (.docx) con
  formato propio (`src/reporte_word.py`, vía `python-docx`).
- Modelo reentrenado con las 17 columnas (14 originales + 3 de
  dispositivo): ~75% de exactitud en el conjunto de prueba.
- **Frontend Flask**: probado con el test client de Flask (todas las rutas
  `/api/*`, incluyendo casos de error con payload incompleto → 400) y con
  el navegador real: sin errores de consola, paleta y tipografía
  verificadas en modo claro y oscuro (contraste corregido en la barra
  superior, que usa un color fijo en vez de heredar el token de tema), y
  el cálculo final de cada gráfico (velocímetro, radar, barras) verificado
  numéricamente. La reproducción de las animaciones en sí no se pudo
  verificar visualmente porque el entorno de pruebas mantiene la pestaña
  en segundo plano (Chrome pausa `requestAnimationFrame` ahí) — el código
  usa técnicas CSS estándar, pero vale la pena que confirmes visualmente
  que las transiciones se ven bien en tu navegador real.
- Bug real encontrado y corregido durante las pruebas: al agregar la
  categoría "Dispositivo" nunca se había actualizado el esquema de
  `historial.py`, así que ese puntaje se perdía silenciosamente al
  guardar el historial.
- Otro bug real, reportado por el usuario y confirmado programáticamente
  (pidiéndole al navegador qué elemento hay exactamente en cada punto de
  la pantalla): los interruptores (`.toggle`) tenían un `<span>`
  decorativo dibujado encima del `<input>` real, así que ningún clic
  llegaba al checkbox. Se corrigió con `pointer-events: none` en las
  capas decorativas.
- Reporte Word verificado reabriendo el `.docx` generado con
  `python-docx` y comprobando el contenido real (tablas, puntajes, plan
  de acción), no solo que la descarga "no fallara".

## Visión de escalabilidad

- **Aprendizaje continuo real**: con historial acumulado en
  `data/historial.db`, el siguiente paso es que `entrenar_modelo.py`
  pueda incorporar (con consentimiento) evaluaciones reales —no solo
  sintéticas— para que el modelo aprenda de patrones de uso reales.
- **Más señales del sistema**: `senales_sistema.ps1` ya está estructurado
  para sumar más chequeos (BitLocker, contraseña de pantalla de bloqueo,
  antigüedad del navegador) sin tocar el resto de la app.
- **Multi-perfil**: el esquema de `historial.py` ya tiene una columna
  `perfil`, pensada para habilitar más adelante varios perfiles (ej. una
  vista familiar) sin rediseñar la base.
- **Multiplataforma**: `senales_sistema.py` aísla todo lo específico de
  Windows detrás de una función; agregar macOS/Linux implica un nuevo
  script y una rama en `disponible()`/`obtener_senales_sistema()`.
- **Chequeos que salen a internet (evaluado, no implementado)**: cosas
  como verificar si tu email apareció en una filtración conocida (estilo
  HaveIBeenPwned) o detectar software con vulnerabilidades (CVEs)
  conocidas serían de alto valor, pero **rompen la promesa de "100%
  local"** de este proyecto y agregan mantenimiento pesado (una base de
  CVEs se desactualiza rápido). Si se agregan alguna vez, deberían ser
  opt-in explícito con consentimiento claro en la UI, no parte del flujo
  por defecto.

## Privacidad

Todo corre localmente. `data/historial.db` vive únicamente en tu equipo
(está en `.gitignore`, no se sube al repositorio) y nada se envía a
servidores externos. El diagnóstico del sistema es de solo lectura: no
modifica configuraciones. El dataset de entrenamiento es 100% sintético.
