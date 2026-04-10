// relatorio_inspecao.js
// Contador de não conformidades, salvar, observações e equipe

document.addEventListener('DOMContentLoaded', function () {
    tornarInterativos();
    atualizarContadores();
    document.querySelectorAll('input[type="radio"]').forEach(function (r) {
        r.addEventListener('change', atualizarContadores);
    });
    document.querySelectorAll('textarea.campo-obs-texto').forEach(ativarAutoExpand);
});

// ===== TORNAR [ ] ( ) E ____ INTERATIVOS =====
function tornarInterativos() {
    var contador = 0;

    function processarElemento(el) {
        // Não processar linha de seção nem cabeçalho duplo
        if (el.closest('tr.section-row') || el.closest('tr.dual-header')) return;
        // Não processar dentro de <label> que já tem radio (cat_ac)
        // (essas já têm input real, o ( ) é decorativo)

        var html = el.innerHTML;
        var original = html;

        // [ ] / [  ] / [ X] / [ X ] → checkbox (marcado se tiver X/x)
        html = html.replace(/\[\s*([Xx]?)\s*\]/g, function (_match, x) {
            var checked = x ? ' checked' : '';
            var name = 'cb_' + (contador++);
            return '<input type="checkbox" class="cb-inline" name="' + name + '"' + checked + '>';
        });

        // ( ) fora de <label> → checkbox (sanitários e similares)
        // Evita alterar "(comprovar...)" e similares — só substitui parênteses VAZIOS
        html = html.replace(/\(\s*\)/g, function () {
            // Não substituir se vier imediatamente após letra (parte de texto normal)
            var name = 'cb_' + (contador++);
            return '<input type="checkbox" class="cb-inline" name="' + name + '">';
        });

        // ____+ → input de texto inline
        html = html.replace(/_{3,}/g, function () {
            var name = 'fi_' + (contador++);
            return '<input type="text" class="inline-field" name="' + name + '">';
        });

        if (html !== original) el.innerHTML = html;
    }

    // Células de descrição do checklist (3ª coluna — sem classe especial de coluna)
    document.querySelectorAll(
        '.checklist td:not(.col-num):not(.col-cl):not(.col-s):not(.col-n):not(.col-na):not(.col-leg)'
    ).forEach(processarElemento);

    // Células internas das tabelas col-dual (açougue estrutura física)
    document.querySelectorAll('.col-dual td').forEach(processarElemento);

    // Linha de entrega
    var entrega = document.querySelector('.entrega-linha');
    if (entrega) processarElemento(entrega);

    // Ativa auto-largura em todos os campos inline gerados
    document.querySelectorAll('.inline-field').forEach(ativarAutoLargura);
}

function ativarAutoExpand(el) {
    el.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });
}

// ===== AUTO-LARGURA PARA CAMPOS INLINE =====
function ativarAutoLargura(el) {
    var medidor = document.createElement('span');
    medidor.style.cssText = 'visibility:hidden;position:absolute;white-space:pre;font-size:8.5px;font-family:inherit;padding:0 2px;';
    document.body.appendChild(medidor);

    function ajustar() {
        medidor.textContent = el.value || el.placeholder || ' ';
        var largura = medidor.offsetWidth + 6;
        el.style.width = Math.max(40, largura) + 'px';
    }

    el.addEventListener('input', ajustar);
    ajustar();
}

