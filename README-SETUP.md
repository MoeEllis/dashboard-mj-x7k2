# Dashboard-Automatik: Einrichtung (einmalig, ca. 10 Minuten)

Danach aktualisiert sich dein Dashboard **alle 30 Minuten von selbst** aus
Todoist und Google Kalender – plus **⟳-Knopf** für sofortige Aktualisierung.
Claude brauchst du nur noch für Design-Änderungen.

---

## Schritt 1: Die zwei Dateien ins Repository bringen

**a) `build_dashboard.py`** (das Bau-Skript)

1. Repo `dashboard-mj-x7k2` auf github.com öffnen
2. **Add file → Upload files** → `build_dashboard.py` aus diesem Paket hineinziehen
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
| `REFRESH_TOKEN` | *(optional)* Feintoken | Nur für den ⟳-Knopf direkt in der Seite, siehe unten |
| `TRELLO_KEY` | *(optional)* dein Trello-API-Key | [trello.com/app-key](https://trello.com/app-key) (eingeloggt öffnen) → oben den **Key** kopieren |
| `TRELLO_TOKEN` | *(optional)* dein Trello-Token | Auf derselben Seite unten auf **„Token"** klicken → Zugriff erlauben → den angezeigten Token kopieren |
| `ANTHROPIC_API_KEY` | *(optional)* dein Claude-API-Key | [console.anthropic.com](https://console.anthropic.com/) → **Get API Keys** → neuen Key erstellen (eigenes, separates Konto mit Guthaben – siehe unten) |
| `SHOP_WATCHLIST` | *(optional)* Produkt-Adressen, **eine pro Zeile**, optional `\| Wunschname` dahinter | Produktseite im Shop öffnen, Adresse aus der Browserzeile kopieren – siehe „Reiter Markt → Händler" unten |
| `SHOP_PROBE` | *(optional)* Produkt-Adressen zum Testen, eine pro Zeile | Nur zur Diagnose: prüft im Actions-Log, ob ein Shop maschinenlesbare Preise liefert |
| `SHOP_SWEEP_KEYWORDS` | *(optional)* Suchwörter für den Katalog-Abgleich, eine pro Zeile oder per Komma | Vorgabe: `bundesliga`, `panini`, `topps` |
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
- **Reiter „Markt":** Ersetzt den früheren Reiter „Releases" und fasst drei
  Unterreiter zusammen: **Releases**, **Händler** und **Branche**. Die Auswahl
  des Unterreiters ist unabhängig von der im Reiter „Kalender".
- **Markt → Releases (Wettbewerbs-Sicht):** Dieselbe Release-Liste wie vorher,
  jetzt zusätzlich eingeordnet. Jeder Release bekommt automatisch aus seinem
  Titel eine **Konfiguration** (Hobby / Retail / Sticker, oder `?` wenn nicht
  erkennbar) und eine **Liga/Lizenz** (Bundesliga, Champions League, FIFA/WM,
  Premier League …). Eigene Releases (alles aus `OWN_BRANDS`) haben einen
  blauen Rand links, alles andere gilt als Wettbewerb. Oben stehen drei
  Kennzahlen-Karten für die nächsten 30/60/90 Tage (Anzahl insgesamt, eigen vs.
  Wettbewerb, eigener Anteil in Prozent, Hobby-Anteil, Treffer in beobachteten
  Ligen) und darunter die Liste **„Wettbewerbs-Releases in beobachteten Ligen"**
  – also genau die Termine, die für die eigene Planung kollidieren könnten.
  Filterbar nach Sicht, Konfiguration, Liga/Lizenz, Hersteller, Kategorie und
  Monat; ein Klick auf ein Hersteller- oder Liga-Badge filtert direkt.
  **Keine KI, keine Kosten** – reine Auswertung der ohnehin geladenen Daten.
- **Markt → Händler (Preis- und Verfügbarkeits-Monitor):** Liest Preis und
  Lagerstatus direkt von den Produktseiten deutscher Trading-Card-Shops
  (aktuell deichcards.de, crispycards.de, trading-card-corner.de, collect-it.de,
  cardport.de, card-corner.de, inside-the-box.de) – höchstens alle 2 Stunden je
  Shop, mit Pause zwischen den Abrufen, damit die Shops nicht belastet werden.
  Je Produkt siehst du den aktuellen Preis, die Veränderung zu gestern und zur
  Vorwoche, eine kleine Verlaufskurve, Minimum/Maximum, den Lagerstatus
  (verfügbar / ausverkauft / **unbekannt**, wenn der Shop es nicht verrät) und
  einen Marker, wenn ein Produkt gerade **wieder da** oder **neu ausverkauft**
  ist. Der Verlauf wird 180 Tage lang in `cache/shopwatch.json` mitgeschrieben.
  Zwei Wege, wie Produkte in die Liste kommen: **(1) Watchlist** – Adressen im
  Secret `SHOP_WATCHLIST`, eine pro Zeile, optional mit `| Wunschname`
  dahinter; diese bleiben dauerhaft in der Liste, auch wenn ein Shop sie mal
  nicht ausliefert (dann steht „nicht gefunden" daran). **(2) Katalog-Abgleich**
  – bei den Shopify-Shops wird der Katalog nach den Wörtern aus
  `SHOP_SWEEP_KEYWORDS` durchsucht und passende Treffer automatisch ergänzt;
  verschwindet so ein Treffer länger als 30 Tage, fällt er wieder heraus.
  **Keine KI, keine Kosten.**
- **Markt → Branche (Branchen- und Lizenz-Radar):** Sammelt Meldungen aus
  Branchenquellen (Cardlines, Cardboard Connection, Sports Collectors Daily,
  CrispyCards-Blog, Kartenfan, Google-News-Suche DE) und filtert sie auf die
  für dich relevanten Stichwörter (Lizenz, Rechte, Hobby, Bundesliga, Panini,
  Topps, Fanatics, Grading …). Oben fasst Claude einmal **pro Kalendertag**
  die wichtigsten 5 Punkte zusammen – jeweils mit einer Zeile dazu, was das
  konkret für Panini bedeutet. Darunter je Quelle eine Kachel mit der
  ungefilterten Rohliste („2 von 12" = 2 relevante von 12 geladenen
  Meldungen), die sich bei jedem Lauf aktualisiert. Ist eine Quelle mal nicht
  erreichbar, steht das an der jeweiligen Kachel und die übrigen laufen
  weiter. Kosten: geschätzt **unter 0,5 Cent pro Tag**, da nur ein kurzer
  Aufruf täglich (Zwischenspeicher `cache/industry.json`), egal wie oft der
  ⟳-Knopf gedrückt wird. Ohne `ANTHROPIC_API_KEY` bleibt die Rohliste
  vollständig nutzbar, nur die Kurzfassung fehlt.
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
