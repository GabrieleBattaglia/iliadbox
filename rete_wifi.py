# Iliadbox, il Wi-Fi: reti, punti di accesso, dispositivi collegati, canali e filtri.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dal comando wifi del prototipo, che accendeva e spegneva e
# basta. Qui si cambiano nome e password delle reti, si sceglie il canale con
# l'aiuto della scansione dei vicini, si vedono i collegati e si filtrano i MAC.

"""Il Wi-Fi della Iliadbox.

Tre livelli, che le API tengono distinti e che conviene non confondere. Il
Wi-Fi in generale, che si accende e si spegne tutto insieme. I punti di
accesso, uno per banda, dove si sceglie il canale e la larghezza. Le reti,
cioe' gli SSID, dove stanno nome, password e tipo di protezione: la stessa
rete puo' vivere su piu' bande, ed e' il motivo per cui il nome non sta nel
punto di accesso.
"""

import time

from api import ErroreAPI, ErroreRete
from formati import (
    acceso_spento,
    attivo_disattivo,
    banda,
    chiedi,
    chiedi_si_no,
    cifratura,
    conferma,
    dimensione,
    dire,
    durata,
    errore,
    incolonna,
    riga,
    scegli,
    segnale,
    si_no,
    titolo,
)

# Le protezioni che si possono scegliere, dalla piu' sicura alla meno.
CIFRATURE = ["wpa23_psk_ccmp_mrsno", "wpa3_psk_sae", "wpa2_psk_ccmp", "wpa2_psk_auto", "wpa_psk_auto", "none"]
# Le larghezze di canale, per banda: sono stringhe perche' cosi' le vuole il router.
LARGHEZZE = {"2d4g": ["20", "40"], "5g": ["20", "40", "80", "160"], "6g": ["20", "40", "80", "160", "320"]}


def _punti(cliente):
    """I punti di accesso, uno per banda."""
    return cliente.get("wifi/ap/") or []


def righe_wifi(cliente):
    """Lo stato del Wi-Fi in poche righe: acceso, reti, punti, collegati."""
    config = cliente.get("wifi/config/")
    filtri = {"disabled": "spento", "whitelist": "solo i MAC ammessi", "blacklist": "tutti tranne i MAC vietati"}
    righe = [
        f"Wi-Fi: {acceso_spento(config.get('enabled'))}",
        f"Risparmio energetico: {attivo_disattivo(config.get('power_saving'))}",
        f"Filtro degli indirizzi MAC: {filtri.get(config.get('mac_filter_state'), config.get('mac_filter_state'))}",
    ]
    for punto in cliente.prova("wifi/ap/") or []:
        stato = punto.get("status", {})
        collegati = cliente.prova(f"wifi/ap/{punto.get('id')}/stations/") or []
        righe.append(
            f"Punto {punto.get('name')}: {stato.get('state')}, canale {stato.get('primary_channel')}, "
            f"larghezza {stato.get('channel_width')} MHz, {len(collegati)} collegati"
        )
    for rete in cliente.prova("wifi/bss/") or []:
        config_rete = rete.get("config", {})
        stato = rete.get("status", {})
        righe.append(
            f"Rete {config_rete.get('ssid')}: {acceso_spento(config_rete.get('enabled'))}, "
            f"{cifratura(config_rete.get('encryption'))}, banda {banda(stato.get('band'))}, "
            f"{stato.get('sta_count', 0)} collegati{', nascosta' if config_rete.get('hide_ssid') else ''}"
        )
    return righe


