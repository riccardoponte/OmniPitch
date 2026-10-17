Add-Type -AssemblyName System.Speech

# English Voiceover (Microsoft David / Zira)
$synthEn = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voices = $synthEn.GetInstalledVoices()
foreach ($v in $voices) {
    if ($v.VoiceInfo.Culture.Name -like "en*" -or $v.VoiceInfo.Name -like "*David*") {
        $synthEn.SelectVoice($v.VoiceInfo.Name)
        break
    }
}
$synthEn.Rate = 0  # Normal speed
$synthEn.Volume = 100

$enText = @"
Welcome to OmniPitch: Personalized Synthetic Match Intelligence on Microsoft AI.
In this demonstration, we showcase how high-frequency synthetic football telemetry is transformed into real-time explainable tactical intelligence.
First, we initiate the live match stream. The acoustic whistle engine synthesizes the match kickoff.
On the interactive pitch radar, pass vectors, ball coordinates, and defensive compactness are tracked with sub-second precision.
With our tactical system switcher, match analysts can instantly shift formations from four three three to four two three one, dynamically recomputing player spatial responsibilities.
Switching from Analyst to Casual Fan persona, our Narrator agent immediately transforms complex tactical jargon into accessible, high-energy storytelling in four languages.
In the Pro Match Intelligence Center, the Attack Momentum graph visualizes minute-by-minute dominance and key match events.
Head-to-head comparative analytics display live expected goals, possession splits, and tackles won.
Algorithmic player ratings dynamically evaluate performance from zero to ten, automatically crowning the match MVP.
The penalty shot map charts spatial attempts scaled by expected goal values and shot speeds.
Finally, analysts can export complete match intelligence reports with a single click.
With an anti-hallucination Grounding Verifier and native Microsoft AI Foundry integration, OmniPitch is engineered for the Grand Prize.
Thank you!
"@

$outWavEn = "C:\Users\pontu\Desktop\Hackaton MSFT PPL\OmniPitch_Voiceover_EN.wav"
$synthEn.SetOutputToWaveFile($outWavEn)
$synthEn.Speak($enText)
$synthEn.Dispose()
Write-Host "English Voiceover created: $outWavEn"

# Italian Voiceover (Microsoft Elsa)
$synthIt = New-Object System.Speech.Synthesis.SpeechSynthesizer
foreach ($v in $voices) {
    if ($v.VoiceInfo.Culture.Name -like "it*" -or $v.VoiceInfo.Name -like "*Elsa*") {
        $synthIt.SelectVoice($v.VoiceInfo.Name)
        break
    }
}
$synthIt.Rate = 0
$synthIt.Volume = 100

$itText = @"
Benvenuti su OmniPitch: intelligenza sintetica personalizzata per il calcio, basata su Microsoft AI.
In questa dimostrazione presentiamo come i dati di telemetria calcistica sintetica vengono trasformati in tempo reale in analisi tattiche spiegabili e telecronache personalizzate.
Avviamo lo streaming della partita: il motore acustico Web Audio sintetizza il fischio d'inizio arbitrale.
Sul radar tattico interattivo, vettori di passaggio, coordinate e densità difensiva sono calcolati istantaneamente.
Con il selettore tattico possiamo cambiare formazione al volo, passando dal quattro tre tre al quattro due tre uno, ricalcolando le posizioni dei calciatori.
Cambiando la persona da Analista a Tifoso, l'agente Narratore adatta immediatamente il linguaggio in quattro lingue diverse, rendendolo coinvolgente e privo di tecnicismi ostici.
Nel Pro Match Intelligence Center, il grafico Attack Momentum illustra l'inerzia offensiva minuto per minuto.
Le statistiche comparate mostrano expected goals, possesso palla e contrasti vinti.
I voti prestazionali da zero a dieci premiano automaticamente il miglior giocatore della partita con il badge MVP.
La mappa dei tiri evidenzia le conclusioni scalate per pericolosità e velocità in chilometri orari.
Infine, con un clic, l'analista può esportare il report completo della partita in formato JSON.
Grazie al Grounding Verifier anti-allucinazione e all'ecosistema Microsoft AI, OmniPitch è pronta per vincere il concorso.
Grazie per l'attenzione!
"@

$outWavIt = "C:\Users\pontu\Desktop\Hackaton MSFT PPL\OmniPitch_Voiceover_IT.wav"
$synthIt.SetOutputToWaveFile($outWavIt)
$synthIt.Speak($itText)
$synthIt.Dispose()
Write-Host "Italian Voiceover created: $outWavIt"
