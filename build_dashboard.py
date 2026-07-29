#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baut Moritz' persönliches Dashboard und verschlüsselt es zu index.html.

Datenquellen:
  - Todoist Unified API v1 (Aufgaben, Projekte)        [Secret: TODOIST_TOKEN]
  - Google Kalender, private iCal-Adresse(n) (Termine) [Secret: ICS_URL (+ optional ICS_URLS für weitere Kalender)]
  - gradedmoments.de/cardshows (Cardshow-Termine)      [öffentlich]
  - News: ZDFheute, kicker, LigaInsider                [öffentlich]
Verschlüsselung:
  - AES-256-GCM, Schlüssel via PBKDF2-SHA256           [Secret: DASH_PASSWORD]
Optional:
  - REFRESH_TOKEN: Fine-grained PAT (nur Actions:write) für den ⟳-Knopf.
  - HOLIDAY_EXCLUDE: Titel-Fragmente (Termine/Feiertage), die trotz gültigem
    Kalender-Feed ausgefiltert werden sollen (z.B. irrelevante regionale
    Feiertage – Googles "Feiertag ausblenden" wirkt nur auf die eigene Ansicht,
    nicht auf den iCal-Export selbst).

Testmodus: DASH_TEST=1 nutzt eingebaute Beispieldaten statt der APIs.
Öffentliche Daten (Cardshows/News) werden in cache/ zwischengespeichert,
damit ein zeitweiliger Ausfall einer Quelle den Bau nicht stoppt.
"""
import os, re, sys, json, base64, html
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from email.utils import parsedate_to_datetime

TZ = ZoneInfo("Europe/Berlin")
REPO = os.environ.get("GITHUB_REPOSITORY", "MoeEllis/dashboard-mj-x7k2")
AREAS = ["Privat", "Arbeit", "Studium"]
MONTH_VIEW_HORIZON_MONTHS = 60  # Monatsansicht + Termine-Fetch: wie viele Monate in die Zukunft (5 Jahre)
AREA_KEYS = {"privat": "Privat", "arbeit": "Arbeit", "studium": "Studium"}
WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WD_LONG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]
CARDSHOWS_URL = "https://gradedmoments.de/cardshows/"
RELEASES_URL = "https://www.collectosk.com/de/new-release-calendar/"
# Bekannte Hersteller (Reihenfolge = Erkennungspriorität; 'UPPER DECK' vor 'LEAF' etc. unkritisch)
MAKERS = [("UPPER DECK", "Upper Deck"), ("TOPPS", "Topps"), ("PANINI", "Panini"),
          ("LEAF", "Leaf"), ("ULTIMATE DROPZ", "Ultimate Dropz"), ("FUTERA", "Futera"),
          ("BOWMAN", "Bowman"), ("FANATICS", "Fanatics"), ("CARDSMITHS", "Cardsmiths"),
          ("PARKSIDE", "Parkside"), ("SAGE", "Sage")]
MONTH_NUM = {"januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5,
             "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10,
             "november": 11, "dezember": 12}
UA = {"User-Agent": "Mozilla/5.0 (compatible; PersonalDashboard/1.0)"}
# Trello legt für jeden neuen Account automatisch ein Demo-Board an – das blenden wir aus.
TRELLO_SKIP_BOARDS = {"welcome board", "willkommens-board", "welcome-board"}
# Podcast "Das Hobby" – nur Folgen mit offiziellem Transkript werden zusammengefasst.
PODCAST_HOME = "https://dashobby.podigee.io"
PODCAST_FEED_URL = f"{PODCAST_HOME}/feed/mp3"
PODCAST_MODEL = (os.environ.get("PODCAST_MODEL") or "").strip() or "claude-haiku-4-5-20251001"
PODCAST_MAX_NEW_PER_RUN = 12     # bremst den Erst-Backfill über mehrere Läufe ab, statt alles auf einmal
PODCAST_STOP_AFTER_MISSES = 5    # so viele Folgen ohne Transkript hintereinander -> älter wird nicht mehr geprüft
PODCAST_FEED_SCAN_LIMIT = 60     # wie viele der neuesten Feed-Einträge je Lauf überhaupt betrachtet werden
# Wetter: Stuttgart, kostenlose Open-Meteo-API (kein Key nötig)
WEATHER_LAT, WEATHER_LON = 48.7758, 9.1829
WMO_CODES = {
    0: ("☀️", "Klar"), 1: ("🌤️", "Meist sonnig"), 2: ("⛅", "Teilweise bewölkt"), 3: ("☁️", "Bedeckt"),
    45: ("🌫️", "Nebel"), 48: ("🌫️", "Nebel (Reif)"),
    51: ("🌦️", "Leichter Nieselregen"), 53: ("🌦️", "Nieselregen"), 55: ("🌧️", "Starker Nieselregen"),
    56: ("🌧️", "Gefrierender Niesel"), 57: ("🌧️", "Gefrierender Niesel"),
    61: ("🌦️", "Leichter Regen"), 63: ("🌧️", "Regen"), 65: ("🌧️", "Starker Regen"),
    66: ("🌧️", "Gefrierender Regen"), 67: ("🌧️", "Gefrierender Regen"),
    71: ("🌨️", "Leichter Schneefall"), 73: ("🌨️", "Schneefall"), 75: ("❄️", "Starker Schneefall"), 77: ("❄️", "Schneegriesel"),
    80: ("🌦️", "Leichte Schauer"), 81: ("🌧️", "Schauer"), 82: ("⛈️", "Heftige Schauer"),
    85: ("🌨️", "Schneeschauer"), 86: ("❄️", "Starke Schneeschauer"),
    95: ("⛈️", "Gewitter"), 96: ("⛈️", "Gewitter mit Hagel"), 99: ("⛈️", "Schweres Gewitter mit Hagel"),
}
# News: welche Quellen zählen als "Sport" (Rest fällt unter "Weitere Themen")
NEWS_SPORT_SOURCES = {"kicker", "LigaInsider"}

# --- Markt · Händler-Monitor (STILLGELEGT) ----------------------------------
# STILLGELEGT am 28.07.2026: Der Unterreiter "Händler" ist aus dem Dashboard
# entfernt, weil die erreichbaren Shops nicht die relevanten Händler waren.
# Der komplette Unterbau (Konstanten, Auslese-Verfahren, fetch_shopwatch) bleibt
# absichtlich erhalten und getestet, damit die Funktion mit einer passenden
# Shop-Liste jederzeit wieder eingeschaltet werden kann. Sie wird derzeit
# NICHT aufgerufen – es entstehen keine Abrufe und keine Laufzeit.
#
# Drei Auslese-Verfahren decken alle geprüften deutschen Trading-Card-Shops ab:
#   1. Shopify: an eine Produkt-Adresse angehängtes ".js" liefert JSON mit Preis
#      (in Cent!) und Lagerstatus. Zusätzlich gibt es /products.json als
#      Katalog-Endpunkt – ein Abruf, bis zu 250 Produkte.
#   2. JSON-LD nach schema.org (JTL-Shop, Magento): <script type="application/ld+json">
#      mit Product/Offer -> price, priceCurrency, availability.
#   3. Open Graph (ePages, z.B. inside-the-box.de): og:price:amount/-currency,
#      Lagerstatus nur als deutscher Text ("bestellbar" / "ausverkauft").
# Nicht aufgenommen: toptradingcards.com (Jimdo rendert Preise erst im Browser,
# im ausgelieferten HTML steht kein Preis) und tradingcards-zubehoer.de
# (Zubehör-Sortiment, Gesellschaft im Insolvenzverfahren).
SHOP_SWEEP_SHOPS = [
    ("deichcards.de", "https://deichcards.de"),
    ("crispycards.de", "https://crispycards.de"),
    ("trading-card-corner.de", "https://trading-card-corner.de"),
]
SHOP_SWEEP_KEYWORDS_DEFAULT = ["bundesliga", "panini", "topps"]
SHOP_SWEEP_PAGES = 3            # bis zu 750 Produkte je Shop
SHOP_SWEEP_MAX_HITS = 30        # Sicherheitsnetz je Shop
SHOP_WATCH_MAX = 60             # Sicherheitsnetz für die Watchlist
SHOP_INTERVAL_HOURS = 2         # Shops nur alle N Stunden abfragen, nicht bei jedem 30-Minuten-Lauf
SHOP_HISTORY_DAYS = 180         # so lange bleibt die Preishistorie erhalten
SHOP_DROP_DAYS = 30             # ausgelistete Katalogtreffer nach so vielen Tagen vergessen
SHOP_DEFAULT_DELAY = 1.5        # Mindestabstand zwischen zwei Anfragen an denselben Host
SHOP_HOST_DELAY = {"collect-it.de": 20.0}   # robots.txt bittet dort um Crawl-delay 20

# --- Markt · Branchen- & Lizenz-Radar --------------------------------------
# Geprüfte Feeds. Bewusst NICHT dabei: beckett.com (403, Bot-Sperre),
# blowoutbuzz.com (Feed-Pfad existiert nicht mehr), sammelbild.info (seit 2022
# nicht mehr gepflegt).
INDUSTRY_FEEDS_DEFAULT = [
    ("Cardlines", "https://cardlines.com/feed/"),
    ("Cardboard Connection", "https://www.cardboardconnection.com/feed/"),
    # Entfernt am 28.07.2026: Sports Collectors Daily (lieferte keine
    # relevanten Meldungen), CrispyCards (DE) und Kartenfan (DE) (veraltete
    # Meldungen). Über das Secret INDUSTRY_FEEDS jederzeit wieder ergänzbar.
    ("Google News (int.)",
     "https://news.google.com/rss/search?q=%22trading+cards%22+(Panini+OR+Topps+OR+Fanatics)"
     "&hl=en-US&gl=US&ceid=US:en"),
    ("Google News (DE)",
     "https://news.google.com/rss/search?q=%22Sammelkarten%22+OR+%22Sammelbilder%22+OR+%22Trading+Cards%22"
     "&hl=de&gl=DE&ceid=DE:de"),
]
INDUSTRY_KEYWORDS_DEFAULT = [
    "panini", "topps", "fanatics", "upper deck", "futera", "leaf", "bundesliga", "dfb", "dfl",
    "uefa", "fifa", "champions league", "premier league", "lizenz", "license", "licensing",
    "sammelbilder", "sammelkarten", "trading card", "hobby box", "breaker", "psa", "grading",
    "sticker", "album", "hobby", "release",
]
INDUSTRY_ITEMS_PER_FEED = 12
INDUSTRY_DIGEST_MAX = 45        # so viele Überschriften gehen maximal in den KI-Aufruf
INDUSTRY_DIGEST_CACHE_V = 2     # 2 = Kurzfassung mit Quell-Verweisen je Zeile

# --- Markt · Releases: eigene Marken, Konfiguration, Liga/Lizenz -----------
OWN_BRANDS_DEFAULT = ["Panini"]
WATCH_LEAGUES_DEFAULT = ["Bundesliga", "Champions League", "FIFA / WM", "Premier League"]
# Reihenfolge = Erkennungspriorität (Hobby-Marker vor Retail-Markern)
CONFIG_MARKERS = [
    ("BREAKERS DELIGHT", "Hobby"), ("FIRST OFF THE LINE", "Hobby"), ("FOTL", "Hobby"),
    ("HOBBY", "Hobby"), (" H2", "Hobby"), ("CHOICE", "Hobby"),
    ("BLASTER", "Retail"), ("MEGA", "Retail"), ("HANGER", "Retail"), ("FAT PACK", "Retail"),
    ("VALUE PACK", "Retail"), ("MULTI-PACK", "Retail"), ("MULTIPACK", "Retail"),
    ("TIN", "Retail"), ("RETAIL", "Retail"),
    ("STICKER", "Sticker"), ("ALBUM", "Sticker"),
]
LEAGUE_MARKERS = [
    ("BUNDESLIGA", "Bundesliga"),
    ("CHAMPIONS LEAGUE", "Champions League"), ("UCC ", "Champions League"), ("UEFA CLUB", "Champions League"),
    ("EUROPA LEAGUE", "Europa League"),
    ("PREMIER LEAGUE", "Premier League"), ("MERLIN", "Premier League"), ("EPL", "Premier League"),
    ("WORLD CUP", "FIFA / WM"), ("WELTMEISTER", "FIFA / WM"), ("FIFA", "FIFA / WM"),
    ("EURO 2028", "UEFA EURO"), ("UEFA EURO", "UEFA EURO"),
    ("LALIGA", "LaLiga"), ("LA LIGA", "LaLiga"), ("SERIE A", "Serie A"), ("LIGUE 1", "Ligue 1"),
    ("EREDIVISIE", "Eredivisie"), ("MLS", "MLS"),
    ("WNBA", "WNBA"), ("NBA", "NBA"), ("NFL", "NFL"), ("MLB", "MLB"), ("NHL", "NHL"),
    ("UFC", "UFC"), ("WWE", "WWE"), ("FORMULA", "Formel 1"), ("F1 ", "Formel 1"),
    ("POKEMON", "Pokémon"), ("POKÉMON", "Pokémon"), ("ONE PIECE", "One Piece"),
    ("YU-GI-OH", "Yu-Gi-Oh!"), ("LORCANA", "Lorcana"), ("MAGIC", "Magic"), ("DISNEY", "Disney"),
    ("SOCCER", "Fußball (weitere)"), ("FUSSBALL", "Fußball (weitere)"), ("FUßBALL", "Fußball (weitere)"),
    ("BASKETBALL", "Basketball (weitere)"), ("BASEBALL", "Baseball (weitere)"),
    ("HOCKEY", "Hockey (weitere)"), ("FOOTBALL", "Football (weitere)"),
]

esc = html.escape


def ym_add(y, m, k):
    m2 = m - 1 + k
    return (y + m2 // 12, m2 % 12 + 1)


# ------------------------------------------------------------------ Cache ---
def load_cache(name):
    try:
        with open(f"cache/{name}.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cache(name, data):
    os.makedirs("cache", exist_ok=True)
    with open(f"cache/{name}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


# ---------------------------------------------------------------- Todoist ---
def fetch_todoist(token):
    """Liefert (tasks, done_today) über die aktuelle Todoist Unified API v1."""
    import requests
    H = {"Authorization": f"Bearer {token}", **UA}
    r = requests.post(
        "https://api.todoist.com/api/v1/sync", headers=H, timeout=30,
        data={"sync_token": "*", "resource_types": '["items","projects"]'})
    if r.status_code == 401:
        sys.exit("FEHLER: TODOIST_TOKEN wird abgelehnt (401). Bitte in Todoist unter "
                 "Einstellungen → Integrationen → Entwickler den API-Token neu kopieren "
                 "und das Secret TODOIST_TOKEN aktualisieren.")
    if r.status_code != 200:
        sys.exit(f"FEHLER: Todoist-API antwortet mit HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    projects = [p for p in data.get("projects", []) if not p.get("is_deleted")]
    raw_tasks = [t for t in data.get("items", [])
                 if not t.get("checked") and not t.get("is_deleted")]
    print(f"Todoist: {len(projects)} Projekte, {len(raw_tasks)} offene Aufgaben geladen")

    tasks = map_todoist(projects, raw_tasks)

    done_today = 0
    try:
        since = datetime.now(TZ).strftime("%Y-%m-%dT00:00:00")
        until = datetime.now(TZ).strftime("%Y-%m-%dT23:59:59")
        r2 = requests.get("https://api.todoist.com/api/v1/tasks/completed/by_completion_date",
                          headers=H, params={"since": since, "until": until, "limit": 200},
                          timeout=30)
        if r2.status_code == 200:
            j = r2.json()
            done_today = len(j.get("items", j.get("results", [])))
        else:
            print(f"Hinweis: Erledigt-Zähler nicht verfügbar (HTTP {r2.status_code}) – zeige 0.")
    except Exception as e:
        print(f"Hinweis: Erledigt-Zähler nicht verfügbar ({e}) – zeige 0.")
    return tasks, done_today


def close_todoist_tasks(token, ids):
    """Schließt Aufgaben in Todoist ab. Wird vom Häkchen im Dashboard ausgelöst.

    Der Browser darf die Todoist-API nicht direkt ansprechen (kein CORS für
    Anfragen mit Zugangsdaten), und der TODOIST_TOKEN soll die Seite ohnehin
    nie erreichen. Stattdessen stößt ein Klick den Workflow mit der Eingabe
    `close_tasks` an – hier, im Lauf auf dem Server, wird tatsächlich
    geschlossen. Fehler einzelner IDs sind harmlos: der Browser merkt sich
    offene Häkchen und versucht es beim nächsten Laden erneut.
    """
    import requests
    H = {"Authorization": f"Bearer {token}", **UA}
    ok, fehler = 0, 0
    for tid in ids:
        try:
            r = requests.post(f"https://api.todoist.com/api/v1/tasks/{tid}/close",
                              headers=H, timeout=20)
            # 204 = geschlossen. 404/410 = war schon weg, zählt auch als Erfolg.
            if r.status_code in (200, 204, 404, 410):
                ok += 1
            else:
                fehler += 1
                print(f"Hinweis: Aufgabe {tid} nicht geschlossen (HTTP {r.status_code}).")
        except Exception as e:
            fehler += 1
            print(f"Hinweis: Aufgabe {tid} nicht geschlossen ({e}).")
    print(f"Todoist: {ok} Aufgabe(n) abgeschlossen"
          + (f", {fehler} fehlgeschlagen" if fehler else ""))
    return ok


def map_todoist(projects, raw_tasks):
    """Ordnet Todoist-Aufgaben den drei Lebensbereichen zu."""
    by_id = {p["id"]: p for p in projects}

    def top_ancestor(p):
        seen = set()
        while p.get("parent_id") and p["parent_id"] in by_id and p["id"] not in seen:
            seen.add(p["id"])
            p = by_id[p["parent_id"]]
        return p

    tasks = []
    for t in raw_tasks:
        proj = by_id.get(t.get("project_id"))
        if not proj:
            continue
        top = top_ancestor(proj)
        area = AREA_KEYS.get(top["name"].strip().lower())
        if not area:
            continue
        due = None
        if t.get("due") and t["due"].get("date"):
            due = t["due"]["date"][:10]
        tasks.append({
            "area": area,
            # Die Todoist-ID wird gebraucht, um die Aufgabe später per Klick im
            # Dashboard wirklich in Todoist abschließen zu können.
            "id": str(t.get("id") or ""),
            "content": t.get("content", ""),
            # Todoist nennt das Notizfeld "description". Es kann mehrzeilig sein.
            "beschreibung": (t.get("description") or "").strip(),
            "project": proj["name"] if proj["id"] != top["id"] else None,
            "due": due,
            "prio_hoch": t.get("priority", 1) >= 4,
        })
    if not tasks and raw_tasks:
        names = ", ".join(sorted({top_ancestor(by_id[t["project_id"]])["name"]
                                  for t in raw_tasks if t.get("project_id") in by_id}))
        print(f"WARNUNG: Keine Aufgabe konnte Privat/Arbeit/Studium zugeordnet werden. "
              f"Gefundene Hauptprojekte: {names}. Bitte Projektnamen prüfen.")
    return tasks


# ------------------------------------------------------------------- iCal ---
def fetch_events(ics_urls, start, end, exclude_titles=None):
    """Google-Kalender-Termine [start, end) inkl. aufgelöster Serientermine –
    über einen oder mehrere Kalender (ICS_URL + optional ICS_URLS) zusammengeführt.
    Eine einzelne nicht ladbare Kalender-Adresse bricht den Bau nicht ab (Warnung
    statt Abbruch), nur wenn KEINE der Adressen ladbar ist, wird abgebrochen.
    Jeder Termin bekommt "cal" = Index seiner Quelle (Reihenfolge ICS_URL, dann
    ICS_URLS) für die Farbcodierung; zusätzlich wird cal_meta zurückgegeben
    (Name je Kalender aus X-WR-CALNAME, Fallback "Kalender N").
    exclude_titles: optionale Liste von Titel-Fragmenten (z.B. aus HOLIDAY_EXCLUDE) –
    Termine, deren Titel eines dieser Fragmente enthält (Groß-/Kleinschreibung egal),
    werden verworfen. Nötig, weil Googles persönliches "Feiertag ausblenden" nur die
    eigene Ansicht betrifft, nicht aber die exportierte iCal-Adresse selbst."""
    import requests, icalendar, recurring_ical_events
    if isinstance(ics_urls, str):
        ics_urls = [ics_urls]
    exclude_norm = [t.strip().casefold() for t in (exclude_titles or []) if t.strip()]
    out, seen, any_ok, errors = [], set(), False, []
    cal_meta = []
    for idx, ics_url in enumerate(ics_urls):
        try:
            resp = requests.get(ics_url, timeout=30, headers=UA)
            if resp.status_code != 200:
                raise ValueError(f"HTTP {resp.status_code}")
            cal = icalendar.Calendar.from_ical(resp.content)
        except Exception as e:
            short = ics_url[:70] + ("…" if len(ics_url) > 70 else "")
            errors.append(f"{short}: {e}")
            print(f"Hinweis: Kalender-Adresse nicht ladbar ({short}): {e}")
            cal_meta.append({"idx": idx, "name": f"Kalender {idx + 1}", "ok": False})
            continue
        any_ok = True
        name = str(cal.get("X-WR-CALNAME") or "").strip() or f"Kalender {idx + 1}"
        cal_meta.append({"idx": idx, "name": name, "ok": True})
        for ev in recurring_ical_events.of(cal).between(start, end):
            dtstart = ev.get("DTSTART").dt
            dtend = ev.get("DTEND").dt if ev.get("DTEND") else None
            title = str(ev.get("SUMMARY", "Termin"))
            uid = str(ev.get("UID", ""))
            if isinstance(dtstart, datetime):
                local = dtstart.astimezone(TZ)
                d, tm = local.date(), local.strftime("%H:%M")
                if isinstance(dtend, datetime):
                    end_local = dtend.astimezone(TZ)
                    te, end_d = end_local.strftime("%H:%M"), end_local.date()
                    # Endet exakt um Mitternacht: gehört noch zum Vortag (sonst "Phantom-Tag" ohne Inhalt)
                    if end_d > d and end_local.time() == datetime.min.time():
                        end_d -= timedelta(days=1)
                else:
                    te, end_d = "", d
            else:
                # Ganztägiger Termin: DTSTART/DTEND sind reine Datumswerte, DTEND ist laut
                # iCal-Spec EXKLUSIV (der Tag NACH dem letzten Tag) und muss daher -1 Tag gerechnet werden.
                d, tm, te = dtstart, "", ""
                end_d = (dtend - timedelta(days=1)) if isinstance(dtend, date) and dtend > dtstart else d
            if end_d < d:
                end_d = d
            if exclude_norm and any(t in title.casefold() for t in exclude_norm):
                continue
            # Dedup (z.B. falls dieselbe Kalender-Adresse versehentlich doppelt hinterlegt ist)
            key = (uid, d.isoformat(), tm)
            if key in seen:
                continue
            seen.add(key)
            out.append({"date": d.isoformat(), "end_date": end_d.isoformat(), "time": tm, "end_time": te,
                        "title": title, "cal": idx})
    if not any_ok:
        sys.exit("FEHLER: Keine der hinterlegten Kalender-Adressen (ICS_URL/ICS_URLS) konnte geladen werden – "
                  + " | ".join(errors) + ". Bitte in Google Kalender → Einstellungen → jeweiliger Kalender → "
                  "'Kalender integrieren' die 'Privatadresse im iCal-Format' (bzw. bei öffentlichen Kalendern "
                  "wie Feiertagen die 'Öffentliche Adresse im iCal-Format') neu kopieren.")
    out.sort(key=lambda e: (e["date"], e["time"]))
    return out, cal_meta


# -------------------------------------------------------------- Cardshows ---
_DATE_DE = re.compile(r"(\d{1,2})\.\s*(Januar|Februar|März|Maerz|April|Mai|Juni|Juli|August|"
                      r"September|Oktober|November|Dezember)\s*(\d{4})", re.IGNORECASE)
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\b")
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(_TAG_RE.sub(" ", s))).strip()


def parse_cardshows(html_text, today):
    """Parst die Event-Tabelle von gradedmoments.de/cardshows.
    (Der iCal-Export der Seite enthält nur Alt-Termine bis 2024 und ist unbrauchbar –
    deshalb wird die sichtbare Tabelle geparst.)"""
    if isinstance(html_text, bytes):
        html_text = html_text.decode("utf-8", errors="replace")
    shows = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, re.S | re.I):
        link = re.search(r'<a[^>]+href="(https?://(?:www\.)?gradedmoments\.de/events/[^"]+)"[^>]*>(.*?)</a>',
                         row, re.S | re.I)
        if not link:
            continue
        url, name = link.group(1), _strip_tags(link.group(2))
        text = _strip_tags(row)
        dates = _DATE_DE.findall(text)
        if not dates or not name:
            continue
        def to_date(m):
            return date(int(m[2]), MONTH_NUM[m[1].lower()], int(m[0]))
        try:
            sdate = to_date(dates[0])
            edate = to_date(dates[1]) if len(dates) > 1 else None
        except Exception:
            continue
        times = _TIME_RE.findall(text)
        stime = f"{int(times[0][0]):02d}:{times[0][1]}" if times else None
        etime = f"{int(times[1][0]):02d}:{times[1][1]}" if len(times) > 1 else None
        # Ort: Text nach dem Veranstaltungsnamen bis "Kategorie"
        loc = ""
        pos = text.find(name)
        if pos >= 0:
            tail = text[pos + len(name):]
            kat = re.search(r"[-–]\s*Kategorie", tail)
            loc = tail[:kat.start()] if kat else tail
            loc = loc.strip(" -–*·|")
        low = text.lower()
        end_ref = edate or sdate
        if end_ref < today:
            continue
        shows.append({
            "start": sdate.isoformat(), "end": edate.isoformat() if edate else None,
            "time": stime, "end_time": etime,
            "name": name, "location": loc, "url": url,
            "is_de": ("deutschland" in low) or ("germany" in low),
        })
    shows.sort(key=lambda s: s["start"])
    return shows


def fetch_cardshows(today):
    """Liest ALLE Seiten der Event-Übersicht (Pagination: ?pno=2, ?pno=3, …)."""
    import requests
    try:
        shows, seen = [], set()
        for p in range(1, 11):  # Sicherheitsgrenze: max. 10 Seiten
            url = CARDSHOWS_URL if p == 1 else f"{CARDSHOWS_URL}?pno={p}"
            r = requests.get(url, timeout=30, headers=UA)
            r.raise_for_status()
            page_shows = parse_cardshows(r.text, today)
            new = [s for s in page_shows if (s["start"], s["name"]) not in seen]
            if not new:
                break
            for s in new:
                seen.add((s["start"], s["name"]))
            shows.extend(new)
        if not shows:
            raise ValueError("keine kommenden Shows in der Seite gefunden")
        shows.sort(key=lambda s: s["start"])
        shows = shows[:200]
        save_cache("cardshows", shows)
        print(f"Cardshows: {len(shows)} kommende Shows geladen ({p} Seite(n) gelesen)")
        return shows, None
    except Exception as e:
        cached = load_cache("cardshows")
        if cached:
            print(f"Hinweis: Cardshows-Quelle nicht erreichbar ({e}) – nutze Zwischenspeicher.")
            return cached, "Quelle gerade nicht erreichbar – Stand vom letzten erfolgreichen Abruf."
        print(f"Hinweis: Cardshows nicht verfügbar ({e}).")
        return [], "Quelle derzeit nicht erreichbar."


# --------------------------------------------------------------- Releases ---
_REL_DATE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")


def detect_maker(name):
    up = name.upper()
    for key, label in MAKERS:
        if key in up:
            return label
    return "Sonstige"


def parse_releases(html_text):
    """Parst die Release-Tabelle von collectosk.com.
    Zeilen: Datum (DD.MM.YYYY oder leer/TBD) | Kollektionsname (ggf. verlinkt)
    | Checklisten-Link | Kategorie."""
    if isinstance(html_text, bytes):
        html_text = html_text.decode("utf-8", errors="replace")
    releases = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html_text, re.S | re.I):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)
        if len(cells) < 2:
            continue
        texts = [_strip_tags(c) for c in cells]
        # Datum aus der ersten Zelle
        m = _REL_DATE.search(texts[0])
        rel_date = None
        if m:
            try:
                rel_date = date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
            except Exception:
                rel_date = None
        # Namenszelle: die Zelle mit dem längsten Text (überspringt Datum/CL/Kategorie)
        name_idx = max(range(len(texts)), key=lambda i: len(texts[i]))
        name = texts[name_idx]
        if not name or name.lower() in ("datum", "kollektionsname", "kategorie", "cl"):
            continue
        if not m and "tbd" not in texts[0].lower() and texts[0].strip():
            # erste Zelle enthält weder Datum noch TBD/leer -> vermutlich keine Datenzeile
            if not _REL_DATE.search(_strip_tags(row)):
                pass  # TBD-Zeilen haben oft eine leere Datumszelle – Zeile trotzdem zulassen
        url = ""
        mlink = re.search(r'<a[^>]+href="(https?://(?:www\.)?collectosk\.com/[^"#]+)"[^>]*>', cells[name_idx], re.I)
        if mlink:
            url = mlink.group(1)
        checklist = ""
        mcl = re.search(r'<a[^>]+href="(https?://[^"]*#checklist[^"]*)"', row, re.I)
        if mcl:
            checklist = mcl.group(1)
        category = texts[-1].strip() if len(texts) >= 2 else ""
        if category == name:
            category = ""
        releases.append({
            "date": rel_date, "name": name, "url": url, "checklist": checklist,
            "category": category, "maker": detect_maker(name),
        })
    return releases


def fetch_releases(today):
    """Lädt den Release-Kalender und pflegt eine dauerhafte Historie im Cache:
    Releases, die von der Seite verschwinden (älter als ~1 Woche), bleiben erhalten."""
    import requests
    history = load_cache("releases_history") or {}
    try:
        r = requests.get(RELEASES_URL, timeout=30, headers=UA)
        r.raise_for_status()
        current = parse_releases(r.text)
        if not current:
            raise ValueError("keine Releases in der Seite gefunden")
        for rel in current:
            key = rel["name"].lower()
            history[key] = rel  # neue Daten gewinnen (z. B. TBD bekommt später ein Datum)
        save_cache("releases_history", history)
        releases = list(history.values())
        print(f"Releases: {len(current)} aktuell auf der Seite, {len(releases)} insgesamt in der Historie")
        return releases, None
    except Exception as e:
        if history:
            print(f"Hinweis: Release-Kalender nicht erreichbar ({e}) – nutze Historie.")
            return list(history.values()), "Quelle gerade nicht erreichbar – Stand vom letzten erfolgreichen Abruf."
        print(f"Hinweis: Release-Kalender nicht verfügbar ({e}).")
        return [], "Quelle derzeit nicht erreichbar."


# ----------------------------------------------------------------- Trello ---
def _trello_due(due_iso):
    """Wandelt Trellos UTC-Fälligkeitsdatum in lokales Datum/Uhrzeit um."""
    if not due_iso:
        return None, None
    try:
        dt = datetime.fromisoformat(due_iso.replace("Z", "+00:00")).astimezone(TZ)
        return dt.date().isoformat(), dt.strftime("%H:%M")
    except Exception:
        return None, None


def fetch_trello(key, token, today):
    """Liefert offene Trello-Karten je Board/Liste (nur Listen mit Karten,
    Trellos automatisches Willkommens-Board wird ausgeblendet)."""
    if not key or not token:
        return [], None
    import requests
    auth = {"key": key, "token": token}
    try:
        r = requests.get("https://api.trello.com/1/members/me/boards", params={
            **auth, "fields": "name,url,closed", "filter": "open"}, timeout=20)
        r.raise_for_status()
        boards = []
        for b in r.json():
            if b.get("closed") or b.get("name", "").strip().lower() in TRELLO_SKIP_BOARDS:
                continue
            lr = requests.get(f"https://api.trello.com/1/boards/{b['id']}/lists", params={
                **auth, "cards": "open", "card_fields": "name,due,dueComplete,shortUrl",
                "fields": "name"}, timeout=20)
            lr.raise_for_status()
            lists = []
            for l in lr.json():
                cards = []
                for c in l.get("cards") or []:
                    due_date, due_time = _trello_due(c.get("due"))
                    overdue = bool(due_date) and not c.get("dueComplete") and due_date < today.isoformat()
                    cards.append({"name": c.get("name", ""), "due_date": due_date,
                                  "due_time": due_time, "overdue": overdue,
                                  "url": c.get("shortUrl", "")})
                if cards:
                    lists.append({"name": l.get("name", ""), "cards": cards})
            if lists:
                boards.append({"name": b.get("name", ""), "url": b.get("url", ""), "lists": lists})
        save_cache("trello", boards)
        n = sum(len(l["cards"]) for b in boards for l in b["lists"])
        print(f"Trello: {len(boards)} Board(s), {n} offene Karten geladen")
        return boards, None
    except Exception as e:
        cached = load_cache("trello")
        if cached is not None:
            print(f"Hinweis: Trello nicht erreichbar ({e}) – nutze letzten Stand.")
            return cached, "Quelle gerade nicht erreichbar – Stand vom letzten erfolgreichen Abruf."
        print(f"Hinweis: Trello nicht erreichbar ({e}).")
        return [], "Trello nicht erreichbar – TRELLO_KEY/TRELLO_TOKEN prüfen."


# ----------------------------------------------------------------- Wetter ---
def fetch_weather():
    """7-Tage-Vorhersage für Stuttgart über die kostenlose Open-Meteo-API (kein Secret nötig)."""
    import requests
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": WEATHER_LAT, "longitude": WEATHER_LON,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "Europe/Berlin", "forecast_days": 7,
        }, timeout=20, headers=UA)
        r.raise_for_status()
        d = r.json()["daily"]
        codes = d.get("weather_code") or d.get("weathercode") or []
        tmax = d.get("temperature_2m_max") or []
        tmin = d.get("temperature_2m_min") or []
        rain = d.get("precipitation_probability_max") or []
        days = []
        for i, iso in enumerate(d.get("time", [])):
            icon, label = WMO_CODES.get(codes[i] if i < len(codes) else None, ("🌡️", "—"))
            days.append({
                "date": iso, "icon": icon, "label": label,
                "tmax": round(tmax[i]) if i < len(tmax) and tmax[i] is not None else None,
                "tmin": round(tmin[i]) if i < len(tmin) and tmin[i] is not None else None,
                "rain": rain[i] if i < len(rain) else None,
            })
        save_cache("weather", days)
        print(f"Wetter: {len(days)} Tage geladen (Stuttgart)")
        return days, None
    except Exception as e:
        cached = load_cache("weather")
        if cached:
            print(f"Hinweis: Wetter nicht erreichbar ({e}) – nutze Zwischenspeicher.")
            return cached, "Stand vom letzten erfolgreichen Abruf"
        print(f"Hinweis: Wetter nicht verfügbar ({e}).")
        return [], "Quelle derzeit nicht erreichbar"


# ------------------------------------------------------------- Tages-Fokus ---
def fetch_day_focus(api_key, tasks, events, cardshows, trello, today):
    """Kurze KI-Einordnung für Tag+Woche – wird unabhängig davon, wie oft das
    Dashboard an einem Kalendertag aktualisiert wird, nur EINMAL pro Tag
    tatsächlich per Claude API berechnet (Cache-Key = Datum)."""
    key_today = today.isoformat()
    cache = load_cache("dayfocus") or {}
    if cache.get("date") == key_today and cache.get("lines"):
        return cache["lines"], None
    if not api_key:
        return None, ("Noch nicht eingerichtet – Secret ANTHROPIC_API_KEY hinterlegen, dann erscheint "
                       "hier täglich eine kurze Einordnung für Tag und Woche.")

    monday = today - timedelta(days=today.weekday())
    week_end = monday + timedelta(days=6)
    week_events = [e for e in events if monday.isoformat() <= e["date"] <= week_end.isoformat()]
    week_tasks = [t for t in tasks if t["due"] and monday.isoformat() <= t["due"] <= week_end.isoformat()]
    overdue_tasks = [t for t in tasks if t["due"] and t["due"] < key_today]
    overdue_trello = [c["name"] for b in (trello or []) for l in b["lists"] for c in l["cards"] if c.get("overdue")]
    de_shows_sorted = sorted([s for s in cardshows if s.get("is_de") and s["start"] >= key_today],
                              key=lambda s: s["start"])
    next_de_show = de_shows_sorted[0] if de_shows_sorted else None

    lines_in = [f"Heutiges Datum: {key_today} ({WD_LONG[today.weekday()]})."]
    lines_in.append("Termine diese Woche: " + ("; ".join(
        f'{e["date"]} {e["time"] or "ganztägig"} {e["title"]}' for e in week_events) or "keine"))
    lines_in.append("Aufgaben mit Fälligkeit diese Woche: " + ("; ".join(
        f'{t["due"]} {t["content"]} ({t["area"]})' for t in week_tasks) or "keine"))
    lines_in.append("Überfällige Aufgaben: " + ("; ".join(t["content"] for t in overdue_tasks) or "keine"))
    lines_in.append("Überfällige Trello-Karten: " + ("; ".join(overdue_trello) or "keine"))
    lines_in.append("Nächste Cardshow in Deutschland: " + (
        f'{next_de_show["start"]} {next_de_show["name"]}' if next_de_show else "keine bekannt"))

    prompt = (
        "Du bist der persönliche Assistent für ein privates Dashboard. Schreib auf Basis der folgenden "
        "Rohdaten eine kurze, konkrete Einordnung für HEUTE und DIESE WOCHE auf Deutsch (3 bis 5 knappe, "
        "eigenständige Sätze, die konkrete Namen/Daten aus den Rohdaten nennen). Priorisiere Dringendes "
        "(überfällig, heute/morgen fällig) zuerst. Gib NUR die Sätze zurück, einen pro Zeile, ohne "
        "Nummerierung, ohne Aufzählungszeichen, ohne Einleitung oder Floskeln.\n\n" + "\n".join(lines_in)
    )
    import requests
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": PODCAST_MODEL, "max_tokens": 400, "messages": [{"role": "user", "content": prompt}]},
            timeout=60)
        r.raise_for_status()
        data = r.json()
        raw = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        out_lines = [re.sub(r"^[\-•*\d\.\)\s]+", "", ln).strip() for ln in raw.splitlines()]
        out_lines = [ln for ln in out_lines if ln]
    except Exception as e:
        print(f"Hinweis: Tages-Fokus fehlgeschlagen ({e}).")
        return None, None
    if not out_lines:
        return None, None
    save_cache("dayfocus", {"date": key_today, "lines": out_lines})
    print("Tages-Fokus: neu berechnet für heute.")
    return out_lines, None


# --------------------------------------------------------------- Podcast ---
def _strip_tags(raw):
    """Grober HTML->Text-Konverter (Skripte/Styles raus, Tags raus, Entities aufgelöst)."""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _podcast_episode_list(limit=PODCAST_FEED_SCAN_LIMIT):
    """Liste der neuesten Folgen (neueste zuerst) aus dem öffentlichen RSS-Feed."""
    import requests
    import xml.etree.ElementTree as ET
    PODCAST_NS = "{https://podcastindex.org/namespace/1.0}"
    r = requests.get(PODCAST_FEED_URL, timeout=30, headers=UA)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if not (title and link):
            continue
        guid = (item.findtext("guid") or link).strip()
        pub = (item.findtext("pubDate") or "").strip()
        try:
            date_iso = parsedate_to_datetime(pub).astimezone(TZ).date().isoformat()
        except Exception:
            date_iso = None
        desc_raw = item.findtext("description") or ""
        transcript_url = None
        el = item.find(f"{PODCAST_NS}transcript")
        if el is not None and el.get("url"):
            transcript_url = el.get("url")
        out.append({"title": title, "url": link, "guid": guid, "date": date_iso,
                     "description": _strip_tags(desc_raw), "transcript_url": transcript_url})
        if len(out) >= limit:
            break
    return out


def _fetch_transcript_text(ep):
    """Versucht den vollen Transkript-Text einer Folge zu holen. None, falls keins existiert."""
    import requests
    if ep.get("transcript_url"):
        try:
            r = requests.get(ep["transcript_url"], timeout=30, headers=UA)
            if r.status_code == 200 and r.text.strip():
                text = r.text.strip()
                # Manche Feeds liefern das Transkript als JSON-Array von Sprechsegmenten
                # (z.B. [{"start":..,"end":..,"text":".."}, ...]) statt als VTT/SRT-Text.
                # Ohne diese Sonderbehandlung würde die rohe JSON-Syntax (Klammern,
                # "start"/"end"-Felder) als Fließtext an die Zusammenfassung weitergereicht.
                if text[:1] in "[{":
                    try:
                        data = json.loads(text)
                        segments = data if isinstance(data, list) else (
                            data.get("segments") or data.get("cues") or data.get("words") or [])
                        parts = [seg.get("text", "").strip() for seg in segments
                                 if isinstance(seg, dict) and seg.get("text")]
                        if parts:
                            text = " ".join(parts)
                    except Exception:
                        pass
                else:
                    text = re.sub(r"^WEBVTT.*?\n\n", "", text, flags=re.DOTALL)
                    text = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[.,]\d{3}.*", "", text)
                    text = re.sub(r"^\d+$", "", text, flags=re.MULTILINE)
                text = re.sub(r"\s+", " ", text).strip()
                if len(text) > 200:
                    return text
        except Exception:
            pass
    # Fallback: die Podigee-Episodenseite veröffentlicht ein Transkript unter .../transcript
    try:
        r = requests.get(ep["url"].rstrip("/") + "/transcript", timeout=30, headers=UA)
        if r.status_code != 200:
            return None
        text = _strip_tags(r.text)
        if len(text) < 300:
            return None
        return text
    except Exception:
        return None


def _summarize_takeaways(title, description, transcript_text, api_key):
    """Fasst eine Folge in 4-7 prägnante, deutsche Takeaway-Stichpunkte zusammen
    (Claude API – echte Neuformulierung statt Satzausschnitten)."""
    import requests
    text = (transcript_text or description or "").strip()
    if not text:
        return None
    text = text[:15000]
    prompt = (
        'Du bekommst das Transkript (oder ersatzweise nur die Kurzbeschreibung) einer Folge '
        f'des deutschen Sammelkarten-Podcasts "Das Hobby".\n\nFolge: {title}\n\nText:\n{text}\n\n'
        "Fasse die 4 bis 7 wichtigsten inhaltlichen Takeaways als kurze, prägnante Stichpunkte "
        "auf Deutsch zusammen (je ein vollständiger, eigenständiger Satz, konkret, ohne "
        "Füllwörter oder Gesprächspartikel). Gib NUR die Stichpunkte zurück, einen pro Zeile, "
        "ohne Nummerierung, ohne Aufzählungszeichen, ohne Einleitung."
    )
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": PODCAST_MODEL, "max_tokens": 500,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60)
    r.raise_for_status()
    data = r.json()
    raw = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    lines = [re.sub(r"^[\-•*\d\.\)\s]+", "", ln).strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln]
    return lines or None


def fetch_podcast(api_key):
    """Holt neue Folgen von 'Das Hobby' mit offiziellem Transkript und lässt die
    Takeaways per Claude API zusammenfassen. Bereits verarbeitete Folgen werden
    dauerhaft in cache/podcast.json zwischengespeichert – pro Lauf werden nur
    neue Folgen (max. PODCAST_MAX_NEW_PER_RUN) verarbeitet, das genügt für die
    laufende Aktualisierung; ein initialer Rückstand baut sich über mehrere
    automatische Läufe hinweg ab. Kosten: siehe README-SETUP.md (grob unter
    einem Cent pro neuer Folge, da jede Folge nur einmal verarbeitet wird)."""
    if not api_key:
        print("Hinweis: Secret ANTHROPIC_API_KEY ist leer/fehlt – Podcast-Abschnitt wird übersprungen.")
        return [], "Noch nicht eingerichtet – Secret ANTHROPIC_API_KEY hinterlegen, dann erscheinen hier die Takeaways je Folge."
    print(f"Podcast: ANTHROPIC_API_KEY erkannt (Länge {len(api_key)} Zeichen, beginnt mit '{api_key[:7]}...').")
    cache = load_cache("podcast") or {}
    episodes_cache = cache.get("episodes", {})
    try:
        feed_eps = _podcast_episode_list()
        print(f"Podcast-Feed: {len(feed_eps)} Einträge im RSS-Feed gefunden.")
    except Exception as e:
        print(f"Hinweis: Podcast-Feed nicht erreichbar ({e}) – nutze Zwischenspeicher.")
        feed_eps = []

    processed, misses = 0, 0
    for ep in feed_eps:
        key = ep["guid"]
        cached = episodes_cache.get(key)
        if cached is not None:
            misses = misses + 1 if cached.get("no_transcript") else 0
        else:
            if processed >= PODCAST_MAX_NEW_PER_RUN:
                break
            transcript = _fetch_transcript_text(ep)
            if not transcript:
                print(f"Podcast – kein Transkript gefunden für: {ep['title']}")
                episodes_cache[key] = {"no_transcript": True, "title": ep["title"], "date": ep["date"]}
                processed += 1
                misses += 1
            else:
                try:
                    takeaways = _summarize_takeaways(ep["title"], ep["description"], transcript, api_key)
                except Exception as e:
                    print(f"Hinweis: Zusammenfassung für '{ep['title']}' fehlgeschlagen ({e}).")
                    takeaways = None
                processed += 1
                if takeaways:
                    episodes_cache[key] = {"no_transcript": False, "title": ep["title"],
                                            "date": ep["date"], "url": ep["url"], "takeaways": takeaways}
                    misses = 0
                    print(f"Podcast – neue Folge zusammengefasst: {ep['title']}")
                else:
                    # Kein Ergebnis (z.B. API-Fehler) -> nicht cachen, nächster Lauf versucht es erneut
                    misses = 0
        if misses >= PODCAST_STOP_AFTER_MISSES:
            break

    cache["episodes"] = episodes_cache
    save_cache("podcast", cache)
    result = [v for v in episodes_cache.values() if not v.get("no_transcript") and v.get("takeaways")]
    result.sort(key=lambda e: e.get("date") or "", reverse=True)
    n_no_transcript = sum(1 for v in episodes_cache.values() if v.get("no_transcript"))
    print(f"Podcast: {len(episodes_cache)} Folge(n) insgesamt im Zwischenspeicher, "
          f"davon {len(result)} mit Takeaways, {n_no_transcript} ohne Transkript.")
    note = None if result else "Noch keine Folge mit Transkript gefunden – der Erst-Abgleich läuft über mehrere automatische Aktualisierungen."
    return result, note


# ------------------------------------------------------------------- News ---
_IMG_EXT_RE = re.compile(r"\.(?:jpe?g|png|webp|gif)(?:\?|$)", re.IGNORECASE)


def parse_rss(xml_bytes, limit=8):
    """Titel + Link je News-Item; Bild wird optional aus <enclosure>/Media-RSS
    (media:content, media:thumbnail) ausgelesen, falls die Quelle das anbietet."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_bytes)
    MEDIA_NS = "{http://search.yahoo.com/mrss/}"

    def find_image(item):
        enc = item.find("enclosure")
        if enc is not None:
            url, typ = enc.get("url"), (enc.get("type") or "")
            if url and (typ.startswith("image") or _IMG_EXT_RE.search(url)):
                return url
        for tag in (f"{MEDIA_NS}content", f"{MEDIA_NS}thumbnail"):
            for el in item.iter(tag):
                url, typ = el.get("url"), (el.get("type") or "")
                if url and (not typ or typ.startswith("image") or _IMG_EXT_RE.search(url)):
                    return url
        return None

    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            entry = {"title": title, "url": link}
            image = find_image(item)
            if image:
                entry["image"] = image
            items.append(entry)
        if len(items) >= limit:
            break
    return items


