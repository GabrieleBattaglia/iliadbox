# Iliadbox, i servizi: condivisione dei file, FTP, UPnP AV, AirMedia e display.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dai comandi ftp e lcd del prototipo, con l'aggiunta di
# Samba, AFP, il server multimediale e l'invio di un suono al televisore.

"""I servizi che la box offre alla rete di casa.

Samba e' la condivisione dei file che vede Windows, e la sua impostazione
piu' delicata e' logon_enabled: quando e' acceso, per entrare nelle cartelle
servono nome e password; quando e' spento, la condivisione e' libera per
chiunque sia in casa. Il server FTP e' un modo piu' vecchio di prendere gli
stessi file, e puo' essere aperto anche da internet, che e' proprio il caso in
cui conviene guardarlo due volte.
"""

from api import ErroreAPI, ErroreRete
from formati import (
    acceso_spento,
    attivo_disattivo,
    chiedi,
    chiedi_si_no,
    conferma,
    dire,
    errore,
    incolonna,
    riga,
    scegli,
    si_no,
    titolo,
)


def righe_condivisione(cliente):
    """Come la box condivide i file con la rete di casa."""
    righe = []
    samba = cliente.prova("netshare/samba/") or {}
    righe.append(f"Condivisione Windows: {attivo_disattivo(samba.get('file_share_enabled'))}")
    righe.append(f"Gruppo di lavoro: {samba.get('workgroup')}")
    righe.append(f"Richiede nome e password: {si_no(samba.get('logon_enabled'))}")
    righe.append(f"Utente della condivisione: {samba.get('logon_user')}")
    righe.append(f"Protocollo SMB versione 2: {attivo_disattivo(samba.get('smbv2_enabled'))}")
    righe.append(f"Condivisione delle stampanti: {attivo_disattivo(samba.get('print_share_enabled'))}")
    afp = cliente.prova("netshare/afp/") or {}
    righe.append(f"Condivisione Apple: {attivo_disattivo(afp.get('enabled'))}")
    ftp = cliente.prova("ftp/config/") or {}
    righe.append(f"Server FTP: {attivo_disattivo(ftp.get('enabled'))}")
    righe.append(f"FTP raggiungibile da internet: {si_no(ftp.get('allow_remote_access'))}")
    upnp = cliente.prova("upnpav/config/") or {}
    righe.append(f"Server multimediale UPnP AV: {attivo_disattivo(upnp.get('enabled'))}")
    aria = cliente.prova("airmedia/config/") or {}
    righe.append(f"AirMedia: {attivo_disattivo(aria.get('enabled'))}")
    return righe


