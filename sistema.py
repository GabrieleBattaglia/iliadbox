# Iliadbox, il sistema: stato della box, temperature, connessione, traffico e riavvio.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dai comandi status e connection del prototipo, corretti nei
# nomi dei campi, che nella v15 delle API non sono quelli della v4: le
# temperature stanno in un elenco di sensori e non in una chiave fissa.

"""Lo stato della Iliadbox e della sua connessione.

Le funzioni che cominciano con righe_ non stampano: restituiscono una lista
di righe gia' scritte, cosi' la stessa informazione serve sia alla schermata
sia al rapporto salvato su file. I comandi veri e propri, quelli che il menu
chiama, stampano e dialogano.
"""

import time

from GBUtils import key

from api import ErroreAPI, ErroreRete
from formati import (
    acceso_spento,
    attivo_disattivo,
    chiedi,
    chiedi_si_no,
    conferma,
    da_quando,
    data_estesa,
    data_ora,
    dimensione,
    dire,
    durata,
    durata_breve,
    errore,
    intero,
    numero,
    percentuale,
    prompt_compatto,
    scegli,
    si_no,
    titolo,
    velocita_bit,
    velocita_breve,
    velocita_byte,
)

# Le basi dati storiche del router e cosa contengono.
BASI_STORICHE = {
    "traffico": ("net", "Traffico su internet, in byte al secondo"),
    "temperature": ("temp", "Temperature e ventole"),
    "porte": ("switch", "Traffico sulle porte ethernet, in byte al secondo"),
    "fibra": ("dsl", "Portata e rapporto segnale rumore della linea"),
}
# Quanto indietro guardare, in secondi.
PERIODI = {
    "ora": ("l'ultima ora", 3600),
    "sei_ore": ("le ultime sei ore", 21600),
    "giorno": ("l'ultimo giorno", 86400),
    "settimana": ("l'ultima settimana", 604800),
    "mese": ("l'ultimo mese", 2592000),
}


def _sensori(sistema):
    """I sensori di temperatura della box, come coppie nome e gradi."""
    return [(s.get("name", s.get("id", "?")), s.get("value")) for s in sistema.get("sensors", [])]


def _ventole(sistema):
    """Le ventole, come coppie nome e giri al minuto."""
    return [(v.get("name", v.get("id", "?")), v.get("value")) for v in sistema.get("fans", [])]


def righe_stato(cliente):
    """Lo stato della box: modello, firmware, tempo acceso, calore, disco."""
    sistema = cliente.get("system/")
    modello = sistema.get("model_info", {})
    righe = [
        f"Modello: {modello.get('pretty_name', sistema.get('board_name', 'sconosciuto'))}",
        f"Firmware: {sistema.get('firmware_version', 'sconosciuto')}",
        f"Numero di serie: {sistema.get('serial', 'sconosciuto')}",
        f"Indirizzo MAC: {sistema.get('mac', 'sconosciuto')}",
        f"Acceso da: {durata(sistema.get('uptime_val'))}",
        f"Operatore: {modello.get('net_operator', 'sconosciuto')}",
        f"Lingua della box: {modello.get('default_language', 'sconosciuta')}",
    ]
    for nome, valore in _sensori(sistema):
        righe.append(f"{nome}: {valore} gradi")
    for nome, valore in _ventole(sistema):
        righe.append(f"{nome}: {intero(valore)} giri al minuto")
    righe.append(f"Disco interno: {sistema.get('disk_status', 'sconosciuto')}")
    righe.append(f"Alimentazione del disco: {acceso_spento(sistema.get('user_storage_powered'))}")
    righe.append(f"Box autenticata presso l'operatore: {si_no(sistema.get('box_authenticated'))}")
    return righe


