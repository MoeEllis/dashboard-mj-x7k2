# Dashboard-Automatik: Einrichtung (einmalig, ca. 10 Minuten)

Danach aktualisiert sich dein Dashboard **alle 30 Minuten von selbst** aus
Todoist und Google Kalender – plus **⟳-Knopf** für sofortige Aktualisierung.
Claude brauchst du nur noch für Design-Änderungen.

---

## Schritt 1: Die drei Dateien ins Repository bringen

**a) `build_dashboard.py`** (das Bau-Skript) und **`italian_course.py`**
(der Lernstoff des Italienisch-Kurses – eine reine Datendatei, liegt direkt
neben dem Bau-Skript im Hauptordner des Repos)

1. Repo `dashboard-mj-x7k2` auf github.com öffnen
2. **Add file → Upload files** → `build_dashboard.py` und `italian_course.py` aus diesem Paket hineinziehen
3. **Commit directly to the main branch** → **Commit changes**

**b) `.github/workflows/update.yml`** (der Zeitplan)

1. **Add file → Create new file**
2. Als Dateinamen exakt eintippen: `.github/workflows/update.yml`
   (die Schrägstriche erzeugen automatisch die Ordner)
3. Den kompletten Inhalt der Datei `update.yml` aus diesem Paket hineinkopieren
4. **Commit changes** (direkt auf main)

## Schritt 2: Die Zugangsdaten als Secrets hinterlegen

Im Repo: **Settings → Secrets and variables → Actions → New repository secret**.
Secrets anlegen (Name exakt so schreiben) – die ersten drei sind Pflicht, der Rest optional:

