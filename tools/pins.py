#!/usr/bin/env python3
"""Pinterest pins for the iflipbook.com gallery, sent by RSS (founder 2026-11-09).
One pin per gallery drawing (gallery/items.json, tools/gallery.py: iFlipbook's library drawings, each a Coordigo Library subject
drawn new in the iFlipbook look, founder approved 2026-11-08). Board "Easy Things to Draw" on pinterest.com/iflipbook, fed by
pins/ideas.xml. A pin's image is the gallery's image (the app's own rendering after its pen); its link is /gallery/<id>/ with
utm_campaign=web-if-pin, which the gallery pages use as the App Store ct.
The library itself ships in the next iFlipbook version; until it is live the words say only "easy thing to draw, make it move"
(founder.md: a new version's words go out after it is live).

  tools/pins.py render [--ids a,b] [--force]  pin images pins/ideas/<id>.jpg (1000x1500) from gallery/img/<id>.png
  tools/pins.py plan [--start D] [--force]    pins/plan.json: the day each pin goes out (kept once made; needs the app repo for tags)
  tools/pins.py feed [--date D]               pins/ideas.xml: the pins of the last 3 days
  tools/pins.py check                         PASS/FAIL: every gallery drawing has its pin and is in the plan

Pace: 12 on day 1, then 10 a day. Christmas, winter and New Year first with Thanksgiving and autumn, the rest, Valentine's last;
Halloween waits for 2027-09-01. Pinterest keeps the first image it fetched for an address, so image addresses carry the content
hash, an item's pubDate is fixed by its day, and the feed lists only 3 days (coordigo.com tools/pins.py, same rules).
The mini runs tools/pins-daily.sh each morning. New drawings in the gallery: render, then add them to the plan by hand or --force
only before the first pin is out."""
import concurrent.futures, datetime, functools, glob, hashlib, html, http.server, json, pathlib, subprocess, sys, tempfile, threading
from email.utils import format_datetime

SITE = pathlib.Path(__file__).resolve().parent.parent
LIB = pathlib.Path.home() / 'Projects' / 'iFlipbook' / 'iFlipbook' / 'Helper' / 'Library'
ORIGIN = 'https://iflipbook.com'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
FIRST, DAILY, DAYS = 12, 10, 3
HALLOWEEN_FROM = '2027-09-01'

def items(): return json.loads((SITE / 'gallery' / 'items.json').read_text())
def art(i): return SITE / 'gallery' / 'img' / f'{i}.png'
def pin(i): return SITE / 'pins' / 'ideas' / f'{i}.jpg'

PIN_CSS = '''*{box-sizing:border-box;margin:0} html,body{width:1000px;height:1500px;overflow:hidden}
body{background:#0b0f1a;color:#eef2ff;font-family:Inter,sans-serif;display:flex;flex-direction:column;align-items:center}
.kicker{margin-top:104px;font:600 22px/1 "Space Grotesk";letter-spacing:.24em;text-transform:uppercase;color:#22d3ee}
h1{font:700 92px/1.02 "Space Grotesk";letter-spacing:-.02em;margin-top:22px;text-align:center;padding:0 60px} h1.m{font-size:74px} h1.s{font-size:60px}
.sub{font:500 29px/1.38 Inter;color:#c7d0ea;margin-top:20px;text-align:center;max-width:800px}
.card{margin-top:56px;width:820px;height:820px;background:#fff;border-radius:28px;display:flex;align-items:center;justify-content:center;box-shadow:0 30px 80px rgba(0,0,0,.5)}
.card img{width:760px;height:760px;object-fit:contain}
.note{margin-top:40px;font:500 26px/1.3 Inter;color:#9aa6c4}
.foot{margin-top:auto;margin-bottom:56px;display:flex;align-items:center;gap:14px;font:600 28px "Space Grotesk"}
.foot img{width:42px;height:42px;border-radius:10px}'''

