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


# ── PP425 — a sibling repo that is missing must not read as "checked" ────
#
# Two guards in this repo need a repo that is not this one. The screenshot
# manifest lives in `design-docs/`; the capture inventory and the changelog
# live in `app/`. On a working copy of the six-repo tree both are there, and
# the question "does the site agree with them?" has an answer.
#
# On a checkout that has neither, the honest answer is "unanswerable" — and
# what these guards used to do with that was print SKIP and exit 0. A green
# tick. CI clones this repo alone, so the only cross-repo guard the site had
# printed SKIP on every run since it was written, and every green Y140 gate
# since has been read as evidence the manifest agreed. It was evidence of
# nothing. A guard that could not run is not a guard that passed.
#
# So unanswerable is a local convenience and a CI failure. `CI` is set by
# GitHub Actions and by every other runner, so this is right by default and
# cannot be forgotten in a workflow edit. The escape hatch is named for what it
# actually does, and it shows up in a diff.
def siblings_are_required():
    if os.environ.get('ALLOW_MISSING_SIBLING_REPOS') == '1':
        return False
    return bool(os.environ.get('CI'))


def missing_sibling(repo, what):
    """Excuse a guard that could not run for want of `repo`, or fail on it."""
    if siblings_are_required():
        problems.append(
            f'no {repo} checkout beside this repo, so {what} was not '
            f'checked. In CI that is a failure and not a skip: check the '
            f'sibling out, or set ALLOW_MISSING_SIBLING_REPOS=1 to say out '
            f'loud that this run does not check it')
    else:
        print(f'  SKIP: no {repo} checkout beside this repo — {what} '
              f'not checkable here')


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
    #
    # WW310 — a root-absolute `/foo.html` resolves against ROOT, not against the
    # page's own directory. 404.html needs those: it is served for ANY missing
    # path, including one directory down, where a relative `features.html`
    # would resolve to `/features/features.html` and send a lost visitor
    # somewhere else lost. Before this it was neither resolved nor skipped —
    # `os.path.join(dirname, '/features.html')` returns '/features.html', which
    # does not exist on disk, so every correct absolute link read as dead.
    for href in re.findall(r'href="([^"]+)"', html):
        if href.startswith(('http', 'mailto:', '#', './')):
            continue
        target = href.split('#')[0]
        if not target:
            continue
        if target.startswith('/'):
            found = os.path.exists(os.path.join(ROOT, target.lstrip('/')))
        else:
            found = os.path.exists(resolve(page, target))
        if not found:
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

    # ...and the same claim made as a shape rather than as one of four
    # phrases. See VERDICT_SHAPES.
    check_verdict_shape(name, html)


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


# ── PP425 — a clinical claim has a shape, not a spelling ────────────────
#
# The four fixed substrings in `check()` catch a page offering to diagnose or
# to treat. They do not catch the sentence this product is actually at risk of
# publishing, which is a verdict about the reader's own reading: *"your blood
# pressure is normal"*. The app refuses precisely that at construction —
# `MetricTileCard` rejects `normal`, `high`, `low`, `stage`, `overweight` and
# `obese` as status text — and `about.html` publishes that refusal as a
# promise to the reader. Until now the site itself was free to break it.
#
# A longer substring list would not do, because the failure is a shape and not
# a word. `normal` appears legitimately on this site inside the sentence that
# lists the forbidden words; `high` and `low` are ordinary English. So what is
# matched is the shape: the reader's own reading, a linking verb, and a
# verdict, inside one sentence.
#
# The test of this test is that it must NOT fire on the population-reference
# wording `about.html` and `terms.html` carry — "coloured against published
# general guidelines … nothing in it states a verdict about your health" —
# which is the legitimate way to say this and is operator-signed copy. That is
# why the pattern demands `your <reading>` and not the reading alone: a
# guideline is about everybody, a verdict is about you. Both pages are checked
# on every run and neither matches.
READING = (r'(?:blood pressure|blood sugar|blood glucose|glucose|oxygen'
           r'|heart rate|pulse|weight|bmi|body mass index|sleep'
           r'|readings?|numbers?|levels?|results?|scores?)')
VERDICT = (r'(?:normal|abnormal|healthy|unhealthy|elevated|too high|too low'
           r'|high|low|overweight|obese|borderline|stage \d'
           r'|fine|good|bad|poor|excellent|concerning|worrying)')
