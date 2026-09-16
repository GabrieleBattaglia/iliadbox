# Iliadbox, la sicurezza: porte aperte, DMZ, VPN, controllo dei contenuti, notifiche.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dai comandi nat, vpn_server, vpn_client e parental del
# prototipo, che elencavano e basta: qui le regole si aggiungono e si tolgono.

"""Cio' che entra in casa dalla rete, e cio' che glielo impedisce.

Le porte aperte sono l'unica strada per cui qualcuno da internet puo'
raggiungere un dispositivo di casa: ogni regola va guardata sapendo che
apre un varco. La DMZ e' il varco piu' largo di tutti, perche' manda tutto
quello che arriva a un dispositivo solo. Le VPN, al contrario, sono il modo
sicuro di entrare in casa da fuori.
"""

from api import ErroreAPI, ErroreRete
from formati import (
    attivo_disattivo,
    chiedi,
    chiedi_si_no,
    conferma,
    da_quando,
    dire,
    durata,
    errore,
    incolonna,
    riga,
    scegli,
    si_no,
    titolo,
)

PROTOCOLLI = {"tcp": "TCP", "udp": "UDP"}
# I server VPN che la box puo' offrire, con il nome per esteso.
NOMI_VPN = {
    "pptp": "PPTP, vecchio e poco sicuro",
    "openvpn_routed": "OpenVPN instradato",
    "openvpn_bridge": "OpenVPN a ponte",
    "ipsec": "IPsec",
    "wireguard": "WireGuard, il piu' moderno",
}
# Come sta un server VPN, detto in italiano.
STATI_VPN = {"stopped": "fermo", "starting": "sta partendo", "started": "acceso", "stopping": "si sta fermando", "error": "errore"}


def _porta_descritta(regola):
    """Una regola di apertura porte in una riga sola."""
    inizio = regola.get("wan_port_start", regola.get("src_port_start"))
    fine = regola.get("wan_port_end", regola.get("src_port_end"))
    esterna = f"{inizio}" if inizio == fine else f"{inizio}-{fine}"
    stato = "attiva" if regola.get("enabled") else "spenta"
    sorgente = regola.get("src_ip") or "0.0.0.0"  # noqa: S104
    da_chi = "da chiunque" if sorgente in ("", "0.0.0.0") else f"solo da {sorgente}"  # noqa: S104
    commento = regola.get("comment") or ""
    return (
        f"{incolonna(stato, 7)} {incolonna(PROTOCOLLI.get(regola.get('ip_proto'), regola.get('ip_proto', '')), 4)} "
        f"porta {incolonna(esterna, 12)} verso {incolonna(regola.get('lan_ip', ''), 15)}:{regola.get('lan_port')} {da_chi} {commento}"
    )


def righe_porte(cliente):
    """Le regole di apertura porte, una per riga."""
    regole = cliente.get("fw/redir/") or []
    righe = [f"Regole di apertura porte: {len(regole)}"]
    righe += [_porta_descritta(r) for r in regole]
    dmz = cliente.prova("fw/dmz/") or {}
    righe.append(f"DMZ: {attivo_disattivo(dmz.get('enabled'))}{', verso ' + dmz.get('ip') if dmz.get('enabled') else ''}")
    return righe


