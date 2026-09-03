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
    ('ink', 'ground', 'body text on the page ground', AA_BODY),
    ('ink', 'paper', 'body text on a card', AA_BODY),
    ('ink', 'tint', 'body text on a callout fill', AA_BODY),
    ('ink-soft', 'ground', 'secondary text on the page ground', AA_BODY),
    ('ink-soft', 'paper', 'secondary text on a card', AA_BODY),
    ('ink-soft', 'tint', 'secondary text on a callout fill', AA_BODY),

    # WW200 — one green, at the body threshold everywhere. The old palette
    # carried two: --emerald was 4.19:1 on the old ground, under AA, so
    # --emerald-text existed as a 5%-darker variant for links and nothing
    # else. --sage is 6.89:1 on --ground, so the patch token is deleted and
    # the brand colour is legal at body size on every surface it lands on.
    ('sage', 'ground', 'links and icons on the page ground', AA_BODY),
    ('sage', 'paper', 'links and icons on a card', AA_BODY),
    ('sage', 'tint', 'links and icons on a callout fill', AA_BODY),
    ('pine', 'ground', 'the primary button and headings on the ground', AA_BODY),
    ('on-pine', 'pine', 'text on the inverted band', AA_BODY),

    # Also promoted to the body threshold: --bronze was 3.55:1 and large-only,
    # which meant a rule about where it could be used that nobody could see in
    # the token. At 5.04:1 it is simply legal.
    ('bronze', 'ground', 'counter-accent marks on the page ground', AA_BODY),
    ('bronze', 'paper', 'counter-accent marks on a card', AA_BODY),

    # WW210 — the pair the note at the foot of this file predicted. WCAG
    # 1.4.11 is 3:1 for a boundary required to perceive a component, and
    # --edge is exactly that and nothing else.
    ('edge', 'ground', 'the only boundary of a control, on the ground', AA_LARGE),
    ('edge', 'paper', 'the only boundary of a control, on a card', AA_LARGE),
]

# Deliberately NOT checked, with the reason recorded so it is a decision rather
# than an omission:
#
#   --line on --ground is 1.25:1. The first version of this script required
#   3:1 and failed it. That was the script being wrong, not the design. WCAG
#   1.4.11 applies to boundaries REQUIRED to perceive a component; a card here
#   is also distinguished by its background (--paper against --ground) and a
#   shadow, so the hairline is decorative reinforcement. Raising it to 3:1
#   would put a hard grey rule around every card and change the design to
#   satisfy a rule that does not apply.
#
#   The old version of this note ended: "if a control is ever added whose ONLY
#   boundary is --line, this stops being true and the pair belongs back in the
#   list above." WW210 found that control had already been added — and had been
#   sitting on the landing hero for some time. `.btn--ghost` was
#   `background: transparent` with `border-color: var(--line)`: no fill, no
#   shadow, a 1.25:1 hairline and nothing else.
#
#   The exemption was therefore live and false at the same time. It is true
#   again only because such controls now take --edge, which IS checked, at 3:1.
#   The condition in this note has not been relaxed; it has been met. If a
#   control appears bounded by --line alone again, the same sentence applies
#   and the same answer follows: give it --edge, do not widen the exemption.

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
