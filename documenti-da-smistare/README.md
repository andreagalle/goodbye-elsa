# Documenti da smistare

Cartella di appoggio per i **documenti ufficiali dei fondi che non si scaricano in automatico** (siti che bloccano gli
script, documenti aperti solo con JavaScript, siti non raggiungibili): l'elenco aggiornato è nella dashboard, sezione
*Qualità dei dati → Documenti da recuperare*, e in [`docs/documenti/README.md`](../docs/documenti/README.md).

1. Scarica i PDF dal browser, dalla pagina del fondo, e mettili qui. Il nome del file non conta. Se vuoi essere sicuro
   del fondo, mettili in una sottocartella con il suo id (es. `teseo/`, `arca-previdenza/`, `allianz-previdenza/`:
   gli id sono quelli di `data/fondi.json` e delle cartelle in `docs/documenti/`).
2. Guarda cosa farebbe lo smistamento, senza toccare nulla:
   ```bash
   python scripts/documenti.py smista
   ```
   Per ogni PDF riconosce il fondo (dalla sottocartella, altrimenti dal nome del file e dalle prime pagine) e il tipo
   (Nota informativa, Regolamento, Documento sulle rendite…), e lo abbina al documento mancante del registro
   `data/documenti.csv` più simile. Se il fondo è dubbio, lo lascia qui e lo segnala.
3. Esegui:
   ```bash
   python scripts/documenti.py smista --applica   # sposta i PDF in docs/documenti/<fondo>/, estrae il testo, aggiorna il registro
   python scripts/documenti.py indice             # aggiorna l'indice per il sito
   ```
   Nel registro la copia risulta "fornita a mano" con la data; i documenti che non corrispondono a nessuna riga
   vengono aggiunti come nuovi (controlla il titolo).

I file di questa cartella (tranne questo) sono ignorati da git: non si committano per errore.
