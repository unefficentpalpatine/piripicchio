from pathlib import Path

def get_unique_filepath(folder, words, ext, original_path):
    if not words:
        words = ["immagine", "sconosciuta"]
        
    # Nessun limite assoluto di parole: sfruttiamo la capacità di sintesi di Qwen
    
    # Partiamo da 2 parole (o 1 se c'è solo quella)
    start_len = min(2, len(words))
    
    for i in range(start_len, len(words) + 1):
        base_name = "_".join(words[:i])
        new_name = f"{base_name}{ext}"
        new_path = folder / new_name
        
        # Se il nome è già perfetto e combacia
        if original_path.name == new_name:
            return original_path
            
        if not new_path.exists():
            return new_path
            
    # Se tutte le combinazioni fino al massimo (es. 6 parole) esistono già, usiamo il counter
    base_name = "_".join(words)
    counter = 1
    while True:
        new_name = f"{base_name}_{counter}{ext}"
        new_path = folder / new_name
        if original_path.name == new_name:
            return original_path
        if not new_path.exists():
            return new_path
        counter += 1
