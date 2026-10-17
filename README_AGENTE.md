# Contesto del progetto per l'agente (leggi tutto prima di scrivere codice)

Questo file spiega all'agente di sviluppo (IDE agentico) cosa stiamo facendo, perché, con quali vincoli e come lavorare. Va letto per intero all'inizio di ogni sessione e riletto quando c'è un dubbio su priorità o regole.

Puoi rinominarlo come serve al tuo strumento (per esempio `README.md`, `AGENTS.md`, `.github/copilot-instructions.md`, `CLAUDE.md` o le regole del tuo IDE).

---

## 1. In sintesi

Stiamo partecipando all'hackathon **Inside the Game: Developer Hackathon**, organizzato da **Microsoft** insieme alla **Premier League**. Bisogna costruire una soluzione basata su intelligenza artificiale che trasformi **eventi di partita sintetici** (dati calcistici simulati, realistici ma non reali) in:

- intelligence di partita **spiegabile**;
- **narrazioni in tempo reale**;
- **riepiloghi automatici** delle partite;
- esperienze **personalizzate** e **multilingua** per tifosi, analisti e broadcaster.

**Obiettivo dichiarato: vincere e ottenere il massimo punteggio in tutti i criteri di giudizio, non in uno solo.** Ogni decisione tecnica va valutata anche con questa domanda: "questo aumenta il punteggio davanti ai giudici?"

## 2. Chi siamo

- **Sviluppatore principale:** lavora da solo ed è un "vibe coder", cioè sviluppa dialogando con l'agente. Significa che l'agente deve spiegare in modo semplice cosa fa, procedere a piccoli passi verificabili e non dare nulla per scontato.
- **Collaboratrice (solo parte visiva):** un'amica che potrebbe aiutare con grafica e aspetto dell'interfaccia. Se partecipa davvero, andrà indicata nel team con il suo ruolo reale.
- **Lingua di lavoro:** con lo sviluppatore si parla in **italiano**. Il codice, i commenti, i nomi di variabili, i messaggi di commit e la documentazione destinata ai giudici sono in **inglese**.

## 3. Scadenze (fuso orario del Pacifico, PT)

| Cosa | Data |
|---|---|
| Fine registrazioni | 20 ottobre 2026, ore 12:00 PT (lo sviluppatore è già registrato) |
| Periodo di sviluppo | 6 ottobre, ore 9:00 PT, fino al **27 ottobre 2026, ore 23:59 PT** |
| Periodo di giudizio | 27 ottobre fino al 10 novembre 2026 |
| Annuncio vincitori | entro il 20 novembre 2026 |

Note per l'agente:
- Oggi è il 17 ottobre 2026, quindi restano circa **10 giorni**.
- La scadenza del 27 ottobre alle 23:59 PT corrisponde a circa le **07:59 del 28 ottobre in Italia**. L'obiettivo interno è consegnare entro il **26 ottobre**, lasciando il 27 come margine di sicurezza.
- Il tempo è poco: preferisci sempre una versione **completa, funzionante e dimostrabile** a una ambiziosa ma incompleta.

## 4. La sfida ufficiale

Il progetto deve implementare una pipeline in **cinque fasi**:

1. **Acquisire (Ingest):** ricevere eventi di partita sintetici man mano che accadono (passaggi, tiri, contrasti, cambi di possesso, eventi di pressione, metadati della partita).
2. **Interpretare:** trasformarli in statistiche, schemi e contesto calcistico significativi.
3. **Spiegare:** dire *perché* un momento conta, non solo che è successo (per esempio controllo contro caos, cambi di pressione tattica, ritmo di gioco).
4. **Rappresentare (Render):** produrre qualcosa che possa stare accanto alla partita, per esempio overlay grafici sincronizzati, temporizzati e leggibili da una macchina (JSON).
5. **Personalizzare:** la stessa intelligenza deve produrre esperienze davvero diverse per un analista esperto e per un tifoso occasionale (modalità, squadra preferita, giocatore preferito, modalità focus su un giocatore, metrica singola, lingua).

Un progetto che produce solo metriche non ha pubblico; uno che personalizza soltanto non ha nulla da personalizzare. **Servono entrambe le cose.**

