#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baut Moritz' persönliches Dashboard und verschlüsselt es zu index.html.

Datenquellen:
  - Todoist REST API v2 (Aufgaben, Projekte)          [Secret: TODOIST_TOKEN]
  - Google Kalender, private iCal-Adresse (Termine)    [Secret: ICS_URL]
Verschlüsselung:
  - AES-256-GCM, Schlüssel via PBKDF2-SHA256           [Secret: DASH_PASSWORD]
Optional:
  - REFRESH_TOKEN: Fine-grained PAT (nur Actions:write) für den
    "Jetzt aktualisieren"-Knopf. Fehlt er, verlinkt der Knopf auf die Actions-Seite.

Testmodus: DASH_TEST=1 nutzt eingebaute Beispieldaten statt der APIs.
"""
import os, sys, json, base64, html
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
REPO = os.environ.get("GITHUB_REPOSITORY", "MoeEllis/dashboard-mj-x7k2")
AREAS = ["Privat", "Arbeit", "Studium"]
AREA_KEYS = {"privat": "Privat", "arbeit": "Arbeit", "studium": "Studium"}
WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
WD_LONG = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

esc = html.escape


# ---------------------------------------------------------------- Todoist ---
def fetch_todoist(token):
    """Liefert (tasks, done_today). tasks: Liste von Dicts mit
    area, content, project, due (date|None), prio_hoch (bool)."""
    import requests
    H = {"Authorization": f"Bearer {token}"}
    projects = requests.get("https://api.todoist.com/rest/v2/projects", headers=H, timeout=30).json()
    raw_tasks = requests.get("https://api.todoist.com/rest/v2/tasks", headers=H, timeout=30).json()

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
            continue  # Projekte außerhalb von Privat/Arbeit/Studium ignorieren
        due = None
        if t.get("due") and t["due"].get("date"):
            due = t["due"]["date"][:10]
        tasks.append({
            "area": area,
            "content": t.get("content", ""),
            "project": proj["name"] if proj["id"] != top["id"] else None,
            "due": due,
            "prio_hoch": t.get("priority", 1) >= 4,  # Todoist: 4 == P1
        })

    done_today = 0
    try:
        since = datetime.now(TZ).strftime("%Y-%m-%dT00:00:00")
        r = requests.get("https://api.todoist.com/sync/v9/completed/get_all",
                         headers=H, params={"since": since, "limit": 200}, timeout=30)
        done_today = len(r.json().get("items", []))
    except Exception:
        pass
    return tasks, done_today


# ------------------------------------------------------------------- iCal ---
def fetch_events(ics_url, start, end):
    """Termine [start, end) als Liste von Dicts: date, time ('' bei ganztägig),
    end_time, title. Nutzt icalendar + recurring_ical_events (löst Serien auf)."""
    import requests, icalendar, recurring_ical_events
    cal = icalendar.Calendar.from_ical(requests.get(ics_url, timeout=30).content)
    out = []
    for ev in recurring_ical_events.of(cal).between(start, end):
        dtstart = ev.get("DTSTART").dt
        dtend = ev.get("DTEND").dt if ev.get("DTEND") else None
        title = str(ev.get("SUMMARY", "Termin"))
        if isinstance(dtstart, datetime):
            local = dtstart.astimezone(TZ)
            d, tm = local.date(), local.strftime("%H:%M")
            te = dtend.astimezone(TZ).strftime("%H:%M") if isinstance(dtend, datetime) else ""
        else:  # ganztägig
            d, tm, te = dtstart, "", ""
        out.append({"date": d.isoformat(), "time": tm, "end_time": te, "title": title})
    out.sort(key=lambda e: (e["date"], e["time"]))
    return out


# ------------------------------------------------------------- Testdaten ---
def testdata(today):
    tasks = [
        {"area": "Privat", "content": "Einkauf für die Woche planen", "project": None, "due": today.isoformat(), "prio_hoch": False},
        {"area": "Privat", "content": "Physio-Termin vorbereiten", "project": None, "due": (today + timedelta(days=2)).isoformat(), "prio_hoch": False},
        {"area": "Arbeit", "content": "Wochenplanung: Top-3-Prioritäten", "project": "Projekt Alpha", "due": today.isoformat(), "prio_hoch": True},
        {"area": "Arbeit", "content": "Projekt-Update an Team", "project": "Projekt Beta", "due": (today + timedelta(days=1)).isoformat(), "prio_hoch": False},
        {"area": "Studium", "content": "Übungsblatt bearbeiten", "project": "Mathe II", "due": (today + timedelta(days=3)).isoformat(), "prio_hoch": True},
        {"area": "Studium", "content": "Skript nacharbeiten", "project": "Info I", "due": None, "prio_hoch": False},
    ]
    events = [
        {"date": (today + timedelta(days=3)).isoformat(), "time": "08:00", "end_time": "08:20", "title": "Physio ZAR"},
        {"date": (today + timedelta(days=8)).isoformat(), "time": "17:15", "end_time": "17:35", "title": "Physio ZAR"},
    ]
    return tasks, 2, events


# ------------------------------------------------------------------ HTML ---
def build_html(tasks, done_today, events, refresh_token):
    now = datetime.now(TZ)
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]
    month_first = today.replace(day=1)
    next_month = (month_first.replace(day=28) + timedelta(days=7)).replace(day=1)
    grid_start = month_first - timedelta(days=month_first.weekday())
    grid_end = next_month + timedelta(days=(7 - next_month.weekday()) % 7)

    ev_by_date = {}
    for e in events:
        ev_by_date.setdefault(e["date"], []).append(e)
    task_by_date = {}
    for t in tasks:
        if t["due"]:
            task_by_date.setdefault(t["due"], []).append(t)

    area_var = {"Privat": "privat", "Arbeit": "arbeit", "Studium": "studium"}

    def fmt_date_line():
        return f"{WD_LONG[today.weekday()]}, {today.day}. {MONTHS[today.month-1]} {today.year} · Stand {now.strftime('%H:%M')} Uhr"

    def due_label(iso):
        d = date.fromisoformat(iso)
        if d == today: return "heute"
        if d == today + timedelta(days=1): return "morgen"
        if d < today: return f"überfällig ({d.day}.{d.month:02d}.)"
        return f"bis {WD[d.weekday()]}, {d.day:02d}.{d.month:02d}."

    # --- Heute: Bereichs-Karten
    area_cards = []
    for area in AREAS:
        atasks = [t for t in tasks if t["area"] == area]
        items = []
        for t in atasks:
            meta = " · ".join(x for x in [t["project"], due_label(t["due"]) if t["due"] else None] if x)
            prio = '<span class="prio hoch">hoch</span>' if t["prio_hoch"] else ""
            meta_html = f'<span class="meta">{esc(meta)}</span>' if meta else ""
            items.append(f'<li><span class="box"></span><span class="txt">{esc(t["content"])}'
                         f'{meta_html}</span>{prio}</li>')
        body = "\n".join(items) if items else '<li class="none">Keine offenen Aufgaben 🎉</li>'
        area_cards.append(f'''
    <div class="area {area_var[area]}">
      <div class="area-head"><h2><span class="dot"></span>{area}</h2><span class="count">{len(atasks)} offen</span></div>
      <ul class="tasks">{body}</ul>
    </div>''')

    # --- Kacheln
    open_total = len(tasks)
    per_area = " · ".join(f"{a} {len([t for t in tasks if t['area']==a])}" for a in AREAS)
    todays_ev = ev_by_date.get(today.isoformat(), [])
    future = [e for e in events if e["date"] >= today.isoformat() and (e["date"] > today.isoformat() or e["time"] >= now.strftime("%H:%M") or e["time"] == "")]
    if future:
        ne = future[0]
        nd = date.fromisoformat(ne["date"])
        next_ev_title = esc(ne["title"])
        next_ev_sub = f"{WD[nd.weekday()]}, {nd.day:02d}.{nd.month:02d}." + (f" · {ne['time']}" + (f"–{ne['end_time']}" if ne['end_time'] else "") if ne['time'] else " · ganztägig")
    else:
        next_ev_title, next_ev_sub = "—", "keine anstehenden Termine"
    week_ev_count = sum(1 for e in events if monday.isoformat() <= e["date"] <= week_days[6].isoformat())

    # --- Termine heute Panel
    if todays_ev:
        rows = "".join(f'<div class="event"><span class="time">{e["time"]}–{e["end_time"]}</span><span>{esc(e["title"])}</span></div>'
                       if e["time"] else f'<div class="event"><span class="time">ganztägig</span><span>{esc(e["title"])}</span></div>'
                       for e in todays_ev)
        today_panel = rows
    else:
        today_panel = f'<div class="empty"><span class="big">Keine Termine heute.</span><br>Nächster Termin: <strong style="color:var(--text-secondary)">{next_ev_title}</strong> ({next_ev_sub}).</div>'

    # --- Woche
    day_cards = []
    for d in week_days:
        iso = d.isoformat()
        cls = "day today" if d == today else "day"
        parts = [f'<h3>{WD[d.weekday()]} <span>{d.day:02d}.{d.month:02d}.{" · heute" if d == today else ""}</span></h3>']
        for e in ev_by_date.get(iso, []):
            tstr = f'<span class="t">{e["time"]}–{e["end_time"]}</span> · ' if e["time"] else ""
            parts.append(f'<div class="ev">{tstr}{esc(e["title"])}</div>')
        for t in task_by_date.get(iso, []):
            parts.append(f'<div class="due"><span class="d" style="background:var(--{area_var[t["area"]]})"></span>{esc(t["content"])}</div>')
        day_cards.append(f'<div class="{cls}">{"".join(parts)}</div>')

    # --- Monat
    mcells = []
    d = grid_start
    while d < grid_end:
        iso = d.isoformat()
        cls = "mday"
        if d.month != today.month: cls += " out"
        if d == today: cls += " today"
        num = f"{d.day:02d}.{d.month:02d}." if d.month != today.month else str(d.day)
        chips = ""
        for e in ev_by_date.get(iso, []):
            past = " past" if iso < today.isoformat() else ""
            label = (e["time"] + " " if e["time"] else "") + e["title"]
            chips += f'<div class="chip{past}">{esc(label)}</div>'
        mcells.append(f'<div class="{cls}"><div class="num">{num}</div>{chips}</div>')
        d += timedelta(days=1)

    monday_iso = f"{monday.day}.–{week_days[6].day}. {MONTHS[week_days[6].month-1]} {week_days[6].year}"
    kw = today.isocalendar()[1]

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
    --privat: #1baf7a; --arbeit: #2a78d6; --studium: #4a3aa7;
    --good: #0ca30c; --good-text: #006300; --done-ink: #898781;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --surface-1: #1a1a19; --page: #0d0d0d; --text-primary: #ffffff; --text-secondary: #c3c2b7;
      --muted: #898781; --hairline: #2c2c2a; --border: rgba(255,255,255,0.10);
      --privat: #199e70; --arbeit: #3987e5; --studium: #9085e9; --good-text: #0ca30c;
    }}
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background: var(--page); color: var(--text-primary); padding: 24px; min-height: 100vh; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; }}
  header {{ margin-bottom: 16px; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }}
  header h1 {{ font-size: 22px; font-weight: 650; letter-spacing: -0.01em; }}
  header .date {{ color: var(--text-secondary); font-size: 14px; margin-top: 2px; }}
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
  .row2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .panel {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 16px; }}
  .panel h2 {{ font-size: 15px; font-weight: 650; margin-bottom: 12px; }}
  .event {{ display: flex; gap: 12px; align-items: baseline; padding: 8px 0; border-bottom: 1px solid var(--hairline); font-size: 14px; }}
  .event:last-child {{ border-bottom: none; }}
  .event .time {{ color: var(--text-secondary); font-variant-numeric: tabular-nums; white-space: nowrap; min-width: 110px; }}
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
  .month-head {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; font-size: 12px; color: var(--muted); margin-bottom: 6px; text-align: center; }}
  .month-grid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-bottom: 20px; }}
  .mday {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; min-height: 72px; padding: 6px; font-size: 12px; }}
  .mday .num {{ font-weight: 600; font-size: 12px; margin-bottom: 4px; color: var(--text-secondary); }}
  .mday.out {{ opacity: .4; }}
  .mday.today {{ border-color: var(--arbeit); box-shadow: 0 0 0 1px var(--arbeit); }}
  .mday.today .num {{ color: var(--arbeit); }}
  .chip {{ font-size: 10.5px; line-height: 1.3; padding: 2px 5px; border-radius: 6px; background: rgba(42,120,214,0.12); border-left: 2px solid var(--arbeit); margin-bottom: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .chip.past {{ opacity: .55; }}
  footer {{ color: var(--muted); font-size: 12px; line-height: 1.5; border-top: 1px solid var(--hairline); padding-top: 12px; }}
  footer strong {{ color: var(--text-secondary); font-weight: 600; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>Mein Dashboard</h1>
      <div class="date">{fmt_date_line()}</div>
    </div>
    <div>{refresh_html}</div>
  </header>

  <nav class="viewnav">
    <button class="active" data-view="view-today">Heute</button>
    <button data-view="view-week">Woche</button>
    <button data-view="view-month">Monat</button>
  </nav>

  <div id="view-today" class="view active">
  <section class="tiles">
    <div class="tile"><div class="label">Offene Aufgaben</div><div class="value">{open_total}</div><div class="sub">{per_area}</div></div>
    <div class="tile"><div class="label">Heute erledigt</div><div class="value">{done_today}</div><div class="sub">Weiter so</div></div>
    <div class="tile"><div class="label">Nächster Termin</div><div class="value small">{next_ev_title}</div><div class="sub">{next_ev_sub}</div></div>
    <div class="tile"><div class="label">Termine diese Woche</div><div class="value">{week_ev_count}</div><div class="sub">KW {kw}</div></div>
  </section>
  <section class="areas">{"".join(area_cards)}
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
    <h2 class="vtitle">Monat im Überblick · {MONTHS[today.month-1]} {today.year}</h2>
    <div class="month-head"><div>Mo</div><div>Di</div><div>Mi</div><div>Do</div><div>Fr</div><div>Sa</div><div>So</div></div>
    <div class="month-grid">{"".join(mcells)}</div>
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
  }});{refresh_js}
</script>
</body>
</html>'''


# ------------------------------------------------------- Verschlüsselung ---
def encrypt_page(plain_html, password):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    import hashlib
    # Deterministisch aus Inhalt + Passwort abgeleitet: identischer Inhalt
    # ergibt identische Datei -> kein unnötiger Commit alle 30 Minuten.
    # (Nonce-Wiederverwendung ist ausgeschlossen: anderer Inhalt -> anderer Seed.)
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
    password = os.environ.get("DASH_PASSWORD")
    if not password:
        sys.exit("FEHLER: Secret DASH_PASSWORD fehlt.")
    refresh_token = os.environ.get("REFRESH_TOKEN") or None
    now = datetime.now(TZ)
    today = now.date()

    if os.environ.get("DASH_TEST") == "1":
        tasks, done_today, events = testdata(today)
    else:
        token, ics = os.environ.get("TODOIST_TOKEN"), os.environ.get("ICS_URL")
        tasks, done_today = fetch_todoist(token) if token else ([], 0)
        if ics:
            month_first = today.replace(day=1)
            start = datetime.combine(min(today - timedelta(days=today.weekday()), month_first), datetime.min.time(), TZ)
            next_month = (month_first.replace(day=28) + timedelta(days=7)).replace(day=1)
            end = datetime.combine(next_month + timedelta(days=7), datetime.min.time(), TZ)
            events = fetch_events(ics, start, end)
        else:
            events = []

    plain = build_html(tasks, done_today, events, refresh_token)
    encrypted = encrypt_page(plain, password)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(encrypted)
    print(f"OK: index.html geschrieben ({len(encrypted)} Zeichen), "
          f"{len(tasks)} Aufgaben, {len(events)} Termine, Stand {now.strftime('%H:%M')} Uhr")


if __name__ == "__main__":
    main()
