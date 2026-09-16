# Iliadbox, la rete locale: dispositivi, DHCP, indirizzi, porte ethernet e risveglio.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dal comando lan del prototipo. Il campo con gli indirizzi
# dei dispositivi si chiama l3connectivities e non l3_connectivities: con il
# nome sbagliato ogni dispositivo risultava senza indirizzo.

"""La rete di casa vista dalla Iliadbox.

Il router tiene un elenco di tutto cio' che si e' mai collegato, con nome,
indirizzi, costruttore della scheda di rete e, per chi va in Wi-Fi, la banda e
la potenza del segnale. Da qui si guarda, si rinomina, si sveglia un computer
spento e si governano gli indirizzi che il DHCP distribuisce.
"""

from api import ErroreAPI, ErroreRete
from formati import (
    acceso_spento,
    attivo_disattivo,
    banda,
    chiedi,
    chiedi_si_no,
    conferma,
    da_quando,
    data_ora,
    dimensione,
    dire,
    durata,
    elenco_numerato,
    errore,
    incolonna,
    intero,
    percentuale,
    riga,
    scegli,
    segnale,
    si_no,
    tipo_apparecchio,
    titolo,
    velocita_byte,
)

# Le categorie che il router accetta quando si dice che tipo di apparecchio e'.
TIPI_APPARECCHIO = [
    "workstation",
    "laptop",
    "smartphone",
    "tablet",
    "printer",
    "vg_console",
    "television",
    "nas",
    "ip_camera",
    "ip_phone",
    "freebox_player",
    "freebox_server",
    "networking_device",
    "multimedia_device",
    "car",
    "other",
]


def _ordine_indirizzo(indirizzo):
    """Un indirizzo IPv4 come quaterna di numeri, per ordinarlo come si deve.

    Ordinati come stringhe, 192.168.1.109 verrebbe prima di 192.168.1.17, che
    a chi scorre l'elenco con le dita non torna.
    """
    pezzi = (indirizzo or "").split(".")
    try:
        return tuple(int(pezzo) for pezzo in pezzi)
    except ValueError:
        return (999, 999, 999, 999)


def _indirizzo(ospite, famiglia="ipv4"):
    """Il primo indirizzo di quella famiglia, o una stringa vuota."""
    for collegamento in ospite.get("l3connectivities") or []:
        if collegamento.get("af") == famiglia and collegamento.get("active"):
            return collegamento.get("addr", "")
    for collegamento in ospite.get("l3connectivities") or []:
        if collegamento.get("af") == famiglia:
            return collegamento.get("addr", "")
    return ""


def _come_collegato(ospite):
    """Come e' attaccato alla rete: Wi-Fi con banda e segnale, oppure cavo."""
    punto = ospite.get("access_point") or {}
    tipo = punto.get("connectivity_type")
    if tipo == "wifi":
        radio = punto.get("wifi_information") or {}
        ripetitore = " via ripetitore" if punto.get("type") == "repeater" else ""
        return f"wifi {banda(radio.get('band'))} {radio.get('signal')} dBm{ripetitore}"
    if tipo == "ethernet":
        return "cavo"
    if tipo:
        return tipo
    return "sconosciuto"


def _riga_ospite(ospite):
    """Un dispositivo in una riga sola, con le colonne sempre allo stesso posto."""
    segno = "*" if ospite.get("active") else " "
    nome = incolonna(ospite.get("primary_name") or ospite.get("default_name") or "senza nome", 22)
    indirizzo = incolonna(_indirizzo(ospite), 15)
    return f"{segno} {nome} {indirizzo} {_come_collegato(ospite)}"


def _ospiti(cliente, solo_attivi=True, interfaccia="pub"):
    """L'elenco dei dispositivi di una interfaccia, ordinato per nome.

    La box tiene elenchi separati: pub e' la rete di casa, wifiguest e' la
    rete degli ospiti, che esiste anche quando non la usa nessuno.
    """
    elenco = cliente.get(f"lan/browser/{interfaccia}/") or []
    if solo_attivi:
        elenco = [o for o in elenco if o.get("active")]
    return sorted(elenco, key=lambda o: (o.get("primary_name") or "").lower())


