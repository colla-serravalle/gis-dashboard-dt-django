/**
 * Gestione download PDF via blob con loading overlay
 * Material Design 3 style
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('pdf-download-form');
    const overlay = document.getElementById('pdf-loading-overlay');
    
    if (!form || !overlay) return;

    form.addEventListener('submit', function(e) {
        e.preventDefault(); // Previene il submit normale del form
        
        // Mostra l'overlay di caricamento
        showLoadingOverlay();
        
        // Ottieni i dati del form
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        const url = form.action + '?' + params.toString();
        
        // Effettua la richiesta per scaricare il PDF
        fetch(url, {
            method: 'GET',
            headers: {
                'Accept': 'application/pdf'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Errore nella generazione del PDF');
            }
            return response.blob();
        })
        .then(blob => {
            // Crea un URL temporaneo per il blob
            const url = URL.createObjectURL(blob);
            
            // Crea un link temporaneo e simula il click per scaricare
            const link = document.createElement('a');
            link.href = url;
            link.download = 'verbale_sopralluogo_' + params.get('rowid') + '.pdf';
            document.body.appendChild(link);
            link.click();
            
            // Pulisci
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            // Nascondi l'overlay dopo un breve delay per feedback
            setTimeout(() => {
                hideLoadingOverlay();
            }, 500);
        })
        .catch(error => {
            console.error('Errore durante il download del PDF:', error);
            hideLoadingOverlay();
            
            // Mostra messaggio di errore all'utente
            showErrorMessage('Si è verificato un errore durante la generazione del PDF. Riprova.');
        });
    });
});

/**
 * Mostra l'overlay di caricamento
 */
function showLoadingOverlay() {
    const overlay = document.getElementById('pdf-loading-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
        // Aggiungi animazione fade-in
        setTimeout(() => {
            overlay.style.opacity = '1';
        }, 10);
    }
}

/**
 * Nascondi l'overlay di caricamento
 */
function hideLoadingOverlay() {
    const overlay = document.getElementById('pdf-loading-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 300);
    }
}

/**
 * Mostra un messaggio di errore
 */
function showErrorMessage(message) {
    // Crea un elemento per il messaggio di errore
    const errorDiv = document.createElement('div');
    errorDiv.className = 'pdf-error-message';
    errorDiv.textContent = message;
    errorDiv.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background-color: #d32f2f;
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        z-index: 10001;
        font-family: var(--font-tester);
        font-size: 14px;
        animation: slideDown 0.3s ease-out;
    `;
    
    document.body.appendChild(errorDiv);
    
    // Rimuovi il messaggio dopo 5 secondi
    setTimeout(() => {
        errorDiv.style.animation = 'slideUp 0.3s ease-in';
        setTimeout(() => {
            document.body.removeChild(errorDiv);
        }, 300);
    }, 5000);
}
