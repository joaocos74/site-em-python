const ano = 2026;

function carregarUsuarios(){
    fetch("/api/usuarios")
    .then(r=>r.json())
    .then(data=>{
        const select = document.getElementById("filtroFiscal");
        select.innerHTML = "<option value=''>Todos</option>";
        data.forEach(u=>{
            select.innerHTML += `<option value="${u.matricula}">${u.nome}</option>`;
        });
    });
}

function carregarCronograma(){

    const fiscal = document.getElementById("filtroFiscal").value;

    fetch(`/api/cronograma?ano=${ano}&fiscal=${fiscal}`)
    .then(r=>r.json())
    .then(data=>{

        const container = document.getElementById("tabelas");
        container.innerHTML = "";

        for(let q=1; q<=3; q++){

            const div = document.createElement("div");
            div.className = "quadrimestre";

            div.innerHTML = `
                <h3>${q}º QUADRIMESTRE</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Nível</th>
                            <th>Estabelecimento</th>
                            <th>Mês Previsto</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="tbody${q}"></tbody>
                </table>
            `;

            container.appendChild(div);
        }

        data.forEach(e=>{

            let quad = e.quadrimestre || 1;

            let status = "A FAZER";
            let classe = "status-afazer";

            if(e.ultima_inspecao && new Date(e.ultima_inspecao).getFullYear() == ano){
                status = "REALIZADO";
                classe = "status-realizado";
            }

            const tr = document.createElement("tr");

            tr.innerHTML = `
                <td>${e.nivel}</td>
                <td>${e.nome_fantasia}</td>
                <td>
                    <select onchange="salvar(${e.id}, this.value)">
                        ${[...Array(12).keys()].map(m=>
                            `<option value="${m+1}" ${e.mes_previsto==m+1?"selected":""}>
                                ${m+1}
                            </option>`
                        ).join("")}
                    </select>
                </td>
                <td class="${classe}">${status}</td>
            `;

            document.getElementById("tbody"+quad).appendChild(tr);
        });
    });
}

function salvar(cadastro_id, mes){

    const fiscal = document.getElementById("filtroFiscal").value;

    fetch("/api/cronograma",{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
            cadastro_id,
            ano,
            mes,
            fiscal
        })
    });
}

document.getElementById("filtroFiscal")
    .addEventListener("change",carregarCronograma);

carregarUsuarios();
carregarCronograma();