def _quale_interfaccia(cliente):
    """Su quale rete guardare: chiede solo quando ce n'e' piu' d'una abitata."""
    interfacce = cliente.prova("lan/browser/interfaces/") or []
    abitate = [i for i in interfacce if i.get("host_count")]
    if len(abitate) < 2:
        return abitate[0]["name"] if abitate else "pub"
    nomi = {"pub": "la rete di casa", "wifiguest": "la rete degli ospiti"}
    voci = {i["name"]: f"{nomi.get(i['name'], i['name'])}, {i.get('host_count')} dispositivi" for i in abitate}
    return scegli(voci, "quale rete") or "pub"


def righe_dispositivi(cliente, solo_attivi=True):
    """I dispositivi della rete, uno per riga."""
    elenco = _ospiti(cliente, solo_attivi)
    righe = [f"Dispositivi {'attivi' if solo_attivi else 'conosciuti'}: {len(elenco)}"]
    righe += [_riga_ospite(o) for o in elenco]
    return righe


def dispositivi(ctx):
    """L'elenco dei dispositivi collegati, con il dettaglio a richiesta."""
    titolo("Dispositivi della rete locale")
    dire("L'asterisco davanti al nome vuol dire che il dispositivo e' attivo adesso.")
    solo_attivi = not chiedi_si_no("Vuoi vedere anche quelli spenti?", False)
    try:
        elenco = _ospiti(ctx.cliente, solo_attivi, _quale_interfaccia(ctx.cliente))
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Dispositivi {'attivi' if solo_attivi else 'conosciuti'}: {len(elenco)}")
    for ospite in elenco:
        dire(_riga_ospite(ospite))
    if not elenco or not chiedi_si_no("Vuoi il dettaglio di uno di questi?", False):
        return
    _dettaglio_scelto(ctx, elenco)


def _scegli_ospite(elenco, prompt="quale dispositivo"):
    """Fa scegliere un dispositivo dall'elenco e lo restituisce."""
    voci = {}
    for indice, ospite in enumerate(elenco):
        nome = ospite.get("primary_name") or ospite.get("default_name") or "senza nome"
        voci[str(indice)] = f"{nome} {_indirizzo(ospite)} {_come_collegato(ospite)}"
    scelta = elenco_numerato(voci, prompt)
    return elenco[int(scelta)] if scelta is not None else None


def _dettaglio_scelto(ctx, elenco):
    ospite = _scegli_ospite(elenco)
    if ospite:
        _mostra_dettaglio(ctx, ospite)


def _mostra_dettaglio(ctx, ospite):
    """Tutto quello che la box sa di un dispositivo, e cosa ci si puo' fare."""
    titolo(f"Dispositivo {ospite.get('primary_name') or ospite.get('default_name')}")
    riga("Attivo adesso", si_no(ospite.get("active")))
    riga("Tipo", tipo_apparecchio(ospite.get("host_type")))
    riga("Indirizzo MAC", (ospite.get("l2ident") or {}).get("id", "sconosciuto"))
    riga("Costruttore della scheda", ospite.get("vendor_name") or "sconosciuto")
    riga("Collegamento", _come_collegato(ospite))
    punto = ospite.get("access_point") or {}
    radio = punto.get("wifi_information") or {}
    if radio:
        riga("Rete Wi-Fi", radio.get("ssid", "sconosciuta"))
        riga("Segnale", segnale(radio.get("signal")))
        riga("Standard", radio.get("standard", "sconosciuto"))
        riga("Velocita' radio in ricezione", f"{radio.get('phy_rx_rate')} Mb/s")
        riga("Velocita' radio in trasmissione", f"{radio.get('phy_tx_rate')} Mb/s")
        riga("Collegato da", durata(radio.get("sess_duration")))
    if punto.get("rx_bytes") is not None:
        riga("Ricevuti dal dispositivo", dimensione(punto.get("rx_bytes")))
        riga("Inviati al dispositivo", dimensione(punto.get("tx_bytes")))
    for collegamento in ospite.get("l3connectivities") or []:
        stato = "attivo" if collegamento.get("active") else "non attivo"
        dire(
            f"{collegamento.get('af')}: {collegamento.get('addr')}, {stato}, ultima attivita' {da_quando(collegamento.get('last_activity'))}"
        )
    riga("Visto la prima volta", data_ora(ospite.get("first_activity")))
    riga("Ultima attivita'", da_quando(ospite.get("last_activity")))
    riga("Tenuto in elenco anche da spento", si_no(ospite.get("persistent")))
    informazioni = ospite.get("info") or {}
    for fonte, valori in informazioni.items():
        for chiave, valore in (valori or {}).items():
            dire(f"{fonte}, {chiave}: {valore}")
    _azioni_dispositivo(ctx, ospite)


