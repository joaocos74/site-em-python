const map = L.map('map').setView([-15.808, -42.233], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
}).addTo(map);

// =========================
// ÍCONES
// =========================
const iconAzul = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

const iconVerde = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

// =========================
// BUSCA DADOS DO BACKEND
// =========================
fetch('/estabelecimentos')
    .then(response => response.json())
    .then(dados => {

        console.log('Dados recebidos:', dados); // DEBUG

        dados.forEach(local => {

            // =========================
            // TRATAMENTO DA DATA (DD/MM/YYYY)
            // =========================
            let anoInspecao = null;

            if (local.ultima_inspecao && local.ultima_inspecao.includes('/')) {
                const partes = local.ultima_inspecao.split('/');
                anoInspecao = parseInt(partes[2]); // YYYY
            }

            // =========================
            // DEFINE COR DO MARCADOR
            // =========================
            const icone = (anoInspecao === 2026)
                ? iconVerde
                : iconAzul;

            // =========================
            // TEXTO DA DATA
            // =========================
            const ultimaInspecaoTexto = local.ultima_inspecao
                ? local.ultima_inspecao
                : 'Não informada';

            // =========================
            // POPUP
            // =========================
            const popupConteudo = `
                <strong>${local.nome_fantasia || 'Sem nome'}</strong><br>
                Última inspeção: <b>${ultimaInspecaoTexto}</b><br>
                <br>
                <strong>Observações:</strong><br>
                ${local.observacoes || 'Nenhuma observação'}
            `;

            // =========================
            // MARCADOR
            // =========================
            if (local.latitude && local.longitude) {
                L.marker(
                    [parseFloat(local.latitude), parseFloat(local.longitude)],
                    { icon: icone }
                )
                .addTo(map)
                .bindPopup(popupConteudo);
            }
        });
    })
    .catch(error => {
        console.error('Erro ao carregar estabelecimentos:', error);
    });