def righe_connessione(cliente):
    """La connessione a internet: stato, indirizzi, portata e traffico."""
    connessione = cliente.get("connection/")
    stati = {"up": "attiva", "down": "caduta", "going_up": "si sta alzando", "going_down": "si sta chiudendo"}
    mezzi = {"ftth": "fibra", "ethernet": "ethernet", "xdsl": "ADSL o VDSL", "backup_4g": "rete mobile di scorta"}
    righe = [
        f"Stato: {stati.get(connessione.get('state'), connessione.get('state', 'sconosciuto'))}",
        f"Tipo di collegamento: {mezzi.get(connessione.get('media'), connessione.get('media', 'sconosciuto'))}",
        f"Indirizzo pubblico IPv4: {connessione.get('ipv4', 'nessuno')}",
        f"Indirizzo pubblico IPv6: {connessione.get('ipv6', 'nessuno')}",
        f"Portata in discesa: {velocita_bit(connessione.get('bandwidth_down') or 0)}",
        f"Portata in salita: {velocita_bit(connessione.get('bandwidth_up') or 0)}",
        f"Traffico adesso in discesa: {velocita_byte(connessione.get('rate_down'))}",
        f"Traffico adesso in salita: {velocita_byte(connessione.get('rate_up'))}",
        f"Scaricati da quando e' accesa: {dimensione(connessione.get('bytes_down'))}",
        f"Inviati da quando e' accesa: {dimensione(connessione.get('bytes_up'))}",
    ]
    intervallo = connessione.get("ipv4_port_range")
    if intervallo:
        righe.append(f"Porte assegnate dall'operatore: dalla {intervallo[0]} alla {intervallo[1]}")
    return righe


def righe_configurazione_connessione(cliente):
    """Le impostazioni della connessione: filtro pubblicita', ping, accesso da fuori."""
    config = cliente.get("connection/config/")
    righe = [
        f"Filtro pubblicita' sul DNS: {attivo_disattivo(config.get('adblock'))}",
        f"Risponde al ping da internet: {si_no(config.get('ping'))}",
        f"Accensione della box da remoto: {attivo_disattivo(config.get('wol'))}",
        f"Accesso da fuori casa all'interfaccia: {attivo_disattivo(config.get('remote_access'))}",
        f"Accesso da fuori casa alle API: {attivo_disattivo(config.get('api_remote_access'))}",
        f"Richieste di associazione consentite: {si_no(config.get('allow_token_request'))}",
    ]
    if config.get("remote_access"):
        righe.append(f"Indirizzo da fuori casa: {config.get('remote_access_ip')} porta {config.get('remote_access_port')}")
    if config.get("api_domain"):
        righe.append(f"Nome per le API da fuori casa: {config.get('api_domain')} porta {config.get('https_port')}")
    righe.append(f"Rete ospiti disabilitata: {si_no(config.get('disable_guest'))}")
    righe.append(f"Gestione SIP: {config.get('sip_alg', 'sconosciuta')}")
    return righe


def righe_fibra(cliente):
    """Il collegamento in fibra e il suo ricetrasmettitore ottico."""
    fibra = cliente.prova("connection/ftth/")
    if fibra is None:
        return ["La box non riferisce nessun collegamento in fibra."]
    righe = [
        f"Modulo ottico presente: {si_no(fibra.get('sfp_present'))}",
        f"Alloggiamento per il modulo: {si_no(fibra.get('has_sfp'))}",
        f"Collegamento ottico attivo: {si_no(fibra.get('link'))}",
        f"Tipo di collegamento: {fibra.get('link_type', 'sconosciuto')}",
        f"Alimentazione del modulo a posto: {si_no(fibra.get('sfp_alim_ok'))}",
    ]
    if fibra.get("sfp_has_power_report"):
        righe.append(f"Potenza ricevuta: {numero((fibra.get('sfp_pwr_rx') or 0) / 100, 2)} dBm")
        righe.append(f"Potenza trasmessa: {numero((fibra.get('sfp_pwr_tx') or 0) / 100, 2)} dBm")
    if fibra.get("sfp_model"):
        righe.append(f"Modulo: {fibra.get('sfp_vendor', '')} {fibra.get('sfp_model', '')} serie {fibra.get('sfp_serial', '')}")
    return righe