LINK = r'(?:is|are|was|were|looks?|seems?|appears?|reads?|came back)'
# A named condition, for the second shape. Deliberately narrower than VERDICT:
# "you have high blood pressure" is a diagnosis, "you have good reason" is
# English, and only the first may be caught.
CONDITION = (rf'(?:overweight|obese|obesity|hypertensive|hypertension'
             rf'|pre-?hypertension|pre-?diabetes|pre-?diabetic|diabetes'
             rf'|diabetic|(?:high|low|elevated|abnormal)\s+(?:\w+\s+)?'
             rf'{READING})')

VERDICT_SHAPES = (
    # "your blood pressure is normal", "your numbers look fine"
    re.compile(rf'\byour\s+(?:\w+\s+){{0,2}}{READING}\b[^.?!]{{0,40}}?'
               rf'\b{LINK}\b\s+(?:\w+\s+){{0,3}}{VERDICT}\b', re.I),
    # "you are overweight", "you have high blood pressure"
    re.compile(rf'\byou\s+(?:are|were|have|had|may have|might have)\b'
               rf'[^.?!]{{0,30}}?\b{CONDITION}\b', re.I),
)

BLOCK_END = re.compile(
    r'</(?:p|h[1-6]|li|td|th|div|section|article|figcaption|blockquote)>',
    re.I)


def prose(html):
    """The page as sentences, with block boundaries kept as sentence ends.

    `strip_tags` turns every tag into a space, which would let a heading and
    the paragraph beneath it run together into a sentence neither of them
    wrote — which is exactly how a shape test invents a claim nobody
    published. The shapes above refuse to cross `.?!`, so block ends become
    one.
    """
    html = re.sub(r'<(script|style)\b.*?</\1>', ' ', html, flags=re.S)
    html = BLOCK_END.sub('. ', html)
    return ' '.join(words(re.sub(r'<[^>]+>', ' ', html)))


def check_verdict_shape(name, html):
    text = prose(html)
    for pattern in VERDICT_SHAPES:
        for hit in pattern.finditer(text):
            problems.append(
                f'{name}: states a verdict about the reader rather than '
                f'against a published guideline -> "{hit.group(0).strip()}"')


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


def images_used_by_site():
    """Every capture the site references, named as the PNG the harness wrote.

    BB102 — the site ships WebP built from the captures, so the name is
    compared back to the PNG. The manifest and the inventory are both records
    of what the harness produced; the extension is this site's business, not
    the harness's.
    """
    used = set()
    for page in html_pages():
        html = open(page, encoding='utf-8').read()
        for src in re.findall(r'src="(?:\.\./)*assets/img/([^"]+)"', html):
            used.add(os.path.splitext(src)[0] + '.png')
    return used


def check_manifest():
    # design-docs is a separate repo. On a checkout that has it — any working
    # copy of the four-repo tree — the manifest must be there and must agree
    # with the site. On a checkout that does not (CI clones this repo alone),
    # the question is unanswerable, not answered "no": skip it and say so.
    # Absent sibling repo != missing manifest, and conflating them made the
    # Pages deploy fail on a check it could never have passed.
    if not os.path.isdir(DESIGN_DOCS):
        # PP425 — this used to print and return, which passed. See
        # `missing_sibling`.
        missing_sibling('design-docs', 'agreement with the screenshot manifest')
        return
    if not os.path.exists(MANIFEST):
        problems.append('no screenshot manifest at ' + MANIFEST)
        return
    listed = set(re.findall(r'`([^`]+\.png)`', open(MANIFEST, encoding='utf-8').read()))
    if not listed:
        problems.append('manifest lists no images — it should name every capture')
        return
    for name in sorted(images_used_by_site() - listed):
        problems.append(
            f'{name} is used by the site but is not in the capture manifest — '
            'run scripts/sync-assets.py, or recapture')


