# Iliadbox, i comandi: l'elenco di tutto cio' che il programma sa fare.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dalla CMD_MAP del prototipo, che teneva anche il codice dei
# comandi dentro la stessa classe. Qui resta solo l'elenco: il codice sta nei
# moduli per area, e aggiungere un comando vuol dire scrivere una riga qui.

"""Il registro dei comandi.

Ogni voce ha una chiave, che e' cio' che si digita, una descrizione, che e'
cio' che si legge nel menu, la funzione che la esegue e l'area a cui
appartiene. Le funzioni ricevono tutte lo stesso unico parametro, il
contesto, e non sanno niente del menu che le ha chiamate: cosi' lo stesso
comando si puo' lanciare dalla riga di comando del sistema operativo senza
cambiare una virgola.
"""

import dischi
import rete
import rete_wifi
import scaricamenti
import servizi
import sicurezza
import sistema
import voip
from formati import dire, errore, scegli, titolo

# L'ordine delle aree e' quello in cui compaiono nel menu delle aree.
AREE = [
    "Sistema e diagnosi",
    "Internet",
    "Rete locale",
    "Wi-Fi",
    "Sicurezza",
    "Disco e file",
    "Servizi di casa",
    "Telefono",
    "Programma",
]


def _voce(descrizione, funzione, area, scrive=False):
    return {"desc": descrizione, "funzione": funzione, "area": area, "scrive": scrive}


