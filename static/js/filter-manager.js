/**
 * Sistema modulare di filtri per tabelle
 * Permette di filtrare i dati attraverso select multiple
 */
class FilterManager {
    constructor(config) {
        this.config = {
            containerId: config.containerId || 'filters-container',
            dataEndpoint: config.dataEndpoint || '../api/get_data.php',
            filterOptionsEndpoint: config.filterOptionsEndpoint || '../api/get_filter_options.php',
            onDataLoad: config.onDataLoad || null,
            filters: config.filters || [],
            ...config
        };
        
        this.activeFilters = {};
        this.filterOptions = {};
        this.container = null; // cache container element
        this._debounceTimers = new Map();
        this.forceRefresh = false; // Flag per forzare il refresh della cache
        
        this.init();
    }
    
    async init() {
        await this.loadFilterOptions();
        this.renderFilters();
        this.container = document.getElementById(this.config.containerId);
        if (!this.container) {
            console.error(`Container ${this.config.containerId} non trovato`);
            return;
        }
        this.attachEventListeners();
    }
    
    async loadFilterOptions() {
        try {
            const response = await fetch(this.config.filterOptionsEndpoint);
            if (!response.ok) {
                throw new Error('Errore nel caricamento delle opzioni di filtro');
            }
            this.filterOptions = await response.json();
            
        } catch (error) {
            console.error('Errore nel caricamento opzioni filtri:', error);
        }
    }
    
    renderFilters() {
        // render into cached container (set in init)
        const container = this.container || document.getElementById(this.config.containerId);
        if (!container) return;

        let filtersHTML = '<div class="filters-wrapper">';
        
        this.config.filters.forEach(filterConfig => {
            const options = this.filterOptions[filterConfig.field] || [];
            
            if (filterConfig.type === 'dateRange') {
                filtersHTML += this.renderDateRangeFilter(filterConfig);
            } else {
                filtersHTML += this.renderSelectFilter(filterConfig, options);
            }
        });
        
        filtersHTML += `
            <div class="filter-actions">
                <button type="button" id="apply-filters" class="btn btn-primary">
                    <i class="fa-solid fa-filter"></i> Applica Filtri
                </button>
                <button type="button" id="clear-filters" class="btn btn-secondary">
                    <i class="fa-solid fa-filter-circle-xmark"></i> Pulisci
                </button>
                <div class="filter-status" id="filter-status">
                    <i class="fa-solid fa-circle-info"></i>
                    <span>Nessun filtro attivo</span>
                </div>
            </div>
        </div>`;
        
        // Replace HTML in one operation to minimize reflows
        container.innerHTML = filtersHTML;
    }
    
    renderSelectFilter(filterConfig, options) {
        const selectId = `filter-${filterConfig.field}`;
        let optionsHTML = '';
        
        options.forEach((option, index) => {
            const checkboxId = `${selectId}-option-${index}`;
            optionsHTML += `
                <div class="dropdown-option">
                    <input type="checkbox" 
                           id="${checkboxId}" 
                           value="${this.escapeHtml(option.value)}" 
                           data-field="${filterConfig.field}"
                           class="dropdown-checkbox">
                    <label for="${checkboxId}" class="dropdown-label">
                        ${this.escapeHtml(option.label)}
                    </label>
                </div>
            `;
        });
        
        const icons = {
            'nome_operatore': 'fa-user',
            'tratta': 'fa-road',
            'tipologia_appalto': 'fa-tasks'
        };
        
        const icon = icons[filterConfig.field] || 'fa-filter';
        
        return `
            <div class="filter-group">
                <label class="filter-main-label">
                    <i class="fa-solid ${icon}"></i> ${filterConfig.label}
                </label>
                <div class="custom-dropdown" data-field="${filterConfig.field}">
                    <div class="dropdown-trigger" id="${selectId}-trigger">
                        <span class="dropdown-text">Seleziona opzioni</span>
                        <i class="fa-solid fa-chevron-down dropdown-arrow"></i>
                    </div>
                    <div class="dropdown-menu" id="${selectId}-menu">
                        <div class="dropdown-search">
                            <input type="text" 
                                   placeholder="Cerca..." 
                                   class="dropdown-search-input"
                                   id="${selectId}-search">
                            <i class="fa-solid fa-search"></i>
                        </div>
                        <div class="dropdown-actions">
                            <button type="button" class="dropdown-action-btn select-all" data-target="${selectId}">
                                <i class="fa-solid fa-check-double"></i> Seleziona tutto
                            </button>
                            <button type="button" class="dropdown-action-btn deselect-all" data-target="${selectId}">
                                <i class="fa-solid fa-times"></i> Deseleziona tutto
                            </button>
                        </div>
                        <div class="dropdown-options" id="${selectId}-options">
                            ${optionsHTML}
                        </div>
                    </div>
                </div>
                <small class="filter-help">
                    <i class="fa-solid fa-info-circle"></i> 
                    Clicca per aprire il menu e seleziona le opzioni desiderate
                </small>
            </div>
        `;
    }
    