# ── PP425 — the site may not ship a capture the app has declared wrong ───
#
# `check_manifest` above is one-directional: it fails when the site uses an
# image the manifest does not list, and says nothing when the site uses an
# image that is listed *and* known to photograph a screen that no longer
# exists. Both `40-tasks` and `83-medications-full` are in that state and both
# ship today — one of them on the landing page.
#
# **Where the marker lives, and why it is not in the manifest.** The obvious
# move is a machine-readable `stale:` line in `design-docs/assets/MANIFEST.md`,
# next to the prose that already says `30-people.png` and `50-checkin.png`
# "mislead as a set". That is refused, on two grounds:
#
#   1. **MANIFEST.md is generated, and rewritten whole.** The capture driver
#      (`app/test_driver/integration_test.dart:88-93`) builds the entire file
#      from a template and the folder listing on every run, and the file says
#      so in its first line. Any marker written there survives until the next
#      `flutter drive` and not one run longer — a guard with a scheduled
#      deletion date.
#   2. **The inventory already exists and is already enforced.** KK150 put it
#      in `app/lib/features/help/help_capture_inventory.dart`, where
#      `app/test/help_capture_freshness_test.dart` holds it in both
#      directions: an entry must carry a reason, a date and the task that
#      retakes the shot, and it must still match the PNG on disk, so a
#      regenerated capture whose entry was left behind fails. MANIFEST.md's
#      own prose records that the list moved there for exactly this reason. A
#      second copy in a second repo would be a second thing to keep true.
#
# So this reads the app's list rather than growing one here, and
# `design-docs/` needs no change at all.
#
# **What this cannot see**, stated rather than pretended away: the app's
# inventory is per-screen, and `30-people` / `50-checkin` are stale for a
# reason that is not on their screen — they were shot when People and Check-in
# were bottom-bar destinations, and it is `app_shell.dart` that changed, not
# `people_screen.dart`. Both therefore sit in the fingerprint half of the
# inventory rather than the stale half, and this guard passes them. Closing
# that is a change in `app/`, not here: either add
# `lib/shared/widgets/app_shell.dart` to their source sets — which trips their
# fingerprints immediately, because the shell did change — or list them in
# `knownStaleCaptures`. Recorded in README.md under "Cross-repo guards".
APP = os.path.normpath(os.path.join(ROOT, '..', 'app'))
CAPTURE_INVENTORY = os.path.join(
    APP, 'lib', 'features', 'help', 'help_capture_inventory.dart')


def known_stale_captures(src=None):
    """`knownStaleCaptures` from the app.

    Returns **None** when the declaration is absent — the reader has broken and
    the caller must fail. Returns a **dict, possibly empty**, when it is
    present: an empty map is a real and expected state.

    WW100 — those two were one return value until 2026-09-03, and the day the
    map legitimately drained the guard accused the app of moving a file that
    had not moved. TT150 retook all 29 shipped captures on Clover, every one
    moved to a recorded fingerprint, and the map emptied exactly as it was
    designed to. `if not body: return {}` could not tell that from a reader
    that had stopped matching, so it reported the wrong one.

    Failing safe was right and stays: an absent declaration is still a hard
    failure, because a reader that quietly stops matching is a guard that
    quietly stops guarding. What changes is that a drained queue is no longer
    mistaken for one.

    [src] is for the self-test below; production reads the file.
    """
    if src is None:
        src = open(CAPTURE_INVENTORY, encoding='utf-8').read()
    body = re.search(
        r'const Map<String, StaleCapture> knownStaleCaptures = \{(.*?)\n\};',
        src, re.S)
    if not body:
        return None
    found = {}
    for entry in re.finditer(r"^  '([^']+)': StaleCapture\((.*?)\n  \),",
                             body.group(1), re.S | re.M):
        task = re.search(r"regeneratedBy: '([^']*)'", entry.group(2))
        found[entry.group(1)] = task.group(1) if task else 'unassigned'
    return found


