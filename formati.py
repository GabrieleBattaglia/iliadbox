# Iliadbox, i formati: numeri all'italiana, date, unita' di misura e domande.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce con la prima release, raccogliendo le formule che nel
# prototipo stavano sparse dentro i comandi.

"""Come Iliadbox scrive le cose.

Tutto cio' che il programma dice a numeri passa da qui, cosi' la virgola
decimale, le unita' di misura e le date sono le stesse in ogni schermata.
Le regole sono quelle dello screen reader: niente separatori grafici, niente
righe vuote di servizio, e i dati che cambiano in tempo reale scritti come
una riga sola entro quaranta caratteri, fra due ritorni carrello, perche' su
un display braille a otto punti quaranta caratteri sono una lettura sola.

Le spiegazioni invece restano lunghe quanto serve: la console e' larga e
spezzare una frase a quaranta caratteri la rende soltanto piu' faticosa.
"""

import datetime

from GBUtils import accorcia, dgt, enter_escape, formatta_dimensione, key, menu

LARGHEZZA_BRAILLE = 40
GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = [
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
]


def dire(testo=""):
    """Una riga di testo normale."""
    print(testo)


def titolo(testo):
    """L'intestazione di una schermata: a capo prima, niente separatori grafici."""
    print(f"\n{testo}")


def errore(testo):
    """Un guaio da riferire a chi legge."""
    print(f"Errore: {testo}")


def prompt_compatto(testo):
    """Una riga di dati in tempo reale, entro quaranta caratteri, fra due ritorni carrello.

    Il ritorno carrello finale riporta il cursore all'inizio della riga: il
    display braille la legge dal primo carattere senza scorrere.
    """
    print("\n\r" + testo[:LARGHEZZA_BRAILLE] + "\r", end="", flush=True)


def riga(etichetta, valore):
    """Una voce con il suo valore, per esempio "Firmware: 4.9.18.2"."""
    print(f"{etichetta}: {valore}")


def numero(valore, decimali=1):
    """Un numero all'italiana, con la virgola al posto del punto."""
    if valore is None:
        return "sconosciuto"
    return f"{valore:.{decimali}f}".replace(".", ",")


def intero(valore):
    """Un intero con il punto ogni tre cifre: 1.234.567."""
    if valore is None:
        return "sconosciuto"
    return f"{int(valore):,}".replace(",", ".")


def si_no(valore):
    return "si" if valore else "no"


def acceso_spento(valore):
    return "acceso" if valore else "spento"


def attivo_disattivo(valore):
    return "attivo" if valore else "disattivo"


def dimensione(byte, decimali=1):
    """Una quantita' di byte con l'unita' adatta: 1,4 GB."""
    if byte is None:
        return "sconosciuta"
    return formatta_dimensione(byte, decimali=decimali, separatore=",", byte_interi=True)


def velocita_byte(byte_al_secondo, decimali=1):
    """Una velocita' in byte al secondo, come la misura il router: 1,2 MB/s."""
    if byte_al_secondo is None:
        return "sconosciuta"
    return formatta_dimensione(byte_al_secondo, decimali=decimali, separatore=",", byte_interi=True) + "/s"


def velocita_bit(bit_al_secondo, decimali=1):
    """Una velocita' in bit al secondo, come la dichiara l'operatore: 2,5 Gb/s."""
    if bit_al_secondo is None:
        return "sconosciuta"
    valore = float(bit_al_secondo)
    for unita, soglia in (("Gb/s", 1_000_000_000), ("Mb/s", 1_000_000), ("kb/s", 1_000)):
        if valore >= soglia:
            return f"{numero(valore / soglia, decimali)} {unita}"
    return f"{intero(valore)} b/s"


def velocita_breve(byte_al_secondo):
    """Una velocita' in pochi caratteri, per le righe in tempo reale: 1,2M.

    Niente spazio e niente unita' per esteso: su un display braille ogni
    carattere e' una cella, e il contesto dice gia' che si parla di byte al
    secondo.
    """
    if not byte_al_secondo:
        return "0"
    valore = float(byte_al_secondo)
    for lettera, soglia in (("G", 1024**3), ("M", 1024**2), ("K", 1024)):
        if valore >= soglia:
            return f"{numero(valore / soglia, 1)}{lettera}"
    return f"{int(valore)}"


