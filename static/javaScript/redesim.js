async function buscarCNPJ() {
    const cnpj = document.getElementById("buscar_cnpj").value.trim();

    if (!cnpj) {
        alert("Digite o CNPJ");
        return;
    }

    const response = await fetch(`/api/redesim/buscar_cnpj?cnpj=${cnpj}`);
    const data = await response.json();

    // sempre preenche o campo do formulário
    document.getElementById("cnpj_ou_cpf").value = cnpj;

    if (!data.existe) {
        alert("Estabelecimento não cadastrado.");
        return;
    }

    const d = data.dados;

    document.getElementById("razao_social").value = d.razao_social || "";
    document.getElementById("nome_fantasia").value = d.nome_fantasia || "";
    document.getElementById("nivel").value = d.nivel || "";
    document.getElementById("classe").value = d.classe || "";
    document.getElementById("cnae_principal").value = d.cnae_principal || "";
    document.getElementById("alvara").value = d.alvara || "";
    document.getElementById("fiscal_responsavel").value = d.fiscal_responsavel || "";
    document.getElementById("fiscal_matricula").value = d.fiscal_matricula || "";
    document.getElementById("observacoes").value = d.observacoes || "";

    alert("Estabelecimento encontrado. Dados carregados.");
}

async function verLiberados(){

    const response = await fetch("/api/redesim/listar");
    const dados = await response.json();

    const corpo = document.getElementById("corpo_redesim");

    if (!corpo) return;

    corpo.innerHTML = "";

    dados.forEach(d => {

        const linha = `
        <tr>
            <td>${d.cadastro_id}</td>
            <td>${d.nivel || ""}</td>
            <td>${d.classe || ""}</td>
            <td>${d.razao_social || ""}</td>
            <td>${d.cnpj_ou_cpf || ""}</td>
            <td>${d.alvara || ""}</td>
        </tr>
        `;

        corpo.innerHTML += linha;
    });

    document.getElementById("redesim_resultados").style.display = "block";
}

function exportarExcel(){

    let tabela = document.getElementById("tabela_redesim").outerHTML;

    let data = "data:application/vnd.ms-excel," + encodeURIComponent(tabela);

    let link = document.createElement("a");

    link.href = data;
    link.download = "redesim.xls";

    link.click();
}


