// static/javaScript/estatisticas.js

const $ = (id) => document.getElementById(id);

const COLORS = {
  NIVEL_1: "#bbf16a",
  NIVEL_2: "#5ca3ff",
  NIVEL_3: "#ff5757",
  FEITO: "#1bcb87",
  A_FAZER: "#ffde59",
  INSPECIONADO: "#1bcb87",
  NAO_INSPECIONADO: "#a6a6a6",
  REDESIM: "#5ca3ff",
  DEFAULT: "#5ca3ff"
};

async function fetchJSON(url) {
  const res = await fetch(url, { credentials: "same-origin" });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Erro ${res.status} em ${url}\n${txt}`);
  }
  return res.json();
}

function setOptions(selectEl, items, { includeAll = false, allLabel = "Todos", valueKey = null, labelKey = null } = {}) {
  if (!selectEl) return;

  selectEl.innerHTML = "";

  if (includeAll) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = allLabel;
    selectEl.appendChild(opt);
  }

  items.forEach((it) => {
    const opt = document.createElement("option");
    if (valueKey) {
      opt.value = it[valueKey];
      opt.textContent = labelKey ? it[labelKey] : it[valueKey];
    } else {
      opt.value = it;
      opt.textContent = it;
    }
    selectEl.appendChild(opt);
  });
}

function pickDefaultYear(anos) {
  if (!anos || !anos.length) return new Date().getFullYear();
  return anos[0];
}

function formatPercent(p) {
  if (p === null || p === undefined) return "-";
  return `${String(p).replace(".", ",")}%`;
}

function clearTable(tbodyEl) {
  if (!tbodyEl) return;
  tbodyEl.innerHTML = "";
}

function addRow(tbodyEl, cells) {
  const tr = document.createElement("tr");
  cells.forEach((c) => {
    const td = document.createElement("td");
    td.textContent = c;
    tr.appendChild(td);
  });
  tbodyEl.appendChild(tr);
}

function monthName(m) {
  const nomes = ["", "JANEIRO","FEVEREIRO","MARÇO","ABRIL","MAIO","JUNHO","JULHO","AGOSTO","SETEMBRO","OUTUBRO","NOVEMBRO","DEZEMBRO"];
  return nomes[m] || String(m);
}

function buildQS(params) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && String(v).trim() !== "") p.set(k, v);
  });
  return p.toString();
}

/* =========================
   NORMALIZAÇÃO NÍVEL/LABEL
   ========================= */
function normalizeNivelValue(v) {
  if (v === null || v === undefined) return "";
  const s = String(v).trim();
  if (!s) return "";
  const m = s.match(/\d+/); // pega o primeiro número
  return m ? m[0] : "";
}

function nivelLabel(nivel) {
  const n = normalizeNivelValue(nivel);
  if (!n) return "";               // linha sem identificação => descrição em branco
  return `Nível ${n}`;             // SEM "NIVEL" duplicado
}

function colorByNivel(nivel) {
  const n = normalizeNivelValue(nivel);
  if (n === "1") return COLORS.NIVEL_1;
  if (n === "2") return COLORS.NIVEL_2;
  if (n === "3") return COLORS.NIVEL_3;
  return COLORS.DEFAULT;
}

/* =========================
   CORES DO PIE (por label)
   ========================= */
function pieColorForLabel(label) {
  const k = String(label || "").trim();

  if (k === "FEITO") return COLORS.FEITO;
  if (k === "A FAZER") return COLORS.A_FAZER;

  if (k === "INSPECIONADO") return COLORS.INSPECIONADO;
  if (k === "NÃO INSPECIONADO" || k === "NAO INSPECIONADO") return COLORS.NAO_INSPECIONADO;

  // níveis podem vir como "Nível 1" etc
  if (k === "Nível 1" || k === "Nivel 1") return COLORS.NIVEL_1;
  if (k === "Nível 2" || k === "Nivel 2") return COLORS.NIVEL_2;
  if (k === "Nível 3" || k === "Nivel 3") return COLORS.NIVEL_3;

  return COLORS.DEFAULT;
}

function plotPie(divId, labels, values, title = "") {
  const colors = (labels || []).map(pieColorForLabel);

  const data = [{
    type: "pie",
    labels,
    values,
    hole: 0.35,
    textinfo: "percent",
    marker: { colors, line: { color: "#ffffff", width: 2 } },
    hovertemplate: "%{label}<br>%{value} (%{percent})<extra></extra>",
  }];

  const layout = {
    title: { text: title, font: { size: 12 } },
    margin: { t: 30, r: 10, b: 10, l: 10 },
    paper_bgcolor: "#fff",
    plot_bgcolor: "#fff",
    font: { color: "#222", family: "Arial, Helvetica, sans-serif" },
    legend: { orientation: "h" }
  };

  Plotly.newPlot(divId, data, layout, { responsive: true, displaylogo: false });
}

function plotBar(divId, x, y, title = "", yTitle = "", colors = null) {
  const data = [{
    type: "bar",
    x,
    y,
    marker: { color: colors || COLORS.DEFAULT },
    hovertemplate: "%{x}<br>%{y}<extra></extra>"
  }];

  const layout = {
    title: { text: title, font: { size: 12 } },
    margin: { t: 30, r: 10, b: 80, l: 50 },
    paper_bgcolor: "#fff",
    plot_bgcolor: "#fff",
    font: { color: "#222", family: "Arial, Helvetica, sans-serif" },
    xaxis: { tickangle: -25, gridcolor: "#eee" },
    yaxis: { title: yTitle, gridcolor: "#eee" }
  };

  Plotly.newPlot(divId, data, layout, { responsive: true, displaylogo: false });
}

/* =========================
   CARREGAR FILTROS (DINÂMICO)
   ========================= */
async function loadFilters() {
  const filtros = await fetchJSON("/api/estatisticas/filtros");
  const anoDefault = pickDefaultYear(filtros.anos_inspecao);

  setOptions($("ano_ano"), filtros.anos_inspecao || []);
  setOptions($("classe_ano"), filtros.anos_inspecao || []);
  setOptions($("nivel_ano"), filtros.anos_inspecao || []);
  setOptions($("quad_ano"), filtros.anos_cronograma || (filtros.anos_inspecao || []));
  setOptions($("mes_ano"), filtros.anos_cronograma || (filtros.anos_inspecao || []));
  setOptions($("red_ano"), filtros.anos_redesim || (filtros.anos_inspecao || []));

  if ($("ano_ano")) $("ano_ano").value = anoDefault;
  if ($("classe_ano")) $("classe_ano").value = anoDefault;
  if ($("nivel_ano")) $("nivel_ano").value = anoDefault;

  const anoCrono = pickDefaultYear(filtros.anos_cronograma || filtros.anos_inspecao);
  if ($("quad_ano")) $("quad_ano").value = anoCrono;
  if ($("mes_ano")) $("mes_ano").value = anoCrono;

  const anoRed = pickDefaultYear(filtros.anos_redesim || filtros.anos_inspecao);
  if ($("red_ano")) $("red_ano").value = anoRed;

  const fiscais = filtros.fiscais || [];
  setOptions($("ano_fiscal"), fiscais, { includeAll: true, allLabel: "Todos", valueKey: "matricula", labelKey: "nome" });
  setOptions($("classe_fiscal"), fiscais, { includeAll: true, allLabel: "Todos", valueKey: "matricula", labelKey: "nome" });
  setOptions($("nivel_fiscal"), fiscais, { includeAll: true, allLabel: "Todos", valueKey: "matricula", labelKey: "nome" });
  setOptions($("quad_fiscal"), fiscais, { includeAll: true, allLabel: "Todos", valueKey: "matricula", labelKey: "nome" });
  setOptions($("mes_fiscal"), fiscais, { includeAll: true, allLabel: "Todos", valueKey: "matricula", labelKey: "nome" });

  const classes = filtros.classes || [];
  setOptions($("classe_classe"), classes, { includeAll: true, allLabel: "Todas" });
  setOptions($("red_classe"), classes, { includeAll: true, allLabel: "Todas" });

  const niveis = (filtros.niveis || []).map(String);
  setOptions($("nivel_nivel"), niveis, { includeAll: true, allLabel: "Todos" });
  setOptions($("quad_nivel"), niveis, { includeAll: true, allLabel: "Todos" });
  setOptions($("mes_nivel"), niveis, { includeAll: true, allLabel: "Todos" });

  const nowM = new Date().getMonth() + 1;
  if ($("mes_mes")) $("mes_mes").value = String(nowM);
}

/* =========================
   SEÇÃO: POR ANO
   ========================= */
async function updateAno() {
  const ano = $("ano_ano").value;
  const fiscal = $("ano_fiscal").value;

  const qs = buildQS({ ano, fiscal });
  const r = await fetchJSON("/api/estatisticas/por_ano?" + qs);

  const tbody = $("tblAno").querySelector("tbody");
  clearTable(tbody);
  r.table.forEach((row) => {
    addRow(tbody, [row.ano, row.total, row.feito, formatPercent(row.percentual)]);
  });

  // força labels corretos para as cores baterem
  plotPie("chAno", ["INSPECIONADO", "NÃO INSPECIONADO"], r.chart.values, "Percentual por Ano");
}

/* =========================
   SEÇÃO: POR CLASSE
   ========================= */
async function updateClasse() {
  const ano = $("classe_ano").value;
  const classe = $("classe_classe").value;
  const fiscal = $("classe_fiscal").value;

  const qs = buildQS({ ano, classe, fiscal });
  const r = await fetchJSON("/api/estatisticas/por_classe?" + qs);

  const tbody = $("tblClasse").querySelector("tbody");
  clearTable(tbody);
  r.table.forEach((row) => {
    addRow(tbody, [row.classe, row.total, row.feito, formatPercent(row.percentual)]);
  });

  // barras coloridas por nível (precisa do backend enviar r.chart.nivel)
  const colors = Array.isArray(r.chart?.nivel) ? r.chart.nivel.map(colorByNivel) : null;
  plotBar("chClasse", r.chart.x, r.chart.y, "Percentual por classe (Top 10)", "%", colors);
}

/* =========================
   SEÇÃO: POR NÍVEL  (CORRIGIDA)
   ========================= */
async function updateNivel() {
  const ano = $("nivel_ano").value;
  const nivel = $("nivel_nivel").value;
  const fiscal = $("nivel_fiscal").value;

  const qs = buildQS({ ano, nivel, fiscal });
  const r = await fetchJSON("/api/estatisticas/por_nivel?" + qs);

  const tbody = $("tblNivel").querySelector("tbody");
  clearTable(tbody);

  // Tabela: se nivel vier vazio => descrição em branco
  r.table.forEach((row) => {
    const desc = nivelLabel(row.nivel); // "" ou "Nível 1/2/3"
    addRow(tbody, [
      desc,
      row.total,
      row.feito,
      formatPercent(row.percentual)
    ]);
  });

  // Pizza: limpar labels duplicados e corrigir cores
  // r.chart.labels vem do backend; vamos normalizar para "Nível X" e ignorar vazios
  const pairs = (r.chart.labels || []).map((lb, i) => {
    const n = normalizeNivelValue(lb);
    return { nivel: n, value: (r.chart.values || [])[i] ?? 0 };
  });

  // agrega por nível (caso venha repetido)
  const agg = new Map(); // nivel -> value
  pairs.forEach(p => {
    if (!p.nivel) return; // sem identificação não entra no gráfico
    agg.set(p.nivel, (agg.get(p.nivel) || 0) + Number(p.value || 0));
  });

  const labels = Array.from(agg.keys())
    .sort((a,b) => Number(a) - Number(b))
    .map(n => `Nível ${n}`);

  const values = Array.from(agg.keys())
    .sort((a,b) => Number(a) - Number(b))
    .map(n => agg.get(n));

  plotPie("chNivel", labels, values, "Percentual por nível (feitos)");
}

/* =========================
   SEÇÃO: POR QUADRIMESTRE
   ========================= */
async function updateQuad() {
  const ano = $("quad_ano").value;
  const nivel = $("quad_nivel").value;
  const quadrimestre = $("quad_quad").value;
  const fiscal = $("quad_fiscal").value;

  const qs = buildQS({ ano, nivel, quadrimestre, fiscal });
  const r = await fetchJSON("/api/estatisticas/por_quadrimestre?" + qs);

  const tbody = $("tblQuad").querySelector("tbody");
  clearTable(tbody);
  r.table.forEach((row) => {
    addRow(tbody, [row.quadrimestre + "º", row.total, row.feito, formatPercent(row.percentual)]);
  });

  plotPie("chQuad", ["FEITO", "A FAZER"], r.chart.values, "Percentual por quadrimestre");
}

/* =========================
   SEÇÃO: POR MÊS
   ========================= */
async function updateMes() {
  const ano = $("mes_ano").value;
  const nivel = $("mes_nivel").value;
  const mes = $("mes_mes").value;
  const fiscal = $("mes_fiscal").value;

  const qs = buildQS({ ano, nivel, mes, fiscal });
  const r = await fetchJSON("/api/estatisticas/por_mes?" + qs);

  const tbody = $("tblMes").querySelector("tbody");
  clearTable(tbody);
  r.table.forEach((row) => {
    addRow(tbody, [monthName(parseInt(row.mes, 10)), row.total, row.feito, formatPercent(row.percentual)]);
  });

  plotPie("chMes", ["FEITO", "A FAZER"], r.chart.values, "Percentual por mês");
}

/* =========================
   SEÇÃO: REDESIM
   ========================= */
async function updateRedesim() {
  const ano = $("red_ano").value;
  const classe = $("red_classe").value;

  const qs = buildQS({ ano, classe });
  const r = await fetchJSON("/api/estatisticas/redesim_por_classe?" + qs);

  const tbody = $("tblRedesim").querySelector("tbody");
  clearTable(tbody);
  r.table.forEach((row) => {
    addRow(tbody, [row.classe, row.total]);
  });

  // barras por nível (precisa do backend enviar r.chart.nivel)
  const colors = Array.isArray(r.chart?.nivel) ? r.chart.nivel.map(colorByNivel) : COLORS.REDESIM;
  plotBar("chRedesim", r.chart.x, r.chart.y, "Cadastros REDESIM (Top 10)", "Qtd.", colors);
}

/* =========================
   INIT
   ========================= */
function bindButtons() {
  $("btnAno").addEventListener("click", () => updateAno().catch(console.error));
  $("btnClasse").addEventListener("click", () => updateClasse().catch(console.error));
  $("btnNivel").addEventListener("click", () => updateNivel().catch(console.error));
  $("btnQuad").addEventListener("click", () => updateQuad().catch(console.error));
  $("btnMes").addEventListener("click", () => updateMes().catch(console.error));
  $("btnRedesim").addEventListener("click", () => updateRedesim().catch(console.error));
}

document.addEventListener("DOMContentLoaded", async () => {
  try {
    await loadFilters();
    bindButtons();

    await Promise.all([
      updateAno(),
      updateClasse(),
      updateNivel(),
      updateQuad(),
      updateMes(),
      updateRedesim()
    ]);
  } catch (err) {
    console.error(err);
    alert("Erro ao carregar filtros/estatísticas. Veja o console (F12).");
  }
});