def percentuale(parte, totale, decimali=1):
    """Quanto e' parte rispetto a totale, in percento."""
    if not totale:
        return "sconosciuta"
    return f"{numero(parte / totale * 100, decimali)}%"


def data_ora(marca):
    """Un momento nel tempo, come lo scrive un orologio: 16/09/26 14:32."""
    if not marca:
        return "mai"
    return datetime.datetime.fromtimestamp(marca).strftime("%d/%m/%y %H:%M")


def data_estesa(marca):
    """Un momento nel tempo detto per esteso: lunedì 16 settembre 2026 alle 14:32."""
    if not marca:
        return "mai"
    momento = datetime.datetime.fromtimestamp(marca)
    return f"{GIORNI[momento.weekday()]} {momento.day} {MESI[momento.month - 1]} {momento.year} alle {momento:%H:%M}"


def durata(secondi):
    """Una durata detta a parole, saltando le parti che valgono zero."""
    if secondi is None:
        return "sconosciuta"
    secondi = int(secondi)
    if secondi < 60:
        return f"{secondi} second{'o' if secondi == 1 else 'i'}"
    giorni, resto = divmod(secondi, 86400)
    ore, resto = divmod(resto, 3600)
    minuti, sec = divmod(resto, 60)
    parti = []
    if giorni:
        parti.append(f"{giorni} giorn{'o' if giorni == 1 else 'i'}")
    if ore:
        parti.append(f"{ore} or{'a' if ore == 1 else 'e'}")
    if minuti:
        parti.append(f"{minuti} minut{'o' if minuti == 1 else 'i'}")
    if sec and not giorni:
        parti.append(f"{sec} second{'o' if sec == 1 else 'i'}")
    if not parti:
        return "meno di un minuto"
    if len(parti) == 1:
        return parti[0]
    return ", ".join(parti[:-1]) + " e " + parti[-1]


def durata_breve(secondi):
    """Una durata in cifre, per le righe compatte: 62g 22h, oppure 04:12."""
    if secondi is None:
        return "?"
    secondi = int(secondi)
    giorni, resto = divmod(secondi, 86400)
    ore, resto = divmod(resto, 3600)
    minuti, sec = divmod(resto, 60)
    if giorni:
        return f"{giorni}g{ore:02d}h"
    return f"{ore:02d}:{minuti:02d}:{sec:02d}" if ore else f"{minuti:02d}:{sec:02d}"


def da_quando(marca):
    """Quanto tempo e' passato da un momento: 3 ore fa."""
    if not marca:
        return "mai"
    passati = int(datetime.datetime.now().timestamp() - marca)
    if passati < 0:
        return data_ora(marca)
    if passati < 60:
        return "adesso"
    return durata(passati) + " fa"


def segnale(dbm):
    """La potenza di un segnale radio con il suo giudizio: -65 dBm, buono."""
    if dbm is None or dbm == 0:
        return "sconosciuto"
    if dbm >= -55:
        giudizio = "ottimo"
    elif dbm >= -67:
        giudizio = "buono"
    elif dbm >= -75:
        giudizio = "debole"
    else:
        giudizio = "scarso"
    return f"{dbm} dBm, {giudizio}"


def banda(sigla):
    """La banda radio come la si nomina parlando: 2,4 GHz.

    Le API scrivono la stessa banda in modi diversi a seconda del punto in cui
    la si chiede, 2d4g dentro le informazioni radio e 2G4 dentro lo stato di
    una rete: qui le forme diventano una sola.
    """
    if not sigla:
        return "sconosciuta"
    nomi = {"2d4g": "2,4 GHz", "2g4": "2,4 GHz", "5g": "5 GHz", "6g": "6 GHz", "60g": "60 GHz"}
    return nomi.get(str(sigla).lower(), sigla)