# ── PP440 — a deleted screen is a worse picture than a drifted one ───────
#
# `knownStaleCaptures` is "this photograph no longer looks like the screen".
# `retiredCaptures`, in the same file, is the stronger statement: **the screen
# is gone**, no step in the app renders the picture, and the asset must not be
# in the app's bundle at all. Reading only the first half meant the site could
# ship a picture of a surface that does not exist and the gate would call it
# green — and it did: `62-medications.webp` is on the landing page twice, and
# MM260 deleted that screen outright.
#
# That green was the expensive part. A guard that catches stale-but-real
# captures while missing deleted ones reads as coverage of both, so nobody
# looks. The two maps are read together for that reason, and counted out loud
# on every run so the coverage number is visible rather than assumed.
#
# The same regex-over-Dart unease applies, and gets the same answer as above:
# an empty parse is a failure, never an empty list. Two ways this reader can
# stop matching — the map is renamed, or the entry shape changes — and both
# land on `retiredCaptures` returning `{}`, which the caller reports loudly.
def _dart_string(text):
    """Every quoted literal in a Dart expression, unescaped and joined.

    Values in `retiredCaptures` are adjacent-literal concatenations spread
    over several lines, and the file uses **both** quote styles for keys and
    values, so both are matched. Escapes are undone, so `\\'` reads back as an
    apostrophe rather than ending a literal early.
    """
    parts = []
    for m in re.finditer(r"'((?:\\.|[^'\\])*)'|\"((?:\\.|[^\"\\])*)\"",
                         text, re.S):
        raw = m.group(1) if m.group(1) is not None else m.group(2)
        parts.append(re.sub(r'\\(.)', r'\1', raw))
    return ' '.join(''.join(parts).split())


def retired_captures():
    """`retiredCaptures` from the app, as {basename: why it was retired}."""
    src = open(CAPTURE_INVENTORY, encoding='utf-8').read()
    body = re.search(
        r'const Map<String, String> retiredCaptures = \{(.*?)\n\};',
        src, re.S)
    if not body:
        return {}
    text = body.group(1)
    starts = [m.start() for m in re.finditer(r"""^  ['"]""", text, re.M)]
    found = {}
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        chunk = text[start:end]
        key = re.match(r"""^  (['"])([^'"]+)\1:""", chunk)
        if not key:
            continue
        found[key.group(2)] = _dart_string(chunk[key.end():])
    return found


# Set when either capture guard fires, so the run can say once at the end that
# this red was chosen. See CAPTURE_RED_NOTE.
capture_problems = []


def check_stale_captures(used):
    stale = known_stale_captures()
    if stale is None:
        problems.append(
            'the knownStaleCaptures declaration was not found in '
            'help_capture_inventory.dart — the reader in check.py has broken, '
            'and an empty result here would pass everything')
        return
    if not stale:
        print('  the app declares no known-stale captures — the map is '
              'present and empty, which is the drained state, not a failure')
        return
    print(f'  read {len(stale)} known-stale capture(s) from the app inventory')
    for png in used:
        base = os.path.splitext(png)[0]
        if base in stale:
            capture_problems.append(png)
            problems.append(
                f'{png} is shipped by the site and is in the app\'s '
                f'knownStaleCaptures — it photographs a screen that no longer '
                f'looks like that, and the recapture belongs to '
                f'{stale[base]}. Drop the picture or wait for that task; do '
                f'not caption around it')


def check_retired_captures(used):
    retired = retired_captures()
    if not retired:
        problems.append(
            'the retired-capture list parsed to no entries — '
            'retiredCaptures in help_capture_inventory.dart has moved out '
            'from under the reader in check.py, and an empty list here '
            'passes everything')
        return
    print(f'  read {len(retired)} retired capture(s) from the app inventory')
    for png in used:
        base = os.path.splitext(png)[0]
        if base in retired:
            capture_problems.append(png)
            # The app's reasons run to a paragraph each. One line of it here,
            # and the file named for the rest: a failure nobody can read to the
            # end is a failure nobody reads.
            why = retired[base]
            if len(why) > 150:
                why = why[:150].rsplit(' ', 1)[0] + '...'
            problems.append(
                f'{png} is shipped by the site and is in the app\'s '
                f'retiredCaptures — the screen it photographs was deleted, so '
                f'this is not a picture that has drifted out of date, it is a '
                f'picture of something that is not in the app at all. The '
                f'app\'s reason: "{why}" (in full in '
                f'help_capture_inventory.dart). A recapture cannot fix this '
                f'one — there is nothing left to photograph — so clearing it '
                f'means a different picture or none, which is the operator\'s '
                f'call. See README.md, "Known red, and who clears it"')


