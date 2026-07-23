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
| `REFRESH_TOKEN` | *(optional)* Feintoken | Nur für den ⟳-Knopf direkt in der Seite, siehe unten |
| `TRELLO_KEY` | *(optional)* dein Trello-API-Key | [trello.com/app-key](https://trello.com/app-key) (eingeloggt öffnen) → oben den **Key** kopieren |
| `TRELLO_TOKEN` | *(optional)* dein Trello-Token | Auf derselben Seite unten auf **„Token"** klicken → Zugriff erlauben → den angezeigten Token kopieren |
| `ANTHROPIC_API_KEY` | *(optional)* dein Claude-API-Key | [console.anthropic.com](https://console.anthropic.com/) → **Get API Keys** → neuen Key erstellen (eigenes, separates Konto mit Guthaben – siehe unten) |

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
  sichtbar als kleiner Punkt vor jedem Termin (Heute, Jahr) bzw. als
  eingefärbte Kachel (Woche, Monat). Eine Legende mit Kalendernamen und
  Farbe steht über den Ansichten „Woche", „Monat" und „Jahr". Die
  Zuordnung Kalender → Farbe bleibt stabil, auch wenn später ein weiterer
  Kalender dazukommt oder einer kurzzeitig nicht erreichbar ist.
- **Woche – vor/zurück blättern:** Im Reiter „Woche" mit den Pfeilen links
  und rechts der Wochenanzeige beliebig weit in vergangene oder zukünftige
  Wochen blättern; „Diese Woche" springt jederzeit zur aktuellen Woche
  zurück.
- **Monat – 5 Jahre im Überblick:** Im Reiter „Monat" zuerst das Jahr,
  dann den Monat auswählen (statt eines einzigen langen Dropdowns) – so
  bleiben auch die nächsten 5 Jahre übersichtlich erreichbar. Die
  Pfeile links/rechts blättern monatsweise weiter, auch über Jahresgrenzen
  hinweg.
- **Fehlersuche:** Wenn die Seite nicht aktualisiert, im Reiter **Actions**
  den letzten Lauf anklicken – die Fehlermeldung dort sagt meist direkt,
  welches Secret fehlt oder falsch ist. Einfach Claude zeigen.
