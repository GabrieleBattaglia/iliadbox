# Cronologia di Iliadbox

## 1.0.0, 16 settembre 2026

Prima release pubblica. Il prototipo "Iliad BryBox", che viveva dentro la cartella Stuff e faceva il monitoraggio e poco altro, diventa un progetto a sé stante con il suo repository e la Unlicense.

- Cinquantotto comandi, divisi in otto aree piu' quelli del programma: sistema e diagnosi, internet, rete locale, Wi-Fi, sicurezza, disco e file, servizi di casa, telefono. Il prototipo ne aveva diciotto, e dodici si limitavano a elencare.
- Il codice si divide in moduli per area. `api.py` e' il cliente HTTP, `accesso.py` l'associazione e il login, `formati.py` il modo di scrivere le cose, e ogni area ha il suo modulo; `comandi.py` tiene il registro, dove aggiungere un comando vuol dire scrivere una riga.
- Gli errori del router non vengono piu' stampati dentro le funzioni che li incontrano: diventano `ErroreAPI` ed `ErroreRete`, con codice, messaggio e, quando c'e', il permesso mancante. Chi chiama riceve il risultato e basta.
- La sessione scaduta viene rifatta da sola: il router risponde `auth_required`, il cliente ripete il login e poi la chiamata, e chi sta lavorando non se ne accorge. Prima, dopo qualche minuto di pausa, ogni comando falliva.
- Nomi dei campi corretti sulla versione 15 delle API, dove non sono quelli della versione 4 su cui il prototipo era stato scritto: le temperature stanno in un elenco di sensori e non in `temp_cpub`, il modello sta in `model_info.pretty_name` e non in `mac_model_name`, e gli indirizzi di un dispositivo stanno in `l3connectivities` e non in `l3_connectivities`, che e' il motivo per cui l'elenco della rete mostrava tutti i dispositivi senza indirizzo.
- Il file di configurazione viene cercato accanto al programma e non nella cartella da cui lo si e' lanciato: prima, lanciandolo da un'altra parte, chiedeva di rifare l'associazione.
- Il token non viene mai stampato, `config.json` e' escluso da git, e i rapporti salvati su file portano un nome con la data e sono anche loro fuori dal repository, perche' dentro ci sono gli indirizzi e i nomi dei dispositivi di casa.
- Niente separatori grafici in nessuna schermata: il prototipo apriva ogni comando con una riga di trattini e chiudeva le intestazioni con tre trattini per lato.
- I dati in tempo reale, cioe' traffico, temperature e avanzamento dei lavori sul disco, sono una riga entro quaranta caratteri fra due ritorni carrello, con le lettere come codice; la legenda sta nel manuale. Le domande che aspettano una riga scritta restano invece prompt normali.
- Ogni modifica viene chiesta due volte e dice prima che cosa cambiera'. Quelle che possono chiudere fuori chi le sta facendo, come spegnere il Wi-Fi mentre si e' collegati in Wi-Fi o cambiare l'indirizzo del router, lo avvisano.
- `diagnosi` controlla in un colpo solo temperature, ventole, connessione, cadute recenti, Wi-Fi, protezione delle reti, segnale dei collegati, dischi, spazio libero, accesso da fuori casa, FTP anonimo, DMZ e DHCP, e ogni riga comincia con ok, avviso o guasto.
- `rapporto` scrive su file la stessa roba per esteso, con la data in testa: a schermo i dati stanno stretti, nel file no.
- `storico` legge le serie che il router conserva, traffico, temperature, porte ethernet e linea, da un'ora a un mese, e le puo' far ascoltare con `sonify` di GBUtils: un suono che sale e scende da sinistra a destra al posto di un grafico. I valori vengono riportati alla loro scala, perche' il router li moltiplica per la precisione richiesta.
- Il navigatore del disco entra nelle cartelle, crea, rinomina, copia, sposta, cancella, condivide e scarica sul computer. Le operazioni lunghe creano un compito sul router e vengono seguite con una riga che si riscrive; Escape smette di seguirle senza fermarle.
- Il Wi-Fi si governa per intero: accensione, nome e password delle reti, protezione, canale e larghezza dei punti di accesso, dispositivi collegati con il segnale, scansione dei vicini, occupazione dei canali con il consiglio su quale scegliere, filtro dei MAC, calendario e WPS.
- Il telefono: registro delle chiamate filtrabile, segnato come letto, svuotato; cornette DECT che si fanno squillare per ritrovarle, si registrano, cambiano suoneria e volume; rubrica da elencare, cercare, aggiungere e togliere.
- Il gestore degli scaricamenti aggiunge un indirizzo, mette in pausa, riprende, toglie e segue l'avanzamento. L'aggiunta passa da una funzione apposta del cliente, perche' e' l'unico punto delle API che non vuole il JSON ma i campi di una form.
- L'elenco dei dispositivi distingue la rete di casa da quella degli ospiti, e chiede quale guardare solo quando tutte e due sono abitate.
- Le porte ethernet si possono forzare a una velocita' e a un duplex, o rimettere in automatico, che e' cio' che serve quando un apparecchio vecchio non si mette d'accordo da solo con il router.
- La scansione delle reti vicine si puo' chiedere nuova invece di leggere quella di prima.
- Nel navigatore del disco: archivio zip di un file o di una cartella, estrazione di un archivio, e impronta md5 o sha1 di un file, per sapere se la copia sulla box e' identica all'originale.
- Negli scaricamenti: i feed RSS che la box sorveglia, da elencare, aggiungere, togliere e far rileggere, e il diario di un singolo scaricamento.
- Si puo' lanciare con il nome di un comando, e allora lo esegue e torna alla shell; `--host` dice dove sta la box, `--elenco` stampa i comandi, `--aiuto` ricorda l'uso.
- Manuale in italiano, aperto dal comando `aiuto`, con la legenda delle righe compatte e una sezione per ogni area.
- Prove con pytest che non toccano la box: formati, registro dei comandi e cliente delle API contro risposte finte.
- Si compila con PyInstaller in un file unico, `iliadbox.spec`, che porta dentro il manuale e il changelog; `zip_maker.py` ne fa l'archivio per la distribuzione. numpy e sounddevice restano fuori di proposito: dentro portano l'eseguibile da 46 a 125 MB e l'avvio da 1,4 a 5,5 secondi, e a rimetterci sarebbe ogni comando per il bene di una funzione sola.
- `banco_comandi.py` esegue tutti i comandi contro la box vera, con le funzioni che dialogano sostituite da risposte gia' pronte, e riferisce quali sono arrivati in fondo: e' l'altra meta' del collaudo, quella che pytest non puo' fare perche' non ha un router davanti.
- I percorsi seguono lo schema del parco software: un modulo `percorsi.py` nella radice che chiama `cartella_applicazione` e `percorso_risorsa` di GBUtils.

## 0.5.2, gennaio 2026, e le versioni prima

Il prototipo privato, dentro `Stuff/iliadbox`, con il nome "Iliad BryBox".

- Autenticazione con associazione fisica e login a sfida HMAC-SHA1, che sono rimasti tali e quali.
- Diciotto comandi: stato, connessione, LAN, Wi-Fi acceso e spento, riavvio, DHCP, dischi, chiamate, FTP, LCD, porte, VPN, controllo genitori, macchine virtuali, permessi, ricerca.
- La ricerca fra i comandi e il menu di GBUtils c'erano gia'.