### Funzionalità suggerite dal bando (da considerare)

- **Identificazione dei giocatori:** nomi in tempo reale, con indicatori opzionali di velocità e distanza quando si superano soglie predefinite.
- **Qualità del passaggio:** distanza, precisione e valutazione di difficoltà.
- **Metriche di velocità:** velocità del pallone e del tiro.
- **Auto-eventing (opzionale e avanzato):** modello che genera le metriche da un flusso video invece di etichettarle a mano.
- **Narrazione:** narrazioni chiave, contesto sulle prestazioni dei giocatori, traguardi, riepiloghi.
- **Spiegabilità:** ritmo di gioco, pressione, controllo contro caos.
- **Innovazione sui dati:** creare o estendere dataset sintetici realistici.
- **Storytelling multilingua:** testi naturali in più lingue per studi e streaming globali.

Il progetto può essere un agente, un flusso di lavoro, un'integrazione, una piattaforma dati, un'esperienza di analisi, un'automazione o un'esperienza del tutto nuova.

## 5. Come verremo giudicati

**Fase 1 (idoneità, passa o non passa):** il progetto deve rispettare il tema e usare ragionevolmente le tecnologie richieste.

**Fase 2:** cinque criteri con **lo stesso peso (20% ciascuno)**.

| Criterio | Cosa cercano i giudici | Cosa deve fare l'agente |
|---|---|---|
| **Implementazione tecnologica (20%)** | Creatività e qualità dei dati sintetici; buone pratiche di sviluppo; uso efficace delle tecnologie chiave (Microsoft Foundry, Agent Framework, Azure MCP, GitHub Copilot Agent Mode, Fabric, servizi Azure AI, database Azure); codice ben strutturato, documentato e manutenibile | Codice pulito, modulare, tipizzato, con test, commenti utili e README chiaro; usare davvero Foundry e servizi Azure |
| **Design agentico e innovazione (20%)** | Uso creativo di pattern agentici; orchestrazione sofisticata, MCP, collaborazione multi-agente; IA innovativa | Più agenti con ruoli distinti, stato condiviso, passaggi di consegne, recupero dagli errori |
| **Impatto nel mondo reale (20%)** | Importanza del problema; possibilità di uso in produzione; impatto su sviluppatori, aziende, utenti | Pensare come un prodotto: affidabilità, osservabilità, sicurezza, scalabilità |
| **Esperienza utente e presentazione (20%)** | Interfaccia ben progettata e intuitiva; video che comunica il valore; equilibrio tra frontend e backend | Interfaccia curata (con la collaboratrice), demo fluida, video chiaro |
| **Aderenza alla categoria (20%)** | Il progetto rispetta la descrizione della categoria scelta | Scegliere le categorie target e soddisfarne i requisiti in modo esplicito |

I punteggi più alti si ottengono evitando punti deboli: **ogni criterio vale il 20%, quindi trascurarne uno costa molto.** In caso di parità si confrontano i criteri nell'ordine della tabella.

## 6. Categorie di premio

Ogni progetto può vincere **un solo premio principale** e **un solo premio di categoria**. I giudici possono riassegnare un progetto a una categoria più adatta.

| Premio | Cosa premia |
|---|---|
| **Primo e secondo posto (Grand Prize)** | Miglior soluzione complessiva, con impatto reale e uso innovativo della piattaforma Microsoft; deve mostrare come l'IA trasforma eventi e statistiche in narrazioni, contesto e esperienze personalizzate e accessibili |
| **Best Use of Microsoft Foundry** | Uso efficace di Microsoft Foundry per sviluppo, orchestrazione e gestione di soluzioni IA |
| **Best Enterprise Solution** | Prontezza per l'uso aziendale: affidabilità, trasparenza, controlli, percorso chiaro verso l'adozione |
| **Best Multi-Agent System** | Collaborazione multi-agente mirata (GitHub Copilot, Microsoft Agent Framework, A2A o altro): agenti con ruoli distinti, stato condiviso, passaggi efficaci, recupero dai guasti, risultato che un singolo agente non otterrebbe altrettanto bene |
| **Best Azure Cloud Native Integration** | Uso di servizi cloud native Azure (AKS, Container Apps, Functions, Logic Apps, piattaforme dati ottimizzate per IA), architetture a eventi, automazione, eccellenza operativa |

