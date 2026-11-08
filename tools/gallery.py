#!/usr/bin/env python3
"""gallery.py — iflipbook.com as a gallery of the drawings iFlipbook's pen makes (founder 2026-11-09, RDM-if-web-gallery).

The home page is the collection: every approved library subject (accessories left out) on a quiet wall, a dozen to a
page, newest (highest number) first; each room has its own pages; each drawing has its own page with a free PNG
download, so it can be found, saved and shared. Numbers are kept in gallery/numbers.json: a new drawing gets the next.
Making a flipbook in the browser stays at /draw/, one quiet link from the home page.

    python3 tools/gallery.py --lib <iFlipbook>/iFlipbook/Helper/Library --renders <dir of <id>-after.png>

  --lib      the app's library JSON (status, name, category, description)
  --renders  the app's own renders of each drawing, 512 px (iFlipbookTests HelperLibraryPenFitTests
             testDumpBeforeAndAfterThePen, PENFIT_DIR=<dir>; '<id>-after.png' is what the app draws)

Writes index.html (the home), gallery/<id>/index.html, gallery/img/<id>.png, gallery/items.json (the list other tools
read, e.g. the Pinterest pins) and the gallery part of sitemap.xml.
The shared app menu and footer come from swiftian.com tools/app_menu.py, as on every page of the six sites.
"""

import html
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGIN = "https://iflipbook.com"
APP_MENU = os.path.expanduser("~/Projects/swiftian.com/tools/app_menu.py")
STORE = "https://apps.apple.com/app/id6759637879"
ROOMS = [("animal", "Animals"), ("food", "Food"), ("nature", "Nature"), ("object", "Things"),
         ("fantasy", "Fantasy"), ("holiday", "Holidays"), ("vehicle", "Vehicles")]
FEATURED = ["dragon", "bubble-tea", "lighthouse"]
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '  <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;1,9..144,400'
         '&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')
e = html.escape


def arg(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None


def title(s):
    small = {"and", "of", "or", "a", "the", "in"}
    return " ".join(w if (i and w in small) else w[:1].upper() + w[1:] for i, w in enumerate(s.split()))


def load(lib):
    works = []
    for f in sorted(os.listdir(lib)):
        if not f.endswith(".helper.json"):
            continue
        d = json.load(open(os.path.join(lib, f), encoding="utf-8"))
        if d.get("status") != "approved" or d.get("kind") != "subject":
            continue
        works.append({"id": d["id"], "name": title(d["name"]), "room": d.get("category", "object"),
                      "desc": d.get("description", "").strip()})
    # numbers are kept once given (gallery/numbers.json): a drawing added later gets the next number, and the wall
    # shows the highest number first, so the newest hang first (founder 2026-11-09)
    nf = os.path.join(ROOT, "gallery", "numbers.json")
    nums = json.load(open(nf, encoding="utf-8")) if os.path.exists(nf) else {}
    nxt = max(nums.values(), default=0) + 1
    for w in sorted(works, key=lambda w: w["name"].lower()):
        if w["id"] not in nums:
            nums[w["id"]] = nxt
            nxt += 1
    os.makedirs(os.path.dirname(nf), exist_ok=True)
    json.dump(dict(sorted(nums.items(), key=lambda kv: kv[1])), open(nf, "w", encoding="utf-8"), indent=0)
    for w in works:
        w["no"] = f"{nums[w['id']]:03d}"
    works.sort(key=lambda w: -int(w["no"]))
    return works


def trim(src, dst, margin=0.12):
    """The drawing on its own square of paper: crop the render to the drawing plus an even margin, no resampling
    (the app's pixels as drawn)."""
    from PIL import Image, ImageChops
    im = Image.open(src).convert("RGB")
    box = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).point(lambda v: 255 if v > 12 else 0).getbbox()
    if not box:
        im.save(dst, optimize=True)
        return im.size[0]
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    side = int(max(box[2] - box[0], box[3] - box[1]) * (1 + 2 * margin))
    side = min(max(side, 160), max(im.size))
    x0, y0 = int(round(cx - side / 2)), int(round(cy - side / 2))
    paper = Image.new("RGB", (side, side), (255, 255, 255))
    # only the part inside the render: past its edge is more paper, not black
    ix0, iy0 = max(x0, 0), max(y0, 0)
    ix1, iy1 = min(x0 + side, im.size[0]), min(y0 + side, im.size[1])
    paper.paste(im.crop((ix0, iy0, ix1, iy1)), (ix0 - x0, iy0 - y0))
    paper.save(dst, optimize=True)
    return side