def cifratura(sigla):
    """Il tipo di protezione di una rete Wi-Fi, in chiaro."""
    nomi = {
        "wep": "WEP, obsoleta e insicura",
        "wpa_psk_auto": "WPA",
        "wpa_psk_tkip": "WPA con TKIP",
        "wpa_psk_ccmp": "WPA con AES",
        "wpa2_psk_auto": "WPA2",
        "wpa2_psk_tkip": "WPA2 con TKIP",
        "wpa2_psk_ccmp": "WPA2 con AES",
        "wpa3_psk_sae": "WPA3",
        "wpa23_psk_ccmp_mrsno": "WPA2 e WPA3",
        "wpa23_psk_sae_ccmp": "WPA2 e WPA3",
        "none": "aperta, senza password",
    }
    return nomi.get(sigla, sigla or "sconosciuta")


def tipo_apparecchio(sigla):
    """La categoria di un dispositivo di rete, in italiano."""
    nomi = {
        "workstation": "computer",
        "laptop": "portatile",
        "smartphone": "telefono",
        "tablet": "tavoletta",
        "printer": "stampante",
        "vg_console": "console",
        "television": "televisione",
        "nas": "disco di rete",
        "ip_camera": "videocamera",
        "ip_phone": "telefono IP",
        "freebox_player": "player",
        "freebox_server": "router",
        "networking_device": "apparato di rete",
        "multimedia_device": "apparecchio multimediale",
        "car": "automobile",
        "other": "altro",
    }
    return nomi.get(sigla, sigla or "sconosciuto")


def taglia(testo, lunghezza, posizione="fine"):
    """Un testo ridotto alla larghezza voluta, con i puntini al posto del resto."""
    return accorcia(testo or "", lunghezza, posizione)


def incolonna(testo, larghezza):
    """Un testo portato a larghezza fissa, tagliato o allungato con spazi.

    Serve agli elenchi in cui la stessa informazione deve stare sempre nella
    stessa colonna: sul display braille le dita la ritrovano senza cercarla.
    """
    return taglia(testo or "", larghezza).ljust(larghezza)


def chiedi(domanda, tipo="s", **limiti):
    """Una domanda che aspetta una riga scritta.

    Il prompt e' testo normale, senza i ritorni carrello dei prompt a tasto
    singolo: su una riga che si sta scrivendo il ritorno carrello finale
    riporterebbe il cursore sopra la domanda e lo screen reader leggerebbe
    male mentre si digita.
    """
    return dgt(domanda, kind=tipo, **limiti)


def chiedi_si_no(domanda, predefinito=None):
    """Una domanda da si o no. Restituisce vero, falso, o il predefinito a vuoto."""
    if predefinito is None:
        suggerimento = "s/n"
        valore_vuoto = None
    else:
        suggerimento = "S/n" if predefinito else "s/N"
        valore_vuoto = predefinito
    while True:
        risposta = dgt(f"{domanda} ({suggerimento}): ", kind="s").strip().lower()
        if not risposta:
            if valore_vuoto is not None:
                return valore_vuoto
            continue
        if risposta[0] in "sy":
            return True
        if risposta[0] == "n":
            return False


def conferma(domanda):
    """Chiede conferma con un tasto solo: Invio conferma, Escape annulla.

    Il prompt sta fra due ritorni carrello, perche' qui non si scrive niente e
    il display braille deve restare sulla domanda.
    """
    return bool(enter_escape(f"\r{taglia(domanda, LARGHEZZA_BRAILLE)}\r"))


def pausa(testo="premi un tasto"):
    """Ferma lo scorrimento finche' non si preme un tasto."""
    key(f"\r{taglia(testo, LARGHEZZA_BRAILLE)}\r")


def scegli(voci, prompt="scegli", mostra=True):
    """Un menu di voci: restituisce la chiave scelta, o None se si annulla."""
    if not voci:
        return None
    return menu(voci, p=f"{prompt}> ", ntf="nessuna voce corrisponde", show=mostra, keyslist=True, pager=20)


def elenco_numerato(voci, prompt="scegli"):
    """Un menu numerato, per gli elenchi che non hanno chiavi parlanti."""
    if not voci:
        return None
    return menu(voci, p=f"{prompt}> ", ntf="nessuna voce corrisponde", show=True, numbered=True, ordered=False, pager=20)


def mostra_righe(righe):
    """Stampa una lista di righe gia' pronte."""
    for testo in righe:
        print(testo)
