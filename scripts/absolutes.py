"""KK127 — the absolutes this site is not allowed to publish.

**Why this exists.** The app has been guarded against these sentences since
M123 shipped. The website was not, and that gap is not theoretical: the exact
string `app/test/what_leaves_phone_test.dart` exists to keep out of shipped
copy was live on `privacy.html`, in a table row, on a page that had been
signed off. The app guard could never have caught it, because it reads Dart
strings and this site is HTML in a different repository.

So this is the same guard, on this side of the fence. A phrase banned in the
app is banned here, quoting the app test that bans it. Where the KK127 audit
found the same *shape* of claim in wording the app happens not to use, that
phrase is listed too, in its own section, with what makes it false.

**The shape being banned.** Every entry is an unqualified absolute about what
crosses the network or what a carer can see. The rule the project works to is
*state the default plus the named exception, never an absolute* — the shipped
in-app wording at `app/lib/l10n/arb/app_en.arb` (`privacyLeavesCaregiverBody`,
`privacyLeavesNeverBody`) is the model. Two things can carry more than a yes
or no, and both need the person to act first: a single reading approved when a
carer asks, and any medication tagged for a carer. A sentence that denies
either of them is false, however well it reads.

**A second kind of false, added by PP445.** A sentence can also be false
because the thing it describes no longer exists. `privacy.html` published a
"you read an article" row for eleven days after PP430 deleted the app's feed
client and PP435 deleted the routes behind it, and no guard on either side of
the fence could see it: the app test reads Dart strings, and this script only
knew about absolutes. Copy describing a removed feature is not merely stale —
it tells someone their data does something it can no longer do, which is the
same harm the absolutes cause by the opposite route. So retired features get
their own list below, on the same terms: a named phrase, and what makes it
false.

**What this is not.** It is not a style checker and it does not ban strong
claims. "There is no column that could hold one" is true and stays. It bans
named sentences that are false, each with its evidence.

    python scripts/absolutes.py

Exits 1 with the page, the phrase and the surrounding words for every hit.
Stdlib-only, like every other script here, so CI needs no install step.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Ported from the app's own guards ────────────────────────────────────────
#
# Each entry is (phrase, the test that bans it and why). These must agree with
# the app: if one of these tests is ever relaxed, relax it here in the same
# change, and if a new one is added there, add it here.
#
# Cited by file and by what the assertion says, deliberately without a line
# number. The app repository is worked on independently of this one and those
# numbers move; a citation that rots is worse than a slightly vaguer one,
# because the next person reads a wrong line and concludes the rule is stale.
PORTED = [
    (
        'never the reading',
        'app/test/what_leaves_phone_test.dart — "the old absolute is false '
        'now that M123 has shipped". A reading does cross, encrypted, on '
        'per-instance approval.',
    ),
    (
        'they never see a number',
        'app/test/caregiver_help_accuracy_test.dart — the no-numbers claim '
        'is a default, not a guarantee.',
    ),
    (
        'never leaves your phone',
        'app/test/help_copy_guard_test.dart — "the absolute M123 '
        'falsified, in a new place".',
    ),
    (
        'nothing is sent',
        'app/test/help_copy_guard_test.dart — same list.',
    ),
    (
        'stays on this phone',
        'app/test/help_copy_guard_test.dart — same list.',
    ),
    (
        'never sends them anywhere',
        'app/test/backup_copy_test.dart and '
        'app/test/caregiver_help_accuracy_test.dart.',
    ),
]

# ── Found on this site by the KK127 audit ───────────────────────────────────
#
# The same shape, in wording the app does not happen to use. Each is here
# because it was published and false, not because it sounds strong.
SITE = [
    (
        'never leave the phone',
        'The sentence about.html retracts by name. Kept banned so it cannot '
        'come back as an assertion; about.html is allowed to quote it.',
    ),
    (
        'we never see a reading',
        'A headline absolute is not rescued by a qualifier seventy lines '
        'below it. An approved reading crosses our server encrypted — '
        'back-end/src/routes/envelope/index.ts:126-170.',
    ),
    (
        'names, contacts, or locates',
        'back-end/src/db/schema.ts:129 deviceTokens holds an FCM delivery '
        'token, whose whole purpose is contacting the person. privacy.html '
        'says so itself further down the same page.',
    ),
    (
        'names, contacts or locates',
        'Comma-free variant of the same sentence.',
    ),
    (
        'no reading of yours on our servers',
        'True of the database and not of the server: an approved reading sits '
        'in the ephemeral store between approval and pickup. Say "in our '
        'database", which is the checkable claim.',
    ),
    (
        'readings, of anyone, on our servers',
        'Same claim as a headline statistic, contradicted by a card fourteen '
        'lines below it on verify.html.',
    ),
    (
        'nothing about you on our servers',
        'Same claim again. Adherence rows are about you, and are the largest '
        'thing held.',
    ),
    (
        'one thing only',
        'data.html said this of the ephemeral store, which also carries '
        'tagged medication lists — back-end/src/routes/envelope/index.ts:11-13.',
    ),
    (
        'never to either phone',
        'A received medication list is written to the carer\'s phone as '
        'caregiver_medications.enc — '
        'app/lib/data/caregiver/caregiver_medication_cache.dart:22-29, :49.',
    ),
    (
        'rather than what it was',
        'A carer also sees an approved reading and every tagged medication by '
        'name. The default is right; stating it as the whole truth is not.',
    ),
    (
        'no route to you',
        'A device code handed out before invites existed is still accepted, '
        'deliberately — app/lib/features/people/add_person_sheet.dart:55-64.',
    ),
    (
        'nobody reaches you',
        'Same claim, on the features hub.',
    ),
]

# ── Features that are gone, and the copy that outlived them (PP445) ────────
#
# Not absolutes. Each entry describes something the app no longer does, which
# a reader has no way to discover is untrue. Delete an entry only when the
# feature comes back — not when the phrase becomes inconvenient.
RETIRED = [
    (
        'reading feed',
        'PP430 deleted the app\'s feed client and PP435 the routes and the '
        'RSA key. There is no feed and no article to ask for. What is left '
        'under that heading is two requests with different shapes: GET '
        '/content/messages, which carries no code and returns one fixed list '
        'to everyone, and GET /themes/entitlements, which carries the uuid '
        'and a bearer token — see privacyLeavesContentBody in '
        'app/lib/l10n/arb/app_en.arb.',
    ),
    (
        'you read an article',
        'The privacy-table row PP445 replaced. It claimed a request that no '
        'longer leaves the phone, on the page whose whole promise is that '
        'every request the app makes is one of the rows below it.',
    ),
]

BANNED = [(p, why, 'app') for p, why in PORTED] + \
         [(p, why, 'site') for p, why in SITE] + \
         [(p, why, 'retired') for p, why in RETIRED]

# A page may quote a banned sentence in order to retract it — that is the
# opposite of publishing it, and it is the most honest thing a page can do
# with a claim it got wrong. Listed rather than pattern-matched: an exemption
# should cost someone a line in this file and a reason.
ALLOWED = {
    ('about.html', 'never leave the phone'):
        'about.html quotes the retracted sentence in order to retract it, '
        'which is the point of that section.',
}


def normalise(html):
    """The words a reader sees, on one line.

    A phrase check against raw HTML misses every sentence that wraps across
    lines, which on this site is most of them — the site-wide call to action
    breaks "on our / servers" over two lines in all seven feature pages.
    """
    text = re.sub(r'<(script|style)\b.*?</\1>', ' ', html, flags=re.S)
    text = re.sub(r'<!--.*?-->', ' ', text, flags=re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    for entity, char in (
        ('&rsquo;', "'"), ('&lsquo;', "'"), ('&ldquo;', '"'),
        ('&rdquo;', '"'), ('&mdash;', '—'), ('&ndash;', '–'),
        ('&amp;', '&'), ('&nbsp;', ' '), ('&hellip;', '…'),
    ):
        text = text.replace(entity, char)
    text = text.replace('’', "'").replace('‘', "'")
    return re.sub(r'\s+', ' ', text).strip().lower()


def pages():
    found = glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True)
    return sorted(p for p in found if 'scripts' + os.sep not in p)


def main():
    checked = pages()
    hits = []
    for page in checked:
        name = os.path.relpath(page, ROOT).replace('\\', '/')
        text = normalise(open(page, encoding='utf-8').read())
        for phrase, why, origin in BANNED:
            start = 0
            while True:
                at = text.find(phrase, start)
                if at == -1:
                    break
                start = at + 1
                if (name, phrase) in ALLOWED:
                    continue
                context = text[max(0, at - 45):at + len(phrase) + 45]
                hits.append((name, phrase, origin, why, context))

    print(f'checked {len(checked)} page(s) against {len(BANNED)} '
          f'forbidden phrase(s)')
    if not hits:
        print('  no forbidden phrase is published')
        return 0

    for name, phrase, origin, why, context in hits:
        print(f'  FAIL: {name}: "{phrase}" [{origin}]')
        print(f'        …{context}…')
        print(f'        {why}')
    print(f'\n{len(hits)} forbidden phrase(s) published. '
          f'State the default plus the named exception instead, and do not '
          f'describe a feature that has been removed.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
