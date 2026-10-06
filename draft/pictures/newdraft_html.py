# python newdraft_html.py <NewDraft.md> <out.html> -- fcad's docs/NewDraft.md
# as one HTML page for publishing.
#
# The page references its pictures as pictures/NewDraft/<case>.png, as the
# doc does (relative to docs/): publish docs/pictures/NewDraft/*.png at those
# paths with it. Needs python-markdown (the FreeCAD conda env has it).
import html
import re
import sys

import markdown

SRC, OUT = sys.argv[1], sys.argv[2]
text = open(SRC, encoding="utf-8").read()
first, body = text.split("\n", 1)
title = first.lstrip("# ").strip()
# the status paragraph opens the page; the rest is the body
status, body = body.strip().split("\n\n", 1)

md = markdown.Markdown(extensions=["toc", "tables", "fenced_code"],
                       extension_configs={"toc": {"toc_depth": "2-3"}})
out = md.convert(body)
status_html = markdown.markdown(status)


def figures(m):
    figs = []
    for alt, src in re.findall(r'<img alt="([^"]*)" src="([^"]*)"\s*/?>', m.group(0)):
        figs.append('<figure><a href="%s"><img alt="%s" src="%s" loading="lazy"></a>'
                    '<figcaption>%s</figcaption></figure>' % (src, alt, src, alt))
    return "\n".join(figs)


out = re.sub(r"<p>(?:\s*<img [^>]*>\s*)+</p>", figures, out)
# tables scroll in their own box
out = out.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")
# a double hyphen reads as a dash
dash = lambda s: re.sub(r"(?<=\s)--(?=\s)", "&ndash;", s)
out, status_html, title_html = dash(out), dash(status_html), dash(html.escape(title))

toc = []
for level, hid, inner in re.findall(r'<h([23]) id="([^"]+)">(.*?)</h\1>', out):
    label = re.sub(r"<[^>]+>", "", inner)
    toc.append('<li class="l%s"><a href="#%s">%s</a></li>' % (level, hid, label))
nfig = len(re.findall(r"<figure>", out))