def tool(*args):
    return subprocess.run([sys.executable, APP_MENU, "--site", "iflipbook.com", *args],
                          capture_output=True, text=True, check=True).stdout


def shared():
    out = tool("--print").splitlines()
    return out[0] + "\n  " + out[1], "\n".join(out[2:]).strip(), tool("--footer", "en").strip()


ROOM_NAME = dict(ROOMS)

CSS = """
    :root{--wall:#f4f2ed;--paper:#fff;--ink:#1c1b19;--soft:#6d6a63;--faint:#a29e95;--line:#e3dfd6;--ac:#127a8a}
    *{box-sizing:border-box} html,body{margin:0}
    body{font-family:"Inter",-apple-system,system-ui,sans-serif;color:var(--ink);background:var(--wall);-webkit-font-smoothing:antialiased}
    a{color:inherit}
    .wrap{width:100%;max-width:1180px;margin:0 auto;padding:0 24px}
    /* shared app menu on a light wall (RDM-web-app-menu-all-sites) */
    .wrap .am{--am-muted:#8a867d;--am-line:var(--line);--am-hover:rgba(28,27,25,.28);--am-cur-bg:rgba(28,27,25,.05);--am-cur-line:rgba(28,27,25,.75)}
    nav.tabs-bar{display:flex;align-items:flex-end;gap:10px;padding:22px 0 0;border-bottom:1px solid var(--line);margin-top:18px}
    nav.tabs-bar img.brand{width:32px;height:32px;border-radius:8px;align-self:center;margin:0 4px 8px 0;display:block}
    .tabs{display:flex;gap:6px}
    .tab{min-width:118px;padding:10px 16px 9px;margin-bottom:-1px;text-align:center;text-decoration:none;color:var(--soft);
      font:500 14px/1.2 "Inter",system-ui,sans-serif;border:1px solid var(--line);border-bottom:none;border-radius:10px 10px 0 0;background:rgba(255,255,255,.4)}
    .tab:hover{color:var(--ink)}
    .tab[aria-current]{color:var(--ink);background:var(--wall);border-color:var(--ink);border-top-width:2px;padding-top:9px}
    .serif{font-family:"Fraunces",Georgia,serif;font-optical-sizing:auto}
    .eyebrow{font:600 11px/1 "Inter",sans-serif;letter-spacing:.22em;text-transform:uppercase;color:var(--soft);margin:0}
    .appstore{display:inline-flex;align-items:center;gap:10px;min-height:48px;padding:7px 18px 7px 9px;border-radius:12px;
      background:var(--ink);color:#fff;text-decoration:none;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .appstore img{border-radius:7px;display:block}
    .appstore span{display:flex;flex-direction:column;line-height:1.05}
    .appstore small{font-size:10px;opacity:.8}
    .appstore b{font-size:17px;font-weight:600}
    .appstore:hover{background:#000}
    .frame{margin:0;background:var(--paper);border:1px solid var(--line);padding:9%;
      box-shadow:0 1px 1px rgba(28,27,25,.04),0 10px 30px -12px rgba(28,27,25,.18);transition:transform .25s ease,box-shadow .25s ease}
    .frame img{display:block;width:100%;height:auto;aspect-ratio:1}
"""

