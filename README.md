# Your Health — website

Static marketing and documentation site. No build step: the HTML is the
artefact, and GitHub Pages serves this directory as-is.

## Structure

| Path | What it is |
|---|---|
| `index.html` | Landing page |
| `features.html` | What ships today |
| `privacy.html` | The public privacy account — see the warning below |
| `help.html` | Help and support, including what cannot be recovered |
| `about.html` | Why the project exists |
| `assets/css/tokens.css` | The site palette — its own, see Design below |
| `assets/css/base.css` | Elements and components |
| `assets/img/` | Screenshots, copied from `design-docs/assets/` |
| `scripts/check.py` | Pre-publish checks (`python scripts/check.py`) |
| `scripts/absolutes.py` | Sentences these pages may not publish (KK127) |
| `scripts/contrast.py` | WCAG contrast, computed from `tokens.css` |
| `scripts/build-changes.py` | Renders `changes.html` from `app/CHANGELOG.md` |
| `scripts/chrome.py` | Rewrites the shared head, nav and footer |
| `scripts/reflow.html` | 360px reflow, by hand, five pages (see below) |

## Before publishing

```bash
python scripts/check.py       # links, alt text, hosts, structure, prose
python scripts/absolutes.py   # sentences these pages may not publish
python scripts/contrast.py    # WCAG contrast, from tokens.css
```

All three run in CI (`.github/workflows/deploy.yml`) and all three fail the
build. Two more are run by hand and are **not** gates, which
`accessibility.html` and `changes.html` now say plainly rather than implying
otherwise:

- `scripts/reflow.html` — needs a real browser and
  `--allow-file-access-from-files`, and covers five of the nineteen pages.
- `python scripts/build-changes.py --check` — needs the `app` repository
  checked out beside this one, which CI does not have. It skips rather than
  failing there. Run it, and `python scripts/build-changes.py` to regenerate,
  whenever `app/CHANGELOG.md` gains a release.

`privacy.html` publishes the W110 wording as a public legal statement. The
2026-08-23 sign-off no longer covers it: KK127 re-derived four of its claims
from the code on 2026-08-29, found them false, and corrected them, so the
page needs re-signing before it goes live. The reasons are in the comment at
the top of the file. If you change a privacy claim there, change
`design-docs/01-privacy-and-data.md` first and get the wording re-signed —
the page is downstream of that document, not a place to draft in.

## Design

Light mode only, by decision — there is no `prefers-color-scheme` block.

**The palette is the site's own, and nothing in the app governs it.** This
used to say the values in `tokens.css` were copied verbatim from
`_founderLight` in `app/lib/core/theme/app_theme.dart`, and that whichever
way the two disagreed, the app was right. Both halves are now false.
`_founderLight` does not exist; the JJ cull rebuilt the roster and
`AppThemeStyle.founders` is the `Acid` template (`_kAcid`), which is a dark
palette on a near-black ground with an acid-yellow accent. Following the old
rule would repaint this site in it.

So there is no upstream to follow. The warm sand and emerald here are web
values, authored for this site, and `scripts/contrast.py` reads them straight
out of `tokens.css` and fails the build if a pair drops below AA. That check
is what holds them, not a pointer at a symbol.

Type is Newsreader (display) and Hanken Grotesk (body), the pairing the app
ships, loaded from Google Fonts with a real fallback stack.

## Screenshots

Captured unattended from the emulator. Regenerate with the harness in `app/`:

```bash
flutter drive --driver=test_driver/integration_test.dart \
  --target=integration_test/screenshots_test.dart \
  --dart-define-from-file=dev_config.json -d <device>
```

then copy `design-docs/assets/*.png` into `assets/img/`.

Two traps. `flutter drive` poisons the next release build and `flutter clean`
does not fix it — delete
`app/android/app/src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java`,
which is gitignored and regenerated. And the current set is stale: the
captures of Home, the record picker, Trends, the appearance screen and the
settings menu were all taken before those screens were rebuilt or deleted, so
KK127 removed them from the pages rather than re-caption pictures of screens
nobody can open. They come back with the next capture run.