COMANDI = {
    # Sistema e diagnosi
    "stato": _voce("Stato della box: modello, firmware, tempo acceso, temperature", sistema.stato, "Sistema e diagnosi"),
    "temperatura": _voce("Temperature e ventole, anche in tempo reale", sistema.temperatura, "Sistema e diagnosi"),
    "diagnosi": _voce("Controllo completo della box, con gli avvisi in evidenza", sistema.diagnosi, "Sistema e diagnosi"),
    "rapporto": _voce("Salva su file un rapporto completo, scritto per esteso", sistema.rapporto, "Sistema e diagnosi"),
    "riavvia": _voce("Riavvia la box", sistema.riavvia, "Sistema e diagnosi", True),
    # Internet
    "internet": _voce("Connessione a internet: stato, indirizzi, portata, traffico", sistema.connessione, "Internet"),
    "traffico": _voce("Traffico in tempo reale, riga per riga", sistema.traffico, "Internet"),
    "storico": _voce("Storico di traffico, temperature e porte, anche da ascoltare", sistema.storico, "Internet"),
    "eventi": _voce("Registro della connessione: cadute, ritorni, cambi di portata", sistema.registro, "Internet"),
    "fibra": _voce("Collegamento in fibra e modulo ottico", sistema.fibra, "Internet"),
    "ipv6": _voce("Configurazione IPv6 e prefissi delegati", sistema.ipv6, "Internet"),
    "opzioni-internet": _voce("Filtro pubblicita', ping, accesso da fuori casa", sistema.configura_connessione, "Internet", True),
    # Rete locale
    "dispositivi": _voce("Dispositivi collegati alla rete di casa, con il dettaglio", rete.dispositivi, "Rete locale"),
    "sveglia": _voce("Accendi un computer spento con il pacchetto magico", rete.sveglia, "Rete locale", True),
    "lan": _voce("Nome e indirizzo del router sulla rete locale", rete.rete_locale, "Rete locale", True),
    "dhcp": _voce("Distribuzione automatica degli indirizzi", rete.dhcp, "Rete locale", True),
    "assegnazioni": _voce("Indirizzi assegnati adesso dal DHCP", rete.assegnazioni, "Rete locale"),
    "statici": _voce("Indirizzi fissi legati a un dispositivo", rete.statici, "Rete locale", True),
    "ethernet": _voce("Porte ethernet: cavi collegati e statistiche", rete.porte_ethernet, "Rete locale"),
    "dhcpv6": _voce("Distribuzione automatica degli indirizzi IPv6", rete.dhcpv6, "Rete locale", True),
    # Wi-Fi
    "wifi": _voce("Wi-Fi: stato generale, accensione e spegnimento", rete_wifi.stato_wifi, "Wi-Fi", True),
    "reti-wifi": _voce("Reti Wi-Fi: nome, protezione, e come cambiarli", rete_wifi.reti, "Wi-Fi", True),
    "chiavi-wifi": _voce("Mostra le password delle reti Wi-Fi", rete_wifi.chiavi, "Wi-Fi"),
    "punti-wifi": _voce("Punti di accesso: banda, canale, larghezza", rete_wifi.punti_accesso, "Wi-Fi", True),
    "collegati-wifi": _voce("Dispositivi attaccati al Wi-Fi, con segnale e velocita'", rete_wifi.collegati, "Wi-Fi"),
    "vicini-wifi": _voce("Reti Wi-Fi dei vicini e canali affollati", rete_wifi.vicini, "Wi-Fi"),
    "canali-wifi": _voce("Occupazione dei canali e quale conviene scegliere", rete_wifi.canali, "Wi-Fi"),
    "filtro-mac": _voce("Filtro degli indirizzi MAC: chi puo' collegarsi", rete_wifi.filtro_mac, "Wi-Fi", True),
    "orari-wifi": _voce("Calendario del Wi-Fi: quando e' acceso", rete_wifi.orari_wifi, "Wi-Fi", True),
    "wps": _voce("WPS, il collegamento senza password", rete_wifi.wps, "Wi-Fi", True),
    # Sicurezza
    "porte": _voce("Apertura porte verso internet", sicurezza.porte, "Sicurezza", True),
    "dmz": _voce("DMZ: un dispositivo esposto a internet", sicurezza.dmz, "Sicurezza", True),
    "porte-servizi": _voce("Porte occupate dai servizi della box", sicurezza.porte_dei_servizi, "Sicurezza", True),
    "vpn": _voce("Server VPN: stato, accensione, utenti, collegati", sicurezza.vpn, "Sicurezza", True),
    "vpn-cliente": _voce("La box collegata a una VPN esterna", sicurezza.vpn_cliente, "Sicurezza"),
    "contenuti": _voce("Controllo dei contenuti e profili di rete", sicurezza.controllo_contenuti, "Sicurezza", True),
    "notifiche": _voce("Chi riceve le notifiche della box", sicurezza.notifiche, "Sicurezza"),
    # Disco e file
    "dischi": _voce("Dischi, partizioni e spazio libero", dischi.dischi, "Disco e file"),
    "file": _voce("Naviga il disco della box: entra, copia, cancella, scarica", dischi.file_browser, "Disco e file", True),
    "compiti": _voce("Compiti che il router sta portando avanti sul disco", dischi.compiti, "Disco e file", True),
    "condivisioni": _voce("Collegamenti pubblici verso i file della box", dischi.condivisioni, "Disco e file", True),
    "risparmio-disco": _voce("Quando il disco si ferma da solo", servizi.risparmio_disco, "Disco e file", True),
    # Servizi di casa
    "samba": _voce("Condivisione dei file per Windows", servizi.condivisione_windows, "Servizi di casa", True),
    "afp": _voce("Condivisione dei file per Apple", servizi.condivisione_apple, "Servizi di casa", True),
    "ftp": _voce("Server FTP della box", servizi.ftp, "Servizi di casa", True),
    "multimediale": _voce("Server multimediale UPnP AV", servizi.server_multimediale, "Servizi di casa", True),
    "airmedia": _voce("AirMedia: manda musica o video a un apparecchio", servizi.airmedia, "Servizi di casa", True),
    "display": _voce("Display sul fronte della box", servizi.display, "Servizi di casa", True),
    "scaricamenti": _voce("Gestore degli scaricamenti della box", scaricamenti.scaricamenti, "Servizi di casa", True),
    # Telefono
    "chiamate": _voce("Registro delle chiamate", voip.chiamate, "Telefono", True),
    "telefono": _voce("Linee, cornette DECT, suoneria e volumi", voip.telefono, "Telefono", True),
    "rubrica": _voce("Rubrica della box", voip.rubrica, "Telefono", True),
}


def dizionario_menu():
    """Chiave e descrizione di ogni comando, per il menu principale."""
    return {chiave: voce["desc"] for chiave, voce in COMANDI.items()}


