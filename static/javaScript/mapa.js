const map = L.map('map').setView([-15.808, -42.233], 13);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap'
}).addTo(map);

// Ícones
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

fetch('/estabelecimentos')
    .then(response => response.json())
    .then(dados => {

        console.log(dados); // DEBUG

        dados.forEach(local => {

            // Converte a data da última inspeção
            let anoInspecao = null;

            if (local.ultima_inspecao) {
            anoInspecao = parseInt(local.ultima_inspecao.substring(0, 4));
            }

            // Define cor do marcador
            const icone = (anoInspecao === 2026) ? iconVerde : iconAzul;

            // Texto da inspeção
            const ultimaInspecaoTexto = local.ultima_inspecao
                ? local.ultima_inspecao
                : 'Não informada';

            // Conteúdo do popup usando OBSERVAÇÕES
            const popupConteudo = `
                <strong>${local.nome_fantasia || 'Sem nome'}</strong><br>
                Última inspeção: <b>${ultimaInspecaoTexto}</b><br>
                Observações:<br>
                ${local.observacoes || 'Nenhuma observação'}
            `;

            L.marker([local.latitude, local.longitude], { icon: icone })
                .addTo(map)
                .bindPopup(popupConteudo);
        });
    });
