# Iliadbox, i dischi e i file: spazio, partizioni, navigazione, copie e scaricamenti.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dal comando disk del prototipo e dalla voce "file browser"
# rimasta nella lista delle cose da fare. Le API fs sono anche l'unico modo
# sensato di lavorare in ricorsione sul disco della box: via SMB la sessione
# cade, qui una cancellazione di settantatremila file dura ventiquattro secondi.

"""Il disco della Iliadbox e i file che ci stanno sopra.

I percorsi viaggiano in base64, perche' cosi' il router li riceve identici a
come sono scritti sul disco, senza che le lettere accentate cambino forma per
strada. La radice del disco dell'utente e' di solito /iliadbox, e il
filesystem distingue le maiuscole dalle minuscole: un nome va preso com'e'
dall'elenco, non riscritto a memoria.

Le operazioni lunghe, cioe' copia, spostamento e cancellazione, non finiscono
quando la richiesta torna: il router crea un compito e lo porta avanti per
conto suo. Qui il compito viene seguito con una riga che si riscrive, e la
riga sta nei quaranta caratteri del display braille.
"""

import base64
import os
import time

from GBUtils import key

from api import ErroreAPI, ErroreRete
from formati import (
    chiedi,
    chiedi_si_no,
    conferma,
    data_ora,
    dimensione,
    dire,
    durata,
    errore,
    incolonna,
    intero,
    percentuale,
    prompt_compatto,
    riga,
    scegli,
    si_no,
    taglia,
    titolo,
    velocita_byte,
)

RADICE = "/"
# Quanto spesso guardare com'e' messo un compito del router, in secondi.
PASSO_ATTESA = 1.0


def codifica(percorso):
    """Un percorso come lo vuole il router: base64 dei suoi byte."""
    return base64.b64encode(percorso.encode("utf-8")).decode("ascii")


def decodifica(percorso64):
    """Il percorso vero dietro un base64 del router."""
    try:
        return base64.b64decode(percorso64).decode("utf-8", "replace")
    except (ValueError, TypeError):
        return percorso64


def _voci(risultato):
    """L'elenco di una cartella, qualunque forma abbia la risposta.

    Il router a volte risponde con una lista di file e a volte con un
    dizionario che ha la lista dentro la chiave entries: qui le due forme
    diventano una sola.
    """
    if isinstance(risultato, dict):
        return risultato.get("entries") or []
    return risultato or []


def righe_dischi(cliente):
    """I dischi e le partizioni, con lo spazio libero."""
    righe = []
    dischi = cliente.get("storage/disk/") or []
    righe.append(f"Dischi collegati: {len(dischi)}")
    for disco in dischi:
        nome = disco.get("model") or f"{disco.get('type', 'disco')} sul connettore {disco.get('connector')}"
        righe.append(f"{nome}, stato {disco.get('state')}, {dimensione(disco.get('total_bytes'))}")
        dettagli = []
        if disco.get("temp"):
            dettagli.append(f"{disco.get('temp')} gradi")
        dettagli.append("in rotazione" if disco.get("spinning") else "fermo")
        if disco.get("idle_duration"):
            dettagli.append(f"fermo da {durata(disco.get('idle_duration'))}")
        righe.append("  " + ", ".join(dettagli))
        errori = (disco.get("read_error_requests") or 0) + (disco.get("write_error_requests") or 0)
        righe.append(
            f"  letture {intero(disco.get('read_requests'))}, scritture {intero(disco.get('write_requests'))}, errori {intero(errori)}"
        )
    parti = cliente.get("storage/partition/") or []
    for parte in parti:
        totale = parte.get("total_bytes") or 0
        libero = parte.get("free_bytes") or 0
        usato = parte.get("used_bytes") or (totale - libero)
        righe.append(
            f"Partizione {parte.get('label')}: {dimensione(libero)} liberi su {dimensione(totale)}, "
            f"usato il {percentuale(usato, totale)}, formato {parte.get('fstype')}, {parte.get('state')}"
        )
    return righe


