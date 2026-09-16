# Iliadbox, il contesto: cio' che ogni comando riceve per lavorare.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce con la prima release.

"""Il contesto di una sessione di lavoro.

Un oggetto solo che i comandi ricevono come unico parametro: dentro ci sono
il cliente delle API, l'accesso con i suoi permessi e la configurazione. Cosi'
la firma di un comando non cambia mai, e aggiungere qualcosa che serve a
tutti non obbliga a ritoccare sessanta funzioni.
"""


class Contesto:
    def __init__(self, cliente, accesso, configurazione):
        self.cliente = cliente
        self.accesso = accesso
        self.configurazione = configurazione
        # Lo alza il comando di uscita, e il ciclo principale lo guarda.
        self.uscita = False
        # Le informazioni sulla box, prese all'avvio dalla scoperta.
        self.scoperta = {}