    renderDateRangeFilter(filterConfig) {
        const dateRange = this.filterOptions.date_range || {};
        
        return `
            <div class="filter-group">
                <label>
                    <i class="fa-solid fa-calendar-days"></i> ${filterConfig.label}
                </label>
                <div class="date-range-inputs">
                    <input type="date" 
                           id="filter-date-from" 
                           class="filter-date" 
                           data-field="date_from"
                           min="${dateRange.min || ''}" 
                           max="${dateRange.max || ''}"
                           title="Data inizio periodo">
                    <span class="date-separator">
                        <i class="fa-solid fa-arrow-right"></i>
                    </span>
                    <input type="date" 
                           id="filter-date-to" 
                           class="filter-date" 
                           data-field="date_to"
                           min="${dateRange.min || ''}" 
                           max="${dateRange.max || ''}"
                           title="Data fine periodo">
                </div>
                <small class="filter-help">
                    <i class="fa-solid fa-info-circle"></i> 
                    Lascia vuoto per non limitare l'inizio o la fine
                </small>
            </div>
        `;
    }
    
    attachEventListeners() {
        // Use event delegation on the container to reduce number of listeners
        const base = this.container || document.getElementById(this.config.containerId) || document;

        // Click handler for many actions: trigger toggle, select/deselect all, apply/clear
        base.addEventListener('click', (e) => {
            const target = e.target;

            // Apply filters
            if (target.closest && target.closest('#apply-filters')) {
                e.preventDefault();
                return this.applyFilters();
            }

            // Clear filters
            if (target.closest && target.closest('#clear-filters')) {
                e.preventDefault();
                return this.clearFilters();
            }

            // Dropdown trigger toggle
            const trigger = target.closest && target.closest('.dropdown-trigger');
            if (trigger) {
                e.stopPropagation();
                const dropdown = trigger.closest('.custom-dropdown');
                const menu = dropdown.querySelector('.dropdown-menu');
                const isOpen = menu.classList.contains('open');

                // Close other dropdowns
                (this.container || document).querySelectorAll('.dropdown-menu.open').forEach(openMenu => {
                    if (openMenu !== menu) openMenu.classList.remove('open');
                });

                menu.classList.toggle('open', !isOpen);
                return;
            }

            // Select all / Deselect all buttons
            const selectAllBtn = target.closest && target.closest('.select-all');
            if (selectAllBtn) {
                e.preventDefault();
                const targetId = selectAllBtn.dataset.target;
                return this.selectAllOptions(targetId);
            }

            const deselectAllBtn = target.closest && target.closest('.deselect-all');
            if (deselectAllBtn) {
                e.preventDefault();
                const targetId = deselectAllBtn.dataset.target;
                return this.deselectAllOptions(targetId);
            }

            // Checkbox change handled via change event (attached below)
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest || !e.target.closest('.custom-dropdown')) {
                (this.container || document).querySelectorAll('.dropdown-menu.open').forEach(menu => menu.classList.remove('open'));
            }
        });

        // Handle input events (search) with debounce
        base.addEventListener('input', (e) => {
            const input = e.target;
            if (input.classList && input.classList.contains('dropdown-search-input')) {
                this.debounce(() => this.filterDropdownOptions(input), 200, input);
            }
        });

        // Handle checkbox changes with delegation using change event
        base.addEventListener('change', (e) => {
            const el = e.target;
            if (el.classList && el.classList.contains('dropdown-checkbox')) {
                // Update the trigger text for this dropdown
                this.updateDropdownText(null, el.closest('.custom-dropdown'));
            }
            // Apply on enter for date fields is preserved via keypress on container
        });