def dischi(ctx):
    """Lo spazio sui dischi e lo stato di salute."""
    titolo("Dischi e spazio")
    try:
        for testo in righe_dischi(ctx.cliente):
            dire(testo)
        config = ctx.cliente.prova("storage/config/") or {}
        if config:
            dire(
                f"Spegnimento automatico del disco esterno: {si_no(config.get('external_pm_enabled'))}, dopo {config.get('external_pm_idle_before_spindown')} minuti di riposo"
            )
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _radice_utente(cliente):
    """La cartella da cui conviene cominciare a navigare: il disco dell'utente."""
    parti = cliente.prova("storage/partition/") or []
    for parte in parti:
        if parte.get("path"):
            return decodifica(parte["path"])
    return RADICE


def _riga_voce(voce):
    """Un file o una cartella in una riga sola."""
    tipo = "cartella" if voce.get("type") == "dir" else "file"
    misura = "" if voce.get("type") == "dir" else dimensione(voce.get("size"))
    return f"{incolonna(tipo, 9)} {incolonna(voce.get('name', ''), 40)} {incolonna(misura, 10)} {data_ora(voce.get('modification'))}"


def file_browser(ctx):
    """Naviga il disco della box: entra, guarda, copia, cancella, scarica."""
    titolo("File sul disco della box")
    dire("Si entra nelle cartelle scegliendole dall'elenco; il primo elemento torna indietro di un livello.")
    percorso = ctx.configurazione.leggi("cartella_iniziale") or _radice_utente(ctx.cliente)
    appunti = {"file": [], "modo": None}
    while True:
        try:
            risultato = ctx.cliente.get(f"fs/ls/{codifica(percorso)}")
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)
            return
        voci = [v for v in _voci(risultato) if v.get("name") not in (".", "..")]
        cartelle = sorted([v for v in voci if v.get("type") == "dir"], key=lambda v: v.get("name", "").lower())
        file_soli = sorted([v for v in voci if v.get("type") != "dir"], key=lambda v: v.get("name", "").lower())
        ordinate = cartelle + file_soli
        titolo(f"Cartella {percorso}")
        dire(f"{len(cartelle)} cartelle e {len(file_soli)} file.")
        elenco = {"su": "Torna alla cartella superiore", "azioni": "Azioni sulla cartella corrente"}
        for indice, voce in enumerate(ordinate):
            elenco[str(indice)] = _riga_voce(voce)
        scelta = scegli(elenco, taglia(os.path.basename(percorso) or percorso, 20), mostra=True)
        if scelta is None:
            return
        if scelta == "su":
            nuovo = os.path.dirname(percorso.rstrip("/")) or RADICE
            percorso = nuovo
            continue
        if scelta == "azioni":
            uscire, percorso = _azioni_cartella(ctx, percorso, ordinate, appunti)
            if uscire:
                return
            continue
        voce = ordinate[int(scelta)]
        if voce.get("type") == "dir":
            percorso = percorso.rstrip("/") + "/" + voce.get("name", "")
        else:
            _azioni_file(ctx, percorso, voce, appunti)


def _azioni_cartella(ctx, percorso, voci, appunti):
    """Cosa si puo' fare qui dentro. Restituisce se uscire e il percorso nuovo."""
    voci_menu = {
        "nuova": "Crea una cartella qui dentro",
        "incolla": f"Incolla i {len(appunti['file'])} elementi segnati" if appunti["file"] else "Niente da incollare",
        "vai": "Vai a un percorso scritto a mano",
        "iniziale": "Ricorda questa cartella come punto di partenza",
        "spazio": "Quanto spazio resta sul disco",
        "esci": "Chiudi il navigatore",
        "niente": "Torna all'elenco",
    }
    scelta = scegli(voci_menu, "azione")
    if not scelta or scelta == "niente":
        return False, percorso
    try:
        if scelta == "nuova":
            nome = chiedi("Nome della cartella nuova: ", "s", smin=1, smax=128).strip()
            if nome:
                ctx.cliente.post("fs/mkdir/", dati={"parent": codifica(percorso), "dirname": nome})
                dire(f"Creata la cartella {nome}.")
        elif scelta == "incolla" and appunti["file"]:
            _incolla(ctx, percorso, appunti)
        elif scelta == "vai":
            nuovo = chiedi("Percorso, per esempio /iliadbox/Download: ", "s", smin=1, smax=512).strip()
            if nuovo:
                return False, nuovo
        elif scelta == "iniziale":
            ctx.configurazione.scrivi("cartella_iniziale", percorso)
            dire(f"D'ora in poi il navigatore parte da {percorso}.")
        elif scelta == "spazio":
            for testo in righe_dischi(ctx.cliente):
                dire(testo)
        elif scelta == "esci":
            return True, percorso
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
    return False, percorso


