#!/usr/bin/env python3
"""Generate localized landing pages for iflipbook.com.

Source of truth for the prose is the App Store metadata in the app repo
(fastlane/metadata/<locale>/), which is already professionally localized.
Each description.txt has the same 16-line shape:

    0  intro paragraph
    1  hook line
    2..13  six (heading, body) pairs, headings prefixed with U+25CF
    14 audience paragraph
    15 closing call to action

Run from the site repo root:  python3 build-locales.py
"""

import html
import os
import pathlib
import re

APP_REPO = pathlib.Path.home() / "Projects/iFlipbook"
META = APP_REPO / "fastlane/metadata"
SITE = pathlib.Path(__file__).parent
APPID = "6759637879"
CT = "web-iflipbook"          # App Analytics 캠페인 토큰 — 이 사이트가 만든 설치를 가른다
STORE = f"https://apps.apple.com/app/id{APPID}?ct={CT}"
ORIGIN = "https://iflipbook.com"
LASTMOD = "2026-08-24"

# path, ASC locale, hreflang, native name, support label, "Download on the"
LOCALES = [
    ("ar",      "ar-SA",   "ar",       "العربية",           "الدعم",           "التنزيل من"),
    ("de",      "de-DE",   "de",       "Deutsch",           "Support",         "Laden im"),
    ("es",      "es-ES",   "es",       "Español",           "Soporte",         "Descárgalo en el"),
    ("es-mx",   "es-MX",   "es-MX",    "Español (México)",  "Soporte",         "Consíguelo en el"),
    ("fr",      "fr-FR",   "fr",       "Français",          "Assistance",      "Télécharger dans l'"),
    ("hi",      "hi",      "hi",       "हिन्दी",              "सहायता",           "डाउनलोड करें"),
    ("id",      "id",      "id",       "Bahasa Indonesia",  "Dukungan",        "Unduh di"),
    ("it",      "it",      "it",       "Italiano",          "Supporto",        "Scaricala su"),
    ("ja",      "ja",      "ja",       "日本語",             "サポート",          "ダウンロード"),
    ("ko",      "ko",      "ko",       "한국어",             "지원",             "다운로드"),
    ("nl",      "nl-NL",   "nl",       "Nederlands",        "Support",         "Download in de"),
    ("pt-br",   "pt-BR",   "pt-BR",    "Português (Brasil)","Suporte",         "Baixar na"),
    ("ru",      "ru",      "ru",       "Русский",           "Поддержка",       "Загрузите в"),
    ("sv",      "sv",      "sv",       "Svenska",           "Support",         "Ladda ned i"),
    ("th",      "th",      "th",       "ไทย",               "ฝ่ายสนับสนุน",       "ดาวน์โหลดบน"),
    ("tr",      "tr",      "tr",       "Türkçe",            "Destek",          "İndir"),
    ("vi",      "vi",      "vi",       "Tiếng Việt",        "Hỗ trợ",          "Tải về từ"),
    ("zh-hans", "zh-Hans", "zh-Hans",  "简体中文",           "支持",             "下载"),
    ("zh-hant", "zh-Hant", "zh-Hant",  "繁體中文",           "支援",             "下載"),
]

ICONS = ["✎", "⇄", "▶", "✨", "↗", "◎"]
RTL = {"ar"}

SHOTS = [
    ("shot-library.jpg", "iFlipbook"),
    ("shot-editor.jpg", "iFlipbook"),
    ("shot-otto.jpg", "Otto"),
    ("shot-latte.jpg", "iFlipbook"),
    ("shot-birthday.jpg", "iFlipbook"),
]


def read(locale, field):
    return (META / locale / f"{field}.txt").read_text(encoding="utf-8").strip()


def parse_description(locale):
    lines = [l.strip() for l in read(locale, "description").split("\n") if l.strip()]
    if len(lines) != 16:
        raise SystemExit(f"{locale}: expected 16 lines, got {len(lines)}")
    heads = [i for i, l in enumerate(lines) if l.startswith("●")]
    if heads != [2, 4, 6, 8, 10, 12]:
        raise SystemExit(f"{locale}: unexpected section layout {heads}")
    sections = [(lines[i].lstrip("●").strip(), lines[i + 1]) for i in heads]
    return {
        "intro": lines[0],
        "hook": lines[1],
        "sections": sections,
        "audience": lines[14],
        "closing": lines[15],
    }


