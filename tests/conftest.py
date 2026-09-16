# Iliadbox, le prove automatiche: la cartella del progetto va nel percorso.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
