# Developer Command Center

**The problem: CI is green while the live site serves stale code — and nobody notices.**

If you run many repos with manual deploys (Firebase CLI, App Hosting manual builds), you have two sources of truth that never talk to each other. GitHub knows what you *pushed*. Your hosting provider knows what is *live*. GitHub's own deployment records are empty for this entire workflow — checked across the whole fleet, zero deployment records — so no dashboard can answer the one question that matters: **"did what I pushed actually go live?"**

This bit me for real: on 2026-10-01, regulatory-change-radar's App Hosting auto-builds silently never fired on push. Only the initial manual build ever ran. CI was fine. The live site just wasn't the latest code, and there was no signal anywhere saying so.

Developer Command Center closes that gap. It is a fleet command center that tracks, per repo per deploy target, **latest main commit vs. last known live stamp** — push-vs-live drift detection, not another Actions list.

## What it does

- **Drift board (the core):** every repo gets a status — `LIVE` (last known deploy covers the latest push), `STALE` (main was pushed after the last deploy — pushed but not live), or `UNKNOWN` (no stamp recorded yet). Stale repos surface first with the exact gap ("pushed 43s after last deploy") and the evidence behind it.
- **Fleet overview:** per-repo cards with drift badge, latest commit, Actions status, stale-PR count, and Dependabot counts.
- **Repo detail:** commit history, Actions runs, stale PRs (>14 days untouched), Dependabot breakdown, and the stamp box showing when the target was last known live and where that stamp came from.
- **Alerts:** drift, failed Actions runs, stale PRs, and Dependabot alerts in one severity-sorted feed.
- **Build stamps:** every web build injects `stamp.json` (repo, SHA, build time, target) into the bundle, so a deployed site carries proof of what it was built from. After a manual deploy, `report_stamp.py` records the live stamp back into the fleet.

## Real data, honestly labeled

This repo is seeded with a real 19-repo fleet and real fetched state — no invented numbers anywhere:

- GitHub state (latest commits, Actions runs, open/stale PRs, Dependabot alerts, deployment records) is fetched live from the GitHub REST API by `services/main.py sync`.
- Live stamps come from **real deploy history**: Firebase Hosting release IDs (which encode microsecond deploy timestamps) for the Hosting sites, and real App Hosting rollout history for the App Hosting backends. Each stamp records its source; stamps fetched from provider history are labeled last-known-live, not cryptographically verified.
- Where a target can't be listed, the repo shows `UNKNOWN` — an honest status, not a gap to paper over.

## Rebuild it yourself

```bash
python3 services/main.py sync    # fetch GitHub state for the fleet -> data/github.json
python3 services/main.py build   # drift analysis -> web/public/{fleet,drift,alerts}.json + stamp
python3 services/main.py stamps  # show the current live-stamp table

# after you deploy one of your own sites:
python3 services/report_stamp.py <repo-name> [--sha <sha>] [--at <iso-time>]

cd web && npm install && npm run build   # prebuild hook re-runs the pipeline, then Vite builds
```

`npm run build` runs `web/scripts/prepare-public.cjs` first, which re-runs `services/main.py build` and fails loudly if the expected JSON files are missing — the deployed site can never serve stale pipeline output.

To point it at your own fleet, edit `fleet.yaml` (repo names + live URLs + target kinds) and seed `data/live-stamps.json` with your real last-deploy times.

## Project layout

```
fleet.yaml            # the fleet: repos, live URLs, deploy target kinds
data/
  github.json         # raw GitHub state per repo (from sync)
  live-stamps.json    # last-known-live stamps per repo (seeded real, operator-updated)
services/
  github_client.py    # GitHub REST fetcher (zero-auth reads; token raises limits, required for Dependabot)
  stamp.py            # build-stamp injector -> web/public/stamp.json
  report_stamp.py     # post-deploy CLI: record a live stamp after a manual deploy
  main.py             # CLI: sync / build / stamps; drift analysis -> web/public/*.json
  tests/              # pytest: drift logic edge cases, stamp round-trip, build views
web/                  # React + TypeScript + Vite (light mode ops console)
  scripts/prepare-public.cjs   # prebuild hook: re-runs the Python pipeline, verifies outputs
  src/                # Fleet overview, Drift board, Repo detail, Alerts
```

## Honest limitations

- Stamps from provider history (release IDs, rollout lists) are **last-known-live**, reconstructed after the fact — precise to the minute, but not a signed attestation from the running site. The `stamp.json` injector + `report_stamp.py` workflow is the precise path; provider history is the bootstrap.
- GitHub deployment records are empty for this entire fleet (verified 2026-10-06/07) — GitHub fundamentally cannot show "what's actually live" for manual Firebase deploys. That is the gap this tool closes, and also why the tool can't lean on GitHub for the live side.
- Drift is computed from commit time vs. stamp time with no grace period: a 43-second gap from a timestamps-only refresh flags `STALE` just like real drift. The gap text is always shown so you can tell the difference.