def stato_wifi(ctx):
    """Il Wi-Fi in generale: com'e' messo e come accenderlo o spegnerlo."""
    titolo("Wi-Fi")
    try:
        config = ctx.cliente.get("wifi/config/")
        for testo in righe_wifi(ctx.cliente):
            dire(testo)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    acceso = bool(config.get("enabled"))
    voci = {
        "spegni" if acceso else "accendi": "Spegni il Wi-Fi" if acceso else "Accendi il Wi-Fi",
        "risparmio": "Cambia il risparmio energetico",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta in ("accendi", "spegni"):
            nuovo = scelta == "accendi"
            if not nuovo:
                dire(
                    "Attenzione: se questo computer e' collegato in Wi-Fi, spegnendolo perdi la connessione e non potrai riaccenderlo da qui."
                )
            if not conferma(f"Invio {'accende' if nuovo else 'spegne'}, Esc annulla"):
                dire("\nAnnullato.")
                return
            ctx.cliente.put("wifi/config/", dati={"enabled": nuovo})
            dire(f"\nWi-Fi {acceso_spento(nuovo)}.")
        elif scelta == "risparmio":
            nuovo = not config.get("power_saving")
            ctx.cliente.put("wifi/config/", dati={"power_saving": nuovo})
            dire(f"Risparmio energetico {attivo_disattivo(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def reti(ctx):
    """Le reti Wi-Fi: nome, protezione, stato, e come cambiarli."""
    titolo("Reti Wi-Fi")
    try:
        elenco = ctx.cliente.get("wifi/bss/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for rete in elenco:
        config = rete.get("config", {})
        stato = rete.get("status", {})
        dire(f"{incolonna(config.get('ssid', ''), 24)} {incolonna(banda(stato.get('band')), 8)} {cifratura(config.get('encryption'))}")
        dire(
            f"  identificativo {rete.get('id')}, {acceso_spento(config.get('enabled'))}, {stato.get('sta_count', 0)} collegati, {'nascosta' if config.get('hide_ssid') else 'visibile'}"
        )
    if not elenco or not chiedi_si_no("Vuoi cambiare qualcosa in una rete?", False):
        return
    voci = {r.get("id"): f"{r.get('config', {}).get('ssid')} su {banda(r.get('status', {}).get('band'))}" for r in elenco}
    quale = scegli(voci, "quale rete")
    if not quale:
        return
    rete = next(r for r in elenco if r.get("id") == quale)
    _modifica_rete(ctx, rete)


def _modifica_rete(ctx, rete):
    """Cambia nome, password, protezione o stato di una rete."""
    config = dict(rete.get("config", {}))
    voci = {
        "ssid": f"Nome della rete, adesso {config.get('ssid')}",
        "key": "Password della rete",
        "encryption": f"Tipo di protezione, adesso {cifratura(config.get('encryption'))}",
        "enabled": f"Accendere o spegnere questa rete, adesso {acceso_spento(config.get('enabled'))}",
        "hide_ssid": f"Nascondere il nome, adesso {si_no(config.get('hide_ssid'))}",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa cambiare")
    if not scelta or scelta == "niente":
        return
    nuovo_valore = None
    if scelta == "ssid":
        nuovo_valore = chiedi("Nuovo nome della rete: ", "s", smin=1, smax=32).strip()
    elif scelta == "key":
        dire("La password deve avere almeno otto caratteri.")
        nuovo_valore = chiedi("Nuova password: ", "s", smin=8, smax=63).strip()
    elif scelta == "encryption":
        nuovo_valore = scegli({c: cifratura(c) for c in CIFRATURE}, "quale protezione")
        if nuovo_valore == "none":
            dire("Attenzione: una rete aperta e' usabile da chiunque passi davanti a casa.")
    elif scelta == "enabled":
        nuovo_valore = not config.get("enabled")
    elif scelta == "hide_ssid":
        nuovo_valore = not config.get("hide_ssid")
    if nuovo_valore is None or nuovo_valore == "":
        dire("Nessun cambiamento.")
        return
    dire("I dispositivi collegati a questa rete dovranno ricollegarsi.")
    if not conferma("Invio conferma, Esc annulla"):
        dire("\nAnnullato.")
        return
    try:
        ctx.cliente.put(f"wifi/bss/{rete.get('id')}", dati={"config": {scelta: nuovo_valore}})
        dire(f"\nFatto: {scelta} adesso vale {nuovo_valore if scelta != 'key' else 'la nuova password'}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def chiavi(ctx):
    """Mostra le password delle reti Wi-Fi.

    Comando a se' stante apposta: la password non compare negli elenchi, cosi'
    non finisce per sbaglio dentro un rapporto o sullo schermo mentre qualcuno
    guarda.
    """
    titolo("Password delle reti Wi-Fi")
    try:
        elenco = ctx.cliente.get("wifi/bss/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    viste = set()
    for rete in elenco:
        for quale in (rete.get("config") or {}, rete.get("bss_params") or {}):
            coppia = (quale.get("ssid"), quale.get("key"))
            if not quale.get("ssid") or coppia in viste:
                continue
            viste.add(coppia)
            dire(f"{quale.get('ssid')}: {quale.get('key')}")
    lcd = ctx.cliente.prova("lcd/config/") or {}
    dire(f"Password nascosta sul display della box: {si_no(lcd.get('hide_wifi_key'))}")


def punti_accesso(ctx):
    """I punti di accesso: banda, canale, larghezza, e come cambiarli."""
    titolo("Punti di accesso Wi-Fi")
    try:
        elenco = _punti(ctx.cliente)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for punto in elenco:
        config = punto.get("config", {})
        stato = punto.get("status", {})
        scelto = str(config.get("primary_channel")) if config.get("primary_channel") else "automatico"
        dire(f"{incolonna(punto.get('name', ''), 8)} banda {incolonna(banda(config.get('band')), 8)} stato {stato.get('state')}")
        dire(f"  canale in uso {stato.get('primary_channel')}, canale scelto {scelto}, larghezza {stato.get('channel_width')} MHz")
        dire(f"  radar DFS: {attivo_disattivo(config.get('dfs_enabled'))}, acceso: {si_no(config.get('enabled'))}")
    if not elenco or not chiedi_si_no("Vuoi cambiare canale o larghezza?", False):
        return
    voci = {str(p.get("id")): f"{p.get('name')}, {banda(p.get('config', {}).get('band'))}" for p in elenco}
    quale = scegli(voci, "quale punto di accesso")
    if quale is None:
        return
    punto = next(p for p in elenco if str(p.get("id")) == quale)
    _modifica_punto(ctx, punto)


def _modifica_punto(ctx, punto):
    """Cambia canale, larghezza o accensione di un punto di accesso."""
    config = punto.get("config", {})
    banda_punto = config.get("band", "5g")
    voci = {
        "canale": "Canale, con zero per lasciare scegliere alla box",
        "larghezza": "Larghezza del canale",
        "acceso": f"Accendere o spegnere questa banda, adesso {acceso_spento(config.get('enabled'))}",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa cambiare")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "canale":
            _suggerisci_canale(ctx, punto)
            massimo = 13 if banda_punto == "2d4g" else 196
            nuovo = chiedi(
                f"Canale da 0 a {massimo}, zero per automatico: ", "i", imin=0, imax=massimo, default=config.get("primary_channel", 0)
            )
            ctx.cliente.put(f"wifi/ap/{punto.get('id')}", dati={"config": {"primary_channel": nuovo}})
            dire(f"Canale impostato a {nuovo or 'automatico'}.")
        elif scelta == "larghezza":
            possibili = LARGHEZZE.get(banda_punto, ["20", "40", "80"])
            nuovo = scegli({larghezza: f"{larghezza} MHz" for larghezza in possibili}, "quale larghezza")
            if not nuovo:
                return
            ctx.cliente.put(f"wifi/ap/{punto.get('id')}", dati={"config": {"channel_width": nuovo}})
            dire(f"Larghezza impostata a {nuovo} MHz.")
        elif scelta == "acceso":
            nuovo = not config.get("enabled")
            if not conferma(f"Invio {'accende' if nuovo else 'spegne'} la banda"):
                dire("\nAnnullato.")
                return
            ctx.cliente.put(f"wifi/ap/{punto.get('id')}", dati={"config": {"enabled": nuovo}})
            dire(f"\nBanda {acceso_spento(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _suggerisci_canale(ctx, punto):
    """Guarda l'occupazione dei canali e dice quali sono i piu' liberi."""
    try:
        occupazione = ctx.cliente.get(f"wifi/ap/{punto.get('id')}/channel_usage/") or []
    except (ErroreAPI, ErroreRete):
        return
    if not occupazione:
        return
    ordinati = sorted(occupazione, key=lambda c: (c.get("rx_busy_percent", 100), c.get("noise_level", 0)))
    dire("Canali piu' liberi secondo la box, dal migliore:")
    for canale in ordinati[:5]:
        dire(f"  canale {canale.get('channel')}: occupato al {canale.get('rx_busy_percent')}%, rumore {canale.get('noise_level')} dBm")


def collegati(ctx):
    """I dispositivi attaccati al Wi-Fi, con segnale e velocita'."""
    titolo("Dispositivi collegati in Wi-Fi")
    try:
        elenco = _punti(ctx.cliente)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    totale = 0
    for punto in elenco:
        try:
            stazioni = ctx.cliente.get(f"wifi/ap/{punto.get('id')}/stations/") or []
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)
            continue
        dire(f"Banda {banda(punto.get('config', {}).get('band'))}: {len(stazioni)} collegati")
        totale += len(stazioni)
        for stazione in sorted(stazioni, key=lambda s: s.get("signal", -100), reverse=True):
            nome = incolonna(stazione.get("hostname") or stazione.get("mac", ""), 24)
            dire(f"  {nome} {incolonna(segnale(stazione.get('signal')), 18)} da {durata(stazione.get('conn_duration'))}")
    dire(f"In tutto: {totale} dispositivi in Wi-Fi.")
    if not totale or not chiedi_si_no("Vuoi il dettaglio di uno di questi?", False):
        return
    tutte = []
    for punto in elenco:
        tutte += ctx.cliente.prova(f"wifi/ap/{punto.get('id')}/stations/") or []
    voci = {s.get("id", str(i)): f"{s.get('hostname') or s.get('mac')} {segnale(s.get('signal'))}" for i, s in enumerate(tutte)}
    quale = scegli(voci, "quale dispositivo")
    if not quale:
        return
    stazione = next(s for s in tutte if s.get("id") == quale)
    titolo(f"Dispositivo {stazione.get('hostname') or stazione.get('mac')}")
    riga("Indirizzo MAC", stazione.get("mac"))
    riga("Segnale", segnale(stazione.get("signal")))
    riga("Stato", stazione.get("state"))
    riga("Collegato da", durata(stazione.get("conn_duration")))
    riga("Fermo da", f"{stazione.get('inactive')} secondi")
    riga("Protezione in uso", f"{stazione.get('wpa_alg')} con {stazione.get('pairwise_cipher')}")
    riga("Ricevuti dal dispositivo", dimensione(stazione.get("rx_bytes")))
    riga("Inviati al dispositivo", dimensione(stazione.get("tx_bytes")))
    for verso, chiave in (("in ricezione", "last_rx"), ("in trasmissione", "last_tx")):
        dettaglio = stazione.get(chiave) or {}
        if dettaglio:
            riga(
                f"Ultima velocita' radio {verso}",
                f"{dettaglio.get('bitrate', 0) / 1000:.0f} Mb/s, larghezza {dettaglio.get('width')} MHz, {(dettaglio.get('mcs') and 'MCS ' + str(dettaglio.get('mcs'))) or ''}",
            )


def vicini(ctx):
    """Le reti Wi-Fi dei vicini, per capire chi occupa i canali."""
    titolo("Reti Wi-Fi nei dintorni")
    dire("La box elenca cio' che sente: piu' reti stanno sullo stesso canale, piu' la banda e' affollata.")
    try:
        elenco = _punti(ctx.cliente)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    if chiedi_si_no("Vuoi che la box faccia una scansione nuova prima di elencarle?", False):
        for punto in elenco:
            try:
                ctx.cliente.post(f"wifi/ap/{punto.get('id')}/neighbors/scan")
            except (ErroreAPI, ErroreRete) as guaio:
                errore(guaio)
        dire("Scansione chiesta: durante la scansione il Wi-Fi puo' fare qualche scatto. Aspetto qualche secondo.")
        time.sleep(6)
    for punto in elenco:
        try:
            reti_vicine = ctx.cliente.get(f"wifi/ap/{punto.get('id')}/neighbors/") or []
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)
            continue
        dire(f"Banda {banda(punto.get('config', {}).get('band'))}: {len(reti_vicine)} reti sentite")
        canali = {}
        for vicina in sorted(reti_vicine, key=lambda v: v.get("signal", -100), reverse=True):
            canali[vicina.get("channel")] = canali.get(vicina.get("channel"), 0) + 1
            dire(
                f"  {incolonna(vicina.get('ssid') or 'senza nome', 26)} canale {incolonna(str(vicina.get('channel')), 4)} {segnale(vicina.get('signal'))}"
            )
        if canali:
            affollati = sorted(canali.items(), key=lambda coppia: coppia[1], reverse=True)
            dire(
                "  Canali piu' affollati: "
                + ", ".join(f"{canale} con {quante} ret{'e' if quante == 1 else 'i'}" for canale, quante in affollati[:3])
            )


def canali(ctx):
    """Quanto sono occupati i canali, e quale conviene scegliere."""
    titolo("Occupazione dei canali")
    try:
        elenco = _punti(ctx.cliente)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for punto in elenco:
        try:
            occupazione = ctx.cliente.get(f"wifi/ap/{punto.get('id')}/channel_usage/") or []
        except (ErroreAPI, ErroreRete) as guaio:
            errore(guaio)
            continue
        stato = punto.get("status", {})
        dire(f"Banda {banda(punto.get('config', {}).get('band'))}, adesso sul canale {stato.get('primary_channel')}")
        for canale in sorted(occupazione, key=lambda c: c.get("channel", 0)):
            segno = " <-- in uso" if canale.get("channel") == stato.get("primary_channel") else ""
            dire(
                f"  canale {incolonna(str(canale.get('channel')), 4)} occupato al {incolonna(str(canale.get('rx_busy_percent')) + '%', 5)} rumore {canale.get('noise_level')} dBm{segno}"
            )
        _suggerisci_canale(ctx, punto)


def filtro_mac(ctx):
    """Il filtro degli indirizzi MAC: chi puo' collegarsi e chi no."""
    titolo("Filtro degli indirizzi MAC")
    modi = {
        "disabled": "spento, si collega chiunque conosca la password",
        "whitelist": "lista bianca, si collegano solo gli indirizzi elencati",
        "blacklist": "lista nera, si collegano tutti tranne gli indirizzi elencati",
    }
    try:
        config = ctx.cliente.get("wifi/config/")
        elenco = ctx.cliente.get("wifi/mac_filter/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    stato = config.get("mac_filter_state", "disabled")
    dire(f"Filtro: {modi.get(stato, stato)}")
    dire(f"Indirizzi in elenco: {len(elenco)}")
    for voce in elenco:
        dire(f"  {incolonna(voce.get('mac', ''), 18)} {voce.get('type', '')} {voce.get('comment', '')}")
    voci = {
        "modo": "Cambia il modo del filtro",
        "aggiungi": "Aggiungi un indirizzo",
        "togli": "Togli un indirizzo",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "modo":
            nuovo = scegli(modi, "quale modo")
            if not nuovo:
                return
            if nuovo == "whitelist":
                dire("Attenzione: con la lista bianca si collegano solo gli indirizzi elencati, e tutti gli altri restano fuori.")
                if not conferma("Invio conferma, Esc annulla"):
                    dire("\nAnnullato.")
                    return
            ctx.cliente.put("wifi/config/", dati={"mac_filter_state": nuovo})
            dire(f"\nFiltro impostato: {modi[nuovo]}.")
        elif scelta == "aggiungi":
            mac = chiedi("Indirizzo MAC: ", "s", smin=11, smax=17).strip()
            tipo = scegli({"whitelist": "ammesso", "blacklist": "vietato"}, "ammesso o vietato")
            if not mac or not tipo:
                return
            commento = chiedi("Commento (Invio per nessuno): ", "s", default="").strip()
            ctx.cliente.post("wifi/mac_filter/", dati={"mac": mac, "type": tipo, "comment": commento})
            dire("Aggiunto.")
        elif scelta == "togli":
            if not elenco:
                dire("Non c'e' niente da togliere.")
                return
            voci_togli = {str(v.get("id")): f"{v.get('mac')} {v.get('type')} {v.get('comment', '')}" for v in elenco}
            quale = scegli(voci_togli, "quale togliere")
            if not quale:
                return
            ctx.cliente.delete(f"wifi/mac_filter/{quale}")
            dire("Tolto.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def orari_wifi(ctx):
    """Il calendario del Wi-Fi: quando e' acceso e quando si spegne da solo."""
    titolo("Orari del Wi-Fi")
    try:
        piano = ctx.cliente.get("wifi/planning/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Calendario: {attivo_disattivo(piano.get('use_planning'))}")
    mappa = piano.get("mapping") or []
    risoluzione = piano.get("resolution") or 48
    if mappa:
        dire(f"La settimana e' divisa in {len(mappa)} caselle, {risoluzione} al giorno, cioe' una ogni {24 * 60 // risoluzione} minuti.")
        giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
        for indice, giorno in enumerate(giorni):
            fette = mappa[indice * risoluzione : (indice + 1) * risoluzione]
            if not fette:
                continue
            accese = sum(1 for f in fette if f == "on")
            if accese == len(fette):
                dire(f"{giorno}: acceso tutto il giorno")
            elif accese == 0:
                dire(f"{giorno}: spento tutto il giorno")
            else:
                dire(f"{giorno}: acceso per {accese} caselle su {len(fette)}, {_intervalli(fette, risoluzione)}")
    if not chiedi_si_no("Vuoi accendere o spegnere il calendario?", False):
        return
    try:
        nuovo = not piano.get("use_planning")
        ctx.cliente.put("wifi/planning/", dati={"use_planning": nuovo})
        dire(f"Calendario {attivo_disattivo(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _intervalli(fette, risoluzione):
    """Le fasce accese di un giorno, dette a orologio: dalle 7:00 alle 23:30."""
    minuti_per_fetta = 24 * 60 // risoluzione
    pezzi = []
    inizio = None
    for indice, fetta in enumerate([*list(fette), "off"]):
        if fetta == "on" and inizio is None:
            inizio = indice
        elif fetta != "on" and inizio is not None:
            pezzi.append(f"dalle {_orologio(inizio * minuti_per_fetta)} alle {_orologio(indice * minuti_per_fetta)}")
            inizio = None
    return ", ".join(pezzi)


def _orologio(minuti):
    return f"{minuti // 60:02d}:{minuti % 60:02d}"


def wps(ctx):
    """Il tasto che collega un dispositivo senza scrivere la password."""
    titolo("WPS")
    try:
        config = ctx.cliente.get("wifi/wps/config/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"WPS: {attivo_disattivo(config.get('enabled'))}")
    dire(
        "Il WPS collega un dispositivo premendo un tasto, ma e' anche un modo in piu' per entrare nella rete: chi non lo usa fa bene a tenerlo spento."
    )
    if not chiedi_si_no("Vuoi cambiare?", False):
        return
    try:
        nuovo = not config.get("enabled")
        ctx.cliente.put("wifi/wps/config/", dati={"enabled": nuovo})
        dire(f"WPS {attivo_disattivo(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
