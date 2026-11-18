"""Forecast GTA VI's launch-day Twitch viewers, hour by hour (make.fun entry).

The contest (gta6-twitch-ccu-forecast-01, harness program/v1) runs this program
once per case in a sandbox with no network. A case file carries everything the
forecast may use: hour 1's printed viewer count for the launch day (00:00-01:00
UTC), the category's history before that checkpoint, and a panel of comparable
past launches, each with its own hourly Twitch category averages from 14 days
before its release day to 3 days after it. For every hour h = 2..24 the program
writes five quantiles (levels 0.05, 0.25, 0.5, 0.75, 0.95) of that hour's
concurrent-viewer count; the score is the mean pinball loss on the log scale.

Model (see MODEL.md for the full write-up and the validation numbers):

  A launch day's shape is forecast from the shapes of past launches. For each
  comparable launch c with a complete launch day, form the log-ratio curve

      L_c(h) = ln( viewers_c(h) / viewers_c(1) ),   h = 2..24,

  i.e. each launch's day expressed relative to its own first hour, the same
  anchor the case gives us for the target (hour 1's print p). The forecast for
  hour h is p times the exponential of a weighted empirical quantile of the
  donors' L_c(h):

      q_tau(h) = p * exp( m(h) + ALPHA * (Q_tau(h) - m(h)) ),

  where m(h) is the weighted median of the donors' log-ratios at h, Q_tau(h)
  the weighted tau-quantile, and ALPHA = 0.9 a mild spread shrinkage.

  Donor weights reward the launches that resemble this one. GTA VI is a
  console-only, single-player launch that unlocks at midnight local time,
  rolling country by country (New Zealand first, 2026-11-18T11:00Z), with no
  early access. A comparable's weight is

      w_c = CLASS_W[class of c's unlock] * exp( -|ln(v1_c / p)| / BW ),

  with BW = 0.7. The unlock classes are read off the comparable's own `unlock`
  text: rolling-midnight launches weigh 1.0, unverified ones 0.45,
  early-access-contaminated ones 0.15 and simultaneous-global ones 0.12. The
  scale term keeps the pool local in size: a launch whose first hour drew a
  similar crowd to the target's behaves more like it than one ten times
  bigger or smaller, whatever its unlock style.

  The parameters were chosen by leave-one-out cross-validation over the 37
  game launches in the practice panel: each launch in turn was forecast from
  the other 36 plus its own hour 1, and scored with the contest's pinball
  loss. This model scores about 0.26 on the rolling-midnight launches (the
  house persistence baseline scores about 0.39 on the practice cases) and
  about 0.24 on the launches whose first hour drew at least 100k viewers.
  Three refinements were tested on the same cross-validation and rejected:
  capping any one donor's weight (it starves exactly the large, closest
  launches), a minimum hour-1 floor for donors (no effect), and widening
  the spread when the effective donor count is low (the pool's effective
  size is about 10, never low enough to help).

  One comparable is never a donor: the target category's own pre-release
  history, whose note says it is not a launch. Its start day is a trailer
  premiere, not a release, so its "curve" would teach the wrong shape; it
  is excluded by name in build_donors, not left to chance.

Fallbacks keep every case valid: an hour no donor covers falls back to the
nearest covered hour's distribution, and if a case carried no usable donor at
all, the program emits the house persistence curve (every hour at hour 1's
print, log-spread 0.15 * sqrt(h - 1)). The output is validated row by row
before it is written; a case that fails validation is rewritten with the
persistence curve rather than shipped malformed.

Deterministic: donors are processed in name order, all arithmetic is plain
float math on the case's own numbers, and the output bytes are a pure
function of the input file. Standard library only.

Run locally the way the grader does, with the kit's practice cases:

    mkdir -p out && MAKEFUN_INPUT_DIR=<kit>/input MAKEFUN_OUTPUT_DIR=out python3 main.py
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# The grader runs `python3 -P -s /bot/main.py`, which keeps this file's
# directory off sys.path; put it back first, as the kit's starter does, so a
# sibling module would import if one were ever shipped beside this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

# The quantile levels the contest scores, in the order each row lists them.
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
# The standard normal's quantile at each level (the persistence fallback).
Z = [-1.645, -0.674, 0, 0.674, 1.645]

# --- Model parameters (chosen by leave-one-out validation, see MODEL.md) ---
# Donor weight by unlock class, read from the comparable's `unlock` text.
CLASS_W = {"roll": 1.0, "unk": 0.45, "sim": 0.12, "ea": 0.15}
# Bandwidth of the scale-similarity term, in natural-log units of hour 1.
BW = 0.7
# Spread shrinkage applied to the weighted quantiles around the median.
ALPHA = 0.9
# The persistence fallback's log-spread per square-root hour (the baseline's).
FALLBACK_SIGMA = 0.15


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up; whole numbers come back as int.

    Matches the kit starter's rounding, so output bytes are tidy and stable.
    """
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_ts(ts: str) -> datetime:
    """Parse an ISO 8601 UTC timestamp from the case file."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def unlock_class(unlock_text: str) -> str:
    """Classify a comparable's unlock pattern from its free-text note.

    'ea'   an early-access period preceded the standard release day, so the
           day's curve is the tail of an earlier peak, not a launch ramp;
    'sim'  one simultaneous global unlock time, so hour 1 (00:00 UTC) caught
           the category long before the unlock and the day explodes from ~0;
    'roll' midnight local time, rolling across timezones (this contest's
           target pattern);
    'unk'  anything else, mostly launches whose note says 'unverified'.
    """
    u = unlock_text.lower()
    rolling = (
        "midnight local" in u
        or "rolling" in u
        or "midnight in every timezone" in u
        or "12 am local" in u
    )
    early_access = "early-access-contaminated" in u or (
        "early access" in u
        and "no early access" not in u
        and "campaign early" not in u
    )
    simultaneous = "simultaneous" in u or "single global" in u
    if early_access:
        return "ea"
    if simultaneous and not rolling:
        return "sim"
    if rolling:
        return "roll"
    return "unk"


def launch_day_curve(comparable: dict) -> dict[int, float]:
    """The comparable's launch-day hourly viewers, keyed by hour 1..24."""
    day_start = parse_ts(comparable["day_start"])
    curve: dict[int, float] = {}
    for point in comparable.get("hourly", []):
        viewers = point.get("viewers")
        if not viewers:
            continue
        hour = int((parse_ts(point["from"]) - day_start).total_seconds() // 3600) + 1
        if 1 <= hour <= 24:
            curve[hour] = float(viewers)
    return curve


def build_donors(case: dict, p1: float) -> list[tuple[float, dict[int, float]]]:
    """(weight, log-ratio curve) for every comparable that can donate.

    A comparable donates when its launch day has a positive hour 1; its curve
    is ln(viewers(h) / viewers(1)) for the hours it has. The weight combines
    its unlock class with its scale similarity to the target's hour 1.
    """
    donors: list[tuple[float, dict[int, float]]] = []
    for comparable in sorted(case.get("comparables", []), key=lambda c: c.get("name", "")):
        # The panel also carries the target category's own pre-release
        # history, labelled "Not a launch" in its unlock note: a trailer
        # premiere day, not a release day. Never let it donate.
        if "not a launch" in str(comparable.get("unlock", "")).lower():
            continue
        curve = launch_day_curve(comparable)
        v1 = curve.get(1)
        if not v1 or v1 <= 0:
            continue
        weight = CLASS_W[unlock_class(str(comparable.get("unlock", "")))]
        weight *= math.exp(-abs(math.log(v1 / p1)) / BW)
        if weight <= 0:
            continue
        log_ratio = {h: math.log(v / v1) for h, v in curve.items() if h >= 2 and v > 0}
        if log_ratio:
            donors.append((weight, log_ratio))
    return donors


def weighted_quantile(pairs: list[tuple[float, float]], tau: float) -> float:
    """The tau-quantile of weighted (value, weight) pairs, interpolated.

    Values are sorted; the quantile is read off the cumulative-weight line
    at tau of the total weight, linearly interpolated between neighbours.
    """
    ordered = sorted(pairs)
    total = sum(w for _, w in ordered)
    if total <= 0:
        return ordered[len(ordered) // 2][0]
    target = tau * total
    acc = 0.0
    for i, (value, w) in enumerate(ordered):
        acc += w
        if acc >= target:
            if i == 0:
                return value
            prev = ordered[i - 1][0]
            return prev + (value - prev) * ((target - (acc - w)) / w if w > 0 else 0.0)
    return ordered[-1][0]


def model_quantiles(
    donors: list[tuple[float, dict[int, float]]], p1: float, hours: list[int]
) -> dict[int, list[float]] | None:
    """The model's five quantiles per hour, or None if no donor covers it.

    An hour no donor covers borrows the distribution of the nearest covered
    hour, so a sparse panel still yields a full day; only a panel with no
    usable donor at all returns None and sends the caller to the fallback.
    """
    covered = sorted({h for _, curve in donors for h in curve})
    if not covered:
        return None
    out: dict[int, list[float]] = {}
    for h in hours:
        src = h if h in covered else min(covered, key=lambda c: (abs(c - h), c))
        pairs = [(curve[src], w) for w, curve in donors if src in curve]
        median = weighted_quantile(pairs, 0.5)
        row = []
        for tau in LEVELS:
            dev = ALPHA * (weighted_quantile(pairs, tau) - median)
            row.append(p1 * math.exp(median + dev))
        out[h] = row
    return out


def persistence_quantiles(p1: float, hours: list[int]) -> dict[int, list[float]]:
    """The house baseline's curve: every hour stays at hour 1's print."""
    return {
        h: [p1 * math.exp(z * FALLBACK_SIGMA * math.sqrt(h - 1)) for z in Z] for h in hours
    }


def clean_row(values: list[float]) -> list[float | int]:
    """Clamp a quantile row into the contest's bounds and round it.

    Each value must be finite, above 0 and at most 1e9, and the row must be
    non-decreasing; rounding to 2 decimals (half up) happens last and the
    running maximum is re-applied so rounding can never invert two values.
    """
    row: list[float | int] = []
    prev = 0.0
    for v in values:
        if not math.isfinite(v) or v <= 0:
            v = prev if prev > 0 else 1.0
        v = min(max(v, 1e-9), 1e9)
        v = max(v, prev)
        r = round2(v)
        if float(r) < prev:
            r = round2(prev)
        row.append(r)
        prev = float(r)
    return row


def valid_output(obj: dict, hours: list[int]) -> bool:
    """True when obj is exactly the output shape the contest scores."""
    if set(obj.keys()) != {"hours"}:
        return False
    rows = obj["hours"]
    if len(rows) != len(hours):
        return False
    seen = set()
    for row in rows:
        if set(row.keys()) != {"hour", "q"} or row["hour"] in seen:
            return False
        seen.add(row["hour"])
        q = row["q"]
        if len(q) != len(LEVELS):
            return False
        if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 or v > 1e9 for v in q):
            return False
        if any(q[i] > q[i + 1] for i in range(len(q) - 1)):
            return False
    return seen == set(hours)


def forecast_case(case: dict, name: str) -> dict:
    """Forecast one case: model quantiles, validated, with safe fallbacks."""
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1.0, float(first["viewers"]))
    hours = [row["hour"] for row in case["forecast"]]

    donors = build_donors(case, p1)
    quantiles = model_quantiles(donors, p1, hours)
    if quantiles is None:
        quantiles = persistence_quantiles(p1, hours)
    out = {"hours": [{"hour": h, "q": clean_row(quantiles[h])} for h in hours]}
    if not valid_output(out, hours):
        fallback = persistence_quantiles(p1, hours)
        out = {"hours": [{"hour": h, "q": clean_row(fallback[h])} for h in hours]}
    if not valid_output(out, hours):
        raise ValueError(f"{name}: could not build a valid forecast")
    return out


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # Every case file, in name order, so two runs write the same bytes.
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