def esegui(ctx, chiave):
    """Esegue un comando. Restituisce falso se la chiave non esiste."""
    voce = COMANDI.get(chiave)
    if not voce:
        errore(f"comando sconosciuto: {chiave}")
        return False
    voce["funzione"](ctx)
    return True


def per_area():
    """I comandi raggruppati per area, nell'ordine delle aree."""
    gruppi = {area: {} for area in AREE}
    for chiave, voce in COMANDI.items():
        gruppi.setdefault(voce["area"], {})[chiave] = voce["desc"]
    return gruppi


def aree(ctx):
    """Naviga i comandi per area invece che tutti insieme."""
    gruppi = per_area()
    while True:
        voci = {area: f"{area}, {len(comandi)} comandi" for area, comandi in gruppi.items() if comandi}
        area = scegli(voci, "quale area")
        if not area:
            return
        chiave = scegli(gruppi[area], area.lower())
        if chiave:
            esegui(ctx, chiave)
            return


def elenco(ctx):
    """Stampa tutti i comandi, raggruppati per area."""
    titolo("Tutti i comandi")
    for area, comandi in per_area().items():
        if not comandi:
            continue
        dire(f"{area}:")
        for chiave, descrizione in sorted(comandi.items()):
            dire(f"  {chiave}: {descrizione}")
    dire(f"In tutto {len(COMANDI)} comandi, piu' cerca, aree, elenco, permessi, aiuto ed esci.")


def cerca(ctx):
    """Cerca un comando per parola, nella chiave o nella descrizione."""
    from formati import chiedi

    titolo("Cerca un comando")
    parola = chiedi("Che cosa cerchi: ", "s", smin=1, smax=40).strip().lower()
    if not parola:
        return
    trovati = {
        chiave: voce["desc"]
        for chiave, voce in COMANDI.items()
        if parola in chiave.lower() or parola in voce["desc"].lower() or parola in voce["area"].lower()
    }
    if not trovati:
        dire(f"Nessun comando per {parola}.")
        return
    dire(f"Trovati {len(trovati)} comandi.")
    chiave = scegli(trovati, f"risultati per {parola}")
    if chiave:
        esegui(ctx, chiave)


def permessi(ctx):
    """I permessi della sessione e i dati della box a cui siamo collegati."""
    from formati import riga

    titolo("Sessione e permessi")
    riga("Box", ctx.scoperta.get("box_model_name", "sconosciuta"))
    riga("Indirizzo", ctx.cliente.host)
    riga("Versione delle API", f"v{ctx.cliente.versione_api}")
    riga("Applicazione registrata come", ctx.accesso.app_id)
    riga("Nome di questo computer per la box", ctx.accesso.nome_dispositivo)
    riga("Chiamate fatte in questa sessione", ctx.cliente.chiamate)
    dire("Permessi:")
    for testo in ctx.accesso.elenco_permessi():
        dire(f"  {testo}")
    dire("I permessi si concedono e si tolgono dall'interfaccia web della box, alla voce Gestione degli accessi.")


def aiuto(ctx):
    """Apre il manuale del programma."""
    from GBUtils import manuale

    from percorsi import percorso_risorsa

    try:
        manuale(nf=percorso_risorsa("manuale.txt"), nome="Iliadbox")
    except (OSError, ValueError) as guaio:
        errore(f"il manuale non si apre: {guaio}")
        dire("L'elenco dei comandi si ottiene comunque con il comando elenco.")


def esci(ctx):
    """Chiude il programma."""
    ctx.uscita = True


COMANDI.update(
    {
        "aree": _voce("Scegli un comando navigando per area", aree, "Programma"),
        "elenco": _voce("Stampa tutti i comandi raggruppati per area", elenco, "Programma"),
        "cerca": _voce("Cerca un comando per parola", cerca, "Programma"),
        "permessi": _voce("Permessi della sessione e dati della box", permessi, "Programma"),
        "aiuto": _voce("Apri il manuale", aiuto, "Programma"),
        "esci": _voce("Chiudi il programma", esci, "Programma"),
    }
)