| Name | Wert | Wo finde ich das? |
|---|---|---|
| `DASH_PASSWORD` | `Orbit-Falke-10%` | Dein Dashboard-Passwort (unverändert) |
| `TODOIST_TOKEN` | dein API-Token | Todoist → Einstellungen → **Integrationen** → Reiter **Entwickler** → API-Token kopieren |
| `ICS_URL` | private iCal-Adresse (dein Hauptkalender) | Google Kalender im Browser → Zahnrad → **Einstellungen** → links unter „Einstellungen für meine Kalender" deinen Kalender anklicken → Abschnitt **„Kalender integrieren"** → **„Privatadresse im iCal-Format"** kopieren |
| `ICS_URLS` | *(optional)* weitere iCal-Adressen, je eine pro Zeile (oder durch Komma getrennt) | Für zusätzliche Kalender wie „Privat" oder „Feiertage in Deutschland" – siehe „Mehrere Kalender" unten |
| `HOLIDAY_EXCLUDE` | *(optional)* Termin-/Feiertagsnamen, je einer pro Zeile (oder durch Komma getrennt) | Um bestimmte Termine (z. B. für dich irrelevante regionale Feiertage) dauerhaft auszublenden – siehe „Feiertage/Termine ausblenden" unten |
| `REFRESH_TOKEN` | *(optional)* Feintoken | Für den ⟳-Knopf, das Abhaken der Aufgaben und den Geräte-Abgleich des Italienisch-Fortschritts, siehe unten |
| `WORKER_URL` | *(optional)* Adresse deines Übersetzen-Workers | Ausgabe von `wrangler deploy` im Ordner `translate-worker/` – siehe „Übersetzen" weiter unten |
| `WORKER_TOKEN` | *(optional)* selbst ausgedachtes Zufalls-Token | Muss mit dem Wert übereinstimmen, den du dem Worker per `wrangler secret put WORKER_TOKEN` gegeben hast |
| `TRELLO_KEY` | *(optional)* dein Trello-API-Key | [trello.com/app-key](https://trello.com/app-key) (eingeloggt öffnen) → oben den **Key** kopieren |
| `TRELLO_TOKEN` | *(optional)* dein Trello-Token | Auf derselben Seite unten auf **„Token"** klicken → Zugriff erlauben → den angezeigten Token kopieren |
| `ANTHROPIC_API_KEY` | *(optional)* dein Claude-API-Key | [console.anthropic.com](https://console.anthropic.com/) → **Get API Keys** → neuen Key erstellen (eigenes, separates Konto mit Guthaben – siehe unten) |
| `INDUSTRY_FEEDS` | *(optional)* eigene Branchenquellen, je Zeile `Name \| Feed-Adresse` | Ersetzt die eingebaute Quellenliste komplett – siehe „Reiter Markt → Branche" unten |
| `INDUSTRY_KEYWORDS` | *(optional)* Filterwörter für die Branchenquellen, eine pro Zeile oder per Komma | Ersetzt die eingebaute Wortliste (Lizenz, Hobby, Bundesliga, Panini, Topps …) |
| `OWN_BRANDS` | *(optional)* eigene Marken, eine pro Zeile oder per Komma | Vorgabe: `Panini`. Bestimmt, was als „eigen" statt „Wettbewerb" gilt |
| `WATCH_LEAGUES` | *(optional)* beobachtete Ligen/Lizenzen, eine pro Zeile oder per Komma | Vorgabe: `Bundesliga`, `Champions League`, `FIFA / WM`, `Premier League` |
| `PODCAST_MODEL` | *(optional)* Modellname für alle KI-Kacheln | Vorgabe: `claude-haiku-4-5-20251001` (das günstigste Modell). Nur ändern, wenn du bewusst ein anderes willst |

**Zum optionalen `REFRESH_TOKEN`:** Ohne dieses Secret funktioniert alles –
der ⟳-Knopf öffnet dann die GitHub-Actions-Seite, wo du mit zwei Klicks
(„Run workflow") aktualisierst. Mit dem Secret stößt der Knopf die
Aktualisierung direkt aus der Seite an. Dafür: GitHub → Settings →
Developer settings → Fine-grained tokens → neues Token, **nur** Repo
`dashboard-mj-x7k2`, **einzige** Berechtigung: „Actions: Read and write".
Hinweis: Dieses Token wird in die *verschlüsselte* Seite eingebettet –
lesbar nur für jemanden, der dein Dashboard-Passwort kennt, und selbst dann
kann man damit ausschließlich die Aktualisierung anstoßen.
Dasselbe Token trägt inzwischen zwei weitere Bequemlichkeiten: das **Abhaken
der Aufgaben** (Eingabe `close_tasks`) und den **Geräte-Abgleich des
Italienisch-Fortschritts** (Eingabe `it_progress`). Beide laufen über denselben
Workflow-Anstoß, brauchen deshalb kein zusätzliches Secret – ohne
`REFRESH_TOKEN` bleiben beide einfach lokal auf dem jeweiligen Gerät.

**Zu `TRELLO_KEY`/`TRELLO_TOKEN`:** Ohne diese beiden Secrets baut sich das
Dashboard trotzdem ganz normal – im Trello-Bereich erscheint dann nur ein
Hinweis, dass die Anbindung noch fehlt. Sind beide hinterlegt, zeigt das
Dashboard automatisch alle deine offenen Trello-Boards (das automatisch
angelegte „Welcome Board" wird ausgeblendet) mit ihren Listen – aber nur
Listen, die auch tatsächlich Karten enthalten, damit es übersichtlich bleibt.

## Schritt 3: Ersten Lauf starten und prüfen

1. Im Repo auf den Reiter **Actions** → links „Dashboard aktualisieren"
   → rechts **Run workflow** → **Run workflow**
2. Nach ca. 1 Minute sollte der Lauf einen grünen Haken haben
3. `https://moeellis.github.io/dashboard-mj-x7k2/` neu laden (ggf. Strg+F5) –
   fertig: Ab jetzt läuft alles von selbst.

---

## Wichtig zu wissen

- **Todoist-Struktur:** Das Skript erwartet Hauptprojekte mit den Namen
  **Privat**, **Arbeit**, **Studium** (Groß-/Kleinschreibung egal).
  Unterprojekte darunter (Fächer, Arbeitsprojekte …) sind beliebig und
  erscheinen als graue Zusatzzeile bei der Aufgabe. Priorität 1 (rot) in
  Todoist wird als „hoch" markiert.
- **Aufgaben: Beschreibung aufklappen.** Hat eine Aufgabe in Todoist eine
  Beschreibung (das Notizfeld unter dem Titel), erscheint hinter dem Titel ein
  kleiner Pfeil. Ein Klick darauf klappt die Beschreibung auf, ein zweiter
  wieder zu – dadurch bleibt die Liste so kurz wie vorher. Zeilenumbrüche
  bleiben erhalten, Internetadressen darin werden zu klickbaren Links.
  Aufgaben ohne Beschreibung bekommen keinen Pfeil.
- **Aufgaben abhaken.** Das Kästchen links neben der Aufgabe ist jetzt ein
  echter Knopf. Ein Klick streicht die Aufgabe durch, setzt ein grünes Häkchen,
  zählt den Zähler „x offen" herunter – und schließt die Aufgabe **wirklich in
  Todoist ab**. Der Weg dorthin: der Browser darf die Todoist-API nicht direkt
  ansprechen, und der `TODOIST_TOKEN` soll die Seite ohnehin nie erreichen.
  Stattdessen stößt der Klick denselben Workflow an wie der ⟳-Knopf, nur mit
  der Zusatzangabe `close_tasks`; das Abschließen passiert dann serverseitig im
  Lauf. Deshalb dauert es rund eineinhalb Minuten, bis die Aufgabe ganz
  verschwindet – das Häkchen ist aber sofort sichtbar. **Ein neues Secret ist
  nicht nötig**, es genügt der schon vorhandene `REFRESH_TOKEN`. Nochmal
  klicken nimmt das Häkchen zurück, solange der Lauf noch nicht durch ist.
  Klappt die Übertragung nicht (kein Netz, abgebrochener Lauf), bleibt das
  Häkchen gesetzt und wird beim nächsten Laden der Seite automatisch erneut
  versucht – höchstens dreimal, damit daraus keine Endlosschleife wird. Eine
  Zeile unter den drei Aufgabenkarten sagt jeweils, was gerade passiert.
  Zwei Grenzen: Die Kachel **„Heute erledigt"** kommt direkt aus Todoist und
  zieht erst beim nächsten Lauf nach. Und die Kästchen an den **Trello-Karten**
  sind weiterhin nur Deko – Trello-Karten lassen sich im Dashboard noch nicht
  abhaken.
- **Mehrere Kalender (z. B. „Privat", „Feiertage in Deutschland"):** Standardmäßig
  wird nur der eine in `ICS_URL` hinterlegte Kalender geladen. Um weitere
  Kalender zusätzlich anzuzeigen, für jeden gewünschten weiteren Kalender in
  Google Kalender → Einstellungen → den jeweiligen Kalender anklicken →
  „Kalender integrieren" die passende iCal-Adresse kopieren (bei eigenen,
  privaten Kalendern die „Privatadresse im iCal-Format"; bei abonnierten
  öffentlichen Kalendern wie „Feiertage in Deutschland" die „Öffentliche
  Adresse im iCal-Format"). Alle diese zusätzlichen Adressen kommen zusammen
  in das Secret `ICS_URLS` – eine pro Zeile (oder durch Komma getrennt). Das
  Dashboard führt dann alle Kalender zu einer gemeinsamen Terminliste zusammen.
  Ist eine der Adressen mal kurzzeitig nicht erreichbar, fällt nur dieser eine
  Kalender für den Lauf aus (Hinweis im Actions-Log), die übrigen werden
  trotzdem geladen. Adressen, die mit `webcal://` beginnen (typisch bei
  abonnierten Apple/iCloud-Kalendern), werden automatisch erkannt und
  funktionieren genauso wie `https://`-Adressen – keine manuelle Anpassung nötig.
- **Sicherheit:** Alle Zugangsdaten liegen ausschließlich in GitHubs
  Secrets-Tresor (für niemanden einsehbar, auch nicht im öffentlichen Repo).
  Veröffentlicht wird immer nur die verschlüsselte Seite.
- **E-Mail-Kachel:** Der Gmail-Überblick ist in der Automatik nicht mehr
  enthalten (Gmail bietet dafür keinen einfachen sicheren Zugang außerhalb
  von Claude). Termine + Aufgaben sind vollständig da.
- **Trello:** Erscheint auf der Startseite als eigener Bereich, gruppiert nach
  Board und Liste. Offene Karten stehen mit einem Kästchen-Symbol da (wie bei
  den Todoist-Aufgaben); Karten mit überschrittenem Fälligkeitsdatum bekommen
  ein rotes „überfällig"-Label. Leere Listen werden ausgeblendet.
- **Podcast „Das Hobby":** Eigener Reiter oben, durchwischbar (oder mit den
  Pfeilen) durch die Takeaways jeder Folge. Es werden nur Folgen berücksichtigt,
  für die der Podcast selbst ein Transkript veröffentlicht (aktuell ungefähr
  seit Frühjahr 2026) – ältere Folgen ohne Transkript tauchen nicht auf. Die
  Takeaways werden per Claude API zu kurzen, eigenständig formulierten
  Stichpunkten zusammengefasst (nicht nur Satzausschnitte). Jede Folge wird
  nur **einmal** verarbeitet und danach dauerhaft zwischengespeichert
  (`cache/podcast.json`); ein neuer automatischer Lauf verarbeitet nur neu
  erschienene Folgen. Der anfängliche Rückstand an vorhandenen Folgen mit
  Transkript baut sich über mehrere automatische Läufe ab (max. 12 neue
  Folgen pro Lauf), nicht alles auf einmal. Ohne `ANTHROPIC_API_KEY`
  erscheint hier nur ein Hinweis, dass das Secret noch fehlt.

  **Zu den Kosten:** Das `ANTHROPIC_API_KEY`-Secret gehört zu einem eigenen,
  separaten Konto auf [console.anthropic.com](https://console.anthropic.com/)
  (nicht dasselbe wie ein eventuelles Claude.ai/Pro-Abo) – dort lädst du
  einmalig Guthaben auf, danach wird nur pro tatsächlich genutztem Token
  abgerechnet, keine Abo-/Grundgebühr. Mit dem günstigsten Modell (Haiku)
  kostet die Zusammenfassung einer Folge geschätzt **0,5–1 Cent**; bei ca.
  2–3 neuen Folgen pro Woche macht das laufend etwa **5–15 Cent im Monat**.
  Der einmalige Rückstand an bereits bestehenden Folgen mit Transkript
  (ca. 20–40 Folgen) kostet einmalig geschätzt **20–40 Cent**, danach nie
  wieder, da jede Folge dauerhaft zwischengespeichert wird.
- **Fokus-Kachel (KI):** Oben auf der Startseite fasst Claude einmal **pro
  Kalendertag** (nicht bei jedem Dashboard-Lauf) Termine, fällige Aufgaben,
  überfällige Trello-Karten und die nächste Cardshow in Deutschland zu 3–5
  knappen Sätzen zusammen. Kosten: geschätzt **unter 0,5 Cent pro Tag**
  (~10–15 Cent im Monat), da nur einmal täglich ein kurzer Aufruf passiert,
  egal wie oft der ⟳-Knopf gedrückt wird. Ohne `ANTHROPIC_API_KEY` erscheint
  hier nur ein Hinweis, dass das Secret noch fehlt.
- **News-Kurzfassung (KI):** Im News-Reiter fasst Claude einmal pro Tag je
  Kategorie (⚽ Sport = kicker + LigaInsider, 📰 Weitere Themen = ZDFheute)
  die Schlagzeilen zu 3–4 Kernpunkten zusammen – die gewohnte Rohliste
  bleibt unverändert darunter erhalten und aktualisiert sich weiterhin bei
  jedem Lauf. Kosten: geschätzt **unter 0,5 Cent pro Tag** (2 kurze Aufrufe
  täglich, nur Schlagzeilen als Eingabe, kein Volltext).
- **Wetter (Stuttgart):** 7-Tage-Vorschau über die kostenlose, öffentliche
  Open-Meteo-API – **kein Secret, keine Kosten**, da keine Claude-API
  beteiligt ist.
- **Countdowns:** Drei Kacheln mit live tickender Zeit bis zum nächsten
  Termin, zur nächsten fälligen Aufgabe und zur nächsten Cardshow in
  Deutschland – reine Berechnung aus den ohnehin geladenen Daten, **keine
  zusätzlichen Kosten**.
- **Kalender-Farben:** Jeder Kalender (Standard aus `ICS_URL`, plus alle
  weiteren aus `ICS_URLS`) bekommt automatisch eine eigene feste Farbe –
  sichtbar als kleiner Punkt vor jedem Termin (Übersicht, Terminliste) bzw.
  als eingefärbte Kachel (Woche, Monat). Die Zuordnung Kalender → Farbe
  bleibt stabil, auch wenn später ein weiterer Kalender dazukommt oder
  einer kurzzeitig nicht erreichbar ist.
- **Reiter „Kalender":** Fasst Woche, Monat und Terminliste (früher „Jahr")
  als Unterreiter zusammen. Oben in diesem Reiter steht eine Kalender-Filterzeile
  mit einer Checkbox je verknüpftem Kalender (Farbe + Name) – jeder Kalender
  lässt sich einzeln ein-/ausblenden, die Auswahl gilt gemeinsam für Woche,
  Monat und Terminliste und bleibt beim Wechseln zwischen den Unterreitern
  erhalten. So bleibt die Übersicht auch mit vielen Kalendern übersichtlich.
- **Reiter „Markt":** Ersetzt den früheren Reiter „Releases" und fasst zwei
  Unterreiter zusammen: **Releases** und **Branche**. Die Auswahl
  des Unterreiters ist unabhängig von der im Reiter „Kalender".
- **Markt → Releases (aufgeräumt, mit Wettbewerbs-Einordnung):** Im Vordergrund
  steht wieder die schlichte Release-Liste. Darüber steht **eine** kurze
  Textzeile mit den nächsten 90 Tagen (Anzahl insgesamt, davon eigen bzw.
  Wettbewerb, Treffer in beobachteten Ligen) statt der früheren drei
  Kennzahlen-Karten. Die Liste **„Wettbewerb in beobachteten Ligen"** steckt
  jetzt in einem zugeklappten Abschnitt – ein Klick öffnet sie. Sichtbar sind
  nur die zwei wichtigsten Filterzeilen (**Sicht** und **Monat**); Konfiguration,
  Liga/Lizenz, Hersteller und Kategorie liegen hinter „Weitere Filter".
  Jede Zeile bleibt eingeordnet, aber ruhiger: eigene Releases haben einen
  blauen Rand links, **Hobby** trägt eine dezente Pille, Retail/Sticker stehen
  als graue Kleinschrift daneben, bei nicht erkennbarer Konfiguration steht
  nichts mehr (früher `?`), und die doppelte Kategorie-Angabe ist entfallen.
  Die Liga/Lizenz bleibt anklickbar und filtert direkt.
  **Keine KI, keine Kosten** – reine Auswertung der ohnehin geladenen Daten.
- **Markt → Branche (Branchen- und Lizenz-Radar):** Sammelt Meldungen aus vier
  Branchenquellen (Cardlines, Cardboard Connection, Google-News-Suche
  international und Google-News-Suche DE) und filtert sie auf die
  für dich relevanten Stichwörter (Lizenz, Rechte, Hobby, Bundesliga, Panini,
  Topps, Fanatics, Grading …). Oben fasst Claude einmal **pro Kalendertag**
  die wichtigsten 5 Punkte zusammen – jeweils mit einer Zeile dazu, was das
  konkret für Panini bedeutet. **Jede Zeile der Kurzfassung ist verlinkt:**
  die Überschrift führt direkt zur Meldung, auf die sie sich stützt, und
  stützt sie sich auf mehrere, stehen die weiteren als kleine Verweise
  darunter. Darunter je Quelle eine Kachel mit der
  ungefilterten Rohliste („2 von 12" = 2 relevante von 12 geladenen
  Meldungen), die sich bei jedem Lauf aktualisiert. Ist eine Quelle mal nicht
  erreichbar, steht das an der jeweiligen Kachel und die übrigen laufen
  weiter. Kosten: geschätzt **unter 0,5 Cent pro Tag**, da nur ein kurzer
  Aufruf täglich (Zwischenspeicher `cache/industry.json`), egal wie oft der
  ⟳-Knopf gedrückt wird. Ohne `ANTHROPIC_API_KEY` bleibt die Rohliste
  vollständig nutzbar, nur die Kurzfassung fehlt.
- **Italiano (Italienisch-Kurs):** Ein eigener Reiter mit vier Unterreitern.
  **Heute** ist die Startseite: Tagesziel, Serie, fällige Karteikarten und der
  „Satz des Tages". **Kurs** zeigt alle 48 Lektionen in 4 Blöcken à 12
  (Fundament → Alltag → Business-Grundlagen → Feinschliff); jede Lektion ist
  eine Portion von 15–20 Minuten, jede 12. Lektion ein **Meilenstein**, der den
  Block abfragt. **Vokabeln** ist der Karteikasten. **Übersetzen** ist der
  freie Übersetzer, siehe eigener Abschnitt weiter unten. Eine Lektion läuft in fünf
  Schritten ab (Wörter → Sätze → Grammatik → Quiz → Sprechen) und öffnet sich
  als Overlay, damit die Seite ruhig bleibt; mit `Esc` jederzeit zu.
  Das **Tagesziel** gilt als erfüllt, sobald entweder eine Lektion
  abgeschlossen **oder** alle fälligen Karten wiederholt sind. Die **Serie**
  bricht erst am Tag *nach* einem verpassten Tag – ein Tag Pause kostet also
  nichts, solange am Folgetag gelernt wird. Der **Karteikasten** arbeitet nach
  Leitner mit den Abständen 1/2/4/8/16/35 Tage: was sitzt, kommt seltener,
  der Tagesaufwand sinkt also mit der Zeit von selbst. Die **Aussprache**
  kommt über die Stimme deines Geräts (Web Speech, `it-IT`) – auf Lautsprecher
  tippen, kein Download, keine externe Seite. Auf **Übersicht** steht oben eine
  kleine Anstoß-Kachel mit dem heutigen Stand.
  Wichtig: Der Kurs ist **komplett KI-frei** – Lernstoff, Quiz und Karteikasten
  laufen im Browser. Er **kostet also nichts**, braucht **kein neues Secret**
  und funktioniert auch ohne `ANTHROPIC_API_KEY`. Der Lernstoff liegt in der
  Datei `italian_course.py`; sie lässt sich erweitern, ohne das Bau-Skript
  anzufassen, und ist so abgesichert, dass ein Fehler darin das Dashboard nicht
  lahmlegt (der Reiter bleibt dann nur leer).
  **Fortschritt auf allen Geräten:** Der Stand liegt weiterhin im Speicher des
  Browsers (`localStorage`) – das hält den Kurs schnell und offline nutzbar –,
  wird zusätzlich aber in der Datei `cache/italiano.json` im Repo geführt.
  Ablauf: Nach einer Änderung (Lektion fertig, Karte bewertet, Richtung
  umgestellt) stößt die Seite denselben Workflow an wie der ⟳-Knopf und
  übergibt ihren Stand als Eingabe `it_progress`; der Lauf führt beide Stände
  zusammen und backt das Ergebnis in die neue Seite. Dafür genügt der schon
  vorhandene `REFRESH_TOKEN` – **kein neues Secret, keine neue Fremd-API,
  weiterhin KI-frei**. Zusammengeführt wird *vereinigt*, nicht überschrieben:
  Erledigte Lektionen beider Geräte bleiben erhalten, bei einer Karteikarte
  gewinnt das höhere Leitner-Fach (Gelerntes fällt also nie zurück), bei der
  Serie der spätere Tag, beim Bestwert der höhere. Wer also am Rechner und am
  Handy unabhängig lernt, verliert nichts.
  Zwei Dinge dazu im Kopf behalten: Ein anderes Gerät sieht den neuen Stand
  erst, **nachdem es die Seite neu geladen hat** (⟳-Knopf oder der nächste
  halbstündige Lauf) – es ist ein Abgleich, keine Live-Verbindung. Und
  `cache/italiano.json` liegt – wie die übrigen Dateien in `cache/` – **im
  Klartext** im Repo, anders als die verschlüsselte `index.html`. Für den
  Kursfortschritt selbst (Lektionsnummern, Leitner-Fächer, Fälligkeiten,
  Serienzähler) sind das nur Zahlen und Datumsangaben, kein freier Text.
  Seit dem Übersetzer (siehe unten) kommen aber zwei Stellen mit **frei
  getipptem bzw. übersetztem Text** dazu: der Übersetzungsverlauf (die letzten
  20 Einträge) und selbst angelegte Karteikarten. Wer nur Alltags- und
  Business-Sätze zum Italienischlernen übersetzt, ist das unkritisch – für
  irgendetwas Vertrauliches ist der Übersetzer ohnehin nicht gedacht (siehe
  unten). Wer auch das nicht öffentlich im Repo stehen haben will, sagt
  Bescheid – die Datei lässt sich genauso verschlüsseln wie die Seite.

  **Übersetzen:** Freier Übersetzer für Wörter, Sätze oder ganze Texte, in
  beide Richtungen. Übersetzt wird von Claude – aber der API-Schlüssel selbst
  darf nirgends in dieser Seite stehen, denn `index.html` ist verschlüsselt,
  liegt aber öffentlich auf GitHub Pages und wäre damit dauerhaft
  offline-angreifbar. Deshalb sitzt dazwischen ein eigener, winziger
  Cloudflare-Worker (Ordner `translate-worker/` in diesem Paket): Er hält den
  `ANTHROPIC_API_KEY` als eigenes Cloudflare-Secret, prüft ein separates,
  enges Freigabe-Token und gibt nur die fertige Übersetzung zurück. Ohne
  diesen Worker bleibt der Reiter da, meldet aber nur „noch nicht
  eingerichtet" – der Rest des Dashboards ist davon unberührt.
  Einrichtung (einmalig, per Claude Code auf deinem Rechner, siehe
  `translate-worker/wrangler.toml`):
  1. Kostenloses Konto auf [cloudflare.com](https://cloudflare.com) anlegen (falls noch nicht vorhanden).
  2. Im Ordner `translate-worker/`: `npx wrangler login`, dann `npx wrangler deploy`.
  3. `npx wrangler secret put ANTHROPIC_API_KEY` (derselbe Schlüssel wie oben bei `ANTHROPIC_API_KEY`, eigenes Konto mit Guthaben).
  4. `npx wrangler secret put WORKER_TOKEN` – ein selbst ausgedachtes, langes Zufalls-Token (z. B. per Passwortgenerator).
  5. In den GitHub-Repo-Secrets zwei neue Einträge anlegen: `WORKER_URL` (die Adresse, die `wrangler deploy` ausgibt, z. B. `https://dashboard-mj-translate.<konto>.workers.dev`) und `WORKER_TOKEN` (derselbe Wert wie in Schritt 4).
  6. Optional, aber empfohlen: `npx wrangler kv namespace create TRANS_LIMIT`, die zurückgegebene `id` in `wrangler.toml` eintragen, den `[[kv_namespaces]]`-Block einkommentieren, erneut `npx wrangler deploy`. Das begrenzt den Worker auf 250 Übersetzungen/Tag – unabhängig von allem anderen ein zusätzlicher Kostendeckel.
  Kosten: Cloudflare Workers ist im kostenlosen Tarif (100.000 Aufrufe/Tag)
  mehr als ausreichend für den persönlichen Gebrauch. Für Claude wird das
  günstigste Modell (Haiku) mit knapper Antwortlänge verwendet; die genauen
  aktuellen Preise pro Million Tokens findest du unter
  [docs.claude.com](https://docs.claude.com/en/docs/about-claude/pricing) bzw. deinen tatsächlichen Verbrauch im
  [Anthropic Console](https://console.anthropic.com/) unter „Usage" – bei normaler
  Alltagsnutzung ist mit Bruchteilen eines Cents pro Tag zu rechnen, die
  Tagesbremse aus Schritt 6 deckelt das Worst-Case-Szenario zusätzlich.
  **Bevor überhaupt übersetzt wird**, schaut die Seite kurz nach, ob genau das
  Eingegebene schon eine deiner 480 Kursvokabeln oder 240 Kurssätze ist, und
  zeigt das zusätzlich an („Kennst du schon aus deinem Kurs") – das ist reine
  Bequemlichkeit und schränkt den Übersetzer selbst nicht ein, er bleibt
  uneingeschränkt für beliebigen Text nutzbar.
  Über „★ Als Karteikarte übernehmen" wandert eine Übersetzung direkt in den
  Leitner-Karteikasten und wird dort mitgelernt wie jede Kursvokabel; dieselbe
  Übersetzung legt keine Dublette an, sondern findet die vorhandene Karte
  wieder. Verlauf und selbst angelegte Karteikarten laufen über denselben
  Geräte-Abgleich wie der übrige Kursfortschritt (siehe oben) – kein
  zusätzliches Secret dafür nötig, das war schon da.
  Der eingegebene Text geht ausschließlich an Claude über den eigenen Worker,
  nicht an einen weiteren Drittanbieter. Für vertrauliche Panini-Inhalte ist
  der Übersetzer trotzdem nicht gedacht – dafür gilt dieselbe Zurückhaltung
  wie generell beim Umgang mit Arbeitsinhalten in diesem Dashboard.
- **Woche – vor/zurück blättern:** Mit den Pfeilen links und rechts der
  Wochenanzeige beliebig weit in vergangene oder zukünftige Wochen blättern;
  „Diese Woche" springt jederzeit zur aktuellen Woche zurück.
- **Monat – 5 Jahre im Überblick:** Zuerst das Jahr, dann den Monat auswählen
  (statt eines einzigen langen Dropdowns) – so bleiben auch die nächsten
  5 Jahre übersichtlich erreichbar. Die Pfeile links/rechts blättern
  monatsweise weiter, auch über Jahresgrenzen hinweg.
- **Terminliste (früher „Jahr"):** Zeigt nicht mehr nur pauschal die nächsten
  12 Monate, sondern nutzt dieselbe Jahr-/Monatsauswahl wie „Monat" (Vormonat
  bis +5 Jahre) – lässt sich also gezielt auf jeden einzelnen Monat springen,
  dort dann als chronologische Liste statt als Kalenderraster.
- **Feiertage/Termine ausblenden:** Ein Feiertag (oder Termin) über den
  Papierkorb in Google Kalender „ausblenden" wirkt nur auf deine eigene
  Google-Kalender-Ansicht – die von dort exportierte iCal-Adresse liefert
  weiterhin den vollständigen, unveränderten Kalender, daher taucht so
  ein ausgeblendeter Feiertag trotzdem im Dashboard auf. Abhilfe: den
  (Teil-)Namen des Termins ins Secret `HOLIDAY_EXCLUDE` eintragen (z. B.
  `Fronleichnam`, `Mariä Himmelfahrt`) – einen pro Zeile oder durch Komma
  getrennt, Groß-/Kleinschreibung egal. Das Dashboard filtert dann bei
  jedem Lauf alle Termine heraus, deren Titel diesen Text enthält – egal
  aus welchem der verknüpften Kalender sie stammen.
- **Fehlersuche:** Wenn die Seite nicht aktualisiert, im Reiter **Actions**
  den letzten Lauf anklicken – die Fehlermeldung dort sagt meist direkt,
  welches Secret fehlt oder falsch ist. Einfach Claude zeigen.
