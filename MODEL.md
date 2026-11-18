# The model: GTA VI's launch-day Twitch viewers, hour by hour

## What is being forecast

The contest asks for five quantiles (0.05, 0.25, 0.5, 0.75, 0.95) of the
concurrent viewers of Twitch's "Grand Theft Auto VI" category (game id
1867279146) for each hour 2..24 of release day, 2026-11-19 (UTC), given only
what is known at the end of hour 1: hour 1's printed count, the category's
recorded history before it, and a panel of comparable past launches with
their own hourly curves. Scoring is the mean pinball loss on the log scale,
so what matters is the *shape* of the day relative to hour 1 and an honest
spread — a 20% miss costs the same at 10k viewers as at 1M.

## The launch being forecast

Facts established from Rockstar's published schedule and launch-week
reporting (checked 2026-11-18):

- **Release**: Thursday 2026-11-19, PlayStation 5 and Xbox Series X|S only.
  No PC version at launch, single-player.
- **No early access**: no edition (Standard, Ultimate, code-in-box) plays
  before the unlock; Rockstar skipped the usual 72-hour paid head start.
  Preload opened 2026-11-10.
- **Rolling midnight-local unlock**: New Zealand first, 2026-11-18T11:00Z;
  central Europe 2026-11-18T23:00Z; the UK at 00:00Z; the US as one
  storefront region at Eastern midnight, 05:00Z (Xbox Cloud Gaming 06:00Z);
  the US west coast's local midnight would be 08:00Z.
- So by the end of hour 1 (01:00Z) the game is live across NZ, Asia and
  Europe and in the UK; the Americas wave lands in hours 5–9; the daily
  peak is expected in the UTC evening, when US afternoon/evening overlaps
  the European evening (in the practice panel the median curve peaks in
  hours 19–22).
- **Demand signals**: Trailer 1 drew 90.4M YouTube views in 24 hours
  (Guinness record for a game reveal; ~304M cumulative by late October
  2026); Trailer 2 drew 475M views across platforms in 24 hours, the
  biggest video launch of its time; the game is the most pre-ordered title
  in PlayStation Store history. The category itself already printed a
  1.42M hourly average during the 2026-08-27 extended-look premiere (the
  panel's own-history comparable). This is a top-of-the-range launch, in
  the Elden Ring / Cyberpunk class — which is exactly what the model's
  scale-similarity weighting keys on once hour 1 prints.

## Reference points (SullyGnome hourly category averages, via the case panel)

| launch | unlock pattern | hour 1 | day peak (hourly avg) |
|---|---|---|---|
| ELDEN RING (2022) | consoles midnight local rolling + PC global | 875,155 | 875,155 |
| Cyberpunk 2077 (2020) | PC simultaneous 00:00Z + consoles local | 851,999 | 1,069,278 |
| Diablo IV (2023) | early access 4 days prior | 533,455 | 673,808 (902k in early access) |
| Hogwarts Legacy (2023) | consoles local; deluxe early access | 387,358 | 504,995 (1.21M in early access) |
| The Last of Us Part II (2020) | Sony midnight local (expected) | 365,019 | 488,329 |
| God of War Ragnarök (2022, practice) | midnight local rolling | 269,517 | — |
| Marvel's Spider-Man 2 (2023, practice) | midnight local rolling | 119,087 | — |
| Red Dead Redemption 2 (2018, practice) | midnight local rolling | 116,550 | — |
| Marvel's Wolverine (2026, practice) | midnight local rolling | 23,357 | — |

The pattern in the panel: a launch's hour 1 says a lot about its shape.
Rolling console launches start strong (much of the world is already in)
and roughly double into the UTC evening. Simultaneous-global launches
start near zero at 00:00 UTC and explode when the unlock lands.
Early-access titles start *past* their peak and sag. One distribution for
all three shapes is a bad forecast; the model separates them.

## The model

For every comparable launch c with a positive hour 1, form the log-ratio
curve L_c(h) = ln(viewers_c(h) / viewers_c(1)), h = 2..24. For the target's
hour-1 print p, hour h's quantiles are

    q_tau(h) = p * exp( m(h) + 0.9 * (Q_tau(h) - m(h)) )

where Q_tau(h) is the weighted empirical tau-quantile of the donors'
L_c(h) and m(h) its weighted median. Donor weights:

    w_c = CLASS_W[class(c)] * exp( -|ln(v1_c / p)| / 0.7 )

with the class read from the comparable's own unlock note —
rolling-midnight 1.0, unverified 0.45, early-access-contaminated 0.15,
simultaneous-global 0.12. The target category's own pre-release history
(labelled "Not a launch") is never a donor. If a case carried no usable
donor, the program falls back to the house persistence curve; every output
row is validated against the contest's format before it is written.

## Validation (leave-one-out over the practice panel)

Each of the 37 game launches in the panel was forecast in turn from the
other 36 plus its own hour 1, and scored with the contest's exact pinball
loss over hours 2..24. "Rolling" = the 11 launches whose unlock class is
rolling-midnight (GTA VI's class); "big" = the 16 whose hour 1 drew at
least 100k viewers.

| model | all 37 | rolling | big |
|---|---|---|---|
| house persistence baseline | 0.930 | — | — |
| empirical quantiles, all donors equal | 0.714 | 0.363 | — |
| + unlock-class weights | 0.717 | 0.339 | — |
| **this model (+ scale weighting, alpha 0.9)** | 0.446 | **0.260** | **0.237** |

(The house baseline's 0.930 here is on the comparable panel, which
includes simultaneous launches persistence cannot describe; on the four
practice cases — all rolling console launches — the rules quote it at
about 0.387. The like-for-like rolling comparison is 0.363 → 0.260.)

Tested and rejected on the same cross-validation: capping any single
donor's weight, a minimum hour-1 floor for donors, widening the spread
when the effective donor count is low (it averages ~10), weighting by
pre-launch ramp or by hour-1 viewers-per-channel, and spread factors
0.85–1.25 around the chosen 0.9 (a plateau, not a spike).

What the fitted model says about the practice cases (median peak, hours
19–22): Wolverine 23,357 → ~79k (3.4x), RDR2 116,550 → ~262k (2.2x),
Spider-Man 2 119,087 → ~268k (2.2x), God of War Ragnarök 269,517 → ~433k
(1.6x) — smaller first hours grow more, the biggest launches start
closest to their peak. For GTA VI the same rule applies mechanically to
whatever hour 1 prints at 01:00Z on 2026-11-19.

## Sources

- Contest kit (RULES.txt, input/NOTICE.txt): counting method, unlock
  times, practice/comparable data (SullyGnome.com hourly Twitch category
  averages, read 2026-11-17), baseline definition and practice score.
- Rockstar Games support / PlayStation Blog / Xbox Wire launch schedule,
  via launch-week reporting (northjersey.com, clarin.com, gamingroute.com,
  patchcrest.com, pro-gamer.gg, November 2026): release date, platforms,
  rolling midnight unlock, no early access, preload from Nov 10.
- Trailer figures: Guinness World Records (Trailer 1, 90,421,491 YouTube
  views in 24h); Rockstar via The Hollywood Reporter (Trailer 2, 475M
  cross-platform views in 24h); Rockstar Games' YouTube counters as read
  2026-10-29 (Trailer 1 ≈ 300M cumulative).