HOME_CSS = """
    .hero{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:56px;align-items:center;padding:72px 0 64px}
    .hero h1{font-weight:400;font-size:clamp(40px,5.4vw,66px);line-height:1.02;letter-spacing:-.02em;margin:18px 0 0}
    .hero h1 em{font-style:italic;color:var(--soft)}
    .hero .lede{font-size:16px;line-height:1.65;color:var(--soft);margin:22px 0 30px;max-width:420px}
    .trio{display:grid;grid-template-columns:1.25fr 1fr;grid-template-rows:auto auto;gap:22px}
    .trio a{text-decoration:none;display:block}
    .trio a:first-child{grid-row:span 2;align-self:center}
    .trio a:hover .frame,.wall a:hover .frame{transform:translateY(-3px);box-shadow:0 1px 1px rgba(28,27,25,.04),0 18px 40px -14px rgba(28,27,25,.28)}
    .cap{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin-top:11px}
    .cap .t{font-family:"Fraunces",Georgia,serif;font-size:15.5px}
    .cap .n{font-size:11px;letter-spacing:.12em;color:var(--faint);font-variant-numeric:tabular-nums}
    .rooms{position:sticky;top:0;z-index:5;background:rgba(244,242,237,.92);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
      display:flex;gap:6px 22px;flex-wrap:wrap;align-items:baseline;padding:16px 0 14px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
    .rooms a{font-size:13.5px;color:var(--soft);padding:2px 0;border-bottom:1.5px solid transparent;text-decoration:none}
    .rooms a sup{font-size:10px;color:var(--faint);margin-left:3px}
    .rooms a:hover{color:var(--ink)}
    .rooms a[aria-current]{color:var(--ink);border-color:var(--ink)}
    .hub-h{padding:64px 0 40px} .hub-h h1{font-weight:400;font-size:clamp(34px,4.4vw,52px);letter-spacing:-.015em;margin:14px 0 0}
    /* room to breathe: three across at most, a wide wall gap, a dozen to a page (founder 2026-11-09) */
    .wall{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:80px 72px;max-width:1040px;margin:0 auto;padding:72px 0 24px}
    .wall a{text-decoration:none;display:block}
    .pager{display:flex;justify-content:space-between;align-items:center;max-width:1040px;margin:56px auto 0;padding:22px 0;border-top:1px solid var(--line);font-size:14px;color:var(--faint)}
    .pager a{color:var(--ink);text-decoration:none} .pager a:hover{text-decoration:underline;text-underline-offset:3px}
    .pager .off{visibility:hidden}
    .aside{margin:52px 0 0;padding:26px 0 0;border-top:1px solid var(--line);color:var(--soft);font-size:14px;text-align:center}
    .aside a{color:var(--ink);text-underline-offset:3px}
    @media (max-width:860px){.hero{grid-template-columns:1fr;gap:40px;padding:48px 0 44px} .wall{gap:56px 40px}}
    @media (max-width:540px){
      .wrap{padding:0 16px}
      .tab{min-width:0;flex:1;padding:10px 6px 9px} .tabs{flex:1}
      .wall{grid-template-columns:repeat(2,minmax(0,1fr));gap:40px 22px;padding:44px 0 16px}
      .trio{gap:14px} .cap .t{font-size:14px} .rooms{gap:6px 16px}
    }
"""

