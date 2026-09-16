# Iliadbox

Il router Iliadbox dalla tastiera: un programma da console che fa quello che fa l'interfaccia web della box, ma in righe di testo e menu che si filtrano digitando.

Nasce per un motivo preciso. L'interfaccia web della Iliadbox è fatta di riquadri, cursori e finestrelle che uno screen reader attraversa a fatica, e certe impostazioni con NVDA non si raggiungono affatto. Le stesse cose, però, la box le espone attraverso le sue API, le stesse che usa l'applicazione ufficiale: questo programma passa da lì, e ogni informazione diventa una riga che la sintesi vocale legge e il display braille mostra.

Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalità auto).

## Che cosa sa fare

Cinquantotto comandi, divisi in aree.

**Sistema e diagnosi**: stato della box, temperature e ventole anche in tempo reale, diagnosi completa con gli avvisi in evidenza, rapporto salvato su file, riavvio.

**Internet**: stato della connessione e indirizzi pubblici, traffico in tempo reale, storico delle misure con media, massimo e minimo, registro delle cadute, collegamento in fibra, IPv6, filtro della pubblicità, ping, accesso da fuori casa.

**Rete locale**: i dispositivi collegati con indirizzo, segnale e modo di collegamento, il dettaglio di ciascuno, la rinomina, il risveglio di un computer spento, il DHCP con il suo intervallo e i suoi indirizzi fissi, le porte ethernet con le statistiche.

**Wi-Fi**: accensione, reti con nome, password e protezione, punti di accesso con canale e larghezza, dispositivi collegati con il segnale, scansione delle reti dei vicini, occupazione dei canali con il consiglio su quale scegliere, filtro degli indirizzi MAC, calendario, WPS.

**Sicurezza**: apertura delle porte verso internet, DMZ, porte occupate dai servizi, server VPN con utenti e collegamenti, controllo dei contenuti, destinatari delle notifiche.

**Disco e file**: dischi e spazio, un navigatore del disco della box che entra nelle cartelle, copia, sposta, cancella, rinomina, crea collegamenti condivisi e scarica sul computer, con i lavori lunghi seguiti da una riga di avanzamento.

**Servizi di casa**: condivisione Samba e AFP, server FTP, server multimediale UPnP AV, AirMedia, display sul fronte della box, gestore degli scaricamenti.

**Telefono**: registro delle chiamate con i filtri, linee e cornette DECT che si fanno squillare per ritrovarle, rubrica.

## Accessibilità

È il motivo per cui il programma esiste, quindi non è una sezione di cortesia.

Niente separatori grafici, niente righe vuote di servizio, niente tabelle disegnate con i trattini: le colonne sono spazi, così le dita ritrovano l'informazione sempre allo stesso posto. Le spiegazioni sono lunghe quanto serve, perché la console è larga e spezzare una frase la rende solo più faticosa da seguire.

I dati che cambiano mentre si guarda, cioè il traffico, le temperature e l'avanzamento di un lavoro, sono una riga sola entro quaranta caratteri, scritta fra due ritorni carrello: su un display braille a otto punti quaranta caratteri sono una lettura sola, e il ritorno carrello finale riporta il cursore all'inizio. Le lettere sono sempre le stesse e la legenda sta nel manuale.

I prompt che aspettano un tasto solo stanno fra due ritorni carrello; quelli che aspettano una riga scritta, no, perché lì il ritorno carrello confonde lo screen reader mentre si digita.

Ogni modifica viene chiesta due volte: prima il programma dice che cosa cambierà, poi aspetta Invio per confermare o Escape per annullare. Le modifiche che possono chiudere fuori chi le sta facendo, come spegnere il Wi-Fi mentre si è collegati in Wi-Fi, lo dicono prima.

## Che cosa serve