def style_block():
    s = (SITE / "index.html").read_text(encoding="utf-8")
    return s[s.index("  <style>"):s.index("</style>") + len("</style>")]


def alternates(current):
    """hreflang set — identical on every page, including the English root."""
    out = [f'  <link rel="alternate" hreflang="x-default" href="{ORIGIN}/" />',
           f'  <link rel="alternate" hreflang="en" href="{ORIGIN}/" />']
    for path, _asc, hl, *_ in LOCALES:
        out.append(f'  <link rel="alternate" hreflang="{hl}" href="{ORIGIN}/{path}/" />')
    return "\n".join(out)


def language_nav(current):
    items = [f'<a href="/"{" class=\"on\"" if current is None else ""}>English</a>']
    for path, _asc, _hl, native, *_ in LOCALES:
        on = ' class="on"' if path == current else ""
        items.append(f'<a href="/{path}/"{on}>{html.escape(native)}</a>')
    return "\n        ".join(items)


def clip(text, limit=155):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def build(path, asc, hl, native, support, dl_small):
    d = parse_description(asc)
    name = read(asc, "name")
    subtitle = read(asc, "subtitle")
    e = html.escape
    lang_dir = ' dir="rtl"' if path in RTL else ""

    cards = "\n".join(
        f'''        <div class="card">
          <div class="ico" aria-hidden="true">{ICONS[i]}</div>
          <h3>{e(head)}</h3>
          <p>{e(body)}</p>
        </div>''' for i, (head, body) in enumerate(d["sections"]))

    rail = "\n".join(
        f'        <figure><img src="/media/{f}" alt="{e(alt)}" loading="lazy" /></figure>'
        for f, alt in SHOTS)

    cta = f'''<a class="cta" href="{STORE}" target="_blank" rel="noopener">
            <svg viewBox="0 0 384 512" aria-hidden="true"><path fill="currentColor" d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7-59.5.9-118.7 43.5-118.7 132.2 0 26.2 4.8 53.3 14.4 81.2 12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zM262.1 104.5c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z"/></svg>
            <span class="txt"><small>{e(dl_small)}</small><strong>App Store</strong></span>
          </a>'''

    return f'''<!DOCTYPE html>
<html lang="{hl}"{lang_dir}>
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{e(name)}</title>
  <meta name="description" content="{e(clip(subtitle + " — " + d["intro"]))}" />
  <meta name="theme-color" content="#060816" />
  <link rel="canonical" href="{ORIGIN}/{path}/" />
  <meta name="apple-itunes-app" content="app-id={APPID}" />
{alternates(path)}
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="iFlipbook" />
  <meta property="og:locale" content="{hl.replace("-", "_")}" />
  <meta property="og:title" content="{e(name)}" />
  <meta property="og:description" content="{e(clip(d["hook"], 120))}" />
  <meta property="og:image" content="{ORIGIN}/media/shot-library.jpg" />
  <meta property="og:url" content="{ORIGIN}/{path}/" />
  <meta name="twitter:card" content="summary_large_image" />
{style_block()}
  <style>
    .langs {{ display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 18px; font-size: 0.82rem; }}
    .langs a {{ color: var(--faint); }}
    .langs a.on {{ color: var(--text); font-weight: 700; }}
    .footer-row {{ align-items: flex-start; }}
    .hook {{ font-size: clamp(1.05rem, 2.1vw, 1.32rem); font-weight: 600; color: var(--text); margin: 0 0 14px; max-width: 34em; }}
    .lead {{ max-width: 40em; }}
    :lang(ko) h1, :lang(ko) .hook, :lang(zh-Hans) h1, :lang(zh-Hant) h1 {{ word-break: keep-all; overflow-wrap: break-word; }}
  </style>
</head>
<body>
  <header class="nav">
    <div class="container nav-row">
      <a class="brand" href="/{path}/">
        <img src="/media/icon.png" alt="" />
        <span>iFlipbook</span>
      </a>
      <nav class="nav-links">
        <a href="/support/">{e(support)}</a>
        <a class="nav-cta" href="{STORE}" target="_blank" rel="noopener">App Store</a>
      </nav>
    </div>
  </header>

  <main class="hero">
    <div class="container hero-grid">
      <section>
        <div class="eyebrow"><span class="dot"></span> iPhone · iPad · Mac</div>
        <h1>{e(subtitle)}</h1>
        <p class="hook">{e(d["hook"])}</p>
        <p class="lead">{e(d["intro"])}</p>
        <div class="cta-row">
          {cta}
          <span class="cta-note">iPhone · iPad · Mac</span>
        </div>
      </section>
      <section aria-label="iFlipbook">
        <div class="phone">
          <span class="glow" aria-hidden="true"></span>
          <video autoplay muted loop playsinline poster="/media/shot-library.jpg">
            <source src="/media/preview-phone.mp4" type="video/mp4" />
          </video>
        </div>
      </section>
    </div>
  </main>

  <section class="block">
    <div class="container">
      <div class="cards">
{cards}
      </div>
    </div>
  </section>

  <section class="block">
    <div class="container">
      <div class="rail">
{rail}
      </div>
    </div>
  </section>

  <section class="block">
    <div class="container">
      <div class="section-head">
        <h2>{e(d["closing"])}</h2>
        <p>{e(d["audience"])}</p>
      </div>
      <div class="cta-row" style="justify-content:center">
        {cta}
      </div>
    </div>
  </section>

  <footer class="footer">
    <div class="container footer-row">
      <div>
        © 2026 iFlipbook · <a href="https://swiftian.com" style="opacity:.85">Swiftian Inc.</a>
        <nav class="langs" aria-label="Language">
        {language_nav(path)}
        </nav>
      </div>
      <nav class="footer-links">
        <a href="/support/">{e(support)}</a>
        <a href="/privacy/">Privacy</a>
        <a href="{STORE}" target="_blank" rel="noopener">App Store</a>
      </nav>
    </div>
  </footer>
</body>
</html>
'''


