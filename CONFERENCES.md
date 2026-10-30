# Automatic conference collection

The Conferences workspace combines public organizer calendars with clearly labeled community directory leads. It is broad discovery, not an exhaustive global registry. No API keys or paid services are required.

## Sources

Configured in `conference_sources.yaml`:

| Source family | Evidence | Collection |
| --- | --- | --- |
| USENIX | Organizer calendar | Public HTML calendar |
| Linux Foundation | Organizer calendar | Public event cards |
| AFCEA International | Organizer calendar | Three public calendar pages; federal and international events |
| HPC User Forum | Organizer calendar | Public upcoming event rows; location may be unannounced |
| Quantum Technology Lab / quantum.info | Directory leads | Current and next-year public calendars |
| confs.tech security | Directory leads | Current and next-year public JSON |
| confs.tech data / AI | Directory leads | Current and next-year public JSON |
| confs.tech DevOps | Directory leads | Current and next-year public JSON |
| confs.tech IoT | Directory leads | Current and next-year public JSON |
| AI Deadlines community | Directory leads | Eleven conference-family YAML files; event dates only |

Organizer-calendar dates are confirmed against that calendar. They do not guarantee an announced venue or attendance format. Community dates remain leads unless a manual check or matching organizer Event JSON-LD confirms them. Dataset estimates and paper submission deadlines never become conference dates. Eight organizer confirmation attempts rotate per refresh; pages lacking structured data remain leads.

## Scheduling and resilience

Both existing hourly news and daily research jobs invoke `python scripts/refresh_conferences.py`. A persisted 24-hour due gate limits conference requests to once daily, under their existing shared publication concurrency lock. The normal report commit and Pages deployment flow publishes the resulting snapshot. GitHub dispatch timing is best effort. `--force` runs an intentional refresh; `--dry-run` collects without writing.

The collector has a 240-second budget, 15-second request timeouts and no retries. Each endpoint reports last attempt, last success, parsed/accepted/rejected rows and health. Partial failures keep previous good observations, without updating their verification dates. Missing calendar entries are marked retained; absence never implies cancellation. Explicit organizer JSON-LD cancellation/postponement and manual corrections are supported. HTML calendars do not reliably expose cancellation status, so users must check event links before booking.

Events retain 90 days of history and a two-year horizon. Deduplication uses canonical links, edition, title, location and stable source identities; different cities and years remain separate. Conflicting date ranges stay visible. Date/location/status changes retain a short history. Event dates are local calendar dates, while collection timestamps display Central Time.

`reports/conference-state.json` persists observations for collection only; it is not shipped as a site asset. `reports/conferences.json` is the validated public snapshot, loaded only when Conferences opens, with 36-card pagination. The builder uses the original `dashboard/conferences.json` manual seed only when no collected snapshot exists. The public directory budget is 750 KB and 1,200 events; overflow fails before replacing good data. Existing dashboard budgets and release gates remain in force.

## Maintenance and corrections

To add a source, add its public endpoint, evidence role, topics and parser name to the YAML. Add representative offline parser fixtures/tests when introducing markup. Inspect the workspace's Sources and collection health disclosure after changes. Do not bypass blocked sources: HPCwire returned HTTP 403 during discovery and is not enabled.

`conference_overrides.json` supports `excluded_ids` and an `events` mapping keyed by public event ID. An override requires `reason` and an ISO `verified` date; allowed corrections are name, URL, start/end, location, mode, status and note. Set both start/end to null for unannounced editions. Preserve the organizer URL and explain the evidence in the reason. Overrides win over automatic observations; review and remove obsolete overrides deliberately.

Coverage limits: directory accuracy varies; many organizer pages lack structured metadata; new annual endpoints may not exist yet; AFCEA discovery is bounded to three pages; topic labels are broad. Public snapshots expose source failures and unconfirmed leads instead of silently claiming complete coverage.
