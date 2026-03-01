// agenda.js (versão limpa e completa)
// - Vincular usuários via @primeironome no texto (sem select feio)
// - Backend esperado: /api/usuarios, /api/agenda*, conforme seu main.py

let usuariosDisponiveis = []; // [{matricula, nome}]

const board = document.getElementById("agenda-grid");
const btnRecarregar = document.getElementById("btn-recarregar");

// Sem domingo
const diasPt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

async function api(url, opts = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...opts
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Erro ${res.status}`);
  }

  return res.json();
}

function normaliza(s) {
  return (s || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

async function carregarUsuarios() {
  // Usado para resolver @primeironome -> matrícula
  usuariosDisponiveis = await api("/api/usuarios");
}

function extrairMencoesPrimeiroNome(texto) {
  // @ + apenas letras (aceita acentos), mínimo 2 letras
  const re = /@([a-zA-ZÀ-ÿ]{2,})/g;
  const out = new Set();
  let m;
  while ((m = re.exec(texto)) !== null) out.add(normaliza(m[1]));
  return Array.from(out);
}

function resolverPrimeirosNomesParaMatriculas(primeirosNomes) {
  const mapa = new Map(); // primeiroNomeNorm -> [matriculas]

  for (const u of usuariosDisponiveis) {
    const primeiro = normaliza((u.nome || "").split(" ")[0] || "");
    if (!primeiro) continue;

    if (!mapa.has(primeiro)) mapa.set(primeiro, []);
    mapa.get(primeiro).push(String(u.matricula));
  }

  const vinculados = new Set();
  const ambiguos = [];

  for (const p of primeirosNomes) {
    const mats = mapa.get(p) || [];
    if (mats.length === 1) vinculados.add(mats[0]);
    if (mats.length > 1) ambiguos.push(p);
  }

  // Você escolheu primeiro nome; quando for ambíguo, avisamos e não vinculamos.
  if (ambiguos.length) {
    alert(
      "Não consegui vincular: " +
        ambiguos.map(x => `@${x}`).join(", ") +
        " (primeiro nome repetido)"
    );
  }

  return Array.from(vinculados);
}

function fmtDia(iso) {
  const d = new Date(iso + "T00:00:00");
  const dia = String(d.getDate()).padStart(2, "0");
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  return `${dia}/${mes}`;
}

function slotSelector(diaIso, turno) {
  return `.slot[data-dia="${diaIso}"][data-turno="${turno}"]`;
}

function getSlot(diaIso, turno) {
  return document.querySelector(slotSelector(diaIso, turno));
}

function renderSemana(inicioIso, itens) {
  board.innerHTML = "";

  const wrap = document.createElement("div");
  wrap.className = "week-grid";
  board.appendChild(wrap);

  const inicio = new Date(inicioIso + "T00:00:00");

  // 6 dias (Seg–Sáb)
  for (let i = 0; i < 6; i++) {
    const d = new Date(inicio);
    d.setDate(inicio.getDate() + i);
    const iso = d.toISOString().slice(0, 10);

    const col = document.createElement("div");
    col.className = "day-col";

    const head = document.createElement("div");
    head.className = "day-head";

    const title = document.createElement("div");
    title.className = "day-title";
    title.textContent = `${diasPt[i]} (${fmtDia(iso)})`;

    const actions = document.createElement("div");
    actions.className = "day-actions";

    const addBtn = document.createElement("button");
    addBtn.textContent = "+";
    addBtn.onclick = () => criarPostit(iso, "manha");

    const limparBtn = document.createElement("button");
    limparBtn.textContent = "Limpar";
    limparBtn.onclick = () => apagarDia(iso);

    actions.appendChild(addBtn);
    actions.appendChild(limparBtn);

    head.appendChild(title);
    head.appendChild(actions);

    const slotManha = criarSlot(iso, "manha", "07:00–11:00");
    const slotTarde = criarSlot(iso, "tarde", "13:00–17:00");

    col.appendChild(head);
    col.appendChild(slotManha);
    col.appendChild(slotTarde);

    wrap.appendChild(col);
  }

  for (const it of itens) adicionarPostitNoDOM(it);
}

function criarSlot(diaIso, turno, label) {
  const slot = document.createElement("div");
  slot.className = "slot";
  slot.dataset.dia = diaIso;
  slot.dataset.turno = turno;
  slot.dataset.label = label;

  slot.addEventListener("dragover", ev => {
    ev.preventDefault();
    slot.classList.add("dragover");
    ev.dataTransfer.dropEffect = "move";
  });

  slot.addEventListener("dragleave", () => slot.classList.remove("dragover"));

  slot.addEventListener("drop", async ev => {
    ev.preventDefault();
    slot.classList.remove("dragover");

    const postitId = ev.dataTransfer.getData("text/plain");
    if (!postitId) return;

    const card = document.getElementById(`postit-${postitId}`);
    if (!card) return;

    const novoDia = slot.dataset.dia;
    const novoTurno = slot.dataset.turno;

    // Move visual imediato
    slot.appendChild(card);

    // Persiste no backend
    try {
      await api(`/api/agenda/${postitId}`, {
        method: "PATCH",
        body: JSON.stringify({ dia: novoDia, turno: novoTurno })
      });
    } catch (e) {
      console.error(e);
      alert("Erro ao salvar movimentação. Recarregue a página.");
      // Volta ao estado consistente
      await carregar();
    }
  });

  // Botão de criar dentro do slot
  const add = document.createElement("button");
  add.className = "btn";
  add.style.margin = "6px 8px 0 0";
  add.style.background = "rgba(255,255,255,0.75)";
  add.textContent = `+ ${turno === "manha" ? "manhã" : "tarde"}`;
  add.onclick = () => criarPostit(diaIso, turno);

  const bar = document.createElement("div");
  bar.style.display = "flex";
  bar.style.justifyContent = "flex-end";
  bar.appendChild(add);

  slot.appendChild(bar);
  return slot;
}

function adicionarPostitNoDOM(it) {
  const slot = getSlot(it.dia, it.turno || "manha");
  if (!slot) return;

  const card = document.createElement("div");
  card.className = "postit" + (it.feito ? " feito" : "");
  card.id = `postit-${it.id}`;
  card.draggable = true;
  card.dataset.id = it.id;

  // Cor por autor
  if (it.cor) card.style.background = it.cor;

  card.addEventListener("dragstart", ev => {
    ev.dataTransfer.setData("text/plain", String(it.id));
  });

  const top = document.createElement("div");
  top.className = "top";

  const left = document.createElement("div");
  const chk = document.createElement("input");
  chk.type = "checkbox";
  chk.checked = !!it.feito;
  chk.onchange = () => marcarFeito(it.id, chk.checked);
  left.appendChild(chk);

  const right = document.createElement("div");

  const editBtn = document.createElement("button");
  editBtn.className = "icon-btn";
  editBtn.textContent = "Editar";
  editBtn.onclick = () => editarPostit(it.id, it.texto);

  const delBtn = document.createElement("button");
  delBtn.className = "icon-btn";
  delBtn.textContent = "Apagar";
  delBtn.onclick = () => apagarPostit(it.id);

  right.appendChild(editBtn);
  right.appendChild(delBtn);

  top.appendChild(left);
  top.appendChild(right);

  const autor = document.createElement("div");
  autor.className = "autor";
  autor.textContent = it.autor_nome ? `Criado por: ${it.autor_nome}` : (it.matricula ? `Mat.: ${it.matricula}` : "");

  const texto = document.createElement("div");
  texto.className = "texto";
  texto.textContent = it.texto;

  card.appendChild(top);
  card.appendChild(autor);
  card.appendChild(texto);

  slot.appendChild(card);
}

async function carregar() {
  const data = await api("/api/agenda/semana-atual");
  renderSemana(data.inicio, data.itens);
}

async function criarPostit(diaIso, turno) {
  const texto = prompt(
    `Novo post-it (${turno})\n` +
    `Para vincular alguém, use @nome (ex.: @maria)`
  );
  if (!texto) return;

  const mencoes = extrairMencoesPrimeiroNome(texto);
  const vinculados = resolverPrimeirosNomesParaMatriculas(mencoes);

  await api("/api/agenda", {
    method: "POST",
    body: JSON.stringify({ dia: diaIso, turno, texto, vinculados })
  });

  await carregar();
}

async function editarPostit(id, textoAtual) {
  const novoTexto = prompt("Editar texto:", textoAtual);
  if (!novoTexto) return;

  await api(`/api/agenda/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ texto: novoTexto })
  });

  await carregar();
}

async function marcarFeito(id, feito) {
  await api(`/api/agenda/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ feito })
  });

  const card = document.getElementById(`postit-${id}`);
  if (card) card.classList.toggle("feito", !!feito);
}

async function apagarPostit(id) {
  if (!confirm("Apagar este post-it?")) return;

  await api(`/api/agenda/${id}`, { method: "DELETE" });

  const card = document.getElementById(`postit-${id}`);
  if (card) card.remove();
}

async function apagarDia(diaIso) {
  if (!confirm("Apagar todos os post-its deste dia?")) return;

  await api(`/api/agenda/dia/${diaIso}`, { method: "DELETE" });
  await carregar();
}

btnRecarregar.onclick = () => carregar().catch(console.error);

document.addEventListener("DOMContentLoaded", async () => {
  try {
    await carregarUsuarios();
  } catch (e) {
    console.error(e);
    // Se falhar carregar usuários, ainda deixa usar agenda sem vínculos
  }

  await carregar();
});