PIECE_CSS = """
    .back{display:inline-block;margin:30px 0 0;font-size:13.5px;color:var(--soft);text-decoration:none}
    .back:hover{color:var(--ink)}
    .piece{display:grid;grid-template-columns:minmax(0,7fr) minmax(0,5fr);gap:64px;align-items:center;padding:36px 0 60px}
    .piece .frame{max-width:620px;padding:7%}
    .placard h1{font-weight:400;font-size:clamp(34px,4.4vw,52px);line-height:1.05;letter-spacing:-.015em;margin:14px 0 0}
    .placard .desc{font-size:16px;line-height:1.65;color:var(--soft);margin:18px 0 0;max-width:420px}
    .placard .medium{font-size:12.5px;color:var(--faint);margin:20px 0 0;letter-spacing:.02em}
    .acts{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:30px 0 0}
    .dl{display:inline-flex;align-items:center;gap:8px;min-height:48px;padding:0 20px;border:1px solid var(--ink);border-radius:12px;
      text-decoration:none;font-weight:500;font-size:14.5px;background:transparent}
    .dl:hover{background:var(--ink);color:#fff}
    .pn{display:flex;justify-content:space-between;gap:16px;padding:22px 0;border-top:1px solid var(--line);font-size:14px}
    .pn a{text-decoration:none;color:var(--soft)} .pn a:hover{color:var(--ink)}
    .pn .t{font-family:"Fraunces",Georgia,serif;color:var(--ink);font-size:15.5px}
    .kin h2{font:600 11px/1 "Inter",sans-serif;letter-spacing:.22em;text-transform:uppercase;color:var(--soft);margin:34px 0 22px}
    .kin .row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:26px}
    .kin a{text-decoration:none}
    .kin .t{font-family:"Fraunces",Georgia,serif;font-size:14.5px;margin-top:9px;display:block}
    @media (max-width:860px){.piece{grid-template-columns:1fr;gap:34px}}
    @media (max-width:540px){.wrap{padding:0 16px} .tab{min-width:0;flex:1;padding:10px 6px 9px} .tabs{flex:1}
      .kin .row{grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}}
"""

# a visit from a Pinterest pin keeps its campaign for the session, so App Store clicks count as web-if-pin*
# (pins link with ?utm_campaign=web-if-pin…, tools/pins.py; same as coordigo.com)
TRACK = ('<script>(function(){var pin=(location.search.match(/[?&]utm_campaign=(web-if-pin[a-z-]*)/)||[])[1];'
         'try{if(pin)sessionStorage.setItem("if_ct",pin);else pin=sessionStorage.getItem("if_ct");}catch(e){}'
         'if(pin)document.querySelectorAll(\'a[href*="apps.apple.com"]\').forEach(function(a){a.href=a.href.replace(/ct=[\\w-]+/,"ct="+pin);});})();</script>\n  '
         '<script type="module" src="/js/track.js"></script>\n'
         '<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js" data-cf-beacon=\'{"token": "19910af39e1b43edb0af1b9e65939b36"}\'></script>')


def tabs():
    t = [("/", "iFlipbook", True), ("/postcards/", "Postcards", False)]
    inner = "".join(f'<a class="tab" href="{h}"' + (' aria-current="page"' if cur else "") + f'>{n}</a>' for h, n, cur in t)
    return (f'<nav class="tabs-bar" aria-label="iFlipbook"><img src="/media/icon.png" alt="" class="brand" width="32" height="32">'
            f'<div class="tabs">{inner}</div></nav>')


def store(ct):
    return (f'<a class="appstore" href="{STORE}?ct={ct}" target="_blank" rel="noopener"><img src="/media/icon.png" width="30" height="30" alt="">'
            '<span><small>Download on the</small><b>App Store</b></span></a>')


def card(w, lazy=True):
    load_ = ' loading="lazy" decoding="async"' if lazy else ""
    return (f'<a href="/gallery/{w["id"]}/" data-room="{w["room"]}"><figure class="frame">'
            f'<img src="/gallery/img/{w["id"]}.png" width="{w["px"]}" height="{w["px"]}" alt="{e(w["desc"] or w["name"])}"{load_}></figure>'
            f'<div class="cap"><span class="t">{e(w["name"])}</span><span class="n">No.&nbsp;{w["no"]}</span></div></a>')