**Strategia:** puntiamo al premio principale e a **più categorie contemporaneamente**, quindi l'architettura deve essere multi-agente, costruita su Foundry, a eventi su servizi cloud native Azure e con caratteristiche da prodotto aziendale.

## 7. Requisiti obbligatori di consegna

La consegna avviene sul sito dell'hackathon (pagina "Projects"). Servono:

1. Un **progetto nuovo**, creato dopo il 29 settembre 2026. Non riutilizzare progetti precedenti.
2. Una **descrizione breve** (elevator pitch): cosa abbiamo costruito, quali tecnologie Microsoft e Azure usiamo, cosa fa, quale problema risolve.
3. Un **video dimostrativo di meno di 2 minuti** (i giudici non sono obbligati a guardare oltre), pubblico su YouTube, Vimeo, Facebook Video o Youku. Deve mostrare il progetto funzionante sulla piattaforma per cui è stato fatto. Niente musica con copyright né marchi di terzi senza permesso.
4. Un **repository GitHub pubblico** (se non è pubblico, la candidatura non viene considerata).
5. Un **link a una demo funzionante** o a una build di test, **gratuita e senza restrizioni** fino alla fine del periodo di giudizio. Se è privata, vanno inserite le credenziali nelle istruzioni di test.
6. Tutto il materiale **in inglese** (o con traduzione inglese).
7. Il progetto non deve aver già vinto altri concorsi.

I giudici non sono obbligati a provare il progetto e possono valutare solo da descrizione, immagini e video, quindi **video e descrizione devono bastare da soli a convincere.**

## 8. Regole che l'agente non deve mai violare

- **Solo dati sintetici.** Non usare dati reali, filmati o materiale della Premier League. Tutti i nomi di squadre e giocatori nei dati di esempio devono essere **inventati**.
- **Niente marchi o contenuti protetti** (loghi, immagini, musica, font o testi con diritti) senza permesso. Evitare di usare loghi della Premier League o di altri nell'interfaccia e nel video; Microsoft e Premier League possono essere citati solo come contesto dell'hackathon.
- **Originalità e licenze:** il codice deve essere nostro. Se si usano librerie open source, rispettarne la licenza e costruirci sopra qualcosa di nuovo. Se si usano API o dati di terzi, verificare di avere il diritto di usarli.
- **Nessun contenuto vietato:** osceno, offensivo, violento, diffamatorio, illegale, che promuova alcol, droghe, tabacco o un'agenda politica, o che possa danneggiare l'immagine di Microsoft.
- **Nessun segreto nel repository.** Chiavi, token e credenziali vanno solo in `.env` (escluso da Git) o in Azure Key Vault. Il repository è pubblico, quindi una chiave committata è una chiave persa. Controllare sempre prima di ogni commit.
- **Nessun dato personale** di persone reali nel progetto.
- **Il codice non deve contenere malware, bot o automazioni ingannevoli**, né tentare di alterare la piattaforma dell'hackathon.
- **Nessun supporto economico o preferenziale da Microsoft** per lo sviluppo del progetto.

Il progetto ha poi un obbligo di **funzionamento**: deve poter essere installato ed eseguito in modo coerente e comportarsi come mostrato nel video e descritto nel testo.

## 9. Architettura di riferimento (da adattare)

Questa è la direzione proposta per coprire tutti i criteri. L'agente deve proporre modifiche solo se migliorano il punteggio o riducono il rischio.

```
Generatore di partite sintetiche
        |
        v
Azure Event Hubs  -->  Azure Functions (elaborazione eventi)
                              |
                              v
                 Archivio stato e statistiche  +  Microsoft Fabric (analisi e storico)
                              |
                              v
        Agenti su Microsoft Foundry + Agent Framework
   Orchestratore -> Analista tattico -> Narratore -> Verificatore
                         -> Personalizzazione -> Localizzazione
                              |
                              v
              API su Azure Container Apps
                 |                       |
                 v                       v
       Interfaccia web             Feed JSON overlay
   (modalità analista e tifoso)   (per grafiche broadcast)
```