// ===== CONTADOR DE NÃO CONFORMIDADES =====
function atualizarContadores() {
    var total = 0, crit = 0, maior = 0, outra = 0;

    // Percorre todos os grupos de radio
    var grupos = {};
    document.querySelectorAll('input[type="radio"]').forEach(function (r) {
        if (!r.name || r.name === 'categ' || r.name.startsWith('motivo_') || r.name.startsWith('cat_')) return;
        if (!grupos[r.name]) grupos[r.name] = { checked: null, row: r.closest('tr') };
        if (r.checked) grupos[r.name].checked = r.value;
    });

    Object.keys(grupos).forEach(function (name) {
        var g = grupos[name];
        if (g.checked !== 'N') return; // só conta "Não"
        total++;
        var row = g.row;
        if (!row) return;
        var cl = row.querySelector('.col-cl');
        if (!cl) return;
        var cls = cl.textContent.trim().toUpperCase();
        if (cls === 'C')       crit++;
        else if (cls === 'MA') maior++;
        else                   outra++;
    });

    var elTotal = document.getElementById('nc-total');
    var elC     = document.getElementById('nc-c');
    var elMa    = document.getElementById('nc-ma');
    var elO     = document.getElementById('nc-o');
    var fTotal  = document.getElementById('f_total');
    var fCrit   = document.getElementById('f_crit');
    var fMai    = document.getElementById('f_mai');
    var fOut    = document.getElementById('f_out');

    if (elTotal) elTotal.textContent = total;
    if (elC)     elC.textContent     = crit;
    if (elMa)    elMa.textContent    = maior;
    if (elO)     elO.textContent     = outra;
    if (fTotal)  fTotal.value = total;
    if (fCrit)   fCrit.value  = crit;
    if (fMai)    fMai.value   = maior;
    if (fOut)    fOut.value   = outra;
}

// ===== ADICIONAR LINHA DE OBSERVAÇÃO =====
function addObsRow() {
    var tbody = document.getElementById('obs-tbody');
    if (!tbody) return;
    var idx = tbody.rows.length;
    var tr = document.createElement('tr');
    tr.innerHTML =
        '<td><input class="campo-obs" name="obs_i_' + idx + '"></td>' +
        '<td><textarea class="campo-obs campo-obs-texto" name="obs_t_' + idx + '"></textarea> <button type="button" onclick="this.closest(\'tr\').remove()" style="float:right;font-size:9px;background:#c62828;color:#fff;border:none;border-radius:3px;cursor:pointer;padding:1px 5px">✕</button></td>';
    ativarAutoExpand(tr.querySelector('textarea'));
    tbody.appendChild(tr);
}

// ===== ADICIONAR LINHA DE INSPETOR =====
function addEquipeRow() {
    var tbody = document.getElementById('equipe-tbody');
    if (!tbody) return;
    var idx = tbody.rows.length;
    var tr = document.createElement('tr');
    tr.innerHTML =
        '<td><input class="campo-obs" style="font-size:9.5px" name="insp_' + idx + '"></td>' +
        '<td style="text-align:center"><input class="campo-obs" style="font-size:9.5px;text-align:center" name="mat_' + idx + '"></td>' +
        '<td> <button type="button" onclick="this.closest(\'tr\').remove()" style="float:right;font-size:9px;background:#c62828;color:#fff;border:none;border-radius:3px;cursor:pointer;padding:1px 5px">✕</button></td>';
    tbody.appendChild(tr);
}

// ===== SALVAR RELATÓRIO =====
function salvarRelatorio() {
    var wrapper = document.querySelector('.page-wrapper');
    var cadastroId = wrapper ? wrapper.getAttribute('data-cadastro-id') : '0';

    var dados = { cadastro_id: cadastroId, radios: {}, campos: {}, checkboxes: {} };

    document.querySelectorAll('input[type="radio"]').forEach(function (r) {
        if (r.checked) dados.radios[r.name] = r.value;
    });
    document.querySelectorAll('input[type="checkbox"]').forEach(function (c) {
        dados.checkboxes[c.name] = c.checked;
    });
    document.querySelectorAll('input[type="text"], input:not([type])').forEach(function (i) {
        if (i.name) dados.campos[i.name] = i.value;
    });

    fetch('/salvar_relatorio_alimentacao', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
    })
    .then(function (r) { return r.json(); })
    .then(function (res) {
        alert(res.ok ? 'Relatório salvo com sucesso!' : ('Erro: ' + (res.erro || 'desconhecido')));
    })
    .catch(function () { alert('Erro ao salvar. Verifique a conexão.'); });
}
