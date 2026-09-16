# Iliadbox, l'accesso: associazione al router, login a sfida e permessi.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dalla auth.py del prototipo, con il nome del computer preso
# dal sistema, l'attesa dell'autorizzazione che riferisce cosa sta succedendo e
# la riautenticazione automatica quando la sessione scade.

"""Come Iliadbox entra nel router.

Due momenti distinti. L'associazione si fa una volta sola: il programma si
presenta, il router mostra sul suo display una richiesta e aspetta che
qualcuno prema la freccia destra sulla box, poi consegna un token. Il token
vale per sempre e va custodito, perche' da solo apre il router: vive in
config.json, che git non pubblica.

Il login si fa a ogni avvio, e anche ogni volta che la sessione scade. Il
router manda una sfida, una stringa buona una volta sola; il programma la
firma con il token usando HMAC-SHA1 e rimanda la firma. Il token, quindi, non
viaggia mai sulla rete. In cambio arriva un token di sessione, che va in
testa a ogni richiesta successiva, insieme all'elenco dei permessi concessi.
"""

import contextlib
import hashlib
import hmac
import socket
import time

from api import ErroreAPI, ErroreRete
from versione import NOME, VERSIONE

# I permessi che il programma chiede al momento dell'associazione. Chiederli
# tutti subito evita di dover rifare l'associazione quando servira' un comando
# che tocca un'altra area: il router li concede tutti in blocco, e chi non
# vuole concederne qualcuno lo toglie dall'interfaccia web della box.
PERMESSI_RICHIESTI = {
    "settings": True,
    "contacts": True,
    "calls": True,
    "explorer": True,
    "downloader": True,
    "parental": True,
    "pvr": True,
    "profile": True,
    "camera": True,
    "home": True,
    "player": True,
    "tv": True,
    "vm": True,
}
# Come si chiamano i permessi quando li si mostra a chi legge.
NOMI_PERMESSI = {
    "settings": "impostazioni del router",
    "contacts": "rubrica",
    "calls": "registro delle chiamate",
    "explorer": "file del disco",
    "downloader": "gestore degli scaricamenti",
    "parental": "controllo dei contenuti",
    "pvr": "registrazioni TV",
    "profile": "profili di rete",
    "camera": "videocamere",
    "home": "domotica",
    "player": "lettore multimediale",
    "tv": "televisione",
    "vm": "macchine virtuali",
    "wdo": "accesso da fuori casa",
}


class Accesso:
    """L'associazione, il login e i permessi della sessione."""

    def __init__(self, cliente, configurazione):
        self.cliente = cliente
        self.configurazione = configurazione
        self.app_id = configurazione.app_id
        self.nome_app = NOME
        self.versione_app = VERSIONE
        self.nome_dispositivo = configurazione.leggi("device_name") or socket.gethostname()
        self.permessi = {}
        self.token_sessione = None

    def associa(self, avviso=print, attesa_massima=120):
        """Chiede al router di fidarsi di questo programma.

        avviso viene chiamata con le frasi da mostrare, cosi' che la funzione
        non decida da sola come parlare: chi la usa da un'interfaccia diversa
        dal terminale le passa altro. attesa_massima sono i secondi concessi
        a chi deve premere il tasto sulla box.

        Restituisce vero se il token e' stato ottenuto e salvato.
        """
        richiesta = {
            "app_id": self.app_id,
            "app_name": self.nome_app,
            "app_version": self.versione_app,
            "device_name": self.nome_dispositivo,
            "permissions": PERMESSI_RICHIESTI,
        }
        risposta = self.cliente.post("login/authorize/", dati=richiesta)
        token = risposta.get("app_token")
        traccia = risposta.get("track_id")
        avviso("Richiesta inviata alla box.")
        avviso("Sul display della Iliadbox compare la richiesta di autorizzazione: premi la freccia destra per accettare.")
        stato = "pending"
        scadenza = time.time() + attesa_massima
        while stato == "pending" and time.time() < scadenza:
            time.sleep(2)
            controllo = self.cliente.get(f"login/authorize/{traccia}")
            nuovo = controllo.get("status", "unknown")
            if nuovo != stato:
                avviso(f"Stato della richiesta: {self.descrizione_stato(nuovo)}")
            stato = nuovo
        if stato == "granted":
            self.configurazione.scrivi("app_token", token)
            self.configurazione.scrivi("track_id", traccia)
            self.configurazione.scrivi("app_id", self.app_id)
            self.configurazione.scrivi("device_name", self.nome_dispositivo)
            avviso("Autorizzazione concessa: il token e' stato salvato in config.json e non serve piu' ripetere questa procedura.")
            return True
        avviso(f"Autorizzazione non ottenuta: {self.descrizione_stato(stato)}.")
        return False

    @staticmethod
    def descrizione_stato(stato):
        """La parola del router tradotta in una frase comprensibile."""
        return {
            "unknown": "richiesta sconosciuta alla box",
            "pending": "in attesa che qualcuno prema il tasto sulla box",
            "timeout": "tempo scaduto, nessuno ha premuto il tasto",
            "granted": "concessa",
            "denied": "rifiutata",
        }.get(stato, stato)

    def entra(self):
        """Fa il login con il token e prepara la sessione. Restituisce i permessi.

        Solleva ErroreAPI se il router rifiuta, ErroreRete se non risponde e
        ValueError se il token non c'e' proprio.
        """
        token = self.configurazione.token
        if not token:
            raise ValueError("Nessun token: prima va fatta l'associazione con la box.")
        sfida = self.cliente.chiama("get", "login/", riprova=False).get("challenge")
        firma = hmac.new(token.encode("utf-8"), sfida.encode("utf-8"), hashlib.sha1).hexdigest()
        risposta = self.cliente.chiama("post", "login/session/", dati={"app_id": self.app_id, "password": firma}, riprova=False)
        self.token_sessione = risposta.get("session_token")
        self.permessi = risposta.get("permissions", {})
        self.cliente.sessione.headers.update({"X-Fbx-App-Auth": self.token_sessione})
        self.cliente.riautentica = self._rientra
        return self.permessi

    def _rientra(self):
        """Rifa' il login quando la sessione e' scaduta. Vero se ci riesce."""
        try:
            self.entra()
            return True
        except (ErroreAPI, ErroreRete, ValueError):
            return False

    def esci(self):
        """Chiude la sessione sul router. Non solleva: si esce comunque."""
        with contextlib.suppress(ErroreAPI, ErroreRete):
            self.cliente.chiama("post", "login/logout/", riprova=False)
        self.cliente.sessione.headers.pop("X-Fbx-App-Auth", None)
        self.cliente.riautentica = None
        self.token_sessione = None

    def permesso(self, nome):
        """Vero se la sessione ha quel permesso."""
        return bool(self.permessi.get(nome))

    def elenco_permessi(self):
        """I permessi in righe leggibili, i concessi prima dei negati."""
        righe = []
        for chiave, valore in sorted(self.permessi.items(), key=lambda coppia: (not coppia[1], coppia[0])):
            nome = NOMI_PERMESSI.get(chiave, chiave)
            righe.append(f"{'si' if valore else 'no'} {nome} ({chiave})")
        return righe
