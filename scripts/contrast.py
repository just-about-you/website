"""Y140 — WCAG contrast, computed from the tokens rather than eyeballed.

Reads the hex values straight out of tokens.css so it cannot drift from the
stylesheet, and checks every foreground/background pair the pages actually
use. Exact arithmetic beats squinting at a screenshot.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, 'assets', 'css', 'tokens.css')

AA_BODY = 4.5   # normal text
AA_LARGE = 3.0  # >=24px, or >=18.66px bold — our display sizes clear this


def tokens():
    text = open(CSS, encoding='utf-8').read()
    found = dict(re.findall(r'--([a-z-]+):\s*(#[0-9a-fA-F]{6});', text))
    assert found, 'no colour tokens found in tokens.css'
    return found


def srgb(channel):
    c = channel / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_colour):
    h = hex_colour.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b)


def ratio(fg, bg):
    a, b = luminance(fg), luminance(bg)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


T = tokens()

# (foreground, background, label, threshold)
PAIRS = [
    ('ink', 'sand', 'body text on the page ground', AA_BODY),
    ('ink', 'paper', 'body text on a card', AA_BODY),
    ('ink-soft', 'sand', 'secondary text on the page ground', AA_BODY),
    ('ink-soft', 'paper', 'secondary text on a card', AA_BODY),
    ('emerald-text', 'sand', 'links on the page ground', AA_BODY),
    ('emerald-text', 'paper', 'links on a card', AA_BODY),
    ('on-ink-surface', 'ink-surface', 'text on the inverted band', AA_BODY),

    # Added with the redesign. The brand emerald is 4.19:1 on --sand, under
    # AA for normal text — which is why --emerald-text exists for links. These
    # two uses are display-sized, so the large-text threshold is the right one
    # and the brand colour itself can be used:
    ('emerald', 'sand', 'accented word in the hero headline', AA_LARGE),
    ('bronze', 'sand', 'list marks in "what we do not do"', AA_LARGE),
    # Step numerals are content, not decoration — they carry the order — so
    # they are held to the body threshold even though they render large.
    ('emerald', 'paper', 'numerals on the numbered steps', AA_BODY),
]

# Deliberately NOT checked, with the reason recorded so it is a decision rather
# than an omission:
#
#   --line on --sand is 1.25:1. The first version of this script required 3:1
#   and failed it. That was the script being wrong, not the design. WCAG 1.4.11
#   applies to boundaries REQUIRED to perceive a component; a card here is also
#   distinguished by its background (--paper against --sand) and a shadow, so
#   the hairline is decorative reinforcement. Raising it to 3:1 would put a
#   hard grey rule around every card and change the design to satisfy a rule
#   that does not apply.
#
#   If a control is ever added whose ONLY boundary is --line, this stops being
#   true and the pair belongs back in the list above.

print('WCAG contrast, from tokens.css\n')
failures = []
for fg, bg, label, need in PAIRS:
    assert fg in T, 'missing token: ' + fg
    assert bg in T, 'missing token: ' + bg
    r = ratio(T[fg], T[bg])
    ok = r >= need
    print('  %-38s %s on %s  %5.2f:1  need %.1f  %s'
          % (label, T[fg], T[bg], r, need, 'PASS' if ok else 'FAIL'))
    if not ok:
        failures.append((label, fg, bg, r, need))

print()
if failures:
    print('%d pair(s) below AA:' % len(failures))
    for label, fg, bg, r, need in failures:
        print('  FAIL: %s — %s on %s is %.2f:1, needs %.1f'
              % (label, fg, bg, r, need))
    sys.exit(1)
print('  all pairs meet AA')
