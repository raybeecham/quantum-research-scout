# Growth and reliability work, October 25, 2026

## 1. Built-site release gate

CI and Pages deployment now run the browser regressions against the built artifact before it can be published. The release gate covers frozen examples of the five requested event pairs, a different study that must not merge, security-only exclusions from Quantum, serialized and rendered excerpt cleanup, all twelve workspaces, mobile overflow, placeholder text, and every generated permanent story URL. The existing round-two suite covers all eleven deep links, search, keyboard focus, notebook actions, and persistent display preferences.

CI runs the new gate headed under Xvfb. Local verification uses Edge with an active, visible page and explicitly confirms animation frames execute. External images and AI services are intercepted; no provider calls are made.

Verification: the current build passed, including 222 story pages. Deliberately adding `Read More` to a rendered summary failed the feed assertion. Deliberately restoring a second card for one merged event failed the exact card-count assertion. `--prove-regressions` automates both negative checks in CI.

Run with a static server serving `site/` on port 8765:

```powershell
python scripts/build_dashboard.py --output site
python scripts/verify_frontier_round2_browser.py --channel msedge
python scripts/verify_publication_gate.py --channel msedge --prove-regressions
```
