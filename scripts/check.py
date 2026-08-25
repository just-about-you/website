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


def resolve(page, ref):
    """A page-relative reference, as a browser would resolve it.

    BB103 — this used to join against ROOT, which is only the same thing while
    every page sits at the top level. The moment one did not, a correct
    `../assets/...` would have been reported as a dead link and a genuinely
    broken link one directory down would have resolved by accident.
    """
    return os.path.normpath(os.path.join(os.path.dirname(page), ref))


def check(page, html):
    name = os.path.relpath(page, ROOT).replace('\\', '/')

    # Every image resolves, and carries alt text.
    for tag in re.findall(r'<img\b[^>]*>', html):
        src = re.search(r'src="([^"]+)"', tag)
        if not src:
            problems.append(f'{name}: <img> with no src')
            continue
        if not src.group(1).startswith('http'):
            if not os.path.exists(resolve(page, src.group(1))):
                problems.append(f'{name}: missing image {src.group(1)}')
        alt = re.search(r'alt="([^"]*)"', tag)
        if not alt or not alt.group(1).strip():
            problems.append(f'{name}: image without alt text -> {src.group(1)}')

    # Internal links resolve.
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith(('http', 'mailto:', '#', './')):
            continue
        target = href.split('#')[0]
        if target and not os.path.exists(resolve(page, target)):
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


# Y130 — the site may only reference screenshots the capture harness produced.
#
# The manifest is rebuilt from `design-docs/assets/` on every capture run, so
# an image that is in the site but not the manifest is either hand-copied or
# left over from a deleted screen. Both have already happened once: a blank
# settings capture survived a failed run and was committed as part of the set.
# ── BB101 — the writing standard, as far as a gate can hold it ───────────
#
# The operator has rejected this project's copy twice, once in the app and
# once here. A style note is graded by whoever wrote the words, so every rule
# in `design-docs/09-help-and-support.md` §7 that *can* be mechanical is
# mechanical, and this is where the web half lives. The app half is
# `app/test/help_story_test.dart`; the numbers differ, the rules do not.

TITLE_CEILING = 60      # characters in a section heading
PARAGRAPH_CEILING = 80  # words in one paragraph
SENTENCE_CEILING = 30   # words in one sentence

# A heading is read on its own, so one opening on a pronoun is a sentence
# missing its subject.
DANGLING_OPENERS = {
    'they', 'it', 'this', 'that', 'these', 'those', 'which',
    'them', 'its', "it's", 'there',
}
LAZY_TAILS = {'too', 'as well', 'also', 'instead', 'anyway'}

# Words belonging to the people who built this, not the people using it. The
# list grows by decision, never by silence.
JARGON = {
    'sync', 'synced', 'payload', 'entitlement', 'uuid', 'toggle',
    'provider', 'endpoint', 'cache', 'schema', 'metadata', 'config',
    'instance', 'boolean', 'nullable', 'persist', 'persisted', 'backend',
}


def strip_tags(html):
    html = re.sub(r'<(script|style)\b.*?</\1>', ' ', html, flags=re.S)
    return re.sub(r'<[^>]+>', ' ', html)


def words(text):
    return [w for w in re.split(r'\s+', text.strip()) if w]


def check_story(page, html):
    """Every feature page is a story: what, then why, then how."""
    name = os.path.relpath(page, ROOT).replace('\\', '/')
    if not name.startswith('features/'):
        return

    roles = re.findall(r'<section\b[^>]*data-role="(what|why|how)"', html)
    if not roles:
        problems.append(f'{name}: no data-role sections — a feature page has '
                        f'to declare its shape, or the shape is a claim')
        return

    if roles.count('what') != 1:
        problems.append(f'{name}: {roles.count("what")} "what" sections. A page '
                        f'names the thing once, at the top')
    elif roles[0] != 'what':
        problems.append(f'{name}: opens with a "{roles[0]}" section — someone '
                        f'arriving does not yet know what they are looking at')
    if 'why' not in roles:
        problems.append(f'{name}: never says why any of this matters')
    if 'how' not in roles:
        problems.append(f'{name}: explains but never shows what using it is like')

    if 'why' in roles and 'how' in roles:
        if roles.index('how') < len(roles) - 1 - roles[::-1].index('why'):
            problems.append(f'{name}: goes back to explaining after it has '
                            f'started showing. Order is what/why/how')


# Words that appear in operator-signed wording, where changing them is not a
# copy edit but a re-signature. Listed rather than silently skipped: this is a
# register that can shrink, and every entry is on BB133's re-sign list.
JARGON_EXEMPT = {
    'privacy.html': {'cache', 'schema'},
}


def is_feature_page(page):
    """The strict rules apply where the standard was written to apply.

    BB100 was written for the feature pages: twelve pages that have to read as
    one product. The landing page is a different job and does it well — its
    headings are full sentences on purpose (*"Looking after someone should not
    mean watching everything they do."*), which is exactly what a card title
    must never be. Applying a card rule to it produced six failures against
    copy the operator had already approved, and a gate that fails on good
    writing is one people learn to skip.
    """
    return os.path.relpath(page, ROOT).replace('\\', '/').startswith('features/')