def patch_root():
    """Give the English root the same hreflang set and a language switcher."""
    p = SITE / "index.html"
    s = p.read_text(encoding="utf-8")
    s = re.sub(r'\n  <link rel="alternate" hreflang="[^"]+" href="[^"]+" />', "", s)
    anchor = f'  <link rel="canonical" href="{ORIGIN}/" />\n'
    s = s.replace(anchor, anchor + alternates(None) + "\n", 1)

    s = re.sub(r'\n    \.langs \{.*?\n    \.langs a\.on \{[^}]*\}\n', "\n", s, flags=re.S)
    s = s.replace("  </style>", """    .langs { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 18px; font-size: 0.82rem; }
    .langs a { color: var(--faint); }
    .langs a.on { color: var(--text); font-weight: 700; }
  </style>""", 1)

    # Rebuild the copyright block wholesale so re-runs stay idempotent.
    footer_re = re.compile(
        r'      <div>© 2026 iFlipbook · <a href="https://swiftian\.com" style="opacity:\.85">'
        r'Swiftian Inc\.</a>.*?</div>\n', re.S)
    block = (f'      <div>© 2026 iFlipbook · <a href="https://swiftian.com" style="opacity:.85">'
             f'Swiftian Inc.</a>\n'
             f'        <nav class="langs" aria-label="Language">\n'
             f'        {language_nav(None)}\n'
             f'        </nav>\n'
             f'      </div>\n')
    s, n = footer_re.subn(lambda _m: block, s, count=1)
    if n != 1:
        raise SystemExit("index.html: could not locate the footer copyright block")
    p.write_text(s, encoding="utf-8")


def write_sitemap():
    urls = [(f"{ORIGIN}/", "1.0", "weekly")]
    urls += [(f"{ORIGIN}/{p}/", "0.9", "weekly") for p, *_ in LOCALES]
    urls += [(f"{ORIGIN}/support/", "0.5", "monthly"), (f"{ORIGIN}/privacy/", "0.3", "yearly")]
    body = "\n".join(
        f"  <url>\n    <loc>{u}</loc>\n    <lastmod>{LASTMOD}</lastmod>\n"
        f"    <changefreq>{cf}</changefreq>\n    <priority>{pr}</priority>\n  </url>"
        for u, pr, cf in urls)
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n", encoding="utf-8")


def main():
    if not META.is_dir():
        raise SystemExit(f"App Store metadata not found at {META}")
    patch_root()
    for path, asc, hl, native, support, dl in LOCALES:
        out = SITE / path
        out.mkdir(exist_ok=True)
        (out / "index.html").write_text(build(path, asc, hl, native, support, dl), encoding="utf-8")
        print(f"  /{path}/  <- {asc}")
    write_sitemap()
    print(f"{len(LOCALES)} locale pages + sitemap.xml + index.html hreflang")


if __name__ == "__main__":
    main()