def pin_html(d, B):
    e = html.escape; t = d['name']
    size = '' if len(t) <= 14 else ' class="m"' if len(t) <= 20 else ' class="s"'
    return (f'<!doctype html><meta charset="utf-8"><link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=Inter:wght@500&display=swap" rel="stylesheet">'
            f'<style>{PIN_CSS}</style><div class="kicker">Easy thing to draw</div><h1{size}>{e(t)}</h1><div class="sub">{e(d["desc"])}</div>'
            f'<div class="card"><img src="{B}/gallery/img/{d["id"]}.png"></div><div class="note">Draw it with one finger, then make it move</div>'
            f'<div class="foot"><img src="{B}/media/icon.png">iflipbook.com</div>')

def render(args):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    B = f'http://127.0.0.1:{srv.server_address[1]}'; tmp = pathlib.Path(tempfile.mkdtemp())
    only = set(args[args.index('--ids') + 1].split(',')) if '--ids' in args else None
    todo = [d for d in items() if (not only or d['id'] in only) and ('--force' in args or not pin(d['id']).exists())]
    def one(d):
        h = tmp / f'{d["id"]}.html'; png = tmp / f'{d["id"]}.png'; h.write_text(pin_html(d, B))
        subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', f'--user-data-dir={tmp / ("u-" + d["id"])}', '--window-size=1000,1500',
                        '--virtual-time-budget=10000', f'--screenshot={png}', f'file://{h}'], capture_output=True, timeout=180)
        if not png.exists(): return f'FAIL {d["id"]}'
        pin(d['id']).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '80', str(png), '--out', str(pin(d['id']))], capture_output=True)
    n = 0
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        for r in ex.map(one, todo):
            n += 1
            if r: print(r, file=sys.stderr)
            if n % 20 == 0 or n == len(todo): print(f'render {n}/{len(todo)}', file=sys.stderr)
    srv.shutdown()

