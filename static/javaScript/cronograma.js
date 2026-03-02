// ===============================
// CONFIGURAÇÃO
// ===============================
const ANO_CRONOGRAMA = 2026;

const meses = [
    "Janeiro","Fevereiro","Março","Abril",
    "Maio","Junho","Julho","Agosto",
    "Setembro","Outubro","Novembro","Dezembro"
];

// ===============================
// CARREGAR USUÁRIOS
// ===============================
function carregarUsuarios(){

    fetch("/api/usuarios")
        .then(response => response.json())
        .then(data => {

            const select = document.getElementById("filtroFiscal");
            if (!select) return;

            select.innerHTML = "<option value=''>Todos</option>";

            data.forEach(u => {
                const option = document.createElement("option");
                option.value = u.matricula;
                option.textContent = `${u.nome} - ${u.matricula}`;
                select.appendChild(option);
            });
        })
        .catch(error => {
            console.error("Erro ao carregar usuários:", error);
        });
}

// ===============================
// CARREGAR CRONOGRAMA
// ===============================
function carregarCronograma(){

    const selectFiscal = document.getElementById("filtroFiscal");
    if (!selectFiscal) return;

    const fiscal = selectFiscal.value;

    fetch(`/api/cronograma?ano=${ANO_CRONOGRAMA}&fiscal=${fiscal}`)
        .then(response => response.json())
        .then(data => {

            const container = document.getElementById("tabelas");
            if (!container) return;

            container.innerHTML = "";

            // Criar 3 quadrimestres
            for(let q = 1; q <= 3; q++){

                const section = document.createElement("section");
                section.className = "card card--section quadrimestre-section";

                section.innerHTML = `
                    <div class="card__header">
                        <h2>${q}º QUADRIMESTRE</h2>
                    </div>

                    <div class="card__body">
                        <div class="table-wrapper">
                            <table class="cronograma-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Nível</th>
                                        <th>Estabelecimento</th>
                                        <th>CNPJ</th>
                                        <th>Mês Previsto</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="tbody${q}"></tbody>
                            </table>
                        </div>
                    </div>
                `;

                container.appendChild(section);
            }

            // Preencher dados
            data.forEach(e => {

                const quad = e.quadrimestre || 1;
                const tbody = document.getElementById("tbody" + quad);
                if (!tbody) return;

                let status = "A FAZER";
                let classe = "status-afazer";

                if (
                    e.ultima_inspecao &&
                    new Date(e.ultima_inspecao).getFullYear() === ANO_CRONOGRAMA
                ) {
                    status = "REALIZADO";
                    classe = "status-realizado";
                }

                const tr = document.createElement("tr");

                // Montar select de meses
                const select = document.createElement("select");

                meses.forEach((nome, index) => {
                    const option = document.createElement("option");
                    option.value = index + 1;
                    option.textContent = nome;

                    if (e.mes_previsto == index + 1) {
                        option.selected = true;
                    }

                    select.appendChild(option);
                });

                select.addEventListener("change", function(){
                    salvar(e.id, this.value);
                });

                // Montar células
                tr.innerHTML = `
                    <td>${e.id}</td>
                    <td>${e.nivel}</td>
                    <td style="text-align:left">${e.nome_fantasia}</td>
                    <td>${e.cnpj_ou_cpf || ""}</td>
                    <td></td>
                    <td class="${classe}">${status}</td>
                `;

                // Inserir select na 5ª coluna
                tr.children[4].appendChild(select);

                tbody.appendChild(tr);
            });

        })
        .catch(error => {
            console.error("Erro ao carregar cronograma:", error);
        });
}

// ===============================
// SALVAR ALTERAÇÃO
// ===============================
function salvar(cadastro_id, mes){

    const selectFiscal = document.getElementById("filtroFiscal");
    const fiscal = selectFiscal ? selectFiscal.value : "";

    fetch("/api/cronograma", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            cadastro_id: cadastro_id,
            ano: ANO_CRONOGRAMA,
            mes: mes,
            fiscal: fiscal
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Erro ao salvar");
        }
        return response.json();
    })
    .then(() => {
        carregarCronograma();
    })
    .catch(error => {
        console.error("Erro ao salvar:", error);
    });
}

// ===============================
// EVENTOS
// ===============================
document.addEventListener("DOMContentLoaded", function(){

    const btnAtualizar = document.getElementById("btnAtualizar");
    if (btnAtualizar) {
        btnAtualizar.addEventListener("click", carregarCronograma);
    }

    const filtroFiscal = document.getElementById("filtroFiscal");
    if (filtroFiscal) {
        filtroFiscal.addEventListener("change", carregarCronograma);
    }

    carregarUsuarios();
    carregarCronograma();
});