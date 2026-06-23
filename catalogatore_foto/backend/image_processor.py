import base64
import string
import subprocess
from pathlib import Path

def get_base64_image(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def prepare_lightweight_image(file_path, log_callback=None):
    temp_jpg = file_path.with_name(f".temp_img_{file_path.stem}.jpg")
    try:
        subprocess.run(["sips", "-Z", "512", "-s", "format", "jpeg", str(file_path), "--out", str(temp_jpg)], 
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return temp_jpg
    except Exception as e:
        if log_callback:
            log_callback(f"Errore sips (ridimensionamento): {e}")
        return None
import re

def extract_keywords(text, prompt_text=""):
    text = text.lower().strip()
    
    # Rimuovi numeri e tag html comuni (es. <br>)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = ''.join([c for c in text if not c.isdigit()])
    
    # Sostituisci gli "a capo" con le virgole per simulare i tag
    text = text.replace('\n', ',').replace('\r', ',')
    
    # Fallback se non ci sono virgole (frase singola)
    if ',' not in text:
        text = text.translate(str.maketrans('', '', string.punctuation))
        words = [w.strip() for w in text.split() if len(w.strip()) > 2]
    else:
        raw_words = [w.strip() for w in text.split(',')]
        words = []
        for w in raw_words:
            # Pulisci punteggiatura interna
            cleaned = w.translate(str.maketrans('', '', string.punctuation.replace('_','').replace('-','')))
            if cleaned:
                # Usa underscore per parole composte
                cleaned = cleaned.strip().replace(' ', '_')
                # Evita tag vuoti o troppo corti dopo la pulizia
                if len(cleaned) > 2:
                    words.append(cleaned)
                    
    # Filtriamo parole inutili che il modello inserisce spesso per educazione
    stop_words = {'picture', 'image', 'photo', 'photograph', 'shows', 'showing', 'features', 'the', 'a', 'an', 'and', 'of', 'in', 'on', 'with'}
    final_words = []
    
    for w in words:
        # Se il tag stesso è una stop word, ignoralo (se è composto es. "a_cat" teniamo il blocco per intero o lo si divide? Meglio non spaccare i blocchi, ma scartare le preposizioni assolute)
        if w not in stop_words:
            final_words.append(w)
            
    if not final_words:
        final_words = ["immagine", "sconosciuta"]
        
    # Deduce il numero massimo di tag desiderato dal prompt dell'utente
    max_tags = 6 # Default morbido di sicurezza
    if prompt_text:
        nums = [int(n) for n in re.findall(r'\d+', prompt_text) if 0 < int(n) <= 20]
        if nums:
            max_tags = nums[0]
            
    return final_words[:max_tags]