def parse_ligainsider(html_text, limit=8):
    """Auf ligainsider.de zeigen mehrere <a>-Tags (Bild-Caption + echte
    Überschrift) auf dieselbe Artikel-URL; die Bild-Caption ist meist nur der
    Spielername und daher kürzer. Wir behalten je URL-Pfad den LÄNGSTEN
    Linktext (= die echte Überschrift) statt des ersten Treffers, und suchen
    im Text davor nach dem zugehörigen Vorschaubild."""
    pat = re.compile(
        r'<a[^>]+href="(?:https?://(?:www\.)?ligainsider\.de)?(/[a-z0-9\-]+_\d+/[a-z0-9\-]+-\d+/)"[^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL)
    img_pat = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)

    best = {}       # path -> (title, position im Dokument)
    order = []      # Pfade in Reihenfolge ihres ersten Auftretens
    for m in pat.finditer(html_text):
        path, inner = m.group(1), m.group(2)
        title = re.sub(r"<[^>]+>", " ", inner)
        title = html.unescape(title)
        title = re.sub(r"\s+", " ", title).strip()
        if not title or len(title) < 8:
            continue
        if path not in best:
            order.append(path)
            best[path] = (title, m.start())
        elif len(title) > len(best[path][0]):
            best[path] = (title, m.start())

    items = []
    for path in order:
        title, pos = best[path]
        window = html_text[max(0, pos - 2000):pos]
        imgs = img_pat.findall(window)
        entry = {"title": title, "url": "https://www.ligainsider.de" + path}
        if imgs:
            image = imgs[-1]
            entry["image"] = "https:" + image if image.startswith("//") else image
        items.append(entry)
        if len(items) >= limit:
            break
    return items


def fetch_news():
    """Liefert Liste von Quellen: {name, home, items, note}."""
    import requests
    sources = []

    def try_source(name, home, cache_key, getter):
        try:
            items = getter()
            if not items:
                raise ValueError("keine Einträge gefunden")
            save_cache(cache_key, items)
            print(f"News – {name}: {len(items)} Schlagzeilen")
            return {"name": name, "home": home, "items": items, "note": None}
        except Exception as e:
            cached = load_cache(cache_key)
            if cached:
                print(f"Hinweis: {name} nicht erreichbar ({e}) – nutze Zwischenspeicher.")
                return {"name": name, "home": home, "items": cached,
                        "note": "Stand vom letzten erfolgreichen Abruf"}
            print(f"Hinweis: {name} nicht verfügbar ({e}).")
            return {"name": name, "home": home, "items": [],
                    "note": "Quelle derzeit nicht erreichbar"}

    sources.append(try_source(
        "ZDFheute", "https://www.zdfheute.de", "news_zdf",
        lambda: parse_rss(requests.get("https://www.zdfheute.de/rss/zdf/nachrichten",
                                       timeout=30, headers=UA).content)))
    sources.append(try_source(
        "kicker", "https://www.kicker.de", "news_kicker",
        lambda: parse_rss(requests.get("https://newsfeed.kicker.de/news/aktuell",
                                       timeout=30, headers=UA).content)))
    sources.append(try_source(
        "LigaInsider", "https://www.ligainsider.de", "news_ligainsider",
        lambda: parse_ligainsider(requests.get("https://www.ligainsider.de/",
                                               timeout=30, headers=UA).text)))
    return sources


def summarize_news_digest(sources, api_key, today):
    """Kurze KI-Verdichtung je Kategorie (Sport / Weitere Themen), 1x pro Tag und
    Kategorie gecacht (cache/newsdigest.json) – bei häufigeren Dashboard-Läufen am
    selben Tag entsteht kein zusätzlicher API-Aufruf. Eingabe sind nur die
    Schlagzeilen (kein Volltext), das hält Kosten und Kontextlänge minimal."""
    key_today = today.isoformat()
    cache = load_cache("newsdigest") or {}
    if cache.get("date") != key_today:
        cache = {"date": key_today}
    groups = {
        "sport": [s for s in sources if s["name"] in NEWS_SPORT_SOURCES],
        "andere": [s for s in sources if s["name"] not in NEWS_SPORT_SOURCES],
    }
    labels = {"sport": "Sport", "andere": "Weitere Themen"}
    result = {}
    import requests
    for key, srcs in groups.items():
        if cache.get(key):
            result[key] = cache[key]
            continue
        titles = [it["title"] for s in srcs for it in s.get("items", [])][:30]
        if not api_key or not titles:
            result[key] = None
            continue
        prompt = (
            f'Hier sind aktuelle deutsche Nachrichten-Überschriften aus der Kategorie "{labels[key]}":\n\n'
            + "\n".join(f"- {t}" for t in titles)
            + '\n\nFasse daraus die 3 bis 4 wichtigsten Themen des Tages als kurze, eigenständige Sätze '
              "auf Deutsch zusammen (thematisch gebündelt, nicht jede Überschrift einzeln aufzählen). "
              "Gib NUR die Sätze zurück, einen pro Zeile, ohne Nummerierung, ohne Aufzählungszeichen, "
              "ohne Einleitung."
        )
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": PODCAST_MODEL, "max_tokens": 400, "messages": [{"role": "user", "content": prompt}]},
                timeout=60)
            r.raise_for_status()
            data = r.json()
            raw = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            lines = [re.sub(r"^[\-•*\d\.\)\s]+", "", ln).strip() for ln in raw.splitlines()]
            lines = [ln for ln in lines if ln]
            result[key] = lines or None
            if result[key]:
                print(f"News-Digest ({labels[key]}): neu berechnet für heute.")
        except Exception as e:
            print(f"Hinweis: News-Digest {labels[key]} fehlgeschlagen ({e}).")
            result[key] = None
    cache["sport"] = result.get("sport")
    cache["andere"] = result.get("andere")
    save_cache("newsdigest", cache)
    return result


# ------------------------------------------- Markt: Händler-Monitor (Preise) ---
_LDJSON_RE = re.compile(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)
_META_KV_RE = re.compile(r'<meta[^>]+(?:property|name)=["\']([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']', re.I)
_META_VK_RE = re.compile(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']([^"\']+)["\']', re.I)
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
# Reihenfolge zählt: "nicht verfügbar" muss vor "verfügbar" geprüft werden.
_SOLDOUT_WORDS = ["ausverkauft", "nicht mehr verfügbar", "nicht verfügbar", "nicht auf lager",
                  "derzeit nicht lieferbar", "vergriffen", "sold out", "out of stock"]
_INSTOCK_WORDS = ["bestellbar", "auf lager", "sofort verfügbar", "sofort lieferbar",
                  "lieferzeit", "versandfertig", "in stock", "verfügbar"]


