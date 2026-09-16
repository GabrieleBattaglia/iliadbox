# Iliadbox, la configurazione: il file accanto al programma con il token e le preferenze.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dalla config.py del prototipo, con il file cercato accanto
# al programma invece che nella directory di lavoro e senza mai stampare il token.

"""La configurazione di Iliadbox.

Un file JSON, config.json, accanto al programma. Dentro ci stanno il token
dell'applicazione, che vale quanto una password perche' da solo apre il
router, l'indirizzo della box e qualche preferenza. Per questo il file e'
escluso da git e il token non viene mai stampato: quando serve dire che c'e',
si dice che c'e' e basta.
"""

import json
import os

from percorsi import percorso_dati

NOME_FILE = "config.json"
# L'identificativo con cui il router conosce questa applicazione. Non si cambia
# a cuor leggero: il token e' legato a questo nome, e cambiandolo il router
# chiede di rifare l'associazione premendo il tasto sul suo display.
APP_ID_PREDEFINITO = "it.iliad.brybox"


class Configurazione:
    """Legge e scrive config.json, e risponde alle domande su cosa c'e' dentro."""

    def __init__(self, percorso=None):
        self.percorso = percorso or percorso_dati(NOME_FILE)
        self.dati = self._leggi()

    def _leggi(self):
        if not os.path.exists(self.percorso):
            return {}
        try:
            with open(self.percorso, encoding="utf-8") as file_entrata:
                dati = json.load(file_entrata)
            return dati if isinstance(dati, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def salva(self):
        """Scrive il file. Solleva OSError se il disco non collabora."""
        with open(self.percorso, "w", encoding="utf-8") as file_uscita:
            json.dump(self.dati, file_uscita, indent=4, ensure_ascii=False)

    def leggi(self, chiave, predefinito=None):
        return self.dati.get(chiave, predefinito)

    def scrivi(self, chiave, valore):
        self.dati[chiave] = valore
        self.salva()

    def togli(self, chiave):
        if chiave in self.dati:
            del self.dati[chiave]
            self.salva()

    @property
    def token(self):
        return self.dati.get("app_token")

    @property
    def app_id(self):
        return self.dati.get("app_id", APP_ID_PREDEFINITO)

    @property
    def associata(self):
        """Vero quando c'e' un token, cioe' quando l'associazione e' gia' fatta."""
        return bool(self.token)