def check_app_captures():
    """Both capture guards, over one sibling checkout and one image list.

    PP440 split this in two: `knownStaleCaptures` and `retiredCaptures` are
    different claims about a picture and deserve different sentences, but they
    share a precondition and a subject, and duplicating the missing-sibling
    branch would report the same absent repo twice.
    """
    if not os.path.isdir(APP):
        missing_sibling(
            'app', 'the captures the app has declared stale or retired')
        return
    if not os.path.exists(CAPTURE_INVENTORY):
        problems.append('no capture inventory at ' + CAPTURE_INVENTORY)
        return
    used = sorted(images_used_by_site())
    check_stale_captures(used)
    check_retired_captures(used)


# ── PP440 — why this build is red, printed where the red is read ─────────
#
# The capture failures are a standing red that nobody is going to clear soon,
# and the operator named the risk in the act of accepting it: a build that is
# always red invites someone to "fix" it by softening the guard. The CI log is
# what a person actually reads first, so the log says whose decision it was and
# what does and does not clear it. README.md carries the same thing at length.
#
# Written in plain ASCII, deliberately. Every other printed string in this file
# is cp1252-safe; the box-drawing rules used in the comments above are not, and
# a Windows console raises UnicodeEncodeError on them, which would turn "the
# build is red for a reason" into a crash on the machine this site is edited
# from. The comment rules are never printed. This is.
CAPTURE_RED_NOTE = """
  ---- The capture failures above are a decision, not a regression ----

  Decided by the operator on 2026-09-01. Asked whether to drop the pictures or
  to accept a red build, they chose:

      "Accept the red build until EE192. The pictures stay up. The site stays
       un-deployable until the captures are re-shot."

  Why it could not be cleared by fixing the pictures: operator ruling CC130
  (2026-08-29) deferred all recapture indefinitely, so nothing here could
  re-shoot them, and dropping them was put to the operator and declined.

  THE CAPTURE RUN HAPPENED. On 2026-09-02 the app's TT150 retook all 29
  shipped captures on Clover and knownStaleCaptures drained, so eleven of the
  twelve failures this note used to cover no longer occur, and WW120 re-synced
  the site's copies. If you are reading this note at all, what is left is the
  twelfth.

  It is not a re-shoot: see the retiredCaptures line above, whose screen no
  longer exists. That one needs an operator decision on what picture replaces
  it, and no capture run can make it for them.

  What does NOT clear it: softening, skipping, allow-listing or grace-
  periodding this check. That reverses a decision the operator made on purpose
  and hides it from the next person. README.md, "Known red, and who clears
  it", is the long version.
"""


if '--self-test' in sys.argv:
    # WW100 — the three states the reader must tell apart, exercised on
    # fixtures rather than asserted in a comment. The middle one is today's
    # real file: TT150 drained the map and left the declaration standing.
    ABSENT = 'const Map<String, RetiredCapture> retiredCaptures = {\n};\n'
    EMPTY = ('const Map<String, StaleCapture> knownStaleCaptures = {\n'
             '  // Empty, and that is the point.\n};\n')
    ONE = ("const Map<String, StaleCapture> knownStaleCaptures = {\n"
           "  '10-home': StaleCapture(\n"
           "    reason: 'x',\n"
           "    regeneratedBy: 'WW999',\n"
           "  ),\n};\n")
    cases = [
        ('declaration absent  -> None (reader broken)',
         known_stale_captures(ABSENT), None),
        ('present and empty   -> {} (drained, not a failure)',
         known_stale_captures(EMPTY), {}),
        ('present with entries-> parsed',
         known_stale_captures(ONE), {'10-home': 'WW999'}),
    ]
    bad = 0
    for label, got, want in cases:
        ok = got == want and type(got) is type(want)
        print(f'  {"ok  " if ok else "FAIL"} {label}: {got!r}')
        bad += 0 if ok else 1
    # The distinction only matters if the two empties are distinguishable.
    if known_stale_captures(ABSENT) is known_stale_captures(EMPTY):
        print('  FAIL absent and empty are still the same value')
        bad += 1
    sys.exit(1 if bad else 0)


pages = html_pages()
for page in pages:
    html = open(page, encoding='utf-8').read()
    check(page, html)
    check_story(page, html)
    check_prose(page, html)

check_manifest()
check_app_captures()
check_chrome()

print(f'checked {len(pages)} page(s)')
if problems:
    for p in problems:
        print('  FAIL:', p)
    if capture_problems:
        print(CAPTURE_RED_NOTE)
    sys.exit(1)
print('  all checks passed')