def righe_ipv6(cliente):
    """La configurazione IPv6 e i prefissi delegati alla rete di casa."""
    config = cliente.get("connection/ipv6/config/")
    righe = [
        f"IPv6: {attivo_disattivo(config.get('ipv6_enabled'))}",
        f"Indirizzo locale del router: {config.get('ipv6ll', 'nessuno')}",
        f"Firewall IPv6: {attivo_disattivo(config.get('ipv6_firewall'))}",
        f"Firewall sui prefissi delegati: {attivo_disattivo(config.get('ipv6_prefix_firewall'))}",
    ]
    delegati = config.get("delegations") or []
    righe.append(f"Prefissi delegati: {len(delegati)}")
    for delega in delegati:
        prossimo = delega.get("next_hop") or "nessun instradamento"
        righe.append(f"  {delega.get('prefix')} verso {prossimo}")
    return righe


def righe_registro(cliente, quanti=20):
    """Gli ultimi eventi della connessione: cadute, ritorni, cambi di portata."""
    eventi = cliente.get("connection/logs/") or []
    tipi = {"link": "collegamento", "conn": "connessione", "ftth_sfp": "modulo ottico"}
    stati = {"up": "attivo", "down": "caduto", "going_up": "in salita", "going_down": "in discesa"}
    righe = [f"Eventi registrati: {len(eventi)}"]
    for evento in sorted(eventi, key=lambda e: e.get("date", 0), reverse=True)[:quanti]:
        descrizione = f"{data_ora(evento.get('date'))} {tipi.get(evento.get('type'), evento.get('type', ''))} {stati.get(evento.get('state'), evento.get('state', ''))}"
        if evento.get("bw_down"):
            descrizione += f" {velocita_bit(evento.get('bw_down'))} in discesa"
        if evento.get("link"):
            descrizione += f" via {evento.get('link')}"
        righe.append(descrizione)
    return righe


def stato(ctx):
    """Lo stato generale della box."""
    titolo("Stato del sistema")
    try:
        for testo in righe_stato(ctx.cliente):
            dire(testo)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def connessione(ctx):
    """La connessione a internet."""
    titolo("Connessione a internet")
    try:
        for testo in righe_connessione(ctx.cliente):
            dire(testo)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def fibra(ctx):
    """Il collegamento in fibra."""
    titolo("Collegamento in fibra")
    try:
        for testo in righe_fibra(ctx.cliente):
            dire(testo)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def ipv6(ctx):
    """La configurazione IPv6."""
    titolo("IPv6")
    try:
        for testo in righe_ipv6(ctx.cliente):
            dire(testo)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def registro(ctx):
    """Il registro degli eventi della connessione."""
    titolo("Registro della connessione")
    try:
        for testo in righe_registro(ctx.cliente):
            dire(testo)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def temperatura(ctx):
    """Le temperature e le ventole, adesso e nel tempo."""
    titolo("Temperature e raffreddamento")
    try:
        sistema = ctx.cliente.get("system/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for nome, valore in _sensori(sistema):
        giudizio = "normale"
        if valore is not None and valore >= 80:
            giudizio = "alta, la box sta soffrendo"
        elif valore is not None and valore >= 70:
            giudizio = "sopra la media"
        dire(f"{nome}: {valore} gradi, {giudizio}")
    for nome, valore in _ventole(sistema):
        dire(f"{nome}: {intero(valore)} giri al minuto")
    dire(f"Acceso da: {durata(sistema.get('uptime_val'))}")
    if chiedi_si_no("Vuoi seguire le temperature in tempo reale?", False):
        _sorveglia_temperatura(ctx)


def _sorveglia_temperatura(ctx, intervallo=3):
    """Riscrive la riga delle temperature ogni pochi secondi finche' non si preme un tasto."""
    dire("Riga compatta: t seguito dal numero del sensore e dai gradi, v dalla ventola in giri al minuto. Premi un tasto per smettere.")
    while True:
        try:
            sistema = ctx.cliente.get("system/")
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)
            return
        pezzi = [f"t{indice + 1} {valore}" for indice, (_, valore) in enumerate(_sensori(sistema))]
        pezzi += [f"v{indice + 1} {intero(valore)}" for indice, (_, valore) in enumerate(_ventole(sistema))]
        prompt_compatto(" ".join(pezzi))
        if key(attesa=intervallo, alla_scadenza=None) is not None:
            dire("")
            return