def head_common(title_, desc, url, image, extra=""):
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title_)}</title>
  <meta name="description" content="{e(desc)}">
  <meta name="theme-color" content="#f4f2ed">
  <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png?v=20261108">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png?v=20261108">
  <link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png?v=20261108">
  <link rel="apple-touch-icon" href="/apple-touch-icon.png?v=20261108">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{e(title_)}">
  <meta property="og:description" content="{e(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{image}">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="{url}" />
{extra}  {FONTS}"""


PER_PAGE = 12


def hub_url(room, n):
    """Page n of the whole wall ('' room) or of one room."""
    base = "/" if not room else f"/gallery/room/{room}/"
    if n == 1:
        return base
    return (f"/gallery/page/{n}/" if not room else f"{base}page/{n}/")


def hub(works, all_works, room, n, pages, menu_head, menu, foot, keep):
    """One page of the wall: the home is page 1 of all of them (with the hero); rooms have their own pages."""
    by = {w["id"]: w for w in all_works}
    feat = [by[i] for i in FEATURED if i in by]
    counts = {k: sum(1 for w in all_works if w["room"] == k) for k, _ in ROOMS}
    cur = lambda k: ' aria-current="page"' if k == room else ""
    rooms = f'<a href="/#wall"{cur("")}>All<sup>{len(all_works)}</sup></a>' + "".join(
        f'<a href="/gallery/room/{k}/#wall"{cur(k)}>{nm}<sup>{counts[k]}</sup></a>' for k, nm in ROOMS if counts[k])
    url = ORIGIN + hub_url(room, n)
    home = not room and n == 1
    if home:
        title_ = "iFlipbook — The Collection: free drawings to download and share"
        desc = (f"The iFlipbook collection: {len(all_works)} small drawings made with iFlipbook's pen, "
                "from a bubble tea to a dragon. Every one is free to download, print and share.")
        top = f"""<header class="hero">
      <div>
        <p class="eyebrow">The iFlipbook Collection</p>
        <h1 class="serif">Small drawings,<br><em>one pen.</em></h1>
        <p class="lede">{len(all_works)} drawings made with iFlipbook&rsquo;s pen. Every one is free to download, print and share.</p>
        {store("web-if-home")}
      </div>
      <div class="trio">{"".join(card(w, lazy=False) for w in feat)}</div>
    </header>"""
    else:
        label = ROOM_NAME[room] if room else "All drawings"
        title_ = f"{label} — free drawings to download" + (f", page {n}" if n > 1 else "") + " · iFlipbook"
        desc = (f"{label}: small drawings made with iFlipbook's pen, free to download, print and share."
                + (f" Page {n} of {pages}." if pages > 1 else ""))
        top = f"""<header class="hub-h"><p class="eyebrow">The iFlipbook Collection</p><h1 class="serif">{e(label)}</h1></header>"""
    newer = f'<a href="{hub_url(room, n - 1)}#wall">&larr; Newer</a>' if n > 1 else '<span class="off">&larr; Newer</span>'
    older = f'<a href="{hub_url(room, n + 1)}#wall">Older &rarr;</a>' if n < pages else '<span class="off">Older &rarr;</span>'
    pager = f'<nav class="pager" aria-label="Pages">{newer}<span>{n} / {pages}</span>{older}</nav>' if pages > 1 else ""
    rel = (f'  <link rel="prev" href="{ORIGIN}{hub_url(room, n - 1)}" />\n' if n > 1 else "") + \
          (f'  <link rel="next" href="{ORIGIN}{hub_url(room, n + 1)}" />\n' if n < pages else "")
    ld = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage", "name": "The iFlipbook Collection",
                     "url": url, "description": desc, "publisher": {"@id": "https://swiftian.com/#org"},
                     "hasPart": [{"@type": "ImageObject", "name": w["name"], "contentUrl": f"{ORIGIN}/gallery/img/{w['id']}.png",
                                  "url": f"{ORIGIN}/gallery/{w['id']}/"} for w in works]}, ensure_ascii=False)
    aside = '<p class="aside">Want to see a drawing move? <a href="/draw/">Make a flipbook in your browser</a>.</p>' if home else ""
    return head_common(title_, desc, url, f"{ORIGIN}/gallery/img/{(feat if home else works)[0]['id']}.png",
                       (keep if home else "") + rel) + f"""
  {menu_head}
  <style>{CSS}{HOME_CSS}  </style>
  <script type="application/ld+json">{ld}</script>
