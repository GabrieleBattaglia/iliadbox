# Iliadbox, il telefono: registro delle chiamate, linee, cornette DECT e rubrica.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dal comando phone del prototipo, che elencava dieci chiamate
# e basta. Qui il registro si filtra, si segna come letto e si svuota, e le
# cornette senza filo si fanno squillare per ritrovarle.

"""Il telefono di casa visto dalla box.

Il registro tiene tutte le chiamate, non solo le ultime: da qui si guarda per
tipo, si segna come letto cio' che era nuovo e si cancella cio' che non serve
piu'. Le cornette DECT si registrano, si fanno squillare tutte insieme per
ritrovarle sotto il divano, e si puo' cambiare la suoneria.
"""

from api import ErroreAPI, ErroreRete
from formati import (
    attivo_disattivo,
    chiedi,
    conferma,
    data_estesa,
    data_ora,
    dire,
    durata,
    errore,
    incolonna,
    riga,
    scegli,
    si_no,
    titolo,
)

TIPI_CHIAMATA = {"missed": "persa", "accepted": "ricevuta", "outgoing": "fatta"}
# Il verso della chiamata in due caratteri, per le righe strette.
FRECCE = {"missed": "<x", "accepted": "<-", "outgoing": "->"}


def _riga_chiamata(chiamata):
    """Una chiamata in una riga sola."""
    chi = chiamata.get("name") or chiamata.get("number") or "sconosciuto"
    nuova = "*" if chiamata.get("new") else " "
    return (
        f"{nuova} {data_ora(chiamata.get('datetime'))} {FRECCE.get(chiamata.get('type'), '??')} "
        f"{incolonna(chi, 26)} {durata(chiamata.get('duration'))}"
    )


def righe_chiamate(cliente, quante=20):
    """Le ultime chiamate, una per riga."""
    elenco = cliente.get("call/log/") or []
    ordinate = sorted(elenco, key=lambda c: c.get("datetime", 0), reverse=True)
    nuove = [c for c in elenco if c.get("new")]
    righe = [f"Chiamate in registro: {len(elenco)}, di cui {len(nuove)} non ancora lette"]
    righe += [_riga_chiamata(c) for c in ordinate[:quante]]
    return righe