def porte(ctx):
    """Le porte aperte verso internet: quali sono, come aprirne e come chiuderle."""
    titolo("Apertura porte verso internet")
    dire("Ogni regola lascia entrare da internet fino a un dispositivo di casa: sono i varchi da conoscere uno per uno.")
    try:
        regole = ctx.cliente.get("fw/redir/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Regole impostate: {len(regole)}")
    for regola in regole:
        dire(_porta_descritta(regola))
    voci = {
        "aggiungi": "Apri una porta nuova",
        "accendi": "Accendi o spegni una regola",
        "togli": "Togli una regola",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "aggiungi":
            _aggiungi_porta(ctx)
        elif not regole:
            dire("Non c'e' nessuna regola su cui lavorare.")
        elif scelta == "accendi":
            voci_regole = {str(r.get("id")): _porta_descritta(r) for r in regole}
            quale = scegli(voci_regole, "quale regola")
            if not quale:
                return
            regola = next(r for r in regole if str(r.get("id")) == quale)
            nuovo = not regola.get("enabled")
            ctx.cliente.put(f"fw/redir/{quale}", dati={"enabled": nuovo})
            dire(f"Regola {'attivata' if nuovo else 'spenta'}.")
        elif scelta == "togli":
            voci_regole = {str(r.get("id")): _porta_descritta(r) for r in regole}
            quale = scegli(voci_regole, "quale togliere")
            if not quale:
                return
            if not conferma("Invio toglie la regola, Esc annulla"):
                dire("\nAnnullato.")
                return
            ctx.cliente.delete(f"fw/redir/{quale}")
            dire("\nTolta.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _aggiungi_porta(ctx):
    """Chiede i dati di una regola nuova e la crea."""
    protocollo = scegli(PROTOCOLLI, "quale protocollo")
    if not protocollo:
        return
    porta_esterna = chiedi("Porta vista da internet: ", "i", imin=1, imax=65535)
    porta_fine = chiedi(
        f"Ultima porta dell'intervallo (Invio per {porta_esterna}): ", "i", imin=porta_esterna, imax=65535, default=porta_esterna
    )
    destinazione = chiedi("Indirizzo del dispositivo di casa: ", "s", smin=7, smax=15).strip()
    porta_interna = chiedi(f"Porta sul dispositivo (Invio per {porta_esterna}): ", "i", imin=1, imax=65535, default=porta_esterna)
    sorgente = chiedi("Aprire solo a un indirizzo di internet (Invio per chiunque): ", "s", default="").strip()
    commento = chiedi("Commento, per ricordarsi a cosa serve: ", "s", default="").strip()
    regola = {
        "enabled": True,
        "ip_proto": protocollo,
        "wan_port_start": porta_esterna,
        "wan_port_end": porta_fine,
        "lan_ip": destinazione,
        "lan_port": porta_interna,
        "src_ip": sorgente or "0.0.0.0",  # noqa: S104
        "comment": commento,
    }
    dire(f"Sto per aprire la porta {porta_esterna} verso {destinazione}:{porta_interna} in {protocollo.upper()}.")
    if not conferma("Invio apre la porta, Esc annulla"):
        dire("\nAnnullato.")
        return
    ctx.cliente.post("fw/redir/", dati=regola)
    dire("\nPorta aperta.")


def dmz(ctx):
    """La DMZ: tutto cio' che arriva da internet verso un solo dispositivo."""
    titolo("DMZ")
    dire(
        "Con la DMZ accesa, tutto il traffico che arriva da internet e non ha gia' una regola finisce a un unico dispositivo, che resta cosi' esposto."
    )
    try:
        config = ctx.cliente.get("fw/dmz/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"DMZ: {attivo_disattivo(config.get('enabled'))}")
    if config.get("ip"):
        dire(f"Dispositivo esposto: {config.get('ip')}")
    if not chiedi_si_no("Vuoi cambiare?", False):
        return
    try:
        if config.get("enabled"):
            if not conferma("Invio spegne la DMZ, Esc annulla"):
                dire("\nAnnullato.")
                return
            ctx.cliente.put("fw/dmz/", dati={"enabled": False})
            dire("\nDMZ spenta.")
            return
        indirizzo = chiedi("Indirizzo del dispositivo da esporre: ", "s", smin=7, smax=15).strip()
        if not indirizzo:
            return
        dire(f"Attenzione: {indirizzo} sara' raggiungibile da internet su tutte le porte non gia' occupate.")
        if not conferma("Invio accende la DMZ, Esc annulla"):
            dire("\nAnnullato.")
            return
        ctx.cliente.put("fw/dmz/", dati={"enabled": True, "ip": indirizzo})
        dire("\nDMZ accesa.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def porte_dei_servizi(ctx):
    """Le porte che i servizi della box occupano, e su quali si possono spostare."""
    titolo("Porte dei servizi della box")
    try:
        elenco = ctx.cliente.get("fw/incoming/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for servizio in sorted(elenco, key=lambda s: str(s.get("id"))):
        stato = "attivo" if servizio.get("active") else "fermo"
        modificabile = "" if servizio.get("readonly") else f", si puo' spostare fra {servizio.get('min_port')} e {servizio.get('max_port')}"
        dire(
            f"{incolonna(str(servizio.get('id')), 14)} porta {incolonna(str(servizio.get('in_port')), 6)} {incolonna(servizio.get('type', ''), 8)} {stato}{modificabile}"
        )
    modificabili = [s for s in elenco if not s.get("readonly")]
    if not modificabili or not chiedi_si_no("Vuoi spostare un servizio su un'altra porta?", False):
        return
    voci = {str(s.get("id")): f"{s.get('id')}, adesso sulla {s.get('in_port')}" for s in modificabili}
    quale = scegli(voci, "quale servizio")
    if not quale:
        return
    servizio = next(s for s in modificabili if str(s.get("id")) == quale)
    nuova = chiedi(
        f"Nuova porta fra {servizio.get('min_port')} e {servizio.get('max_port')}: ",
        "i",
        imin=servizio.get("min_port", 1),
        imax=servizio.get("max_port", 65535),
        default=servizio.get("in_port"),
    )
    try:
        ctx.cliente.put(f"fw/incoming/{quale}", dati={"in_port": nuova})
        dire(f"Il servizio {quale} adesso ascolta sulla porta {nuova}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def righe_vpn(cliente):
    """I server VPN della box e il loro stato."""
    servitori = cliente.get("vpn/") or []
    righe = [f"Server VPN disponibili: {len(servitori)}"]
    for servitore in servitori:
        righe.append(
            f"{incolonna(NOMI_VPN.get(servitore.get('name'), servitore.get('name', '')), 28)} "
            f"{incolonna(STATI_VPN.get(servitore.get('state'), servitore.get('state', '')), 12)} {servitore.get('connection_count', 0)} collegamenti"
        )
    riserva = cliente.prova("vpn/ip_pool/") or {}
    if riserva:
        righe.append(f"Indirizzi per i collegati: da {riserva.get('ip_start')} a {riserva.get('ip_end')}")
    utenti = cliente.prova("vpn/user/") or []
    righe.append(f"Utenti VPN: {len(utenti)}")
    return righe


def vpn(ctx):
    """I server VPN: stato, accensione, utenti e collegamenti in corso."""
    titolo("Server VPN")
    dire("Una VPN ti fa entrare in casa da fuori come se fossi sul divano: e' l'alternativa sicura all'aprire le porte.")
    try:
        servitori = ctx.cliente.get("vpn/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    for testo in righe_vpn(ctx.cliente):
        dire(testo)
    voci = {
        "dettaglio": "Vedi la configurazione di un server",
        "accendi": "Accendi o spegni un server",
        "utenti": "Gli utenti che possono collegarsi",
        "collegati": "Chi e' collegato adesso",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta in ("dettaglio", "accendi"):
            voci_server = {
                s.get("name"): f"{NOMI_VPN.get(s.get('name'), s.get('name'))}, {STATI_VPN.get(s.get('state'), s.get('state'))}"
                for s in servitori
            }
            quale = scegli(voci_server, "quale server")
            if not quale:
                return
            config = ctx.cliente.get(f"vpn/{quale}/config/")
            if scelta == "dettaglio":
                _mostra_config_vpn(config)
            else:
                nuovo = not config.get("enabled")
                if nuovo and quale == "pptp":
                    dire("Attenzione: PPTP e' un protocollo vecchio, la sua cifratura si rompe facilmente.")
                if not conferma(f"Invio {'accende' if nuovo else 'spegne'} {quale}, Esc annulla"):
                    dire("\nAnnullato.")
                    return
                ctx.cliente.put(f"vpn/{quale}/config/", dati={"enabled": nuovo})
                dire(f"\nServer {quale} {'acceso' if nuovo else 'spento'}.")
        elif scelta == "utenti":
            _utenti_vpn(ctx)
        elif scelta == "collegati":
            collegamenti = ctx.cliente.prova("vpn/connection/") or []
            dire(f"Collegamenti in corso: {len(collegamenti)}")
            for collegamento in collegamenti:
                dire(
                    f"{collegamento.get('user', 'sconosciuto')} da {collegamento.get('src_ip', '')} "
                    f"con indirizzo {collegamento.get('local_ip', '')} da {durata(collegamento.get('duration'))}"
                )
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _mostra_config_vpn(config):
    """La configurazione di un server VPN, campo per campo."""
    titolo(f"Server {config.get('id', '')}")
    riga("Acceso", si_no(config.get("enabled")))
    riga("Porta", config.get("port"))
    riga("IPv4", si_no(config.get("enable_ipv4")))
    riga("IPv6", si_no(config.get("enable_ipv6")))
    riga("Indirizzi assegnati", f"da {config.get('ip_start')} a {config.get('ip_end')}")
    for chiave, valore in config.items():
        if chiave.startswith("conf_") and isinstance(valore, dict):
            for nome, contenuto in valore.items():
                riga(f"  {nome}", contenuto)


def _utenti_vpn(ctx):
    """Gli utenti della VPN: chi c'e', come aggiungerne e come toglierli."""
    utenti = ctx.cliente.prova("vpn/user/") or []
    dire(f"Utenti VPN: {len(utenti)}")
    for utente in utenti:
        dire(
            f"{incolonna(utente.get('login', ''), 20)} {'attivo' if not utente.get('disabled') else 'disattivato'} {utente.get('ip_reservation', '')}"
        )
    voci = {"aggiungi": "Aggiungi un utente", "togli": "Togli un utente", "niente": "Torna indietro"}
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    if scelta == "aggiungi":
        nome = chiedi("Nome dell'utente: ", "s", smin=1, smax=32).strip()
        if not nome:
            return
        from GBUtils import dgt

        parola = dgt("Password per questo utente: ", kind="s", smin=8, smax=64, pwd=True)
        ctx.cliente.post("vpn/user/", dati={"login": nome, "password": parola})
        dire(f"Utente {nome} creato.")
    elif scelta == "togli":
        if not utenti:
            dire("Non c'e' nessun utente da togliere.")
            return
        voci_utenti = {u.get("login"): u.get("login") for u in utenti}
        quale = scegli(voci_utenti, "quale togliere")
        if not quale:
            return
        if not conferma("Invio toglie l'utente, Esc annulla"):
            dire("\nAnnullato.")
            return
        ctx.cliente.delete(f"vpn/user/{quale}")
        dire("\nTolto.")


def vpn_cliente(ctx):
    """La box che si collega lei a una VPN esterna."""
    titolo("Collegamento della box a una VPN esterna")
    try:
        stato = ctx.cliente.get("vpn_client/status/") or {}
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Cliente VPN: {attivo_disattivo(stato.get('enabled'))}")
    if stato.get("enabled"):
        riga("Stato", stato.get("state", "sconosciuto"))
        riga("Profilo in uso", stato.get("config_id", "sconosciuto"))
        riga("Indirizzo ricevuto", stato.get("ip", "nessuno"))
    configurazioni = ctx.cliente.prova("vpn_client/config/") or []
    dire(f"Profili configurati: {len(configurazioni)}")
    for profilo in configurazioni:
        dire(
            f"{incolonna(profilo.get('description') or profilo.get('id', ''), 24)} {profilo.get('type', '')} {attivo_disattivo(profilo.get('active'))}"
        )
    if not configurazioni:
        dire("Nessun profilo: si creano dall'interfaccia web della box, perche' servono i file del fornitore della VPN.")


def controllo_contenuti(ctx):
    """Il controllo dei contenuti e i profili di rete dei dispositivi."""
    titolo("Controllo dei contenuti")
    try:
        config = ctx.cliente.prova("parental/config/") or {}
        modi = {"allowed": "tutto permesso", "denied": "tutto vietato", "webonly": "solo il web"}
        dire(f"Comportamento predefinito: {modi.get(config.get('default_filter_mode'), config.get('default_filter_mode', 'sconosciuto'))}")
        filtri = ctx.cliente.prova("parental/filter/") or []
        dire(f"Filtri impostati: {len(filtri)}")
        for filtro in filtri:
            dire(f"{incolonna(filtro.get('name', ''), 20)} {filtro.get('current_mode', '')} {filtro.get('comment', '')}")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
    profili = ctx.cliente.prova("profile/") or []
    dire(f"Profili di rete: {len(profili)}")
    for profilo in profili:
        dire(f"{incolonna(profilo.get('name', ''), 20)} {'in pausa' if profilo.get('paused') else 'attivo'}")
    controlli = ctx.cliente.prova("network_control/") or []
    dire(f"Regole di accesso alla rete: {len(controlli)}")
    for controllo in controlli:
        dire(f"{incolonna(controllo.get('name', ''), 20)} {controllo.get('current_mode', '')}")
    if not profili and not controlli:
        dire("Su questa box non c'e' nessun profilo: si creano dall'interfaccia web, assegnando dei dispositivi a una persona.")
        return
    if not profili or not chiedi_si_no("Vuoi mettere in pausa o riattivare un profilo?", False):
        return
    voci = {str(p.get("id")): f"{p.get('name')}, {'in pausa' if p.get('paused') else 'attivo'}" for p in profili}
    quale = scegli(voci, "quale profilo")
    if not quale:
        return
    profilo = next(p for p in profili if str(p.get("id")) == quale)
    nuovo = not profilo.get("paused")
    try:
        ctx.cliente.put(f"profile/{quale}", dati={"paused": nuovo})
        dire(f"Profilo {profilo.get('name')} {'messo in pausa' if nuovo else 'riattivato'}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def notifiche(ctx):
    """I telefoni e i computer che ricevono le notifiche della box."""
    titolo("Chi riceve le notifiche della box")
    try:
        bersagli = ctx.cliente.get("notif/targets/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Destinatari registrati: {len(bersagli)}")
    for bersaglio in bersagli:
        iscrizioni = ", ".join(bersaglio.get("subscriptions") or []) or "nessuna"
        dire(
            f"{incolonna(bersaglio.get('name', ''), 22)} {incolonna(bersaglio.get('type', ''), 10)} ultimo uso {da_quando(bersaglio.get('last_use'))}"
        )
        dire(f"  avvisi: {iscrizioni}")
    dire("I destinatari si aggiungono dall'applicazione ufficiale sul telefono: qui si controlla che non ce ne siano di sconosciuti.")
