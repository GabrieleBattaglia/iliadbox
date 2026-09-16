"""Prove delle schermate di sistema e della lettura delle serie storiche.

Le funzioni che cominciano con righe_ non stampano: restituiscono righe, e
sono quindi le piu' facili da provare. Il cliente qui e' finto e risponde con
un pezzo di quello che risponderebbe una box vera.
"""

import pytest

from api import ErroreAPI
from sistema import _riassunto_serie, _serie_storica, righe_connessione, righe_diagnosi, righe_stato

SISTEMA = {
    "board_name": "fbxgw8r",
    "firmware_version": "4.9.18.2",
    "serial": "0000",
    "mac": "00:11:22:33:44:55",
    "uptime_val": 90061,
    "model_info": {"pretty_name": "iliadbox (r1)", "net_operator": "iliad_ita", "default_language": "ita"},
    "sensors": [
        {"id": "temp_t1", "name": "Temperatura 1", "value": 54},
        {"id": "temp_cpub", "name": "Temperatura della CPU B", "value": 57},
    ],
    "fans": [{"id": "fan0_speed", "name": "Ventola 1", "value": 1530}],
    "disk_status": "active",
    "user_storage_powered": True,
    "box_authenticated": True,
}
CONNESSIONE = {
    "state": "up",
    "media": "ethernet",
    "ipv4": "81.56.167.214",
    "ipv6": "2a01:e11::1",
    "bandwidth_down": 2_500_000_000,
    "bandwidth_up": 2_500_000_000,
    "rate_down": 3382,
    "rate_up": 2797,
    "bytes_down": 135_597_077_733,
    "bytes_up": 29_095_000_414,
    "ipv4_port_range": [8192, 16383],
}


class ClienteFinto:
    """Risponde quello che gli si e' messo nel dizionario, e nient'altro."""

    def __init__(self, risposte, storico=None):
        self.risposte = risposte
        self.storico = storico or {}
        self.chieste = []

    def get(self, endpoint, parametri=None):
        self.chieste.append(endpoint)
        if endpoint not in self.risposte:
            raise ErroreAPI("invalid_request", "Richiesta non valida (404)", endpoint)
        return self.risposte[endpoint]

    def post(self, endpoint, dati=None, parametri=None):
        if endpoint == "rrd/":
            return self.storico
        raise ErroreAPI("invalid_request", "Richiesta non valida", endpoint)

    def prova(self, endpoint, parametri=None, predefinito=None):
        return self.risposte.get(endpoint, predefinito)


def test_righe_stato_dicono_le_cose_importanti():
    righe = righe_stato(ClienteFinto({"system/": SISTEMA}))
    testo = "\n".join(righe)
    assert "iliadbox (r1)" in testo
    assert "4.9.18.2" in testo
    assert "1 giorno, 1 ora e 1 minuto" in testo
    # Le temperature stanno in un elenco di sensori, non in una chiave fissa.
    assert "Temperatura della CPU B: 57 gradi" in testo
    assert "Ventola 1: 1.530 giri al minuto" in testo


def test_righe_connessione():
    testo = "\n".join(righe_connessione(ClienteFinto({"connection/": CONNESSIONE})))
    assert "Stato: attiva" in testo
    assert "2,5 Gb/s" in testo
    assert "81.56.167.214" in testo
    assert "dalla 8192 alla 16383" in testo


def test_serie_storica_riporta_i_valori_alla_loro_scala():
    # Il router moltiplica per la precisione chiesta: 522 con precisione 10
    # vuol dire 52,2 gradi.
    cliente = ClienteFinto({}, storico={"data": [{"time": 1, "temp_t1": 522}, {"time": 2, "temp_t1": 531}]})
    punti = _serie_storica(cliente, "temp", 3600, precisione=10)
    assert punti[0]["temp_t1"] == pytest.approx(52.2)
    assert punti[1]["temp_t1"] == pytest.approx(53.1)
    assert punti[0]["time"] == 1


def test_riassunto_di_una_serie():
    punti = [{"time": 1, "x": 10}, {"time": 2, "x": 20}, {"time": 3, "x": 30}]
    riassunto = _riassunto_serie(punti, "x")
    assert riassunto["minimo"] == 10
    assert riassunto["massimo"] == 30
    assert riassunto["media"] == 20
    assert len(riassunto["valori"]) == 3
    assert _riassunto_serie(punti, "manca") is None


def test_diagnosi_trova_i_guai():
    caldo = dict(SISTEMA)
    caldo["sensors"] = [{"name": "Temperatura 1", "value": 90}]
    caldo["fans"] = [{"name": "Ventola 1", "value": 0}]
    risposte = {
        "system/": caldo,
        "connection/": dict(CONNESSIONE, state="down"),
        "wifi/config/": {"enabled": False},
        "wifi/bss/": [{"config": {"ssid": "aperta", "encryption": "none"}}],
        "fw/dmz/": {"enabled": True, "ip": "192.168.1.9"},
        "ftp/config/": {"enabled": True, "allow_anonymous": True},
        "connection/config/": {"remote_access": True, "allow_token_request": True},
        "dhcp/config/": {"enabled": False},
    }
    righe, avvisi = righe_diagnosi(ClienteFinto(risposte))
    testo = "\n".join(righe)
    assert avvisi >= 7
    assert "guasto" in testo
    assert "troppo calda" in testo
    assert "Ventola 1 ferma" in testo
    assert "connessione a internet down" in testo
    assert "protezione insicura" in testo
    assert "DMZ" in testo or "esposto" in testo


def test_diagnosi_su_una_box_a_posto():
    risposte = {
        "system/": SISTEMA,
        "connection/": CONNESSIONE,
        "connection/logs/": [],
        "wifi/config/": {"enabled": True},
        "wifi/bss/": [{"config": {"ssid": "casa", "encryption": "wpa2_psk_ccmp"}}],
        "wifi/ap/": [],
        "storage/disk/": [],
        "storage/partition/": [{"label": "iliadbox", "total_bytes": 1000, "free_bytes": 900, "state": "mounted"}],
        "connection/config/": {},
        "ftp/config/": {"enabled": False},
        "fw/dmz/": {"enabled": False},
        "fw/redir/": [],
        "dhcp/config/": {"enabled": True},
        "lan/browser/pub/": [{"active": True}, {"active": False}],
    }
    righe, avvisi = righe_diagnosi(ClienteFinto(risposte))
    assert avvisi == 0
    assert righe[-1].startswith("ok")


def test_diagnosi_quando_la_box_non_risponde():
    righe, avvisi = righe_diagnosi(ClienteFinto({}))
    assert avvisi == 1
    assert righe[0].startswith("guasto")
