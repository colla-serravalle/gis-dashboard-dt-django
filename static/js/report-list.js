(function () {
    var cfg = document.getElementById('page-config').dataset;
    var itemsPerPage = parseInt(cfg.itemsPerPage, 10);
    var reportDetailUrl = cfg.reportDetailUrl;
    var labels = {
        nome_operatore: cfg.labelNomeOperatore,
        tratta: cfg.labelTratta,
        tipologia_appalto: cfg.labelTipologiaAppalto,
    };

    var currentPage = 1;
    var totalItems = 0;
    var filterManager;
    var tableSorter;
    var currentSort = { by: 'data_rilevamento', order: 'desc' };

    window.currentSort = currentSort;

    function loadData(page, useFilters) {
        var url = '/api/data/?page=' + page + '&per_page=' + itemsPerPage;
        url += '&sort_by=' + currentSort.by + '&sort_order=' + currentSort.order;

        if (useFilters && filterManager) {
            var filters = filterManager.getActiveFilters();
            var params = new URLSearchParams(filters);
            if (params.toString()) {
                url += '&' + params.toString();
            }
        }

        return fetch(url)
            .then(function (res) {
                if (!res.ok) {
                    throw new Error('Errore nel caricamento dei dati');
                }
                return res.json();
            })
            .then(function (response) {
                console.log('Dati ricevuti dal server:', response);
                updateTable(response, page);
                return response;
            })
            .catch(function (error) {
                console.error('Errore:', error);
                var tbody = document.getElementById('tableBody');
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px; color: red;">Errore nel caricamento dei dati</td></tr>';
                throw error;
            });
    }

    function updateTable(response, page) {
        var tbody = document.getElementById('tableBody');
        totalItems = response.total;
        var data = response.data;
        currentPage = page;

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 20px;">Nessun dato trovato</td></tr>';
            updatePaginationControls();
            return;
        }

        tbody.innerHTML = '';

        data.forEach(function (row) {
            var tr = document.createElement('tr');
            tr.innerHTML =
                '<td>' + escapeHtml(row.uniquerowid.replace(/^{|}$/g, '')) + '</td>' +
                '<td>' + escapeHtml(row.nome_operatore) + '</td>' +
                '<td>' + escapeHtml(row.tratta) + '</td>' +
                '<td>' + escapeHtml(row.tipologia_appalto) + '</td>' +
                '<td>' + escapeHtml(row.data_rilevamento) + '</td>' +
                '<td>' +
                    '<div class="action-cell">' +
                        '<a href="/reports/pdf/?rowid=' + encodeURIComponent(row.uniquerowid) + '"' +
                           ' class="link-tabella action-icon-only action-download"' +
                           ' title="Scarica PDF"' +
                           ' download>' +
                            '<i class="fa-solid fa-file-arrow-down"></i>' +
                        '</a>' +
                        '<a href="' + reportDetailUrl + '?id=' + encodeURIComponent(row.uniquerowid) + '"' +
                           ' class="link-tabella action-icon-only"' +
                           ' title="Apri Report">' +
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

    function handleSortChange(field, order) {
        currentSort = { by: field, order: order };
        window.currentSort = currentSort;

        if (filterManager) {
            filterManager.reloadData(1, itemsPerPage);
        } else {
            loadData(1);
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        tableSorter = new TableSorter({
            tableSelector: 'table',
            defaultSort: {
                by: 'data_rilevamento',
                order: 'desc'
            },
            sortableColumns: {
                1: { field: 'nome_operatore' },
                2: { field: 'tratta' },
                3: { field: 'tipologia_appalto' },
                4: { field: 'data_rilevamento' }
            },
            onSortChange: handleSortChange
        });

        filterManager = new FilterManager({
            containerId: 'filters-container',
            dataEndpoint: '/api/data/',
            filterOptionsEndpoint: '/api/filters/',
            itemsPerPage: itemsPerPage,
            filters: [
                {
                    field: 'nome_operatore',
                    label: labels.nome_operatore,
                    type: 'select'
                },
                {
                    field: 'tratta',
                    label: labels.tratta,
                    type: 'select'
                },
                {
                    field: 'tipologia_appalto',
                    label: labels.tipologia_appalto,
                    type: 'select'
                },
                {
                    field: 'date_range',
                    label: 'Periodo',
                    type: 'dateRange'
                }
            ],
            onDataLoad: function (data, page) {
                updateTable(data, page);
            }
        });

        loadData(1);

        document.getElementById('tableBody').addEventListener('click', function (e) {
            var btn = e.target.closest('.action-download');
            if (!btn) return;
            e.preventDefault();

            var url = btn.href;
            var rowid = new URL(url).searchParams.get('rowid');

            showLoadingOverlay();

            fetch(url, {
                method: 'GET',
                headers: { 'Accept': 'application/pdf' }
            })
            .then(function (response) {
                if (!response.ok) throw new Error('Errore nella generazione del PDF');
                return response.blob();
            })
            .then(function (blob) {
                var blobUrl = URL.createObjectURL(blob);
                var link = document.createElement('a');
                link.href = blobUrl;
                link.download = 'verbale_sopralluogo_' + rowid + '.pdf';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(blobUrl);
                setTimeout(function () { hideLoadingOverlay(); }, 500);
            })
            .catch(function (error) {
                console.error('Errore durante il download del PDF:', error);
                hideLoadingOverlay();
                showErrorMessage('Si è verificato un errore durante la generazione del PDF. Riprova.');
            });
        });
    });
}());
