# Iliadbox, il gestore degli scaricamenti: code, torrent, avanzamento e velocita'.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce con la prima release, dalla voce "download manager" che il
# prototipo aveva lasciato nella lista delle cose da fare.

"""Gli scaricamenti che la box porta avanti da sola.

Il gestore della box scarica anche a computer spento, e mette i file sul
disco: e' il motivo per cui conviene usarlo invece del browser. Un compito
puo' essere un file preso dal web, un torrent o un gruppo di notizie; qui si
aggiunge, si mette in pausa, si riprende e si toglie, e si segue
l'avanzamento con una riga che si riscrive dentro i quaranta caratteri.

L'aggiunta e' l'unico punto delle API che non vuole il JSON ma i campi di una
form, e infatti passa da una funzione apposta del cliente.
"""

from GBUtils import key

from api import ErroreAPI, ErroreRete
from dischi import codifica, decodifica
from formati import (
    chiedi,
    chiedi_si_no,
    conferma,
    data_ora,
    dimensione,
    dire,
    durata_breve,
    errore,
    incolonna,
    intero,
    prompt_compatto,
    riga,
    scegli,
    si_no,
    taglia,
    titolo,
    velocita_byte,
)

STATI = {
    "stopped": "ferma",
    "queued": "in coda",
    "starting": "sta partendo",
    "downloading": "scarica",
    "stopping": "si sta fermando",
    "error": "errore",
    "done": "finita",
    "checking": "verifica",
    "repairing": "ripara",
    "extracting": "estrae",
    "seeding": "condivide",
    "retry": "riprova",
}


def _riga_compito(compito):
    """Uno scaricamento in una riga sola."""
    stato = STATI.get(compito.get("status"), compito.get("status", ""))
    fatto = compito.get("rx_pct", 0) / 100 if compito.get("rx_pct") is not None else 0
    return (
        f"{incolonna(taglia(compito.get('name', ''), 40), 40)} {incolonna(stato, 14)} "
        f"{incolonna(f'{fatto:.0f}%', 5)} {incolonna(velocita_byte(compito.get('rx_rate'), 0), 11)} {dimensione(compito.get('size'))}"
    )


def righe_scaricamenti(cliente):
    """Gli scaricamenti in corso, uno per riga, con il riassunto in testa."""
    statistiche = cliente.prova("downloads/stats/") or {}
    compiti = cliente.prova("downloads/") or []
    righe = [
        f"Scaricamenti in elenco: {len(compiti)}",
        f"In corso {statistiche.get('nb_tasks_downloading', 0)}, in coda {statistiche.get('nb_tasks_queued', 0)}, "
        f"finiti {statistiche.get('nb_tasks_done', 0)}, in errore {statistiche.get('nb_tasks_error', 0)}",
        f"Velocita' complessiva: {velocita_byte(statistiche.get('rx_rate'))} in discesa, {velocita_byte(statistiche.get('tx_rate'))} in salita",
    ]
    righe += [_riga_compito(c) for c in compiti]
    return righe


