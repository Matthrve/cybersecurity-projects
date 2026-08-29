# Medidas de Seguridad

El sistema procesa datos personales de solicitantes (nombres, trayectoria laboral, educación).
Estas son las medidas implementadas y su justificación.

## 1. Control de acceso para editar/crear vacantes

Cualquiera puede **usar** los puestos predefinidos (evaluar candidatos contra ellos), pero
**modificar** los requisitos de una vacante existente o **crear una nueva** requiere una
contraseña de administrador de RRHH (`src/auth.py`, `render_admin_gate`).

- Solo se compara un **hash SHA-256** de la contraseña — el valor en texto plano nunca se
  guarda ni se transmite. El hash real vive en `.streamlit/secrets.toml`, que está en
  `.gitignore` y por lo tanto nunca se sube al repositorio.
- El valor de demostración (`admin123`) es solo para poder probar el proyecto de inmediato.
  **Antes de cualquier uso real, cambiar la contraseña:**
  ```bash
  python -c "import hashlib; print(hashlib.sha256(b'tu_password_nueva').hexdigest())"
  ```
  y reemplazar `admin_password_hash` en `.streamlit/secrets.toml` con el resultado.
- El desbloqueo es por sesión de navegador (`st.session_state`), no persiste entre sesiones ni
  se comparte entre usuarios distintos.
- Limitación conocida: es una contraseña única compartida (autenticación simple), adecuada para
  una demo académica. Un despliegue real necesitaría cuentas individuales, control de acceso
  basado en roles y un registro de auditoría de cambios — ver sección "Próximos pasos".

## 2. Protección contra CSV injection en la exportación

El nombre de un candidato proviene del **nombre del archivo subido**, que un atacante podría
controlar (por ejemplo, nombrando su CV `=HYPERLINK("http://evil.com","click")_.pdf`). Si ese
valor se escribe tal cual en un CSV y la víctima lo abre en Excel/Sheets, el programa puede
interpretarlo como una fórmula y ejecutarla — un vector real y documentado (CSV/Formula
Injection, OWASP).

`ui.py::_csv_safe` antepone una comilla simple a cualquier celda que empiece con `=`, `+`, `-`,
`@`, tab o retorno de carro, neutralizando la fórmula sin alterar el dato visible. Cubierto por
`tests/test_security.py`.

## 3. Prevención de XSS al renderizar resultados

El dashboard construye tarjetas HTML dinámicamente a partir de datos que también provienen del
nombre del archivo subido (`ui.py::render_candidate_card` y funciones relacionadas). Todo texto
insertado en HTML pasa primero por `ui.py::esc` (equivalente a `html.escape`), de modo que un
nombre de archivo como `<script>alert(1)</script>.pdf` se muestra como texto literal y no se
ejecuta como marcado.

## 4. Manejo seguro de archivos subidos

- Solo se aceptan extensiones `.pdf`, `.docx`, `.txt` (`st.file_uploader(type=[...])`).
- Si un archivo está corrupto, cifrado o no se puede leer, `app.py` captura la excepción por
  archivo individual, lo excluye del lote y avisa al usuario — en vez de detener toda la
  evaluación o exponer un traceback interno (que podría revelar rutas del sistema u otra
  información de la infraestructura).
- Límite de tamaño por archivo (200 MB, valor por defecto de Streamlit) para mitigar el envío
  de archivos anormalmente grandes.

## 5. Minimización y no persistencia de datos personales

- Los CVs se procesan **en memoria** durante la sesión y se descartan al cerrarla: no se
  escriben a disco, no se registran en logs ni se envían a ningún servicio externo.
- El único dato que sale del proceso local es, opcionalmente, el CSV que el propio usuario
  decide descargar — su protección posterior (dónde se guarda, con quién se comparte) es
  responsabilidad de quien lo descarga.
- El modelo de IA corre 100% local; ningún CV ni fragmento de CV se envía a una API externa de
  pago (ver `docs/arquitectura.md`, sección "Integraciones externas").

## 6. Marco legal de referencia

En Ecuador, el tratamiento de datos personales de solicitantes está regulado por la **Ley
Orgánica de Protección de Datos Personales (LOPDP, 2021)**, que exige minimización de datos,
finalidad específica y medidas de seguridad técnicas — principios que las medidas 1–5 buscan
respetar a nivel de prototipo académico.

## Próximos pasos para un despliegue real (fuera del alcance de esta entrega)

- Autenticación individual por usuario (no una contraseña compartida) y control de acceso
  basado en roles.
- Registro de auditoría (quién cambió qué requisito de vacante y cuándo).
- Cifrado en reposo si se llegara a persistir CVs, y política de retención/eliminación de datos.
- Ejecución bajo HTTPS y gestión de secretos vía un vault en lugar de un archivo local.
