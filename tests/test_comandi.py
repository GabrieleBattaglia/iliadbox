"""Prove del registro dei comandi e delle righe che compongono le schermate.

Il registro e' il punto in cui un comando si aggiunge, quindi la prova serve a
scoprire subito una voce scritta male: una funzione che non esiste, un'area
inventata, una chiave doppia.
"""

import pytest

import comandi
import dischi
from comandi import AREE, COMANDI, dizionario_menu, per_area


def test_ogni_comando_ha_una_funzione_vera():
    for chiave, voce in COMANDI.items():
        assert callable(voce["funzione"]), f"{chiave} non ha una funzione"
        assert voce["desc"], f"{chiave} non ha descrizione"


def test_le_aree_esistono_tutte():
    for chiave, voce in COMANDI.items():
        assert voce["area"] in AREE, f"{chiave} sta in un'area che non esiste: {voce['area']}"


def test_le_chiavi_sono_scritte_per_essere_digitate():
    for chiave in COMANDI:
        assert chiave == chiave.lower()
        assert " " not in chiave
        assert len(chiave) <= 20


def test_il_menu_contiene_tutto():
    voci = dizionario_menu()
    assert set(voci) == set(COMANDI)
    assert all(isinstance(descrizione, str) for descrizione in voci.values())


def test_i_gruppi_coprono_tutti_i_comandi():
    gruppi = per_area()
    totale = sum(len(comandi_area) for comandi_area in gruppi.values())
    assert totale == len(COMANDI)


def test_esegui_chiama_la_funzione_giusta():
    chiamati = []
    COMANDI["prova-finta"] = {"desc": "prova", "funzione": lambda ctx: chiamati.append(ctx), "area": "Programma", "scrive": False}
    try:
        assert comandi.esegui("contesto finto", "prova-finta") is True
        assert chiamati == ["contesto finto"]
    finally:
        del COMANDI["prova-finta"]


def test_esegui_dice_di_no_a_un_comando_inventato(capsys):
    assert comandi.esegui(None, "questo-non-esiste") is False
    assert "sconosciuto" in capsys.readouterr().out


def test_ci_sono_i_comandi_del_programma():
    for chiave in ("aiuto", "elenco", "cerca", "aree", "permessi", "esci"):
        assert chiave in COMANDI


def test_percorsi_in_base64():
    # Il router vuole i percorsi in base64, e li rivuole identici.
    assert dischi.codifica("/iliadbox") == "L2lsaWFkYm94"
    assert dischi.decodifica("L2lsaWFkYm94") == "/iliadbox"
    strano = "/iliadbox/Città degli angeli/così"
    assert dischi.decodifica(dischi.codifica(strano)) == strano


def test_elenco_di_una_cartella_in_tutte_e_due_le_forme():
    # A volte il router risponde una lista, a volte un dizionario con entries.
    voce = {"name": "file", "type": "file"}
    assert dischi._voci([voce]) == [voce]
    assert dischi._voci({"entries": [voce]}) == [voce]
    assert dischi._voci(None) == []


@pytest.mark.parametrize("chiave", ["stato", "diagnosi", "wifi", "file", "chiamate"])
def test_i_comandi_storici_ci_sono_ancora(chiave):
    assert chiave in COMANDI
