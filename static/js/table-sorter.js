/**
 * TableSorter - Sistema per l'ordinamento delle tabelle
 * Semplice, scalabile e riutilizzabile
 */
class TableSorter {
    constructor(config) {
        this.tableSelector = config.tableSelector || 'table';
        this.onSortChange = config.onSortChange || (() => {});
        this.sortableColumns = config.sortableColumns || {};
        this.currentSort = {
            by: config.defaultSort?.by || null,
            order: config.defaultSort?.order || 'desc'
        };
        
        this.init();
    }
    
    init() {
        this.setupSortableHeaders();
    }
    
    setupSortableHeaders() {
        const table = document.querySelector(this.tableSelector);
        if (!table) return;
        
        const headers = table.querySelectorAll('thead th');
        
        headers.forEach((header, index) => {
            const columnConfig = this.sortableColumns[index];
            if (!columnConfig) return;
            
            // Crea il contenitore per il titolo e l'icona
            const headerContent = header.innerHTML;
            header.innerHTML = '';
            
            const container = document.createElement('div');
            container.className = 'sortable-header';
            container.style.cssText = 'display: flex; align-items: center; justify-content: space-between; cursor: pointer; user-select: none;';
            
            const title = document.createElement('span');
            title.innerHTML = headerContent;
            
            const icon = document.createElement('i');
            icon.className = 'fas fa-sort sort-icon';
            icon.style.cssText = 'margin-left: 8px; opacity: 0.5; transition: opacity 0.2s;';
            
            container.appendChild(title);
            container.appendChild(icon);
            header.appendChild(container);
            
            // Aggiungi event listener
            container.addEventListener('click', () => {
                this.handleSort(columnConfig.field, icon);
            });
            
            // Imposta l'icona iniziale se questo è il campo di ordinamento predefinito
            if (this.currentSort.by === columnConfig.field) {
                this.updateSortIcon(icon, this.currentSort.order);
            }
        });
    }
    
    handleSort(field, icon) {
        let newOrder = 'asc';
        
        if (this.currentSort.by === field) {
            // Se clicchiamo sulla stessa colonna, inverti l'ordine
            newOrder = this.currentSort.order === 'asc' ? 'desc' : 'asc';
        } else {
            // Se cambiamo colonna, ripristina tutte le altre icone
            this.resetAllIcons();
        }
        
        this.currentSort = {
            by: field,
            order: newOrder
        };
        
        this.updateSortIcon(icon, newOrder);
        this.onSortChange(field, newOrder);
    }
    
    updateSortIcon(icon, order) {
        icon.style.opacity = '1';
        if (order === 'asc') {
            icon.className = 'fas fa-sort-up sort-icon';
        } else {
            icon.className = 'fas fa-sort-down sort-icon';
        }
    }
    
    resetAllIcons() {
        const icons = document.querySelectorAll('.sort-icon');
        icons.forEach(icon => {
            icon.className = 'fas fa-sort sort-icon';
            icon.style.opacity = '0.5';
        });
    }
    
    getCurrentSort() {
        return { ...this.currentSort };
    }
    
    setSort(field, order) {
        this.currentSort = { by: field, order: order };
        
        // Aggiorna le icone
        this.resetAllIcons();
        const table = document.querySelector(this.tableSelector);
        if (table) {
            const headers = table.querySelectorAll('thead th');
            headers.forEach((header, index) => {
                const columnConfig = this.sortableColumns[index];
                if (columnConfig && columnConfig.field === field) {
                    const icon = header.querySelector('.sort-icon');
                    if (icon) {
                        this.updateSortIcon(icon, order);
                    }
                }
            });
        }
    }
}