def traffico(ctx):
    """Il traffico su internet in tempo reale, riga per riga."""
    titolo("Traffico in tempo reale")
    dire("Ogni riga sta in quaranta caratteri: d e' la discesa e u la salita, in byte al secondo con K per mille e M per un milione; t e' la temperatura della CPU e q da quanto la box e' accesa.")
    dire("Premi un tasto per smettere.")
    while True:
        try:
            connessione_ora = ctx.cliente.get("connection/")
            sistema = ctx.cliente.get("system/")
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)
            return
        sensori = _sensori(sistema)
        temperatura_cpu = sensori[-1][1] if sensori else "?"
        riga_compatta = (
            f"d{velocita_breve(connessione_ora.get('rate_down'))} "
            f"u{velocita_breve(connessione_ora.get('rate_up'))} "
            f"t{temperatura_cpu} q{durata_breve(sistema.get('uptime_val'))}"
        )
        prompt_compatto(riga_compatta)
        if key(attesa=1, alla_scadenza=None) is not None:
            dire("")
            return


def _serie_storica(cliente, base, secondi, precisione=10):
    """Chiede al router la storia di una base dati e la riporta a valori veri.

    Il router moltiplica i valori per la precisione chiesta, cosi' che gli
    interi conservino i decimali: qui si divide e si torna ai numeri di
    sempre. Restituisce la lista dei punti, ciascuno un dizionario con time e
    i campi della base dati.
    """
    adesso = int(time.time())
    richiesta = {"db": base, "date_start": adesso - secondi, "date_end": adesso, "precision": precisione}
    risposta = cliente.post("rrd/", dati=richiesta)
    punti = risposta.get("data") or []
    veri = []
    for punto in punti:
        pulito = {"time": punto.get("time")}
        for chiave, valore in punto.items():
            if chiave == "time":
                continue
            pulito[chiave] = valore / precisione if isinstance(valore, (int, float)) else valore
        veri.append(pulito)
    return veri


def _riassunto_serie(punti, campo):
    """Minimo, massimo e media di un campo lungo la serie."""
    valori = [p[campo] for p in punti if isinstance(p.get(campo), (int, float))]
    if not valori:
        return None
    return {"minimo": min(valori), "massimo": max(valori), "media": sum(valori) / len(valori), "valori": valori}


def storico(ctx):
    """La storia di traffico, temperature e porte, con la possibilita' di ascoltarla."""
    titolo("Storico delle misure")
    voci = {chiave: descrizione for chiave, (_, descrizione) in BASI_STORICHE.items()}
    scelta = scegli(voci, "quale misura")
    if not scelta:
        return
    base = BASI_STORICHE[scelta][0]
    periodo = scegli({chiave: testo for chiave, (testo, _) in PERIODI.items()}, "quale periodo")
    if not periodo:
        return
    secondi = PERIODI[periodo][1]
    try:
        punti = _serie_storica(ctx.cliente, base, secondi)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    if not punti:
        dire("Il router non ha dati per questo periodo.")
        return
    dire(f"Punti raccolti: {len(punti)}, da {data_ora(punti[0]['time'])} a {data_ora(punti[-1]['time'])}.")
    campi = [chiave for chiave in punti[0] if chiave != "time"]
    serie_disponibili = {}
    for campo in campi:
        riassunto = _riassunto_serie(punti, campo)
        if not riassunto:
            continue
        serie_disponibili[campo] = riassunto
        if base in ("net", "switch"):
            dire(f"{campo}: media {velocita_byte(riassunto['media'])}, massimo {velocita_byte(riassunto['massimo'])}, minimo {velocita_byte(riassunto['minimo'])}")
        else:
            dire(f"{campo}: media {numero(riassunto['media'])}, massimo {numero(riassunto['massimo'])}, minimo {numero(riassunto['minimo'])}")
    if not serie_disponibili:
        return
    if chiedi_si_no("Vuoi ascoltare una di queste serie come suono?", False):
        _ascolta_serie(serie_disponibili)