**Ruoli degli agenti:**

- **Orchestratore:** individua i momenti chiave, decide quali agenti chiamare, gestisce stato condiviso e tentativi.
- **Analista tattico:** spiega cambi di pressione, controllo contro caos, ritmo, usando le statistiche calcolate.
- **Narratore:** scrive le frasi di commento temporizzate e i riepiloghi.
- **Verificatore:** controlla ogni affermazione confrontandola con gli eventi; rifiuta ciò che i dati non supportano. Questo è fondamentale per spiegabilità e affidabilità.
- **Personalizzazione:** adatta profondità, tono e focus al profilo dello spettatore.
- **Localizzazione:** produce il testo nella lingua scelta, mantenendo nomi e numeri corretti.

**Gestione dei guasti:** se un agente va in timeout o il verificatore rifiuta l'output due volte, l'orchestratore ripiega su una narrazione a modello basata solo sui dati, così l'esperienza dal vivo non si interrompe mai.

**Principio guida:** ogni affermazione in una narrazione deve avere **evidenze collegate** (ID degli eventi che la giustificano).

## 10. Stack tecnologico

Tecnologie da usare davvero (i giudici le valutano):

- **Microsoft Foundry** (modelli, tracciamento, valutazione).
- **Microsoft Agent Framework**, A2A e/o MCP per l'orchestrazione.
- **Azure Event Hubs, Azure Functions, Azure Container Apps** per l'architettura a eventi.
- **Microsoft Fabric** e/o un database Azure per dati e analisi.
- **Application Insights / OpenTelemetry** per osservabilità.
- **GitHub, GitHub Actions** per repository e integrazione continua.
- **GitHub Copilot Agent Mode** nel flusso di sviluppo, dichiarato apertamente.
- Infrastruttura come codice (**Bicep** / Azure Developer CLI) per rendere il progetto riproducibile.

Scelte da confermare con lo sviluppatore prima di iniziare (non decidere da solo):

- linguaggio e framework del backend (suggerito: Python con FastAPI);
- framework del frontend (suggerito: React con TypeScript);
- elenco delle lingue supportate;
- nome definitivo del progetto.

## 11. Come deve lavorare l'agente

**Comunicazione**
- Rispondere in italiano, in modo semplice e diretto. Spiegare cosa si sta per fare, farlo, poi riassumere cosa è cambiato e come verificarlo.
- Dire sempre chiaramente cosa funziona, cosa è solo abbozzato e cosa manca. **Mai dichiarare completa una funzione non testata.**
- Se una richiesta è ambigua o comporta una scelta importante (architettura, costi Azure, dipendenze nuove), fare **una sola domanda mirata** e proporre un'opzione predefinita.

**Metodo**
- Procedere per **piccoli passi verticali**: ogni passo deve produrre qualcosa di eseguibile e verificabile.
- Prima di scrivere molto codice, assicurarsi che esista una **versione minima end to end** (dato sintetico, elaborazione, spiegazione, schermata). Poi migliorare.
- Scrivere o aggiornare **test** per la logica importante (generatore dati, statistiche, verificatore). Eseguirli prima di dichiarare un lavoro concluso.
- Fare **commit frequenti** con messaggi chiari in inglese (per esempio `feat: add pass difficulty metric`).
- Non fare refactoring estesi non richiesti. Non cancellare file senza dirlo.
- Non installare dipendenze pesanti o inutili: il progetto deve restare installabile da zero in pochi minuti.

**Qualità del codice (conta nei criteri)**
- Struttura modulare con responsabilità chiare, tipi espliciti, nomi comprensibili.
- Commenti e docstring brevi dove servono; documentazione aggiornata in `docs/`.
- Gestione degli errori, tentativi e timeout nelle chiamate ai servizi.
- Configurazione tramite variabili d'ambiente, con `.env.example` sempre aggiornato.
- Nessun codice morto, nessun `TODO` dimenticato nella versione consegnata.

**Sicurezza e costi**
- Mai inserire segreti nel codice o nei commit.
- Preferire identità gestite e privilegi minimi.
- Avvisare lo sviluppatore prima di creare risorse Azure che possano generare costi significativi.