page = """<title>The Cell Draft</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600;700&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap">
<style>
:root {
  --ground: #f4f6f8;
  --paper: #fbfcfd;
  --ink: #1b2430;
  --muted: #5a6677;
  --rule: #d9dfe7;
  --steel: #4d6a8c;
  --steel-soft: #e3e9f1;
  --draft: #b85a12;
  --draft-soft: #fbeadb;
  --code-bg: #eceff4;
  --shadow: 0 1px 2px rgba(27, 36, 48, .06), 0 6px 24px rgba(27, 36, 48, .06);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --ground: #11151b;
    --paper: #161b22;
    --ink: #e4e9f0;
    --muted: #9aa6b6;
    --rule: #2a323e;
    --steel: #8fabcc;
    --steel-soft: #1f2a37;
    --draft: #f0954a;
    --draft-soft: #33241a;
    --code-bg: #1d232c;
    --shadow: none;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --ground: #11151b;
  --paper: #161b22;
  --ink: #e4e9f0;
  --muted: #9aa6b6;
  --rule: #2a323e;
  --steel: #8fabcc;
  --steel-soft: #1f2a37;
  --draft: #f0954a;
  --draft-soft: #33241a;
  --code-bg: #1d232c;
  --shadow: none;
}
body {
  background: var(--ground);
  color: var(--ink);
  font: 400 16px/1.62 "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  padding-inline: 16px;
  padding-block: 0 64px;
}
.wrap { max-width: 1240px; margin: 0 auto; display: grid; grid-template-columns: 1fr; gap: 32px; }
@media (min-width: 1080px) { .wrap { grid-template-columns: 250px minmax(0, 1fr); } }
header.top { grid-column: 1 / -1; padding-block: 40px 8px; border-bottom: 1px solid var(--rule); }
.eyebrow {
  font: 500 12px/1.4 "IBM Plex Mono", ui-monospace, monospace;
  letter-spacing: .06em; text-transform: uppercase; color: var(--steel);
  display: flex; flex-wrap: wrap; gap: 6px 18px;
}
.eyebrow span::before { content: ""; display: inline-block; width: 8px; height: 8px;
  margin-right: 8px; vertical-align: 1px; background: var(--draft); }
.eyebrow span + span::before { background: var(--steel); }
h1 {
  font: 700 clamp(30px, 4.4vw, 46px)/1.08 "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  letter-spacing: -.01em; margin: 14px 0 12px; text-wrap: balance; max-width: 22ch;
}
.status { max-width: 72ch; color: var(--muted); font-size: 15.5px; }
.status p { margin: 0 0 14px; }
.count { font: 400 13px/1.5 "IBM Plex Mono", ui-monospace, monospace; color: var(--muted); margin: 0 0 22px; }
nav.toc { font-size: 14px; }
@media (min-width: 1080px) {
  nav.toc { position: sticky; top: calc(env(safe-area-inset-top, 0px) + 20px);
    max-height: calc(100vh - 40px); overflow-y: auto; padding-right: 6px; }
}
nav.toc h2 { font: 600 12px/1.4 "IBM Plex Mono", ui-monospace, monospace; letter-spacing: .08em;
  text-transform: uppercase; color: var(--muted); margin: 6px 0 10px; }
nav.toc ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
nav.toc li.l3 { padding-left: 14px; font-size: 13px; }
nav.toc a { color: var(--ink); text-decoration: none; display: block; padding: 3px 8px;
  border-left: 2px solid transparent; border-radius: 0 4px 4px 0; }
nav.toc li.l2 > a { font-weight: 500; }
nav.toc a:hover, nav.toc a:focus-visible { background: var(--steel-soft); border-left-color: var(--steel); outline: none; }
@media (max-width: 1079px) {
  nav.toc { background: var(--paper); border: 1px solid var(--rule); border-radius: 6px; padding: 12px 14px; }
  nav.toc ul { grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }
}
main { min-width: 0; }
main > * { max-width: 74ch; }
main h2 {
  font: 600 27px/1.2 "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  margin: 56px 0 14px; padding-top: 18px; border-top: 2px solid var(--ink); text-wrap: balance;
}
main h3 { font: 600 19px/1.3 "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  margin: 34px 0 10px; color: var(--steel); text-wrap: balance; }
main h2:first-child { margin-top: 18px; }
p, li { margin: 0 0 14px; }
ul, ol { padding-left: 22px; }
li { margin-bottom: 8px; }
a { color: var(--steel); text-underline-offset: 3px; }
code { font: 400 .87em/1.4 "IBM Plex Mono", ui-monospace, monospace; background: var(--code-bg);
  padding: .08em .32em; border-radius: 3px; overflow-wrap: anywhere; }
strong { font-weight: 600; }
pre { background: var(--code-bg); padding: 14px 16px; border-radius: 6px; overflow-x: auto; }
pre code { background: none; padding: 0; }
.tbl { max-width: 100%%; overflow-x: auto; margin: 6px 0 22px; border: 1px solid var(--rule);
  border-radius: 6px; background: var(--paper); }
table { border-collapse: collapse; font-size: 14px; min-width: 100%%; }
th, td { padding: 8px 12px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--rule); }
th { font: 600 12.5px/1.4 "IBM Plex Mono", ui-monospace, monospace; letter-spacing: .02em;
  color: var(--muted); background: var(--steel-soft); }
tr:last-child td { border-bottom: none; }
td[style*="right"], th[style*="right"] { font-variant-numeric: tabular-nums; white-space: nowrap; }
figure { max-width: none; margin: 22px 0 30px; background: #fff; border: 1px solid var(--rule);
  border-radius: 6px; box-shadow: var(--shadow); overflow: hidden; }
figure a { display: block; }
figure img { display: block; width: 100%%; height: auto; }
figcaption { font: 500 12.5px/1.4 "IBM Plex Mono", ui-monospace, monospace; color: #5a6677;
  padding: 8px 12px; border-top: 1px solid #e4e8ee; background: #f7f8fa; }
footer { grid-column: 1 / -1; border-top: 1px solid var(--rule); padding-top: 18px;
  color: var(--muted); font-size: 13.5px; }
footer p { max-width: 90ch; }
@media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
</style>
<div class="wrap">
  <header class="top">
    <div class="eyebrow"><span>FreeCAD (realthunder) &middot; Part::CellDraft</span><span>PartDesign Draft &middot; Method = Auto / New</span></div>
    <h1>%(title)s</h1>
    <div class="status">%(status)s</div>
    <p class="count">%(nfig)d pictures &middot; source <code>fcad/docs/NewDraft.md</code></p>
  </header>
  <nav class="toc" aria-label="Contents"><h2>Contents</h2><ul>%(toc)s</ul></nav>
  <main>%(body)s</main>
  <footer><p>Rendered from <code>docs/NewDraft.md</code> by <code>occt/tests/fork/draft/pictures/newdraft_html.py</code>; the pictures come from <code>make_newdraft.sh</code> beside it. The cases are drafted through PartDesign, each recomputed as a document would be.</p></footer>
</div>
""" % dict(title=title_html, status=status_html, nfig=nfig, toc="\n".join(toc), body=out)
open(OUT, "w", encoding="utf-8").write(page)
print(OUT, len(page), "bytes,", len(toc), "headings,", nfig, "pictures")
