import json
import urllib.request
import urllib.error
import subprocess
import time
import os
import signal

OLLAMA_URL = "http://127.0.0.1:11435/api/generate"
MODEL_NAME = "qwen3.5:0.8b"

ollama_proc = None
requests_count = 0

def check_ollama(log_callback=None):
    global ollama_proc
    
    try:
        req = urllib.request.Request("http://127.0.0.1:11435/")
        with urllib.request.urlopen(req, timeout=1) as response:
            if response.status == 200:
                return True
    except:
        pass
        
    if log_callback:
        log_callback("Avvio server Ollama isolato (Rolling Restart per flush RAM)...")
        
    try:
        my_env = os.environ.copy()
        my_env["OLLAMA_HOST"] = "127.0.0.1:11435"
        
        # Manteniamo comunque questi limiti come rete di sicurezza
        my_env["OLLAMA_MAX_VRAM"] = "2147483648" 
        my_env["OLLAMA_KV_CACHE_TYPE"] = "q8_0"
        
        ollama_proc = subprocess.Popen(
            ["ollama", "serve"], 
            env=my_env, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        
        for _ in range(10):
            time.sleep(1)
            try:
                req = urllib.request.Request("http://127.0.0.1:11435/")
                with urllib.request.urlopen(req, timeout=1) as response:
                    if response.status == 200:
                        return True
            except:
                continue
                
        return False
    except Exception as e:
        if log_callback:
            log_callback(f"Impossibile avviare il server isolato: {e}")
        return False

def cleanup_ollama():
    global ollama_proc
    if ollama_proc:
        try:
            ollama_proc.terminate()
            ollama_proc.wait(timeout=3)
        except:
            pass
        try:
            ollama_proc.kill()
        except:
            pass
        ollama_proc = None

def ask_vision_model(base64_img, prompt_text, log_callback=None):
    global requests_count
    
    # ROLLING RESTART: Ogni 15 foto riavviamo il server isolato. 
    # Questo richiede 5 secondi ogni 15 foto, mantenendo la media a ~2s/foto, 
    # ma stronca definitivamente qualsiasi Memory Leak di Qwen3!
    if requests_count >= 15:
        if log_callback:
            log_callback("Svuotamento forzato della RAM (Rolling Restart in corso)...")
        cleanup_ollama()
        check_ollama(log_callback)
        requests_count = 0
        
    requests_count += 1

    secret_instruction = " (CRITICAL INSTRUCTION: Respond IMMEDIATELY with a comma separated list of tags. Do NOT think. Do NOT explain. Just the tags.)"
    final_prompt = prompt_text + secret_instruction
    
    data = {
        "model": MODEL_NAME,
        "prompt": final_prompt,
        "stream": False,
        "think": False,
        "context": [],
        "images": [base64_img],
        "options": {
            "temperature": 0.7,
            "top_p": 0.80,
            "top_k": 20,
            "min_p": 0.0,
            "repeat_penalty": 1.1,
            "num_predict": 50
        }
    }
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('response', '').strip()
    except Exception as e:
        if log_callback:
            log_callback(f"Errore comunicazione Ollama: {e}")
        return None

def preload_model():
    time.sleep(2)  # Aspetta che ollama serve sia pronto
    
    try:
        data = {
            "model": MODEL_NAME, 
            "prompt": "hi", 
            "stream": False
        }
        req = urllib.request.Request(OLLAMA_URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=30)
        print("Modello pre-caricato in RAM con successo.")
    except Exception as e:
        print(f"Impossibile pre-caricare il modello: {e}")