def _ascolta_serie(serie_disponibili):
    """Trasforma una serie di numeri in un suono che sale e scende.

    E' il modo di leggere un grafico senza vederlo: il tempo scorre da
    sinistra a destra, l'altezza della nota dice quanto vale il dato. Serve la
    sonify di GBUtils, che a sua volta vuole numpy e sounddevice.
    """
    quale = scegli({campo: f"{campo}, {len(dati['valori'])} valori" for campo, dati in serie_disponibili.items()}, "quale serie")
    if not quale:
        return
    valori = serie_disponibili[quale]["valori"]
    if len(valori) < 5:
        dire("Servono almeno cinque valori per farne un suono.")
        return
    secondi = chiedi("Durata del suono in secondi (Invio per 4): ", "f", fmin=0.5, fmax=60, default=4.0)
    try:
        from GBUtils import sonify

        sonify(valori, secondi)
        dire("Suono avviato: parte da sinistra con il primo valore e arriva a destra con l'ultimo.")
    except ImportError:
        errore("per il suono servono numpy e sounddevice, che qui non ci sono.")
    except (TypeError, ValueError, OSError) as guaio:
        errore(guaio)


def configura_connessione(ctx):
    """Cambia le impostazioni della connessione: pubblicita', ping, accesso da fuori."""
    titolo("Impostazioni della connessione")
    try:
        config = ctx.cliente.get("connection/config/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for testo in righe_configurazione_connessione(ctx.cliente):
        dire(testo)
    voci = {
        "adblock": "Filtro pubblicita' sul DNS della box",
        "ping": "Rispondere al ping proveniente da internet",
        "wol": "Accensione della box da remoto",
        "remote_access": "Accesso all'interfaccia da fuori casa",
        "api_remote_access": "Accesso alle API da fuori casa",
        "allow_token_request": "Consentire nuove richieste di associazione",
    }
    scelta = scegli(voci, "cosa cambiare")
    if not scelta:
        return
    attuale = bool(config.get(scelta))
    dire(f"{voci[scelta]}: adesso e' {attivo_disattivo(attuale)}.")
    nuovo = chiedi_si_no("Vuoi attivarlo?", not attuale)
    if nuovo == attuale:
        dire("Nessun cambiamento.")
        return
    if scelta in ("remote_access", "api_remote_access") and nuovo:
        dire("Attenzione: aprendo l'accesso da fuori casa la box diventa raggiungibile da internet.")
    if not conferma("Invio conferma, Esc annulla"):
        dire("\nAnnullato.")
        return
    try:
        ctx.cliente.put("connection/config/", dati={scelta: nuovo})
        dire(f"\nFatto: {voci[scelta]} adesso e' {attivo_disattivo(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def riavvia(ctx):
    """Riavvia la Iliadbox, dopo averlo chiesto due volte."""
    titolo("Riavvio della box")
    dire("Il riavvio interrompe internet, telefono e televisione per qualche minuto, e tutti i dispositivi collegati perdono la rete.")
    try:
        sistema = ctx.cliente.get("system/")
        dire(f"La box e' accesa da {durata(sistema.get('uptime_val'))}.")
    except (ErroreAPI, ErroreRete):
        pass
    if not chiedi_si_no("Vuoi davvero riavviare la box?", False):
        dire("Annullato.")
        return
    if not conferma("Invio riavvia, Esc annulla"):
        dire("\nAnnullato.")
        return
    try:
        ctx.cliente.post("system/reboot/")
        dire("\nComando inviato: la box si sta riavviando e tornera' raggiungibile fra qualche minuto.")
        ctx.uscita = True
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _controllo(righe, esito, testo):
    """Aggiunge una riga alla diagnosi e conta gli avvisi."""
    righe.append(f"{esito} {testo}")
    return esito != "ok"


def righe_diagnosi(cliente):
    """Un controllo completo della box, riga per riga, con gli avvisi in evidenza.

    Ogni riga comincia con ok, avviso o guasto, cosi' chi ascolta sa subito se
    deve preoccuparsi senza aspettare la fine della frase.
    """
    righe = []
    avvisi = 0
    try:
        sistema = cliente.get("system/")
    except (ErroreAPI, ErroreRete) as guaio:
        return [f"guasto la box non risponde: {guaio}"], 1
    righe.append(f"ok box {sistema.get('model_info', {}).get('pretty_name', '')} con firmware {sistema.get('firmware_version')}")
    righe.append(f"ok accesa da {durata(sistema.get('uptime_val'))}")
    for nome, valore in _sensori(sistema):
        if valore is None:
            continue
        if valore >= 85:
            avvisi += _controllo(righe, "guasto", f"{nome} a {valore} gradi, troppo calda")
        elif valore >= 75:
            avvisi += _controllo(righe, "avviso", f"{nome} a {valore} gradi, sopra la media")
        else:
            righe.append(f"ok {nome} a {valore} gradi")
    for nome, valore in _ventole(sistema):
        if not valore:
            avvisi += _controllo(righe, "avviso", f"{nome} ferma")
        else:
            righe.append(f"ok {nome} a {intero(valore)} giri")
    connessione_ora = cliente.prova("connection/")
    if not connessione_ora:
        avvisi += _controllo(righe, "guasto", "stato della connessione non disponibile")
    elif connessione_ora.get("state") != "up":
        avvisi += _controllo(righe, "guasto", f"connessione a internet {connessione_ora.get('state')}")
    else:
        righe.append(f"ok internet attiva su {connessione_ora.get('media')} con indirizzo {connessione_ora.get('ipv4')}")
        righe.append(f"ok portata {velocita_bit(connessione_ora.get('bandwidth_down'))} in discesa e {velocita_bit(connessione_ora.get('bandwidth_up'))} in salita")
    eventi = cliente.prova("connection/logs/") or []
    cadute = [e for e in eventi if e.get("state") == "down"]
    if cadute:
        ultima = max(cadute, key=lambda e: e.get("date", 0))
        avvisi += _controllo(righe, "avviso", f"{len(cadute)} cadute nel registro, l'ultima {da_quando(ultima.get('date'))}")
    else:
        righe.append("ok nessuna caduta nel registro della connessione")
    wifi = cliente.prova("wifi/config/")
    if wifi is not None:
        if wifi.get("enabled"):
            righe.append("ok Wi-Fi acceso")
        else:
            avvisi += _controllo(righe, "avviso", "Wi-Fi spento")
    reti = cliente.prova("wifi/bss/") or []
    for rete in reti:
        config = rete.get("config", {})
        if config.get("encryption") in ("none", "wep"):
            avvisi += _controllo(righe, "guasto", f"la rete {config.get('ssid')} usa una protezione insicura")
    stazioni = []
    for punto in cliente.prova("wifi/ap/") or []:
        stazioni += cliente.prova(f"wifi/ap/{punto.get('id')}/stations/") or []
    deboli = [s for s in stazioni if (s.get("signal") or 0) < -75]
    righe.append(f"ok {len(stazioni)} dispositivi collegati in Wi-Fi")
    if deboli:
        avvisi += _controllo(righe, "avviso", f"{len(deboli)} con segnale sotto i 75 dBm negativi")
    dischi = cliente.prova("storage/disk/") or []
    for disco in dischi:
        if disco.get("state") != "enabled":
            avvisi += _controllo(righe, "avviso", f"disco {disco.get('id')} in stato {disco.get('state')}")
        if disco.get("temp"):
            righe.append(f"ok disco {disco.get('id')} a {disco.get('temp')} gradi")
    for parte in cliente.prova("storage/partition/") or []:
        totale = parte.get("total_bytes") or 0
        libero = parte.get("free_bytes") or 0
        if totale and libero / totale < 0.1:
            avvisi += _controllo(righe, "avviso", f"sulla partizione {parte.get('label')} resta solo il {percentuale(libero, totale)}")
        else:
            righe.append(f"ok partizione {parte.get('label')} con {dimensione(libero)} liberi su {dimensione(totale)}")
        if parte.get("state") != "mounted":
            avvisi += _controllo(righe, "avviso", f"partizione {parte.get('label')} non montata")
    config = cliente.prova("connection/config/") or {}
    if config.get("remote_access"):
        avvisi += _controllo(righe, "avviso", "l'interfaccia della box e' raggiungibile da internet")
    if config.get("api_remote_access"):
        righe.append("ok le API sono raggiungibili da fuori casa")
    if config.get("allow_token_request"):
        avvisi += _controllo(righe, "avviso", "la box accetta nuove richieste di associazione: chi ha accesso fisico puo' autorizzare una applicazione")
    ftp = cliente.prova("ftp/config/") or {}
    if ftp.get("enabled") and ftp.get("allow_anonymous"):
        avvisi += _controllo(righe, "avviso", "il server FTP accetta collegamenti anonimi")
    if ftp.get("weak_password"):
        avvisi += _controllo(righe, "avviso", "la password del server FTP e' debole")
    dmz = cliente.prova("fw/dmz/") or {}
    if dmz.get("enabled"):
        avvisi += _controllo(righe, "avviso", f"la DMZ e' attiva verso {dmz.get('ip')}: quel dispositivo e' esposto a internet")
    porte = cliente.prova("fw/redir/") or []
    attive = [p for p in porte if p.get("enabled")]
    if attive:
        righe.append(f"ok {len(attive)} regole di apertura porte attive")
    dhcp = cliente.prova("dhcp/config/") or {}
    if dhcp and not dhcp.get("enabled"):
        avvisi += _controllo(righe, "avviso", "il DHCP e' spento: i dispositivi non ricevono un indirizzo da soli")
    ospiti = cliente.prova("lan/browser/pub/") or []
    attivi = [o for o in ospiti if o.get("active")]
    righe.append(f"ok {len(attivi)} dispositivi attivi in rete locale su {len(ospiti)} conosciuti")
    righe.append(f"{'ok' if not avvisi else 'avviso'} controllo finito con {avvisi} cose da guardare")
    return righe, avvisi


def diagnosi(ctx):
    """Il controllo completo della box, con un riepilogo finale."""
    titolo("Diagnosi della box")
    dire("Ogni riga comincia con ok, avviso o guasto.")
    righe, avvisi = righe_diagnosi(ctx.cliente)
    for testo in righe:
        dire(testo)
    if avvisi:
        dire(f"Da guardare: {avvisi}.")
    else:
        dire("Tutto a posto.")


def rapporto(ctx):
    """Salva su file un rapporto completo, scritto per esteso.

    A schermo i dati stanno stretti, nel file no: qui ogni cosa e' scritta a
    parole, con la data in testa, cosi' il file si puo' mandare a chi deve
    capire cosa succede alla linea.
    """
    import os

    from percorsi import percorso_dati
    from versione import NOME, VERSIONE

    titolo("Rapporto completo")
    dire("Raccolgo i dati dalla box: ci vuole qualche secondo.")
    momento = time.time()
    sezioni = (
        ("Sistema", righe_stato),
        ("Connessione a internet", righe_connessione),
        ("Impostazioni della connessione", righe_configurazione_connessione),
        ("Fibra", righe_fibra),
        ("IPv6", righe_ipv6),
        ("Registro della connessione", righe_registro),
    )
    righe = [f"Rapporto di {NOME} versione {VERSIONE}", f"Scritto {data_estesa(momento)}"]
    for nome_sezione, funzione in sezioni:
        righe.append("")
        righe.append(nome_sezione)
        try:
            righe += funzione(ctx.cliente)
        except (ErroreAPI, ErroreRete) as guaio:
            righe.append(f"non disponibile: {guaio}")
    righe.append("")
    righe.append("Diagnosi")
    diagnostiche, avvisi = righe_diagnosi(ctx.cliente)
    righe += diagnostiche
    nome_file = time.strftime("iliadbox-%y%m%d-%H%M%S.txt")
    percorso = percorso_dati(nome_file)
    try:
        with open(percorso, "w", encoding="utf-8") as file_uscita:
            file_uscita.write("\n".join(righe) + "\n")
    except OSError as guaio:
        errore(guaio)
        return
    dire(f"Scritte {len(righe)} righe in {os.path.basename(percorso)}, dentro {os.path.dirname(percorso)}.")
    dire(f"Cose da guardare: {avvisi}.")
