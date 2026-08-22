// Mapa de Riesgos Digitales — interactividad y gráficos SVG animados.
// Sin librerías externas: todo (dial, radar, barras, línea de tendencia)
// es SVG generado a mano con animaciones CSS/JS propias.

const NOMBRES_CATEGORIA = {
  "contraseñas": "Contraseñas", "actualizaciones": "Actualizaciones", "redes": "Redes",
  "respaldo": "Respaldo", "dispositivo": "Dispositivo",
};
const ORDEN_CATEGORIAS = ["contraseñas", "actualizaciones", "dispositivo", "redes", "respaldo"];
const COLOR_RIESGO = { Bajo: "var(--good)", Medio: "var(--warn)", Alto: "var(--critical)" };
const SEV_VAR = { alto: "var(--critical)", medio: "var(--warn)", bajo: "var(--info)" };
const ETIQUETA_SEVERIDAD = { alto: "Alto", medio: "Medio", bajo: "Bajo" };
const ETIQUETA_ESFUERZO = { bajo: "esfuerzo bajo", medio: "esfuerzo medio", alto: "esfuerzo alto" };

let ultimoResultado = null;
let senalesSistema = null;

/* ------------------------------------------------------------------ */
/* Tabs                                                                  */
/* ------------------------------------------------------------------ */

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("panel-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "historial") cargarHistorial();
  });
});

/* ------------------------------------------------------------------ */
/* Sliders en vivo                                                       */
/* ------------------------------------------------------------------ */

const fLongitud = document.getElementById("f-longitud");
const vLongitud = document.getElementById("v-longitud");
fLongitud.addEventListener("input", () => { vLongitud.textContent = fLongitud.value; });

const fDias = document.getElementById("f-dias");
const vDias = document.getElementById("v-dias");
fDias.addEventListener("input", () => { vDias.textContent = fDias.value; });

/* ------------------------------------------------------------------ */
/* Diagnóstico del sistema                                               */
/* ------------------------------------------------------------------ */

document.getElementById("btn-diagnostico").addEventListener("click", async (e) => {
  const btn = e.currentTarget;
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="border-color: var(--line-strong); border-top-color: var(--accent);"></span> Consultando…';

  try {
    const res = await fetch("/api/diagnostico");
    const datos = await res.json();
    renderDiagnostico(datos);
  } catch (err) {
    renderDiagnostico({ ok: false, error: "No se pudo conectar con el servidor." });
  } finally {
    btn.disabled = false;
    btn.innerHTML = original;
  }
});

function renderDiagnostico(datos) {
  const box = document.getElementById("diag-results");
  box.style.display = "grid";

  if (!datos.ok) {
    box.className = "";
    box.innerHTML = `<div class="notice notice-warn" style="grid-column:1/-1">${datos.error || "No se pudo completar el diagnóstico."}</div>`;
    return;
  }

  senalesSistema = datos;

  const items = [
    ["Actualizaciones automáticas", datos.actualizaciones_automaticas],
    ["Días desde última actualización", datos.dias_desde_actualizacion, true],
    ["Firewall activo", datos.firewall_activo],
    ["Antivirus activo", datos.antivirus_activo],
    ["Bloqueo automático de pantalla", datos.bloqueo_automatico],
    ["Disco cifrado", datos.disco_cifrado],
    ["Acceso remoto (RDP) habilitado", datos.acceso_remoto_habilitado],
  ];

  box.className = "diag-results animate-pop";
  box.innerHTML = items.map(([label, valor, esNumero]) => {
    let claseValor = "na", texto = "no disponible";
    if (esNumero) {
      if (valor !== null && valor !== undefined) { claseValor = ""; texto = valor + " días"; }
    } else if (valor === true) { claseValor = "yes"; texto = "Sí"; }
    else if (valor === false) { claseValor = "no"; texto = "No"; }
    return `<div class="diag-item"><div class="label">${label}</div><div class="value ${claseValor}">${texto}</div></div>`;
  }).join("");

  aplicarPrellenado(datos);

  if (datos.errores && datos.errores.length) {
    box.innerHTML += `<div class="notice notice-info" style="grid-column:1/-1; margin-top:.6rem; margin-bottom:0;">Algunos chequeos no se pudieron completar (pueden requerir permisos de administrador).</div>`;
  }
}

