const root = document.getElementById("mini-agenda");
const diasPt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

async function api(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function fmtDia(iso) {
  const d = new Date(iso + "T00:00:00");
  const dia = String(d.getDate()).padStart(2, "0");
  const mes = String(d.getMonth() + 1).padStart(2, "0");
  return `${dia}/${mes}`;
}

function render(inicioIso, itens) {
  root.innerHTML = "";

  const inicio = new Date(inicioIso + "T00:00:00");

  for (let i=0; i<6; i++) {
    const d = new Date(inicio);
    d.setDate(inicio.getDate() + i);
    const iso = d.toISOString().slice(0,10);

    const col = document.createElement("div");
    col.className = "day-col day-col--mini";

    const head = document.createElement("div");
    head.className = "day-head";

    const title = document.createElement("div");
    title.className = "day-title";
    title.textContent = `${diasPt[i]} (${fmtDia(iso)})`;

    head.appendChild(title);

    const manha = document.createElement("div");
    manha.className = "slot slot--mini";
    manha.dataset.label = "07–11";

    const tarde = document.createElement("div");
    tarde.className = "slot slot--mini";
    tarde.dataset.label = "13–17";

    // adiciona post-its
    for (const it of itens.filter(x => x.dia === iso && (x.turno || "manha") === "manha")) {
      manha.appendChild(card(it));
    }
    for (const it of itens.filter(x => x.dia === iso && (x.turno || "manha") === "tarde")) {
      tarde.appendChild(card(it));
    }

    col.appendChild(head);
    col.appendChild(manha);
    col.appendChild(tarde);

    root.appendChild(col);
  }
}

function card(it) {
  const c = document.createElement("div");
  c.className = "postit postit--mini" + (it.feito ? " feito" : "");
  if (it.cor) c.style.background = it.cor;

  const t = document.createElement("div");
  t.className = "texto";
  t.textContent = it.texto;

  c.appendChild(t);
  return c;
}

api("/api/agenda/semana-atual/minha")
  .then(data => render(data.inicio, data.itens))
  .catch(err => {
    console.error(err);
    root.innerHTML = "<p>Erro ao carregar mini-agenda</p>";
  });
