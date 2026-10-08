(() => {
    const searchInputs = document.querySelectorAll('[data-search-input]');
    const productCards = [...document.querySelectorAll('[data-product-card]')];
    const categoryButtons = document.querySelectorAll('[data-category-filter]');
    const emptyMessage = document.querySelector('[data-search-empty]');
    let activeCategory = 'all';
    const initialSearch = new URLSearchParams(window.location.search).get('q') || '';
    let searchTerm = initialSearch.trim().toLocaleLowerCase();

    const updateCatalog = () => {
        let visibleCount = 0;
        for (const card of productCards) {
            const matchesCategory = activeCategory === 'all' || card.dataset.category === activeCategory;
            const matchesSearch = card.dataset.search.toLocaleLowerCase().includes(searchTerm);
            card.hidden = !matchesCategory || !matchesSearch;
            if (!card.hidden) visibleCount += 1;
        }
        if (emptyMessage) emptyMessage.hidden = visibleCount > 0;
    };

    if (initialSearch) {
        for (const input of searchInputs) input.value = initialSearch;
        updateCatalog();
    }

    for (const input of searchInputs) {
        input.addEventListener('input', () => {
            searchTerm = input.value.trim().toLocaleLowerCase();
            for (const otherInput of searchInputs) {
                if (otherInput !== input) otherInput.value = input.value;
            }
            updateCatalog();
        });
    }

    for (const button of categoryButtons) {
        button.addEventListener('click', () => {
            activeCategory = button.dataset.categoryFilter;
            for (const choice of categoryButtons) {
                const isSelected = choice === button;
                choice.classList.toggle('is-selected', isSelected);
                choice.setAttribute('aria-pressed', String(isSelected));
            }
            updateCatalog();
        });
    }

    for (const button of document.querySelectorAll('[data-focus-search]')) {
        button.addEventListener('click', () => {
            const input = [...searchInputs].find((searchInput) => searchInput.getClientRects().length > 0);
            input?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            input?.focus();
        });
    }

    const newsletterForm = document.querySelector('[data-newsletter-form]');
    newsletterForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        const note = document.querySelector('[data-newsletter-note]');
        if (note) note.textContent = 'Newsletter sign-up is not available yet.';
        newsletterForm.reset();
    });

    for (const link of document.querySelectorAll('.mobile-menu-panel a')) {
        link.addEventListener('click', () => {
            const menu = link.closest('details');
            if (menu) menu.open = false;
        });
    }
})();