</head>
<body>
  <div class="wrap">
    {menu}
    {tabs()}
    {top}
    <nav class="rooms" aria-label="Rooms">{rooms}</nav>
    <main class="wall" id="wall">{"".join(card(w) for w in works)}</main>
    {pager}
    {aside}
  </div>
  {foot}
  {TRACK}
</body>
</html>
"""


def write_hubs(works, menu_head, menu, foot, keep):
    """Every page of the wall and of each room; returns {id: the All page it hangs on} for the back links."""
    on_page = {}
    for room in [""] + [k for k, _ in ROOMS]:
        ws = [w for w in works if not room or w["room"] == room]
        if not ws:
            continue
        pages = (len(ws) + PER_PAGE - 1) // PER_PAGE
        for n in range(1, pages + 1):
            chunk = ws[(n - 1) * PER_PAGE:n * PER_PAGE]
            if not room:
                for w in chunk:
                    on_page[w["id"]] = hub_url("", n)
            path = hub_url(room, n).strip("/")
            out = os.path.join(ROOT, path, "index.html") if path else os.path.join(ROOT, "index.html")
            os.makedirs(os.path.dirname(out), exist_ok=True)
            open(out, "w", encoding="utf-8").write(hub(chunk, works, room, n, pages, menu_head, menu, foot, keep))
    return on_page


def piece(w, newer, older, kin, menu_head, menu, foot):
    url = f"{ORIGIN}/gallery/{w['id']}/"
    img = f"{ORIGIN}/gallery/img/{w['id']}.png"
    room = ROOM_NAME.get(w["room"], "Things")
    desc = (w["desc"] + " " if w["desc"] else "") + "A free drawing from the iFlipbook collection: download the PNG, print it or share it."
    ld = json.dumps({"@context": "https://schema.org", "@type": "ImageObject", "name": w["name"], "description": w["desc"],
                     "contentUrl": img, "url": url, "width": w["px"], "height": w["px"], "encodingFormat": "image/png",
                     "isAccessibleForFree": True, "creditText": "iFlipbook", "copyrightNotice": "Swiftian Inc.",
                     "creator": {"@id": "https://swiftian.com/#org"}}, ensure_ascii=False)
    kin_html = "".join(f'<a href="/gallery/{k["id"]}/"><figure class="frame"><img src="/gallery/img/{k["id"]}.png" width="{k["px"]}" height="{k["px"]}" '
                       f'alt="{e(k["desc"] or k["name"])}" loading="lazy"></figure><span class="t">{e(k["name"])}</span></a>' for k in kin)
    return head_common(f"{w['name']} — free drawing to download · iFlipbook", desc, url, img) + f"""
  {menu_head}
  <style>{CSS}{PIECE_CSS}  </style>
  <script type="application/ld+json">{ld}</script>
</head>
<body>
  <div class="wrap">
    {menu}
    {tabs()}
    <a class="back" href="/gallery/room/{w['room']}/">&larr; The Collection &middot; {room}</a>
    <article class="piece">
      <figure class="frame"><img src="/gallery/img/{w['id']}.png" width="{w['px']}" height="{w['px']}" alt="{e(w['desc'] or w['name'])}"></figure>
      <div class="placard">
        <p class="eyebrow">No. {w['no']} &middot; {room}</p>
        <h1 class="serif">{e(w['name'])}</h1>
        <p class="desc">{e(w['desc'])}</p>
        <p class="medium">Drawn with iFlipbook&rsquo;s pen &middot; PNG, {w['px']} &times; {w['px']}</p>
        <div class="acts">
          <a class="dl" href="/gallery/img/{w['id']}.png" download="iflipbook-{w['id']}.png">Download free</a>
          {store("web-if-gallery")}
        </div>
      </div>
    </article>
    <nav class="pn" aria-label="More drawings">
      {f'<a href="/gallery/{newer["id"]}/">&larr; <span class="t">{e(newer["name"])}</span></a>' if newer else '<span></span>'}
      {f'<a href="/gallery/{older["id"]}/"><span class="t">{e(older["name"])}</span> &rarr;</a>' if older else '<span></span>'}
    </nav>
    <section class="kin"><h2>Also in {room}</h2><div class="row">{kin_html}</div></section>
  </div>
  {foot}
  {TRACK}
