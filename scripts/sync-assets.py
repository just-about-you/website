#!/usr/bin/env python3
"""Y130 / BB102 — one screenshot set, two outputs, and the site gets the small one.

`design-docs/assets/` is the single source: the capture harness in `app/`
writes there and rebuilds MANIFEST.md from the folder. This produces the site's
copy, and is the only supported way to do it — a hand-copied image is exactly
the drift `check.py`'s manifest rule exists to catch.

**BB102 — this used to copy the PNGs verbatim.** That meant 52 files at 9.7 MB,
averaging 191 KB each, on a site whose audience skews toward older phones and
slower connections. The app had already solved the same problem in
`app/scripts/build_help_assets.py`: downscale, re-encode as WebP, and the same
pictures come out at about 35 KB — five and a half times smaller. There was no
argument for the site carrying the heavy set except that nobody had looked.

    python scripts/sync-assets.py           # build, report what changed
    python scripts/sync-assets.py --check   # fail if out of date, write nothing

Width is chosen so the site never upscales. WW230 re-derived it, because the
old sentence here — "the widest a screenshot is drawn is the `.device` frame at
~420 CSS px, so 900 px covers 2x displays with room over" — was wrong about the
frame and therefore wrong about the multiple.

Measured: `.device` is `min(20rem, 74vw)`, so **320 CSS px**, and the image
inside it sits within `0.5rem` of padding on each side, so it renders at **304
px**. `.feature-media .shot` is `min(15rem, 60vw)` = 240 px, narrower. 304 px
is the widest any capture is drawn.

So 900 px is not 2x of 420. It is **just under 3x of 304**, which is the density
of ordinary current Android hardware (2.75x-3.5x) rather than headroom over 2x.
The number is unchanged and correct; only the reason was wrong, which is worth
saying plainly — a constant justified by a measurement nobody re-took is a
constant nobody can move safely. If the frame changes, this follows it: target
= widest rendered width x 3, rounded up.
"""
import io
import os
import sys

try:
    from PIL import Image
except ImportError:  # pragma: no cover - developer setup
    sys.exit('Pillow is required: python -m pip install Pillow')

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
SRC = os.path.normpath(os.path.join(SITE, '..', 'design-docs', 'assets'))
DST = os.path.join(SITE, 'assets', 'img')

TARGET_WIDTH = 900
QUALITY = 82

check_only = '--check' in sys.argv

if not os.path.isdir(SRC):
    print('source not found: ' + SRC)
    print('Capture the set first — see website/README.md.')
    sys.exit(1)

os.makedirs(DST, exist_ok=True)

source = sorted(f for f in os.listdir(SRC) if f.endswith('.png'))
wanted = {os.path.splitext(f)[0] + '.webp' for f in source}
present = {f for f in os.listdir(DST) if f.endswith('.webp')}

# Anything still shipped as PNG is left over from before BB102 and is dead
# weight the moment its WebP exists.
stale_png = sorted(f for f in os.listdir(DST) if f.endswith('.png'))

built, changed, removed = [], [], sorted(present - wanted) + stale_png


def build(name):
    src_path = os.path.join(SRC, name)
    out_path = os.path.join(DST, os.path.splitext(name)[0] + '.webp')
    with Image.open(src_path) as im:
        im = im.convert('RGB')
        if im.width > TARGET_WIDTH:
            height = round(im.height * TARGET_WIDTH / im.width)
            im = im.resize((TARGET_WIDTH, height), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, 'WEBP', quality=QUALITY, method=6)
    data = buf.getvalue()
    existing = None
    if os.path.exists(out_path):
        with open(out_path, 'rb') as f:
            existing = f.read()
    if existing == data:
        return None
    if not check_only:
        with open(out_path, 'wb') as f:
            f.write(data)
    return len(data)


for name in source:
    size = build(name)
    if size is None:
        continue
    (built if os.path.splitext(name)[0] + '.webp' not in present else changed).append(
        (name, size))

if not check_only:
    for name in removed:
        os.remove(os.path.join(DST, name))

if check_only:
    if built or changed or removed:
        for name, _ in built:
            print('  MISSING:', name)
        for name, _ in changed:
            print('  STALE:  ', name)
        for name in removed:
            print('  ORPHAN: ', name)
        print('\nout of date. Run: python scripts/sync-assets.py')
        sys.exit(1)
    total = sum(os.path.getsize(os.path.join(DST, f)) for f in present)
    print(f'in sync — {len(present)} images, {total / 1048576:.2f} MB')
    sys.exit(0)

for name, size in built:
    print(f'  new      {name} -> {size / 1024:.0f} KB')
for name, size in changed:
    print(f'  changed  {name} -> {size / 1024:.0f} KB')
for name in removed:
    print(f'  removed  {name}')

final = sorted(f for f in os.listdir(DST) if f.endswith('.webp'))
total = sum(os.path.getsize(os.path.join(DST, f)) for f in final)
print(f'\n{len(final)} images, {total / 1048576:.2f} MB total '
      f'(mean {total / max(len(final), 1) / 1024:.0f} KB)')