def condivisione_windows(ctx):
    """La condivisione dei file che Windows vede come cartelle di rete."""
    titolo("Condivisione dei file, Samba")
    try:
        config = ctx.cliente.get("netshare/samba/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    riga("Condivisione dei file", attivo_disattivo(config.get("file_share_enabled")))
    riga("Gruppo di lavoro", config.get("workgroup"))
    riga("Chiede nome e password", si_no(config.get("logon_enabled")))
    riga("Utente", config.get("logon_user"))
    riga("SMB versione 2", attivo_disattivo(config.get("smbv2_enabled")))
    riga("Condivisione delle stampanti", attivo_disattivo(config.get("print_share_enabled")))
    voci = {
        "file_share_enabled": "Accendere o spegnere la condivisione dei file",
        "logon_enabled": "Chiedere o non chiedere nome e password",
        "smbv2_enabled": "Accendere o spegnere SMB versione 2",
        "print_share_enabled": "Condividere o no le stampanti",
        "workgroup": "Cambiare il gruppo di lavoro",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa cambiare")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "workgroup":
            nuovo = chiedi(f"Gruppo di lavoro, adesso {config.get('workgroup')}: ", "s", smin=1, smax=32, default=config.get("workgroup")).strip()
            if nuovo and nuovo != config.get("workgroup"):
                ctx.cliente.put("netshare/samba/", dati={"workgroup": nuovo})
                dire(f"Gruppo di lavoro impostato a {nuovo}.")
            return
        nuovo = not config.get(scelta)
        if scelta == "logon_enabled" and not nuovo:
            dire("Attenzione: senza nome e password, chiunque sia collegato alla rete di casa entra nelle cartelle condivise.")
        if not conferma("Invio conferma, Esc annulla"):
            dire("\nAnnullato.")
            return
        ctx.cliente.put("netshare/samba/", dati={scelta: nuovo})
        dire(f"\nFatto: {voci[scelta]} adesso vale {si_no(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def condivisione_apple(ctx):
    """La condivisione dei file per i computer Apple."""
    titolo("Condivisione dei file, AFP")
    try:
        config = ctx.cliente.get("netshare/afp/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    riga("Condivisione AFP", attivo_disattivo(config.get("enabled")))
    riga("Ospiti ammessi senza password", si_no(config.get("guest_allow")))
    riga("Nome utente", config.get("login_name"))
    riga("Tipo di server", config.get("server_type"))
    if not chiedi_si_no("Vuoi accendere o spegnere la condivisione AFP?", False):
        return
    try:
        nuovo = not config.get("enabled")
        ctx.cliente.put("netshare/afp/", dati={"enabled": nuovo})
        dire(f"AFP {attivo_disattivo(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def ftp(ctx):
    """Il server FTP della box: stato, porte e accesso da internet."""
    titolo("Server FTP")
    try:
        config = ctx.cliente.get("ftp/config/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    riga("Server FTP", attivo_disattivo(config.get("enabled")))
    riga("Utente", config.get("username"))
    riga("Ammette collegamenti anonimi", si_no(config.get("allow_anonymous")))
    riga("Gli anonimi possono scrivere", si_no(config.get("allow_anonymous_write")))
    riga("Raggiungibile da internet", si_no(config.get("allow_remote_access")))
    riga("Porta di controllo", config.get("port_ctrl"))
    riga("Porta dei dati", config.get("port_data"))
    if config.get("allow_remote_access"):
        riga("Indirizzo da fuori casa", config.get("remote_domain"))
    if config.get("weak_password"):
        dire("Attenzione: la box considera debole la password di questo servizio.")
    voci = {
        "enabled": "Accendere o spegnere il server",
        "allow_anonymous": "Ammettere o no i collegamenti anonimi",
        "allow_anonymous_write": "Lasciare o no scrivere gli anonimi",
        "allow_remote_access": "Aprire o chiudere l'accesso da internet",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa cambiare")
    if not scelta or scelta == "niente":
        return
    nuovo = not config.get(scelta)
    if scelta == "allow_remote_access" and nuovo:
        dire("Attenzione: aprendo l'FTP a internet, il disco della box diventa raggiungibile da fuori con una password sola.")
    if scelta == "allow_anonymous" and nuovo:
        dire("Attenzione: con i collegamenti anonimi chiunque sia in rete puo' leggere i file senza password.")
    if not conferma("Invio conferma, Esc annulla"):
        dire("\nAnnullato.")
        return
    try:
        ctx.cliente.put("ftp/config/", dati={scelta: nuovo})
        dire(f"\nFatto: {voci[scelta]} adesso vale {si_no(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def server_multimediale(ctx):
    """Il server UPnP AV, che mostra i file della box a televisori e lettori."""
    titolo("Server multimediale UPnP AV")
    try:
        config = ctx.cliente.get("upnpav/config/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Server multimediale: {attivo_disattivo(config.get('enabled'))}")
    dire("Quando e' acceso, i televisori e i lettori di casa vedono da soli i file multimediali del disco della box.")
    if not chiedi_si_no("Vuoi cambiare?", False):
        return
    try:
        nuovo = not config.get("enabled")
        ctx.cliente.put("upnpav/config/", dati={"enabled": nuovo})
        dire(f"Server multimediale {attivo_disattivo(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def airmedia(ctx):
    """AirMedia: mandare musica, foto o video agli apparecchi che lo sanno ricevere."""
    titolo("AirMedia")
    try:
        config = ctx.cliente.get("airmedia/config/")
        ricevitori = ctx.cliente.prova("airmedia/receivers/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"AirMedia: {attivo_disattivo(config.get('enabled'))}")
    dire(f"Apparecchi che sanno ricevere: {len(ricevitori)}")
    for ricevitore in ricevitori:
        capacita = ricevitore.get("capabilities") or {}
        cosa = ", ".join(nome for nome, puo in capacita.items() if puo) or "niente"
        dire(f"{incolonna(ricevitore.get('name', ''), 32)} riceve {cosa}{', con password' if ricevitore.get('password_protected') else ''}")
    voci = {"manda": "Manda qualcosa a un apparecchio", "ferma": "Ferma la riproduzione", "acceso": "Accendi o spegni AirMedia", "niente": "Torna indietro"}
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "acceso":
            nuovo = not config.get("enabled")
            ctx.cliente.put("airmedia/config/", dati={"enabled": nuovo})
            dire(f"AirMedia {attivo_disattivo(nuovo)}.")
            return
        if not ricevitori:
            dire("Non c'e' nessun apparecchio che sappia ricevere.")
            return
        voci_ricevitori = {r.get("name"): r.get("name") for r in ricevitori}
        quale = scegli(voci_ricevitori, "quale apparecchio")
        if not quale:
            return
        if scelta == "ferma":
            ctx.cliente.post(f"airmedia/receivers/{quale}/", dati={"action": "stop", "media_type": "video"})
            dire("Riproduzione fermata.")
            return
        tipo = scegli({"audio": "musica o suono", "video": "video", "photo": "foto"}, "che cosa mandi")
        if not tipo:
            return
        indirizzo = chiedi("Indirizzo del file, per esempio http://192.168.1.10/brano.mp3: ", "s", smin=5, smax=1024).strip()
        if not indirizzo:
            return
        parola = chiedi("Password dell'apparecchio (Invio per nessuna): ", "s", default="").strip()
        richiesta = {"action": "start", "media_type": tipo, "media": indirizzo, "position": 0}
        if parola:
            richiesta["password"] = parola
        ctx.cliente.post(f"airmedia/receivers/{quale}/", dati=richiesta)
        dire(f"Inviato a {quale}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def display(ctx):
    """Il display sul fronte della box: luminosita', orientamento, cosa mostra."""
    titolo("Display della box")
    try:
        config = ctx.cliente.get("lcd/config/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    riga("Luminosita'", f"{config.get('brightness')} per cento")
    riga("Orientamento", f"{config.get('orientation')} gradi")
    riga("Orientamento forzato a mano", si_no(config.get("orientation_forced")))
    riga("Nasconde la password del Wi-Fi", si_no(config.get("hide_wifi_key")))
    riga("Nasconde la spia luminosa", si_no(config.get("hide_status_led")))
    voci = {
        "brightness": "Luminosita' del display",
        "orientation": "Orientamento del display",
        "hide_wifi_key": "Nascondere o mostrare la password del Wi-Fi",
        "hide_status_led": "Nascondere o mostrare la spia luminosa",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa cambiare")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "brightness":
            nuovo = chiedi(f"Luminosita' da 0 a 100, adesso {config.get('brightness')}: ", "i", imin=0, imax=100, default=config.get("brightness"))
            ctx.cliente.put("lcd/config/", dati={"brightness": nuovo})
            dire(f"Luminosita' impostata a {nuovo}.")
        elif scelta == "orientation":
            nuovo = scegli({"0": "dritto", "90": "ruotato di 90 gradi", "180": "capovolto", "270": "ruotato di 270 gradi"}, "come")
            if not nuovo:
                return
            ctx.cliente.put("lcd/config/", dati={"orientation": int(nuovo), "orientation_forced": True})
            dire(f"Display ruotato di {nuovo} gradi.")
        else:
            nuovo = not config.get(scelta)
            ctx.cliente.put("lcd/config/", dati={scelta: nuovo})
            dire(f"Fatto: {voci[scelta]} adesso vale {si_no(nuovo)}.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def risparmio_disco(ctx):
    """Quando il disco esterno si ferma da solo per non consumare."""
    titolo("Risparmio energetico del disco")
    try:
        config = ctx.cliente.get("storage/config/")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    riga("Spegnimento automatico", acceso_spento(config.get("external_pm_enabled")))
    riga("Minuti di riposo prima di fermarsi", config.get("external_pm_idle_before_spindown"))
    if not chiedi_si_no("Vuoi cambiare?", False):
        return
    try:
        if chiedi_si_no("Tenere acceso lo spegnimento automatico?", bool(config.get("external_pm_enabled"))):
            minuti = chiedi("Dopo quanti minuti di riposo si ferma: ", "i", imin=1, imax=240, default=config.get("external_pm_idle_before_spindown", 10))
            ctx.cliente.put("storage/config/", dati={"external_pm_enabled": True, "external_pm_idle_before_spindown": minuti})
            dire(f"Il disco si fermera' dopo {minuti} minuti di riposo.")
        else:
            ctx.cliente.put("storage/config/", dati={"external_pm_enabled": False})
            dire("Il disco restera' sempre in rotazione.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