def _azioni_file(ctx, percorso, voce, appunti):
    """Cosa si puo' fare a un file o a una cartella scelta."""
    intero_percorso = percorso.rstrip("/") + "/" + voce.get("name", "")
    titolo(f"{voce.get('name')}")
    riga("Tipo", "cartella" if voce.get("type") == "dir" else voce.get("mimetype", "file"))
    riga("Dimensione", dimensione(voce.get("size")))
    riga("Ultima modifica", data_ora(voce.get("modification")))
    riga("Percorso", intero_percorso)
    voci_menu = {
        "scarica": "Scarica questo file sul computer",
        "rinomina": "Rinomina",
        "copia": "Segnalo da copiare",
        "sposta": "Segnalo da spostare",
        "cancella": "Cancella",
        "condividi": "Crea un collegamento per condividerlo",
        "archivia": "Mettilo dentro un archivio zip",
        "estrai": "Estrai qui il contenuto di questo archivio",
        "impronta": "Calcola l'impronta del file, md5 o sha1",
        "niente": "Torna all'elenco",
    }
    if voce.get("type") == "dir":
        del voci_menu["scarica"]
        del voci_menu["estrai"]
        del voci_menu["impronta"]
    scelta = scegli(voci_menu, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "scarica":
            _scarica_file(ctx, intero_percorso, voce)
        elif scelta == "rinomina":
            nuovo = chiedi(f"Nuovo nome, adesso {voce.get('name')}: ", "s", smin=1, smax=255, default=voce.get("name")).strip()
            if nuovo and nuovo != voce.get("name"):
                ctx.cliente.post("fs/rename/", dati={"src": codifica(intero_percorso), "dst": nuovo})
                dire(f"Adesso si chiama {nuovo}.")
        elif scelta in ("copia", "sposta"):
            appunti["file"] = [intero_percorso]
            appunti["modo"] = scelta
            dire(
                f"Segnato per {'la copia' if scelta == 'copia' else 'lo spostamento'}: vai nella cartella di destinazione e scegli Azioni, poi Incolla."
            )
        elif scelta == "cancella":
            dire(f"Sto per cancellare {intero_percorso}.")
            if voce.get("type") == "dir":
                dire("E' una cartella: sparisce con tutto quello che contiene.")
            if not conferma("Invio cancella, Esc annulla"):
                dire("\nAnnullato.")
                return
            compito = ctx.cliente.post("fs/rm/", dati={"files": [codifica(intero_percorso)]})
            _segui_compito(ctx, compito)
        elif scelta == "condividi":
            _crea_condivisione(ctx, intero_percorso)
        elif scelta == "archivia":
            nome = chiedi(f"Nome dell'archivio (Invio per {voce.get('name')}.zip): ", "s", default=f"{voce.get('name')}.zip").strip()
            if nome:
                compito = ctx.cliente.post(
                    "fs/archive/", dati={"files": [codifica(intero_percorso)], "dst": codifica(f"{percorso.rstrip('/')}/{nome}")}
                )
                _segui_compito(ctx, compito)
        elif scelta == "estrai":
            dire(f"Il contenuto finira' dentro {percorso}.")
            if conferma("Invio estrae, Esc annulla"):
                compito = ctx.cliente.post(
                    "fs/extract/",
                    dati={"src": codifica(intero_percorso), "dst": codifica(percorso), "delete_archive": False, "overwrite": False},
                )
                _segui_compito(ctx, compito)
            else:
                dire("\nAnnullato.")
        elif scelta == "impronta":
            _impronta(ctx, intero_percorso)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _impronta(ctx, percorso):
    """Chiede al router l'impronta di un file e la aspetta.

    Serve a sapere se il file sul disco della box e' identico a quello sul
    computer, per esempio dopo una copia lunga: due impronte uguali vogliono
    dire due file uguali.
    """
    tipo = scegli({"md5": "md5, piu' veloce", "sha1": "sha1, piu' robusta"}, "quale impronta")
    if not tipo:
        return
    compito = ctx.cliente.post("fs/hash/", dati={"src": codifica(percorso), "hash_type": tipo})
    numero_compito = compito.get("id") if isinstance(compito, dict) else None
    if numero_compito is None:
        dire("Il router non ha creato nessun compito.")
        return
    dire("Calcolo in corso, su un file grande ci vuole qualche minuto.")
    while True:
        stato = ctx.cliente.get(f"fs/tasks/{numero_compito}")
        prompt_compatto(f"p{stato.get('progress', 0)}%")
        if stato.get("state") in ("done", "failed"):
            dire("")
            break
        if key(attesa=PASSO_ATTESA, alla_scadenza=None) == "\x1b":
            dire("\nLascio perdere: il compito prosegue.")
            return
    risultato = ctx.cliente.prova(f"fs/tasks/{numero_compito}/hash") or ""
    dire(f"Impronta {tipo}: {risultato}")
    ctx.cliente.delete(f"fs/tasks/{numero_compito}")


def _incolla(ctx, destinazione, appunti):
    """Copia o sposta gli elementi segnati dentro la cartella corrente."""
    modo_api = "cp" if appunti["modo"] == "copia" else "mv"
    dire(f"{'Copio' if modo_api == 'cp' else 'Sposto'} {len(appunti['file'])} elementi dentro {destinazione}.")
    if not conferma("Invio conferma, Esc annulla"):
        dire("\nAnnullato.")
        return
    compito = ctx.cliente.post(
        f"fs/{modo_api}/",
        dati={"files": [codifica(p) for p in appunti["file"]], "dst": codifica(destinazione), "mode": "both"},
    )
    _segui_compito(ctx, compito)
    appunti["file"] = []
    appunti["modo"] = None


def _segui_compito(ctx, compito):
    """Segue un compito del router fino alla fine, con una riga che si riscrive.

    La riga sta nei quaranta caratteri: p e' la percentuale, f i file fatti
    sul totale, v la velocita', m i minuti e secondi che mancano.
    """
    if not isinstance(compito, dict):
        dire("Il router non ha creato nessun compito: forse era gia' tutto fatto.")
        return
    numero_compito = compito.get("id")
    if numero_compito is None:
        dire("Fatto.")
        return
    dire("Compito avviato. Premi Escape per smettere di seguirlo: il router va avanti lo stesso.")
    while True:
        try:
            stato = ctx.cliente.get(f"fs/tasks/{numero_compito}")
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)
            return
        fatto = stato.get("state") in ("done", "failed", "paused")
        riga_compatta = (
            f"p{stato.get('progress', 0)}% f{intero(stato.get('nfiles_done'))}/{intero(stato.get('nfiles'))} "
            f"v{velocita_byte(stato.get('rate'), 0)}"
        )
        prompt_compatto(riga_compatta)
        if fatto:
            dire("")
            esito = stato.get("state")
            if esito == "done":
                dire(f"Finito: {intero(stato.get('nfiles_done'))} elementi in {durata(stato.get('duration'))}.")
            else:
                dire(f"Compito {esito}, errore {stato.get('error')}.")
            return
        if key(attesa=PASSO_ATTESA, alla_scadenza=None) == "\x1b":
            dire("\nIl compito prosegue per conto suo: lo trovi nel comando compiti.")
            return


