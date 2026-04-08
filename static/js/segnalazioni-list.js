(function () {
    var cfg = document.getElementById('page-config').dataset;
    var itemsPerPage = parseInt(cfg.itemsPerPage, 10);

    var currentPage = 1;
    var totalItems = 0;
    var filterManager;
    var tableSorter;
    var currentSort = { by: 'data', order: 'desc' };

    window.currentSort = currentSort;

    function loadData(page, useFilters) {
        var url = '/segnalazioni/api/data/?page=' + page + '&per_page=' + itemsPerPage;
        url += '&sort_by=' + currentSort.by + '&sort_order=' + currentSort.order;

        if (useFilters && filterManager) {
            var filters = filterManager.getActiveFilters();
            var params = new URLSearchParams(filters);
            if (params.toString()) url += '&' + params.toString();
        }

        return fetch(url)
            .then(function (res) {
                if (!res.ok) throw new Error('Errore nel caricamento dei dati');
                return res.json();
            })
            .then(function (response) { updateTable(response, page); return response; })
            .catch(function (error) {
                console.error('Errore:', error);
                document.getElementById('tableBody').innerHTML =
                    '<tr><td colspan="6" style="text-align:center;padding:20px;color:red;">Errore nel caricamento dei dati</td></tr>';
                throw error;
            });
    }

    function updateTable(response, page) {
        var tbody = document.getElementById('tableBody');
        totalItems = response.total;
        var data = response.data;
        currentPage = page;

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:20px;">Nessun dato trovato</td></tr>';
            updatePaginationControls();
            return;
        }

        tbody.innerHTML = '';
        data.forEach(function (row) {
            var tr = document.createElement('tr');
            tr.innerHTML =
                '<td>' + escapeHtml(String(row.id != null ? row.id : '')) + '</td>' +
                '<td>' + escapeHtml(row.titolo != null ? row.titolo : '') + '</td>' +
                '<td>' + escapeHtml(row.categoria != null ? row.categoria : '') + '</td>' +
                '<td>' + escapeHtml(row.stato != null ? row.stato : '') + '</td>' +
                '<td>' + escapeHtml(row.data != null ? row.data : '') + '</td>' +
                '<td>' +
                    '<div class="action-cell">' +
                        '<a href="#" class="link-tabella action-icon-only" title="Apri Segnalazione">' +
                            '<i class="fa-solid fa-eye"></i>' +
                        '</a>' +
                    '</div>' +
                '</td>';
            tbody.appendChild(tr);
        });
        updatePaginationControls();
    }

    function updatePaginationControls() {
        var totalPages = Math.ceil(totalItems / itemsPerPage);
        document.getElementById('pageInfo').textContent = 'Pagina ' + currentPage + ' di ' + (totalPages || 1);
        document.getElementById('prevPage').disabled = currentPage === 1;
        document.getElementById('nextPage').disabled = currentPage === totalPages || totalPages === 0;
    }

    document.getElementById('prevPage').addEventListener('click', function () {
        if (currentPage > 1) {
            if (filterManager) {
                filterManager.reloadData(currentPage - 1, itemsPerPage);
            } else {
                loadData(currentPage - 1);
            }
        }
    });

    document.getElementById('nextPage').addEventListener('click', function () {
        var totalPages = Math.ceil(totalItems / itemsPerPage);
        if (currentPage < totalPages) {
            if (filterManager) {
                filterManager.reloadData(currentPage + 1, itemsPerPage);
            } else {
                loadData(currentPage + 1);
            }
        }
    });

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    document.addEventListener('DOMContentLoaded', function () {
        tableSorter = new TableSorter({
            tableSelector: 'table',
            defaultSort: { by: 'data', order: 'desc' },
            sortableColumns: {
                1: { field: 'titolo' },
                2: { field: 'categoria' },
                3: { field: 'stato' },
                4: { field: 'data' }
            },
            onSortChange: function (field, order) {
                currentSort = { by: field, order: order };
                window.currentSort = currentSort;
                if (filterManager) {
                    filterManager.reloadData(1, itemsPerPage);
                } else {
                    loadData(1);
                }
            }
        });

        filterManager = new FilterManager({
            containerId: 'filters-container',
            dataEndpoint: '/segnalazioni/api/data/',
            filterOptionsEndpoint: '/segnalazioni/api/filters/',
            itemsPerPage: itemsPerPage,
            filters: [
                { field: 'categoria',  label: 'Categoria', type: 'select' },
                { field: 'stato',      label: 'Stato',     type: 'select' },
                { field: 'date_range', label: 'Periodo',   type: 'dateRange' }
            ],
            onDataLoad: function (data, page) { updateTable(data, page); }
        });

        loadData(1);
    });
}());
