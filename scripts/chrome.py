#!/usr/bin/env python3
"""BB104 — the head, nav and footer every page shares, from one source.

**Why this exists.** The chrome was copied into each page by hand. That is
survivable at five pages and not at twenty: a nav that drifts on one page is
invisible to `check.py`, because every link in a stale nav still resolves. The
failure is silent by construction, which is the kind this project fixes with a
generator rather than a habit.

**This is not a build step.** The HTML stays the artefact — the same
arrangement as `sync-assets.py` and the app's `build_help_assets.py`: a
committed script producing committed output, run on demand, with a `--check`
mode so drift fails the gate instead of waiting to be noticed.

    python scripts/chrome.py            # rewrite the chrome in every page
    python scripts/chrome.py --check    # fail if any page's chrome has drifted

Pages may live in a subdirectory (`features/trends.html`); the asset prefix is
computed from the page's depth, so a nested page gets `../assets/...` without
anyone remembering to.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# BB103 — the top navigation, deliberately still four items.
#
# Twelve feature links in the header was the obvious reading of "a page each
# for our features", and it is worse for the half of the audience the split
# exists to serve. The features hub carries them instead, and the header stays
# the size someone can take in at a glance.
# WW360 - five, not four, and this is a deliberate amendment of the note
# above. That note defends four against TWELVE, which was the right call and
# is not what this changes. `verify.html` goes claim by claim - eleven of
# them, each tied to the named test that holds it - and it was reachable only
# from the footer. It is the page that answers a sceptic, buried where only
# somebody already convinced would scroll. Five is still glanceable.
TOP_NAV = [
    ('features.html', 'Features'),
    ('privacy.html', 'Privacy'),
    ('verify.html', 'How to check'),
    ('help.html', 'Help'),
    ('about.html', 'About'),
]

# The org links live here rather than in the header — the place people look for
# them, and the place that can grow without costing anyone a decision.
FOOTER_NAV = [
    ('features.html', 'Features'),
    ('privacy.html', 'Privacy'),
    ('verify.html', 'How to check this'),
    ('data.html', 'What is stored'),
    ('security.html', 'Security'),
    ('help.html', 'Help &amp; support'),
    ('about.html', 'About'),
    ('contact.html', 'Contact'),
    ('accessibility.html', 'Accessibility'),
    ('changes.html', 'What&rsquo;s new'),
    ('terms.html', 'Terms'),
]

FOOTER_NOTE = (
    'Your Health is an independent project. Screenshots show the app running '
    'with demonstration data.'
)

FONTS = (
    'https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,'
    '6..72,400;1,6..72,400&family=Hanken+Grotesk:wght@400;500;600&display=swap'
)


def prefix_for(page):
    """`../` per directory between the page and the site root."""
    rel = os.path.relpath(page, ROOT)
    depth = len(rel.replace('\\', '/').split('/')) - 1
    return '../' * depth


def assets_block(p):
    return f'''<!-- chrome:assets -->
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="{FONTS}" rel="stylesheet" />
    <link rel="stylesheet" href="{p}assets/css/tokens.css" />
    <link rel="stylesheet" href="{p}assets/css/base.css" />
    <link rel="stylesheet" href="{p}assets/css/components.css" />
    <link rel="stylesheet" href="{p}assets/css/motion.css" />
    <script src="{p}assets/js/motion.js" defer></script>
    <!-- /chrome:assets -->'''


def header_block(p):
    links = '\n'.join(
        f'            <a href="{p}{href}">{label}</a>' for href, label in TOP_NAV
    )
    return f'''<!-- chrome:header -->
    <a class="skip" href="#main">Skip to content</a>

    <div class="header-shell">
      <header class="site-header">
        <div class="wrap" style="display: contents">
          <a class="wordmark" href="{p or './'}">Your Health</a>
          <nav aria-label="Main">
{links}
          </nav>
        </div>
      </header>
    </div>
    <!-- /chrome:header -->'''


def footer_block(p):
    links = '\n'.join(
        f'          <a href="{p}{href}">{label}</a>' for href, label in FOOTER_NAV
    )
    return f'''<!-- chrome:footer -->
      <footer class="site-footer">
        <nav aria-label="Footer">
{links}
        </nav>
        <p class="muted" style="max-width: none">
          {FOOTER_NOTE}
        </p>
      </footer>
      <!-- /chrome:footer -->'''


REGIONS = [
    ('assets', assets_block,
     # First run has no markers: match the block as it was hand-written, from
     # the first preconnect through the motion script.
     re.compile(r'<link rel="preconnect" href="https://fonts\.googleapis\.com".*?'
                r'<script src="[^"]*assets/js/motion\.js" defer></script>', re.S)),
    ('header', header_block,
     re.compile(r'<a class="skip".*?</div>\s*(?=\n\s*<main)', re.S)),
    ('footer', footer_block,
     re.compile(r'<footer class="site-footer">.*?</footer>', re.S)),
]


def rewrite(page, html):
    p = prefix_for(page)
    for name, build, first_run in REGIONS:
        block = build(p)
        marked = re.compile(
            rf'<!-- chrome:{name} -->.*?<!-- /chrome:{name} -->', re.S)
        if marked.search(html):
            html = marked.sub(lambda _: block, html, count=1)
        elif first_run.search(html):
            html = first_run.sub(lambda _: block, html, count=1)
        else:
            return html, f'no {name} region found'
    return html, None


def main():
    check_only = '--check' in sys.argv
    pages = sorted(glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True))
    pages = [p for p in pages if 'scripts' + os.sep not in p]

    drifted, broken = [], []
    for page in pages:
        html = open(page, encoding='utf-8').read()
        new, err = rewrite(page, html)
        rel = os.path.relpath(page, ROOT).replace('\\', '/')
        if err:
            broken.append(f'{rel}: {err}')
            continue
        if new == html:
            continue
        drifted.append(rel)
        if not check_only:
            open(page, 'w', encoding='utf-8', newline='').write(new)

    for b in broken:
        print('  MISSING REGION:', b)
    if check_only:
        for d in drifted:
            print('  DRIFTED:', d)
        if drifted or broken:
            print(f'\n{len(drifted)} page(s) with stale chrome, '
                  f'{len(broken)} with none. Run: python scripts/chrome.py')
            return 1
        print(f'chrome consistent across {len(pages)} page(s)')
        return 0

    for d in drifted:
        print('  updated:', d)
    print(f'{len(drifted)} of {len(pages)} page(s) rewritten')
    return 1 if broken else 0


if __name__ == '__main__':
    sys.exit(main())
