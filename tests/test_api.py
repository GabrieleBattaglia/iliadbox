"""Prove del cliente delle API, contro risposte finte.

Niente box vera: la sessione HTTP viene sostituita con una che risponde
quello che serve alla prova, cosi' le prove girano anche senza il router in
casa e non cambiano niente a nessuno.
"""

import json

import pytest

from api import HOST_PREDEFINITO, Client, ErroreAPI, ErroreRete


class RispostaFinta:
    def __init__(self, corpo, stato=200):
        self._corpo = corpo
        self.status_code = stato
        self.text = json.dumps(corpo) if isinstance(corpo, dict) else str(corpo)

    def json(self):
        if isinstance(self._corpo, dict):
            return self._corpo
        raise json.JSONDecodeError("non e' JSON", self.text, 0)


class SessioneFinta:
    """Risponde a turno quello che le si e' messo in bocca, e annota le chiamate."""

    def __init__(self, risposte):
        self.risposte = list(risposte)
        self.fatte = []
        self.headers = {}

    def request(self, metodo, indirizzo, json=None, params=None, timeout=None):
        self.fatte.append((metodo, indirizzo, json, params))
        if not self.risposte:
            raise AssertionError(f"chiamata in piu': {metodo} {indirizzo}")
        return self.risposte.pop(0)

    def post(self, indirizzo, data=None, headers=None, timeout=None):
        self.fatte.append(("POST", indirizzo, data, None))
        return self.risposte.pop(0)


def cliente_con(risposte):
    cliente = Client()
    cliente.sessione = SessioneFinta(risposte)
    return cliente


def test_indirizzo_costruito_bene():
    cliente = Client(host="192.168.1.254")
    assert cliente.indirizzo("system/") == "https://192.168.1.254/api/v15/system/"
    cliente.porta = 11991
    assert cliente.indirizzo("/system/") == "https://192.168.1.254:11991/api/v15/system/"
    assert Client().host == HOST_PREDEFINITO


def test_risposta_riuscita_restituisce_solo_il_risultato():
    cliente = cliente_con([RispostaFinta({"success": True, "result": {"firmware_version": "4.9"}})])
    assert cliente.get("system/") == {"firmware_version": "4.9"}
    assert cliente.chiamate == 1


def test_errore_diventa_eccezione_con_il_codice():
    cliente = cliente_con(
        [RispostaFinta({"success": False, "error_code": "insufficient_rights", "msg": "manca il permesso", "missing_right": "settings"})]
    )
    with pytest.raises(ErroreAPI) as guaio:
        cliente.get("wifi/config/")
    assert guaio.value.codice == "insufficient_rights"
    assert guaio.value.mancante == "settings"
    assert "settings" in str(guaio.value)


def test_sessione_scaduta_rifa_il_login_e_ripete():
    risposte = [
        RispostaFinta({"success": False, "error_code": "auth_required", "msg": "devi entrare"}),
        RispostaFinta({"success": True, "result": {"ok": True}}),
    ]
    cliente = cliente_con(risposte)
    tentativi = []

    def finto_login():
        tentativi.append(1)
        return True

    cliente.riautentica = finto_login
    assert cliente.get("system/") == {"ok": True}
    assert len(tentativi) == 1


def test_sessione_scaduta_senza_login_solleva():
    cliente = cliente_con([RispostaFinta({"success": False, "error_code": "auth_required", "msg": "devi entrare"})])
    cliente.riautentica = lambda: False
    with pytest.raises(ErroreAPI):
        cliente.get("system/")


def test_risposta_illeggibile():
    cliente = cliente_con([RispostaFinta("<html>pagina di errore</html>")])
    with pytest.raises(ErroreAPI) as guaio:
        cliente.get("system/")
    assert guaio.value.codice == "risposta_illeggibile"


def test_prova_non_solleva_mai():
    cliente = cliente_con([RispostaFinta({"success": False, "error_code": "service_down", "msg": "spento"})])
    assert cliente.prova("pvr/config/", predefinito={}) == {}


def test_metodi_passano_il_verbo_giusto():
    risposte = [RispostaFinta({"success": True, "result": None}) for _ in range(3)]
    cliente = cliente_con(risposte)
    cliente.put("lcd/config/", dati={"brightness": 40})
    cliente.delete("fw/redir/1")
    cliente.post("system/reboot/")
    verbi = [chiamata[0] for chiamata in cliente.sessione.fatte]
    assert verbi == ["PUT", "DELETE", "POST"]
    assert cliente.sessione.fatte[0][2] == {"brightness": 40}


def test_modulo_manda_i_campi_come_form():
    cliente = cliente_con([RispostaFinta({"success": True, "result": {"id": 7}})])
    assert cliente.posta_modulo("downloads/add", {"download_url": "http://esempio/file"}) == {"id": 7}
    _, indirizzo, dati, _ = cliente.sessione.fatte[0]
    assert dati == {"download_url": "http://esempio/file"}
    assert indirizzo.endswith("downloads/add")


def test_errore_di_rete_diventa_errore_rete():
    class SessioneRotta(SessioneFinta):
        def request(self, *argomenti, **parole):
            import requests

            raise requests.exceptions.ConnectTimeout("nessuno risponde")

    cliente = Client()
    cliente.sessione = SessioneRotta([])
    with pytest.raises(ErroreRete):
        cliente.get("system/")
