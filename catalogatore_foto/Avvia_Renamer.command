#!/bin/bash
# Spostati nella cartella in cui si trova questo script
cd "$(dirname "$0")"

# Installa automaticamente i pacchetti necessari (Flask) senza mostrare output noiosi
python3 -m pip install flask --quiet

# Avvia il server in background, sganciato dal terminale
nohup python3 app.py > /dev/null 2>&1 &

# Aspetta un paio di secondi per dare tempo al server di avviarsi
sleep 2

# Apri il browser predefinito
open http://127.0.0.1:5000

# Tenta di chiudere automaticamente la finestra del terminale
osascript -e 'tell application "Terminal" to close first window' &
exit
