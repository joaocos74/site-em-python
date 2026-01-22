document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('search-form');
    const btnLimpar = document.getElementById('btn-limpar');

    if (!form || !btnLimpar) return;

    btnLimpar.addEventListener('click', () => {
        // limpa apenas campos de texto, data e selects, mantendo alguns defaults se quiser
        const fields = form.querySelectorAll('input[type="text"], input[type="date"], select');
        fields.forEach((field) => {
            if (field.id === 'orgao' || field.id === 'municipio') {
                return;
            }
            field.value = '';
        });

        // volta o radio para "inicio"
        const radioInicio = form.querySelector('input[name="tipo_data"][value="inicio"]');
        if (radioInicio) radioInicio.checked = true;
    });
});
