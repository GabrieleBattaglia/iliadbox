# Iliadbox, il cliente HTTP: una sola porta d'ingresso verso le API del router.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce dalla api.py del prototipo, con gli errori sollevati invece
# che stampati, il metodo DELETE, i parametri di query, la riautenticazione
# automatica quando la sessione scade e il conteggio delle chiamate.

"""Il dialogo con la Iliadbox.

Il router espone una API REST su HTTPS con un certificato firmato da se'
stesso: e' il motivo per cui la verifica del certificato e' spenta, come fa
qualunque cliente che parli con un apparecchio sulla rete locale. Le
risposte hanno tutte la stessa forma, un dizionario con success, result ed
error_code, e qui viene srotolata: chi chiama riceve il result e basta,
oppure un ErroreAPI che dice codice e messaggio. Cosi' i moduli dei comandi
non ripetono a ogni riga il controllo su success.

La sessione del router scade dopo qualche minuto di inattivita'. Quando il
router risponde auth_required il cliente rifa' il login da solo, una volta
sola, e ripete la chiamata: chi lavora non se ne accorge.
"""

import json

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOST_PREDEFINITO = "192.168.1.254"
VERSIONE_API_PREDEFINITA = 15
TEMPO_MASSIMO = 15
# I codici con cui il router dice che la sessione non vale piu': a quel punto
# non c'e' niente di rotto, basta rifare il login.
CODICI_SESSIONE = ("auth_required", "invalid_session", "invalid_token")


class ErroreAPI(Exception):
    """Una risposta del router che dice di no, con il suo codice.

    codice e' l'error_code delle API, per esempio insufficient_rights,
    service_down, invalid_request; messaggio e' la frase che il router manda,
    gia' in italiano perche' la box e' configurata in italiano; endpoint dice
    su quale richiesta e' successo. mancante, quando c'e', e' il permesso che
    manca alla sessione.
    """

    def __init__(self, codice, messaggio, endpoint="", mancante=None):
        self.codice = codice or "sconosciuto"
        self.messaggio = messaggio or ""
        self.endpoint = endpoint
        self.mancante = mancante
        testo = self.messaggio or self.codice
        if self.mancante:
            testo = f"{testo} (permesso mancante: {self.mancante})"
        super().__init__(testo)


class ErroreRete(Exception):
    """Il router non risponde affatto: spento, irraggiungibile o indirizzo sbagliato."""