Python 3.10 o più recente e la libreria `requests`. Serve anche [GBUtils](https://github.com/GabrieleBattaglia/GBUtils), la libreria condivisa da cui vengono i menu, le domande e i formati: la sua cartella va messa nella `PYTHONPATH`.

Per il solo comando `storico`, e solo se si sceglie di ascoltare una serie di numeri invece di leggerla, servono anche `numpy` e `sounddevice`. Senza di loro tutto il resto funziona lo stesso.

## Come si comincia

```
git clone https://github.com/GabrieleBattaglia/iliadbox
cd iliadbox
pip install -r requirements.txt
python iliadbox.py
```

Al primo avvio il programma chiede alla box il permesso di comandarla. Sul display della Iliadbox compare una richiesta, e bisogna premere la freccia destra sul fianco della box entro due minuti. Si fa una volta sola: da quel momento il programma tiene un token in `config.json` e lo riusa a ogni avvio.

Se la box non è al solito indirizzo, si passa il suo:

```
python iliadbox.py --host 192.168.1.254
```

## Il token

Il token che la box consegna vale quanto una password: chi ce l'ha comanda il router. Vive in `config.json`, accanto al programma, e quel file è escluso da git: nel repository non c'è e non deve entrarci. Il programma non lo stampa mai, nemmeno dentro i rapporti.

Chi scarica il programma ne ottiene uno suo alla prima associazione con la propria box. Per ricominciare da capo basta cancellare `config.json`.

Il certificato della box è firmato da sé stessa, come in ogni apparecchio di rete locale, e non c'è modo di verificarlo: la verifica del certificato è quindi spenta, e il programma parla soltanto con l'indirizzo che gli si dice.

## Come si usa

Senza argomenti apre il menu e resta lì. Il prompt è `iliadbox>`: si digitano qualche lettera e l'elenco si filtra, Invio sceglie, Escape esce. `elenco` stampa tutti i comandi raggruppati per area, `aree` fa scegliere prima l'area, `cerca` trova un comando per parola, `aiuto` apre il manuale.

Con il nome di un comando lo esegue e torna alla shell, che è comodo dentro uno script o un collegamento sul desktop:

```
python iliadbox.py stato
python iliadbox.py diagnosi
python iliadbox.py --elenco
```

## Il pacchetto compilato

Dalla cartella del progetto:

```
pyinstaller --noconfirm iliadbox.spec
python zip_maker.py
```

Ne esce un file solo, `dist/iliadbox.exe`, che non ha bisogno né di Python né di GBUtils: si lancia com'è, e cerca `config.json` accanto a sé. Dentro ci sono il manuale e il changelog.

Dal pacchetto restano fuori numpy e sounddevice, e con loro la possibilità di ascoltare le serie di numeri del comando `storico`: metterli dentro porta l'eseguibile da 46 a 125 MB e l'avvio da 1,4 a 5,5 secondi, perché un pacchetto in file unico si scompatta a ogni lancio. Chi vuole la sonificazione lancia il programma dai sorgenti, dove funziona; chi la vuole anche compilata sposta le due righe da `excludes` a `hiddenimports` dentro `iliadbox.spec`.

## Prove

```
python -m pytest -q
```

Le prove non toccano la box: verificano i formati, il registro dei comandi e il cliente delle API contro risposte finte.

## Stato

Versione 1.0.0 del 16 settembre 2026, la prima pubblica. Il programma è nato nel dicembre 2025 come prototipo privato, con il nome "Iliad BryBox", e faceva il monitoraggio e poco altro. La cronologia è in [CHANGELOG.md](CHANGELOG.md).

Provato su una Iliadbox r1, modello ibxgw8-r1, firmware 4.9.18.2, che espone la versione 15 delle API. Le API sono quelle di FreeboxOS, [documentate su dev.freebox.fr](https://dev.freebox.fr/sdk/os/): un comando che chiede alla box qualcosa che quel modello non offre lo dice e tira dritto, quindi il programma dovrebbe funzionare anche sulle Freebox e sulle altre Iliadbox, con le differenze del caso.

## Licenza

Unlicense: il codice è rilasciato nel pubblico dominio, si veda il file [LICENSE](LICENSE).
