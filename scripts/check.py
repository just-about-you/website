"""Y140 — the checks that must pass before the site goes anywhere.

Deliberately dependency-free so it runs anywhere without an install step.
Checks structure and links, not rendering; rendering is checked by eye.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_HOSTS = {'fonts.googleapis.com', 'fonts.gstatic.com'}

problems = []


def check(page, html):
    name = os.path.basename(page)

    # Every image resolves, and carries alt text.
    for tag in re.findall(r'<img\b[^>]*>', html):
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            problems.append(f'{name}: <img> with no src')
            continue
        if not src.group(1).startswith('http'):
            path = os.path.join(ROOT, src.group(1))
            if not os.path.exists(path):
                problems.append(f'{name}: missing image {src.group(1)}')
        alt = re.search(r'alt="([^"]*)"', tag)
        if not alt or not alt.group(1).strip():
            problems.append(f'{name}: image without alt text -> {src.group(1)}')

    # Internal links resolve.
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith(('http', 'mailto:', '#', './')):
            continue
        target = href.split('#')[0]
        if target and not os.path.exists(os.path.join(ROOT, target)):
            problems.append(f'{name}: dead link -> {href}')

    # No external host except Google Fonts. A CDN script or a remote image is
    # both a privacy leak on a site that argues about privacy, and a thing that
    # breaks when the CDN does.
    for url in re.findall(r'(?:src|href)="(https?://[^"]+)"', html):
        host = url.split('/')[2]
        if host not in ALLOWED_HOSTS:
            problems.append(f'{name}: external request to {host}')

    # Structure that accessibility depends on.
    if '<html lang=' not in html:
        problems.append(f'{name}: <html> has no lang')
    if not re.search(r'<title>[^<]+</title>', html):
        problems.append(f'{name}: no <title>')
    # Tolerant of the tag being wrapped across lines, which every hand-authored
    # page here does. The first version required it contiguous and reported
    # three false failures.
    if not re.search(r'<meta\s[^>]*name="description"[^>]*content="[^"]+"', html, re.S):
        problems.append(f'{name}: no meta description')
    if html.count('<h1') != 1:
        problems.append(f'{name}: expected exactly one <h1>, found {html.count("<h1")}')
    if 'class="skip"' not in html:
        problems.append(f'{name}: no skip link')

    # The claim this whole product rests on — a page must not promise medical
    # care. Checked as a word-boundary match so "not a medical device" is fine.
    for phrase in ('diagnose your', 'treats ', 'cures ', 'medical advice for you'):
        if phrase in html.lower():
            problems.append(f'{name}: possible clinical claim -> "{phrase}"')


pages = sorted(glob.glob(os.path.join(ROOT, '*.html')))
for page in pages:
    check(page, open(page, encoding='utf-8').read())

print(f'checked {len(pages)} page(s)')
if problems:
    for p in problems:
        print('  FAIL:', p)
    sys.exit(1)
print('  all checks passed')