def _scarica_file(ctx, percorso, voce):
    """Porta un file dalla box al computer, con la barra dell'avanzamento."""
    cartella = ctx.configurazione.leggi("cartella_scaricamenti") or os.path.expanduser("~/Downloads")
    dire(f"Il file finira' in {cartella}.")
    if chiedi_si_no("Vuoi cambiare cartella?", False):
        nuova = chiedi("Cartella di destinazione: ", "s", smin=1, smax=512).strip()
        if nuova:
            cartella = nuova
            ctx.configurazione.scrivi("cartella_scaricamenti", cartella)
    if not os.path.isdir(cartella):
        errore(f"la cartella {cartella} non esiste.")
        return
    destinazione = os.path.join(cartella, voce.get("name", "scaricato"))
    totale_atteso = voce.get("size") or 0
    inizio = time.time()

    def avanza(scritti, totale):
        quanto = totale or totale_atteso
        parte = f"p{int(scritti / quanto * 100)}%" if quanto else dimensione(scritti)
        velocita = scritti / max(0.001, time.time() - inizio)
        prompt_compatto(f"{parte} {dimensione(scritti, 0)} {velocita_byte(velocita, 0)}")

    try:
        scritti = ctx.cliente.scarica(f"dl/{codifica(percorso)}", destinazione, avanza)
    except (ErroreAPI, ErroreRete, OSError) as guaio:
        dire("")
        errore(guaio)
        return
    dire("")
    dire(f"Scaricati {dimensione(scritti)} in {destinazione}, in {durata(time.time() - inizio)}.")


