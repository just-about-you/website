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
python scripts/check.py                  # links, alt text, hosts, structure,
                                         # prose, the capture manifest, stale
                                         # and retired captures, clinical
                                         # claims by shape
python scripts/absolutes.py              # sentences these pages may not publish
python scripts/contrast.py               # WCAG contrast, from tokens.css
python scripts/build-changes.py --check  # changes.html agrees with the changelog
```

**All four run in CI** (`.github/workflows/deploy.yml`) and all four fail the
build. PP425 added the fourth: it had existed since BB143, it worked, and
nothing ever ran it, so `changes.html` fell seven releases behind the app in
silence. Regenerate with `python scripts/build-changes.py` whenever
`app/CHANGELOG.md` gains a release.

One check is still run by hand and is **not** a gate, which
`accessibility.html` says plainly rather than implying otherwise:
`scripts/reflow.html` needs a real browser and
`--allow-file-access-from-files`, and covers five of the nineteen pages.

## Cross-repo guards — PP425

Three of the checks above read a repository that is not this one:
`app/CHANGELOG.md`, `app/lib/features/help/help_capture_inventory.dart` and
`design-docs/assets/MANIFEST.md`. Three decisions hold them up, recorded here
because each of them is a thing someone will later want to undo.

**A missing sibling repo fails in CI; it does not skip.** This is the one that
mattered most. Both guards used to print `SKIP` and exit 0 when the sibling was
absent, and CI cloned this repo alone — so the only cross-repo check the site
had printed SKIP on every run since it was written, and every green gate since
has been read as evidence the manifest agreed. It was evidence of nothing. The
gate now checks `app` and `design-docs` out beside this repo (see the workflow;
the site itself moves to `website/` in the workspace so the three sit as
siblings, which is the layout the scripts already assume), and the scripts fail
rather than skip whenever `CI` is set. `ALLOW_MISSING_SIBLING_REPOS=1` is the
only way back to a skip, and it is named so that using it is visible in a diff.
A working copy without siblings still skips, as before.

If `app` or `design-docs` is private, the cross-repo checkouts fail with a 404,
because `github.token` reaches a sibling only by way of that sibling being
publicly readable. The fix is a fine-grained token with read access to both,
stored as the `SIBLING_REPO_TOKEN` secret; the workflow already prefers it
where it exists. That failure is loud, which is the point — the version that
must never come back is the quiet one.

**The site may not ship a capture the app has already declared wrong, and the
marker for that lives in `app/`, not in `design-docs/`.** The obvious move was
a machine-readable `stale:` line in `design-docs/assets/MANIFEST.md`, beside
the prose that already says `30-people.png` and `50-checkin.png` "mislead as a
set". It is refused on two grounds. First, MANIFEST.md is generated and
rewritten whole: the capture driver
(`app/test_driver/integration_test.dart:88-93`) rebuilds the entire file from a
template and the folder listing on every run, and the file says so in its first
line, so a marker written there would survive exactly until the next
`flutter drive`. Second, the inventory already exists and is already enforced —
KK150 put it in `help_capture_inventory.dart`, where
`app/test/help_capture_freshness_test.dart` holds it in both directions, and
MANIFEST.md's own prose records that the list moved there for that reason. So
`check.py` reads the app's list, and **`design-docs/` needs no change at all.**

What that cannot see, stated rather than pretended away: the app's inventory is
per-screen, and `30-people` / `50-checkin` are stale for a reason that is not on
their screen — they were shot when People and Check-in were bottom-bar
destinations, and what changed is `app_shell.dart`, not `people_screen.dart`.
Both therefore sit in the fingerprint half of the inventory rather than the
stale half, and this guard passes them. **Closing that is a change in `app/`:**
either add `lib/shared/widgets/app_shell.dart` to those two source sets — which
trips their fingerprints at once, because the shell did change — or list them in
`knownStaleCaptures`. Either way it lands in `app/`, and the site picks it up on
the next run with no change here.

**A clinical claim is caught by shape, not by spelling.** `check.py` grepped
four fixed substrings, which would not have caught *"your blood pressure is
normal"* — the sentence this product is actually at risk of publishing, and one
the app refuses at construction (`MetricTileCard` rejects `normal`, `high`,
`low`, `stage`, `overweight`, `obese` as status text) and that `about.html`
publishes to the reader as a promise. A longer substring list cannot do
it: `normal` appears legitimately on this site inside the sentence listing the
forbidden words. So the shape is matched instead — the reader's own reading, a
linking verb and a verdict, within one sentence — and the constraint on it is
that it must stay silent on the population-reference wording `about.html` and
`terms.html` carry ("coloured against published general guidelines … nothing in
it states a verdict"). That is why it demands `your <reading>` rather than the
reading alone: a guideline is about everybody, a verdict is about you.

**A retired capture is a different failure from a stale one, and until PP440
only one of the two was read.** `help_capture_inventory.dart` carries two maps.
`knownStaleCaptures` says *this photograph no longer looks like the screen*;
`retiredCaptures` says the stronger thing — *the screen is gone*, no step in
the app renders the picture, and the asset must not be in the app's bundle at
all. `check.py` read only the first, so the site could ship a photograph of a
surface that does not exist and the gate would call it green. It did:
`62-medications.webp` is on the landing page twice (`index.html:89` and
`:430`) and MM260 deleted that screen outright. That green was the expensive
part — a guard that catches stale-but-real captures while missing deleted ones
reads as coverage of both, so nobody looks. Both maps are read now, and the
run prints both counts (23 stale, 6 retired) so the coverage is visible rather
than assumed.

Both readers are regexes over Dart source, which is worth being uneasy about,
so both treat **an empty parse as a failure and never as an empty list**. Two
ways a reader can stop matching — the map is renamed, or the entry shape
changes — and both land on `parsed to no entries`, which fails the build with
that sentence. A reader that quietly stops matching is a guard that quietly
stops guarding, and that is the whole complaint these two guards answer.

### Known red, and who clears it

The gate is red, deliberately, on two counts. **Neither is cleared by weakening
a check**, and the failing run says so itself: `check.py` prints the decision
below under the capture failures, because the CI log is what a person actually
reads first.

- **`changes.html` is seven releases behind.** The changelog carries 2.13.0 to
  2.19.0 and the page stops at 2.12.0. Regenerating it now would put it back to
  STALE the moment the next release entry lands, so it is sequenced to the
  release task: run `python scripts/build-changes.py` at ship time.
- **Twelve captures the app has declared wrong, and the site ships all of
  them.** Eleven are in `knownStaleCaptures` (`12-home-entry-sheet`,
  `30-people`, `40-tasks`, `41-tasks-add`, `42-tasks-repeat`,
  `43-tasks-share`, `50-checkin`, `70-care`, `71-medication-sharing`,
  `72-reading-request`, `83-medications-full`) and the twelfth,
  `62-medications`, is in `retiredCaptures`. Two of them are on the landing
  page. Since `deploy` needs `check`, this red means the site does not
  publish at all.

**The red is an operator decision, taken 2026-09-01.** The operator was asked
whether to drop the pictures or to accept a red build, and chose:

> Accept the red build until EE192. The pictures stay up. The site stays
> un-deployable until the captures are re-shot.

Recorded here at that length because the operator named the risk in the act of
taking it: *a standing red build invites someone to "fix" it by softening the
guard.* So, plainly —

- **Why it cannot be fixed here.** Operator ruling CC130 (2026-08-29) defers
  all recapture indefinitely, so nothing in this repo can re-shoot them. The
  other exit — dropping the pictures, which is what KK127 did with five other
  captures — was put to the operator and **declined**.
- **What clears it.** EE192, the capture run. The entries then leave
  `knownStaleCaptures` in `app/` and this repo goes green with no change here.
- **What does not clear it.** Softening, skipping, allow-listing or
  grace-periodding `check.py`. PP440 made the build *redder* by adding the
  retired-capture guard, on the reasoning that the decision was to accept a red
  build and not to cap how red it is. Undoing either guard reverses a decision
  that was made on purpose and hides it from the next person.
- **One of the twelve is not a re-shoot.** `62-medications` photographs a
  deleted screen, so EE192 has nothing to point a camera at. Clearing that one
  means a different picture or none — a content decision, and the operator's,
  not one a capture run or a guard edit can make. Flagged here rather than
  taken.

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
