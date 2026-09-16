"""Prove dei formati di Iliadbox: numeri, misure, tempi e parole.

Sono le funzioni che scrivono ogni riga che l'utente legge, quindi sbagliarle
si vede subito e dappertutto. Si lanciano dalla cartella del progetto con
python -m pytest -q.
"""

import datetime

from formati import (
    acceso_spento,
    attivo_disattivo,
    banda,
    cifratura,
    da_quando,
    data_estesa,
    data_ora,
    dimensione,
    durata,
    durata_breve,
    incolonna,
    intero,
    numero,
    percentuale,
    segnale,
    si_no,
    taglia,
    tipo_apparecchio,
    velocita_bit,
    velocita_breve,
    velocita_byte,
)


def test_numero_con_la_virgola():
    assert numero(12.345) == "12,3"
    assert numero(12.345, 2) == "12,35"
    assert numero(None) == "sconosciuto"


def test_intero_con_i_punti():
    assert intero(1234567) == "1.234.567"
    assert intero(0) == "0"
    assert intero(None) == "sconosciuto"


def test_parole_di_stato():
    assert si_no(True) == "si"
    assert si_no(None) == "no"
    assert acceso_spento(1) == "acceso"
    assert attivo_disattivo(0) == "disattivo"


def test_dimensione():
    assert dimensione(0) == "0 B"
    assert dimensione(1024) == "1,0 KB"
    assert dimensione(None) == "sconosciuta"
    # Sotto il chilo niente decimali: mezzo byte non esiste.
    assert dimensione(980) == "980 B"


def test_velocita_in_bit_e_in_byte():
    assert velocita_bit(2_500_000_000) == "2,5 Gb/s"
    assert velocita_bit(1_000_000) == "1,0 Mb/s"
    assert velocita_bit(999) == "999 b/s"
    assert velocita_byte(0).startswith("0 B")
    assert velocita_byte(None) == "sconosciuta"


def test_velocita_breve_sta_in_pochi_caratteri():
    assert velocita_breve(0) == "0"
    assert velocita_breve(512) == "512"
    assert velocita_breve(1024) == "1,0K"
    assert velocita_breve(5 * 1024 * 1024) == "5,0M"
    assert len(velocita_breve(1234567)) <= 5


def test_percentuale():
    assert percentuale(1, 2) == "50,0%"
    assert percentuale(1, 0) == "sconosciuta"


def test_durata_a_parole():
    assert durata(0) == "0 secondi"
    assert durata(1) == "1 secondo"
    assert durata(60) == "1 minuto"
    assert durata(3661) == "1 ora, 1 minuto e 1 secondo"
    assert durata(3660) == "1 ora e 1 minuto"
    assert durata(90061) == "1 giorno, 1 ora e 1 minuto"
    assert durata(None) == "sconosciuta"


def test_durata_breve():
    assert durata_breve(59) == "00:59"
    assert durata_breve(3600) == "01:00:00"
    assert durata_breve(90000) == "1g01h"
    assert durata_breve(None) == "?"


def test_date():
    momento = datetime.datetime(2026, 9, 16, 14, 32).timestamp()
    assert data_ora(momento) == "16/09/26 14:32"
    assert "16 settembre 2026" in data_estesa(momento)
    assert data_ora(0) == "mai"
    assert da_quando(None) == "mai"


def test_segnale_con_il_giudizio():
    assert "ottimo" in segnale(-50)
    assert "buono" in segnale(-65)
    assert "debole" in segnale(-70)
    assert "scarso" in segnale(-90)
    assert segnale(0) == "sconosciuto"


def test_banda_normalizza_le_forme_delle_api():
    # Le API scrivono la stessa banda in due modi a seconda del punto.
    assert banda("2d4g") == "2,4 GHz"
    assert banda("2G4") == "2,4 GHz"
    assert banda("5g") == banda("5G") == "5 GHz"
    assert banda(None) == "sconosciuta"
    assert banda("strana") == "strana"


def test_cifratura_e_apparecchi():
    assert "WPA2" in cifratura("wpa2_psk_ccmp")
    assert "aperta" in cifratura("none")
    assert cifratura("chissa") == "chissa"
    assert tipo_apparecchio("smartphone") == "telefono"
    assert tipo_apparecchio(None) == "sconosciuto"


def test_colonne_di_larghezza_fissa():
    assert len(incolonna("abc", 10)) == 10
    assert len(incolonna("abcdefghijklmnop", 10)) == 10
    assert taglia("abcdefghij", 5) == "ab..."
    assert taglia("abc", 5) == "abc"