        // Keypress on date inputs to auto-apply on Enter
        base.addEventListener('keypress', (e) => {
            const el = e.target;
            if (el.classList && el.classList.contains('filter-date') && e.key === 'Enter') {
                this.applyFilters();
            }
        });
    }
    
    // Simple debounce helper that keys timers by a provided key (element or string)
    debounce(fn, wait = 200, key = '__default') {
        try {
            const k = key || '__default';
            const existing = this._debounceTimers.get(k);
            if (existing) clearTimeout(existing);
            const t = setTimeout(() => {
                try { fn(); } catch (e) { console.error(e); }
                this._debounceTimers.delete(k);
            }, wait);
            this._debounceTimers.set(k, t);
        } catch (e) {
            // Fallback: immediate call
            fn();
        }
    }
    
    filterDropdownOptions(searchInput) {
        const searchText = (searchInput.value || '').toLowerCase();
        const dropdown = searchInput.closest('.custom-dropdown');
        if (!dropdown) return;
        const options = dropdown.querySelectorAll('.dropdown-option');

        options.forEach(option => {
            const labelEl = option.querySelector('.dropdown-label');
            const label = labelEl ? labelEl.textContent.toLowerCase() : '';
            const shouldShow = label.includes(searchText);
            // use class rather than inline style where possible; fallback to inline for compatibility
            option.style.display = shouldShow ? 'flex' : 'none';
        });
    }
    
    selectAllOptions(targetId) {
        const optionsContainer = document.getElementById(targetId + '-options');
        if (!optionsContainer) return;
        const visibleCheckboxes = optionsContainer.querySelectorAll('.dropdown-option:not([style*="display: none"]) .dropdown-checkbox');
        visibleCheckboxes.forEach(checkbox => checkbox.checked = true);
        // update text based on the dropdown element
        const dropdown = optionsContainer.closest('.custom-dropdown');
        this.updateDropdownText(null, dropdown);
    }
    
    deselectAllOptions(targetId) {
        const optionsContainer = document.getElementById(targetId + '-options');
        if (!optionsContainer) return;
        const checkboxes = optionsContainer.querySelectorAll('.dropdown-checkbox');
        checkboxes.forEach(checkbox => checkbox.checked = false);
        const dropdown = optionsContainer.closest('.custom-dropdown');
        this.updateDropdownText(null, dropdown);
    }
    
    // checkbox optional: if provided, we can derive dropdown from it; otherwise pass dropdownElement
    updateDropdownText(checkbox, dropdownElement) {
        const dropdown = dropdownElement || (checkbox ? checkbox.closest('.custom-dropdown') : null);
        if (!dropdown) return;
        const trigger = dropdown.querySelector('.dropdown-trigger');
        const textSpan = trigger ? trigger.querySelector('.dropdown-text') : null;
        if (!textSpan) return;

        const checkedBoxes = dropdown.querySelectorAll('.dropdown-checkbox:checked');
        const count = checkedBoxes.length;

        if (count === 0) {
            textSpan.textContent = 'Seleziona opzioni';
            textSpan.className = 'dropdown-text';
        } else if (count === 1) {
            const label = checkedBoxes[0].nextElementSibling ? checkedBoxes[0].nextElementSibling.textContent : checkedBoxes[0].value;
            textSpan.textContent = label;
            textSpan.className = 'dropdown-text selected';
        } else {
            textSpan.textContent = `${count} opzioni selezionate`;
            textSpan.className = 'dropdown-text selected';
        }
    }
    
    applyFilters() {
        this.activeFilters = {};
        
        // Raccogli valori dai dropdown con checkbox
        document.querySelectorAll('.custom-dropdown').forEach(dropdown => {
            const field = dropdown.dataset.field;
            const checkedBoxes = dropdown.querySelectorAll('.dropdown-checkbox:checked');
            const selectedValues = Array.from(checkedBoxes).map(checkbox => checkbox.value);
            
            if (selectedValues.length > 0) {
                this.activeFilters[field] = selectedValues;
            }
        });
        
        // Raccogli valori dalle date
        const dateFrom = document.getElementById('filter-date-from')?.value;
        const dateTo = document.getElementById('filter-date-to')?.value;
        
        if (dateFrom) {
            this.activeFilters.date_from = dateFrom;
        }
        if (dateTo) {
            this.activeFilters.date_to = dateTo;
        }
        
        this.updateFilterStatus();
        
        // Chiudi tutti i dropdown aperti
        document.querySelectorAll('.dropdown-menu.open').forEach(menu => {
            menu.classList.remove('open');
        });
        
        // IMPORTANTE: Quando si applicano i filtri, torna sempre a pagina 1
        // Usa itemsPerPage dalla configurazione o dalla pagina
        const perPage = this.config.itemsPerPage || window.itemsPerPage || 10;
        this.loadFilteredData(1, perPage);
    }
    
    clearFilters() {
        this.activeFilters = {};
        
        // Pulisci tutti i checkbox nei dropdown
        document.querySelectorAll('.dropdown-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        // Aggiorna il testo dei dropdown
        document.querySelectorAll('.custom-dropdown').forEach(dropdown => {
            const textSpan = dropdown.querySelector('.dropdown-text');
            textSpan.textContent = 'Seleziona opzioni';
            textSpan.className = 'dropdown-text';
        });
        
        // Pulisci le ricerche nei dropdown
        document.querySelectorAll('.dropdown-search-input').forEach(input => {
            input.value = '';
            this.filterDropdownOptions(input);
        });
        
        // Pulisci i campi data
        document.querySelectorAll('.filter-date').forEach(input => {
            input.value = '';
        });
        
        this.updateFilterStatus();
        
        // Forza refresh della cache alla prossima chiamata
        this.forceRefresh = true;
        
        // Ricarica i dati senza filtri a pagina 1
        const perPage = this.config.itemsPerPage || window.itemsPerPage || 10;
        this.loadFilteredData(1, perPage);
    }
    
    async loadFilteredData(page = 1, perPage = null) {
        try {
            // Mostra loading
            this.setLoadingState(true);
            
            // Se perPage non è specificato, usa quello dalla configurazione o dalla pagina
            if (perPage === null) {
                perPage = this.config.itemsPerPage || window.itemsPerPage || 10;
            }
            
            const queryString = this.buildQueryParams(page, perPage, this.activeFilters);
            const response = await fetch(`${this.config.dataEndpoint}?${queryString}`);
            if (!response.ok) {
                throw new Error('Errore nel caricamento dei dati filtrati');
            }
            
            const data = await response.json();
            
            // Chiama la callback se fornita
            if (this.config.onDataLoad) {
                this.config.onDataLoad(data, page);
            }
            
            return data;
        } catch (error) {
            console.error('Errore nel caricamento dati filtrati:', error);
            throw error;
        } finally {
            // Nascondi loading
            this.setLoadingState(false);
        }
    }

    // Build query string ensuring arrays are appended as repeated params (preferred by PHP)
    buildQueryParams(page, perPage, filters) {
        const params = new URLSearchParams();
        params.append('page', page);
        params.append('per_page', perPage);

        // Aggiungi i parametri di ordinamento se disponibili
        if (window.currentSort) {
            params.append('sort_by', window.currentSort.by);
            params.append('sort_order', window.currentSort.order);
        }

        // Se è richiesto un force refresh, aggiungi il parametro
        if (this.forceRefresh) {
            params.append('force_refresh', '1');
            this.forceRefresh = false; // Reset del flag
        }

        Object.keys(filters || {}).forEach(key => {
            const val = filters[key];
            if (Array.isArray(val)) {
                // append each value separately so PHP receives it as array
                val.forEach(v => params.append(key + '[]', v));
            } else if (val !== undefined && val !== null && val !== '') {
                params.append(key, val);
            }
        });

        return params.toString();
    }
    
    // Metodo pubblico per ricaricare i dati (utilizzabile dall'esterno)
    reloadData(page = 1, perPage = null) {
        // Se perPage non è specificato, usa quello dalla configurazione
        if (perPage === null) {
            perPage = this.config.itemsPerPage || window.itemsPerPage || 10;
        }
        return this.loadFilteredData(page, perPage);
    }
    
    // Metodo per ottenere i filtri attivi (utilizzabile dall'esterno)
    getActiveFilters() {
        return { ...this.activeFilters };
    }
    
    updateFilterStatus() {
        const statusElement = document.getElementById('filter-status');
        if (!statusElement) return;
        
        const span = statusElement.querySelector('span');
        const activeCount = Object.keys(this.activeFilters).length;
        
        if (activeCount === 0) {
            span.textContent = 'Nessun filtro attivo';
            statusElement.className = 'filter-status';
        } else {
            span.textContent = `${activeCount} filtri attivi`;
            statusElement.className = 'filter-status active';
        }
    }
    
    setLoadingState(loading) {
        const applyBtn = document.getElementById('apply-filters');
        const clearBtn = document.getElementById('clear-filters');
        
        if (loading) {
            if (applyBtn) {
                applyBtn.disabled = true;
                applyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Caricamento...';
            }
            if (clearBtn) {
                clearBtn.disabled = true;
            }
        } else {
            if (applyBtn) {
                applyBtn.disabled = false;
                applyBtn.innerHTML = '<i class="fa-solid fa-filter"></i> Applica Filtri';
            }
            if (clearBtn) {
                clearBtn.disabled = false;
            }
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Esporta la classe per l'uso globale
window.FilterManager = FilterManager;