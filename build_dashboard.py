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
PODCAST_MODEL = os.environ.get("PODCAST_MODEL", "claude-haiku-4-5-20251001")
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
            "content": t.get("content", ""),
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
def fetch_events(ics_urls, start, end):
    """Google-Kalender-Termine [start, end) inkl. aufgelöster Serientermine –
    über einen oder mehrere Kalender (ICS_URL + optional ICS_URLS) zusammengeführt.
    Eine einzelne nicht ladbare Kalender-Adresse bricht den Bau nicht ab (Warnung
    statt Abbruch), nur wenn KEINE der Adressen ladbar ist, wird abgebrochen."""
    import requests, icalendar, recurring_ical_events
    if isinstance(ics_urls, str):
        ics_urls = [ics_urls]
    out, seen, any_ok, errors = [], set(), False, []
    for ics_url in ics_urls:
        try:
            resp = requests.get(ics_url, timeout=30, headers=UA)
            if resp.status_code != 200:
                raise ValueError(f"HTTP {resp.status_code}")
            cal = icalendar.Calendar.from_ical(resp.content)
        except Exception as e:
            short = ics_url[:70] + ("…" if len(ics_url) > 70 else "")
            errors.append(f"{short}: {e}")
            print(f"Hinweis: Kalender-Adresse nicht ladbar ({short}): {e}")
            continue
        any_ok = True
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
            # Dedup (z.B. falls dieselbe Kalender-Adresse versehentlich doppelt hinterlegt ist)
            key = (uid, d.isoformat(), tm)
            if key in seen:
                continue
            seen.add(key)
            out.append({"date": d.isoformat(), "end_date": end_d.isoformat(), "time": tm, "end_time": te, "title": title})
    if not any_ok:
        sys.exit("FEHLER: Keine der hinterlegten Kalender-Adressen (ICS_URL/ICS_URLS) konnte geladen werden – "
                  + " | ".join(errors) + ". Bitte in Google Kalender → Einstellungen → jeweiliger Kalender → "
                  "'Kalender integrieren' die 'Privatadresse im iCal-Format' (bzw. bei öffentlichen Kalendern "
                  "wie Feiertagen die 'Öffentliche Adresse im iCal-Format') neu kopieren.")
    out.sort(key=lambda e: (e["date"], e["time"]))
    return out


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


