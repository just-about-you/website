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
| `assets/css/tokens.css` | The founder light palette, copied from the app |
| `assets/css/base.css` | Elements and components |
| `assets/img/` | Screenshots, copied from `design-docs/assets/` |
| `scripts/check.py` | Pre-publish checks (`python scripts/check.py`) |

## Before publishing

```bash
python scripts/check.py
```

Checks that images resolve and carry alt text, internal links are live, no
page requests an external host except Google Fonts, and each page has a lang,
a title, a description, exactly one `<h1>` and a skip link.

`privacy.html` publishes the W110 wording as a public legal statement. That
wording was signed off by the operator on 2026-08-23 and is cleared to go
live. If you change a privacy claim on that page, change
`design-docs/01-privacy-and-data.md` first and get the wording re-signed —
the page is downstream of that document, not a place to draft in.

## Design

Light mode only, by decision — there is no `prefers-color-scheme` block. The
palette is the app's invite-only "founder" theme, and the values in
`tokens.css` are copied verbatim from `_founderLight` in
`app/lib/core/theme/app_theme.dart`. If the two disagree, the app is right.

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