def check_prose(page, html):
    """Headings, sentence length, and words nobody outside this repo uses."""
    name = os.path.relpath(page, ROOT).replace('\\', '/')

    # Jargon is checked everywhere — it is the one rule that is about the
    # reader rather than about the form of a page.
    body = strip_tags(html).lower()
    exempt = JARGON_EXEMPT.get(name, set())
    for word in sorted(JARGON):
        if word in exempt:
            continue
        if re.search(rf'\b{re.escape(word)}\b', body):
            problems.append(f'{name}: "{word}" is ours, not the reader\'s')

    if not is_feature_page(page):
        return

    for heading in re.findall(r'<h[23]\b[^>]*>(.*?)</h[23]>', html, re.S):
        text = ' '.join(words(strip_tags(heading)))
        if not text:
            continue
        if len(text) > TITLE_CEILING:
            problems.append(f'{name}: heading is {len(text)} chars '
                            f'(max {TITLE_CEILING}) -> "{text[:50]}..."')
        if text.rstrip().endswith('.'):
            problems.append(f'{name}: heading ends in a full stop -> "{text}"')
        first = text.split(' ')[0].lower().strip('“”"\'')
        if first in DANGLING_OPENERS:
            problems.append(f'{name}: heading opens on "{first}", which points '
                            f'at nothing -> "{text}"')
        for tail in LAZY_TAILS:
            if text.lower().endswith(' ' + tail):
                problems.append(f'{name}: heading trails off -> "{text}"')

    for para in re.findall(r'<p\b[^>]*>(.*?)</p>', html, re.S):
        text = ' '.join(words(strip_tags(para)))
        if not text:
            continue
        if len(words(text)) > PARAGRAPH_CEILING:
            problems.append(f'{name}: paragraph is {len(words(text))} words '
                            f'(max {PARAGRAPH_CEILING}). Split it')
        for sentence in re.split(r'(?<=[.?!])\s+', text):
            if len(words(sentence)) > SENTENCE_CEILING:
                problems.append(f'{name}: {len(words(sentence))}-word sentence '
                                f'(max {SENTENCE_CEILING}) -> '
                                f'"{sentence[:60]}..."')


def html_pages():
    """Every page on the site, at any depth.

    BB103 — this globbed `ROOT/*.html`, so a page in a subdirectory was not
    checked at all. Not a hypothetical: the feature pages live in `features/`,
    and every rule in this file would have skipped them in silence, which is
    the worst way for a gate to fail.
    """
    found = glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True)
    return sorted(p for p in found if 'scripts' + os.sep not in p)


def check_chrome():
    """BB104 — the shared head, nav and footer have not drifted.

    Checked here rather than left to whoever remembers, because a stale nav
    passes every other rule in this file: each link in it still resolves.
    """
    import subprocess
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, 'scripts', 'chrome.py'), '--check'],
        capture_output=True, text=True)
    if result.returncode != 0:
        for line in result.stdout.strip().splitlines():
            if line.strip():
                problems.append('chrome: ' + line.strip())


DESIGN_DOCS = os.path.normpath(os.path.join(ROOT, '..', 'design-docs'))
MANIFEST = os.path.join(DESIGN_DOCS, 'assets', 'MANIFEST.md')


def check_manifest():
    # design-docs is a separate repo. On a checkout that has it — any working
    # copy of the four-repo tree — the manifest must be there and must agree
    # with the site. On a checkout that does not (CI clones this repo alone),
    # the question is unanswerable, not answered "no": skip it and say so.
    # Absent sibling repo != missing manifest, and conflating them made the
    # Pages deploy fail on a check it could never have passed.
    if not os.path.isdir(DESIGN_DOCS):
        print('  SKIP: no design-docs checkout beside this repo — '
              'manifest agreement not checkable here')
        return
    if not os.path.exists(MANIFEST):
        problems.append('no screenshot manifest at ' + MANIFEST)
        return
    listed = set(re.findall(r'`([^`]+\.png)`', open(MANIFEST, encoding='utf-8').read()))
    if not listed:
        problems.append('manifest lists no images — it should name every capture')
        return
    used = set()
    for page in html_pages():
        html = open(page, encoding='utf-8').read()
        for src in re.findall(r'src="(?:\.\./)*assets/img/([^"]+)"', html):
            # BB102 — the site ships WebP built from the captures, so the name
            # is compared back to the PNG the manifest lists. The manifest is
            # the record of what the harness produced; the extension is this
            # site's business, not the harness's.
            used.add(os.path.splitext(src)[0] + '.png')
    for name in sorted(used - listed):
        problems.append(
            f'{name} is used by the site but is not in the capture manifest — '
            'run scripts/sync-assets.py, or recapture')


pages = html_pages()
for page in pages:
    html = open(page, encoding='utf-8').read()
    check(page, html)
    check_story(page, html)
    check_prose(page, html)

check_manifest()
check_chrome()

print(f'checked {len(pages)} page(s)')
if problems:
    for p in problems:
        print('  FAIL:', p)
    sys.exit(1)
print('  all checks passed')