class Client:
    """Il cliente delle API, con la sessione HTTP e il token di sessione."""

    def __init__(self, host=HOST_PREDEFINITO, porta=None, tempo_massimo=TEMPO_MASSIMO):
        self.host = host
        self.porta = porta
        self.tempo_massimo = tempo_massimo
        self.versione_api = VERSIONE_API_PREDEFINITA
        self.radice_api = "/api/"
        self.modello = ""
        self.versione_firmware = ""
        self.sessione = requests.Session()
        self.sessione.verify = False
        self.sessione.headers.update({"Content-Type": "application/json"})
        # Chi sa rifare il login: lo imposta Auth dopo il primo accesso.
        self.riautentica = None
        self.chiamate = 0
        self.ultimo_errore = None

    @property
    def base(self):
        """L'inizio di ogni indirizzo: https, host, porta e versione delle API."""
        porta = f":{self.porta}" if self.porta else ""
        return f"https://{self.host}{porta}{self.radice_api}v{self.versione_api}/"

    def indirizzo(self, endpoint):
        return f"{self.base}{endpoint.lstrip('/')}"

    def scopri(self):
        """Chiede al router versione delle API e nome del modello.

        La scoperta si fa in chiaro sulla porta 80, che e' l'unico punto delle
        API a non chiedere HTTPS, e serve proprio a sapere dove parlare dopo.
        Restituisce il dizionario del router. Solleva ErroreRete se non
        risponde nessuno.
        """
        indirizzo = f"http://{self.host}/api_version"
        try:
            risposta = requests.get(indirizzo, timeout=self.tempo_massimo)
            risposta.raise_for_status()
            dati = risposta.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as errore:
            raise ErroreRete(f"Nessuna risposta da {self.host}: {errore}") from errore
        self.versione_api = int(str(dati.get("api_version", "15.0")).split(".")[0])
        self.radice_api = dati.get("api_base_url", "/api/")
        self.modello = dati.get("box_model_name", "")
        return dati

    def chiama(self, metodo, endpoint, dati=None, parametri=None, riprova=True):
        """Una chiamata alle API: restituisce il result, o solleva.

        metodo e' get, post, put o delete; endpoint e' la parte che segue la
        versione, per esempio "system/"; dati e' il corpo JSON; parametri
        finisce nella query. Con riprova falso il login scaduto non viene
        rifatto: serve alle chiamate di login, che scaduto non possono essere.
        """
        indirizzo = self.indirizzo(endpoint)
        self.chiamate += 1
        try:
            risposta = self.sessione.request(metodo.upper(), indirizzo, json=dati, params=parametri, timeout=self.tempo_massimo)
        except requests.exceptions.RequestException as errore:
            self.ultimo_errore = str(errore)
            raise ErroreRete(f"{metodo.upper()} {endpoint}: {errore}") from errore
        try:
            corpo = risposta.json()
        except json.JSONDecodeError as errore:
            self.ultimo_errore = risposta.text[:200]
            raise ErroreAPI("risposta_illeggibile", f"Risposta non in JSON ({risposta.status_code})", endpoint) from errore
        if corpo.get("success"):
            return corpo.get("result")
        codice = corpo.get("error_code")
        if codice in CODICI_SESSIONE and riprova and self.riautentica and self.riautentica():
            return self.chiama(metodo, endpoint, dati=dati, parametri=parametri, riprova=False)
        self.ultimo_errore = f"{codice}: {corpo.get('msg', '')}"
        raise ErroreAPI(codice, corpo.get("msg", ""), endpoint, corpo.get("missing_right"))

    def get(self, endpoint, parametri=None):
        return self.chiama("get", endpoint, parametri=parametri)

    def post(self, endpoint, dati=None, parametri=None):
        return self.chiama("post", endpoint, dati=dati, parametri=parametri)

    def put(self, endpoint, dati=None, parametri=None):
        return self.chiama("put", endpoint, dati=dati, parametri=parametri)

    def delete(self, endpoint, dati=None, parametri=None):
        return self.chiama("delete", endpoint, dati=dati, parametri=parametri)

    def posta_modulo(self, endpoint, campi):
        """Una POST con i campi come li manda un modulo di pagina web.

        Serve al gestore degli scaricamenti, che e' l'unico punto delle API a
        non volere il JSON: vuole i campi codificati come una form, altrimenti
        risponde che la richiesta non e' valida.
        """
        indirizzo = self.indirizzo(endpoint)
        self.chiamate += 1
        intestazioni = dict(self.sessione.headers)
        intestazioni["Content-Type"] = "application/x-www-form-urlencoded"
        try:
            risposta = self.sessione.post(indirizzo, data=campi, headers=intestazioni, timeout=self.tempo_massimo)
            corpo = risposta.json()
        except requests.exceptions.RequestException as errore:
            raise ErroreRete(f"POST {endpoint}: {errore}") from errore
        except json.JSONDecodeError as errore:
            raise ErroreAPI("risposta_illeggibile", "Risposta non in JSON", endpoint) from errore
        if corpo.get("success"):
            return corpo.get("result")
        raise ErroreAPI(corpo.get("error_code"), corpo.get("msg", ""), endpoint, corpo.get("missing_right"))

    def prova(self, endpoint, parametri=None, predefinito=None):
        """Come get, ma un errore vale come "niente da dire".

        Serve alle schermate che raccolgono dati da piu' punti, dove un
        servizio spento o un permesso mancante non devono fermare tutto il
        resto: la funzione risponde predefinito e chi chiama tira dritto.
        """
        try:
            return self.get(endpoint, parametri=parametri)
        except (ErroreAPI, ErroreRete):
            return predefinito

    def scarica(self, endpoint, percorso, avanzamento=None):
        """Scarica un file dal router e lo scrive su disco, a pezzi.

        endpoint e' l'indirizzo relativo, per esempio dl/ seguito dal percorso
        in base64; avanzamento, se c'e', viene chiamata con i byte scritti
        finora e il totale dichiarato, che puo' essere zero quando il router
        non lo dice. Restituisce i byte scritti.
        """
        indirizzo = self.indirizzo(endpoint)
        scritti = 0
        try:
            with self.sessione.get(indirizzo, stream=True, timeout=self.tempo_massimo) as risposta:
                risposta.raise_for_status()
                totale = int(risposta.headers.get("Content-Length", 0))
                with open(percorso, "wb") as file_uscita:
                    for pezzo in risposta.iter_content(chunk_size=262144):
                        if not pezzo:
                            continue
                        file_uscita.write(pezzo)
                        scritti += len(pezzo)
                        if avanzamento:
                            avanzamento(scritti, totale)
        except requests.exceptions.RequestException as errore:
            raise ErroreRete(f"Scaricamento di {endpoint}: {errore}") from errore
        return scritti
