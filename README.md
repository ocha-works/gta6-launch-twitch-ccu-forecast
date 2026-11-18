# gta6-launch-twitch-ccu-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/ocha-works/gta6-launch-twitch-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/ocha-works/gta6-launch-twitch-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A forecasting program for Grand Theft Auto VI's launch-day Twitch audience. Given a case file that records hour 1 of release day (2026-11-19, UTC) and a panel of 42 comparable past launches with their hourly Twitch curves, it writes five quantiles (0.05–0.95) of the concurrent-viewer count for each of hours 2–24. The model treats every comparable's launch day as a log-ratio curve over its own first hour, then takes weighted empirical quantiles of those curves: donors are weighted by unlock pattern (GTA VI is a rolling midnight-local console launch with no early access) and by how close their first hour's crowd is to the target's. Parameters were set by leave-one-out cross-validation over the panel (pinball loss ≈ 0.26 on rolling-midnight launches, vs ≈ 0.39 for the persistence baseline on the practice cases). See MODEL.md for the research, the numbers and the sources.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Python 3.13, standard library only. `input/` is a directory of case files (`*.in`, e.g. the practice cases from the competition kit); one `<id>.out` forecast is written per case. With no environment variables set it reads `/input` and writes `/output`, as the grader runs it.

---

<sub>Entered on [make.fun](https://make.fun/?ref=yhjp53pb&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
