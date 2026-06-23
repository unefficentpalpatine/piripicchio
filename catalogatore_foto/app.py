import os
import json
import threading
import queue
import signal
import subprocess
import atexit
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, Response

from backend.ollama_api import check_ollama, cleanup_ollama, preload_model, ask_vision_model
from backend.image_processor import get_base64_image, prepare_lightweight_image, extract_keywords
from backend.file_manager import get_unique_filepath

app = Flask(__name__)

last_ping_time = time.time()

# Global state for SSE
log_queue = queue.Queue()
is_processing = False

def push_event(event_type, message, progress=None):
    data = {"type": event_type, "message": message}
    if progress is not None:
        data["progress"] = progress
    log_queue.put(data)

atexit.register(cleanup_ollama)

def process_folder_logic(folder_str, prompt_text):
    global is_processing
    try:
        folder = Path(folder_str)
        valid_extensions = {'.jpg', '.jpeg', '.png', '.dng'}
        
        def ollama_log(msg):
            push_event("log", msg)

        if not check_ollama(log_callback=ollama_log):
            push_event("error", "ERRORE: Ollama non risponde.")
            return
            
        push_event("log", "Pre-caricamento del modello in RAM...")
        preload_model()
        push_event("log", "Modello pronto all'uso.")
            
        files_to_process = [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in valid_extensions]
        total = len(files_to_process)
        
        if total == 0:
            push_event("info", "Nessuna immagine supportata trovata.")
            return

        push_event("log", f"Trovate {total} immagini. Inizio...")
        
        for i, file_path in enumerate(files_to_process):
            prog = (i / total) * 100
            push_event("status", f"Elaborazione {i+1}/{total}: {file_path.name}", prog)
            
            ext = file_path.suffix.lower()
            img_to_read = prepare_lightweight_image(file_path, log_callback=ollama_log)
            
            if not img_to_read:
                push_event("log", f"Salto {file_path.name}: impossibile preparare l'immagine.")
                continue
                
            try:
                base64_img = get_base64_image(img_to_read)
                description = None
                
                # Strategia 5: Meccanismo di Retry (2 tentativi)
                for attempt in range(2):
                    description = ask_vision_model(base64_img, prompt_text, log_callback=ollama_log)
                    if description:
                        break
                    if attempt == 0:
                        push_event("log", f"⚠️ Errore su {file_path.name}, attesa 2s e secondo tentativo...")
                        time.sleep(2)
                        
                if not description:
                    raise Exception("Nessuna descrizione ricevuta dall'API dopo 2 tentativi")
            except Exception as e:
                push_event("log", f"Salto {file_path.name} per errore API: {str(e)}")
                continue
            finally:
                # Assicura sempre la pulizia del temporaneo
                if img_to_read.exists():
                    img_to_read.unlink()
                # Pausa di decompressione per la GPU (eseguita sempre)
                time.sleep(0.5)
                
            words = extract_keywords(description, prompt_text)
            new_path = get_unique_filepath(folder, words, ext, file_path)
            
            # Se il file ha già il nome corretto
            if new_path.absolute() == file_path.absolute():
                push_event("log", f"✅ Il file {file_path.name} ha già il nome ottimale. Salto.")
                continue
                
            try:
                file_path.rename(new_path)
                push_event("log", f"✅ Rinominato: {file_path.name} -> {new_path.name}")
            except Exception as e:
                push_event("log", f"❌ Errore rinomina {file_path.name}: {e}")

        push_event("status", "Completato! Spengo Ollama...", 100)
        
        # Cleanup brutale ed efficace per svuotare la RAM subito
        cleanup_ollama()
            
        push_event("done", "Operazione conclusa con successo.")
        
    except Exception as e:
        push_event("error", f"Errore critico: {e}")
    finally:
        is_processing = False


@app.route('/')
def index():
    return render_template('index.html')

is_dialog_open = False

@app.route('/choose_folder', methods=['POST'])
def choose_folder():
    global is_dialog_open, last_ping_time
    is_dialog_open = True
    last_ping_time = time.time()
    try:
        script = 'tell application "Finder"\n' \
                 'activate\n' \
                 'set folderPath to choose folder with prompt "Seleziona la cartella con le foto"\n' \
                 'return POSIX path of folderPath\n' \
                 'end tell'
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            folder = result.stdout.strip()
            return jsonify({"success": True, "folder": folder})
    except subprocess.TimeoutExpired:
        print("Timeout Applescript")
    except Exception as e:
        print("Errore Applescript:", e)
    finally:
        is_dialog_open = False
        last_ping_time = time.time()
    return jsonify({"success": False, "error": "Selezione annullata o fallita."})

@app.route('/start', methods=['POST'])
def start():
    global is_processing
    if is_processing:
        return jsonify({"success": False, "error": "Già in elaborazione"})
        
    data = request.json
    folder = data.get('folder', '')
    prompt = data.get('prompt', '').strip()
    if not prompt:
        prompt = "return comma separated list of tags"
    
    if not os.path.isdir(folder):
        return jsonify({"success": False, "error": "Cartella non valida"})
        
    is_processing = True
    
    # Svuota la coda
    while not log_queue.empty():
        try:
            log_queue.get_nowait()
        except:
            pass
            
    thread = threading.Thread(target=process_folder_logic, args=(folder, prompt))
    thread.daemon = True
    thread.start()
    
    return jsonify({"success": True})

@app.route('/stream')
def stream():
    def generate():
        while True:
            try:
                # Usiamo timeout per inviare heartbeat e non bloccare i thread permanentemente
                msg = log_queue.get(timeout=5)
                yield f"data: {json.dumps(msg)}\n\n"
            except queue.Empty:
                yield "data: {\"type\": \"heartbeat\"}\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/shutdown', methods=['POST'])
def shutdown():
    def suicide():
        cleanup_ollama()
        os.kill(os.getpid(), signal.SIGKILL)
    # Attende mezzo secondo per dare tempo a Flask di rispondere al browser
    threading.Timer(0.5, suicide).start()
    return jsonify({"success": True})

@app.route('/ping', methods=['GET'])
def ping():
    global last_ping_time
    last_ping_time = time.time()
    return jsonify({"success": True})

def watchdog_loop():
    while True:
        time.sleep(10)
        # Timeout a 120 secondi: previene il blocco se il browser viene minimizzato (throttling JS a 1 minuto)
        if not is_dialog_open and time.time() - last_ping_time > 120:
            cleanup_ollama()
            os.kill(os.getpid(), signal.SIGKILL)

if __name__ == '__main__':
    threading.Thread(target=watchdog_loop, daemon=True).start()
    
    # Pre-carica Ollama
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass
        
    # Rimosso il caricamento in background asincrono per evitare race condition
    import webbrowser
    threading.Timer(1.0, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(host='127.0.0.1', port=5000)