def scaricamenti(ctx):
    """Il gestore degli scaricamenti: cosa c'e', cosa si aggiunge, cosa si toglie."""
    titolo("Scaricamenti")
    try:
        compiti = ctx.cliente.get("downloads/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for testo in righe_scaricamenti(ctx.cliente):
        dire(testo)
    voci = {
        "aggiungi": "Aggiungi uno scaricamento da un indirizzo",
        "segui": "Segui uno scaricamento in corso",
        "ferma": "Ferma o riprendi uno scaricamento",
        "togli": "Togli uno scaricamento",
        "dettaglio": "Dettaglio di uno scaricamento",
        "diario": "Leggi il diario di uno scaricamento",
        "feed": "Feed RSS che la box sorveglia",
        "impostazioni": "Impostazioni del gestore",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "aggiungi":
            _aggiungi(ctx)
            return
        if scelta == "impostazioni":
            _impostazioni(ctx)
            return
        if scelta == "feed":
            _feed(ctx)
            return
        if not compiti:
            dire("Non c'e' nessuno scaricamento.")
            return
        voci_compiti = {str(c.get("id")): _riga_compito(c) for c in compiti}
        quale = scegli(voci_compiti, "quale scaricamento")
        if not quale:
            return
        compito = next(c for c in compiti if str(c.get("id")) == quale)
        if scelta == "segui":
            _segui(ctx, quale)
        elif scelta == "ferma":
            fermo = compito.get("status") in ("stopped", "error", "done")
            nuovo = "downloading" if fermo else "stopped"
            ctx.cliente.put(f"downloads/{quale}", dati={"status": nuovo})
            dire(f"Scaricamento {'ripreso' if fermo else 'fermato'}.")
        elif scelta == "togli":
            cancella = chiedi_si_no("Vuoi cancellare anche i file gia' scaricati?", False)
            if not conferma("Invio toglie, Esc annulla"):
                dire("\nAnnullato.")
                return
            ctx.cliente.delete(f"downloads/{quale}/erase" if cancella else f"downloads/{quale}")
            dire("\nTolto.")
        elif scelta == "dettaglio":
            _dettaglio(ctx, compito)
        elif scelta == "diario":
            diario = ctx.cliente.prova(f"downloads/{quale}/log") or ""
            dire(diario or "Il diario e' vuoto.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _aggiungi(ctx):
    """Aggiunge uno scaricamento da un indirizzo web o da un magnet."""
    indirizzo = chiedi("Indirizzo da scaricare, http, ftp o magnet: ", "s", smin=4, smax=4096).strip()
    if not indirizzo:
        return
    cartella = ""
    config = ctx.cliente.prova("downloads/config/") or {}
    predefinita = decodifica(config.get("download_dir", "")) if config.get("download_dir") else ""
    if predefinita:
        dire(f"Cartella predefinita: {predefinita}")
    if chiedi_si_no("Vuoi metterlo in un'altra cartella?", False):
        cartella = chiedi("Cartella sul disco della box: ", "s", smin=1, smax=512).strip()
    campi = {"download_url": indirizzo}
    if cartella:
        campi["download_dir"] = codifica(cartella)
    try:
        risposta = ctx.cliente.posta_modulo("downloads/add", campi)
        dire(f"Aggiunto, numero {risposta.get('id')}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _segui(ctx, numero):
    """Segue uno scaricamento con una riga che si riscrive.

    La riga sta nei quaranta caratteri: p e' la percentuale, v la velocita' in
    discesa, m il tempo che manca.
    """
    dire("Premi Escape per smettere di seguirlo: lo scaricamento va avanti lo stesso.")
    while True:
        try:
            compito = ctx.cliente.get(f"downloads/{numero}")
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)
            return
        fatto = (compito.get("rx_pct") or 0) / 100
        prompt_compatto(f"p{fatto:.0f}% v{velocita_byte(compito.get('rx_rate'), 0)} m{durata_breve(compito.get('eta'))}")
        if compito.get("status") in ("done", "error", "stopped", "seeding"):
            dire("")
            dire(f"Stato: {STATI.get(compito.get('status'), compito.get('status'))}.")
            return
        if key(attesa=1, alla_scadenza=None) == "\x1b":
            dire("")
            return


def _dettaglio(ctx, compito):
    """Tutto quello che il gestore sa di uno scaricamento."""
    titolo(taglia(compito.get("name", ""), 60))
    riga("Stato", STATI.get(compito.get("status"), compito.get("status")))
    riga("Tipo", compito.get("type"))
    riga("Dimensione", dimensione(compito.get("size")))
    riga("Scaricato", f"{dimensione(compito.get('rx_bytes'))}, cioe' il {(compito.get('rx_pct') or 0) / 100:.1f} per cento")
    riga("Inviato", dimensione(compito.get("tx_bytes")))
    riga("Velocita' in discesa", velocita_byte(compito.get("rx_rate")))
    riga("Velocita' in salita", velocita_byte(compito.get("tx_rate")))
    riga("Tempo che manca", durata_breve(compito.get("eta")))
    riga("Creato", data_ora(compito.get("created_ts")))
    riga("Cartella", decodifica(compito.get("download_dir", "")))
    if compito.get("error") and compito.get("error") != "none":
        riga("Errore", compito.get("error"))
    if compito.get("type") == "bt":
        for etichetta, indirizzo in (("File", "files"), ("Tracker", "trackers"), ("Peer", "peers")):
            elenco = ctx.cliente.prova(f"downloads/{compito.get('id')}/{indirizzo}") or []
            riga(etichetta, intero(len(elenco)))


def _feed(ctx):
    """I feed RSS che la box sorveglia per scaricare da sola le novita'."""
    titolo("Feed RSS")
    dire("La box guarda ogni tanto questi indirizzi e scarica da sola cio' che vi compare.")
    try:
        elenco = ctx.cliente.get("downloads/feeds/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Feed sorvegliati: {len(elenco)}")
    for feed in elenco:
        dire(f"{incolonna(taglia(feed.get('title') or feed.get('url', ''), 40), 40)} {'automatico' if feed.get('auto_download') else 'a mano'} {feed.get('nb_unread', 0)} non letti")
    voci = {"aggiungi": "Aggiungi un feed", "togli": "Togli un feed", "aggiorna": "Chiedi alla box di rileggerli", "niente": "Torna indietro"}
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "aggiungi":
            indirizzo = chiedi("Indirizzo del feed: ", "s", smin=8, smax=1024).strip()
            if indirizzo:
                ctx.cliente.post("downloads/feeds/", dati={"url": indirizzo})
                dire("Feed aggiunto.")
        elif scelta == "togli":
            if not elenco:
                dire("Non c'e' nessun feed.")
                return
            voci_feed = {str(f.get("id")): f.get("title") or f.get("url") for f in elenco}
            quale = scegli(voci_feed, "quale togliere")
            if quale and conferma("Invio toglie il feed, Esc annulla"):
                ctx.cliente.delete(f"downloads/feeds/{quale}")
                dire("\nTolto.")
        elif scelta == "aggiorna":
            ctx.cliente.post("downloads/feeds/fetch")
            dire("Chiesto alla box di rileggere i feed.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _impostazioni(ctx):
    """Le impostazioni del gestore: cartella, limiti di velocita', code."""
    titolo("Impostazioni degli scaricamenti")
    try:
        config = ctx.cliente.get("downloads/config/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    riga("Cartella degli scaricamenti", decodifica(config.get("download_dir", "")))
    riga("Cartella sorvegliata", decodifica(config.get("watch_dir", "")))
    riga("Usa la cartella sorvegliata", si_no(config.get("use_watch_dir")))
    riga("Scaricamenti insieme al massimo", config.get("max_downloading_tasks"))
    limiti = config.get("throttling") or {}
    normale = limiti.get("normal") or {}
    lento = limiti.get("slow") or {}
    riga("Limite normale", f"{velocita_byte(normale.get('rx_rate')) if normale.get('rx_rate') else 'nessuno'} in discesa")
    riga("Limite ridotto", f"{velocita_byte(lento.get('rx_rate')) if lento.get('rx_rate') else 'nessuno'} in discesa")
    torrent = config.get("bt") or {}
    riga("Porta dei torrent", torrent.get("main_port"))
    riga("Peer al massimo", torrent.get("max_peers"))
    riga("Rapporto di condivisione a cui fermarsi", f"{(torrent.get('stop_ratio') or 0) / 100:.2f}")
    voci = {
        "cartella": "Cambia la cartella degli scaricamenti",
        "massimo": "Cambia quanti scaricamenti insieme",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa cambiare")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "cartella":
            nuova = chiedi("Cartella sul disco della box: ", "s", smin=1, smax=512).strip()
            if nuova:
                ctx.cliente.put("downloads/config/", dati={"download_dir": codifica(nuova)})
                dire(f"Gli scaricamenti finiranno in {nuova}.")
        elif scelta == "massimo":
            quanti = chiedi("Quanti scaricamenti insieme: ", "i", imin=1, imax=20, default=config.get("max_downloading_tasks", 5))
            ctx.cliente.put("downloads/config/", dati={"max_downloading_tasks": quanti})
            dire(f"Al massimo {quanti} insieme.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