def _shop_host(url):
    from urllib.parse import urlparse
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _shop_num(v):
    """Preis-Zahl aus beliebiger Schreibweise: 30000 (Cent), "300.00", "1.234,56 €"."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("\xa0", " ").replace("€", "").replace("EUR", "").strip()
    if not s:
        return None
    if "," in s and "." in s:
        # 1.234,56 (deutsch) vs. 1,234.56 (englisch): das hintere Zeichen ist das Dezimaltrennzeichen
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def _avail_from_text(html_text):
    """Lagerstatus aus dem Seitentext, wenn der Shop ihn nicht maschinenlesbar
    ausgibt (ePages). Bewusst unscharf: liefert None, wenn nichts Klares steht –
    dann zeigt das Dashboard 'unbekannt' statt einer falschen Aussage."""
    low = _strip_tags(html_text).lower()
    for w in _SOLDOUT_WORDS:
        if w in low:
            return False
    for w in _INSTOCK_WORDS:
        if w in low:
            return True
    return None


def _meta_map(html_text):
    metas = {}
    for k, v in _META_KV_RE.findall(html_text):
        metas.setdefault(k.lower(), v)
    for v, k in _META_VK_RE.findall(html_text):
        metas.setdefault(k.lower(), v)
    return metas


def _jsonld_product(html_text):
    """Sucht in allen ld+json-Blöcken den Product-Knoten – auch verschachtelt in
    @graph oder Listen, wie es JTL-Shop und Magento ausgeben."""
    import json as _json
    for block in _LDJSON_RE.findall(html_text):
        raw = block.strip()
        if not raw:
            continue
        try:
            data = _json.loads(raw)
        except Exception:
            try:
                data = _json.loads("[" + re.sub(r"\}\s*\{", "},{", raw) + "]")
            except Exception:
                continue
        stack, seen = [data], 0
        while stack and seen < 400:
            node = stack.pop()
            seen += 1
            if isinstance(node, list):
                stack.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            t = node.get("@type")
            types = t if isinstance(t, list) else [t]
            if any(str(x).lower() == "product" for x in types if x):
                return node
            stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
    return None


def _avail_from_schema(raw):
    a = str(raw or "").lower()
    if not a:
        return None
    if any(w in a for w in ("instock", "limitedavailability", "presale", "preorder", "backorder")):
        return True
    if any(w in a for w in ("outofstock", "soldout", "discontinued")):
        return False
    return None


def _from_jsonld(html_text):
    node = _jsonld_product(html_text)
    if not node:
        return None
    offers = node.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if not isinstance(offers, dict):
        offers = {}
    price = _shop_num(offers.get("price") or offers.get("lowPrice"))
    if price is None:
        return None
    name = node.get("name")
    return {"name": (str(name).strip() if name else None), "price": price,
            "currency": (offers.get("priceCurrency") or "EUR"),
            "available": _avail_from_schema(offers.get("availability")), "via": "JSON-LD"}


def _from_og(html_text):
    m = _meta_map(html_text)
    price = _shop_num(m.get("og:price:amount") or m.get("product:price:amount"))
    if price is None:
        return None
    avail = _avail_from_schema(m.get("og:availability") or m.get("product:availability"))
    if avail is None:
        avail = _avail_from_text(html_text)
    name = m.get("og:title")
    return {"name": (html.unescape(name).strip() if name else None), "price": price,
            "currency": html.unescape(m.get("og:price:currency") or m.get("product:price:currency") or "EUR"),
            "available": avail, "via": "Open Graph"}


class _HostThrottle:
    """Mindestabstand zwischen zwei Anfragen an denselben Host – collect-it.de
    bittet in seiner robots.txt ausdrücklich um 20 Sekunden Crawl-delay."""

    def __init__(self):
        self.last = {}

    def wait(self, url):
        import time
        host = _shop_host(url)
        gap = SHOP_HOST_DELAY.get(host, SHOP_DEFAULT_DELAY)
        prev = self.last.get(host)
        if prev is not None:
            rest = gap - (time.monotonic() - prev)
            if rest > 0:
                time.sleep(rest)
        self.last[host] = time.monotonic()


def _from_shopify(session, throttle, url):
    """Shopify: Produkt-Adresse + '.js' liefert JSON. Preise stehen dort in CENT
    (im Unterschied zu /products.json, wo sie als Dezimalzeichenkette stehen)."""
    base = url.split("?")[0].split("#")[0].rstrip("/")
    if "/products/" not in base:
        return None
    throttle.wait(base)
    r = session.get(base + ".js", timeout=25, headers=UA)
    if r.status_code != 200:
        return None
    try:
        d = r.json()
    except Exception:
        return None
    if not isinstance(d, dict) or "title" not in d:
        return None
    variants = [v for v in (d.get("variants") or []) if isinstance(v, dict)]
    cents = [v.get("price") for v in variants if isinstance(v.get("price"), (int, float))]
    if cents:
        price = min(cents) / 100.0
    elif isinstance(d.get("price"), (int, float)):
        price = d["price"] / 100.0
    else:
        return None
    avail = bool(d["available"]) if isinstance(d.get("available"), bool) \
        else any(v.get("available") for v in variants)
    return {"name": (d.get("title") or "").strip(), "price": price, "currency": "EUR",
            "available": avail, "via": "Shopify"}


def probe_product(session, throttle, url, label=None):
    """Preis + Lagerstatus einer Produktseite über das erste greifende Verfahren."""
    out = None
    try:
        out = _from_shopify(session, throttle, url)
    except Exception:
        out = None
    if out is None:
        try:
            throttle.wait(url)
            r = session.get(url, timeout=30, headers=UA)
            r.raise_for_status()
            text = r.text
            out = _from_jsonld(text) or _from_og(text)
            if out and not out.get("name"):
                mt = _TITLE_RE.search(text)
                if mt:
                    out["name"] = html.unescape(_strip_tags(mt.group(1))).strip()
        except Exception:
            return None
    if not out:
        return None
    out["url"] = url
    out["shop"] = _shop_host(url)
    if label:
        out["name"] = label
    if not out.get("name"):
        out["name"] = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ").title()
    return out


def sweep_shopify(session, throttle, shop_label, base, keywords):
    """Katalog-Abgleich: /products.json liefert bis zu 250 Produkte je Abruf.
    So findet der Monitor passende Neuheiten von selbst, ohne Watchlist-Pflege."""
    hits = []
    for page in range(1, SHOP_SWEEP_PAGES + 1):
        throttle.wait(base)
        r = session.get(f"{base}/products.json?limit=250&page={page}", timeout=30, headers=UA)
        if r.status_code != 200:
            break
        try:
            prods = (r.json() or {}).get("products") or []
        except Exception:
            break
        if not prods:
            break
        for p in prods:
            title = (p.get("title") or "").strip()
            low = title.lower()
            if not title or (keywords and not any(k in low for k in keywords)):
                continue
            variants = [v for v in (p.get("variants") or []) if isinstance(v, dict)]
            prices = [x for x in (_shop_num(v.get("price")) for v in variants) if x is not None]
            if not prices:
                continue
            hits.append({"name": title, "price": min(prices), "currency": "EUR",
                         "available": any(v.get("available") for v in variants),
                         "via": "Shopify (Katalog)", "shop": shop_label,
                         "url": f"{base}/products/{p.get('handle')}"})
        if len(prods) < 250:
            break
    return hits[:SHOP_SWEEP_MAX_HITS]


def _shopwatch_record(items, rec, now):
    """Schreibt einen Messwert in die Historie: ein Punkt je Kalendertag, der
    letzte Wert des Tages gewinnt. Vorwerte bleiben für die Änderungsanzeige."""
    key = rec["url"]
    old = items.get(key) or {}
    hist = [h for h in (old.get("hist") or []) if isinstance(h, list) and len(h) >= 3]
    day = now.date().isoformat()
    point = [day, rec["price"], (1 if rec["available"] else 0) if rec["available"] is not None else None]
    if hist and hist[-1][0] == day:
        hist[-1] = point
    else:
        hist.append(point)
    cutoff = (now.date() - timedelta(days=SHOP_HISTORY_DAYS)).isoformat()
    rec["hist"] = [h for h in hist if h[0] >= cutoff]
    rec["checked"] = now.strftime("%d.%m.%Y %H:%M")
    rec["first_seen"] = old.get("first_seen") or day
    rec["prev_price"] = old.get("price")
    rec["prev_available"] = old.get("available")
    items[key] = rec


def fetch_shopwatch(watchlist, sweep_keywords, now, probe_urls=None):
    """Preis- und Verfügbarkeitsmonitor für die Händler-Watchlist plus
    automatischer Katalog-Abgleich bei den Shopify-Shops. Kostet keine API-
    Aufrufe, nur HTTP. Läuft höchstens alle SHOP_INTERVAL_HOURS Stunden, damit
    der 30-Minuten-Takt des Dashboards die Shops nicht unnötig belastet."""
    import requests
    cache = load_cache("shopwatch") or {}
    items = cache.get("items") or {}
    slot = f'{now.date().isoformat()}-{now.hour // max(1, SHOP_INTERVAL_HOURS):02d}'
    if cache.get("slot") == slot and items:
        print(f"Händler: Zwischenspeicher genutzt ({len(items)} Produkte, "
              f"nächster Abruf nach spätestens {SHOP_INTERVAL_HOURS} h).")
        return items, None

    session = requests.Session()
    throttle = _HostThrottle()
    seen, errors, n_new = set(), 0, 0

    # Diagnose: unbekannte Shops einmal durchprobieren und ins Actions-Log schreiben
    for purl in (probe_urls or []):
        rec = probe_product(session, throttle, purl)
        if rec:
            print(f"Shop-Diagnose {purl}: Preis {rec['price']} {rec['currency']}, "
                  f"verfügbar={rec['available']}, Verfahren={rec['via']}")
        else:
            print(f"Shop-Diagnose {purl}: kein maschinenlesbarer Preis gefunden.")

    for entry in watchlist[:SHOP_WATCH_MAX]:
        url, label = entry
        rec = probe_product(session, throttle, url, label=label)
        if not rec:
            errors += 1
            print(f"Hinweis: Händler-Watchlist – kein Preis von {url}")
            continue
        if url not in items:
            n_new += 1
        rec["source"] = "watch"
        _shopwatch_record(items, rec, now)
        seen.add(url)

    for shop_label, base in SHOP_SWEEP_SHOPS:
        try:
            hits = sweep_shopify(session, throttle, shop_label, base, sweep_keywords)
            print(f"Händler-Katalog {shop_label}: {len(hits)} passende Produkte")
            for rec in hits:
                if rec["url"] in seen:
                    continue
                if rec["url"] not in items:
                    n_new += 1
                rec["source"] = "sweep"
                _shopwatch_record(items, rec, now)
                seen.add(rec["url"])
        except Exception as e:
            errors += 1
            print(f"Hinweis: Händler-Katalog {shop_label} nicht abrufbar ({e}).")

    # Produkte, die diesmal nicht auffindbar waren, bleiben mit Vermerk erhalten
    for url, rec in items.items():
        if url not in seen:
            rec["stale"] = True
        else:
            rec.pop("stale", None)

    # Der Katalog-Abgleich bringt laufend neue Produkte mit; ausgelistete Artikel
    # würden sich sonst endlos ansammeln. Watchlist-Einträge bleiben immer erhalten,
    # Katalogtreffer fliegen nach SHOP_DROP_DAYS ohne Fund heraus.
    if seen:
        drop_before = (now.date() - timedelta(days=SHOP_DROP_DAYS)).isoformat()
        for url in [u for u, r in items.items()
                    if r.get("stale") and r.get("source") != "watch"
                    and ((r.get("hist") or [["0000-00-00"]])[-1][0] < drop_before)]:
            items.pop(url, None)

    note = None
    if not seen and items:
        note = "Kein Shop erreichbar – Stand vom letzten erfolgreichen Abruf."
    elif errors:
        note = f"{errors} Quelle(n) diesmal nicht abrufbar."
    cache = {"slot": slot, "items": items}
    save_cache("shopwatch", cache)
    print(f"Händler: {len(seen)} Produkte aktualisiert ({n_new} neu), {len(items)} insgesamt beobachtet.")
    return items, note


# --------------------------------------- Markt: Branchen- & Lizenz-Radar ---
def _feed_date(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(raw).date().isoformat()
    except Exception:
        pass
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", raw)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def parse_feed(xml_bytes, limit=INDUSTRY_ITEMS_PER_FEED):
    """RSS (<item>) und Atom (<entry>) in einem Parser – die Branchenquellen
    mischen beides (CrispyCards liefert Atom, alle anderen RSS)."""
    import xml.etree.ElementTree as ET
    root = ET.fromstring(xml_bytes)
    ATOM = "{http://www.w3.org/2005/Atom}"
    DC = "{http://purl.org/dc/elements/1.1/}"
    out, seen = [], set()
    for node in list(root.iter("item")) + list(root.iter(f"{ATOM}entry")):
        title = (node.findtext("title") or node.findtext(f"{ATOM}title") or "").strip()
        link = (node.findtext("link") or "").strip()
        if not link:
            for le in node.iter(f"{ATOM}link"):
                if (le.get("rel") or "alternate") == "alternate" and le.get("href"):
                    link = le.get("href")
                    break
        if not title or not link or link in seen:
            continue
        seen.add(link)
        raw_date = (node.findtext("pubDate") or node.findtext(f"{ATOM}published")
                    or node.findtext(f"{ATOM}updated") or node.findtext(f"{DC}date") or "")
        out.append({"title": html.unescape(re.sub(r"\s+", " ", title)).strip(),
                    "url": link, "date": _feed_date(raw_date)})
    out.sort(key=lambda x: x.get("date") or "", reverse=True)
    return out[:limit]


def fetch_industry(feeds, keywords):
    """Branchenquellen einsammeln. Je Quelle mit eigenem Zwischenspeicher, damit
    ein einzelner Ausfall die Kachel nicht leert. Der Stichwortfilter hält die
    Liste – und damit die Eingabe des einen täglichen KI-Aufrufs – klein."""
    import requests
    kw = [k.strip().casefold() for k in keywords if k.strip()]
    sources = []
    for name, url in feeds:
        cache_key = "industry_" + re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
        try:
            r = requests.get(url, timeout=30, headers=UA)
            r.raise_for_status()
            items = parse_feed(r.content)
            if not items:
                raise ValueError("keine Einträge gefunden")
            save_cache(cache_key, items)
            note = None
        except Exception as e:
            items = load_cache(cache_key) or []
            note = "Stand vom letzten erfolgreichen Abruf" if items else "Quelle derzeit nicht erreichbar"
            print(f"Hinweis: Branchenquelle {name} nicht abrufbar ({e}).")
        hits = [it for it in items if not kw or any(k in it["title"].casefold() for k in kw)]
        home = re.match(r"(https?://[^/]+)", url)
        sources.append({"name": name, "home": home.group(1) if home else url,
                        "items": hits, "total": len(items), "note": note})
        if note is None:
            print(f"Branche – {name}: {len(hits)} von {len(items)} Einträgen relevant")
    return sources


def _parse_digest_lines(raw, refs):
    """Antwort des Modells in Zeilen zerlegen: Sachverhalt, Begründung und die
    Nummern der zugrunde liegenden Meldungen. Die Nummern werden hier zu
    echten Verweisen (Name, Titel, Adresse) aufgelöst; fehlen oder stimmen sie
    nicht, bleibt die Zeile einfach unverlinkt statt falsch verlinkt."""
    lines = []
    for ln in (raw or "").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = [p.strip() for p in ln.split("::")]
        idx_part = ""
        # Der Nummern-Teil steht hinten und enthält nur Zahlen und Trennzeichen.
        if len(parts) >= 2 and re.fullmatch(r"[\d\s,;/\.\+&\-]*\d[\d\s,;/\.\+&\-]*", parts[-1] or ""):
            idx_part = parts.pop()
        head = re.sub(r"^[\-•*\d\.\)\s]+", "", parts[0]).strip(" –—-")
        why = " ".join(p for p in parts[1:] if p).strip()
        if not head:
            continue
        links, seen = [], set()
        for num in re.findall(r"\d+", idx_part):
            i = int(num) - 1
            if 0 <= i < len(refs) and i not in seen:
                seen.add(i)
                r = refs[i]
                if r.get("url"):
                    links.append({"name": r.get("name", ""), "title": r.get("title", ""),
                                  "url": r["url"]})
            if len(links) >= 3:
                break
        lines.append({"head": head, "why": why, "links": links})
    return lines


def summarize_industry(sources, api_key, today):
    """Ein Haiku-Aufruf pro Kalendertag, datumsgeschlüsselt in cache/industry.json.
    Mehrfache Dashboard-Läufe am selben Tag kosten dadurch nichts zusätzlich."""
    key_today = today.isoformat()
    cache = load_cache("industry") or {}
    # Version 2 führt je Zeile die Quell-Verweise ("links") mit. Ein älterer
    # Zwischenspeicher ohne diese Angabe wird bewusst NICHT weiterverwendet,
    # sonst blieben die Zeilen bis morgen unverlinkt.
    cache_ok = cache.get("v") == INDUSTRY_DIGEST_CACHE_V
    if cache_ok and cache.get("date") == key_today and cache.get("lines"):
        return cache["lines"], None
    # Nummerierte Liste: das Modell nennt später nur die Nummern, das Auflösen
    # zu Titel und Adresse macht der Code – dadurch keine unscharfe
    # Titel-Zuordnung und keine erfundenen Adressen.
    refs = []
    for s in sources:
        for it in s.get("items", []):
            refs.append({"name": s.get("name", ""), "title": it.get("title", ""),
                         "url": it.get("url", "")})
    refs = refs[:INDUSTRY_DIGEST_MAX]
    if not api_key:
        return None, "Kein ANTHROPIC_API_KEY hinterlegt – Kurzfassung übersprungen."
    if not refs:
        return None, "Keine relevanten Branchenmeldungen gefunden."
    import requests
    prompt = (
        "Du berichtest einem Produktmanager von Panini Deutschland, der für den Hobby-Bereich "
        "des Trading-Card-Marktes verantwortlich ist. Hier sind aktuelle Schlagzeilen aus "
        "Branchenmedien, jede mit einer Nummer:\n\n"
        + "\n".join(f'[{i}] {r["title"]} [{r["name"]}]' for i, r in enumerate(refs, 1))
        + "\n\nFasse daraus die 4 bis 6 wichtigsten Entwicklungen zusammen. Lizenz-, Rechte- und "
          "Herstellerthemen (Panini, Topps, Fanatics, Upper Deck, Ligen und Verbände) zuerst, danach "
          "Produkt- und Markttrends. Schreibe auf Deutsch. Gib pro Zeile GENAU dieses Format aus:\n"
          "Kurzer Sachverhalt :: warum das für Panini Deutschland im Hobby-Bereich relevant ist :: 3, 7\n"
          "Der dritte Teil sind die Nummern der Schlagzeilen, auf die sich die Zeile stützt "
          "(mindestens eine, höchstens drei, wichtigste zuerst, nur Zahlen aus der Liste oben). "
          "Keine Nummerierung am Zeilenanfang, keine Aufzählungszeichen, keine Einleitung, "
          "keine Leerzeilen. Wenn ein Thema nur am Rand relevant ist, lass es weg."
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": PODCAST_MODEL, "max_tokens": 800, "messages": [{"role": "user", "content": prompt}]},
            timeout=90)
        r.raise_for_status()
        data = r.json()
        raw = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        lines = _parse_digest_lines(raw, refs)
        if not lines:
            raise ValueError("leere Antwort")
        save_cache("industry", {"v": INDUSTRY_DIGEST_CACHE_V, "date": key_today, "lines": lines})
        print(f"Branchen-Radar: neu berechnet für heute ({len(lines)} Punkte).")
        return lines, None
    except Exception as e:
        print(f"Hinweis: Branchen-Radar fehlgeschlagen ({e}).")
        old = cache.get("lines") if cache_ok else None
        return old, ("Kurzfassung von " + cache.get("date", "") if old else "Kurzfassung heute nicht verfügbar.")


# ------------------------------ Markt: Releases einordnen (ohne KI) ---------
def detect_config(name):
    """Hobby, Retail oder Sticker – aus den üblichen Produktnamens-Markern."""
    up = " " + name.upper() + " "
    for key, label in CONFIG_MARKERS:
        if key in up:
            return label
    return "unklar"


def detect_league(name, category=""):
    up = " " + (name + " " + (category or "")).upper() + " "
    for key, label in LEAGUE_MARKERS:
        if key in up:
            return label
    return "Sonstige"


def enrich_releases(releases, own_brands):
    """Ergänzt jedes Release um eigen/Wettbewerb, Konfiguration und Liga. Läuft
    bei jedem Build neu, damit auch alte Einträge aus der Historie eingeordnet
    werden, ohne den Zwischenspeicher migrieren zu müssen."""
    own_norm = [b.strip().casefold() for b in own_brands if b.strip()]
    for r in releases:
        maker = (r.get("maker") or "").casefold()
        name_cf = (r.get("name") or "").casefold()
        r["own"] = any(b in maker or b in name_cf for b in own_norm)
        r["side"] = "Eigen" if r["own"] else "Wettbewerb"
        r["config"] = detect_config(r.get("name") or "")
        r["league"] = detect_league(r.get("name") or "", r.get("category") or "")
    return releases


# ------------------------------------------------------------- Testdaten ---
def testdata(today):
    tasks = [
        {"area": "Privat", "id": "9001", "content": "Einkauf für die Woche planen", "project": None,
         "beschreibung": "", "due": today.isoformat(), "prio_hoch": False},
        {"area": "Arbeit", "id": "9002", "content": "Wochenplanung: Top-3-Prioritäten", "project": "Projekt Alpha",
         "beschreibung": "Zuerst die Releases prüfen.\nDanach mit Vertrieb abstimmen: https://example.com/plan",
         "due": today.isoformat(), "prio_hoch": True},
        {"area": "Studium", "id": "9003", "content": "Übungsblatt bearbeiten", "project": "Mathe II",
         "beschreibung": "Aufgaben 3 bis 7, Abgabe im Portal.", "due": (today + timedelta(days=3)).isoformat(), "prio_hoch": True},
    ]
    events = [
        {"date": (today + timedelta(days=3)).isoformat(), "end_date": (today + timedelta(days=3)).isoformat(),
         "time": "08:00", "end_time": "08:20", "title": "Physio ZAR", "cal": 0},
        {"date": (today + timedelta(days=5)).isoformat(), "end_date": (today + timedelta(days=6)).isoformat(),
         "time": "", "end_time": "", "title": "[Sportmanagement] Grundlagen Sportbusiness · Vor Ort: Nürtingen", "cal": 0},
        {"date": (today + timedelta(days=8)).isoformat(), "end_date": (today + timedelta(days=8)).isoformat(),
         "time": "17:15", "end_time": "17:35", "title": "Physio ZAR", "cal": 0},
        {"date": (today + timedelta(days=45)).isoformat(), "end_date": (today + timedelta(days=47)).isoformat(),
         "time": "", "end_time": "", "title": "Urlaub Start", "cal": 1},
        {"date": (today + timedelta(days=100)).isoformat(), "end_date": (today + timedelta(days=100)).isoformat(),
         "time": "10:00", "end_time": "12:00", "title": "Zahnarzt", "cal": 1},
        {"date": (today + timedelta(days=11)).isoformat(), "end_date": (today + timedelta(days=11)).isoformat(),
         "time": "", "end_time": "", "title": "Tag der Deutschen Einheit", "cal": 2},
        {"date": (today + timedelta(days=400)).isoformat(), "end_date": (today + timedelta(days=400)).isoformat(),
         "time": "", "end_time": "", "title": "Beispiel-Termin in über einem Jahr", "cal": 0},
    ]
    cal_meta = [
        {"idx": 0, "name": "Standard", "ok": True},
        {"idx": 1, "name": "Privat", "ok": True},
        {"idx": 2, "name": "Feiertage in Deutschland", "ok": True},
    ]
    shows = [
        {"start": (today + timedelta(days=2)).isoformat(), "end": (today + timedelta(days=5)).isoformat(),
         "time": None, "end_time": None, "name": "Fanatics Fan Fest NYC",
         "location": "Javits Center, New York, United States", "url": "https://gradedmoments.de/", "is_de": False},
        {"start": (today + timedelta(days=17)).isoformat(), "end": None, "time": "18:00", "end_time": "22:00",
         "name": "Tradenight Der Kiosk 030", "location": "Berlin, Deutschland",
         "url": "https://gradedmoments.de/", "is_de": True},
        {"start": (today + timedelta(days=53)).isoformat(), "end": (today + timedelta(days=54)).isoformat(),
         "time": "10:00", "end_time": "18:00", "name": "Heide Cardshow",
         "location": "Lüneburg, Deutschland", "url": "https://gradedmoments.de/", "is_de": True},
    ]
    news = [
        {"name": "ZDFheute", "home": "https://www.zdfheute.de", "note": None,
         "items": [
             {"title": "Beispiel-Schlagzeile 1", "url": "https://www.zdfheute.de",
              "image": "https://placehold.co/160x160?text=ZDF"},
             {"title": "Beispiel-Schlagzeile 2", "url": "https://www.zdfheute.de",
              "image": "https://placehold.co/160x160?text=ZDF"},
             {"title": "Beispiel-Schlagzeile 3", "url": "https://www.zdfheute.de"},
             {"title": "Beispiel-Schlagzeile 4", "url": "https://www.zdfheute.de"},
             {"title": "Beispiel-Schlagzeile 5", "url": "https://www.zdfheute.de"},
         ]},
        {"name": "kicker", "home": "https://www.kicker.de", "note": None,
         "items": [{"title": f"Fußball-Meldung {i}", "url": "https://www.kicker.de"} for i in range(1, 6)]},
        {"name": "LigaInsider", "home": "https://www.ligainsider.de", "note": None,
         "items": [
             {"title": "Dompé mit schwerem Stand beim HSV",
              "url": "https://www.ligainsider.de/jean-luc-dompe_12020/dompe-mit-schwerem-stand-beim-hsv-415247/",
              "image": "https://cdn.ligainsider.de/images/player/team/minor/jean-luc-dompe-hsv-25-26-getty.jpg"},
             {"title": "Transfergerüchte: Nächster Wechsel bahnt sich an",
              "url": "https://www.ligainsider.de/beispiel-spieler_1/beispiel-artikel-2/"},
         ]},
    ]
    releases = [
        {"date": (today - timedelta(days=4)).isoformat(), "name": "2026 TOPPS Finest Baseball Cards ⚾",
         "url": "https://www.collectosk.com/de/", "checklist": "https://www.collectosk.com/de/#checklist",
         "category": "Baseball", "maker": "Topps"},
        {"date": (today + timedelta(days=2)).isoformat(), "name": "2025 TOPPS Chrome Black NFL Football Cards 🏈",
         "url": "https://www.collectosk.com/de/", "checklist": "", "category": "Am. Football", "maker": "Topps"},
        {"date": (today + timedelta(days=6)).isoformat(), "name": "2025-26 PANINI's Football EFL Soccer Cards ⚽",
         "url": "", "checklist": "", "category": "Soccer / Fußball", "maker": "Panini"},
        {"date": (today + timedelta(days=40)).isoformat(), "name": "2026 UPPER DECK Goodwin Champions Cards 🏟️",
         "url": "", "checklist": "", "category": "Sports", "maker": "Upper Deck"},
        {"date": None, "name": "2026 PANINI Flawless FIFA World Cup 2026 Soccer Cards ⚽",
         "url": "", "checklist": "", "category": "Soccer / Fußball", "maker": "Panini"},
        {"date": (today + timedelta(days=11)).isoformat(),
         "name": "2025-26 TOPPS Bundesliga Hobby Box Soccer Cards ⚽",
         "url": "", "checklist": "", "category": "Soccer / Fußball", "maker": "Topps"},
        {"date": (today + timedelta(days=14)).isoformat(),
         "name": "2025-26 PANINI Prizm Bundesliga Hobby Box ⚽",
         "url": "", "checklist": "", "category": "Soccer / Fußball", "maker": "Panini"},
        {"date": (today + timedelta(days=18)).isoformat(),
         "name": "2025-26 PANINI Bundesliga Sticker Album Kollektion",
         "url": "", "checklist": "", "category": "Soccer / Fußball", "maker": "Panini"},
        {"date": (today + timedelta(days=25)).isoformat(),
         "name": "2025-26 TOPPS UEFA Champions League Blaster Box ⚽",
         "url": "", "checklist": "", "category": "Soccer / Fußball", "maker": "Topps"},
    ]
    trello = [
        {"name": "WMF", "url": "https://trello.com/b/Lp3CQPEO/wmf", "lists": [
            {"name": "To Do", "cards": [
                {"name": "Pans Neuheiten – PIM pflegen", "due_date": today.isoformat(),
                 "due_time": None, "overdue": False, "url": "https://trello.com/c/example1"},
                {"name": "WICHTIG: Checkliste PFOA Vorgehen (BPA)",
                 "due_date": (today - timedelta(days=2)).isoformat(), "due_time": None,
                 "overdue": True, "url": "https://trello.com/c/example2"},
                {"name": "Vorbereitung Performance Meeting", "due_date": None,
                 "due_time": None, "overdue": False, "url": "https://trello.com/c/example3"},
            ]},
            {"name": "Ziele 2026", "cards": [
                {"name": "20% Pans 2.0 Strategy", "due_date": None, "due_time": None,
                 "overdue": False, "url": "https://trello.com/c/example4"},
                {"name": "25% Revenue – Business Goals", "due_date": None, "due_time": None,
                 "overdue": False, "url": "https://trello.com/c/example5"},
            ]},
        ]},
    ]
    podcast = [
        {"title": "#W30/26: Fanatics Fest war ein Statement | Der Hobby Talk", "date": today.isoformat(),
         "url": "https://dashobby.podigee.io/291-w30-26-fanatics-fest-war-ein-statement-der-hobby-talk-die-sammelkarten-news-show",
         "takeaways": [
             "Fanatics Fest New York: rund 200.000 Besucher über vier Tage – neuer Maßstab für Event-Charakter im Hobby.",
             "Shohei Ohtani: eine Bowman Super Refractor 1/1 erzielte 3,65 Mio. USD – neuer Rekord.",
             "Victor Wembanyama: mehrere Karten in der Preisspanne von 130.000–230.000 USD.",
             "Messi/Modrić/Ronaldo Triple-Autogrammkarte verkauft für 220.140 USD.",
             "Messi/Lamine-Yamal-„Badewannen“-Foto wird als offizielle Topps-Karte umgesetzt.",
             "Pokémon kündigt Set zum 30-jährigen Jubiläum an; Tech Trading verbessert Transparenz per Backlog-Tracking.",
         ]},
        {"title": "Warum manche das Hobby verlassen – und wie wir es besser machen können | Episode 181",
         "date": (today - timedelta(days=5)).isoformat(),
         "url": "https://dashobby.podigee.io/289-warum-manche-das-hobby-verlassen-und-wie-wir-es-besser-machen-konnen-episode-181",
         "takeaways": [
             "Häufigster Ausstiegsgrund: gefühlter Vertrauensverlust durch Fake-Karten und intransparente Grading-Wartezeiten.",
             "Community-Tonalität (Kommentare, Whatnot-Auktionen) schreckt viele Neueinsteiger ab.",
             "Empfehlung: kleine, lokale Cardshows als niedrigschwelliger Wiedereinstieg statt großer Online-Marktplätze.",
             "Langfristige Bindung entsteht eher über Sammelthemen mit persönlichem Bezug als über reinen Investment-Fokus.",
         ]},
        {"title": "#W29/26: Topps kämpft gegen Flipper | Der Hobby Talk", "date": (today - timedelta(days=7)).isoformat(),
         "url": "https://dashobby.podigee.io/290-w29-26-topps-kampft-gegen-flipper-der-hobby-talk-die-sammelkarten-news-show",
         "takeaways": [
             "Topps führt Kaufmengen-Limits ein, um gezielt gegen Reseller/Flipper vorzugehen.",
             "Erste Community-Reaktionen gemischt: Zustimmung zur Fairness, Kritik an Umsetzung/Kontrolle.",
             "Parallel: neue Restock-Ankündigungen sorgen erneut für kurzfristige Preisspitzen im Sekundärmarkt.",
         ]},
    ]
    weather = [
        {"date": (today + timedelta(days=i)).isoformat(), "icon": icon, "label": label, "tmax": tmax, "tmin": tmin, "rain": rain}
        for i, (icon, label, tmax, tmin, rain) in enumerate([
            ("⛅", "Teilweise bewölkt", 24, 15, 10), ("☀️", "Klar", 27, 16, 0), ("🌦️", "Leichte Schauer", 22, 14, 55),
            ("⛈️", "Gewitter", 21, 15, 80), ("🌤️", "Meist sonnig", 25, 14, 15), ("☀️", "Klar", 28, 17, 5),
            ("⛅", "Teilweise bewölkt", 26, 16, 20),
        ])
    ]
    day_focus = [
        "Heute eng: Wochenplanung Top-3-Prioritäten und das Mathe-Übungsblatt sind beide diese Woche fällig.",
        "Physio ZAR steht in 3 Tagen an, danach folgt der Vor-Ort-Termin Grundlagen Sportbusiness in Nürtingen.",
        "Die WMF-Karte „WICHTIG: Checkliste PFOA Vorgehen“ ist bereits überfällig – zuerst angehen.",
        "Nächste Cardshow in Deutschland: Tradenight Der Kiosk 030 in Berlin in 17 Tagen.",
    ]
    news_digest = {
        "sport": ["Bundesliga-Transferfenster: mehrere Wechsel bahnen sich an, u. a. bei Dompé/HSV.",
                  "Kicker berichtet über anstehende Kaderentscheidungen vor dem Saisonstart."],
        "andere": ["ZDFheute: Beispielhafte Kernthemen des Tages aus den Testdaten."],
    }
    # --- Markt: Branchen- & Lizenz-Radar ---
    def _news(t, u, d):
        return {"title": t, "url": u, "date": (today - timedelta(days=d)).isoformat()}

    industry = [
        {"name": "Cardlines", "home": "https://cardlines.com", "total": 12, "note": None, "items": [
            _news("Fanatics extends exclusive licensing deal for football trading cards",
                  "https://cardlines.com/example-1", 0),
            _news("Panini launches new Bundesliga hobby configuration for 2026",
                  "https://cardlines.com/example-2", 1),
        ]},
        {"name": "Cardboard Connection", "home": "https://www.cardboardconnection.com", "total": 12, "note": None, "items": [
            _news("2026 Topps Champions League checklist and release date revealed",
                  "https://www.cardboardconnection.com/example-3", 1),
            _news("Grading backlog at PSA grows ahead of World Cup product wave",
                  "https://www.cardboardconnection.com/example-4", 2),
        ]},
        {"name": "Google News (int.)", "home": "https://news.google.com", "total": 20,
         "note": "Stand vom letzten erfolgreichen Abruf", "items": [
            _news("Hobby box prices climb as breakers dominate release-day demand",
                  "https://news.google.com/example-5", 3),
        ]},
        {"name": "Google News (DE)", "home": "https://news.google.com", "total": 20, "note": None, "items": [
            _news("Lizenzstreit um Bundesliga-Rechte: DFL prüft neue Vergabe",
                  "https://news.google.com/example-7", 2),
            _news("Trading Cards als Anlageklasse: Sammelkartenmarkt wächst weiter",
                  "https://news.google.com/example-8", 0),
        ]},
    ]
    # Jede Zeile der Kurzfassung trägt die Meldungen, aus denen sie stammt –
    # daraus werden im Dashboard die Verweise gebaut.
    def _src(name, title, url):
        return {"name": name, "title": title, "url": url}

    industry_digest = [
        {"head": "Fanatics verlängert eine exklusive Football-Lizenz",
         "why": "Verengt den Lizenzmarkt weiter – für eigene Fußballprodukte zählt jetzt vor allem die Absicherung der Bundesliga- und WM-Rechte.",
         "links": [_src("Cardlines", "Fanatics extends exclusive licensing deal for football trading cards",
                        "https://cardlines.com/example-1")]},
        {"head": "DFL prüft eine Neuvergabe der Bundesliga-Sammelkartenrechte",
         "why": "Direkt relevant für die Planung der Hobby-Linie 2026/27; frühzeitige Gespräche und ein Szenario ohne Exklusivität wären sinnvoll.",
         "links": [_src("Google News (DE)", "Lizenzstreit um Bundesliga-Rechte: DFL prüft neue Vergabe",
                        "https://news.google.com/example-7"),
                   _src("Cardlines", "Panini launches new Bundesliga hobby configuration for 2026",
                        "https://cardlines.com/example-2")]},
        {"head": "Topps veröffentlicht Checkliste und Termin für Champions League 2026",
         "why": "Setzt das Zeitfenster für den eigenen UCL-Launch – der Hobby-Release sollte nicht in dieselbe Woche fallen.",
         "links": [_src("Cardboard Connection", "2026 Topps Champions League checklist and release date revealed",
                        "https://www.cardboardconnection.com/example-3")]},
        {"head": "Rückstau bei PSA vor der WM-Produktwelle",
         "why": "Grading-Kapazität wird zum Nadelöhr für den Sekundärmarkt; ein Grading-Partnerangebot zum Launch könnte sich differenzierend auswirken.",
         "links": [_src("Cardboard Connection", "Grading backlog at PSA grows ahead of World Cup product wave",
                        "https://www.cardboardconnection.com/example-4")]},
        {"head": "Hobby-Box-Preise steigen, Breaker dominieren den Release-Tag",
         "why": "Spricht für strengere Allokation an den Fachhandel und für eine Konfiguration, die Einzelsammler gegenüber Breakern nicht benachteiligt.",
         "links": []},
    ]

    events.sort(key=lambda e: (e["date"], e["time"]))
    return (tasks, 2, events, shows, news, releases, trello, podcast, weather, day_focus,
            news_digest, cal_meta, industry, industry_digest)


# ------------------------------------------------------------------ HTML ---
# Farbe je Kalenderquelle (Reihenfolge ICS_URL, dann ICS_URLS) – feste Zuordnung
# per Index, damit eine Farbe stabil bleibt, auch wenn ein anderer Kalender mal
# ausfällt oder eine neue Adresse dazukommt (Farbe hängt nicht von der Anzahl ab).
CAL_PALETTE = ["#2a78d6", "#d64545", "#0f9d58", "#e0932a", "#1a9ab0", "#a34fd6", "#c2398a", "#6b7280"]


def cal_color(idx):
    return CAL_PALETTE[(idx or 0) % len(CAL_PALETTE)]


def _hex_to_rgba(hexcolor, alpha):
    h = hexcolor.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _countdown_target(iso_date, time_str=None, end_of_day=False):
    """Baut ein zeitzonenbewusstes datetime-Ziel für eine Countdown-Kachel."""
    d = date.fromisoformat(iso_date)
    if time_str:
        hh, mm = (int(x) for x in time_str.split(":")[:2])
        return datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ)
    if end_of_day:
        return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=TZ)
    return datetime(d.year, d.month, d.day, 0, 0, tzinfo=TZ)


def ev_label(e):
    """Titel eines Termins, bei mehrtägigen Terminen mit Tag-X/Y-Hinweis."""
    total = e.get("multi_total", 1)
    if total > 1:
        return f'{e["title"]} · Tag {e["multi_day"]}/{total}'
    return e["title"]


def month_grid_html(y, m, ev_by_date, today):
    first = date(y, m, 1)
    nxt = (first.replace(day=28) + timedelta(days=7)).replace(day=1)
    d = first - timedelta(days=first.weekday())
    end = nxt + timedelta(days=(7 - nxt.weekday()) % 7)
    cells = []
    while d < end:
        iso = d.isoformat()
        cls = "mday"
        if d.month != m: cls += " out"
        if d == today: cls += " today"
        num = f"{d.day:02d}.{d.month:02d}." if d.month != m else str(d.day)
        chips = ""
        for e in ev_by_date.get(iso, []):
            past = " past" if iso < today.isoformat() else ""
            label = (e["time"] + " " if e["time"] else "") + ev_label(e)
            color = cal_color(e.get("cal"))
            chips += (f'<div class="chip{past}" data-cal="{e.get("cal", 0)}" title="{esc(label)}" '
                      f'style="background:{_hex_to_rgba(color, 0.14)};border-left-color:{color};">{esc(label)}</div>')
        cells.append(f'<div class="{cls}"><div class="num">{num}</div>{chips}</div>')
        d += timedelta(days=1)
    head = "".join(f"<div>{w}</div>" for w in WD)
    return f'<div class="month-head">{head}</div><div class="month-grid">{"".join(cells)}</div>'


def month_agenda_html(y, m, events, today):
    """Chronologische Terminliste für genau einen Monat (Terminliste-Reiter) –
    im Gegensatz zu month_grid_html (Kalender-Raster) eine flache Liste,
    mehrtägige Termine als eine Zeile mit Datumsspanne (wie zuvor bei 'Jahr')."""
    key_events = [e for e in events if e["date"][:7] == f"{y:04d}-{m:02d}"]
    if not key_events:
        return '<div class="empty">Keine Termine in diesem Monat.</div>'
    rows = []
    for e in key_events:
        d = date.fromisoformat(e["date"])
        d_end = date.fromisoformat(e.get("end_date", e["date"]))
        tstr = f'{e["time"]}–{e["end_time"]}' if e["time"] else "ganztägig"
        if d_end == d:
            dstr = f"{WD[d.weekday()]}, {d.day:02d}.{d.month:02d}."
        elif d_end.month == d.month and d_end.year == d.year:
            dstr = f"{d.day:02d}.–{d_end.day:02d}.{d_end.month:02d}."
        else:
            dstr = f"{d.day:02d}.{d.month:02d}.–{d_end.day:02d}.{d_end.month:02d}."
        color = cal_color(e.get("cal"))
        rows.append(
            f'<div class="event" data-cal="{e.get("cal", 0)}"><span class="d" style="background:{color}"></span>'
            f'<span class="time">{dstr} · {tstr}</span><span>{esc(e["title"])}</span></div>')
    return "".join(rows)


def fmt_show_date(s):
    ds = date.fromisoformat(s["start"])
    de_ = date.fromisoformat(s["end"]) if s.get("end") else None
    if de_ and de_ != ds:
        if ds.month == de_.month and ds.year == de_.year:
            return f"{ds.day:02d}.–{de_.day:02d}.{de_.month:02d}.{de_.year}"
        return f"{ds.day:02d}.{ds.month:02d}.–{de_.day:02d}.{de_.month:02d}.{de_.year}"
    base = f"{WD[ds.weekday()]}, {ds.day:02d}.{ds.month:02d}.{ds.year}"
    if s.get("time"):
        base += f" · {s['time']}"
        if s.get("end_time"):
            base += f"–{s['end_time']}"
        base += " Uhr"
    return base


# ------------------------------------------------------ Italienisch-Kurs ---
# Der Lernstoff liegt in italian_course.py (reine Datendatei). Fehlt sie oder
# ist sie fehlerhaft, bleibt der Reiter leer – der Dashboard-Bau läuft weiter.
try:
    from italian_course import kurs_daten as _it_kurs_daten
    ITALIAN_COURSE = _it_kurs_daten()
except Exception as _it_err:            # pragma: no cover - Schutzschicht
    print(f"Hinweis: Italienisch-Kurs nicht geladen ({_it_err}).")
    ITALIAN_COURSE = {"bloecke": [], "lektionen": [], "aussprache": []}


# --- Lernstand über alle Geräte ----------------------------------------------
# Der Fortschritt liegt weiterhin im Browser (schnell, offline nutzbar), wird
# aber zusätzlich in cache/italiano.json gehalten. Damit sieht das Handy, was
# am Rechner gelernt wurde. Weg: Der Browser stößt den Workflow mit seinem
# Stand an (der vorhandene Actions-Token genügt, kein neues Geheimnis), der
# Lauf führt beide Stände zusammen und backt das Ergebnis in die Seite.
IT_KARTE_ID = re.compile(r"^[WS][0-9]{1,3}-[0-9]{1,3}$")
IT_DATUM = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
IT_STAND_TXT = re.compile(r"^[0-9.: ]{0,20}$")
IT_MAX_KARTEN = 4000


def _it_leer():
    return {"done": [], "karten": {}, "serie": {"n": 0, "best": 0, "letzter": ""},
            "tag": {"d": "", "lekt": 0, "karten": 0}, "richtung": "it"}


def _it_zahl(v, lo, hi):
    try:
        n = int(v)
    except Exception:
        return lo
    return max(lo, min(hi, n))


def _it_datum(v):
    v = str(v or "")
    return v if IT_DATUM.match(v) else ""


def it_clean(raw):
    """Einen Lernstand auf das erlaubte Format eindampfen.

    Diese Daten kommen aus dem Browser und werden später in die Seite gebacken.
    Deshalb bleiben nur bekannte Schlüssel übrig, und zwar ausschließlich als
    Zahlen und ISO-Datumsangaben – so kann kein fremder Text in die Seite
    gelangen. Rückgabe None heißt: unlesbar, bitte ignorieren.
    """
    if isinstance(raw, (str, bytes)):
        try:
            raw = json.loads(raw)
        except Exception:
            return None
    if not isinstance(raw, dict):
        return None
    gueltig = {l.get("nr") for l in (ITALIAN_COURSE.get("lektionen") or [])}
    done = []
    roh_done = raw.get("done")
    if isinstance(roh_done, list):
        for x in roh_done[:500]:
            try:
                n = int(x)
            except Exception:
                continue
            if n in gueltig and n not in done:
                done.append(n)
    karten = {}
    roh_k = raw.get("karten")
    if isinstance(roh_k, dict):
        for k in sorted(str(x) for x in roh_k.keys())[:IT_MAX_KARTEN]:
            if not IT_KARTE_ID.match(k):
                continue
            v = roh_k.get(k)
            if not isinstance(v, dict):
                continue
            d = _it_datum(v.get("d"))
            if not d:
                continue
            karten[k] = {"f": _it_zahl(v.get("f"), 0, 5), "d": d}
    serie = raw.get("serie") if isinstance(raw.get("serie"), dict) else {}
    tag = raw.get("tag") if isinstance(raw.get("tag"), dict) else {}
    return {
        "done": sorted(done),
        "karten": karten,
        "serie": {"n": _it_zahl(serie.get("n"), 0, 9999),
                  "best": _it_zahl(serie.get("best"), 0, 9999),
                  "letzter": _it_datum(serie.get("letzter"))},
        "tag": {"d": _it_datum(tag.get("d")),
                "lekt": _it_zahl(tag.get("lekt"), 0, 999),
                "karten": _it_zahl(tag.get("karten"), 0, 9999)},
        "richtung": "de" if raw.get("richtung") == "de" else "it",
    }


def it_merge(alt, neu):
    """Zwei Lernstände vereinigen – nichts geht verloren.

    Absichtlich keine Regel "der letzte gewinnt": wenn Rechner und Handy
    unabhängig voneinander gelernt haben, sollen beide Fortschritte erhalten
    bleiben. `neu` gilt als der frischere Stand und entscheidet nur bei
    echtem Gleichstand.
    """
    a = it_clean(alt) or _it_leer()
    b = it_clean(neu) or _it_leer()

    karten = {}
    for k in sorted(set(a["karten"]) | set(b["karten"])):
        x, y = a["karten"].get(k), b["karten"].get(k)
        if not x:
            karten[k] = y
        elif not y:
            karten[k] = x
        elif y["f"] != x["f"]:
            # Höheres Leitner-Fach heißt: auf dem anderen Gerät schon besser
            # gelernt. Das gewinnt, sonst würde Wiederholtes zurückfallen.
            karten[k] = y if y["f"] > x["f"] else x
        else:
            karten[k] = y if y["d"] >= x["d"] else x

    sa, sb = a["serie"], b["serie"]
    if sa["letzter"] == sb["letzter"]:
        s_n, s_letzt = max(sa["n"], sb["n"]), sa["letzter"]
    elif sb["letzter"] > sa["letzter"]:
        s_n, s_letzt = sb["n"], sb["letzter"]
    else:
        s_n, s_letzt = sa["n"], sa["letzter"]

    ta, tb = a["tag"], b["tag"]
    if ta["d"] == tb["d"]:
        tag = {"d": ta["d"], "lekt": max(ta["lekt"], tb["lekt"]),
               "karten": max(ta["karten"], tb["karten"])}
    else:
        tag = dict(tb if tb["d"] > ta["d"] else ta)

    return {
        "done": sorted(set(a["done"]) | set(b["done"])),
        "karten": karten,
        "serie": {"n": s_n, "best": max(sa["best"], sb["best"], s_n), "letzter": s_letzt},
        "tag": tag,
        "richtung": (b if neu else a)["richtung"],
    }


def it_sync(eingang):
    """Gespeicherten Lernstand laden, einen eingegangenen einmischen, ablegen.

    Gibt den Stand zurück, der in die Seite gebacken wird.
    """
    gespeichert = load_cache("italiano") or {}
    stand = it_clean(gespeichert) or _it_leer()
    zeit = str(gespeichert.get("stand") or "")
    stand["stand"] = zeit if IT_STAND_TXT.match(zeit) else ""

    eingang = (eingang or "").strip()
    if not eingang:
        return stand
    neu = it_clean(eingang)
    if neu is None:
        print("Hinweis: Italienisch-Stand aus dem Browser war unlesbar – ignoriert.")
        return stand
    zusammen = it_merge(stand, neu)
    zusammen["stand"] = datetime.now(TZ).strftime("%d.%m.%Y %H:%M")
    save_cache("italiano", zusammen)
    print(f"Italienisch-Stand abgeglichen: {len(zusammen['done'])} Lektionen, "
          f"{len(zusammen['karten'])} Karten, Serie {zusammen['serie']['n']}.")
    return zusammen


# CSS und JS des Reiters stehen absichtlich als eigene Klartext-Bausteine hier
# und nicht in der großen f-String-Vorlage von build_html: dort müsste jede
# Klammer verdoppelt werden, was bei diesem Umfang unweigerlich zu Fehlern
# führt. Sie werden unten als {IT_CSS} bzw. {IT_JS} eingesetzt.
IT_CSS = '''
  /* ---------------- Italienisch: Lernbereich ---------------- */
  .itnudge { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px;
             border-left: 3px solid var(--italiano); padding: 14px 16px; margin-bottom: 20px;
             display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
  .itnudge .n-flame { font-size: 26px; line-height: 1; }
  .itnudge .n-main { flex: 1 1 260px; min-width: 0; }
  .itnudge .n-head { font-size: 14px; font-weight: 650; }
  .itnudge .n-sub { font-size: 12.5px; color: var(--text-secondary); margin-top: 3px; }
  .itnudge .n-satz { font-size: 12.5px; color: var(--text-secondary); margin-top: 6px; font-style: italic; }
  .itnudge.done { border-left-color: var(--good); }
  .itbtn { padding: 8px 16px; font-size: 13px; font-weight: 650; border-radius: 99px; border: 1px solid var(--italiano);
           background: var(--italiano); color: #fff; cursor: pointer; white-space: nowrap; }
  .itbtn:hover { filter: brightness(1.08); }
  .itbtn.ghost { background: var(--surface-1); color: var(--text-secondary); border-color: var(--border); }
  .itbtn.ghost:hover { color: var(--italiano); border-color: var(--italiano); filter: none; }
  .itbtn:disabled { opacity: .45; cursor: default; filter: none; }
  .itbtn.small { padding: 5px 12px; font-size: 12px; }

  .ittop { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .itstat { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 13px 15px; }
  .itstat .l { font-size: 11.5px; color: var(--muted); margin-bottom: 5px; }
  .itstat .v { font-size: 24px; font-weight: 650; line-height: 1.1; font-variant-numeric: tabular-nums; }
  .itstat .s { font-size: 11.5px; color: var(--text-secondary); margin-top: 3px; }

  .itcards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; margin-bottom: 16px; }
  .itcard { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px;
            border-top: 3px solid var(--italiano); display: flex; flex-direction: column; gap: 8px; }
  .itcard.ok { border-top-color: var(--good); }
  .itcard .c-kicker { font-size: 11.5px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .itcard .c-title { font-size: 15px; font-weight: 650; }
  .itcard .c-text { font-size: 13px; color: var(--text-secondary); }
  .itcard .c-act { margin-top: 4px; display: flex; gap: 8px; flex-wrap: wrap; }

  .itbar { height: 7px; border-radius: 99px; background: var(--hairline); overflow: hidden; margin-top: 8px; }
  .itbar > i { display: block; height: 100%; background: var(--italiano); border-radius: 99px; transition: width .3s; }
  .itbar.good > i { background: var(--good); }

  .itbadges { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
  .itbadge { font-size: 12px; font-weight: 600; padding: 5px 11px; border-radius: 99px; border: 1px dashed var(--border);
             color: var(--muted); background: var(--surface-1); }
  .itbadge.got { border-style: solid; border-color: var(--italiano); color: #fff; background: var(--italiano); }

  .itsatz { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 16px; }
  .itsatz .l { font-size: 11.5px; color: var(--muted); margin-bottom: 6px; }
  .itsatz .it { font-size: 17px; font-weight: 600; }
  .itsatz .de { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

  details.itblock { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 10px; }
  details.itblock > summary { padding: 13px 16px; cursor: pointer; font-size: 14px; font-weight: 650; list-style: none; }
  details.itblock > summary::-webkit-details-marker { display: none; }
  details.itblock > summary:hover { color: var(--italiano); }
  details.itblock .b-claim { font-size: 12.5px; font-weight: 400; color: var(--text-secondary); margin-top: 3px; }
  details.itblock .b-ziel { font-size: 12.5px; color: var(--text-secondary); padding: 0 16px 10px; }
  .itlist { border-top: 1px solid var(--hairline); }
  .itrow { display: flex; align-items: center; gap: 12px; padding: 10px 16px; border-bottom: 1px solid var(--hairline);
           cursor: pointer; }
  .itrow:last-child { border-bottom: none; }
  .itrow:hover { background: rgba(0,0,0,0.03); }
  @media (prefers-color-scheme: dark) { .itrow:hover { background: rgba(255,255,255,0.04); } }
  .itrow .r-nr { font-size: 12px; color: var(--muted); width: 26px; flex: none; font-variant-numeric: tabular-nums; }
  .itrow .r-mark { width: 18px; flex: none; text-align: center; font-size: 13px; }
  .itrow .r-body { flex: 1 1 auto; min-width: 0; }
  .itrow .r-title { display: block; font-size: 13.5px; font-weight: 600; }
  .itrow .r-ziel { display: block; font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
  .itrow.done .r-title { color: var(--done-ink); font-weight: 500; }
  .itrow.next { background: rgba(31,158,90,0.09); }
  .itrow .r-tag { font-size: 10.5px; font-weight: 650; padding: 2px 7px; border-radius: 4px; background: var(--italiano);
                  color: #fff; flex: none; white-space: nowrap; }
  .itrow .r-tag.ms { background: var(--warn); }

  .itsearch { width: 100%; max-width: 320px; padding: 8px 12px; font-size: 13px; border-radius: 8px;
              border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary); margin-bottom: 12px; }
  .itvoc { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
  .itvline { display: flex; align-items: center; gap: 10px; padding: 9px 14px; border-bottom: 1px solid var(--hairline); }
  .itvline:last-child { border-bottom: none; }
  .itvline .v-it { font-size: 13.5px; font-weight: 600; flex: 1 1 45%; min-width: 0; }
  .itvline .v-de { font-size: 13px; color: var(--text-secondary); flex: 1 1 45%; min-width: 0; }
  .itvline .v-box { font-size: 10.5px; color: var(--muted); flex: none; font-variant-numeric: tabular-nums; }
  .say { border: none; background: none; cursor: pointer; font-size: 14px; padding: 2px 4px; color: var(--text-secondary);
         flex: none; border-radius: 6px; line-height: 1; }
  .say:hover { color: var(--italiano); background: var(--hairline); }

  .itpron { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 6px 14px; margin-top: 8px; }
  .itpron div { font-size: 12.5px; color: var(--text-secondary); }
  .itpron b { color: var(--text-primary); font-weight: 650; }

  /* Lektionsablauf: liegt als Ebene über der Seite, damit der Fokus wirklich
     auf der Lektion liegt und nichts anderes ablenkt. */
  .itover { position: fixed; inset: 0; background: rgba(0,0,0,0.45); z-index: 90; display: none;
            padding: 20px; overflow-y: auto; }
  .itover.on { display: block; }
  .itsheet { max-width: 660px; margin: 0 auto; background: var(--page); border: 1px solid var(--border);
             border-radius: 14px; padding: 20px; }
  .itsheet .s-head { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 4px; }
  .itsheet .s-kicker { font-size: 11.5px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .itsheet .s-title { font-size: 18px; font-weight: 650; margin-top: 2px; }
  .itsheet .s-close { margin-left: auto; border: none; background: none; font-size: 20px; cursor: pointer;
                      color: var(--muted); line-height: 1; padding: 2px 6px; }
  .itsheet .s-close:hover { color: var(--bad-text); }
  .itsteps { display: flex; gap: 5px; margin: 12px 0 16px; }
  .itsteps i { flex: 1 1 0; height: 4px; border-radius: 99px; background: var(--hairline); }
  .itsteps i.on { background: var(--italiano); }
  .itsheet .s-goal { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }
  .itsheet .s-body { min-height: 180px; }
  .itsheet .s-foot { display: flex; gap: 8px; align-items: center; margin-top: 18px; flex-wrap: wrap; }
  .itsheet .s-foot .sp { margin-left: auto; font-size: 12px; color: var(--muted); }
  .itsheet h3 { font-size: 14px; font-weight: 650; margin-bottom: 10px; }

  .itpair { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--hairline); }
  .itpair:last-child { border-bottom: none; }
  .itpair .p-it { font-size: 14.5px; font-weight: 600; flex: 1 1 45%; }
  .itpair .p-de { font-size: 13px; color: var(--text-secondary); flex: 1 1 45%; }
  .itgram { background: var(--surface-1); border: 1px solid var(--border); border-left: 3px solid var(--italiano);
            border-radius: 10px; padding: 14px 16px; }
  .itgram .g-t { font-size: 14px; font-weight: 650; margin-bottom: 6px; }
  .itgram .g-x { font-size: 13.5px; color: var(--text-secondary); line-height: 1.55; }

  .itq { }
  .itq .q-n { font-size: 11.5px; color: var(--muted); margin-bottom: 6px; }
  .itq .q-word { font-size: 20px; font-weight: 650; margin-bottom: 14px; }
  .itopt { display: grid; gap: 8px; }
  .itopt button { text-align: left; padding: 11px 14px; font-size: 13.5px; border-radius: 10px;
                  border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary); cursor: pointer; }
  .itopt button:hover { border-color: var(--italiano); }
  .itopt button.right { border-color: var(--good); background: rgba(12,163,12,0.12); font-weight: 650; }
  .itopt button.wrong { border-color: var(--bad); background: rgba(208,59,59,0.12); }
  .itopt button:disabled { cursor: default; }
  .itfeed { font-size: 13px; margin-top: 12px; min-height: 20px; color: var(--text-secondary); }
  .itfeed.ok { color: var(--good-text); font-weight: 600; }
  .itfeed.no { color: var(--bad-text); font-weight: 600; }

  .ittask { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
  .ittask .t-l { font-size: 11.5px; color: var(--muted); margin-bottom: 6px; }
  .ittask .t-x { font-size: 14.5px; line-height: 1.5; }
  .itdone { text-align: center; padding: 18px 0; }
  .itdone .d-ic { font-size: 38px; }
  .itdone .d-t { font-size: 17px; font-weight: 650; margin-top: 8px; }
  .itdone .d-s { font-size: 13px; color: var(--text-secondary); margin-top: 6px; }

  /* Karteikasten */
  .ittrain { text-align: center; }
  .ittrain .tr-front { font-size: 26px; font-weight: 650; margin: 14px 0 6px; }
  .ittrain .tr-dir { font-size: 11.5px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .ittrain .tr-back { font-size: 17px; color: var(--text-secondary); min-height: 26px; margin-bottom: 6px; }
  .ittrain .tr-src { font-size: 11.5px; color: var(--muted); }
  .ittrain .tr-act { display: flex; gap: 8px; justify-content: center; margin-top: 18px; flex-wrap: wrap; }
  .itboxes { display: flex; gap: 6px; justify-content: center; margin-top: 14px; flex-wrap: wrap; }
  .itboxes span { font-size: 11px; color: var(--text-secondary); background: var(--surface-1); border: 1px solid var(--border);
                  border-radius: 99px; padding: 3px 9px; font-variant-numeric: tabular-nums; }
  .itempty { font-size: 13px; color: var(--muted); padding: 18px 0; text-align: center; }
  /* Eine ruhige Zeile: sie sagt, ob der Stand über die Geräte hinweg sitzt. */
  .itsync { font-size: 12px; color: var(--muted); margin: -6px 0 14px; min-height: 1em; }
  .itsync.warn { color: var(--bad-text); }
'''

# Der Lernbereich läuft vollständig im Browser: kein Netz, kein API-Schlüssel,
# keine Kosten. Der Fortschritt liegt in localStorage und übersteht die
# 30-Minuten-Neubauten. Zusätzlich wird er über den Workflow mit
# cache/italiano.json abgeglichen, damit Rechner und Handy denselben Stand
# sehen (siehe it_sync oben).
IT_JS = '''
  // ------------------------------------------------------- Italienisch ---
  (function () {
    const C = window.ITCORSO;
    if (!C || !Array.isArray(C.lektionen) || !C.lektionen.length) return;
    const LK = C.lektionen, BL = C.bloecke || [], PRON = C.aussprache || [];
    const KEY = 'it_progress_v1';
    // Leitner-Kasten: Fach 0 kommt morgen wieder, Fach 5 erst in fünf Wochen.
    const FACH_TAGE = [1, 2, 4, 8, 16, 35];
    const ZIEL_KARTEN = 12;   // Tagesziel, wenn gerade nichts fällig ist

    function heute() {
      const d = new Date();
      return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') +
             '-' + String(d.getDate()).padStart(2, '0');
    }
    function plusTage(n) {
      const d = new Date();
      d.setDate(d.getDate() + n);
      return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') +
             '-' + String(d.getDate()).padStart(2, '0');
    }
    function tageDiff(a, b) {
      return Math.round((new Date(b + 'T00:00:00') - new Date(a + 'T00:00:00')) / 86400000);
    }

    function leer() {
      return { done: [], karten: {}, serie: { n: 0, best: 0, letzter: '' },
               tag: { d: '', lekt: 0, karten: 0 }, richtung: 'it' };
    }
    // Jeden Stand – ob aus dem Browser oder vom Server – auf die gleiche Form
    // bringen. Danach darf der Rest des Codes ohne Prüfungen darauf zugreifen.
    function formen(x) {
      const o = leer();
      if (!x || typeof x !== 'object') return o;
      if (Array.isArray(x.done)) {
        x.done.forEach(n => { n = Number(n); if (n && o.done.indexOf(n) === -1) o.done.push(n); });
      }
      if (x.karten && typeof x.karten === 'object') {
        Object.keys(x.karten).forEach(k => {
          const v = x.karten[k];
          if (v && typeof v === 'object' && v.d) o.karten[k] = { f: v.f | 0, d: String(v.d) };
        });
      }
      const s = x.serie || {}, t = x.tag || {};
      o.serie = { n: s.n | 0, best: s.best | 0, letzter: String(s.letzter || '') };
      o.tag = { d: String(t.d || ''), lekt: t.lekt | 0, karten: t.karten | 0 };
      o.richtung = x.richtung === 'de' ? 'de' : 'it';
      return o;
    }

    // Zwei Stände vereinigen. Bewusst kein "der letzte gewinnt": wenn auf
    // Rechner und Handy unabhängig gelernt wurde, bleibt beides erhalten.
    // b ist der frischere Stand und entscheidet nur bei echtem Gleichstand.
    // Diese Regeln stehen genauso in it_merge() im Python-Teil.
    // (Nicht "mische" nennen – das ist weiter unten das Mischen der Quiz-Antworten.)
    function vereinen(a, b) {
      const done = a.done.slice();
      b.done.forEach(n => { if (done.indexOf(n) === -1) done.push(n); });
      done.sort((x, y) => x - y);
      const karten = {};
      Object.keys(a.karten).concat(Object.keys(b.karten)).forEach(k => {
        if (karten[k]) return;
        const x = a.karten[k], y = b.karten[k];
        if (!x) { karten[k] = y; return; }
        if (!y) { karten[k] = x; return; }
        // Höheres Leitner-Fach heißt: auf dem anderen Gerät besser gelernt.
        if (y.f !== x.f) { karten[k] = y.f > x.f ? y : x; return; }
        karten[k] = y.d >= x.d ? y : x;
      });
      const sa = a.serie, sb = b.serie;
      let sn, sl;
      if (sa.letzter === sb.letzter) { sn = Math.max(sa.n, sb.n); sl = sa.letzter; }
      else if (sb.letzter > sa.letzter) { sn = sb.n; sl = sb.letzter; }
      else { sn = sa.n; sl = sa.letzter; }
      const ta = a.tag, tb = b.tag;
      const tag = ta.d === tb.d
        ? { d: ta.d, lekt: Math.max(ta.lekt, tb.lekt), karten: Math.max(ta.karten, tb.karten) }
        : Object.assign({}, tb.d > ta.d ? tb : ta);
      return { done: done, karten: karten,
               serie: { n: sn, best: Math.max(sa.best, sb.best, sn), letzter: sl },
               tag: tag, richtung: b.richtung };
    }

    // Fingerabdruck zum Vergleich: Was der Server hat, gegen das, was hier
    // liegt. Die Blickrichtung bleibt außen vor – die ist Gerätesache.
    function abdruck(x) {
      const k = {};
      Object.keys(x.karten).sort().forEach(id => { k[id] = [x.karten[id].f, x.karten[id].d]; });
      return JSON.stringify([x.done.slice().sort((a, b) => a - b), k,
                             [x.serie.n, x.serie.best, x.serie.letzter],
                             [x.tag.d, x.tag.lekt, x.tag.karten]]);
    }

    let P;
    try { P = formen(JSON.parse(localStorage.getItem(KEY) || 'null')); }
    catch (e) { P = leer(); }

    // --- Server-Stand einmischen -------------------------------------------
    const fern = window.ITSTAND && typeof window.ITSTAND === 'object' ? window.ITSTAND : null;
    const fernZeit = fern ? String(fern.stand || '') : '';
    // Der Vergleich läuft vor dem Tageswechsel weiter unten: ein neuer Tag
    // allein ist kein Grund, den Server anzufunken.
    const F = formen(fern);
    if (fern) P = vereinen(F, P);   // der lokale Stand gilt als der frischere
    let nachzutragen = abdruck(P) !== abdruck(F);
    if (P.tag.d !== heute()) P.tag = { d: heute(), lekt: 0, karten: 0 };
    // Was vom Server dazukam, gehört sofort in den Speicher dieses Geräts –
    // sonst wäre es nach dem Wegklicken wieder weg. Bewusst ohne Anstoß: der
    // folgt unten nur, wenn sich die Stände wirklich unterscheiden.
    merken();

    function merken() {
      try { localStorage.setItem(KEY, JSON.stringify(P)); } catch (e) {}
    }

    function sichern() {
      merken();
      syncAnstossen();
    }

    // --- Hochladen ---------------------------------------------------------
    // Der Browser darf nicht ins Repo schreiben. Er stößt deshalb denselben
    // Workflow an wie der ⟳-Knopf und übergibt seinen Stand als Eingabe; das
    // Zusammenführen und Ablegen passiert serverseitig.
    const itcfg = window.DASHCFG || {};
    const SYNC_GRENZE = 60000;    // Sicherheitsabstand zum Limit der Eingaben
    const SYNC_ENTPRELLEN = 5000; // erst sammeln, dann einmal senden
    const SYNC_ABSTAND = 25000;   // nie mehr als ein Lauf je 25 Sekunden
    const SYNC_MAX = 6;           // Schutz gegen dauerhaft erfolgloses Senden
    let syncTimer = null, syncLaeuft = false, syncOffen = false;
    let syncVersuche = 0, syncZuletzt = 0;

    function syncSage(text, warnen) {
      const el = document.getElementById('itsync');
      if (!el) return;
      el.textContent = text || '';
      el.classList.toggle('warn', !!warnen);
    }

    function nutzlast() {
      const s = JSON.stringify(P);
      if (s.length <= SYNC_GRENZE) return s;
      // Notbremse: Lektionen und Serie kommen auch ohne Karteikasten durch.
      return JSON.stringify(Object.assign({}, P, { karten: {} }));
    }

    async function syncSenden() {
      clearTimeout(syncTimer);
      syncTimer = null;
      if (!itcfg.rt) {
        syncSage('Fortschritt bleibt auf diesem Gerät – kein Zugriffsschlüssel in der Seite.', true);
        return;
      }
      if (syncLaeuft) { syncOffen = true; return; }
      if (syncVersuche >= SYNC_MAX) return;
      syncLaeuft = true;
      syncVersuche++;
      syncZuletzt = Date.now();
      syncSage('Fortschritt wird für alle Geräte gesichert …');
      try {
        const r = await fetch('https://api.github.com/repos/' + itcfg.repo +
                              '/actions/workflows/update.yml/dispatches', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + itcfg.rt,
                     'Accept': 'application/vnd.github+json' },
          body: JSON.stringify({ ref: 'main', inputs: { it_progress: nutzlast() } })
        });
        if (r.status === 204) {
          syncVersuche = 0;
          nachzutragen = false;
          syncSage('Fortschritt gesichert – andere Geräte sehen ihn beim nächsten Laden.');
        } else {
          syncSage('Abgleich nicht möglich (' + r.status + '). Fortschritt bleibt hier gespeichert.', true);
        }
      } catch (e) {
        syncSage('Kein Netz für den Abgleich. Fortschritt bleibt hier gespeichert.', true);
      }
      syncLaeuft = false;
      if (syncOffen) { syncOffen = false; syncAnstossen(); }
    }

    function syncAnstossen() {
      if (!itcfg.rt || syncVersuche >= SYNC_MAX) return;
      nachzutragen = true;
      // Sofort Bescheid geben, nicht erst wenn der Aufruf rausgeht – sonst
      // wirkt die Zeile in den ersten Sekunden wie eingeschlafen.
      syncSage('Fortschritt wird für alle Geräte gesichert …');
      clearTimeout(syncTimer);
      const warten = Math.max(SYNC_ENTPRELLEN, SYNC_ABSTAND - (Date.now() - syncZuletzt));
      syncTimer = setTimeout(syncSenden, warten);
    }

    // Wer die Seite wegklickt, soll nichts verlieren: was noch wartet, geht
    // sofort raus. Bleibt doch etwas liegen, holt es der nächste Aufruf nach,
    // weil dann der eingebackene Stand vom lokalen abweicht.
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden' && syncTimer) syncSenden();
    });

    // --- Aussprache über die Sprachausgabe des Browsers -------------------
    let stimmen = [];
    function ladeStimmen() {
      try { stimmen = window.speechSynthesis.getVoices() || []; } catch (e) { stimmen = []; }
    }
    if (window.speechSynthesis) {
      ladeStimmen();
      window.speechSynthesis.addEventListener('voiceschanged', ladeStimmen);
    }
    function sprich(text) {
      if (!window.speechSynthesis || !text) return;
      try {
        const u = new SpeechSynthesisUtterance(String(text).replace(/\\s*\\/\\s*/g, ', '));
        u.lang = 'it-IT';
        u.rate = 0.9;
        const v = stimmen.find(s => /^it/i.test(s.lang));
        if (v) u.voice = v;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(u);
      } catch (e) {}
    }
    const hatTon = !!window.speechSynthesis;
    function tonKnopf(text) {
      if (!hatTon) return '';
      return '<button class="say" data-say="' + esc(text) + '" title="Aussprache anhören">🔊</button>';
    }

    function esc(s) {
      return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // --- Kartenverwaltung -------------------------------------------------
    function kartenAnlegen(l) {
      (l.woerter || []).forEach((w, i) => {
        const id = 'W' + l.nr + '-' + i;
        if (!P.karten[id]) P.karten[id] = { f: 0, d: plusTage(1) };
      });
      (l.saetze || []).forEach((s, i) => {
        const id = 'S' + l.nr + '-' + i;
        if (!P.karten[id]) P.karten[id] = { f: 0, d: plusTage(2) };
      });
    }
    function kartePaar(id) {
      const m = /^([WS])(\\d+)-(\\d+)$/.exec(id);
      if (!m) return null;
      const l = LK.find(x => x.nr === Number(m[2]));
      if (!l) return null;
      const arr = m[1] === 'W' ? l.woerter : l.saetze;
      const p = arr && arr[Number(m[3])];
      if (!p) return null;
      return { it: p[0], de: p[1], lekt: l, art: m[1] === 'W' ? 'Wort' : 'Satz' };
    }
    function faellige() {
      const h = heute();
      return Object.keys(P.karten).filter(id => {
        const k = P.karten[id];
        return k && k.d <= h && kartePaar(id);
      });
    }
    function fachZaehlung() {
      const z = [0, 0, 0, 0, 0, 0];
      Object.keys(P.karten).forEach(id => {
        const k = P.karten[id];
        if (k && kartePaar(id)) z[Math.min(5, Math.max(0, k.f | 0))]++;
      });
      return z;
    }

    // --- Fortschritt und Serie -------------------------------------------
    function erledigt(nr) { return P.done.indexOf(nr) !== -1; }
    function naechste() {
      for (let i = 0; i < LK.length; i++) if (!erledigt(LK[i].nr)) return LK[i];
      return LK[LK.length - 1];
    }
    function zielErreicht() {
      if (P.tag.lekt > 0) return true;
      if (P.tag.karten >= ZIEL_KARTEN) return true;
      return P.tag.karten > 0 && faellige().length === 0;
    }
    function serieBuchen() {
      if (!zielErreicht()) return;
      const h = heute();
      if (P.serie.letzter === h) return;
      P.serie.n = (P.serie.letzter && tageDiff(P.serie.letzter, h) === 1) ? P.serie.n + 1 : 1;
      P.serie.letzter = h;
      if (P.serie.n > (P.serie.best || 0)) P.serie.best = P.serie.n;
    }
    function serieAktuell() {
      // Ein ausgelassener Tag setzt zurück – aber erst ab dem Folgetag, damit
      // heute noch alles rettbar ist.
      if (!P.serie.letzter) return 0;
      const d = tageDiff(P.serie.letzter, heute());
      return d <= 1 ? (P.serie.n || 0) : 0;
    }
    function blockInfo(nr) {
      const l = LK.filter(x => x.block === nr);
      const f = l.filter(x => erledigt(x.nr)).length;
      return { gesamt: l.length, fertig: f, lektionen: l };
    }

    // --- Reiter wechseln ---------------------------------------------------
    function zeigeIT(sub) {
      const b = document.querySelector('.viewnav button[data-view="view-italiano"]');
      if (b) b.click();
      if (sub) {
        const s = document.querySelector('#view-italiano .subnav button[data-subview="' + sub + '"]');
        if (s) s.click();
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // --- Satz des Tages ---------------------------------------------------
    function satzDesTages() {
      const bis = naechste().nr;
      const pool = [];
      LK.forEach(l => {
        if (l.nr <= bis) (l.saetze || []).forEach(s => pool.push({ it: s[0], de: s[1], nr: l.nr }));
      });
      if (!pool.length) return null;
      const t = Math.floor(new Date(heute() + 'T00:00:00').getTime() / 86400000);
      return pool[t % pool.length];
    }

    // ====================== Ansicht: Heute ================================
    function zeichneHeute() {
      const el = document.getElementById('sub-it-heute');
      if (!el) return;
      const fert = P.done.length, ges = LK.length;
      const nx = naechste(), f = faellige().length, s = serieAktuell();
      const ziel = zielErreicht();
      const bl = BL.find(b => b.nr === nx.block) || {};
      const bi = blockInfo(nx.block);
      const sdt = satzDesTages();
      const meilen = [12, 24, 36, 48];

      let h = '<div class="srcline">Ein Durchgang: 15–20 Minuten · Fortschritt gilt auf allen Geräten ' +
              '· Aussprache über die Stimme deines Geräts</div>';
      h += '<div class="ittop">';
      h += '<div class="itstat"><div class="l">Serie</div><div class="v">' + s +
           (s === 1 ? ' Tag' : ' Tage') + '</div><div class="s">Bester Lauf: ' +
           (P.serie.best || 0) + '</div></div>';
      h += '<div class="itstat"><div class="l">Lektionen</div><div class="v">' + fert + '/' + ges +
           '</div><div class="itbar' + (fert === ges ? ' good' : '') + '"><i style="width:' +
           Math.round(fert / ges * 100) + '%"></i></div></div>';
      h += '<div class="itstat"><div class="l">Karten fällig</div><div class="v">' + f +
           '</div><div class="s">' + (f ? 'Wiederholung wartet' : 'alles aufgeholt') + '</div></div>';
      h += '<div class="itstat"><div class="l">Tagesziel</div><div class="v">' + (ziel ? '✓' : 'offen') +
           '</div><div class="s">' + (ziel ? 'heute geschafft' : 'eine Lektion oder alle fälligen Karten') +
           '</div></div>';
      h += '</div>';

      h += '<div class="itcards">';
      h += '<div class="itcard' + (P.tag.lekt ? ' ok' : '') + '">' +
           '<div class="c-kicker">Lektion ' + nx.nr + ' · Block ' + nx.block + ' · ' + esc(bl.titel || '') + '</div>' +
           '<div class="c-title">' + esc(nx.titel) + '</div>' +
           '<div class="c-text">' + esc(nx.ziel) + '</div>' +
           '<div class="itbar"><i style="width:' + Math.round(bi.fertig / bi.gesamt * 100) + '%"></i></div>' +
           '<div class="c-text">Block ' + nx.block + ': ' + bi.fertig + ' von ' + bi.gesamt + ' Lektionen</div>' +
           '<div class="c-act"><button class="itbtn" data-it-start="' + nx.nr + '">' +
           (P.tag.lekt ? 'Nächste Lektion' : 'Lektion starten') + '</button>' +
           '<button class="itbtn ghost" data-it-go="sub-it-kurs">Alle Lektionen</button></div></div>';

      h += '<div class="itcard' + (f === 0 ? ' ok' : '') + '">' +
           '<div class="c-kicker">Karteikasten</div>' +
           '<div class="c-title">' + (f ? f + (f === 1 ? ' Karte' : ' Karten') + ' zur Wiederholung'
                                        : 'Nichts fällig') + '</div>' +
           '<div class="c-text">' + (f ? 'Wiederholen ist der Teil, der das Gelernte hält. Fünf Minuten genügen.'
                                      : 'Du bist auf Stand. Neue Karten kommen mit der nächsten Lektion.') + '</div>' +
           '<div class="c-text">Heute schon geübt: ' + P.tag.karten +
           (P.tag.karten === 1 ? ' Karte' : ' Karten') + '</div>' +
           '<div class="c-act"><button class="itbtn' + (f ? '' : ' ghost') + '" data-it-train="faellig"' +
           (f ? '' : ' disabled') + '>Karten üben</button>' +
           '<button class="itbtn ghost" data-it-train="alle">Freies Üben</button></div></div>';
      h += '</div>';

      if (sdt) {
        h += '<div class="itsatz"><div class="l">Satz des Tages</div>' +
             '<div class="it">' + esc(sdt.it) + ' ' + tonKnopf(sdt.it) + '</div>' +
             '<div class="de">' + esc(sdt.de) + '</div></div>';
      }

      h += '<div class="itcard" style="border-top-color:var(--warn)">' +
           '<div class="c-kicker">Meilensteine</div><div class="itbadges">' +
           meilen.map(m => {
             const b = BL.find(x => x.nr === Math.ceil(m / 12)) || {};
             return '<span class="itbadge' + (erledigt(m) ? ' got' : '') + '">' +
                    (erledigt(m) ? '★ ' : '') + esc(b.claim || ('Block ' + Math.ceil(m / 12))) + '</span>';
           }).join('') + '</div>' +
           '<div class="c-text">Jeder Meilenstein ist eine Lektion, in der du nur noch anwendest, was du kannst.</div></div>';

      if (PRON.length) {
        h += '<details class="itblock"><summary>Aussprache · die zehn Regeln, die alles abdecken</summary>' +
             '<div class="b-ziel"><div class="itpron">' +
             PRON.map(p => '<div><b>' + esc(p[0]) + '</b> – ' + esc(p[1]) + '</div>').join('') +
             '</div></div></details>';
      }
      el.innerHTML = h;
    }

    // ====================== Ansicht: Kurs =================================
    function zeichneKurs() {
      const el = document.getElementById('sub-it-kurs');
      if (!el) return;
      const nx = naechste();
      let h = '<div class="srcline">48 Lektionen · je 15–20 Minuten · eine pro Tag reicht. ' +
              'Du kannst jede Lektion jederzeit öffnen und wiederholen.</div>';
      BL.forEach(b => {
        const bi = blockInfo(b.nr);
        const offen = bi.fertig < bi.gesamt;
        h += '<details class="itblock"' + (b.nr === nx.block ? ' open' : '') + '>' +
             '<summary>Block ' + b.nr + ' · ' + esc(b.titel) + ' · ' + bi.fertig + '/' + bi.gesamt +
             '<div class="b-claim">„' + esc(b.claim) + '“</div></summary>' +
             '<div class="b-ziel">' + esc(b.ziel) + '<div class="itbar' + (offen ? '' : ' good') +
             '"><i style="width:' + Math.round(bi.fertig / bi.gesamt * 100) + '%"></i></div></div>' +
             '<div class="itlist">';
        bi.lektionen.forEach(l => {
          const d = erledigt(l.nr), ms = l.nr % 12 === 0;
          h += '<div class="itrow' + (d ? ' done' : '') + (l.nr === nx.nr ? ' next' : '') +
               '" data-it-start="' + l.nr + '">' +
               '<span class="r-nr">' + l.nr + '</span>' +
               '<span class="r-mark">' + (d ? '✓' : '·') + '</span>' +
               '<span class="r-body"><span class="r-title">' + esc(l.titel) + '</span>' +
               '<span class="r-ziel">' + esc(l.ziel) + '</span></span>' +
               (ms ? '<span class="r-tag ms">Meilenstein</span>'
                   : (l.nr === nx.nr ? '<span class="r-tag">dran</span>' : '')) +
               '</div>';
        });
        h += '</div></details>';
      });
      el.innerHTML = h;
    }

    // ====================== Ansicht: Vokabeln =============================
    let vocFilter = '';
    function zeichneWoerter() {
      const el = document.getElementById('sub-it-woerter');
      if (!el) return;
      const ids = Object.keys(P.karten).filter(id => kartePaar(id));
      const z = fachZaehlung(), f = faellige().length;
      let h = '<div class="srcline">' + ids.length + ' freigeschaltete Karten · ' + f +
              ' fällig · Karten entstehen automatisch aus jeder abgeschlossenen Lektion.</div>';
      h += '<div class="itcards"><div class="itcard">' +
           '<div class="c-kicker">Karteikasten</div>' +
           '<div class="c-title">' + (f ? f + ' fällig' : 'Nichts fällig') + '</div>' +
           '<div class="c-text">Gewusste Karten wandern ein Fach weiter und kommen später wieder, ' +
           'unsichere landen zurück in Fach 1.</div>' +
           '<div class="itboxes">' + z.map((n, i) => '<span>Fach ' + (i + 1) + ': ' + n + '</span>').join('') + '</div>' +
           '<div class="c-act"><button class="itbtn" data-it-train="faellig"' + (f ? '' : ' disabled') +
           '>Fällige üben</button>' +
           '<button class="itbtn ghost" data-it-train="alle">Freies Üben</button>' +
           '<button class="itbtn ghost" data-it-dir="1">Richtung: ' +
           (P.richtung === 'it' ? 'Italienisch → Deutsch' : 'Deutsch → Italienisch') + '</button></div></div></div>';

      if (!ids.length) {
        h += '<div class="itempty">Noch keine Karten. Schließe Lektion 1 ab, dann füllt sich der Kasten.</div>';
        el.innerHTML = h;
        return;
      }
      h += '<input class="itsearch" id="it-voc-q" type="search" placeholder="Suchen …" value="' +
           esc(vocFilter) + '">';
      const q = vocFilter.trim().toLowerCase();
      const zeilen = ids.map(id => ({ id: id, p: kartePaar(id) }))
        .filter(x => !q || x.p.it.toLowerCase().indexOf(q) !== -1 || x.p.de.toLowerCase().indexOf(q) !== -1)
        .sort((a, b) => a.p.lekt.nr - b.p.lekt.nr || a.p.it.localeCompare(b.p.it));
      h += '<div class="itvoc">' + (zeilen.length ? zeilen.map(x =>
        '<div class="itvline">' + tonKnopf(x.p.it) +
        '<span class="v-it">' + esc(x.p.it) + '</span>' +
        '<span class="v-de">' + esc(x.p.de) + '</span>' +
        '<span class="v-box">L' + x.p.lekt.nr + ' · Fach ' + ((P.karten[x.id].f | 0) + 1) + '</span></div>'
      ).join('') : '<div class="itempty">Kein Treffer.</div>') + '</div>';
      el.innerHTML = h;
      const inp = document.getElementById('it-voc-q');
      if (inp) {
        inp.addEventListener('input', () => {
          vocFilter = inp.value;
          const pos = inp.selectionStart;
          zeichneWoerter();
          const n = document.getElementById('it-voc-q');
          if (n) { n.focus(); try { n.setSelectionRange(pos, pos); } catch (e) {} }
        });
      }
    }

    // ====================== Anstoß auf der Übersicht ======================
    function zeichneAnstoss() {
      const el = document.getElementById('it-nudge');
      if (!el) return;
      const s = serieAktuell(), f = faellige().length, nx = naechste(), ziel = zielErreicht();
      const sdt = satzDesTages();
      let kopf, sub;
      if (ziel) {
        kopf = 'Italienisch: heute erledigt ✓';
        sub = 'Serie: ' + s + (s === 1 ? ' Tag' : ' Tage') + ' · ' + P.done.length + ' von ' + LK.length +
              ' Lektionen. Noch Lust? Dann leg eine Lektion drauf.';
      } else if (s > 0) {
        kopf = 'Italienisch: ' + s + (s === 1 ? ' Tag' : ' Tage') + ' Serie – halte sie';
        sub = 'Heute dran: Lektion ' + nx.nr + ' · ' + nx.titel +
              (f ? ' · ' + f + ' Karten fällig' : '') + '. 15 Minuten genügen.';
      } else if (P.done.length) {
        kopf = 'Italienisch: zurück in die Serie';
        sub = 'Lektion ' + nx.nr + ' · ' + nx.titel + (f ? ' · ' + f + ' Karten fällig' : '') +
              '. Ein Tag reicht, um neu zu starten.';
      } else {
        kopf = 'Italienisch: leg los';
        sub = 'Lektion 1 · ' + nx.titel + '. Danach kannst du dich vorstellen und einen Kaffee bestellen.';
      }
      el.className = 'itnudge' + (ziel ? ' done' : '');
      el.innerHTML = '<div class="n-flame">' + (ziel ? '✅' : (s > 0 ? '🔥' : '🇮🇹')) + '</div>' +
        '<div class="n-main"><div class="n-head">' + esc(kopf) + '</div>' +
        '<div class="n-sub">' + esc(sub) + '</div>' +
        (sdt ? '<div class="n-satz">Satz des Tages: „' + esc(sdt.it) + '“ – ' + esc(sdt.de) + '</div>' : '') +
        '</div>' +
        '<button class="itbtn" data-it-start="' + nx.nr + '">Lektion ' + nx.nr + '</button>' +
        (f ? '<button class="itbtn ghost" data-it-train="faellig">' + f + ' Karten</button>' : '');
    }

    function alles() { zeichneAnstoss(); zeichneHeute(); zeichneKurs(); zeichneWoerter(); }

    // ====================== Lektionsablauf ================================
    const over = document.getElementById('it-over');
    const sheet = document.getElementById('it-sheet');
    let L = null, schritt = 0, quiz = [], qIdx = 0, qRichtig = 0, gezeigt = {};

    function schliesse() {
      if (over) over.classList.remove('on');
      document.body.style.overflow = '';
      if (window.speechSynthesis) { try { window.speechSynthesis.cancel(); } catch (e) {} }
      L = null;
      alles();
    }
    function oeffne(nr) {
      L = LK.find(x => x.nr === Number(nr));
      if (!L || !over || !sheet) return;
      schritt = 0; gezeigt = {};
      quizBauen();
      over.classList.add('on');
      document.body.style.overflow = 'hidden';
      zeichneSchritt();
    }

    function quizBauen() {
      // Aus den Wörtern der Lektion, Ablenker aus derselben Lektion plus
      // früher gelernten Karten – so bleibt die Auswahl plausibel.
      const eigen = (L.woerter || []).map(w => ({ it: w[0], de: w[1] }));
      const fremd = [];
      LK.forEach(l => {
        if (l.nr !== L.nr && l.nr <= L.nr + 2) (l.woerter || []).forEach(w => fremd.push({ it: w[0], de: w[1] }));
      });
      const pool = eigen.slice();
      quiz = mische(eigen).slice(0, Math.min(6, eigen.length)).map((q, i) => {
        const nachIt = i % 2 === 1;   // abwechselnd beide Richtungen
        const kandidaten = mische(pool.filter(x => x.it !== q.it).concat(mische(fremd).slice(0, 8)));
        const falsch = [];
        kandidaten.forEach(k => {
          const w = nachIt ? k.it : k.de;
          if (falsch.length < 3 && w !== (nachIt ? q.it : q.de) && falsch.indexOf(w) === -1) falsch.push(w);
        });
        const richtig = nachIt ? q.it : q.de;
        return { frage: nachIt ? q.de : q.it, richtig: richtig,
                 optionen: mische(falsch.concat([richtig])), nachIt: nachIt };
      });
      qIdx = 0; qRichtig = 0;
    }
    function mische(a) {
      const b = a.slice();
      for (let i = b.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        const t = b[i]; b[i] = b[j]; b[j] = t;
      }
      return b;
    }

    const SCHRITTE = ['Wörter', 'Sätze', 'Grammatik', 'Quiz', 'Sprechen'];

    function zeichneSchritt() {
      if (!L) return;
      const bl = BL.find(b => b.nr === L.block) || {};
      let body = '', foot = '';
      if (schritt === 0) {
        body = '<h3>Neue Wörter · ' + (L.woerter || []).length + '</h3>' +
          (L.woerter || []).map(w => '<div class="itpair">' + tonKnopf(w[0]) +
            '<span class="p-it">' + esc(w[0]) + '</span><span class="p-de">' + esc(w[1]) + '</span></div>').join('') +
          (hatTon ? '<div class="itfeed">Tipp: einmal auf 🔊 tippen, dann laut nachsprechen. Hören allein reicht nicht.</div>'
                  : '');
      } else if (schritt === 1) {
        body = '<h3>Sätze, die du sofort benutzen kannst</h3>' +
          (L.saetze || []).map(s => '<div class="itpair">' + tonKnopf(s[0]) +
            '<span class="p-it">' + esc(s[0]) + '</span><span class="p-de">' + esc(s[1]) + '</span></div>').join('');
      } else if (schritt === 2) {
        const g = L.grammatik || {};
        body = '<h3>Der eine Grammatikpunkt</h3><div class="itgram"><div class="g-t">' +
               esc(g.titel || '') + '</div><div class="g-x">' + esc(g.text || '') + '</div></div>';
      } else if (schritt === 3) {
        if (qIdx >= quiz.length) {
          body = '<div class="itdone"><div class="d-ic">' + (qRichtig === quiz.length ? '🎯' : '👍') + '</div>' +
                 '<div class="d-t">' + qRichtig + ' von ' + quiz.length + ' richtig</div>' +
                 '<div class="d-s">' + (qRichtig === quiz.length
                   ? 'Alles sitzt. Weiter zur Sprechaufgabe.'
                   : 'Gut genug. Die Karten holen den Rest über die nächsten Tage nach.') + '</div>' +
                 '<div class="c-act" style="justify-content:center"><button class="itbtn ghost" data-it-requiz="1">' +
                 'Quiz wiederholen</button></div></div>';
        } else {
          const q = quiz[qIdx];
          body = '<div class="itq"><div class="q-n">Frage ' + (qIdx + 1) + ' von ' + quiz.length + ' · ' +
                 (q.nachIt ? 'Wie heißt das auf Italienisch?' : 'Was heißt das auf Deutsch?') + '</div>' +
                 '<div class="q-word">' + esc(q.frage) + '</div><div class="itopt">' +
                 q.optionen.map(o => '<button data-it-ans="' + esc(o) + '">' + esc(o) + '</button>').join('') +
                 '</div><div class="itfeed" id="it-feed"></div></div>';
        }
      } else {
        body = '<h3>Sprechaufgabe</h3><div class="ittask"><div class="t-l">Laut sprechen – nicht denken, sprechen</div>' +
               '<div class="t-x">' + esc(L.aufgabe || '') + '</div></div>' +
               '<div class="itfeed">Nimm dich ruhig mit dem Handy auf und hör einmal rein. ' +
               'Das ist der schnellste Weg zu sauberer Aussprache.</div>';
      }

      const zurueck = schritt > 0
        ? '<button class="itbtn ghost" data-it-step="-1">Zurück</button>' : '';
      if (schritt < 4) {
        const sperre = (schritt === 3 && qIdx < quiz.length);
        foot = zurueck + '<button class="itbtn" data-it-step="1"' + (sperre ? ' disabled' : '') + '>' +
               (schritt === 3 ? 'Zur Sprechaufgabe' : 'Weiter') + '</button>' +
               '<span class="sp">' + SCHRITTE[schritt] + '</span>';
      } else {
        foot = zurueck + '<button class="itbtn" data-it-finish="1">' +
               (erledigt(L.nr) ? 'Erneut abschließen' : 'Lektion abschließen') + '</button>' +
               '<span class="sp">' + SCHRITTE[schritt] + '</span>';
      }

      sheet.innerHTML = '<div class="s-head"><div><div class="s-kicker">Lektion ' + L.nr + ' · Block ' +
        L.block + ' · ' + esc(bl.titel || '') + (L.nr % 12 === 0 ? ' · Meilenstein' : '') + '</div>' +
        '<div class="s-title">' + esc(L.titel) + '</div></div>' +
        '<button class="s-close" data-it-close="1" title="Schließen">✕</button></div>' +
        '<div class="itsteps">' + SCHRITTE.map((_, i) =>
          '<i class="' + (i <= schritt ? 'on' : '') + '"></i>').join('') + '</div>' +
        '<div class="s-goal">' + esc(L.ziel) + '</div>' +
        '<div class="s-body">' + body + '</div>' +
        '<div class="s-foot">' + foot + '</div>';
      sheet.scrollIntoView({ block: 'start' });
    }

    function abschliessen() {
      if (!L) return;
      if (!erledigt(L.nr)) P.done.push(L.nr);
      kartenAnlegen(L);
      P.tag.lekt = (P.tag.lekt || 0) + 1;
      serieBuchen();
      sichern();
      const bi = blockInfo(L.block);
      const bl = BL.find(b => b.nr === L.block) || {};
      const blockFertig = bi.fertig === bi.gesamt;
      const s = serieAktuell();
      sheet.innerHTML = '<div class="s-head"><div><div class="s-kicker">Lektion ' + L.nr + ' abgeschlossen</div>' +
        '<div class="s-title">' + esc(L.titel) + '</div></div>' +
        '<button class="s-close" data-it-close="1" title="Schließen">✕</button></div>' +
        '<div class="itdone"><div class="d-ic">' + (blockFertig ? '🏆' : '🎉') + '</div>' +
        '<div class="d-t">' + (blockFertig ? 'Block ' + L.block + ' geschafft: „' + esc(bl.claim || '') + '“'
                                           : P.done.length + ' von ' + LK.length + ' Lektionen') + '</div>' +
        '<div class="d-s">Serie: ' + s + (s === 1 ? ' Tag' : ' Tage') + ' · ' +
        ((L.woerter || []).length + (L.saetze || []).length) +
        ' neue Karten liegen im Kasten und kommen ab morgen zur Wiederholung.</div></div>' +
        '<div class="s-foot"><button class="itbtn" data-it-close="1">Fertig</button>' +
        '<button class="itbtn ghost" data-it-train="faellig">Karten üben</button>' +
        '<button class="itbtn ghost" data-it-start="' + Math.min(LK.length, L.nr + 1) +
        '">Nächste Lektion</button></div>';
    }

    // ====================== Karteikasten-Training =========================
    let queue = [], akt = null, offen = false, modus = 'faellig', sitzung = 0;

    function trainStart(m) {
      modus = m;
      const alle = Object.keys(P.karten).filter(id => kartePaar(id));
      queue = mische(m === 'faellig' ? faellige() : alle);
      if (m === 'alle') queue = queue.slice(0, 30);
      sitzung = 0;
      if (!queue.length) {
        if (!over || !sheet) return;
        over.classList.add('on');
        document.body.style.overflow = 'hidden';
        sheet.innerHTML = '<div class="s-head"><div><div class="s-kicker">Karteikasten</div>' +
          '<div class="s-title">Nichts zu üben</div></div>' +
          '<button class="s-close" data-it-close="1">✕</button></div>' +
          '<div class="itempty">Schließe zuerst eine Lektion ab – dann füllt sich der Kasten.</div>' +
          '<div class="s-foot"><button class="itbtn" data-it-close="1">Zurück</button></div>';
        return;
      }
      L = null;
      over.classList.add('on');
      document.body.style.overflow = 'hidden';
      trainNext();
    }
    function trainNext() {
      akt = queue.shift() || null;
      offen = false;
      trainZeichne();
    }
    function trainZeichne() {
      if (!sheet) return;
      if (!akt) {
        const f = faellige().length;
        sheet.innerHTML = '<div class="s-head"><div><div class="s-kicker">Karteikasten</div>' +
          '<div class="s-title">Runde fertig</div></div>' +
          '<button class="s-close" data-it-close="1">✕</button></div>' +
          '<div class="itdone"><div class="d-ic">🧠</div><div class="d-t">' + sitzung +
          (sitzung === 1 ? ' Karte' : ' Karten') + ' wiederholt</div>' +
          '<div class="d-s">' + (f ? f + ' noch fällig.' : 'Alles aufgeholt – der Kasten ist leer.') +
          ' Heute insgesamt: ' + P.tag.karten + '.</div></div>' +
          '<div class="s-foot"><button class="itbtn" data-it-close="1">Fertig</button>' +
          (f ? '<button class="itbtn ghost" data-it-train="faellig">Weiter üben</button>' : '') + '</div>';
        return;
      }
      const p = kartePaar(akt);
      if (!p) { trainNext(); return; }
      const nachIt = P.richtung !== 'it';
      const vorn = nachIt ? p.de : p.it;
      const hinten = nachIt ? p.it : p.de;
      sheet.innerHTML = '<div class="s-head"><div><div class="s-kicker">Karteikasten · ' +
        (queue.length + 1) + ' in dieser Runde</div>' +
        '<div class="s-title">Wiederholen</div></div>' +
        '<button class="s-close" data-it-close="1" title="Schließen">✕</button></div>' +
        '<div class="ittrain"><div class="tr-dir">' +
        (nachIt ? 'Deutsch → Italienisch' : 'Italienisch → Deutsch') + '</div>' +
        '<div class="tr-front">' + esc(vorn) + (nachIt ? '' : ' ' + tonKnopf(p.it)) + '</div>' +
        '<div class="tr-back">' + (offen ? esc(hinten) + (nachIt ? ' ' + tonKnopf(p.it) : '') : '···') + '</div>' +
        '<div class="tr-src">' + p.art + ' aus Lektion ' + p.lekt.nr + ' · Fach ' +
        (((P.karten[akt] || {}).f | 0) + 1) + '</div>' +
        '<div class="tr-act">' + (offen
          ? '<button class="itbtn ghost" data-it-grade="0">Nochmal</button>' +
            '<button class="itbtn" data-it-grade="1">Gewusst</button>'
          : '<button class="itbtn" data-it-flip="1">Umdrehen</button>') + '</div></div>' +
        '<div class="s-foot"><button class="itbtn ghost" data-it-close="1">Beenden</button>' +
        '<span class="sp">' + sitzung + ' erledigt</span></div>';
    }
    function bewerten(gut) {
      if (!akt) return;
      const k = P.karten[akt] || { f: 0, d: heute() };
      if (gut) {
        k.f = Math.min(5, (k.f | 0) + 1);
        k.d = plusTage(FACH_TAGE[k.f]);
      } else {
        k.f = 0;
        k.d = heute();
        queue.push(akt);          // kommt in dieser Runde noch einmal
      }
      P.karten[akt] = k;
      sitzung++;
      P.tag.karten = (P.tag.karten || 0) + 1;
      serieBuchen();
      sichern();
      trainNext();
    }

    // ====================== Klicks ========================================
    document.addEventListener('click', ev => {
      const t = ev.target.closest('[data-say],[data-it-start],[data-it-go],[data-it-train],' +
        '[data-it-step],[data-it-ans],[data-it-close],[data-it-finish],[data-it-flip],' +
        '[data-it-grade],[data-it-requiz],[data-it-dir]');
      if (!t) return;
      const d = t.dataset;
      if (d.say !== undefined) { ev.preventDefault(); sprich(d.say); return; }
      if (d.itClose) { schliesse(); return; }
      if (d.itGo) { zeigeIT(d.itGo); return; }
      if (d.itDir) { P.richtung = P.richtung === 'it' ? 'de' : 'it'; sichern(); zeichneWoerter(); return; }
      if (d.itStart) { oeffne(d.itStart); return; }
      if (d.itTrain) { trainStart(d.itTrain); return; }
      if (d.itFlip) { offen = true; trainZeichne(); return; }
      if (d.itGrade !== undefined) { bewerten(d.itGrade === '1'); return; }
      if (d.itRequiz) { quizBauen(); zeichneSchritt(); return; }
      if (d.itStep) {
        schritt = Math.max(0, Math.min(4, schritt + Number(d.itStep)));
        zeichneSchritt();
        return;
      }
      if (d.itFinish) { abschliessen(); return; }
      if (d.itAns !== undefined) {
        const q = quiz[qIdx];
        if (!q || t.disabled) return;
        const box = t.parentElement;
        box.querySelectorAll('button').forEach(b => {
          b.disabled = true;
          if (b.dataset.itAns === q.richtig) b.classList.add('right');
        });
        const feed = document.getElementById('it-feed');
        if (d.itAns === q.richtig) {
          qRichtig++;
          if (feed) { feed.textContent = 'Richtig.'; feed.className = 'itfeed ok'; }
        } else {
          t.classList.add('wrong');
          if (feed) { feed.textContent = 'Richtig wäre: ' + q.richtig; feed.className = 'itfeed no'; }
        }
        if (q.nachIt) sprich(q.richtig);
        qIdx++;
        setTimeout(() => { if (L) zeichneSchritt(); }, 950);
      }
    });
    document.addEventListener('keydown', ev => {
      if (ev.key === 'Escape' && over && over.classList.contains('on')) schliesse();
    });
    if (over) over.addEventListener('click', ev => { if (ev.target === over) schliesse(); });

    alles();

    // Beim Laden: Weicht der hiesige Stand vom eingebackenen ab, geht er raus.
    // Das heilt auch abgebrochene Läufe, ohne dass etwas mitgezählt werden muss.
    if (nachzutragen) syncAnstossen();
    else if (fernZeit) syncSage('Auf allen Geräten gleich · Stand ' + fernZeit + ' Uhr');
    else if (!itcfg.rt) syncSage('Fortschritt bleibt auf diesem Gerät.', true);
  })();
'''


def desc_to_html(txt):
    """Aufgaben-Beschreibung als HTML: Zeilenumbrüche bleiben, Links werden klickbar.

    Erst wird nach Adressen gesucht, dann escaped – nie umgekehrt, sonst
    zerlegt das Escaping die Adresse.
    """
    zeilen = []
    for line in txt.splitlines():
        teile, pos = [], 0
        for m in re.finditer(r"https?://[^\s<>\"']+", line):
            u = m.group(0).rstrip(".,;:!?)")
            teile.append(esc(line[pos:m.start()]))
            teile.append(f'<a href="{esc(u)}" target="_blank" rel="noopener">{esc(u)}</a>')
            pos = m.start() + len(u)
        teile.append(esc(line[pos:]))
        zeilen.append("".join(teile))
    return "<br>".join(zeilen)


# Aufgaben: aufklappbare Beschreibung und ein Häkchen, das wirklich abhakt.
# Als eigene Konstanten geschrieben, weil die große Vorlage ein f-String ist –
# hier dürfen geschweifte Klammern also einfach bleiben.
TASK_CSS = '''
  /* Aufgabenzeile: Kopfzeile plus optional aufklappbare Beschreibung */
  ul.tasks li.tsk { display: block; padding: 0; }
  ul.tasks li.tsk .trow { display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; }
  /* Das Häkchen ist jetzt ein echter Knopf, nicht mehr nur Deko. */
  ul.tasks li.tsk .box { flex: 0 0 18px; width: 18px; height: 18px; margin-top: 1px;
    border: 1.5px solid var(--muted); border-radius: 5px; background: none; padding: 0;
    cursor: pointer; position: relative; -webkit-appearance: none; appearance: none;
    transition: border-color .12s, background .12s; }
  ul.tasks li.tsk .box:hover { border-color: var(--italiano); }
  ul.tasks li.tsk .box:focus-visible { outline: 2px solid var(--italiano); outline-offset: 2px; }
  ul.tasks li.tsk.done .box { background: var(--italiano); border-color: var(--italiano); }
  ul.tasks li.tsk.done .box::after { content: '✓'; position: absolute; inset: 0; color: #fff;
    font-size: 12px; line-height: 15px; text-align: center; font-weight: 700; }
  ul.tasks li.tsk.done .txt { text-decoration: line-through; color: var(--muted); }
  ul.tasks li.tsk.done .prio { display: none; }
  .tdtog { flex: 0 0 auto; background: none; border: none; color: var(--muted); cursor: pointer;
    font-size: 15px; line-height: 1; padding: 2px 5px; border-radius: 4px;
    transition: transform .15s ease, color .12s; }
  .tdtog:hover { color: var(--text-secondary); }
  .tdtog[aria-expanded="true"] { transform: rotate(180deg); }
  .tdesc { padding: 0 4px 10px 28px; font-size: 13px; line-height: 1.55;
    color: var(--text-secondary); overflow-wrap: anywhere; }
  .tdesc a { color: inherit; text-decoration: underline; }
  .tsync { font-size: 12px; color: var(--muted); margin: -4px 0 14px; min-height: 1em; }
  .tsync.warn { color: var(--bad-text); }
'''

TASK_JS = '''
  // ---- Aufgaben: Beschreibung aufklappen, Häkchen setzen, in Todoist schließen ----
  (() => {
    const SCHLUESSEL = 'task_done_v1';
    const MAX_VERSUCHE = 3;   // Schutz gegen endloses Neuladen

    const laden = () => {
      try { return JSON.parse(localStorage.getItem(SCHLUESSEL)) || {}; }
      catch (e) { return {}; }
    };
    const sichern = (s) => {
      try { localStorage.setItem(SCHLUESSEL, JSON.stringify(s)); } catch (e) {}
    };

    let stand = laden();
    const alleTasks = () => Array.from(document.querySelectorAll('li.tsk[data-tid]'));

    // Aufräumen: Was nicht mehr auf der Seite steht, ist in Todoist wirklich
    // geschlossen. Die Notiz dazu kann weg, sonst wächst der Speicher endlos.
    (() => {
      const da = new Set(alleTasks().map(li => li.dataset.tid));
      let weg = false;
      Object.keys(stand).forEach(id => { if (!da.has(id)) { delete stand[id]; weg = true; } });
      if (weg) sichern(stand);
    })();

    function zaehler() {
      document.querySelectorAll('.area').forEach(a => {
        const z = a.querySelector('.count[data-offen]');
        if (!z) return;
        z.textContent = a.querySelectorAll('li.tsk:not(.done)').length + ' offen';
      });
    }

    function zeichnen() {
      alleTasks().forEach(li => {
        const fertig = !!stand[li.dataset.tid];
        li.classList.toggle('done', fertig);
        const box = li.querySelector('.box');
        if (box) {
          box.setAttribute('aria-checked', fertig ? 'true' : 'false');
          box.setAttribute('aria-label', fertig ? 'Häkchen zurücknehmen' : 'Als erledigt markieren');
        }
      });
      zaehler();
    }

    // --- Echtes Abschließen: der Browser darf die Todoist-API nicht direkt
    // ansprechen, also stößt er den Workflow an, der es serverseitig macht.
    const cfg = window.DASHCFG || {};
    const meldung = document.getElementById('tasksync');
    let timer = null;

    function sage(text, warnen) {
      if (!meldung) return;
      meldung.textContent = text || '';
      meldung.classList.toggle('warn', !!warnen);
    }

    const offeneIds = () =>
      Object.keys(stand).filter(id => (stand[id].versuche || 0) < MAX_VERSUCHE);

    async function senden() {
      const ids = offeneIds();
      if (!ids.length) return;
      if (!cfg.rt) {
        sage('Häkchen ist hier gesetzt, wird aber nicht nach Todoist übertragen.', true);
        return;
      }
      ids.forEach(id => { stand[id].versuche = (stand[id].versuche || 0) + 1; });
      sichern(stand);
      sage('Wird in Todoist abgeschlossen – die Seite lädt in ~90 s neu.');
      try {
        const r = await fetch('https://api.github.com/repos/' + cfg.repo +
                              '/actions/workflows/update.yml/dispatches', {
          method: 'POST',
          headers: { 'Authorization': 'Bearer ' + cfg.rt, 'Accept': 'application/vnd.github+json' },
          body: JSON.stringify({ ref: 'main', inputs: { close_tasks: ids.join(',') } })
        });
        if (r.status === 204) { setTimeout(() => location.reload(), 90000); }
        else { sage('Todoist nicht erreicht (' + r.status + '). Häkchen bleibt hier gesetzt.', true); }
      } catch (e) {
        sage('Keine Verbindung. Häkchen bleibt gesetzt, nächster Versuch beim Neuladen.', true);
      }
    }

    function anstossen() { clearTimeout(timer); timer = setTimeout(senden, 2500); }

    document.addEventListener('click', (e) => {
      const box = e.target.closest('li.tsk .box');
      if (box) {
        const id = box.closest('li.tsk').dataset.tid;
        if (stand[id]) { delete stand[id]; } else { stand[id] = { versuche: 0 }; }
        sichern(stand);
        zeichnen();
        if (offeneIds().length) { anstossen(); }
        else { clearTimeout(timer); sage(''); }
        return;
      }
      const tog = e.target.closest('.tdtog');
      if (tog) {
        const li = tog.closest('li.tsk');
        const d = li && li.querySelector('.tdesc');
        if (!d) return;
        const auf = d.hasAttribute('hidden');
        if (auf) { d.removeAttribute('hidden'); } else { d.setAttribute('hidden', ''); }
        tog.setAttribute('aria-expanded', auf ? 'true' : 'false');
        tog.setAttribute('aria-label', auf ? 'Beschreibung ausblenden' : 'Beschreibung anzeigen');
      }
    });

    zeichnen();
    // Ein abgebrochener Lauf heilt sich beim nächsten Laden von selbst –
    // begrenzt durch MAX_VERSUCHE, damit daraus keine Schleife wird.
    if (offeneIds().length) anstossen();
  })();
'''


def build_html(tasks, done_today, events, cardshows, news, refresh_token,
               shows_note=None, releases=None, releases_note=None,
               trello=None, trello_note=None, podcast=None, podcast_note=None,
               weather=None, weather_note=None, day_focus=None, day_focus_note=None,
               news_digest=None, cal_meta=None,
               industry=None, industry_note=None,
               industry_digest=None, digest_note=None, watch_leagues=None,
               it_stand=None):
    releases = releases or []
    trello = trello or []
    podcast = podcast or []
    weather = weather or []
    news_digest = news_digest or {}
    cal_meta = cal_meta or []
    industry = industry or []
    watch_leagues = watch_leagues if watch_leagues is not None else list(WATCH_LEAGUES_DEFAULT)
    now = datetime.now(TZ)
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]

    # Mehrtägige Termine an jedem betroffenen Tag einsortieren (nicht nur am Starttag).
    ev_by_date = {}
    for e in events:
        d0 = date.fromisoformat(e["date"])
        d1 = date.fromisoformat(e.get("end_date", e["date"]))
        span = min((d1 - d0).days, 365) + 1  # Sicherheitsgrenze gegen fehlerhafte ICS-Daten
        for i in range(span):
            cur = d0 + timedelta(days=i)
            entry = e if span == 1 else {**e, "multi_day": i + 1, "multi_total": span}
            ev_by_date.setdefault(cur.isoformat(), []).append(entry)
    task_by_date = {}
    for t in tasks:
        if t["due"]:
            task_by_date.setdefault(t["due"], []).append(t)

    area_var = {"Privat": "privat", "Arbeit": "arbeit", "Studium": "studium"}

    def due_label(iso):
        d = date.fromisoformat(iso)
        if d == today: return "heute"
        if d == today + timedelta(days=1): return "morgen"
        if d < today: return f"überfällig ({d.day}.{d.month:02d}.)"
        return f"bis {WD[d.weekday()]}, {d.day:02d}.{d.month:02d}."

    # --- Heute
    area_cards = []
    for area in AREAS:
        atasks = [t for t in tasks if t["area"] == area]
        items = []
        for t in atasks:
            meta = " · ".join(x for x in [t["project"], due_label(t["due"]) if t["due"] else None] if x)
            meta_html = f'<span class="meta">{esc(meta)}</span>' if meta else ""
            prio = '<span class="prio hoch">hoch</span>' if t["prio_hoch"] else ""
            tid = esc(str(t.get("id") or ""))
            beschr = (t.get("beschreibung") or "").strip()
            # Der Pfeil erscheint nur, wenn es überhaupt eine Beschreibung gibt –
            # so bleibt die Liste bei Aufgaben ohne Notiz genauso ruhig wie vorher.
            toggle = ('<button class="tdtog" type="button" aria-expanded="false"'
                      ' aria-label="Beschreibung anzeigen">⌄</button>') if beschr else ""
            desc_html = f'<div class="tdesc" hidden>{desc_to_html(beschr)}</div>' if beschr else ""
            items.append(
                f'<li class="tsk" data-tid="{tid}">'
                f'<div class="trow">'
                f'<button class="box" type="button" role="checkbox" aria-checked="false"'
                f' aria-label="Als erledigt markieren"></button>'
                f'<span class="txt">{esc(t["content"])}{meta_html}</span>{toggle}{prio}'
                f'</div>{desc_html}</li>')
        body = "\n".join(items) if items else '<li class="none">Keine offenen Aufgaben 🎉</li>'
        area_cards.append(f'''
    <div class="area {area_var[area]}">
      <div class="area-head"><h2><span class="dot"></span>{area}</h2><span class="count" data-offen>{len(atasks)} offen</span></div>
      <ul class="tasks">{body}</ul>
    </div>''')

    # --- Trello (Themen = Boards, je Liste eine Karten-Gruppe)
    trello_total = sum(len(l["cards"]) for b in trello for l in b["lists"])
    board_blocks = []
    for b in trello:
        board_total = sum(len(l["cards"]) for l in b["lists"])
        list_blocks = []
        for l in b["lists"]:
            items = []
            for c in l["cards"]:
                meta = due_label(c["due_date"]) if c.get("due_date") else None
                if meta and c.get("due_time"):
                    meta = f"{meta} · {c['due_time']}"
                meta_html = f'<span class="meta">{esc(meta)}</span>' if meta else ""
                overdue = '<span class="prio hoch">überfällig</span>' if c.get("overdue") else ""
                name = esc(c["name"])
                if c.get("url"):
                    name = f'<a href="{esc(c["url"])}" target="_blank" rel="noopener">{name}</a>'
                items.append(f'<li><span class="box"></span><span class="txt">{name}{meta_html}</span>{overdue}</li>')
            list_blocks.append(f'''
        <div class="tlist">
          <div class="tlist-head"><h3>{esc(l["name"])}</h3><span class="count">{len(l["cards"])} offen</span></div>
          <ul class="tasks">{"".join(items)}</ul>
        </div>''')
        board_blocks.append(f'''
    <div class="tboard">
      <div class="tboard-head"><h2><a href="{esc(b["url"])}" target="_blank" rel="noopener">🗂️ {esc(b["name"])}</a></h2><span class="count">{board_total} offen</span></div>
      <div class="tlists">{"".join(list_blocks)}</div>
    </div>''')
    if board_blocks:
        trello_html = "".join(board_blocks)
    elif trello_note:
        trello_html = f'<div class="empty">{esc(trello_note)}</div>'
    else:
        trello_html = ('<div class="empty">Noch nicht eingerichtet – Secrets TRELLO_KEY und '
                        'TRELLO_TOKEN hinterlegen, dann erscheinen hier offene Karten je Board.</div>')
    trello_sub = f"{len(trello)} Board(s)" if trello else "noch nicht eingerichtet"

    open_total = len(tasks)
    per_area = " · ".join(f"{a} {len([t for t in tasks if t['area']==a])}" for a in AREAS)
    todays_ev = ev_by_date.get(today.isoformat(), [])
    future = [e for e in events if e["date"] > today.isoformat()
              or (e["date"] == today.isoformat() and (e["time"] == "" or e["time"] >= now.strftime("%H:%M")))]
    if future:
        ne = future[0]
        nd = date.fromisoformat(ne["date"])
        next_ev_title = esc(ne["title"])
        next_ev_sub = f"{WD[nd.weekday()]}, {nd.day:02d}.{nd.month:02d}." + \
            (f" · {ne['time']}" + (f"–{ne['end_time']}" if ne["end_time"] else "") if ne["time"] else " · ganztägig")
    else:
        next_ev_title, next_ev_sub = "—", "keine anstehenden Termine"
    week_ev_count = sum(1 for e in events
                        if e["date"] <= week_days[6].isoformat()
                        and e.get("end_date", e["date"]) >= monday.isoformat())
    kw = today.isocalendar()[1]

    # --- Countdowns: Zeit bis nächster Termin / nächste fällige Aufgabe / nächste Cardshow (DE)
    cd_event = None
    if future:
        ne = future[0]
        cd_event = {"target": _countdown_target(ne["date"], ne["time"] or None).isoformat(), "label": ev_label(ne)}
    upcoming_tasks = sorted([t for t in tasks if t["due"] and t["due"] >= today.isoformat()], key=lambda t: t["due"])
    cd_task = None
    if upcoming_tasks:
        t0 = upcoming_tasks[0]
        cd_task = {"target": _countdown_target(t0["due"], end_of_day=True).isoformat(), "label": t0["content"]}
    de_shows_sorted = sorted([s for s in cardshows if s.get("is_de") and s["start"] >= today.isoformat()],
                              key=lambda s: s["start"])
    cd_show = None
    if de_shows_sorted:
        s0 = de_shows_sorted[0]
        cd_show = {"target": _countdown_target(s0["start"], s0.get("time")).isoformat(), "label": s0["name"]}

    countdown_specs = [("⏳ Nächster Termin", cd_event), ("📌 Nächste fällige Aufgabe", cd_task),
                        ("🃏 Nächste Cardshow (DE)", cd_show)]
    countdown_html = "".join(
        f'''
    <div class="tile cdtile">
      <div class="label">{lbl}</div>
      <div class="value cdval" data-target="{esc(cd["target"])}">–</div>
      <div class="sub">{esc(cd["label"])}</div>
    </div>''' if cd else f'''
    <div class="tile cdtile">
      <div class="label">{lbl}</div>
      <div class="value small">—</div>
      <div class="sub">nichts Anstehendes</div>
    </div>'''
        for lbl, cd in countdown_specs)

    # --- Wetter (Stuttgart, 7 Tage)
    weather_cards = []
    for w in weather[:7]:
        wd_ = date.fromisoformat(w["date"])
        rain_str = f'{w["rain"]}%' if w.get("rain") is not None else "–"
        tmax_str = f'{w["tmax"]}°' if w.get("tmax") is not None else "–"
        tmin_str = f'{w["tmin"]}°' if w.get("tmin") is not None else "–"
        weather_cards.append(f'''
    <div class="wday">
      <div class="wday-d">{WD[wd_.weekday()]} {wd_.day:02d}.{wd_.month:02d}.</div>
      <div class="wicon" title="{esc(w.get("label",""))}">{w.get("icon","🌡️")}</div>
      <div class="wtemp">{tmax_str} <span class="wtmin">{tmin_str}</span></div>
      <div class="wrain">💧 {rain_str}</div>
    </div>''')
    weather_html = "".join(weather_cards) if weather_cards else (
        f'<div class="empty">{esc(weather_note) if weather_note else "Wetterdaten gerade nicht verfügbar."}</div>')

    # --- Tages-Fokus (KI)
    if day_focus:
        day_focus_html = '<ul class="dftakeaways">' + "".join(f"<li>{esc(l)}</li>" for l in day_focus) + '</ul>'
    elif day_focus_note:
        day_focus_html = f'<div class="empty">{esc(day_focus_note)}</div>'
    else:
        day_focus_html = '<div class="empty">Fokus wird beim nächsten automatischen Lauf berechnet.</div>'

    def _ev_dot(e):
        return f'<span class="d" style="background:{cal_color(e.get("cal"))}"></span>'

    if todays_ev:
        today_panel = "".join(
            f'<div class="event">{_ev_dot(e)}<span class="time">{e["time"]}–{e["end_time"]}</span><span>{esc(ev_label(e))}</span></div>'
            if e["time"] else
            f'<div class="event">{_ev_dot(e)}<span class="time">ganztägig</span><span>{esc(ev_label(e))}</span></div>'
            for e in todays_ev)
    else:
        today_panel = (f'<div class="empty"><span class="big">Keine Termine heute.</span><br>'
                       f'Nächster Termin: <strong style="color:var(--text-secondary)">{next_ev_title}</strong> ({next_ev_sub}).</div>')

    # --- Kalender-Filter (echte Namen + Farben je hinterlegter Kalender-Adresse; per
    # Checkbox einzeln ein-/ausblendbar, gemeinsam für Woche/Monat/Terminliste)
    calfilter_html = "".join(
        f'<label class="cfitem"><input type="checkbox" class="cfbox" data-cal="{cm["idx"]}" checked>'
        f'<span class="d" style="background:{cal_color(cm["idx"])}"></span>{esc(cm["name"])}</label>'
        for cm in cal_meta if cm.get("ok"))
    if not calfilter_html:
        calfilter_html = (f'<label class="cfitem"><input type="checkbox" class="cfbox" data-cal="0" checked>'
                          f'<span class="d" style="background:{cal_color(0)}"></span>Termin (Kalender)</label>')

    # --- Woche: mehrere Wochen (−8 bis +52) navigierbar (Pfeile + "Diese Woche")
    week_wraps = []
    for k in range(-8, 53):
        wk_monday = monday + timedelta(weeks=k)
        wk_days = [wk_monday + timedelta(days=i) for i in range(7)]
        cards = []
        for d in wk_days:
            iso = d.isoformat()
            cls = "day today" if d == today else "day"
            parts = [f'<h3>{WD[d.weekday()]} <span>{d.day:02d}.{d.month:02d}.{" · heute" if d == today else ""}</span></h3>']
            for e in ev_by_date.get(iso, []):
                tstr = f'<span class="t">{e["time"]}–{e["end_time"]}</span> · ' if e["time"] else ""
                color = cal_color(e.get("cal"))
                parts.append(f'<div class="ev" data-cal="{e.get("cal", 0)}" style="background:{_hex_to_rgba(color, 0.12)};border-left-color:{color};">'
                             f'{tstr}{esc(ev_label(e))}</div>')
            for t in task_by_date.get(iso, []):
                parts.append(f'<div class="due"><span class="d" style="background:var(--{area_var[t["area"]]})"></span>{esc(t["content"])}</div>')
            cards.append(f'<div class="{cls}">{"".join(parts)}</div>')
        wk_sun = wk_days[6]
        wk_kw = wk_monday.isocalendar()[1]
        wk_label = f"{wk_monday.day:02d}.{wk_monday.month:02d}.–{wk_sun.day:02d}.{wk_sun.month:02d}. · KW {wk_kw}"
        active = " active" if k == 0 else ""
        week_wraps.append(f'<div class="wkwrap{active}" data-wk="{k}" data-label="{esc(wk_label)}">'
                          f'<div class="week-grid">{"".join(cards)}</div></div>')

    # --- Monat: Vormonat bis +5 Jahre, zweistufig wählbar (erst Jahr, dann Monat)
    month_list = [ym_add(today.year, today.month, k) for k in range(-1, MONTH_VIEW_HORIZON_MONTHS + 1)]
    months_by_year = {}
    for (y, m) in month_list:
        months_by_year.setdefault(y, []).append(m)
    year_options = "".join(
        f'<option value="{y}"{" selected" if y == today.year else ""}>{y}</option>'
        for y in sorted(months_by_year))
    init_month_options = "".join(
        f'<option value="{m}"{" selected" if m == today.month else ""}>{MONTHS[m-1]}</option>'
        for m in months_by_year[today.year])
    month_wraps = []
    for (y, m) in month_list:
        key = f"{y}-{m:02d}"
        active = " active" if (y, m) == (today.year, today.month) else ""
        month_wraps.append(f'<div class="mwrap{active}" data-ym="{key}">{month_grid_html(y, m, ev_by_date, today)}</div>')
    months_by_year_json = json.dumps(months_by_year)
    month_names_json = json.dumps(MONTHS)
    month_list_json = json.dumps([f"{y}-{m:02d}" for (y, m) in month_list])

    # --- Terminliste: wie Monat einzeln je Monat ansteuerbar (Vormonat bis +5 Jahre),
    # pro Monat aber als chronologische Liste statt als Raster.
    term_wraps = []
    for (y, m) in month_list:
        key = f"{y}-{m:02d}"
        active = " active" if (y, m) == (today.year, today.month) else ""
        term_wraps.append(f'<div class="twrap{active}" data-ym="{key}">{month_agenda_html(y, m, events, today)}</div>')

    # --- Cardshows (gruppiert nach Monat/Jahr, Monate per Chip filterbar)
    show_parts, show_month_chips = [], []
    cur_group, de_count = None, 0
    for s in cardshows:
        sd = date.fromisoformat(s["start"])
        mkey = f"{sd.year}-{sd.month:02d}"
        group = f"{MONTHS[sd.month-1]} {sd.year}"
        if group != cur_group:
            if cur_group is not None:
                show_parts.append("</div>")
            show_parts.append(f'<div class="sgroup" data-month="{mkey}"><h3 class="ygroup">{group}</h3>')
            show_month_chips.append(f'<button class="fchip" data-v="{mkey}">{group}</button>')
            cur_group = group
        de_cls = " de" if s.get("is_de") else ""
        if s.get("is_de"):
            de_count += 1
        badge = '<span class="debadge">🇩🇪 Deutschland</span>' if s.get("is_de") else ""
        name = esc(s["name"])
        if s.get("url"):
            name = f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{name}</a>'
        show_parts.append(f'''<div class="show{de_cls}">
      <div class="show-date">{esc(fmt_show_date(s))}</div>
      <div class="show-name">{name}{badge}</div>
      <div class="show-loc">{esc(s["location"])}</div>
    </div>''')
    if cur_group is not None:
        show_parts.append("</div>")
    shows_note = shows_note or ""
    shows_stat = f"{len(cardshows)} kommende Shows, davon {de_count} in Deutschland" if cardshows else ""
    shows_filter = (f'<div class="filterrow"><span class="flabel">Monat:</span>'
                    f'<button class="fchip active" data-v="">Alle</button>{"".join(show_month_chips)}</div>'
                    if show_month_chips else "")
    shows_html = "".join(show_parts) if show_parts else '<div class="empty">Keine kommenden Shows gefunden.</div>'

    # --- Releases (collectosk.com): kommend prominent, vergangene einklappbar, Filter-Chips
    today_iso = today.isoformat()
    rel_dated = [r for r in releases if r.get("date")]
    rel_upcoming = sorted([r for r in rel_dated if r["date"] >= today_iso], key=lambda r: r["date"])
    rel_past = sorted([r for r in rel_dated if r["date"] < today_iso], key=lambda r: r["date"], reverse=True)
    rel_tbd = sorted([r for r in releases if not r.get("date")], key=lambda r: r["name"].lower())
    rel_makers = sorted({r["maker"] for r in releases})
    rel_cats = sorted({r["category"] for r in releases if r.get("category")})
    # Vorschlag 6: Wettbewerbs-Sicht. side/config/league setzt enrich_releases,
    # hier werden daraus nur Filter und Kennzahlen gebaut.
    watch_norm = {w.strip().casefold() for w in (watch_leagues or []) if w.strip()}
    rel_configs = [c for c in ("Hobby", "Retail", "Sticker", "unklar")
                   if any(r.get("config") == c for r in releases)]
    _lg_counts = {}
    for r in releases:
        _lg_counts[r.get("league") or "Sonstige"] = _lg_counts.get(r.get("league") or "Sonstige", 0) + 1
    # beobachtete Ligen zuerst, dahinter der Rest nach Häufigkeit
    rel_leagues = sorted(_lg_counts, key=lambda l: (l.casefold() not in watch_norm, -_lg_counts[l], l))

    def rel_row(r, past=False):
        if r.get("date"):
            d = date.fromisoformat(r["date"])
            dtxt = f"{WD[d.weekday()]}, {d.day:02d}.{d.month:02d}.{d.year}"
            mkey = f"{d.year}-{d.month:02d}"
        else:
            dtxt, mkey = "TBD", "tbd"
        name = esc(r["name"])
        if r.get("url"):
            name = f'<a href="{esc(r["url"])}" target="_blank" rel="noopener">{name}</a>'
        cl = (f' <a class="cl" href="{esc(r["checklist"])}" target="_blank" rel="noopener">✓ Checkliste</a>'
              if r.get("checklist") else "")
        side = r.get("side") or "Wettbewerb"
        cfg = r.get("config") or "unklar"
        lg = r.get("league") or "Sonstige"
        # Bewusst ruhig gehalten (Überarbeitung 28.07.2026): Nur "Hobby" bekommt
        # eine farbige Pille, Retail und Sticker stehen als graue Kleinschrift
        # daneben, bei "unklar" steht gar nichts mehr (früher ein "?"). Die
        # Kategorie-Angabe ist ganz entfallen – sie hat die Liga/Lizenz fast
        # immer nur wiederholt. Gefiltert werden kann weiterhin nach allem,
        # die Werte stehen unverändert in den data-Attributen.
        if cfg == "Hobby":
            cfg_badge = '<span class="cfg cfg-hobby">Hobby</span>'
        elif cfg == "unklar":
            cfg_badge = ""
        else:
            cfg_badge = f'<span class="cfgq">{esc(cfg)}</span>'
        # "Sonstige" als Badge wäre reine Füllung – dann bleibt die Zeile leer.
        lg_badge = "" if lg == "Sonstige" else (
            f'<span class="lg{" lg-watch" if lg.casefold() in watch_norm else ""}" '
            f'title="Nach {esc(lg)} filtern">{esc(lg)}</span>')
        return (f'<div class="rel{" past" if past else ""}{" own" if r.get("own") else ""}" '
                f'data-maker="{esc(r["maker"])}" '
                f'data-cat="{esc(r.get("category") or "")}" data-month="{mkey}" '
                f'data-side="{esc(side)}" data-config="{esc(cfg)}" data-league="{esc(lg)}">'
                f'<span class="rel-date">{dtxt}</span>'
                f'<span class="mk" title="Nach {esc(r["maker"])} filtern">{esc(r["maker"])}</span>'
                f'<span class="rel-name">{name}</span>{cfg_badge}{lg_badge}{cl}</div>')

    rel_month_chips, rel_parts, cur = [], [], None
    for r in rel_upcoming:
        d = date.fromisoformat(r["date"])
        mkey = f"{d.year}-{d.month:02d}"
        group = f"{MONTHS[d.month-1]} {d.year}"
        if group != cur:
            if cur is not None:
                rel_parts.append("</div>")
            rel_parts.append(f'<div class="mgroup" data-month="{mkey}"><h3 class="ygroup">{group}</h3>')
            rel_month_chips.append(f'<button class="fchip" data-dim="month" data-v="{mkey}">{group}</button>')
            cur = group
        rel_parts.append(rel_row(r))
    if cur is not None:
        rel_parts.append("</div>")
    if rel_tbd:
        rel_parts.append('<div class="mgroup" data-month="tbd"><h3 class="ygroup">Ohne Termin (TBD)</h3>')
        rel_parts.extend(rel_row(r) for r in rel_tbd)
        rel_parts.append("</div>")
        rel_month_chips.append('<button class="fchip" data-dim="month" data-v="tbd">TBD</button>')
    past_parts, cur = [], None
    for r in rel_past:
        d = date.fromisoformat(r["date"])
        mkey = f"{d.year}-{d.month:02d}"
        group = f"{MONTHS[d.month-1]} {d.year}"
        if group != cur:
            if cur is not None:
                past_parts.append("</div>")
            past_parts.append(f'<div class="mgroup" data-month="{mkey}"><h3 class="ygroup">{group}</h3>')
            cur = group
        past_parts.append(rel_row(r, past=True))
    if cur is not None:
        past_parts.append("</div>")
    rel_past_html = (f'<details class="pastbox"><summary>Vergangene Releases anzeigen ({len(rel_past)})</summary>'
                     f'{"".join(past_parts)}</details>') if rel_past else ""
    maker_chips = "".join(f'<button class="fchip" data-dim="maker" data-v="{esc(m)}">{esc(m)}</button>'
                          for m in rel_makers)
    cat_chips = "".join(f'<button class="fchip" data-dim="cat" data-v="{esc(c)}">{esc(c)}</button>'
                        for c in rel_cats)
    side_chips = "".join(f'<button class="fchip" data-dim="side" data-v="{s}">{s}</button>'
                         for s in ("Eigen", "Wettbewerb"))
    config_chips = "".join(f'<button class="fchip" data-dim="config" data-v="{esc(c)}">{esc(c)}</button>'
                           for c in rel_configs)
    league_chips = "".join(
        f'<button class="fchip{" watch" if l.casefold() in watch_norm else ""}" '
        f'data-dim="league" data-v="{esc(l)}">{esc(l)}</button>' for l in rel_leagues)
    # Sichtbar bleiben nur die zwei Filterzeilen, die am häufigsten gebraucht
    # werden. Die vier feineren Filter liegen hinter "Weitere Filter" – sie
    # funktionieren unverändert, drängen sich aber nicht mehr auf.
    rel_filters_html = f'''
    <div class="filterrow"><span class="flabel">Sicht:</span><button class="fchip active" data-dim="side" data-v="">Alle</button>{side_chips}</div>
    <div class="filterrow"><span class="flabel">Monat:</span><button class="fchip active" data-dim="month" data-v="">Alle</button>{"".join(rel_month_chips)}</div>
    <details class="morefilters"><summary>Weitere Filter</summary>
      <div class="filterrow"><span class="flabel">Konfiguration:</span><button class="fchip active" data-dim="config" data-v="">Alle</button>{config_chips}</div>
      <div class="filterrow"><span class="flabel">Liga/Lizenz:</span><button class="fchip active" data-dim="league" data-v="">Alle</button>{league_chips}</div>
      <div class="filterrow"><span class="flabel">Hersteller:</span><button class="fchip active" data-dim="maker" data-v="">Alle</button>{maker_chips}</div>
      <div class="filterrow"><span class="flabel">Kategorie:</span><button class="fchip active" data-dim="cat" data-v="">Alle</button>{cat_chips}</div>
    </details>'''
    rel_stat = (f"{len(rel_upcoming)} kommende · {len(rel_tbd)} ohne Termin · {len(rel_past)} vergangene"
                if releases else "")
    releases_note = releases_note or ""
    rel_body = "".join(rel_parts) if rel_parts else '<div class="empty">Keine kommenden Releases gefunden.</div>'

    # --- Vorschlag 6: Wettbewerbs-Sicht, bewusst knapp ---------------------
    # Überarbeitung 28.07.2026: Die drei Kennzahlen-Karten (30/60/90 Tage) sind
    # durch EINE Textzeile über 90 Tage ersetzt. Sie sagt dasselbe, drängt die
    # Release-Liste aber nicht mehr aus dem sichtbaren Bereich.
    def _rel_window(days):
        end = (today + timedelta(days=days)).isoformat()
        win = [r for r in rel_upcoming if r["date"] <= end]
        own = sum(1 for r in win if r.get("own"))
        hobby = sum(1 for r in win if r.get("config") == "Hobby")
        watched = sum(1 for r in win if (r.get("league") or "").casefold() in watch_norm)
        return len(win), own, len(win) - own, hobby, watched

    n90, own90, comp90, hobby90, watch90 = _rel_window(90)
    if n90:
        rel_sum_html = (
            '<div class="relsum"><b>Nächste 90 Tage:</b> '
            f'{n90} {"Release" if n90 == 1 else "Releases"} · '
            f'{own90} eigen, {comp90} Wettbewerb · {hobby90} Hobby · '
            f'{watch90} in beobachteten Ligen</div>')
    else:
        rel_sum_html = ('<div class="relsum"><b>Nächste 90 Tage:</b> '
                        'keine Releases mit Termin.</div>')
    # Bevorstehende Wettbewerbs-Releases in den beobachteten Ligen, die als
    # Terminkonflikt in Frage kommen. Zugeklappt, damit sie die Liste nicht
    # mehr überdeckt – ein Klick öffnet sie.
    rel_conflicts = [r for r in rel_upcoming
                     if not r.get("own")
                     and (r.get("league") or "").casefold() in watch_norm
                     and r["date"] <= (today + timedelta(days=90)).isoformat()][:12]
    if rel_conflicts:
        rows = "".join(
            f'<li><span class="rv-date">{date.fromisoformat(r["date"]).strftime("%d.%m.")}</span>'
            f'<span class="rv-mk">{esc(r["maker"])}</span>'
            f'<span class="rv-name">{esc(r["name"])}</span>'
            f'<span class="rv-lg">{esc(r.get("league") or "")}</span>'
            f'<span class="rv-cfg">{esc(r.get("config") or "")}</span></li>' for r in rel_conflicts)
        rel_conflict_html = (
            '<details class="rivalbox"><summary>Wettbewerb in beobachteten Ligen · '
            f'nächste 90 Tage ({len(rel_conflicts)})</summary>'
            f'<ul class="rivallist">{rows}</ul></details>')
    else:
        # Nichts anzeigen: Die Zusammenfassungszeile darüber nennt die 0 bereits.
        rel_conflict_html = ""
    rel_overview_html = f'{rel_sum_html}{rel_conflict_html}'

    # --- Vorschlag 5: Branchen- & Lizenz-Radar ---------------------------
    dig_html = ""
    if industry_digest:
        dparts = []
        for d in industry_digest:
            lks = [l for l in (d.get("links") or []) if l.get("url")]
            if lks:
                # Die Überschrift führt direkt zur wichtigsten Meldung dahinter.
                first = lks[0]
                head = (f'<a class="dhead dlink" href="{esc(first["url"])}" target="_blank"'
                        f' rel="noopener" title="{esc(first["title"])}">{esc(d["head"])}'
                        f'<span class="dgo">{esc(first["name"])} ↗</span></a>')
            else:
                head = f'<div class="dhead">{esc(d["head"])}</div>'
            why = f'<div class="dwhy">{esc(d["why"])}</div>' if d.get("why") else ""
            more = ""
            if len(lks) > 1:
                more = '<div class="dsrc">Auch dazu: ' + " ".join(
                    f'<a href="{esc(l["url"])}" target="_blank" rel="noopener"'
                    f' title="{esc(l["title"])}">{esc(l["name"] or "Quelle")}</a>'
                    for l in lks[1:]) + '</div>'
            dparts.append(f'<div class="dline">{head}{why}{more}</div>')
        dig_html = '<div class="digest">' + "".join(dparts) + '</div>'
    elif digest_note:
        dig_html = f'<div class="empty">{esc(digest_note)}</div>'

    ind_panels = []
    for s in (industry or []):
        lis = "".join(
            f'<li><a href="{esc(i["url"])}" target="_blank" rel="noopener">{esc(i["title"])}</a>'
            + (f'<span class="idate">{date.fromisoformat(i["date"]).strftime("%d.%m.")}</span>'
               if i.get("date") else "") + '</li>'
            for i in s.get("items", []))
        head = (f'<div class="ihead"><a href="{esc(s["home"])}" target="_blank" rel="noopener">'
                f'{esc(s["name"])}</a><span class="icount">{len(s.get("items", []))} von {s.get("total", 0)}</span></div>')
        note = f'<div class="inote">{esc(s["note"])}</div>' if s.get("note") else ""
        body = f'<ul class="ilist">{lis}</ul>' if lis else '<div class="empty">Aktuell keine passenden Meldungen.</div>'
        ind_panels.append(f'<div class="ipanel">{head}{note}{body}</div>')
    ind_body = ("".join(ind_panels) if ind_panels else
                '<div class="empty">Branchenquellen derzeit nicht erreichbar.</div>')
    # Die Quellenzahl steht schon am Anfang der Zeile – hier nur die Meldungen.
    ind_stat = (f"{sum(len(s.get('items', [])) for s in industry)} relevante Meldungen"
                ) if industry else ""

    # --- News
    news_panels = []
    for src in news:
        li_parts = []
        for i in src["items"]:
            has_img = bool(i.get("image"))
            img_html = f'<img src="{esc(i["image"])}" alt="" loading="lazy">' if has_img else ""
            li_parts.append(
                f'<li class="{"has-img" if has_img else ""}">'
                f'<a href="{esc(i["url"])}" target="_blank" rel="noopener">'
                f'{img_html}<span class="ntitle">{esc(i["title"])}</span></a></li>')
        lis = "".join(li_parts)
        note = f'<div class="srcnote">{esc(src["note"])}</div>' if src.get("note") else ""
        body = f"<ul class='newslist'>{lis}</ul>" if lis else ""
        news_panels.append(f'''<div class="panel">
      <h2><a href="{esc(src["home"])}" target="_blank" rel="noopener">{esc(src["name"])}</a></h2>
      {body}{note or ("" if lis else '<div class="empty">Keine Meldungen verfügbar.</div>')}
    </div>''')

    digest_parts = []
    for key, title in (("sport", "⚽ Sport"), ("andere", "📰 Weitere Themen")):
        lines = news_digest.get(key)
        if lines:
            body = '<ul class="dftakeaways">' + "".join(f"<li>{esc(l)}</li>" for l in lines) + '</ul>'
        else:
            body = '<div class="empty">Kurzfassung erscheint beim nächsten automatischen Lauf.</div>'
        digest_parts.append(f'<div class="panel digestpanel"><h2>{title}</h2>{body}</div>')
    digest_html = "".join(digest_parts)

    # --- Podcast ("Das Hobby")
    podcast_cards = []
    for i, ep in enumerate(podcast):
        dstr = ""
        if ep.get("date"):
            d = date.fromisoformat(ep["date"])
            dstr = f"{WD[d.weekday()]}, {d.day:02d}.{d.month:02d}.{d.year}"
        tks = "".join(f"<li>{esc(t)}</li>" for t in ep.get("takeaways", []))
        podcast_cards.append(f'''<div class="pcard" data-i="{i}">
      <div class="pcard-date">{dstr}</div>
      <h3><a href="{esc(ep.get("url",""))}" target="_blank" rel="noopener">{esc(ep["title"])}</a></h3>
      <ul class="ptakeaways">{tks}</ul>
    </div>''')
    podcast_total = len(podcast_cards)
    podcast_body = (
        f'''<div class="pcarousel">
      <button id="pprev" class="pnav" title="Vorherige Folge" {"disabled" if podcast_total < 2 else ""}>‹</button>
      <div class="pviewport"><div class="ptrack">{"".join(podcast_cards)}</div></div>
      <button id="pnext" class="pnav" title="Nächste Folge" {"disabled" if podcast_total < 2 else ""}>›</button>
    </div>
    <div class="pdots">{"".join(f'<span class="pdot{" active" if i == 0 else ""}" data-i="{i}"></span>' for i in range(podcast_total))}</div>
    <div class="pcount">Folge <span id="pcur">1</span> / {podcast_total}</div>'''
        if podcast_cards else
        f'<div class="empty">{esc(podcast_note) if podcast_note else "Noch keine Folge verfügbar."}</div>'
    )

    # --- Refresh-Knopf
    if refresh_token:
        refresh_html = '<button id="refreshbtn" class="refresh">⟳ Jetzt aktualisieren</button><span id="refreshmsg" class="refreshmsg"></span>'
        refresh_js = f'''
  const RT = {json.dumps(refresh_token)};
  const btn = document.getElementById('refreshbtn'), msg = document.getElementById('refreshmsg');
  btn.addEventListener('click', async () => {{
    btn.disabled = true; msg.textContent = 'Aktualisierung angestoßen – Seite lädt in ~90 s neu …';
    try {{
      const r = await fetch('https://api.github.com/repos/{REPO}/actions/workflows/update.yml/dispatches', {{
        method: 'POST',
        headers: {{ 'Authorization': 'Bearer ' + RT, 'Accept': 'application/vnd.github+json' }},
        body: JSON.stringify({{ ref: 'main' }})
      }});
      if (r.status === 204) {{ setTimeout(() => location.reload(), 90000); }}
      else {{ msg.textContent = 'Fehler (' + r.status + ') – bitte über GitHub Actions aktualisieren.'; btn.disabled = false; }}
    }} catch (e) {{ msg.textContent = 'Netzwerkfehler – bitte über GitHub Actions aktualisieren.'; btn.disabled = false; }}
  }});'''
    else:
        refresh_html = f'<a class="refresh" href="https://github.com/{REPO}/actions/workflows/update.yml" target="_blank" rel="noopener">⟳ Jetzt aktualisieren</a>'
        refresh_js = ""

    stand = now.strftime("%H:%M")
    date_line = f"{WD_LONG[today.weekday()]}, {today.day}. {MONTHS[today.month-1]} {today.year} · Stand {stand} Uhr"
    monday_iso = f"{monday.day}.–{week_days[6].day}. {MONTHS[week_days[6].month-1]} {week_days[6].year}"

    # Der Lernstoff wandert als JSON in die Seite. Kein API-Aufruf, keine Kosten:
    # Fortschritt, Quiz und Karteikasten laufen komplett im Browser.
    it_course_json = json.dumps(ITALIAN_COURSE, ensure_ascii=False, separators=(",", ":"))
    it_lekt_n = len(ITALIAN_COURSE.get("lektionen") or [])
    # Der abgeglichene Lernstand aus cache/italiano.json. Er stammt ursprünglich
    # aus dem Browser, deshalb zusätzlich "<" entschärfen – so kann die Zeile
    # unter keinen Umständen aus dem Script-Block ausbrechen.
    it_stand_json = json.dumps(it_stand or {}, ensure_ascii=False,
                               separators=(",", ":")).replace("<", "\\u003c")

    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Mein Dashboard – Moritz</title>
<style>
  :root {{
    --surface-1: #fcfcfb; --page: #f9f9f7; --text-primary: #0b0b0b; --text-secondary: #52514e;
    --muted: #898781; --hairline: #e1e0d9; --border: rgba(11,11,11,0.10);
    --privat: #1baf7a; --arbeit: #2a78d6; --studium: #4a3aa7; --trello: #eda100; --podcast: #008300; --focus: #0e7490;
    --italiano: #1f9e5a;
    --good: #0ca30c; --good-text: #006300; --done-ink: #898781;
    --bad: #d03b3b; --bad-text: #b02525; --warn: #c98500;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff; --text-secondary: #c3c2b7;
      --muted: #898781; --hairline: #2c2c2a; --border: rgba(255,255,255,0.10);
      --privat: #199e70; --arbeit: #3987e5; --studium: #9085e9; --trello: #c98500; --podcast: #008300; --focus: #22a6c9; --good-text: #0ca30c;
      --italiano: #2fb86e;
      --bad: #e05555; --bad-text: #f07878; --warn: #e0a52a;
    }}
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--page); color: var(--text-primary); padding: 24px; min-height: 100vh; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; }}
  header {{ margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }}
  header h1 {{ font-size: 22px; font-weight: 650; letter-spacing: -0.01em; }}
  header .date {{ color: var(--text-secondary); font-size: 14px; margin-top: 2px; }}
  a {{ color: inherit; }}
  .refresh {{ padding: 8px 16px; font-size: 13px; font-weight: 600; border-radius: 99px; border: 1px solid var(--border);
             background: var(--surface-1); color: var(--text-secondary); cursor: pointer; text-decoration: none; display: inline-block; }}
  .refresh:disabled {{ opacity: .5; cursor: default; }}
  .refreshmsg {{ font-size: 12px; color: var(--muted); margin-left: 8px; }}
  .viewnav {{ display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }}
  .viewnav button {{ padding: 8px 18px; font-size: 14px; font-weight: 600; border-radius: 99px; border: 1px solid var(--border);
                    background: var(--surface-1); color: var(--text-secondary); cursor: pointer; }}
  .viewnav button.active {{ background: var(--arbeit); color: #fff; border-color: var(--arbeit); }}
  .view {{ display: none; }} .view.active {{ display: block; }}
  .vtitle {{ font-size: 16px; font-weight: 650; margin-bottom: 12px; }}
  .tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .tile {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; }}
  .tile .label {{ font-size: 12px; color: var(--muted); margin-bottom: 6px; }}
  .tile .value {{ font-size: 26px; font-weight: 650; line-height: 1.1; }}
  .tile .value.small {{ font-size: 16px; font-weight: 600; margin-top: 2px; }}
  .tile .sub {{ font-size: 12px; color: var(--text-secondary); margin-top: 4px; }}
  .areas {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .area {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; border-top: 3px solid var(--accent); }}
  .area.privat {{ --accent: var(--privat); }} .area.arbeit {{ --accent: var(--arbeit); }} .area.studium {{ --accent: var(--studium); }}
  .area-head {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }}
  .area-head h2 {{ font-size: 15px; font-weight: 650; display: flex; align-items: center; gap: 8px; }}
  .area-head h2 .dot {{ width: 10px; height: 10px; border-radius: 3px; background: var(--accent); display: inline-block; }}
  .area-head .count {{ font-size: 12px; color: var(--muted); }}
  ul.tasks {{ list-style: none; }}
  ul.tasks li {{ display: flex; align-items: flex-start; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--hairline); font-size: 14px; }}
  ul.tasks li:last-child {{ border-bottom: none; }}
  ul.tasks li.none {{ color: var(--muted); }}
  ul.tasks .box {{ flex: 0 0 18px; height: 18px; margin-top: 1px; border: 1.5px solid var(--muted); border-radius: 5px; }}
  ul.tasks .txt {{ flex: 1; }}
  ul.tasks .meta {{ display: block; font-size: 12px; color: var(--muted); margin-top: 2px; }}
  .prio {{ font-size: 11px; padding: 1px 7px; border-radius: 99px; border: 1px solid var(--border); color: var(--text-secondary); white-space: nowrap; margin-top: 2px; }}
  .prio.hoch {{ border-color: #d03b3b; color: #d03b3b; }}
  .trellowrap {{ margin-bottom: 20px; }}
  .trello-head {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }}
  .trello-head h2 {{ font-size: 16px; font-weight: 650; }}
  .trello-head .count {{ font-size: 12px; color: var(--muted); }}
  .tboard {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; margin-bottom: 12px; border-top: 3px solid var(--trello); }}
  .tboard-head {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 6px; }}
  .tboard-head h2 {{ font-size: 15px; font-weight: 650; }}
  .tboard-head h2 a {{ color: inherit; text-decoration: none; }}
  .tboard-head h2 a:hover {{ text-decoration: underline; }}
  .tboard-head .count {{ font-size: 12px; color: var(--muted); }}
  .tlists {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }}
  .tlist {{ background: var(--page); border: 1px solid var(--hairline); border-radius: 10px; padding: 12px; }}
  .tlist-head {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }}
  .tlist-head h3 {{ font-size: 13px; font-weight: 650; color: var(--text-secondary); }}
  .tlist-head .count {{ font-size: 11px; color: var(--muted); }}
  .row2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .row3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .panel {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }}
  .panel h2 {{ font-size: 15px; font-weight: 650; margin-bottom: 12px; }}
  .panel h2 a {{ text-decoration: none; }}
  .event {{ display: flex; gap: 12px; align-items: baseline; padding: 8px 0; border-bottom: 1px solid var(--hairline); font-size: 14px; }}
  .event:last-child {{ border-bottom: none; }}
  .event .time {{ color: var(--text-secondary); font-variant-numeric: tabular-nums; white-space: nowrap; min-width: 150px; }}
  .event .d {{ width: 8px; height: 8px; border-radius: 3px; flex: 0 0 8px; align-self: center; }}
  .empty {{ color: var(--muted); font-size: 14px; padding: 8px 0; }}
  .empty .big {{ font-size: 15px; color: var(--text-secondary); }}
  .week-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 20px; }}
  .day {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 12px; min-height: 120px; }}
  .day.today {{ border-color: var(--arbeit); box-shadow: 0 0 0 1px var(--arbeit); }}
  .day h3 {{ font-size: 13px; font-weight: 650; margin-bottom: 8px; }}
  .day h3 span {{ color: var(--muted); font-weight: 500; }}
  .ev {{ font-size: 12px; padding: 6px 8px; border-radius: 8px; background: rgba(42,120,214,0.12); border-left: 3px solid var(--arbeit); margin-bottom: 6px; }}
  .ev .t {{ font-weight: 600; font-variant-numeric: tabular-nums; }}
  .due {{ font-size: 12px; color: var(--text-secondary); display: flex; gap: 6px; align-items: center; margin-bottom: 4px; }}
  .due .d {{ width: 8px; height: 8px; border-radius: 3px; flex: 0 0 8px; }}
  .legend {{ display: flex; gap: 16px; font-size: 12px; color: var(--muted); margin-bottom: 20px; flex-wrap: wrap; }}
  .legend span {{ display: flex; gap: 6px; align-items: center; }}
  .legend .d {{ width: 8px; height: 8px; border-radius: 3px; }}
  .mnav {{ display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }}
  .mnav button {{ padding: 6px 14px; font-size: 15px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary); cursor: pointer; }}
  .mnav select {{ padding: 7px 10px; font-size: 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-1); color: var(--text-primary); }}
  .mwrap {{ display: none; }} .mwrap.active {{ display: block; }}
  .wknav {{ display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }}
  .wknav button {{ padding: 6px 14px; font-size: 15px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary); cursor: pointer; }}
  .wknav button:disabled {{ opacity: .35; cursor: default; }}
  .wlabel {{ font-size: 14px; font-weight: 650; min-width: 200px; }}
  .wtoday-btn {{ margin-left: auto; font-size: 13px !important; padding: 6px 14px; }}
  .wkwrap {{ display: none; }} .wkwrap.active {{ display: block; }}
  .twrap {{ display: none; }} .twrap.active {{ display: block; }}
  .subnav {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
  .subnav button {{ padding: 6px 16px; font-size: 13px; font-weight: 600; border-radius: 99px; border: 1px solid var(--border);
                   background: var(--page); color: var(--text-secondary); cursor: pointer; }}
  .subnav button.active {{ background: var(--text-primary); color: var(--page); border-color: var(--text-primary); }}
  .subview {{ display: none; }} .subview.active {{ display: block; }}
  .calfilter {{ display: flex; gap: 14px; font-size: 12.5px; color: var(--muted); margin-bottom: 18px; flex-wrap: wrap;
               align-items: center; padding: 10px 12px; background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; }}
  .calfilter .cf-label {{ font-weight: 650; color: var(--text-secondary); }}
  .cfitem {{ display: flex; gap: 6px; align-items: center; cursor: pointer; user-select: none; }}
  .cfitem input {{ cursor: pointer; }}
  .cfitem .d {{ width: 9px; height: 9px; border-radius: 3px; flex: 0 0 9px; }}
  .month-head {{ display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; font-size: 12px; color: var(--muted); margin-bottom: 6px; text-align: center; }}
  .month-grid {{ display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; margin-bottom: 20px; }}
  .mday {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; min-height: 72px; padding: 6px; font-size: 12px; min-width: 0; overflow: hidden; }}
  .mday .num {{ font-weight: 600; font-size: 12px; margin-bottom: 4px; color: var(--text-secondary); }}
  .mday.out {{ opacity: .4; }}
  .mday.today {{ border-color: var(--arbeit); box-shadow: 0 0 0 1px var(--arbeit); }}
  .mday.today .num {{ color: var(--arbeit); }}
  .chip {{ font-size: 10.5px; line-height: 1.3; padding: 2px 5px; border-radius: 6px; background: rgba(42,120,214,0.12); border-left: 2px solid var(--arbeit); margin-bottom: 3px;
          white-space: normal; overflow-wrap: break-word; overflow: hidden;
          display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; cursor: default; }}
  .chip.past {{ opacity: .55; }}
  .ygroup {{ font-size: 14px; font-weight: 650; margin: 18px 0 6px; color: var(--text-secondary); }}
  .ygroup:first-child {{ margin-top: 0; }}
  .show {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; }}
  .show.de {{ border-left: 4px solid var(--privat); background: rgba(27,175,122,0.07); }}
  .show-date {{ font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }}
  .show-name {{ font-size: 15px; font-weight: 650; margin: 3px 0; }}
  .show-name a {{ text-decoration: none; }}
  .show-name a:hover {{ text-decoration: underline; }}
  .debadge {{ font-size: 11px; font-weight: 600; color: var(--good-text); border: 1px solid var(--privat); border-radius: 99px; padding: 1px 8px; margin-left: 8px; white-space: nowrap; }}
  .show-loc {{ font-size: 13px; color: var(--text-secondary); }}
  .srcline {{ font-size: 12px; color: var(--muted); margin-bottom: 16px; }}
  .filterrow {{ display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }}
  .flabel {{ font-size: 12px; color: var(--muted); min-width: 80px; }}
  .fchip {{ padding: 4px 12px; font-size: 12px; font-weight: 600; border-radius: 99px;
          border: 1px solid var(--border); background: var(--surface-1); color: var(--text-secondary); cursor: pointer; }}
  .fchip.active {{ background: var(--arbeit); color: #fff; border-color: var(--arbeit); }}
  .rel {{ display: flex; gap: 10px; align-items: baseline; padding: 8px 12px; flex-wrap: wrap;
         background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 6px; font-size: 14px; }}
  .rel.past {{ opacity: .6; }}
  .rel-date {{ color: var(--text-secondary); font-variant-numeric: tabular-nums; min-width: 118px; font-size: 13px; white-space: nowrap; }}
  .mk {{ font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 99px;
        border: 1px solid var(--arbeit); color: var(--arbeit); cursor: pointer; white-space: nowrap; }}
  .rel-name {{ flex: 1; min-width: 220px; }}
  .rel-name a {{ text-decoration: none; }}
  .rel-name a:hover {{ text-decoration: underline; }}
  .cl {{ font-size: 12px; color: var(--good-text); text-decoration: none; border: 1px solid var(--privat);
        border-radius: 99px; padding: 1px 8px; white-space: nowrap; }}
  /* --- Markt: Wettbewerbs-Sicht auf die Releases --------------------- */
  .rel.own {{ border-left: 3px solid var(--arbeit); }}
  /* Nur "Hobby" trägt Farbe, Retail/Sticker bleiben graue Kleinschrift. */
  .cfg {{ font-size: 11px; font-weight: 600; padding: 1px 7px; border-radius: 4px; white-space: nowrap; }}
  .cfg-hobby {{ color: #fff; background: var(--studium); }}
  .cfgq {{ font-size: 11px; color: var(--muted); white-space: nowrap; }}
  .lg {{ font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 99px; cursor: pointer;
        border: 1px dashed var(--border); color: var(--muted); white-space: nowrap; }}
  .lg.lg-watch {{ border-style: solid; border-color: var(--focus); color: var(--focus); }}
  .fchip.watch {{ border-color: var(--focus); }}
  .relsum {{ font-size: 13px; color: var(--text-secondary); background: var(--surface-1);
            border: 1px solid var(--border); border-left: 3px solid var(--focus); border-radius: 8px;
            padding: 8px 12px; margin-bottom: 12px; font-variant-numeric: tabular-nums; }}
  .relsum b {{ color: var(--text-primary); font-weight: 650; }}
  details.morefilters {{ margin: 2px 0 6px; }}
  details.morefilters > summary {{ font-size: 12.5px; color: var(--text-secondary); cursor: pointer;
                                 padding: 4px 0; width: fit-content; }}
  details.morefilters > summary:hover {{ color: var(--focus); }}
  details.rivalbox {{ margin-bottom: 18px; }}
  details.rivalbox > summary {{ font-size: 13px; font-weight: 650; cursor: pointer; padding: 6px 0;
                              color: var(--text-secondary); width: fit-content; }}
  details.rivalbox > summary:hover {{ color: var(--focus); }}
  ul.rivallist {{ list-style: none; }}
  ul.rivallist li {{ display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; font-size: 13px;
                 padding: 6px 0; border-bottom: 1px solid var(--hairline); }}
  ul.rivallist li:last-child {{ border-bottom: none; }}
  .rv-date {{ font-variant-numeric: tabular-nums; color: var(--text-secondary); min-width: 48px; }}
  .rv-mk {{ font-size: 11px; font-weight: 600; padding: 1px 8px; border-radius: 99px;
           border: 1px solid var(--border); color: var(--text-secondary); white-space: nowrap; }}
  .rv-name {{ flex: 1; min-width: 200px; }}
  .rv-lg {{ font-size: 11px; color: var(--focus); white-space: nowrap; }}
  .rv-cfg {{ font-size: 11px; color: var(--muted); white-space: nowrap; }}

  /* --- Markt: Branchen- & Lizenz-Radar ------------------------------- */
  .digest {{ background: var(--surface-1); border: 1px solid var(--border); border-top: 3px solid var(--focus);
            border-radius: 12px; padding: 14px 16px; margin-bottom: 18px; }}
  .dline {{ padding: 8px 0; border-bottom: 1px solid var(--hairline); }}
  .dline:last-child {{ border-bottom: none; }}
  .dline:first-child {{ padding-top: 0; }}
  .dhead {{ font-size: 14px; font-weight: 650; line-height: 1.35; }}
  a.dhead {{ display: block; color: inherit; text-decoration: none; }}
  a.dhead:hover {{ color: var(--focus); }}
  a.dhead:hover .dgo {{ opacity: 1; }}
  .dgo {{ font-size: 11px; font-weight: 500; color: var(--text-secondary); margin-left: 7px;
         white-space: nowrap; opacity: .72; }}
  .dwhy {{ font-size: 13px; color: var(--text-secondary); line-height: 1.4; margin-top: 2px; }}
  .dsrc {{ font-size: 11.5px; color: var(--text-secondary); margin-top: 4px; }}
  .dsrc a {{ color: var(--text-secondary); text-decoration: none; border-bottom: 1px dotted var(--border);
            margin-right: 8px; }}
  .dsrc a:hover {{ color: var(--focus); border-bottom-color: var(--focus); }}
  .ipanel {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; }}
  .ihead {{ display: flex; justify-content: space-between; align-items: baseline; gap: 8px; margin-bottom: 6px; }}
  .ihead a {{ font-size: 14px; font-weight: 650; text-decoration: none; color: inherit; }}
  .ihead a:hover {{ text-decoration: underline; }}
  .icount {{ font-size: 11px; color: var(--muted); white-space: nowrap; }}
  .inote {{ font-size: 11px; color: var(--warn); margin-bottom: 6px; }}
  ul.ilist {{ list-style: none; }}
  ul.ilist li {{ display: flex; gap: 8px; align-items: baseline; font-size: 13px; line-height: 1.35;
                padding: 6px 0; border-bottom: 1px solid var(--hairline); }}
  ul.ilist li:last-child {{ border-bottom: none; }}
  ul.ilist a {{ flex: 1; text-decoration: none; color: inherit; }}
  ul.ilist a:hover {{ text-decoration: underline; }}
  .idate {{ font-size: 11px; color: var(--muted); font-variant-numeric: tabular-nums; white-space: nowrap; }}

  details.pastbox {{ margin-top: 20px; }}
  details.pastbox summary {{ cursor: pointer; font-weight: 650; font-size: 14px; color: var(--text-secondary);
                             padding: 8px 0; }}
  ul.newslist {{ list-style: none; }}
  ul.newslist li {{ padding: 7px 0; border-bottom: 1px solid var(--hairline); font-size: 14px; line-height: 1.35; }}
  ul.newslist li:last-child {{ border-bottom: none; }}
  ul.newslist a {{ text-decoration: none; display: flex; align-items: center; gap: 0; }}
  ul.newslist a:hover .ntitle {{ text-decoration: underline; }}
  ul.newslist li.has-img a {{ gap: 10px; }}
  ul.newslist img {{ width: 52px; height: 52px; object-fit: cover; border-radius: 6px; flex: none; background: var(--hairline); }}
  ul.newslist .ntitle {{ flex: 1; }}
  .srcnote {{ font-size: 12px; color: var(--muted); margin-top: 8px; }}
  .pcarousel {{ display: flex; align-items: stretch; gap: 10px; }}
  .pviewport {{ flex: 1; overflow: hidden; min-width: 0; }}
  .ptrack {{ display: flex; transition: transform 0.3s ease; touch-action: pan-y; }}
  .pcard {{ flex: 0 0 100%; min-width: 0; background: var(--surface-1); border: 1px solid var(--border);
            border-radius: 12px; padding: 20px 22px; border-top: 3px solid var(--podcast); }}
  .pcard-date {{ font-size: 12px; color: var(--muted); margin-bottom: 4px; }}
  .pcard h3 {{ font-size: 16px; margin-bottom: 12px; line-height: 1.3; }}
  .pcard h3 a {{ color: var(--text-primary); text-decoration: none; }}
  .pcard h3 a:hover {{ text-decoration: underline; }}
  ul.ptakeaways {{ list-style: none; }}
  ul.ptakeaways li {{ position: relative; padding: 5px 0 5px 18px; font-size: 14px; line-height: 1.45; }}
  ul.ptakeaways li::before {{ content: "•"; position: absolute; left: 2px; color: var(--podcast); font-weight: 700; }}
  .pnav {{ flex: none; align-self: center; width: 36px; height: 36px; border-radius: 50%; border: 1px solid var(--border);
           background: var(--surface-1); color: var(--text-primary); font-size: 18px; cursor: pointer; }}
  .pnav:hover:not(:disabled) {{ background: var(--hairline); }}
  .pnav:disabled {{ opacity: 0.35; cursor: default; }}
  .pdots {{ display: flex; justify-content: center; gap: 6px; margin-top: 14px; }}
  .pdot {{ width: 7px; height: 7px; border-radius: 50%; background: var(--hairline); cursor: pointer; }}
  .pdot.active {{ background: var(--podcast); }}
  .pcount {{ text-align: center; font-size: 12px; color: var(--muted); margin-top: 6px; }}
  .focuspanel {{ margin-bottom: 20px; border-top: 3px solid var(--focus); }}
  .panel-head {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }}
  .panel-head h2 {{ font-size: 15px; font-weight: 650; }}
  .panel-head .count {{ font-size: 12px; color: var(--muted); }}
  ul.dftakeaways {{ list-style: none; }}
  ul.dftakeaways li {{ position: relative; padding: 5px 0 5px 18px; font-size: 14px; line-height: 1.45; }}
  ul.dftakeaways li::before {{ content: "•"; position: absolute; left: 2px; color: var(--focus); font-weight: 700; }}
  .digestpanel {{ border-top: 3px solid var(--focus); }}
  .countdowns {{ margin-bottom: 12px; }}
  .cdtile {{ border-top: 3px solid var(--focus); }}
  .cdtile .value.cdval {{ font-variant-numeric: tabular-nums; }}
  .weatherwrap {{ margin-bottom: 20px; }}
  .weekrow {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(88px, 1fr)); gap: 10px; }}
  .wday {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 12px 8px; text-align: center; }}
  .wday-d {{ font-size: 11.5px; color: var(--muted); margin-bottom: 6px; }}
  .wicon {{ font-size: 24px; margin-bottom: 6px; }}
  .wtemp {{ font-size: 14px; font-weight: 650; }}
  .wtmin {{ font-weight: 500; color: var(--text-secondary); }}
  .wrain {{ font-size: 11.5px; color: var(--text-secondary); margin-top: 4px; }}
  footer {{ color: var(--muted); font-size: 12px; line-height: 1.5; border-top: 1px solid var(--hairline); padding-top: 12px; }}
  footer strong {{ color: var(--text-secondary); font-weight: 600; }}
{IT_CSS}
{TASK_CSS}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Mein Dashboard</h1>
      <div class="date">{date_line}</div>
    </div>
    <div>{refresh_html}</div>
  </header>

  <nav class="viewnav">
    <button class="active" data-view="view-today">Übersicht</button>
    <button data-view="view-kalender">Kalender</button>
    <button data-view="view-shows">Cardshows</button>
    <button data-view="view-markt">Markt</button>
    <button data-view="view-news">News</button>
    <button data-view="view-podcast">Podcast</button>
    <button data-view="view-italiano">Italiano</button>
  </nav>

  <div id="view-today" class="view active">
  <section id="it-nudge" class="itnudge"></section>
  <section class="panel focuspanel">
    <div class="panel-head"><h2>🎯 Fokus · heute &amp; diese Woche</h2></div>
    {day_focus_html}
  </section>
  <section class="tiles countdowns">{countdown_html}
  </section>
  <section class="tiles">
    <div class="tile"><div class="label">Offene Aufgaben</div><div class="value">{open_total}</div><div class="sub">{per_area}</div></div>
    <div class="tile"><div class="label">Heute erledigt</div><div class="value">{done_today}</div><div class="sub">Weiter so</div></div>
    <div class="tile"><div class="label">Nächster Termin</div><div class="value small">{next_ev_title}</div><div class="sub">{next_ev_sub}</div></div>
    <div class="tile"><div class="label">Termine diese Woche</div><div class="value">{week_ev_count}</div><div class="sub">KW {kw}</div></div>
    <div class="tile"><div class="label">Trello offen</div><div class="value">{trello_total}</div><div class="sub">{trello_sub}</div></div>
  </section>
  <section class="weatherwrap">
    <div class="panel-head"><h2>🌤️ Wetter · Stuttgart</h2><span class="count">7 Tage</span></div>
    <div class="weekrow">{weather_html}</div>
  </section>
  <section class="areas">{"".join(area_cards)}
  </section>
  <div class="tsync" id="tasksync"></div>
  <section class="trellowrap">
    <div class="trello-head"><h2>🗂️ Trello</h2><span class="count">{trello_total} offen</span></div>
    {trello_html}
  </section>
  <section class="row2">
    <div class="panel"><h2>📅 Termine heute</h2>{today_panel}</div>
  </section>
  </div>

  <div id="view-kalender" class="view">
    <nav class="subnav">
      <button class="active" data-subview="sub-week">Woche</button>
      <button data-subview="sub-month">Monat</button>
      <button data-subview="sub-term">Terminliste</button>
    </nav>
    <div class="calfilter"><span class="cf-label">Kalender:</span>{calfilter_html}</div>

    <div id="sub-week" class="subview active">
      <h2 class="vtitle">Woche im Überblick</h2>
      <div class="wknav">
        <button id="wprev" title="Vorherige Woche">‹</button>
        <span id="wlabel" class="wlabel">{monday.day:02d}.{monday.month:02d}.–{week_days[6].day:02d}.{week_days[6].month:02d}. · KW {kw}</span>
        <button id="wnext" title="Nächste Woche">›</button>
        <button id="wtoday" class="wtoday-btn">Diese Woche</button>
      </div>
      <div class="week-grid-wrap">{"".join(week_wraps)}</div>
      <div class="legend">
        <span><span class="d" style="background:var(--privat)"></span>Aufgabe Privat</span>
        <span><span class="d" style="background:var(--arbeit)"></span>Aufgabe Arbeit</span>
        <span><span class="d" style="background:var(--studium)"></span>Aufgabe Studium</span>
      </div>
    </div>

    <div id="sub-month" class="subview">
      <div class="mnav">
        <button id="mprev" title="Vorheriger Monat">‹</button>
        <select id="ysel">{year_options}</select>
        <select id="msel">{init_month_options}</select>
        <button id="mnext" title="Nächster Monat">›</button>
      </div>
      {"".join(month_wraps)}
    </div>

    <div id="sub-term" class="subview">
      <h2 class="vtitle">Terminliste</h2>
      <div class="mnav">
        <button id="tprev" title="Vorheriger Monat">‹</button>
        <select id="tysel">{year_options}</select>
        <select id="tmsel">{init_month_options}</select>
        <button id="tnext" title="Nächster Monat">›</button>
      </div>
      {"".join(term_wraps)}
    </div>
  </div>

  <div id="view-shows" class="view">
    <h2 class="vtitle">Cardshows &amp; Trade Events</h2>
    <div class="srcline">Quelle: <a href="https://gradedmoments.de/cardshows/" target="_blank" rel="noopener">gradedmoments.de</a> · Stand {stand} Uhr{" · " + shows_stat if shows_stat else ""}{" · " + esc(shows_note) if shows_note else ""} · <span style="color:var(--good-text)">🇩🇪 = Show in Deutschland</span></div>
    {shows_filter}
    {shows_html}
  </div>

  <div id="view-markt" class="view">
    <h2 class="vtitle">Markt · Trading Cards</h2>
    <nav class="subnav">
      <button class="active" data-subview="sub-rel">Releases</button>
      <button data-subview="sub-industry">Branche</button>
    </nav>

    <div id="sub-rel" class="subview active">
      <div class="srcline">Quelle: <a href="{RELEASES_URL}" target="_blank" rel="noopener">collectosk.com</a> · Stand {stand} Uhr{" · " + rel_stat if rel_stat else ""}{" · " + esc(releases_note) if releases_note else ""}</div>
      {rel_overview_html}
      {rel_filters_html}
      {rel_body}
      {rel_past_html}
    </div>

    <div id="sub-industry" class="subview">
      <div class="srcline">Branchen- und Lizenzmeldungen aus {len(industry)} Quellen · Kurzfassung 1×/Tag per KI, Rohliste jederzeit aktuell · Stand {stand} Uhr{" · " + ind_stat if ind_stat else ""}{" · " + esc(industry_note) if industry_note else ""}</div>
      {dig_html}
      <div class="row3">{ind_body}</div>
    </div>
  </div>

  <div id="view-news" class="view">
    <h2 class="vtitle">News</h2>
    <div class="srcline">Stand {stand} Uhr · aktualisiert sich mit jedem Dashboard-Update · Kurzfassung 1×/Tag per KI, Rohliste darunter jederzeit aktuell</div>
    <div class="row2">{digest_html}</div>
    <div class="row3">{"".join(news_panels)}</div>
  </div>

  <div id="view-podcast" class="view">
    <h2 class="vtitle">Podcast · Das Hobby</h2>
    <div class="srcline">Quelle: <a href="{PODCAST_HOME}" target="_blank" rel="noopener">dashobby.podigee.io</a> (offizielles Transkript je Folge) · Stand {stand} Uhr · Durchwischen oder Pfeile für weitere Folgen</div>
    {podcast_body}
  </div>

  <div id="view-italiano" class="view">
    <h2 class="vtitle">Italiano · {it_lekt_n} Lektionen in 4 Blöcken</h2>
    <nav class="subnav">
      <button class="active" data-subview="sub-it-heute">Heute</button>
      <button data-subview="sub-it-kurs">Kurs</button>
      <button data-subview="sub-it-woerter">Vokabeln</button>
    </nav>
    <div class="itsync" id="itsync"></div>

    <div id="sub-it-heute" class="subview active">
      <div class="srcline">Lernbereich wird geladen …</div>
    </div>
    <div id="sub-it-kurs" class="subview"></div>
    <div id="sub-it-woerter" class="subview"></div>
  </div>

  <div class="itover" id="it-over"><div class="itsheet" id="it-sheet"></div></div>

  <footer>
    <strong>Automatisch aktuell:</strong> Aufgaben pflegst du direkt in Todoist, Termine in Google Kalender.
    Das Dashboard aktualisiert sich alle 30 Minuten von selbst – oder sofort über den ⟳-Knopf oben rechts.
    Design-Änderungen: einfach Claude sagen.
  </footer>
</div>
<script>
  document.querySelectorAll('.viewnav button').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('.viewnav button').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.view).classList.add('active');
    }});
  }});
  // Unterreiter (Kalender: Woche/Monat/Terminliste · Markt: Releases/Händler/Branche).
  // Bewusst je Hauptreiter getrennt: sonst würde ein Klick im Markt-Bereich auch die
  // Auswahl im Kalender zurücksetzen und dort eine leere Ansicht hinterlassen.
  document.querySelectorAll('.subnav').forEach(nav => {{
    const scope = nav.closest('.view') || document;
    nav.querySelectorAll('button').forEach(btn => {{
      btn.addEventListener('click', () => {{
        nav.querySelectorAll('button').forEach(b => b.classList.remove('active'));
        scope.querySelectorAll(':scope > .subview').forEach(v => v.classList.remove('active'));
        btn.classList.add('active');
        const target = document.getElementById(btn.dataset.subview);
        if (target) target.classList.add('active');
      }});
    }});
  }});
  // Monat + Terminliste: zweistufig (erst Jahr, dann Monat), Bereich Vormonat bis +5 Jahre –
  // dieselbe Logik für beide Reiter, je mit eigenen Dropdowns/Pfeilen/Wraps.
  const MONTHS_BY_YEAR = {months_by_year_json};
  const MONTH_NAMES = {month_names_json};
  const MONTH_LIST = {month_list_json};
  function setupYearMonthNav(cfg) {{
    const ysel = document.getElementById(cfg.ysel);
    const msel = document.getElementById(cfg.msel);
    const wraps = document.querySelectorAll(cfg.wrapSel);
    if (!ysel || !msel) return;
    let mIdx = MONTH_LIST.indexOf(`${{ysel.value}}-${{String(msel.value).padStart(2, '0')}}`);
    function populateMonths(year, preferMonth) {{
      const months = MONTHS_BY_YEAR[year] || [];
      msel.innerHTML = months.map(m => `<option value="${{m}}">${{MONTH_NAMES[m - 1]}}</option>`).join('');
      msel.value = months.includes(preferMonth) ? preferMonth : months[0];
    }}
    function showKey(key) {{
      wraps.forEach(w => w.classList.toggle('active', w.dataset.ym === key));
    }}
    function currentKey() {{
      return `${{ysel.value}}-${{String(msel.value).padStart(2, '0')}}`;
    }}
    function gotoIdx(idx) {{
      idx = Math.max(0, Math.min(MONTH_LIST.length - 1, idx));
      mIdx = idx;
      const [y, m] = MONTH_LIST[idx].split('-').map(Number);
      ysel.value = y;
      populateMonths(y, m);
      showKey(MONTH_LIST[idx]);
    }}
    ysel.addEventListener('change', () => {{
      populateMonths(parseInt(ysel.value, 10), parseInt(msel.value, 10));
      mIdx = MONTH_LIST.indexOf(currentKey());
      showKey(currentKey());
    }});
    msel.addEventListener('change', () => {{
      mIdx = MONTH_LIST.indexOf(currentKey());
      showKey(currentKey());
    }});
    const prevBtn = document.getElementById(cfg.prev), nextBtn = document.getElementById(cfg.next);
    prevBtn && prevBtn.addEventListener('click', () => gotoIdx(mIdx - 1));
    nextBtn && nextBtn.addEventListener('click', () => gotoIdx(mIdx + 1));
  }}
  setupYearMonthNav({{ysel: 'ysel', msel: 'msel', prev: 'mprev', next: 'mnext', wrapSel: '#sub-month .mwrap'}});
  setupYearMonthNav({{ysel: 'tysel', msel: 'tmsel', prev: 'tprev', next: 'tnext', wrapSel: '#sub-term .twrap'}});
  // Woche: mehrere Wochen navigierbar (Pfeile + "Diese Woche")
  (() => {{
    const wraps = Array.from(document.querySelectorAll('#sub-week .wkwrap'));
    if (!wraps.length) return;
    let wi = wraps.findIndex(w => w.classList.contains('active'));
    if (wi < 0) wi = 0;
    const label = document.getElementById('wlabel');
    const prevBtn = document.getElementById('wprev'), nextBtn = document.getElementById('wnext');
    const todayIdx = wraps.findIndex(w => w.dataset.wk === '0');
    function showWeek(idx) {{
      idx = Math.max(0, Math.min(wraps.length - 1, idx));
      wraps.forEach((w, i) => w.classList.toggle('active', i === idx));
      wi = idx;
      if (label) label.textContent = wraps[wi].dataset.label;
      if (prevBtn) prevBtn.disabled = wi === 0;
      if (nextBtn) nextBtn.disabled = wi === wraps.length - 1;
    }}
    prevBtn && prevBtn.addEventListener('click', () => showWeek(wi - 1));
    nextBtn && nextBtn.addEventListener('click', () => showWeek(wi + 1));
    const todayBtn = document.getElementById('wtoday');
    todayBtn && todayBtn.addEventListener('click', () => showWeek(todayIdx));
    showWeek(wi);
  }})();
  // Kalender-Filter: Checkboxen blenden Termine/Chips des jeweiligen Kalenders
  // in Woche/Monat/Terminliste ein oder aus (gemeinsam für alle drei Unterreiter).
  (() => {{
    const root = document.getElementById('view-kalender');
    if (!root) return;
    const boxes = root.querySelectorAll('.cfbox');
    function applyCalFilter() {{
      const hidden = new Set();
      boxes.forEach(cb => {{ if (!cb.checked) hidden.add(cb.dataset.cal); }});
      // Nur echte Termin-Elemente filtern, nie die Checkboxen selbst (die tragen
      // ebenfalls data-cal, damit die Legende die richtige Farbe zeigen kann).
      root.querySelectorAll('.ev[data-cal], .chip[data-cal], .event[data-cal]').forEach(el => {{
        el.style.display = hidden.has(el.dataset.cal) ? 'none' : '';
      }});
    }}
    boxes.forEach(cb => cb.addEventListener('change', applyCalFilter));
    applyCalFilter();
  }})();
  // Cardshows: Monats-Chips
  document.querySelectorAll('#view-shows .fchip').forEach(c => c.addEventListener('click', () => {{
    document.querySelectorAll('#view-shows .fchip').forEach(x => x.classList.toggle('active', x === c));
    const v = c.dataset.v;
    document.querySelectorAll('#view-shows .sgroup').forEach(g =>
      g.style.display = (!v || g.dataset.month === v) ? '' : 'none');
  }}));
  // Releases: kombinierbare Filter (Sicht + Konfiguration + Liga + Hersteller + Kategorie + Monat)
  const relF = {{ side: '', config: '', league: '', maker: '', cat: '', month: '' }};
  function applyRel() {{
    document.querySelectorAll('#sub-rel .rel').forEach(el => {{
      const ok = (!relF.maker || el.dataset.maker === relF.maker)
        && (!relF.cat || el.dataset.cat === relF.cat)
        && (!relF.month || el.dataset.month === relF.month)
        && (!relF.side || el.dataset.side === relF.side)
        && (!relF.config || el.dataset.config === relF.config)
        && (!relF.league || el.dataset.league === relF.league);
      el.style.display = ok ? '' : 'none';
    }});
    document.querySelectorAll('#sub-rel .mgroup').forEach(g => {{
      const any = Array.from(g.querySelectorAll('.rel')).some(e => e.style.display !== 'none');
      g.style.display = any ? '' : 'none';
    }});
    document.querySelectorAll('#sub-rel .fchip').forEach(c =>
      c.classList.toggle('active', relF[c.dataset.dim] === c.dataset.v));
    // Liegt ein aktiver Filter hinter "Weitere Filter", wird der Abschnitt
    // aufgeklappt – sonst wäre nicht zu sehen, warum die Liste kürzer ist.
    const more = document.querySelector('#sub-rel .morefilters');
    if (more && (relF.config || relF.league || relF.maker || relF.cat)) more.open = true;
  }}
  document.querySelectorAll('#sub-rel .fchip').forEach(c => c.addEventListener('click', () => {{
    relF[c.dataset.dim] = c.dataset.v; applyRel();
  }}));
  document.querySelectorAll('#sub-rel .mk').forEach(b => b.addEventListener('click', () => {{
    const v = b.textContent.trim();
    relF.maker = (relF.maker === v) ? '' : v; applyRel();
  }}));
  document.querySelectorAll('#sub-rel .lg').forEach(b => b.addEventListener('click', () => {{
    const v = b.textContent.trim();
    relF.league = (relF.league === v) ? '' : v; applyRel();
  }}));
  // Podcast: Karussell (Pfeile, Punkte, Swipe)
  (() => {{
    const track = document.querySelector('#view-podcast .ptrack');
    if (!track) return;
    const cards = track.querySelectorAll('.pcard');
    const dots = document.querySelectorAll('#view-podcast .pdot');
    const cur = document.getElementById('pcur');
    const prevBtn = document.getElementById('pprev'), nextBtn = document.getElementById('pnext');
    let i = 0;
    function show(idx) {{
      i = Math.max(0, Math.min(cards.length - 1, idx));
      track.style.transform = `translateX(-${{i * 100}}%)`;
      dots.forEach((d, di) => d.classList.toggle('active', di === i));
      if (cur) cur.textContent = i + 1;
      if (prevBtn) prevBtn.disabled = i === 0;
      if (nextBtn) nextBtn.disabled = i === cards.length - 1;
    }}
    prevBtn && prevBtn.addEventListener('click', () => show(i - 1));
    nextBtn && nextBtn.addEventListener('click', () => show(i + 1));
    dots.forEach(d => d.addEventListener('click', () => show(parseInt(d.dataset.i, 10))));
    let touchX = null;
    track.addEventListener('touchstart', e => {{ touchX = e.touches[0].clientX; }}, {{ passive: true }});
    track.addEventListener('touchend', e => {{
      if (touchX === null) return;
      const dx = e.changedTouches[0].clientX - touchX;
      if (Math.abs(dx) > 40) show(i + (dx < 0 ? 1 : -1));
      touchX = null;
    }}, {{ passive: true }});
    show(0);
  }})();
  // Countdown-Kacheln: live tickende Zeit bis Termin/Aufgabe/Cardshow
  (() => {{
    const els = document.querySelectorAll('.cdval');
    if (!els.length) return;
    function fmt(ms) {{
      if (ms <= 0) return 'jetzt';
      const s = Math.floor(ms / 1000);
      const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
      if (d > 0) return `${{d}}T ${{h}}Std`;
      if (h > 0) return `${{h}}Std ${{m}}Min`;
      return `${{m}}Min`;
    }}
    function tick() {{
      const now = Date.now();
      els.forEach(el => {{ el.textContent = fmt(new Date(el.dataset.target).getTime() - now); }});
    }}
    tick();
    setInterval(tick, 30000);
  }})();

  // Repo und der bereits vorhandene Actions-Token. Beides brauchen sowohl das
  // Abhaken der Aufgaben als auch der Geräte-Abgleich des Lernstands, deshalb
  // steht die Zeile vor beiden Bausteinen.
  window.DASHCFG = {{ repo: {json.dumps(REPO)}, rt: {json.dumps(refresh_token or "")} }};

  // ---- Italienisch-Kurs: Lernstoff, Logik und abgeglichener Stand ----
  window.ITCORSO = {it_course_json};
  window.ITSTAND = {it_stand_json};
{IT_JS}
{TASK_JS}{refresh_js}
</script>
</body>
</html>'''


# ------------------------------------------------------- Verschlüsselung ---
def encrypt_page(plain_html, password):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    import hashlib
    # Deterministisch aus Inhalt + Passwort abgeleitet (kein Nonce-Reuse möglich,
    # da anderer Inhalt -> anderer Seed).
    seed = hashlib.sha256(password.encode() + plain_html.encode()).digest()
    salt = seed[:16]
    iv = hashlib.sha256(seed + b"iv").digest()[:12]
    ITER = 600_000
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER)
    ct = AESGCM(kdf.derive(password.encode())).encrypt(iv, plain_html.encode(), None)
    b64 = lambda b: base64.b64encode(b).decode()
    payload = json.dumps({"salt": b64(salt), "iv": b64(iv), "ct": b64(ct), "iter": ITER})
    return LOCK_TEMPLATE.replace("__PAYLOAD__", payload)


LOCK_TEMPLATE = '''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Mein Dashboard</title>
<style>
  :root { --bg:#f9f9f7; --card:#fcfcfb; --ink:#0b0b0b; --sub:#52514e; --border:rgba(11,11,11,0.10); --accent:#2a78d6; --err:#d03b3b; }
  @media (prefers-color-scheme: dark) {
    :root { --bg:#0d0d0d; --card:#1a1a19; --ink:#ffffff; --sub:#c3c2b7; --border:rgba(255,255,255,0.10); --accent:#3987e5; }
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:system-ui,-apple-system,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink);
         min-height:100vh; display:flex; align-items:center; justify-content:center; padding:24px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:14px; padding:32px; max-width:380px; width:100%; }
  h1 { font-size:18px; font-weight:650; margin-bottom:6px; }
  p { font-size:13px; color:var(--sub); margin-bottom:18px; }
  input[type=password] { width:100%; padding:10px 12px; font-size:15px; border:1px solid var(--border);
         border-radius:8px; background:var(--bg); color:var(--ink); margin-bottom:12px; }
  label { display:flex; gap:8px; align-items:center; font-size:13px; color:var(--sub); margin-bottom:16px; }
  button { width:100%; padding:10px; font-size:15px; font-weight:600; color:#fff; background:var(--accent);
         border:none; border-radius:8px; cursor:pointer; }
  .error { color:var(--err); font-size:13px; margin-top:10px; display:none; }
</style>
</head>
<body>
<div class="card">
  <h1>Mein Dashboard</h1>
  <p>Bitte Passwort eingeben, um das Dashboard zu entschlüsseln.</p>
  <form id="f">
    <input type="password" id="pw" placeholder="Passwort" autofocus autocomplete="current-password">
    <label><input type="checkbox" id="rem" checked> Auf diesem Gerät merken</label>
    <button type="submit">Entsperren</button>
    <div class="error" id="err">Falsches Passwort – bitte erneut versuchen.</div>
  </form>
</div>
<script>
const DATA = __PAYLOAD__;
const b64d = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
async function decrypt(pw) {
  const enc = new TextEncoder();
  const km = await crypto.subtle.importKey('raw', enc.encode(pw), 'PBKDF2', false, ['deriveKey']);
  const key = await crypto.subtle.deriveKey(
    { name:'PBKDF2', salt:b64d(DATA.salt), iterations:DATA.iter, hash:'SHA-256' },
    km, { name:'AES-GCM', length:256 }, false, ['decrypt']);
  const pt = await crypto.subtle.decrypt({ name:'AES-GCM', iv:b64d(DATA.iv) }, key, b64d(DATA.ct));
  return new TextDecoder().decode(pt);
}
async function tryUnlock(pw, remember) {
  try {
    const html = await decrypt(pw);
    if (remember) { try { localStorage.setItem('dash_pw', pw); } catch(e){} }
    document.open(); document.write(html); document.close();
    return true;
  } catch(e) { return false; }
}
document.getElementById('f').addEventListener('submit', async ev => {
  ev.preventDefault();
  const ok = await tryUnlock(document.getElementById('pw').value, document.getElementById('rem').checked);
  if (!ok) document.getElementById('err').style.display = 'block';
});
(async () => {
  let saved = null;
  try { saved = localStorage.getItem('dash_pw'); } catch(e){}
  if (saved) { const ok = await tryUnlock(saved, false); if (!ok) { try { localStorage.removeItem('dash_pw'); } catch(e){} } }
})();
</script>
</body>
</html>'''


# ------------------------------------------------------------------ main ---
def main():
    password = (os.environ.get("DASH_PASSWORD") or "").strip()
    if not password:
        sys.exit("FEHLER: Secret DASH_PASSWORD fehlt.")
    refresh_token = (os.environ.get("REFRESH_TOKEN") or "").strip() or None
    now = datetime.now(TZ)
    today = now.date()

    shows_note = releases_note = trello_note = podcast_note = weather_note = day_focus_note = None
    industry_note = digest_note = None

    # --- Markt: eigene Marken und beobachtete Ligen (per Secret anpassbar) ---
    def _lines_or_commas(raw, default):
        vals = [v.strip() for chunk in (raw or "").splitlines() for v in chunk.split(",") if v.strip()]
        return vals or list(default)

    own_brands = _lines_or_commas(os.environ.get("OWN_BRANDS"), OWN_BRANDS_DEFAULT)
    watch_leagues = _lines_or_commas(os.environ.get("WATCH_LEAGUES"), WATCH_LEAGUES_DEFAULT)

    # --- Italienisch: Lernstand über alle Geräte ---------------------------
    # Kommt ein Stand aus dem Browser mit (IT_SYNC), wird er mit dem
    # gespeicherten vereinigt und abgelegt. Sonst wird nur gelesen. Läuft ganz
    # ohne API und ohne neues Geheimnis.
    it_stand = it_sync(os.environ.get("IT_SYNC"))

    if os.environ.get("DASH_TEST") == "1":
        (tasks, done_today, events, cardshows, news, releases, trello, podcast,
         weather, day_focus, news_digest, cal_meta, industry,
         industry_digest) = testdata(today)
    else:
        token = (os.environ.get("TODOIST_TOKEN") or "").strip()
        # ICS_URL: einzelner Kalender (Bestand). ICS_URLS: beliebig viele weitere,
        # getrennt durch Zeilenumbruch oder Komma (z.B. "Privat" + "Feiertage in
        # Deutschland" zusätzlich zum Standard-Kalender) – alle werden zusammengeführt.
        def _norm_ics_url(u):
            # Apple/iCloud liefert "webcal://..."-Adressen – das ist nur ein Hinweis für
            # Kalender-Apps, sich zu abonnieren, und funktioniert per HTTP(S) genauso wie
            # ein normaler Link. requests kennt das Schema "webcal" aber nicht, daher hier
            # automatisch auf https:// umschreiben.
            if u.lower().startswith("webcal://"):
                return "https://" + u[len("webcal://"):]
            if u.lower().startswith("webcals://"):
                return "https://" + u[len("webcals://"):]
            return u

        ics_primary = (os.environ.get("ICS_URL") or "").strip()
        ics_extra_raw = (os.environ.get("ICS_URLS") or "").strip()
        ics_extra = [u.strip() for chunk in ics_extra_raw.splitlines() for u in chunk.split(",") if u.strip()]
        ics_list = [_norm_ics_url(u) for u in ([ics_primary] if ics_primary else []) + ics_extra]
        # Duplikate entfernen, Reihenfolge erhalten (falls dieselbe Adresse in ICS_URL und ICS_URLS steht)
        seen_ics, ics_list_dedup = set(), []
        for u in ics_list:
            if u not in seen_ics:
                seen_ics.add(u)
                ics_list_dedup.append(u)
        ics_list = ics_list_dedup
        # HOLIDAY_EXCLUDE: optionale Liste von Termin-/Feiertagsnamen (eine pro Zeile
        # oder durch Komma getrennt), die trotz gültigem Kalender-Feed nicht im
        # Dashboard erscheinen sollen (z.B. für dich irrelevante regionale Feiertage,
        # die sich über Googles "Feiertag ausblenden" NICHT aus dem iCal-Export entfernen
        # lassen, da das nur die eigene Google-Kalender-Ansicht betrifft).
        holiday_exclude_raw = (os.environ.get("HOLIDAY_EXCLUDE") or "").strip()
        holiday_exclude = [t.strip() for chunk in holiday_exclude_raw.splitlines() for t in chunk.split(",") if t.strip()]
        trello_key = (os.environ.get("TRELLO_KEY") or "").strip()
        trello_token = (os.environ.get("TRELLO_TOKEN") or "").strip()
        anthropic_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        # Häkchen aus dem Dashboard: kommen als Workflow-Eingabe an und werden
        # VOR dem Laden geschlossen, damit sie in der neuen Seite nicht mehr
        # auftauchen. Maximal 50 pro Lauf, damit ein kaputter Wert nicht in
        # eine lange Schleife läuft.
        close_raw = (os.environ.get("CLOSE_TASKS") or "").strip()
        close_ids = [x.strip() for x in close_raw.replace("\n", ",").split(",")
                     if x.strip().isdigit() or (x.strip() and x.strip().isalnum())][:50]
        if close_ids and token:
            close_todoist_tasks(token, close_ids)
        elif close_ids:
            print("Hinweis: Häkchen erhalten, aber kein TODOIST_TOKEN gesetzt.")

        tasks, done_today = fetch_todoist(token) if token else ([], 0)
        if ics_list:
            y0, m0 = ym_add(today.year, today.month, -1)
            y1, m1 = ym_add(today.year, today.month, MONTH_VIEW_HORIZON_MONTHS + 1)
            start = datetime.combine(date(y0, m0, 1) - timedelta(days=7), datetime.min.time(), TZ)
            end = datetime.combine(date(y1, m1, 1) + timedelta(days=7), datetime.min.time(), TZ)
            events, cal_meta = fetch_events(ics_list, start, end, exclude_titles=holiday_exclude)
            print(f"Kalender: {len(events)} Termine geladen ({len(ics_list)} Kalender-Adresse(n))"
                  + (f", {len(holiday_exclude)} Titel-Fragment(e) ausgeschlossen" if holiday_exclude else ""))
        else:
            events, cal_meta = [], []
        cardshows, shows_note = fetch_cardshows(today)
        releases, releases_note = fetch_releases(today)
        trello, trello_note = fetch_trello(trello_key, trello_token, today)
        weather, weather_note = fetch_weather()
        day_focus, day_focus_note = fetch_day_focus(anthropic_key, tasks, events, cardshows, trello, today)
        news = fetch_news()
        news_digest = summarize_news_digest(news, anthropic_key, today)
        podcast, podcast_note = fetch_podcast(anthropic_key)

        # Hinweis: Der Händler-Monitor ist stillgelegt (siehe Kommentar bei
        # fetch_shopwatch) – hier wird bewusst nichts abgerufen.

        # --- Markt · Branchen- & Lizenz-Radar ----------------------------
        # INDUSTRY_FEEDS: optional eigene Quellen, eine pro Zeile als
        # "Anzeigename | https://.../feed". Ohne Secret gelten die geprüften
        # Standardquellen.
        feeds = []
        for line in (os.environ.get("INDUSTRY_FEEDS") or "").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            nm, u = line.split("|", 1)
            if u.strip().startswith("http"):
                feeds.append((nm.strip() or u.strip(), u.strip()))
        feeds = feeds or list(INDUSTRY_FEEDS_DEFAULT)
        industry_keywords = _lines_or_commas(os.environ.get("INDUSTRY_KEYWORDS"),
                                            INDUSTRY_KEYWORDS_DEFAULT)
        try:
            industry = fetch_industry(feeds, industry_keywords)
        except Exception as e:
            print(f"Hinweis: Branchen-Radar fehlgeschlagen ({e}).")
            industry, industry_note = [], "Branchenquellen derzeit nicht erreichbar."
        industry_digest, digest_note = summarize_industry(industry, anthropic_key, today)

    releases = enrich_releases(releases, own_brands)

    plain = build_html(tasks, done_today, events, cardshows, news, refresh_token,
                       shows_note, releases, releases_note, trello, trello_note,
                       podcast, podcast_note, weather, weather_note,
                       day_focus, day_focus_note, news_digest, cal_meta,
                       industry, industry_note,
                       industry_digest, digest_note, watch_leagues,
                       it_stand=it_stand)
    encrypted = encrypt_page(plain, password)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(encrypted)
    trello_n = sum(len(l["cards"]) for b in trello for l in b["lists"])
    print(f"OK: index.html geschrieben ({len(encrypted)} Zeichen), {len(tasks)} Aufgaben, "
          f"{len(events)} Termine, {len(cardshows)} Cardshows, {len(releases)} Releases, "
          f"{trello_n} Trello-Karten, {len(podcast)} Podcast-Folgen, {len(weather)} Wetter-Tage, "
          f"{sum(len(s['items']) for s in industry)} Branchenmeldungen, "
          f"Stand {now.strftime('%H:%M')} Uhr")


if __name__ == "__main__":
    main()