def _azioni_dispositivo(ctx, ospite):
    """Cosa si puo' fare a un dispositivo: rinominarlo, cambiarne il tipo, svegliarlo."""
    voci = {
        "nome": "Cambia il nome con cui compare in rete",
        "tipo": "Cambia il tipo di apparecchio",
        "permanente": "Tienilo in elenco anche quando e' spento, o smetti di tenerlo",
        "sveglia": "Svegliarlo con un pacchetto magico (Wake on LAN)",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    indirizzo_api = f"lan/browser/pub/{ospite.get('id')}"
    try:
        if scelta == "nome":
            nuovo = chiedi("Nuovo nome: ", "s", smin=1, smax=64).strip()
            if not nuovo:
                dire("Nessun cambiamento.")
                return
            ctx.cliente.put(indirizzo_api, dati={"primary_name": nuovo})
            dire(f"Adesso si chiama {nuovo}.")
        elif scelta == "tipo":
            voci_tipo = {t: tipo_apparecchio(t) for t in TIPI_APPARECCHIO}
            nuovo = scegli(voci_tipo, "che apparecchio e'")
            if not nuovo:
                return
            ctx.cliente.put(indirizzo_api, dati={"host_type": nuovo})
            dire(f"Adesso e' un {tipo_apparecchio(nuovo)}.")
        elif scelta == "permanente":
            nuovo = not ospite.get("persistent")
            ctx.cliente.put(indirizzo_api, dati={"persistent": nuovo})
            dire(f"Tenuto in elenco anche da spento: {si_no(nuovo)}.")
        elif scelta == "sveglia":
            _sveglia_indirizzo(ctx, (ospite.get("l2ident") or {}).get("id", ""))
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _sveglia_indirizzo(ctx, mac):
    """Manda il pacchetto magico a un indirizzo MAC."""
    if not mac:
        dire("Questo dispositivo non ha un indirizzo MAC noto.")
        return
    parola = chiedi("Password del pacchetto magico, se il dispositivo la vuole (Invio per nessuna): ", "s", default="")
    try:
        ctx.cliente.post("lan/wol/pub/", dati={"mac": mac, "password": parola or ""})
        dire(f"Pacchetto magico inviato a {mac}. Se il dispositivo lo consente, si sta accendendo.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def sveglia(ctx):
    """Accende un computer spento mandandogli il pacchetto magico."""
    titolo("Risveglio di un dispositivo")
    dire("Il pacchetto magico accende un computer spento, purche' lui sia predisposto e resti attaccato al cavo o alimentato.")
    try:
        elenco = _ospiti(ctx.cliente, solo_attivi=False)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    spenti = [o for o in elenco if not o.get("active")]
    voci = {"elenco": f"Scegli fra i {len(spenti)} dispositivi spenti che la box conosce", "mano": "Scrivo io l'indirizzo MAC"}
    scelta = scegli(voci, "come")
    if scelta == "mano":
        mac = chiedi("Indirizzo MAC, per esempio 38:07:16:2D:02:65: ", "s", smin=11, smax=17).strip()
        _sveglia_indirizzo(ctx, mac)
    elif scelta == "elenco":
        ospite = _scegli_ospite(spenti, "quale svegliare")
        if ospite:
            _sveglia_indirizzo(ctx, (ospite.get("l2ident") or {}).get("id", ""))


def righe_rete_locale(cliente):
    """Come si presenta il router sulla rete di casa."""
    config = cliente.get("lan/config/")
    modi = {"router": "router, distribuisce lui gli indirizzi", "bridge": "bridge, fa da semplice ponte"}
    return [
        f"Modalita': {modi.get(config.get('mode'), config.get('mode', 'sconosciuta'))}",
        f"Indirizzo del router: {config.get('ip')}",
        f"Nome: {config.get('name')}",
        f"Nome DNS: {config.get('name_dns')}",
        f"Nome mDNS, cioe' Bonjour: {config.get('name_mdns')}",
        f"Nome NetBIOS, cioe' per Windows: {config.get('name_netbios')}",
    ]


def rete_locale(ctx):
    """Nome e indirizzo del router sulla rete di casa, e come cambiarli."""
    titolo("Il router sulla rete locale")
    try:
        config = ctx.cliente.get("lan/config/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for testo in righe_rete_locale(ctx.cliente):
        dire(testo)
    if not chiedi_si_no("Vuoi cambiare qualcosa?", False):
        return
    voci = {
        "name": "Nome della box",
        "name_dns": "Nome DNS",
        "name_mdns": "Nome mDNS, per Bonjour",
        "name_netbios": "Nome NetBIOS, per Windows",
        "ip": "Indirizzo del router sulla rete locale",
    }
    scelta = scegli(voci, "cosa cambiare")
    if not scelta:
        return
    attuale = config.get(scelta, "")
    nuovo = chiedi(f"{voci[scelta]}, adesso {attuale}. Nuovo valore: ", "s", smin=1, smax=64, default=attuale).strip()
    if not nuovo or nuovo == attuale:
        dire("Nessun cambiamento.")
        return
    if scelta == "ip":
        dire(
            "Attenzione: cambiando l'indirizzo del router, tutti i dispositivi dovranno ricollegarsi e questo programma andra' riconfigurato."
        )
    if not conferma("Invio conferma, Esc annulla"):
        dire("\nAnnullato.")
        return
    try:
        ctx.cliente.put("lan/config/", dati={scelta: nuovo})
        dire(f"\nFatto: {voci[scelta]} adesso e' {nuovo}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def righe_dhcp(cliente):
    """Come il router distribuisce gli indirizzi."""
    config = cliente.get("dhcp/config/")
    dns = [d for d in (config.get("dns") or []) if d]
    return [
        f"DHCP: {attivo_disattivo(config.get('enabled'))}",
        f"Intervallo distribuito: da {config.get('ip_range_start')} a {config.get('ip_range_end')}",
        f"Gateway annunciato: {config.get('gateway')}",
        f"Maschera di rete: {config.get('netmask')}",
        f"Server DNS annunciati: {', '.join(dns) if dns else 'nessuno'}",
        f"Stesso indirizzo allo stesso dispositivo: {si_no(config.get('sticky_assign'))}",
    ]


def dhcp(ctx):
    """Il servizio che distribuisce gli indirizzi, e come cambiarlo."""
    titolo("DHCP")
    try:
        config = ctx.cliente.get("dhcp/config/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for testo in righe_dhcp(ctx.cliente):
        dire(testo)
    if not chiedi_si_no("Vuoi cambiare qualcosa?", False):
        return
    voci = {
        "enabled": "Accendere o spegnere il DHCP",
        "ip_range_start": "Primo indirizzo distribuito",
        "ip_range_end": "Ultimo indirizzo distribuito",
        "sticky_assign": "Dare sempre lo stesso indirizzo allo stesso dispositivo",
        "dns": "Server DNS annunciati ai dispositivi",
    }
    scelta = scegli(voci, "cosa cambiare")
    if not scelta:
        return
    try:
        if scelta == "enabled":
            nuovo = chiedi_si_no("Attivare il DHCP?", not config.get("enabled"))
            if nuovo == bool(config.get("enabled")):
                dire("Nessun cambiamento.")
                return
            if not nuovo:
                dire("Attenzione: spegnendo il DHCP i dispositivi nuovi non riceveranno piu' un indirizzo da soli.")
            if not conferma("Invio conferma, Esc annulla"):
                dire("\nAnnullato.")
                return
            ctx.cliente.put("dhcp/config/", dati={"enabled": nuovo})
            dire(f"\nDHCP {attivo_disattivo(nuovo)}.")
        elif scelta in ("ip_range_start", "ip_range_end"):
            nuovo = chiedi(f"{voci[scelta]}, adesso {config.get(scelta)}: ", "s", smin=7, smax=15, default=config.get(scelta)).strip()
            if not nuovo or nuovo == config.get(scelta):
                dire("Nessun cambiamento.")
                return
            ctx.cliente.put("dhcp/config/", dati={scelta: nuovo})
            dire(f"Fatto: {voci[scelta]} adesso e' {nuovo}.")
        elif scelta == "sticky_assign":
            nuovo = chiedi_si_no("Dare sempre lo stesso indirizzo?", not config.get("sticky_assign"))
            ctx.cliente.put("dhcp/config/", dati={"sticky_assign": nuovo})
            dire(f"Fatto: {si_no(nuovo)}.")
        elif scelta == "dns":
            dire("Scrivi gli indirizzi dei DNS separati da uno spazio; a vuoto restano quelli di adesso.")
            testo = chiedi("Server DNS: ", "s", default="").strip()
            if not testo:
                dire("Nessun cambiamento.")
                return
            elenco = testo.split()
            ctx.cliente.put("dhcp/config/", dati={"dns": elenco})
            dire(f"Fatto: adesso annuncia {', '.join(elenco)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def assegnazioni(ctx):
    """Gli indirizzi che il DHCP ha dato, e per quanto ancora valgono."""
    titolo("Indirizzi assegnati dal DHCP")
    try:
        elenco = ctx.cliente.get("dhcp/dynamic_lease/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Assegnazioni in corso: {len(elenco)}")
    for assegnazione in sorted(elenco, key=lambda a: _ordine_indirizzo(a.get("ip", ""))):
        nome = incolonna(assegnazione.get("hostname") or "senza nome", 22)
        indirizzo = incolonna(assegnazione.get("ip", ""), 15)
        resta = durata(assegnazione.get("lease_remaining"))
        dire(f"{nome} {indirizzo} {assegnazione.get('mac')} scade fra {resta}")


def statici(ctx):
    """Gli indirizzi fissi: quali sono, come aggiungerne e come toglierli."""
    titolo("Indirizzi fissi")
    dire("Un indirizzo fisso lega un dispositivo, riconosciuto dal suo MAC, a un indirizzo che non cambia mai.")
    try:
        elenco = ctx.cliente.get("dhcp/static_lease/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Indirizzi fissi impostati: {len(elenco)}")
    for voce in elenco:
        dire(
            f"{incolonna(voce.get('hostname') or voce.get('comment') or 'senza nome', 22)} {incolonna(voce.get('ip', ''), 15)} {voce.get('mac')}"
        )
    voci = {"aggiungi": "Aggiungi un indirizzo fisso", "togli": "Togli un indirizzo fisso", "niente": "Torna indietro"}
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "aggiungi":
            _aggiungi_statico(ctx)
        elif scelta == "togli":
            if not elenco:
                dire("Non ce n'e' nessuno da togliere.")
                return
            voci_togli = {
                v.get("id", str(i)): f"{v.get('hostname') or v.get('comment') or 'senza nome'} {v.get('ip')} {v.get('mac')}"
                for i, v in enumerate(elenco)
            }
            quale = scegli(voci_togli, "quale togliere")
            if not quale:
                return
            if not conferma("Invio toglie, Esc annulla"):
                dire("\nAnnullato.")
                return
            ctx.cliente.delete(f"dhcp/static_lease/{quale}")
            dire("\nTolto.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _aggiungi_statico(ctx):
    """Chiede MAC e indirizzo, proponendo i dispositivi gia' conosciuti."""
    mac = ""
    if chiedi_si_no("Vuoi sceglierlo fra i dispositivi conosciuti?", True):
        elenco = _ospiti(ctx.cliente, solo_attivi=False)
        ospite = _scegli_ospite(elenco, "quale dispositivo")
        if not ospite:
            return
        mac = (ospite.get("l2ident") or {}).get("id", "")
        proposto = _indirizzo(ospite)
    else:
        mac = chiedi("Indirizzo MAC: ", "s", smin=11, smax=17).strip()
        proposto = ""
    indirizzo = chiedi(
        f"Indirizzo da assegnare{f' (Invio per {proposto})' if proposto else ''}: ", "s", smin=7, smax=15, default=proposto
    ).strip()
    if not mac or not indirizzo:
        dire("Manca qualcosa, non faccio niente.")
        return
    commento = chiedi("Commento (Invio per nessuno): ", "s", default="").strip()
    ctx.cliente.post("dhcp/static_lease/", dati={"mac": mac, "ip": indirizzo, "comment": commento})
    dire(f"Fatto: {mac} avra' sempre l'indirizzo {indirizzo}.")


def porte_ethernet(ctx):
    """Le porte del switch: quali hanno il cavo attaccato e quanto ci passa."""
    titolo("Porte ethernet")
    try:
        porte = ctx.cliente.get("switch/status/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for porta in sorted(porte, key=lambda p: p.get("id", 0)):
        stato = "cavo collegato" if porta.get("link") == "up" else "libera"
        velocita = f"{porta.get('speed')} Mb/s {porta.get('duplex')}" if porta.get("link") == "up" else ""
        dire(f"{incolonna(porta.get('name', ''), 12)} {incolonna(stato, 15)} {velocita}")
        for apparecchio in porta.get("mac_list") or []:
            dire(f"  attaccato: {apparecchio.get('hostname') or apparecchio.get('mac')}")
    if not chiedi_si_no("Vuoi le statistiche di una porta?", False):
        return
    voci = {str(p.get("id")): f"{p.get('name')}, {p.get('link')}" for p in porte}
    quale = scegli(voci, "quale porta")
    if not quale:
        return
    try:
        dati = ctx.cliente.get(f"switch/port/{quale}/stats/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    titolo(f"Statistiche della porta {quale}")
    riga("Ricevuti", dimensione(dati.get("rx_good_bytes")))
    riga("Inviati", dimensione(dati.get("tx_bytes")))
    riga("Traffico in ricezione adesso", velocita_byte(dati.get("rx_bytes_rate")))
    riga("Traffico in trasmissione adesso", velocita_byte(dati.get("tx_bytes_rate")))
    riga("Pacchetti buoni ricevuti", intero(dati.get("rx_good_packets")))
    riga("Pacchetti scartati", intero(dati.get("rx_discard_packets")))
    riga("Pacchetti con errori", intero(dati.get("rx_err_packets")))
    riga("Collisioni", intero(dati.get("tx_collisions")))
    errori = (dati.get("rx_err_packets") or 0) + (dati.get("tx_collisions") or 0)
    buoni = dati.get("rx_good_packets") or 0
    if buoni:
        riga("Errori sul totale", percentuale(errori, buoni + errori, 3))
    if chiedi_si_no("Vuoi cambiare velocita' e duplex di questa porta?", False):
        _configura_porta(ctx, quale)


def _configura_porta(ctx, quale):
    """Forza velocita' e duplex di una porta, o li rimette in automatico.

    Serve quando un apparecchio vecchio non si mette d'accordo da solo con il
    router: il cavo risulta collegato ma la porta va a scatti.
    """
    try:
        config = ctx.cliente.get(f"switch/port/{quale}/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Adesso: velocita' {config.get('speed')}, duplex {config.get('duplex')}.")
    velocita = scegli(
        {"auto": "automatica, la scelgono fra loro", "10": "10 Mb/s", "100": "100 Mb/s", "1000": "1000 Mb/s", "2500": "2500 Mb/s"},
        "quale velocita'",
    )
    if not velocita:
        return
    duplex = scegli({"auto": "automatico", "full": "full duplex", "half": "half duplex"}, "quale duplex") or "auto"
    if not conferma("Invio conferma, Esc annulla"):
        dire("\nAnnullato.")
        return
    try:
        ctx.cliente.put(f"switch/port/{quale}/", dati={"speed": velocita, "duplex": duplex})
        dire(f"\nPorta {quale}: velocita' {velocita}, duplex {duplex}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def righe_dhcpv6(cliente):
    config = cliente.get("dhcpv6/config/")
    dns = config.get("dns") or {}
    annunciati = ", ".join(str(v) for v in dns.values()) if dns else "quelli dell'operatore"
    return [
        f"DHCPv6: {attivo_disattivo(config.get('enabled'))}",
        f"DNS personalizzati: {si_no(config.get('use_custom_dns'))}",
        f"DNS annunciati: {annunciati}",
    ]


def dhcpv6(ctx):
    """Il DHCP della versione 6 del protocollo."""
    titolo("DHCPv6")
    try:
        for testo in righe_dhcpv6(ctx.cliente):
            dire(testo)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    if not chiedi_si_no("Vuoi accendere o spegnere il DHCPv6?", False):
        return
    try:
        config = ctx.cliente.get("dhcpv6/config/")
        nuovo = not config.get("enabled")
        if not conferma(f"Invio lo mette {'acceso' if nuovo else 'spento'}"):
            dire("\nAnnullato.")
            return
        ctx.cliente.put("dhcpv6/config/", dati={"enabled": nuovo})
        dire(f"\nDHCPv6 {acceso_spento(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
