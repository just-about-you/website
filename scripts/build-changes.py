#!/usr/bin/env python3
"""BB143 — the What's new page, rendered from the app's CHANGELOG.

Hand-writing it would mean a release note existing in two places, and this
project has now been bitten four separate times by copy that stopped matching
what it described. So the changelog stays the single source and this renders
it; adding a release there makes it appear here with nobody editing HTML.

    python scripts/build-changes.py
    python scripts/build-changes.py --check   # fail if changes.html is stale

Supports the subset the changelog actually uses: `##` release, `###` section,
`-` bullets, paragraphs, `**bold**` and `` `code` ``. Anything else is passed
through escaped rather than guessed at — a renderer that silently swallows
markup it does not understand is how a release note goes half-published.
"""
import html as html_mod
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SOURCE = os.path.normpath(os.path.join(SITE, '..', 'app', 'CHANGELOG.md'))
OUT = os.path.join(SITE, 'changes.html')


def inline(text):
    text = html_mod.escape(text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text


def render(md):
    out, bullets, para = [], [], []

    def flush_para():
        if para:
            out.append('          <p>' + inline(' '.join(para)) + '</p>')
            para.clear()

    def flush_bullets():
        if bullets:
            out.append('          <ul>')
            out.extend(f'            <li>{inline(b)}</li>' for b in bullets)
            out.append('          </ul>')
            bullets.clear()

    open_release = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if line.startswith('# '):
            continue
        if line.startswith('## '):
            flush_para(); flush_bullets()
            if open_release:
                out.append('        </article>')
            out.append('        <article class="card" style="grid-column: 1 / -1">')
            out.append(f'          <h2>{inline(line[3:])}</h2>')
            open_release = True
            continue
        if line.startswith('### '):
            flush_para(); flush_bullets()
            out.append(f'          <h3>{inline(line[4:])}</h3>')
            continue
        if line.startswith('- '):
            flush_para()
            bullets.append(line[2:])
            continue
        if line.startswith('  ') and bullets:
            bullets[-1] += ' ' + line.strip()
            continue
        if not line.strip():
            flush_para(); flush_bullets()
            continue
        para.append(line.strip())

    flush_para(); flush_bullets()
    if open_release:
        out.append('        </article>')
    return '\n'.join(out)


PAGE = '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>What&rsquo;s new — Your Health</title>
    <meta name="description" content="What changed in each release of Your Health, taken straight from the changelog that ships with the app." />
    <!-- chrome:assets -->
    <!-- /chrome:assets -->
  </head>
  <body>
    <!-- chrome:header -->
    <!-- /chrome:header -->

    <main id="main">
      <section class="wrap hero" style="padding-bottom: var(--gap-l)">
        <div class="hero-in">
          <p class="eyebrow">Releases</p>
          <h1>What&rsquo;s <span class="hl">new</span>.</h1>
          <p class="lede">
            Taken straight from the changelog that ships with the app, so this
            page cannot drift from what was actually released.
          </p>
        </div>
      </section>

      <section class="wrap" style="padding-block: var(--gap-l)">
        <div class="grid reveal-group">
{body}
        </div>
      </section>
    </main>

    <div class="wrap">
      <!-- chrome:footer -->
      <!-- /chrome:footer -->
    </div>
  </body>
</html>
'''


def main():
    if not os.path.exists(SOURCE):
        print('no changelog at ' + SOURCE)
        return 1
    md = io.open(SOURCE, encoding='utf-8').read()
    page = PAGE.format(body=render(md))

    existing = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
    if '--check' in sys.argv:
        # Compare only what this script owns: the chrome regions are filled in
        # afterwards by chrome.py, so a straight equality check would report
        # drift on every run.
        if existing is None:
            print('  MISSING: changes.html'); return 1
        mine = re.search(r'<div class="grid reveal-group">(.*?)</div>', page, re.S)
        theirs = re.search(r'<div class="grid reveal-group">(.*?)</div>', existing, re.S)
        if not theirs or mine.group(1) != theirs.group(1):
            print('  STALE: changes.html no longer matches app/CHANGELOG.md')
            return 1
        print('changes.html matches the changelog')
        return 0

    io.open(OUT, 'w', encoding='utf-8', newline='').write(page)
    releases = len(re.findall(r'^## ', md, re.M))
    print(f'changes.html rendered from {releases} release(s)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