function aplicarPrellenado(datos) {
  if (datos.actualizaciones_automaticas !== null && datos.actualizaciones_automaticas !== undefined) {
    document.getElementById("f-auto-updates").checked = datos.actualizaciones_automaticas;
  }
  if (datos.dias_desde_actualizacion !== null && datos.dias_desde_actualizacion !== undefined) {
    const dias = Math.min(365, datos.dias_desde_actualizacion);
    fDias.value = dias;
    vDias.textContent = dias;
    document.getElementById("hint-dias").innerHTML = "Recomendado: menos de 30 días &nbsp;·&nbsp; <span style='color:var(--accent)'>detectado automáticamente</span>";
  }
  if (datos.bloqueo_automatico !== null && datos.bloqueo_automatico !== undefined) {
    document.getElementById("f-bloqueo").checked = datos.bloqueo_automatico;
  }
  if (datos.disco_cifrado !== null && datos.disco_cifrado !== undefined) {
    document.getElementById("f-cifrado").checked = datos.disco_cifrado;
  }
  if (datos.acceso_remoto_habilitado !== null && datos.acceso_remoto_habilitado !== undefined) {
    document.getElementById("f-rdp").checked = datos.acceso_remoto_habilitado;
  }
}

/* ------------------------------------------------------------------ */
/* Envío del formulario                                                  */
/* ------------------------------------------------------------------ */