def chiamate(ctx):
    """Il registro delle chiamate, con i filtri e la pulizia."""
    titolo("Registro delle chiamate")
    dire("L'asterisco davanti a una riga vuol dire che la chiamata non e' ancora stata vista. La freccia dice il verso: freccia verso sinistra ricevuta, con la x persa, verso destra fatta da casa.")
    try:
        elenco = ctx.cliente.get("call/log/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    filtri = {
        "tutte": f"Tutte le chiamate ({len(elenco)})",
        "perse": f"Solo le perse ({sum(1 for c in elenco if c.get('type') == 'missed')})",
        "nuove": f"Solo quelle mai viste ({sum(1 for c in elenco if c.get('new'))})",
        "ricevute": f"Solo le ricevute ({sum(1 for c in elenco if c.get('type') == 'accepted')})",
        "fatte": f"Solo quelle fatte da casa ({sum(1 for c in elenco if c.get('type') == 'outgoing')})",
    }
    quale = scegli(filtri, "cosa mostro")
    if not quale:
        return
    if quale == "perse":
        scelte = [c for c in elenco if c.get("type") == "missed"]
    elif quale == "nuove":
        scelte = [c for c in elenco if c.get("new")]
    elif quale == "ricevute":
        scelte = [c for c in elenco if c.get("type") == "accepted"]
    elif quale == "fatte":
        scelte = [c for c in elenco if c.get("type") == "outgoing"]
    else:
        scelte = list(elenco)
    scelte.sort(key=lambda c: c.get("datetime", 0), reverse=True)
    dire(f"Chiamate: {len(scelte)}")
    for chiamata in scelte:
        dire(_riga_chiamata(chiamata))
    voci = {
        "dettaglio": "Dettaglio di una chiamata",
        "lette": "Segna tutte come lette",
        "cancella": "Cancella una chiamata",
        "svuota": "Svuota tutto il registro",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "lette":
            ctx.cliente.post("call/log/mark_all_as_read/")
            dire("Tutte segnate come lette.")
        elif scelta == "svuota":
            dire(f"Sto per cancellare tutte le {len(elenco)} chiamate del registro.")
            if not conferma("Invio svuota il registro, Esc annulla"):
                dire("\nAnnullato.")
                return
            ctx.cliente.post("call/log/delete_all/")
            dire("\nRegistro svuotato.")
        elif not scelte:
            dire("Non c'e' niente su cui lavorare.")
        elif scelta == "dettaglio":
            voci_chiamate = {str(c.get("id")): _riga_chiamata(c) for c in scelte}
            numero = scegli(voci_chiamate, "quale chiamata")
            if not numero:
                return
            chiamata = next(c for c in scelte if str(c.get("id")) == numero)
            titolo("Dettaglio della chiamata")
            riga("Quando", data_estesa(chiamata.get("datetime")))
            riga("Tipo", TIPI_CHIAMATA.get(chiamata.get("type"), chiamata.get("type")))
            riga("Numero", chiamata.get("number"))
            riga("Nome", chiamata.get("name"))
            riga("Durata", durata(chiamata.get("duration")))
            riga("Mai vista", si_no(chiamata.get("new")))
            if chiamata.get("new"):
                ctx.cliente.put(f"call/log/{numero}", dati={"new": False})
                dire("Segnata come letta.")
        elif scelta == "cancella":
            voci_chiamate = {str(c.get("id")): _riga_chiamata(c) for c in scelte}
            numero = scegli(voci_chiamate, "quale cancellare")
            if not numero:
                return
            ctx.cliente.delete(f"call/log/{numero}")
            dire("Cancellata.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def righe_telefono(cliente):
    """Lo stato delle linee e delle cornette."""
    linee = cliente.prova("phone/") or []
    config = cliente.prova("phone/config/") or {}
    righe = [f"Rete telefonica: {config.get('network', 'sconosciuta')}", f"Linee e cornette: {len(linee)}"]
    for linea in linee:
        tipo = "presa del telefono" if linea.get("type") == "fxs" else "cornetta senza filo"
        stato = "squilla" if linea.get("is_ringing") else ("a riposo" if linea.get("on_hook") else "in conversazione")
        guasto = ", guasta" if linea.get("hardware_defect") else ""
        righe.append(f"{tipo} numero {linea.get('id')}: {stato}{guasto}")
    righe.append(f"DECT: {attivo_disattivo(config.get('dect_enabled'))}")
    righe.append(f"Registrazione di cornette nuove: {attivo_disattivo(config.get('dect_registration'))}")
    righe.append(f"Modo eco: {attivo_disattivo(config.get('dect_eco_mode'))}")
    righe.append(f"Suoneria numero {config.get('dect_ring_pattern')}")
    return righe


def telefono(ctx):
    """Le linee, le cornette DECT e cosa si puo' fare con loro."""
    titolo("Telefono")
    try:
        config = ctx.cliente.get("phone/config/")
        for testo in righe_telefono(ctx.cliente):
            dire(testo)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    voci = {
        "squilla": "Fai squillare le cornette per ritrovarle",
        "zitte": "Smetti di farle squillare",
        "dect": "Accendi o spegni il DECT",
        "registrazione": "Apri o chiudi la registrazione di una cornetta nuova",
        "suoneria": "Cambia la suoneria delle cornette",
        "eco": "Accendi o spegni il modo eco",
        "pin": "Cambia il codice PIN del DECT",
        "guadagni": "Regola il volume di una linea",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "squilla":
            ctx.cliente.post("phone/dect_page_start/")
            dire("Le cornette stanno squillando: quando l'hai trovata, scegli di farle smettere o premi un tasto sulla cornetta.")
        elif scelta == "zitte":
            ctx.cliente.post("phone/dect_page_stop/")
            dire("Silenzio.")
        elif scelta == "dect":
            nuovo = not config.get("dect_enabled")
            ctx.cliente.put("phone/config/", dati={"dect_enabled": nuovo})
            dire(f"DECT {attivo_disattivo(nuovo)}.")
        elif scelta == "registrazione":
            nuovo = not config.get("dect_registration")
            if nuovo:
                dire("La box accetta una cornetta nuova: mettila in registrazione adesso. Il codice PIN da digitare e' quello della box.")
            ctx.cliente.put("phone/config/", dati={"dect_registration": nuovo})
            dire(f"Registrazione {attivo_disattivo(nuovo)}.")
        elif scelta == "suoneria":
            numero = chiedi(f"Numero della suoneria da 1 a 8, adesso {config.get('dect_ring_pattern')}: ", "i", imin=1, imax=8, default=config.get("dect_ring_pattern", 1))
            ctx.cliente.put("phone/config/", dati={"dect_ring_pattern": numero})
            dire(f"Suoneria numero {numero}.")
        elif scelta == "eco":
            nuovo = not config.get("dect_eco_mode")
            ctx.cliente.put("phone/config/", dati={"dect_eco_mode": nuovo})
            dire(f"Modo eco {attivo_disattivo(nuovo)}: quando e' acceso la box abbassa la potenza radio del DECT.")
        elif scelta == "pin":
            nuovo = chiedi("Nuovo codice PIN di quattro cifre: ", "s", smin=4, smax=4).strip()
            if nuovo.isdigit():
                ctx.cliente.put("phone/config/", dati={"dect_pin": nuovo})
                dire("PIN cambiato.")
            else:
                dire("Il PIN deve essere di quattro cifre.")
        elif scelta == "guadagni":
            _guadagni(ctx)
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)


def _guadagni(ctx):
    """Regola il volume in entrata e in uscita di una linea."""
    linee = ctx.cliente.prova("phone/") or []
    if not linee:
        dire("Non c'e' nessuna linea.")
        return
    voci = {str(linea.get("id")): f"linea {linea.get('id')}, {linea.get('type')}" for linea in linee}
    quale = scegli(voci, "quale linea")
    if not quale:
        return
    linea = next(item for item in linee if str(item.get("id")) == quale)
    dire(f"Volume in ricezione adesso {linea.get('gain_rx')}, predefinito {linea.get('default_gain_rx')}.")
    dire(f"Volume in trasmissione adesso {linea.get('gain_tx')}, predefinito {linea.get('default_gain_tx')}.")
    ricezione = chiedi("Nuovo volume in ricezione da 0 a 100: ", "i", imin=0, imax=100, default=linea.get("gain_rx"))
    trasmissione = chiedi("Nuovo volume in trasmissione da 0 a 100: ", "i", imin=0, imax=100, default=linea.get("gain_tx"))
    ctx.cliente.put(f"phone/{quale}", dati={"gain_rx": ricezione, "gain_tx": trasmissione})
    dire("Volumi impostati.")


def _riga_contatto(contatto):
    """Un contatto in una riga sola, con il primo numero."""
    numeri = contatto.get("numbers") or []
    primo = numeri[0].get("number") if numeri else ""
    return f"{incolonna(contatto.get('display_name') or 'senza nome', 30)} {primo}"


def rubrica(ctx):
    """La rubrica della box: chi c'e', come cercarlo, come aggiungerlo."""
    titolo("Rubrica")
    try:
        elenco = ctx.cliente.get("contact/") or []
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
        return
    dire(f"Contatti in rubrica: {len(elenco)}")
    voci = {
        "elenco": "Elenca tutti i contatti",
        "cerca": "Cerca un contatto",
        "aggiungi": "Aggiungi un contatto",
        "togli": "Togli un contatto",
        "niente": "Torna indietro",
    }
    scelta = scegli(voci, "cosa faccio")
    if not scelta or scelta == "niente":
        return
    try:
        if scelta == "elenco":
            for contatto in sorted(elenco, key=lambda c: (c.get("display_name") or "").lower()):
                dire(_riga_contatto(contatto))
        elif scelta == "cerca":
            cosa = chiedi("Nome o numero da cercare: ", "s", smin=1, smax=64).strip().lower()
            if not cosa:
                return
            trovati = []
            for contatto in elenco:
                testo = (contatto.get("display_name") or "").lower()
                numeri = " ".join(n.get("number", "") for n in contatto.get("numbers") or [])
                if cosa in testo or cosa in numeri:
                    trovati.append(contatto)
            dire(f"Trovati: {len(trovati)}")
            for contatto in trovati:
                dire(_riga_contatto(contatto))
                for numero in contatto.get("numbers") or []:
                    dire(f"  {numero.get('type', 'numero')}: {numero.get('number')}")
                for posta in contatto.get("emails") or []:
                    dire(f"  posta: {posta.get('email')}")
        elif scelta == "aggiungi":
            nome = chiedi("Nome da mostrare: ", "s", smin=1, smax=64).strip()
            numero = chiedi("Numero di telefono: ", "s", smin=3, smax=32).strip()
            if not nome or not numero:
                dire("Manca qualcosa, non faccio niente.")
                return
            tipo = scegli({"home": "casa", "mobile": "cellulare", "work": "lavoro", "fax": "fax", "other": "altro"}, "che numero e'") or "home"
            creato = ctx.cliente.post("contact/", dati={"display_name": nome, "last_name": nome})
            ctx.cliente.post("number/", dati={"contact_id": creato.get("id"), "number": numero, "type": tipo, "is_default": True})
            dire(f"{nome} aggiunto alla rubrica con il numero {numero}.")
        elif scelta == "togli":
            if not elenco:
                dire("La rubrica e' vuota.")
                return
            voci_contatti = {str(c.get("id")): _riga_contatto(c) for c in elenco}
            quale = scegli(voci_contatti, "quale togliere")
            if not quale:
                return
            if not conferma("Invio toglie il contatto, Esc annulla"):
                dire("\nAnnullato.")
                return
            ctx.cliente.delete(f"contact/{quale}")
            dire("\nTolto.")
    except (ErroreAPI, ErroreRete) as guaio:
        errore(guaio)