## 12. Priorità quando il tempo stringe

In ordine, se bisogna tagliare qualcosa:

1. **Mai tagliare:** pipeline completa funzionante, dati sintetici, almeno due modalità di personalizzazione, almeno due lingue, verificatore, demo online, repository pubblico, video, descrizione.
2. **Da rifinire se c'è tempo:** osservabilità, test aggiuntivi, deploy automatizzato, interfaccia più ricca.
3. **Da tagliare per primo:** auto-eventing da video, funzioni opzionali non legate ai criteri, effetti grafici superflui.

## 13. Piano indicativo (da aggiornare con lo sviluppatore)

| Giorni | Obiettivo |
|---|---|
| 17 e 18 ottobre | Definire il concept e il nome; creare repository, struttura, `.env.example`; generatore di partite sintetiche con seed riproducibile |
| 19 e 20 ottobre | Ingestione degli eventi in streaming e calcolo delle statistiche (qualità dei passaggi, velocità, pressione, possesso) |
| 21 e 22 ottobre | Agenti: orchestratore, analista, narratore, verificatore con evidenze collegate; fallback senza IA |
| 23 ottobre | Personalizzazione (analista, tifoso, squadra e giocatore preferiti, focus giocatore) e multilingua; feed JSON per overlay |
| 24 ottobre | Interfaccia web (con la collaboratrice per la parte visiva) e collegamento all'API |
| 25 ottobre | Deploy su Azure, test completi, osservabilità, pulizia del codice, controllo segreti |
| 26 ottobre | Video sotto i 2 minuti, README per i giudici in inglese, descrizione, **consegna** |
| 27 ottobre | Margine di sicurezza e correzioni dell'ultimo minuto |

## 14. Definizione di "finito" (checklist prima della consegna)

- [ ] La pipeline in cinque fasi funziona end to end con una partita sintetica.
- [ ] Ogni narrazione ha evidenze collegate e passa dal verificatore.
- [ ] Almeno due modalità di visione molto diverse (analista e tifoso) e personalizzazione per squadra e giocatore.
- [ ] Almeno due lingue funzionanti.
- [ ] Feed JSON per overlay documentato.
- [ ] Architettura multi-agente con ruoli distinti, stato condiviso e recupero dagli errori.
- [ ] Foundry e servizi Azure usati davvero e descritti nel README.
- [ ] Test automatici che passano; integrazione continua attiva.
- [ ] Nessun segreto nel repository (controllare anche la cronologia Git).
- [ ] Il progetto si installa e parte da una macchina pulita seguendo il README.
- [ ] Demo online raggiungibile senza costi e senza restrizioni.
- [ ] Repository **pubblico**.
- [ ] README per i giudici **in inglese**, con collegamento a criteri e categorie.
- [ ] Video **sotto i 2 minuti**, pubblico, senza musica o marchi protetti.
- [ ] Descrizione breve in inglese con tecnologie usate, funzione e problema risolto.
- [ ] Team indicato correttamente.
- [ ] Consegna effettuata sul sito dell'hackathon **con almeno un giorno di margine**.

## 15. Risorse ufficiali

- Pagina dell'hackathon: https://aka.ms/insidethegame
- Regolamento ufficiale: https://aka.ms/insidethegame/rules
- Percorsi di formazione: https://aka.ms/aisn/hack
- Sessioni Microsoft Reactor: https://developer.microsoft.com/en-us/reactor/series/S-1709/
- Codice di condotta degli eventi Microsoft: https://www.microsoft.com/events/codeofconduct

In caso di dubbio o discrepanza, **fa fede il regolamento ufficiale**, non i materiali promozionali. Un'eventuale richiesta di chiarimento sul regolamento va fatta per iscritto prima della scadenza.

## 16. Da compilare dallo sviluppatore (l'agente deve chiedere se mancano)

- **Nome del progetto:** da definire
- **Idea di prodotto in una frase:** da definire
- **Linguaggi e framework scelti:** da definire
- **Lingue supportate:** da definire
- **Categorie su cui puntare:** tutte, con priorità al premio principale
- **Ruolo della collaboratrice:** da definire
- **Licenza del repository:** da definire