document.getElementById("cuestionario").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btn-evaluar");
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Calculando…';

  const payload = {};
  document.querySelectorAll("[data-field]").forEach(el => {
    payload[el.dataset.field] = el.type === "checkbox" ? el.checked : Number(el.value);
  });
  if (senalesSistema) payload._senales_sistema = senalesSistema;

  try {
    const res = await fetch("/api/evaluar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    const datos = await res.json();
    if (!datos.ok) throw new Error(datos.error || "Error desconocido");
    ultimoResultado = datos;
    renderResultados(datos);
    actualizarCaseStatus(datos);
    document.getElementById("resultados").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    const cont = document.getElementById("resultados");
    cont.style.display = "block";
    cont.innerHTML = `<div class="notice notice-warn">No se pudo calcular el resultado: ${err.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = original;
  }
});

function actualizarCaseStatus(datos) {
  const el = document.getElementById("case-status");
  const txt = document.getElementById("case-status-text");
  const cat = datos.prediccion.categoria_predicha;
  el.className = "case-status risk-" + cat.toLowerCase();
  txt.textContent = "Riesgo " + cat + " · " + datos.evaluacion.puntaje_global_reglas + "/100";
}

/* ------------------------------------------------------------------ */
/* Render de resultados                                                  */
/* ------------------------------------------------------------------ */

function renderResultados(datos) {
  const ev = datos.evaluacion;
  const pred = datos.prediccion;
  const catML = pred.categoria_predicha;
  const confianza = Math.round((pred.probabilidades[catML] || 0) * 100);
  const puntaje = ev.puntaje_global_reglas;

  const conteo = { alto: 0, medio: 0, bajo: 0 };
  ev.alertas.forEach(a => conteo[a.severidad]++);

  const peorCat = Object.entries(ev.puntajes_por_categoria).sort((a, b) => b[1] - a[1])[0][0];

  const cont = document.getElementById("resultados");
  cont.style.display = "block";

  let html = "";

  if (datos.discrepancias && datos.discrepancias.length) {
    html += `<div class="section-label">Diferencias con el sistema real</div>`;
    datos.discrepancias.forEach(d => {
      html += `<div class="discrepancy"><svg style="width:14px;height:14px;vertical-align:-2px"><use href="#i-alert"/></svg> ${d.etiqueta}: respondiste <span class="mono">${d.reportado}</span>, el sistema detecta <span class="mono">${d.detectado}</span>.</div>`;
    });
  }

  html += `<div class="section-label">Resultado</div>`;
  html += `
    <div class="result-grid">
      <div class="dial-wrap">
        <div id="dial-container"></div>
        <div class="dial-value">Puntaje de riesgo (reglas)</div>
      </div>
      <div class="result-summary">
        <div class="risk-label">Riesgo global · Modelo ML</div>
        <div class="risk-value" style="color:${COLOR_RIESGO[catML]}">${catML}</div>
        <div class="risk-conf">Confianza del modelo: <span class="mono">${confianza}%</span></div>
        <div class="kpi-row">
          <div class="kpi"><div class="kpi-label">Área más riesgosa</div><div class="kpi-value">${NOMBRES_CATEGORIA[peorCat]}</div></div>
          <div class="kpi"><div class="kpi-label">Alertas altas</div><div class="kpi-value" style="color:var(--critical)">${conteo.alto}</div></div>
          <div class="kpi"><div class="kpi-label">Alertas medias</div><div class="kpi-value" style="color:var(--warn)">${conteo.medio}</div></div>
          <div class="kpi"><div class="kpi-label">Alertas bajas</div><div class="kpi-value" style="color:var(--info)">${conteo.bajo}</div></div>
        </div>
      </div>
    </div>`;

  html += `
    <div class="charts-grid">
      <div class="chart-card">
        <h3><svg><use href="#i-shield"/></svg>Mapa de riesgo por área</h3>
        <div class="chart-hint">Más lejos del centro = mayor riesgo en esa área.</div>
        <div id="radar-container"></div>
      </div>
      <div class="chart-card">
        <h3><svg><use href="#i-activity"/></svg>Confianza del modelo</h3>
        <div class="chart-hint">Probabilidad asignada a cada categoría de riesgo.</div>
        <div id="bars-container"></div>
      </div>
    </div>`;

  html += renderPlanAccion(datos.plan);
  html += renderAlertas(ev.alertas, conteo);

  html += `
    <div class="btn-row">
      <button class="btn btn-ghost" id="btn-reset" type="button"><svg><use href="#i-refresh"/></svg>Reiniciar evaluación</button>
      <button class="btn btn-ghost" id="btn-reporte" type="button"><svg><use href="#i-download"/></svg>Descargar reporte (Word)</button>
    </div>`;

  cont.innerHTML = html;

  dibujarDial(puntaje, COLOR_RIESGO[etiquetarRiesgo(puntaje)]);
  dibujarRadar(ev.puntajes_por_categoria, COLOR_RIESGO[catML]);
  dibujarBarras(pred.probabilidades);
  activarSubtabsAlertas();

  document.getElementById("btn-reset").addEventListener("click", () => {
    cont.style.display = "none";
    cont.innerHTML = "";
    document.getElementById("case-status").className = "case-status";
    document.getElementById("case-status-text").textContent = "Sin evaluar todavía";
  });
  document.getElementById("btn-reporte").addEventListener("click", descargarReporte);
}

function etiquetarRiesgo(puntaje) {
  if (puntaje < 35) return "Bajo";
  if (puntaje < 65) return "Medio";
  return "Alto";
}

function renderPlanAccion(plan) {
  let html = `<div class="section-label">Plan de acción priorizado</div>`;
  if (!plan.length) {
    html += `<div class="notice notice-good"><svg style="width:14px;height:14px;vertical-align:-2px"><use href="#i-check"/></svg> No hay acciones pendientes: no se detectaron hábitos de riesgo.</div>`;
    return html;
  }
  const principales = plan.filter(p => p.impacto > 0).slice(0, 5);
  plan.forEach((item, i) => {
    if (!principales.includes(item)) return;
    const rank = i + 1;
    html += `
      <div class="plan-item" style="--sev:${SEV_VAR[item.severidad]}; animation-delay:${i * 70}ms">
        <div class="plan-rank">${rank}</div>
        <div class="plan-body">
          <div class="plan-meta"><span class="plan-cat">${NOMBRES_CATEGORIA[item.categoria]}</span><span class="badge badge-neutral">${ETIQUETA_ESFUERZO[item.esfuerzo]}</span></div>
          <div class="plan-desc">${item.descripcion}</div>
          <div class="plan-rec">${item.recomendacion}</div>
          <div class="plan-impact">${item.puntaje_actual} <span class="arrow">→</span> ${item.puntaje_resultante} &nbsp;(−${item.impacto} pts)</div>
        </div>
      </div>`;
  });
  const resto = plan.filter(p => !principales.includes(p));
  if (resto.length) {
    html += `<details style="margin-top:.6rem"><summary style="cursor:pointer; color:var(--ink-soft); font-size:.88rem; font-family:var(--font-mono)">Ver el resto del plan (${resto.length})</summary><div style="margin-top:.8rem">`;
    resto.forEach(item => {
      html += `
        <div class="plan-item" style="--sev:${SEV_VAR[item.severidad]}">
          <div class="plan-body">
            <div class="plan-meta"><span class="plan-cat">${NOMBRES_CATEGORIA[item.categoria]}</span><span class="badge badge-neutral">${ETIQUETA_ESFUERZO[item.esfuerzo]}</span></div>
            <div class="plan-desc">${item.descripcion}</div>
            <div class="plan-rec">${item.recomendacion}</div>
          </div>
        </div>`;
    });
    html += `</div></details>`;
  }
  return html;
}

function renderAlertas(alertas, conteo) {
  let html = `<div class="section-label">Todas las alertas</div>`;
  if (!alertas.length) {
    html += `<div class="notice notice-good"><svg style="width:14px;height:14px;vertical-align:-2px"><use href="#i-check"/></svg> No se detectaron hábitos de riesgo. ¡Vas muy bien!</div>`;
    return html;
  }
  html += `<div class="subtabs">
    <button class="subtab-btn active" data-sev="todas">Todas (${alertas.length})</button>
    <button class="subtab-btn" data-sev="alto">Alto (${conteo.alto})</button>
    <button class="subtab-btn" data-sev="medio">Medio (${conteo.medio})</button>
    <button class="subtab-btn" data-sev="bajo">Bajo (${conteo.bajo})</button>
  </div>`;
  html += `<div id="alertas-lista">`;
  alertas.forEach(a => {
    html += `
      <div class="alert-card" data-sev="${a.severidad}" style="--sev:${SEV_VAR[a.severidad]}">
        <div class="cat">${NOMBRES_CATEGORIA[a.categoria]} · ${ETIQUETA_SEVERIDAD[a.severidad]}</div>
        <div class="desc">${a.descripcion}</div>
        <div class="rec">${a.recomendacion}</div>
      </div>`;
  });
  html += `</div>`;
  return html;
}

function activarSubtabsAlertas() {
  const botones = document.querySelectorAll(".subtab-btn");
  if (!botones.length) return;
  botones.forEach(btn => {
    btn.addEventListener("click", () => {
      botones.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const sev = btn.dataset.sev;
      document.querySelectorAll("#alertas-lista .alert-card").forEach(card => {
        card.style.display = (sev === "todas" || card.dataset.sev === sev) ? "" : "none";
      });
    });
  });
}

async function descargarReporte(e) {
  if (!ultimoResultado) return;
  const btn = e ? e.currentTarget : document.getElementById("btn-reporte");
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="border-color: var(--line-strong); border-top-color: var(--accent);"></span> Generando…';

  try {
    const res = await fetch("/api/reporte", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ evaluacion: ultimoResultado.evaluacion, prediccion: ultimoResultado.prediccion, plan: ultimoResultado.plan }),
    });
    if (!res.ok) throw new Error("No se pudo generar el reporte.");

    const blob = await res.blob();
    let nombre = "reporte_riesgo_digital.docx";
    const disposicion = res.headers.get("Content-Disposition");
    const match = disposicion && disposicion.match(/filename="?([^"]+)"?/);
    if (match) nombre = match[1];

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = nombre;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("No se pudo descargar el reporte: " + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = original;
  }
}

/* ------------------------------------------------------------------ */
/* Gráficos SVG hechos a mano                                            */
/* ------------------------------------------------------------------ */

function dibujarDial(puntaje, color) {
  const cont = document.getElementById("dial-container");
  const r = 72, cx = 90, cy = 90, stroke = 14;
  const circunferencia = 2 * Math.PI * r;
  const offsetFinal = circunferencia * (1 - puntaje / 100);

  cont.innerHTML = `
    <svg viewBox="0 0 180 180" width="180" height="180">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--paper-sunken)" stroke-width="${stroke}"/>
      <circle id="dial-arc" cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${color}" stroke-width="${stroke}"
        stroke-linecap="round" stroke-dasharray="${circunferencia}" stroke-dashoffset="${circunferencia}"
        transform="rotate(-90 ${cx} ${cy})"/>
      <text id="dial-num" x="${cx}" y="${cy - 4}" text-anchor="middle" font-family="var(--font-display)" font-weight="700" font-size="34" fill="var(--ink)">0</text>
      <text x="${cx}" y="${cy + 20}" text-anchor="middle" font-family="var(--font-mono)" font-size="12" fill="var(--ink-faint)">/ 100</text>
    </svg>`;

  const arc = document.getElementById("dial-arc");
  const numEl = document.getElementById("dial-num");
  requestAnimationFrame(() => {
    arc.style.transition = "stroke-dashoffset 1.1s cubic-bezier(.22,1,.36,1)";
    arc.style.strokeDashoffset = offsetFinal;
  });
  animarNumero(numEl, 0, puntaje, 1100);
}

function animarNumero(el, desde, hasta, duracion) {
  const inicio = performance.now();
  function paso(ahora) {
    const t = Math.min(1, (ahora - inicio) / duracion);
    const ease = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(desde + (hasta - desde) * ease);
    if (t < 1) requestAnimationFrame(paso);
  }
  requestAnimationFrame(paso);
}

function dibujarRadar(puntajes, color) {
  const cont = document.getElementById("radar-container");
  const cats = ORDEN_CATEGORIAS;
  const n = cats.length;
  const cx = 130, cy = 120, rMax = 90;
  const angulo = i => (Math.PI * 2 * i) / n - Math.PI / 2;
  const punto = (i, radio) => [cx + radio * Math.cos(angulo(i)), cy + radio * Math.sin(angulo(i))];

  let grid = "";
  [0.25, 0.5, 0.75, 1].forEach(frac => {
    const pts = cats.map((_, i) => punto(i, rMax * frac).join(",")).join(" ");
    grid += `<polygon points="${pts}" fill="none" stroke="var(--line)" stroke-width="1"/>`;
  });
  let ejes = "", labels = "";
  cats.forEach((cat, i) => {
    const [x, y] = punto(i, rMax);
    ejes += `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="var(--line)" stroke-width="1"/>`;
    const [lx, ly] = punto(i, rMax + 22);
    labels += `<text x="${lx}" y="${ly}" text-anchor="middle" dominant-baseline="middle" font-family="var(--font-mono)" font-size="10.5" fill="var(--ink-soft)">${NOMBRES_CATEGORIA[cat]}</text>`;
  });

  const puntosValor = cats.map((cat, i) => punto(i, (rMax * (puntajes[cat] || 0)) / 100).join(",")).join(" ");

  cont.innerHTML = `
    <svg viewBox="0 0 260 240" width="100%" height="260">
      ${grid}${ejes}
      <polygon id="radar-poly" points="${puntosValor}" fill="${color}" fill-opacity="0.22" stroke="${color}" stroke-width="2"
        style="transform-origin: ${cx}px ${cy}px; transform: scale(0);"/>
      ${labels}
    </svg>`;

  const poly = document.getElementById("radar-poly");
  requestAnimationFrame(() => {
    poly.style.transition = "transform .8s cubic-bezier(.22,1,.36,1)";
    poly.style.transform = "scale(1)";
  });
}

function dibujarBarras(probabilidades) {
  const cont = document.getElementById("bars-container");
  const orden = ["Bajo", "Medio", "Alto"];
  let html = `<div style="display:flex; flex-direction:column; gap:.9rem; padding-top:.4rem">`;
  orden.forEach(cat => {
    const pct = Math.round((probabilidades[cat] || 0) * 100);
    html += `
      <div>
        <div style="display:flex; justify-content:space-between; font-family:var(--font-mono); font-size:.82rem; margin-bottom:.3rem;">
          <span>${cat}</span><span style="font-weight:600">${pct}%</span>
        </div>
        <div style="height:10px; background:var(--paper-sunken); border-radius:999px; overflow:hidden;">
          <div class="bar-fill" data-pct="${pct}" style="height:100%; width:0%; border-radius:999px; background:${COLOR_RIESGO[cat]}; transition: width 1s cubic-bezier(.22,1,.36,1);"></div>
        </div>
      </div>`;
  });
  html += `</div>`;
  cont.innerHTML = html;
  requestAnimationFrame(() => {
    cont.querySelectorAll(".bar-fill").forEach(el => { el.style.width = el.dataset.pct + "%"; });
  });
}

/* ------------------------------------------------------------------ */
/* Historial                                                             */
/* ------------------------------------------------------------------ */

async function cargarHistorial() {
  const cont = document.getElementById("historial-contenido");
  try {
    const res = await fetch("/api/historial");
    const datos = await res.json();
    renderHistorial(datos.filas || []);
  } catch (err) {
    cont.innerHTML = `<div class="notice notice-warn">No se pudo cargar el historial.</div>`;
  }
}

function renderHistorial(filas) {
  const cont = document.getElementById("historial-contenido");

  if (!filas.length) {
    cont.innerHTML = `
      <div class="empty-state">
        <svg><use href="#i-activity"/></svg>
        <p>Todavía no tenés evaluaciones guardadas.<br>Completá el cuestionario en la pestaña <strong>Evaluar</strong> para empezar tu historial.</p>
      </div>`;
    return;
  }

  const primera = filas[0], ultima = filas[filas.length - 1];
  const tendencia = ultima.puntaje_global - primera.puntaje_global;
  const colorTendencia = tendencia <= 0 ? "var(--good)" : "var(--critical)";
  const signo = tendencia > 0 ? "+" : "";

  let html = `
    <div class="hist-kpis">
      <div class="hist-kpi"><div class="label">Evaluaciones guardadas</div><div class="value">${filas.length}</div></div>
      <div class="hist-kpi"><div class="label">Puntaje actual</div><div class="value">${ultima.puntaje_global}/100</div></div>
      <div class="hist-kpi"><div class="label">Cambio desde la primera</div><div class="value" style="color:${colorTendencia}">${signo}${tendencia} pts</div></div>
    </div>
    <div class="chart-card" style="margin-bottom:1.4rem;">
      <h3><svg><use href="#i-activity"/></svg>Tendencia de riesgo</h3>
      <div class="chart-hint">Puntaje global por evaluación en el tiempo.</div>
      <div id="linea-container"></div>
    </div>
    <div class="section-label">Registro de evaluaciones</div>
    <div class="table-scroll">
      <table class="log">
        <thead><tr><th>Fecha</th><th>Puntaje</th><th>Categoría (reglas)</th><th>Categoría (ML)</th></tr></thead>
        <tbody>
          ${filas.slice().reverse().map(f => `
            <tr>
              <td>${formatearFecha(f.fecha)}</td>
              <td>${f.puntaje_global}</td>
              <td><span class="badge badge-${f.categoria_reglas.toLowerCase()}">${f.categoria_reglas}</span></td>
              <td><span class="badge badge-${f.categoria_ml.toLowerCase()}">${f.categoria_ml}</span></td>
            </tr>`).join("")}
        </tbody>
      </table>
    </div>
    <div class="btn-row">
      <button class="btn btn-danger" id="btn-borrar-historial" type="button"><svg><use href="#i-trash"/></svg>Borrar historial</button>
    </div>
    <div id="confirmar-borrado" style="display:none; margin-top:.8rem;">
      <div class="notice notice-warn">¿Seguro que querés borrar todo tu historial? No se puede deshacer.</div>
      <div class="btn-row" style="margin-top:0">
        <button class="btn btn-danger" id="btn-confirmar-borrar" type="button">Sí, borrar todo</button>
        <button class="btn btn-ghost" id="btn-cancelar-borrar" type="button">Cancelar</button>
      </div>
    </div>`;

  cont.innerHTML = html;
  dibujarLineaHistorial(filas);

  document.getElementById("btn-borrar-historial").addEventListener("click", () => {
    document.getElementById("confirmar-borrado").style.display = "block";
  });
  document.getElementById("btn-cancelar-borrar").addEventListener("click", () => {
    document.getElementById("confirmar-borrado").style.display = "none";
  });
  document.getElementById("btn-confirmar-borrar").addEventListener("click", async () => {
    await fetch("/api/historial/borrar", { method: "POST" });
    cargarHistorial();
  });
}

function formatearFecha(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("es-AR", { year: "numeric", month: "2-digit", day: "2-digit" }) +
    " " + d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
}

function dibujarLineaHistorial(filas) {
  const cont = document.getElementById("linea-container");
  const w = 620, h = 220, padL = 34, padR = 12, padT = 16, padB = 24;

  const series = [
    { campo: "puntaje_global", color: "var(--ink)", width: 2.5 },
    { campo: "puntaje_contrasenas", color: "#8a5cf6" },
    { campo: "puntaje_actualizaciones", color: "#2f9bd6" },
    { campo: "puntaje_redes", color: "#e08a2c" },
    { campo: "puntaje_respaldo", color: "#1f8a56" },
    { campo: "puntaje_dispositivo", color: "#c23b2e" },
  ].filter(s => filas.some(f => f[s.campo] !== undefined));

  const n = filas.length;
  const x = i => padL + (n === 1 ? 0 : (i * (w - padL - padR)) / (n - 1));
  const y = v => padT + (100 - v) * ((h - padT - padB) / 100);

  let grid = "";
  [0, 25, 50, 75, 100].forEach(v => {
    grid += `<line x1="${padL}" y1="${y(v)}" x2="${w - padR}" y2="${y(v)}" stroke="var(--line)" stroke-width="1"/>`;
    grid += `<text x="${padL - 8}" y="${y(v) + 3}" text-anchor="end" font-family="var(--font-mono)" font-size="9.5" fill="var(--ink-faint)">${v}</text>`;
  });

  let paths = "";
  series.forEach(s => {
    const pts = filas.map((f, i) => `${x(i)},${y(f[s.campo])}`).join(" ");
    const largo = n * 60 + 60;
    paths += `<polyline points="${pts}" fill="none" stroke="${s.color}" stroke-width="${s.width || 1.5}"
      stroke-linecap="round" stroke-linejoin="round"
      stroke-dasharray="${largo}" stroke-dashoffset="${largo}" class="draw-line"/>`;
  });

  let puntos = "";
  filas.forEach((f, i) => {
    puntos += `<circle cx="${x(i)}" cy="${y(f.puntaje_global)}" r="3.5" fill="var(--paper-raised)" stroke="var(--ink)" stroke-width="2"/>`;
  });

  cont.innerHTML = `<svg viewBox="0 0 ${w} ${h}" width="100%" height="${h}">${grid}${paths}${puntos}</svg>`;

  cont.querySelectorAll(".draw-line").forEach((el, i) => {
    requestAnimationFrame(() => {
      el.style.transition = `stroke-dashoffset 1s ${i * 90}ms cubic-bezier(.22,1,.36,1)`;
      el.style.strokeDashoffset = "0";
    });
  });
}

/* ------------------------------------------------------------------ */
/* Carga inicial                                                         */
/* ------------------------------------------------------------------ */

cargarHistorial();
