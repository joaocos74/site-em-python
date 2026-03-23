


const LICENCA_ID = new URLSearchParams(window.location.search).get('id') || 
                   window.location.pathname.split('/').pop();


function gerarNotificacao(id) {
    window.location.href = `/notificacao/${id}`;
}