# ------------------------------------------------------------- Testdaten ---
def testdata(today):
    tasks = [
        {"area": "Privat", "content": "Einkauf für die Woche planen", "project": None, "due": today.isoformat(), "prio_hoch": False},
        {"area": "Arbeit", "content": "Wochenplanung: Top-3-Prioritäten", "project": "Projekt Alpha", "due": today.isoformat(), "prio_hoch": True},
        {"area": "Studium", "content": "Übungsblatt bearbeiten", "project": "Mathe II", "due": (today + timedelta(days=3)).isoformat(), "prio_hoch": True},
    ]
    events = [
        {"date": (today + timedelta(days=3)).isoformat(), "end_date": (today + timedelta(days=3)).isoformat(),
         "time": "08:00", "end_time": "08:20", "title": "Physio ZAR"},
        {"date": (today + timedelta(days=5)).isoformat(), "end_date": (today + timedelta(days=6)).isoformat(),
         "time": "", "end_time": "", "title": "[Sportmanagement] Grundlagen Sportbusiness · Vor Ort: Nürtingen"},
        {"date": (today + timedelta(days=8)).isoformat(), "end_date": (today + timedelta(days=8)).isoformat(),
         "time": "17:15", "end_time": "17:35", "title": "Physio ZAR"},
        {"date": (today + timedelta(days=45)).isoformat(), "end_date": (today + timedelta(days=47)).isoformat(),
         "time": "", "end_time": "", "title": "Urlaub Start"},
        {"date": (today + timedelta(days=100)).isoformat(), "end_date": (today + timedelta(days=100)).isoformat(),
         "time": "10:00", "end_time": "12:00", "title": "Zahnarzt"},
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
    return tasks, 2, events, shows, news, releases, trello, podcast, weather, day_focus, news_digest


# ------------------------------------------------------------------ HTML ---
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
            chips += f'<div class="chip{past}" title="{esc(label)}">{esc(label)}</div>'
        cells.append(f'<div class="{cls}"><div class="num">{num}</div>{chips}</div>')
        d += timedelta(days=1)
    head = "".join(f"<div>{w}</div>" for w in WD)
    return f'<div class="month-head">{head}</div><div class="month-grid">{"".join(cells)}</div>'


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


def build_html(tasks, done_today, events, cardshows, news, refresh_token,
               shows_note=None, releases=None, releases_note=None,
               trello=None, trello_note=None, podcast=None, podcast_note=None,
               weather=None, weather_note=None, day_focus=None, day_focus_note=None,
               news_digest=None):
    releases = releases or []
    trello = trello or []
    podcast = podcast or []
    weather = weather or []
    news_digest = news_digest or {}
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
            items.append(f'<li><span class="box"></span><span class="txt">{esc(t["content"])}{meta_html}</span>{prio}</li>')
        body = "\n".join(items) if items else '<li class="none">Keine offenen Aufgaben 🎉</li>'
        area_cards.append(f'''
    <div class="area {area_var[area]}">
      <div class="area-head"><h2><span class="dot"></span>{area}</h2><span class="count">{len(atasks)} offen</span></div>
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

    if todays_ev:
        today_panel = "".join(
            f'<div class="event"><span class="time">{e["time"]}–{e["end_time"]}</span><span>{esc(ev_label(e))}</span></div>'
            if e["time"] else
            f'<div class="event"><span class="time">ganztägig</span><span>{esc(ev_label(e))}</span></div>'
            for e in todays_ev)
    else:
        today_panel = (f'<div class="empty"><span class="big">Keine Termine heute.</span><br>'
                       f'Nächster Termin: <strong style="color:var(--text-secondary)">{next_ev_title}</strong> ({next_ev_sub}).</div>')

    # --- Woche
    day_cards = []
    for d in week_days:
        iso = d.isoformat()
        cls = "day today" if d == today else "day"
        parts = [f'<h3>{WD[d.weekday()]} <span>{d.day:02d}.{d.month:02d}.{" · heute" if d == today else ""}</span></h3>']
        for e in ev_by_date.get(iso, []):
            tstr = f'<span class="t">{e["time"]}–{e["end_time"]}</span> · ' if e["time"] else ""
            parts.append(f'<div class="ev">{tstr}{esc(ev_label(e))}</div>')
        for t in task_by_date.get(iso, []):
            parts.append(f'<div class="due"><span class="d" style="background:var(--{area_var[t["area"]]})"></span>{esc(t["content"])}</div>')
        day_cards.append(f'<div class="{cls}">{"".join(parts)}</div>')

    # --- Monat: 14 Monate (Vormonat bis +12) mit Dropdown und Pfeilen
    month_list = [ym_add(today.year, today.month, k) for k in range(-1, 13)]
    options, month_wraps = [], []
    for (y, m) in month_list:
        key = f"{y}-{m:02d}"
        sel = " selected" if (y, m) == (today.year, today.month) else ""
        options.append(f'<option value="{key}"{sel}>{MONTHS[m-1]} {y}</option>')
        active = " active" if (y, m) == (today.year, today.month) else ""
        month_wraps.append(f'<div class="mwrap{active}" data-ym="{key}">{month_grid_html(y, m, ev_by_date, today)}</div>')

    # --- Jahr: alle Termine der nächsten 12 Monate, nach Monat gruppiert
    horizon = ym_add(today.year, today.month, 12)
    year_groups, cur_key = [], None
    upcoming = [e for e in events if e["date"] >= today.isoformat()
                and date.fromisoformat(e["date"]) < date(horizon[0], horizon[1], 1)]
    for e in upcoming:
        d = date.fromisoformat(e["date"])
        d_end = date.fromisoformat(e.get("end_date", e["date"]))
        key = f"{MONTHS[d.month-1]} {d.year}"
        if key != cur_key:
            year_groups.append(f'<h3 class="ygroup">{key}</h3>')
            cur_key = key
        tstr = f'{e["time"]}–{e["end_time"]}' if e["time"] else "ganztägig"
        if d_end == d:
            dstr = f"{WD[d.weekday()]}, {d.day:02d}.{d.month:02d}."
        elif d_end.month == d.month and d_end.year == d.year:
            dstr = f"{d.day:02d}.–{d_end.day:02d}.{d_end.month:02d}."
        else:
            dstr = f"{d.day:02d}.{d.month:02d}.–{d_end.day:02d}.{d_end.month:02d}."
        year_groups.append(
            f'<div class="event"><span class="time">{dstr} · {tstr}</span>'
            f'<span>{esc(e["title"])}</span></div>')
    year_html = "".join(year_groups) if year_groups else \
        '<div class="empty">Keine Termine in den nächsten 12 Monaten.</div>'

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
        cat = f'<span class="rel-cat">{esc(r["category"])}</span>' if r.get("category") else ""
        return (f'<div class="rel{" past" if past else ""}" data-maker="{esc(r["maker"])}" '
                f'data-cat="{esc(r.get("category") or "")}" data-month="{mkey}">'
                f'<span class="rel-date">{dtxt}</span>'
                f'<span class="mk" title="Nach {esc(r["maker"])} filtern">{esc(r["maker"])}</span>'
                f'<span class="rel-name">{name}</span>{cat}{cl}</div>')

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
    rel_filters_html = f'''
    <div class="filterrow"><span class="flabel">Hersteller:</span><button class="fchip active" data-dim="maker" data-v="">Alle</button>{maker_chips}</div>
    <div class="filterrow"><span class="flabel">Kategorie:</span><button class="fchip active" data-dim="cat" data-v="">Alle</button>{cat_chips}</div>
    <div class="filterrow"><span class="flabel">Monat:</span><button class="fchip active" data-dim="month" data-v="">Alle</button>{"".join(rel_month_chips)}</div>'''
    rel_stat = (f"{len(rel_upcoming)} kommende · {len(rel_tbd)} ohne Termin · {len(rel_past)} vergangene"
                if releases else "")
    releases_note = releases_note or ""
    rel_body = "".join(rel_parts) if rel_parts else '<div class="empty">Keine kommenden Releases gefunden.</div>'

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
    --good: #0ca30c; --good-text: #006300; --done-ink: #898781;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff; --text-secondary: #c3c2b7;
      --muted: #898781; --hairline: #2c2c2a; --border: rgba(255,255,255,0.10);
      --privat: #199e70; --arbeit: #3987e5; --studium: #9085e9; --trello: #c98500; --podcast: #008300; --focus: #22a6c9; --good-text: #0ca30c;
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
  .rel-cat {{ font-size: 12px; color: var(--muted); white-space: nowrap; }}
  .cl {{ font-size: 12px; color: var(--good-text); text-decoration: none; border: 1px solid var(--privat);
        border-radius: 99px; padding: 1px 8px; white-space: nowrap; }}
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
    <button class="active" data-view="view-today">Heute</button>
    <button data-view="view-week">Woche</button>
    <button data-view="view-month">Monat</button>
    <button data-view="view-year">Jahr</button>
    <button data-view="view-shows">Cardshows</button>
    <button data-view="view-releases">Releases</button>
    <button data-view="view-news">News</button>
    <button data-view="view-podcast">Podcast</button>
  </nav>

  <div id="view-today" class="view active">
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
  <section class="trellowrap">
    <div class="trello-head"><h2>🗂️ Trello</h2><span class="count">{trello_total} offen</span></div>
    {trello_html}
  </section>
  <section class="row2">
    <div class="panel"><h2>📅 Termine heute</h2>{today_panel}</div>
  </section>
  </div>

  <div id="view-week" class="view">
    <h2 class="vtitle">Woche im Überblick · {monday_iso} (KW {kw})</h2>
    <div class="week-grid">{"".join(day_cards)}</div>
    <div class="legend">
      <span><span class="d" style="background:var(--arbeit)"></span>Termin (Kalender)</span>
      <span><span class="d" style="background:var(--privat)"></span>Aufgabe Privat</span>
      <span><span class="d" style="background:var(--arbeit)"></span>Aufgabe Arbeit</span>
      <span><span class="d" style="background:var(--studium)"></span>Aufgabe Studium</span>
    </div>
  </div>

  <div id="view-month" class="view">
    <div class="mnav">
      <button id="mprev" title="Vorheriger Monat">‹</button>
      <select id="msel">{"".join(options)}</select>
      <button id="mnext" title="Nächster Monat">›</button>
    </div>
    {"".join(month_wraps)}
  </div>

  <div id="view-year" class="view">
    <h2 class="vtitle">Alle Termine · nächste 12 Monate</h2>
    {year_html}
  </div>

  <div id="view-shows" class="view">
    <h2 class="vtitle">Cardshows &amp; Trade Events</h2>
    <div class="srcline">Quelle: <a href="https://gradedmoments.de/cardshows/" target="_blank" rel="noopener">gradedmoments.de</a> · Stand {stand} Uhr{" · " + shows_stat if shows_stat else ""}{" · " + esc(shows_note) if shows_note else ""} · <span style="color:var(--good-text)">🇩🇪 = Show in Deutschland</span></div>
    {shows_filter}
    {shows_html}
  </div>

  <div id="view-releases" class="view">
    <h2 class="vtitle">Release-Kalender · Trading Cards</h2>
    <div class="srcline">Quelle: <a href="{RELEASES_URL}" target="_blank" rel="noopener">collectosk.com</a> · Stand {stand} Uhr{" · " + rel_stat if rel_stat else ""}{" · " + esc(releases_note) if releases_note else ""} · Tipp: Hersteller-Badge anklicken filtert direkt</div>
    {rel_filters_html}
    {rel_body}
    {rel_past_html}
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
  const msel = document.getElementById('msel');
  function showMonth(key) {{
    document.querySelectorAll('.mwrap').forEach(w => w.classList.toggle('active', w.dataset.ym === key));
    msel.value = key;
  }}
  msel.addEventListener('change', () => showMonth(msel.value));
  document.getElementById('mprev').addEventListener('click', () => {{
    if (msel.selectedIndex > 0) {{ msel.selectedIndex--; showMonth(msel.value); }}
  }});
  document.getElementById('mnext').addEventListener('click', () => {{
    if (msel.selectedIndex < msel.options.length - 1) {{ msel.selectedIndex++; showMonth(msel.value); }}
  }});
  // Cardshows: Monats-Chips
  document.querySelectorAll('#view-shows .fchip').forEach(c => c.addEventListener('click', () => {{
    document.querySelectorAll('#view-shows .fchip').forEach(x => x.classList.toggle('active', x === c));
    const v = c.dataset.v;
    document.querySelectorAll('#view-shows .sgroup').forEach(g =>
      g.style.display = (!v || g.dataset.month === v) ? '' : 'none');
  }}));
  // Releases: kombinierbare Filter (Hersteller + Kategorie + Monat)
  const relF = {{ maker: '', cat: '', month: '' }};
  function applyRel() {{
    document.querySelectorAll('#view-releases .rel').forEach(el => {{
      const ok = (!relF.maker || el.dataset.maker === relF.maker)
        && (!relF.cat || el.dataset.cat === relF.cat)
        && (!relF.month || el.dataset.month === relF.month);
      el.style.display = ok ? '' : 'none';
    }});
    document.querySelectorAll('#view-releases .mgroup').forEach(g => {{
      const any = Array.from(g.querySelectorAll('.rel')).some(e => e.style.display !== 'none');
      g.style.display = any ? '' : 'none';
    }});
    document.querySelectorAll('#view-releases .fchip').forEach(c =>
      c.classList.toggle('active', relF[c.dataset.dim] === c.dataset.v));
  }}
  document.querySelectorAll('#view-releases .fchip').forEach(c => c.addEventListener('click', () => {{
    relF[c.dataset.dim] = c.dataset.v; applyRel();
  }}));
  document.querySelectorAll('#view-releases .mk').forEach(b => b.addEventListener('click', () => {{
    const v = b.textContent.trim();
    relF.maker = (relF.maker === v) ? '' : v; applyRel();
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
  }})();{refresh_js}
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
    if os.environ.get("DASH_TEST") == "1":
        (tasks, done_today, events, cardshows, news, releases, trello, podcast,
         weather, day_focus, news_digest) = testdata(today)
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
        trello_key = (os.environ.get("TRELLO_KEY") or "").strip()
        trello_token = (os.environ.get("TRELLO_TOKEN") or "").strip()
        anthropic_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
        tasks, done_today = fetch_todoist(token) if token else ([], 0)
        if ics_list:
            y0, m0 = ym_add(today.year, today.month, -1)
            y1, m1 = ym_add(today.year, today.month, 13)
            start = datetime.combine(date(y0, m0, 1) - timedelta(days=7), datetime.min.time(), TZ)
            end = datetime.combine(date(y1, m1, 1) + timedelta(days=7), datetime.min.time(), TZ)
            events = fetch_events(ics_list, start, end)
            print(f"Kalender: {len(events)} Termine geladen ({len(ics_list)} Kalender-Adresse(n))")
        else:
            events = []
        cardshows, shows_note = fetch_cardshows(today)
        releases, releases_note = fetch_releases(today)
        trello, trello_note = fetch_trello(trello_key, trello_token, today)
        weather, weather_note = fetch_weather()
        day_focus, day_focus_note = fetch_day_focus(anthropic_key, tasks, events, cardshows, trello, today)
        news = fetch_news()
        news_digest = summarize_news_digest(news, anthropic_key, today)
        podcast, podcast_note = fetch_podcast(anthropic_key)

    plain = build_html(tasks, done_today, events, cardshows, news, refresh_token,
                       shows_note, releases, releases_note, trello, trello_note,
                       podcast, podcast_note, weather, weather_note,
                       day_focus, day_focus_note, news_digest)
    encrypted = encrypt_page(plain, password)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(encrypted)
    trello_n = sum(len(l["cards"]) for b in trello for l in b["lists"])
    print(f"OK: index.html geschrieben ({len(encrypted)} Zeichen), {len(tasks)} Aufgaben, "
          f"{len(events)} Termine, {len(cardshows)} Cardshows, {len(releases)} Releases, "
          f"{trello_n} Trello-Karten, {len(podcast)} Podcast-Folgen, {len(weather)} Wetter-Tage, "
          f"Stand {now.strftime('%H:%M')} Uhr")


if __name__ == "__main__":
    main()
