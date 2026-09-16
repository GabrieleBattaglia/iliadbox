# Iliadbox, utilita': prepara l'archivio per la distribuzione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce con la prima release, e come negli altri progetti il
# mestiere sta in crea_archivio_release di GBUtils.

"""Comprime il risultato di PyInstaller in un solo archivio.

Iliadbox si compila in un file unico, quindi dentro dist c'e' soltanto
l'eseguibile e tutto il resto viaggia dentro di lui.

Restano fuori il file di configurazione, che contiene il token di chi ha
compilato, e i rapporti, che nascono accanto all'eseguibile appena lo si
prova e portano gli indirizzi e i nomi dei dispositivi di casa sua.
"""

import sys

from GBUtils import crea_archivio_release

FUORI = [
    "config.json",
    "iliadbox-*.txt",
]


def main():
    try:
        crea_archivio_release("iliadbox", cartella_dist="dist", escludi=FUORI)
    except (FileNotFoundError, OSError) as guaio:
        print(f"Archivio non creato: {guaio}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
