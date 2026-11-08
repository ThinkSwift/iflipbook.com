<?xml version="1.0" encoding="UTF-8"?>
<!-- Shows a Pinterest feed (tools/pins.py) as a page in the browser: each pin's image, title, description and link.
     Pinterest reads the XML itself and ignores this. -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:media="http://search.yahoo.com/mrss/">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>
<xsl:template match="/rss/channel">
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title><xsl:value-of select="title"/></title>
<style>
:root{--bg:#f7f4ec;--ink:#1b1917;--mute:#5f584c;--card:#fff;--line:#e4ddcd}
@media (prefers-color-scheme:dark){:root{--bg:#1b1917;--ink:#f2eee6;--mute:#b4ab9c;--card:#26231f;--line:#3a352e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.45 -apple-system,system-ui,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:24px;margin:0 0 4px}p.note{color:var(--mute);margin:0 0 20px;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:16px}
.pin{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.pin img{width:100%;aspect-ratio:2/3;object-fit:cover;display:block}
.pin div{padding:10px 12px 12px}.pin b{display:block;font-size:14px}.pin small{display:block;color:var(--mute);font-size:12px;margin-top:4px}
.pin a{color:inherit}
</style></head><body><main>
<h1><xsl:value-of select="title"/></h1>
<p class="note"><xsl:value-of select="count(item)"/> pins in this feed. Pinterest reads this address once a day and pins the new ones.</p>
<div class="grid">
<xsl:for-each select="item">
<div class="pin"><a href="{link}"><img src="{enclosure/@url}" alt="" loading="lazy"/></a>
<div><b><xsl:value-of select="title"/></b><small><xsl:value-of select="substring(pubDate,6,11)"/></small></div></div>
</xsl:for-each>
</div></main></body></html>
</xsl:template>
</xsl:stylesheet>