</body>
</html>
"""


def keep_from_home():
    """Head lines the home keeps from its current file: verification tags and the hreflang set."""
    s = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    keep = re.findall(r'  <meta name="p:domain_verify"[^>]*>\n', s)
    keep += re.findall(r'  <link rel="alternate" hreflang="[^"]+" href="[^"]+" />\n', s)
    return "".join(keep)


def sitemap(works):
    p = os.path.join(ROOT, "sitemap.xml")
    s = open(p, encoding="utf-8").read()
    s = re.sub(r"\s*<url>\s*<loc>https://iflipbook\.com/gallery/.*?</url>", "", s, flags=re.S)
    if "xmlns:image" not in s:
        s = s.replace('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
                      '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                      'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">', 1)
    add = "".join(f"\n  <url>\n    <loc>{ORIGIN}/gallery/{w['id']}/</loc>\n    <changefreq>monthly</changefreq>\n"
                  f"    <priority>0.6</priority>\n    <image:image><image:loc>{ORIGIN}/gallery/img/{w['id']}.png</image:loc></image:image>\n  </url>"
                  for w in works)
    add += "".join(f"\n  <url>\n    <loc>{ORIGIN}/gallery/room/{k}/</loc>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>"
                   for k, _ in ROOMS if any(w["room"] == k for w in works))
    s = s.replace("\n</urlset>", add + "\n</urlset>", 1)
    open(p, "w", encoding="utf-8").write(s)


def main():
    lib, renders = arg("--lib"), arg("--renders")
    if not lib or not renders:
        raise SystemExit(__doc__)
    works = load(lib)
    missing = [w["id"] for w in works if not os.path.exists(os.path.join(renders, f"{w['id']}-after.png"))]
    if missing:
        raise SystemExit(f"no render for {len(missing)}: {', '.join(missing[:8])}")
    menu_head, menu, foot = shared()
    img_dir = os.path.join(ROOT, "gallery", "img")
    os.makedirs(img_dir, exist_ok=True)
    keep = keep_from_home()
    for w in works:
        w["px"] = trim(os.path.join(renders, f"{w['id']}-after.png"), os.path.join(img_dir, f"{w['id']}.png"))
    for i, w in enumerate(works):
        same = [k for k in works if k["room"] == w["room"] and k["id"] != w["id"]]
        start = same.index(next((k for k in same if int(k["no"]) < int(w["no"])), same[0])) if same else 0
        kin = (same[start:] + same[:start])[:4]
        d = os.path.join(ROOT, "gallery", w["id"])
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(
            piece(w, works[i - 1] if i else None, works[i + 1] if i + 1 < len(works) else None, kin, menu_head, menu, foot))
    # old page folders from an earlier run go first, so a shrinking room leaves no stale page behind
    for d in ("page", "room"):
        shutil.rmtree(os.path.join(ROOT, "gallery", d), ignore_errors=True)
    write_hubs(works, menu_head, menu, foot, keep)
    sitemap(works)
    # the drawings this site shows, for other tools (Pinterest pins link to /gallery/<id>/)
    json.dump([{k: w[k] for k in ("id", "no", "name", "room", "desc")} for w in works],
              open(os.path.join(ROOT, "gallery", "items.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"gallery: {len(works)}/{len(works)} drawings · {len(works)} drawing pages · wall in pages of {PER_PAGE} · sitemap")


if __name__ == "__main__":
    main()