def plan(args):
    p = SITE / 'pins' / 'plan.json'
    if p.exists() and '--force' not in args: sys.exit(f'{p} is kept once made (it says which pins went out); --force to remake')
    start = datetime.date.fromisoformat(args[args.index('--start') + 1]) if '--start' in args else datetime.date.today()
    tags = {json.load(open(f))['id']: json.load(open(f))['tags'] for f in glob.glob(str(LIB / '*.helper.json'))}
    ids = [d['id'] for d in items()]
    has = lambda i, *t: any(x in tags.get(i, []) for x in t)
    hold = [i for i in ids if has(i, 'halloween', 'spooky')]
    groups = [[i for i in ids if has(i, 'christmas', 'winter', 'new year') and i not in hold], [i for i in ids if has(i, 'thanksgiving', 'autumn') and i not in hold]]
    first = []
    for k in range(max(map(len, groups))): first += [g[k] for g in groups if k < len(g) and g[k] not in first]
    late = [i for i in ids if has(i, 'valentine', 'love') and i not in hold + first]
    order = first + [i for i in ids if i not in hold + first + late] + late
    day = lambda k: 0 if k < FIRST else 1 + (k - FIRST) // DAILY
    q = [{'id': i, 'date': (start + datetime.timedelta(days=day(k))).isoformat()} for k, i in enumerate(order)]
    h0 = datetime.date.fromisoformat(HALLOWEEN_FROM)
    q += [{'id': i, 'date': (h0 + datetime.timedelta(days=k // DAILY)).isoformat()} for k, i in enumerate(hold)]
    p.parent.mkdir(exist_ok=True); p.write_text(json.dumps({'made': datetime.date.today().isoformat(), 'first': FIRST, 'daily': DAILY, 'pins': q}, indent=1) + '\n')
    print(f'{len(q)} pins: {q[0]["date"]} to {q[len(order) - 1]["date"]}; Halloween {len(hold)} from {HALLOWEEN_FROM}')

def feed(args):
    today = args[args.index('--date') + 1] if '--date' in args else datetime.date.today().isoformat()
    data = json.load(open(SITE / 'pins' / 'plan.json')); by = {d['id']: d for d in items()}
    since = (datetime.date.fromisoformat(today) - datetime.timedelta(days=DAYS - 1)).isoformat()
    slot, seen = {}, {}
    for x in data['pins']: slot[x['id']] = seen.get(x['date'], 0); seen[x['date']] = slot[x['id']] + 1
    due = sorted([x for x in data['pins'] if since <= x['date'] <= today and x['id'] in by and not x.get('sent')],
                 key=lambda x: (x['date'], -slot[x['id']]), reverse=True)
    rows = []
    for x in due:
        d = by[x['id']]; f = pin(d['id'])
        if not f.exists(): sys.exit(f'FAIL no image {f} — run tools/pins.py render first')
        t = f'Easy {d["name"]} Drawing · Simple Doodle to Animate'
        desc = (f'{d["desc"]} An easy thing to draw with one finger: a line or two, a dot for an eye and a dab of colour. '
                f'Draw it, then draw it again a little different on the next page and make it move as a flipbook in iFlipbook.')
        link = f'{ORIGIN}/gallery/{d["id"]}/?utm_source=pinterest&amp;utm_medium=social&amp;utm_campaign=web-if-pin'
        src = f'{ORIGIN}/pins/ideas/{d["id"]}.jpg?v={hashlib.md5(f.read_bytes()).hexdigest()[:8]}'
        when = datetime.datetime.fromisoformat(x['date'] + 'T07:00:00+09:00') - datetime.timedelta(minutes=slot[x['id']])
        rows.append(f'''  <item>
   <title>{html.escape(t)}</title>
   <link>{link}</link>
   <guid isPermaLink="false">iflipbook-pin-idea-{d["id"]}</guid>
   <pubDate>{format_datetime(when)}</pubDate>
   <description>{html.escape(desc)}</description>
   <enclosure url="{src}" length="{f.stat().st_size}" type="image/jpeg"/>
   <media:content url="{src}" medium="image" type="image/jpeg" width="1000" height="1500"/>
  </item>''')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<?xml-stylesheet type="text/xsl" href="/pins/feed.xsl"?>\n'
           '<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">\n <channel>\n'
           f'  <title>iFlipbook · Easy Things to Draw</title>\n  <link>{ORIGIN}/</link>\n'
           '  <description>Easy things to draw with one finger and make move, from iflipbook.com.</description>\n  <language>en</language>\n'
           + '\n'.join(rows) + '\n </channel>\n</rss>\n')
    out = SITE / 'pins' / 'ideas.xml'
    if not out.exists() or out.read_text() != xml: out.write_text(xml)
    print(f'ideas.xml: {len([x for x in data["pins"] if x["date"] <= today])}/{len(data["pins"])} out by {today}, feed lists {len(rows)}')

def check(args):
    ds = items(); planned = {x['id'] for x in json.load(open(SITE / 'pins' / 'plan.json'))['pins']} if (SITE / 'pins' / 'plan.json').exists() else set()
    bad = [f'{d["id"]} pin' for d in ds if not pin(d['id']).exists()] + [f'{d["id"]} plan' for d in ds if d['id'] not in planned]
    bad += [f'{d["id"]} gallery image' for d in ds if not art(d['id']).exists()]
    for x in bad[:10]: print('missing', x, file=sys.stderr)
    print(f'{"PASS" if not bad else "FAIL"} pins {len(ds) * 3 - len(bad)}/{len(ds) * 3} (gallery image, pin, plan per drawing)')
    if bad: sys.exit(1)

if __name__ == '__main__':
    a = sys.argv[1:] or ['check']
    {'render': render, 'plan': plan, 'feed': feed, 'check': check}[a[0]](a[1:])
