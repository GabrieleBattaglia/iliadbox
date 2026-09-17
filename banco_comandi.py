# Iliadbox, il banco di prova dei comandi: li esegue tutti contro la box vera.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 17/09/2026: entra nel repository, dopo essere servito a collaudare la prima
# release. Fino a ieri viveva nella cartella temporanea di una sessione, e con
# quella sarebbe sparito.

"""Il banco di prova di Iliadbox.

Esegue i comandi uno dopo l'altro contro il router vero e dice quali sono
arrivati in fondo. Serve dopo ogni modifica: le prove di pytest guardano i
formati e il cliente contro risposte finte, qui invece si vede se la box
risponde davvero come il codice si aspetta, che e' l'altra meta' del lavoro.

Non cambia niente a nessuno. Le funzioni che aspettano una scelta, una riga
scritta, una conferma o un tasto vengono sostituite con risposte gia' pronte:
i menu rispondono Escape, le domande rispondono no, le conferme annullano, i
tasti dicono Escape. Cosi' ogni comando percorre tutta la parte che legge e si
ferma sulla soglia di cio' che scriverebbe. Il riavvio resta fuori comunque,
perche' la sua domanda e' l'unica cosa che lo separa dallo spegnere la casa.

Si lancia dalla cartella del progetto:
  python banco_comandi.py            tutti i comandi
  python banco_comandi.py wifi porte  soltanto quelli nominati
Risponde zero se nessun comando e' inciampato, uno altrimenti.
"""

import io
import sys
import traceback

import comandi
import dischi
import formati
import rete
import rete_wifi
import scaricamenti
import servizi
import sicurezza
import sistema
import voip
from iliadbox import prepara

# I moduli in cui vanno sostituite le funzioni che dialogano.
MODULI = [sistema, rete, rete_wifi, sicurezza, dischi, servizi, scaricamenti, voip, comandi, formati]
# Cio' che il banco non esegue: il riavvio spegne la casa, il manuale aspetta
# la lettura, l'uscita non ha niente da provare.
FUORI = {"riavvia", "aiuto", "esci"}


def _scegli(voci, prompt="scegli", mostra=True):
    # Non rispondere niente e' cio' che il menu riceve quando si preme Escape.
    print(f"[menu {prompt}: {len(voci)} voci, rispondo Escape]")
    return


def _elenco_numerato(voci, prompt="scegli"):
    print(f"[menu numerato {prompt}: {len(voci)} voci, rispondo Escape]")
    return


def _chiedi_si_no(domanda, predefinito=None):
    print(f"[domanda: {domanda} -> no]")
    return False


def _chiedi(domanda, tipo="s", **limiti):
    print(f"[richiesta: {domanda} -> vuoto]")
    predefinito = limiti.get("default")
    if predefinito is not None:
        return predefinito
    return 0 if tipo in ("i", "f") else ""


def _conferma(domanda):
    print(f"[conferma: {domanda} -> Escape]")
    return False


def _pausa(testo="premi un tasto"):
    print("[pausa saltata]")


def _key(prompt="", attesa=None, alla_scadenza=""):
    print("[tasto finto: Escape]")
    return "\x1b"


SOSTITUTE = {
    "scegli": _scegli,
    "elenco_numerato": _elenco_numerato,
    "chiedi_si_no": _chiedi_si_no,
    "chiedi": _chiedi,
    "conferma": _conferma,
    "pausa": _pausa,
    "key": _key,
}


def sostituisci():
    """Mette le risposte gia' pronte al posto delle funzioni che dialogano."""
    for modulo in MODULI:
        for nome, finta in SOSTITUTE.items():
            if hasattr(modulo, nome):
                setattr(modulo, nome, finta)


class Doppio:
    """Scrive su due flussi insieme: lo schermo e la cattura.

    Serve a leggere cio' che un comando ha stampato senza toglierlo di sotto
    gli occhi di chi guarda il banco mentre gira.
    """

    def __init__(self, uno, due):
        self.uno = uno
        self.due = due

    def write(self, testo):
        self.uno.write(testo)
        self.due.write(testo)

    def flush(self):
        self.uno.flush()


def esegui_uno(ctx, chiave):
    """Esegue un comando e riferisce com'e' andata, senza mai sollevare."""
    cattura = io.StringIO()
    schermo = sys.stdout
    try:
        sys.stdout = Doppio(schermo, cattura)
        comandi.esegui(ctx, chiave)
    except Exception:  # noqa: BLE001
        sys.stdout = schermo
        traceback.print_exc()
        return "eccezione"
    finally:
        sys.stdout = schermo
    righe_errore = [r for r in cattura.getvalue().splitlines() if r.startswith("Errore:")]
    if righe_errore:
        return "errore della box: " + " | ".join(righe_errore)[:160]
    return "ok"


def main(argomenti=None):
    argomenti = list(sys.argv[1:] if argomenti is None else argomenti)
    sostituisci()
    ctx = prepara()
    if ctx is None:
        print("Non sono riuscita a collegarmi alla box.")
        return 1
    quali = argomenti or [chiave for chiave in comandi.COMANDI if chiave not in FUORI]
    sconosciuti = [chiave for chiave in quali if chiave not in comandi.COMANDI]
    if sconosciuti:
        print(f"Comandi che non esistono: {', '.join(sconosciuti)}")
        return 2
    esiti = {}
    for chiave in quali:
        print(f"\nComando {chiave}")
        esiti[chiave] = esegui_uno(ctx, chiave)
    print("\nRiepilogo del banco")
    for chiave, esito in esiti.items():
        print(f"{chiave}: {esito}")
    inciampati = [chiave for chiave, esito in esiti.items() if esito != "ok"]
    print(f"Comandi provati: {len(esiti)}, arrivati in fondo: {len(esiti) - len(inciampati)}.")
    if inciampati:
        print(f"Da guardare: {', '.join(inciampati)}.")
    ctx.accesso.esci()
    return 1 if inciampati else 0


if __name__ == "__main__":
    sys.exit(main())
