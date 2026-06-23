document.addEventListener('DOMContentLoaded', () => {
    const btnChoose = document.getElementById('btn-choose');
    const folderPath = document.getElementById('folder-path');
    const btnStart = document.getElementById('btn-start');
    const promptInput = document.getElementById('prompt');
    const statusLabel = document.getElementById('status-label');
    const progressFill = document.getElementById('progress-fill');
    const logConsole = document.getElementById('log-console');

    let eventSource = null;

    function appendLog(message, type = 'normal') {
        const div = document.createElement('div');
        div.textContent = message;
        if (type === 'error') div.className = 'log-error';
        if (type === 'info') div.className = 'log-info';
        logConsole.appendChild(div);
        logConsole.scrollTop = logConsole.scrollHeight;
    }

    btnChoose.addEventListener('click', async () => {
        btnChoose.disabled = true;
        btnChoose.textContent = "Scelta...";
        
        try {
            const res = await fetch('/choose_folder', { method: 'POST' });
            const data = await res.json();
            
            if (data.success && data.folder) {
                folderPath.value = data.folder;
                appendLog(`Cartella selezionata: ${data.folder}`, 'info');
            } else {
                appendLog(data.error || 'Selezione cartella annullata.', 'error');
            }
        } catch (e) {
            appendLog(`Errore durante la selezione: ${e.message}`, 'error');
        } finally {
            btnChoose.disabled = false;
            btnChoose.textContent = "Scegli Cartella";
        }
    });

    btnStart.addEventListener('click', async () => {
        if (!folderPath.value) {
            alert('Seleziona prima una cartella!');
            return;
        }

        btnStart.disabled = true;
        btnStart.textContent = "ELABORAZIONE IN CORSO...";
        btnChoose.disabled = true;
        logConsole.innerHTML = '';
        progressFill.style.width = '0%';
        statusLabel.textContent = 'Avvio in corso...';
        
        // Listen to server-sent events for logs
        if (eventSource) {
            eventSource.close();
        }
        eventSource = new EventSource('/stream');
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'log') {
                appendLog(data.message);
            } else if (data.type === 'error') {
                appendLog(data.message, 'error');
                statusLabel.textContent = 'Errore riscontrato.';
            } else if (data.type === 'info') {
                appendLog(data.message, 'info');
            } else if (data.type === 'status') {
                statusLabel.textContent = data.message;
                if (data.progress !== undefined) {
                    progressFill.style.width = `${data.progress}%`;
                }
            } else if (data.type === 'done') {
                appendLog(data.message, 'info');
                finishProcessing();
            }
        };

        eventSource.onerror = function() {
            // EventSource might error when finished or disconnected
            console.log("EventSource disconnected.");
        };

        // Start processing backend task
        try {
            const res = await fetch('/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    folder: folderPath.value,
                    prompt: promptInput.value.trim()
                })
            });
            const data = await res.json();
            if (!data.success) {
                appendLog(`Impossibile avviare: ${data.error}`, 'error');
                finishProcessing();
            }
        } catch (e) {
            appendLog('Errore di rete durante l\'avvio.', 'error');
            finishProcessing();
        }
    });

    function finishProcessing() {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        btnStart.disabled = false;
        btnStart.textContent = "AVVIA RINOMINA";
        btnChoose.disabled = false;
    }

    const btnShutdown = document.getElementById('btn-shutdown');
    if (btnShutdown) {
        btnShutdown.addEventListener('click', async () => {
            if (confirm("Sei sicuro di voler spegnere l'applicazione? Il server e Ollama verranno interrotti.")) {
                try {
                    await fetch('/shutdown', { method: 'POST' });
                    document.body.innerHTML = '<div style="display:flex; flex-direction:column; justify-content:center; align-items:center; height:100vh; text-align:center;"><h1 style="color:var(--text-primary); margin-bottom:1rem;">Applicazione Spenta</h1><p style="color:var(--text-secondary);">Il motore locale è stato disattivato e la RAM è stata liberata. Puoi chiudere in sicurezza questa scheda.</p></div>';
                } catch(e) {
                    console.log("Spegnimento effettuato");
                }
            }
        });
    }
    
    // Invia un ping ogni 10 secondi per comunicare al server che la pagina è aperta
    setInterval(() => { fetch('/ping').catch(() => {}); }, 10000);
});
