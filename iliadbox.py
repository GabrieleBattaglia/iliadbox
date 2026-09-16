# Iliadbox, il programma principale: avvio, accesso alla box e ciclo dei comandi.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# Nato come "Iliad BryBox" nel dicembre 2025 dentro la cartella Stuff, diventato
# progetto a se' stante il 16/09/2026 con la prima release pubblica.

"""Iliadbox, il router dalla tastiera.

L'interfaccia web della Iliadbox e' fatta di riquadri, cursori e finestrelle
che uno screen reader attraversa a fatica: questo programma fa le stesse cose
dalla riga di comando, dove ogni informazione e' una riga di testo e ogni
scelta e' un menu che si filtra digitando.

Si puo' usare in due modi. Senza argomenti apre il menu e resta li'; con il
nome di un comando lo esegue e torna alla shell, che e' comodo dentro uno
script o un collegamento sul desktop.
"""

import contextlib
import sys

from GBUtils import menu

from accesso import Accesso
from api import HOST_PREDEFINITO, Client, ErroreAPI, ErroreRete
from comandi import COMANDI, dizionario_menu, esegui
from configurazione import Configurazione
from contesto import Contesto
from formati import dire, errore, titolo
from versione import AUTORI, DATA, NOME, REPOSITORY, VERSIONE


def intestazione():
    """Chi siamo, in tre righe, come fanno tutti i programmi del parco software."""
    dire(f"{NOME} versione {VERSIONE} del {DATA}")
    dire(f"Autori: {AUTORI}")
    dire(f"Il router Iliadbox dalla tastiera, per chi legge con lo screen reader. {REPOSITORY}")


def aiuto_riga_comando():
    """Come si lancia il programma dalla shell."""
    dire("Uso: python iliadbox.py [--host indirizzo] [comando]")
    dire("Senza comando apre il menu. Con un comando lo esegue e torna alla shell.")
    dire("Opzioni: --host indirizzo della box, --elenco per vedere i comandi, --aiuto per questo testo.")


def elenco_comandi_shell():
    """Stampa i comandi con la loro descrizione, per chi guarda dalla shell."""
    for chiave, voce in sorted(COMANDI.items()):
        dire(f"{chiave}: {voce['desc']}")


def prepara(host=None, silenzioso=False):
    """Prepara la sessione: scoperta, associazione se serve, login.

    Restituisce il contesto pronto, oppure None se qualcosa e' andato storto.
    Le frasi che spiegano cosa sta succedendo stanno qui e non nei moduli, che
    cosi' restano muti e riusabili.
    """
    config = Configurazione()
    indirizzo = host or config.leggi("host") or HOST_PREDEFINITO
    cliente = Client(host=indirizzo, porta=config.leggi("porta"))
    accesso = Accesso(cliente, config)
    ctx = Contesto(cliente, accesso, config)
    try:
        ctx.scoperta = cliente.scopri()
    except ErroreRete as guaio:
        errore(guaio)
        dire(f"Controlla che {indirizzo} sia l'indirizzo della box e che il computer sia sulla sua rete.")
        dire("Se la box ha un altro indirizzo, lancia il programma con --host seguito da quello giusto.")
        return None
    if not silenzioso:
        dire(f"Trovata {ctx.scoperta.get('box_model_name', 'una box')} con API versione {ctx.scoperta.get('api_version')} su {indirizzo}.")
    if indirizzo != config.leggi("host"):
        config.scrivi("host", indirizzo)
    if not config.associata:
        dire("Questo computer non e' ancora autorizzato dalla box.")
        dire(
            "L'autorizzazione si da' una volta sola: la box mostra una richiesta sul suo display e aspetta che tu prema la freccia destra."
        )
        try:
            if not accesso.associa():
                return None
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)
            return None
    try:
        permessi = accesso.entra()
    except ValueError as guaio:
        errore(guaio)
        return None
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        dire("Se la box e' stata reimpostata, cancella il file config.json e rifai l'autorizzazione.")
        return None
    if not silenzioso:
        concessi = sum(1 for valore in permessi.values() if valore)
        dire(f"Collegato: {concessi} permessi su {len(permessi)}. Il comando permessi li elenca uno per uno.")
    return ctx


def benvenuto(ctx):
    """Le quattro cose che si vogliono sapere appena entrati."""
    sistema = ctx.cliente.prova("system/") or {}
    connessione = ctx.cliente.prova("connection/") or {}
    ospiti = ctx.cliente.prova("lan/browser/pub/") or []
    attivi = sum(1 for ospite in ospiti if ospite.get("active"))
    sensori = sistema.get("sensors") or []
    calore = f", {sensori[-1].get('value')} gradi" if sensori else ""
    stato_internet = {"up": "internet attiva", "down": "internet caduta"}.get(
        connessione.get("state"), connessione.get("state", "stato sconosciuto")
    )
    titolo(f"{sistema.get('model_info', {}).get('pretty_name', 'Iliadbox')}, firmware {sistema.get('firmware_version', '')}{calore}")
    dire(f"{stato_internet}, {attivi} dispositivi attivi in rete.")
    dire(
        "Digita una parola per filtrare i comandi, Invio per scegliere, Escape per uscire. Scrivi elenco per vederli tutti, aiuto per il manuale."
    )


def ciclo(ctx):
    """Il menu principale: resta li' finche' non si esce."""
    voci = dizionario_menu()
    while not ctx.uscita:
        try:
            scelta = menu(voci, p="iliadbox> ", ntf="nessun comando corrisponde", show=False, keyslist=True, pager=20)
        except KeyboardInterrupt:
            dire("")
            return
        except EOFError:
            return
        if scelta is None:
            return
        try:
            esegui(ctx, scelta)
        except KeyboardInterrupt:
            dire("\nComando interrotto.")
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)


def chiudi(ctx):
    """Chiude la sessione sulla box e saluta."""
    if ctx is None:
        return
    with contextlib.suppress(ErroreAPI, ErroreRete):
        ctx.accesso.esci()
    dire(f"Sessione chiusa dopo {ctx.cliente.chiamate} chiamate alla box. A presto.")


def main(argomenti=None):
    """L'avvio: legge gli argomenti, prepara la sessione e parte."""
    argomenti = list(sys.argv[1:] if argomenti is None else argomenti)
    host = None
    comando = None
    while argomenti:
        pezzo = argomenti.pop(0)
        if pezzo in ("--aiuto", "-h", "--help"):
            intestazione()
            aiuto_riga_comando()
            return 0
        if pezzo in ("--elenco", "-l"):
            elenco_comandi_shell()
            return 0
        if pezzo == "--host":
            if not argomenti:
                errore("--host vuole l'indirizzo della box.")
                return 2
            host = argomenti.pop(0)
        elif pezzo.startswith("--"):
            errore(f"opzione sconosciuta: {pezzo}")
            aiuto_riga_comando()
            return 2
        else:
            comando = pezzo
    if comando and comando not in COMANDI:
        errore(f"comando sconosciuto: {comando}")
        dire("L'elenco completo si ottiene con --elenco.")
        return 2
    if not comando:
        intestazione()
    ctx = prepara(host=host, silenzioso=bool(comando))
    if ctx is None:
        return 1
    try:
        if comando:
            esegui(ctx, comando)
        else:
            benvenuto(ctx)
            ciclo(ctx)
    except KeyboardInterrupt:
        dire("\nInterrotto.")
    finally:
        chiudi(ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
