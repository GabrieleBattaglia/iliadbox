# -*- mode: python ; coding: utf-8 -*-
# Iliadbox, il file di compilazione per PyInstaller: un eseguibile in un file unico.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).
# 16/09/2026: nasce con la prima release. Il manuale viaggia dentro
# l'eseguibile, altrimenti il comando aiuto non avrebbe niente da mostrare.
#
# numpy e sounddevice restano fuori di proposito, e con loro la possibilita' di
# ascoltare le serie di numeri del comando storico: misurato il 16/09/2026,
# metterli dentro porta l'eseguibile da 46 a 125 MB e l'avvio da 1,4 a 5,5
# secondi, perche' un pacchetto in file unico si scompatta a ogni lancio. Per
# uno strumento che si apre per dare un'occhiata alla box, cinque secondi di
# attesa a ogni comando costano piu' di quello che vale una funzione sola. Chi
# la vuole lancia il programma dai sorgenti, dove funziona, oppure sposta
# 'numpy' e 'sounddevice' da excludes a hiddenimports e ricompila.

a = Analysis(
    ['iliadbox.py'],
    pathex=[],
    binaries=[],
    datas=[('manuale.txt', '.'), ('CHANGELOG.md', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'sounddevice', 'tkinter', 'PIL', 'matplotlib', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='iliadbox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
