# Iliadbox, i percorsi: dove stanno i file, da sorgente e da eseguibile.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce con la prima release, usando cartella_applicazione e
# percorso_risorsa di GBUtils come gli altri progetti del parco software.

"""I percorsi di Iliadbox.

Due regole, prese dal memorandum sui percorsi in docs. Cio' che il programma
scrive, cioe' la configurazione con il token e i rapporti salvati, sta
accanto al programma: accanto all'eseguibile quando e' compilato, accanto ai
sorgenti altrimenti. Cio' che il programma legge soltanto, cioe' il manuale e
il changelog, da compilato viaggia dentro il pacchetto, nella cartella
temporanea che PyInstaller apre all'avvio, e li' va cercato per primo.

La radice si ricava a ogni chiamata, mai una volta sola all'importazione del
modulo: una costante calcolata all'import congela il valore e non guarda piu'
se il programma sia compilato.
"""

import os

from GBUtils import cartella_applicazione
from GBUtils import percorso_risorsa as _percorso_risorsa


def radice_app():
    """La cartella del programma: da compilato quella dell'eseguibile.

    Mai la directory di lavoro, che dipende da dove il programma e' stato
    lanciato e non da dove sta. Fino al prototipo il file di configurazione
    veniva cercato nella directory di lavoro, e il programma lanciato da
    un'altra cartella chiedeva di rifare il pairing.
    """
    return cartella_applicazione()


def percorso_risorsa(nome_file):
    """Percorso di una risorsa inclusa nel pacchetto: manuale e changelog."""
    return _percorso_risorsa(nome_file)


def percorso_dati(nome_file):
    """Percorso di lettura e scrittura dei dati dell'utente: config e rapporti."""
    return os.path.join(cartella_applicazione(), nome_file)