def compiti(ctx):
    """I compiti che il router sta portando avanti sul disco."""
    titolo("Compiti sul disco")
    try:
        elenco = ctx.cliente.get("fs/tasks/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    tipi = {
        "cp": "copia",
        "mv": "spostamento",
        "rm": "cancellazione",
        "archive": "archiviazione",
        "extract": "estrazione",
        "hash": "impronta",
        "repair": "riparazione",
    }
    dire(f"Compiti in elenco: {len(elenco)}")
    for compito in elenco:
        origine = compito.get("from") or ", ".join(compito.get("src") or [])
        dire(
            f"{incolonna(tipi.get(compito.get('type'), compito.get('type', '')), 14)} {incolonna(compito.get('state', ''), 8)} {compito.get('progress', 0)}% {taglia(origine, 50)}"
        )
        if compito.get("state") == "done":
            dire(
                f"  {intero(compito.get('nfiles_done'))} elementi in {durata(compito.get('duration'))}, finito {data_ora(compito.get('done_ts'))}"
            )
    attivi = [c for c in elenco if c.get("state") in ("running", "queued", "paused")]
    voci = {}
    if attivi:
        voci["segui"] = "Segui un compito in corso"
        voci["ferma"] = "Ferma un compito"
    if elenco:
        voci["pulisci"] = "Togli dall'elenco i compiti finiti"
    voci["niente"] = "Torna indietro"
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "segui":
            quale = scegli({str(c.get("id")): f"{tipi.get(c.get('type'), '')} {c.get('progress')}%" for c in attivi}, "quale compito")
            if quale:
                _segui_compito(ctx, {"id": int(quale)})
        elif scelta == "ferma":
            quale = scegli({str(c.get("id")): f"{tipi.get(c.get('type'), '')} {c.get('progress')}%" for c in attivi}, "quale fermare")
            if quale and conferma("Invio ferma il compito, Esc annulla"):
                ctx.cliente.delete(f"fs/tasks/{quale}")
                dire("\nFermato. Cio' che era gia' stato fatto resta fatto.")
        elif scelta == "pulisci":
            finiti = [c for c in elenco if c.get("state") in ("done", "failed")]
            for compito in finiti:
                ctx.cliente.delete(f"fs/tasks/{compito.get('id')}")
            dire(f"Tolti {len(finiti)} compiti finiti.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _crea_condivisione(ctx, percorso):
    """Crea un collegamento pubblico verso un file della box."""
    giorni = chiedi("Per quanti giorni deve valere il collegamento (zero per sempre): ", "i", imin=0, imax=365, default=7)
    scadenza = int(time.time()) + giorni * 86400 if giorni else 0
    parola = chiedi("Password per aprirlo (Invio per nessuna): ", "s", default="").strip()
    richiesta = {"path": codifica(percorso), "expire": scadenza}
    if parola:
        richiesta["password"] = parola
    try:
        creato = ctx.cliente.post("share_link/", dati=richiesta)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Collegamento creato: {creato.get('fullurl') or creato.get('url')}")
    if scadenza:
        dire(f"Vale fino al {data_ora(scadenza)}.")


def condivisioni(ctx):
    """I collegamenti pubblici verso i file della box."""
    titolo("Collegamenti condivisi")
    try:
        elenco = ctx.cliente.get("share_link/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Collegamenti attivi: {len(elenco)}")
    for collegamento in elenco:
        scadenza = "senza scadenza" if not collegamento.get("expire") else f"scade {data_ora(collegamento.get('expire'))}"
        dire(f"{incolonna(collegamento.get('name') or decodifica(collegamento.get('path', '')), 36)} {scadenza}")
        dire(f"  {collegamento.get('fullurl') or collegamento.get('url')}")
    if not elenco or not chiedi_si_no("Vuoi togliere un collegamento?", False):
        return
    voci = {str(c.get("token") or c.get("id")): c.get("name") or decodifica(c.get("path", "")) for c in elenco}
    quale = scegli(voci, "quale togliere")
    if not quale:
        return
    try:
        ctx.cliente.delete(f"share_link/{quale}")
        dire("Tolto: il collegamento non funziona piu'.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
