document.addEventListener('DOMContentLoaded', function () {
    const toggles = document.querySelectorAll('.card__toggle');

    toggles.forEach((btn) => {
        const targetSelector = btn.getAttribute('data-target');
        const panel = document.querySelector(targetSelector);
        if (!panel) return;

        btn.addEventListener('click', () => {
            const isHidden = panel.classList.toggle('is-collapsed');
            panel.style.display = isHidden ? 'none' : 'block';
            btn.textContent = isHidden ? '▸' : '▾';
        });
    });
});
