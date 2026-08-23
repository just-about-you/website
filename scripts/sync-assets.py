"""Y130 — one screenshot set, two outputs.

`design-docs/assets/` is the single source: the capture harness in `app/`
writes there and rebuilds MANIFEST.md from the folder. This copies that set
into the site, and is the only supported way to do it — a hand-copied image
is exactly the drift `check.py`'s manifest rule exists to catch.

    python scripts/sync-assets.py          # copy, report what changed
    python scripts/sync-assets.py --check   # fail if out of sync, copy nothing
"""
import filecmp
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SRC = os.path.normpath(os.path.join(SITE, '..', 'design-docs', 'assets'))
DST = os.path.join(SITE, 'assets', 'img')

check_only = '--check' in sys.argv

if not os.path.isdir(SRC):
    print('source not found: ' + SRC)
    print('Capture the set first — see website/README.md.')
    sys.exit(1)

os.makedirs(DST, exist_ok=True)

source = {f for f in os.listdir(SRC) if f.endswith('.png')}
present = {f for f in os.listdir(DST) if f.endswith('.png')}

added = sorted(source - present)
removed = sorted(present - source)
changed = sorted(
    f for f in (source & present)
    if not filecmp.cmp(os.path.join(SRC, f), os.path.join(DST, f), shallow=False)
)

if not (added or removed or changed):
    print('in sync — %d image(s)' % len(source))
    sys.exit(0)

for label, items in (('new', added), ('changed', changed), ('stale', removed)):
    for f in items:
        print('  %-8s %s' % (label, f))

if check_only:
    print('\nout of sync. Run: python scripts/sync-assets.py')
    sys.exit(1)

for f in added + changed:
    shutil.copy2(os.path.join(SRC, f), os.path.join(DST, f))
# Stale images are removed, not left behind. A capture run that drops a screen
# would otherwise leave the old image in the site for a page to keep using —
# the same trap that left a blank settings screenshot in the doc set.
for f in removed:
    os.remove(os.path.join(DST, f))

print('\nsynced — %d copied, %d removed' % (len(added) + len(changed), len(removed)))
