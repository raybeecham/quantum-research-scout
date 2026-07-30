from __future__ import annotations

import argparse
import os
import sys
from copy import deepcopy
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pqc_quantum_research_agent.collectors import collect_patents
from pqc_quantum_research_agent.config import load_config
from pqc_quantum_research_agent.http import HttpClient


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify every configured USPTO patent query without generating reports."
    )
    parser.add_argument("--config", default="sources.yaml")
    parser.add_argument("--max-items-per-query", type=int, default=3)
    args = parser.parse_args()

    config = load_config(args.config)
    patent_config = deepcopy(config.patents)
    api_key_env = str(patent_config.get("api_key_env") or "USPTO_ODP_API_KEY")
    if not os.getenv(api_key_env, "").strip():
        print(f"{api_key_env} is not configured.", file=sys.stderr)
        return 2

    queries = [query for query in patent_config.get("queries", []) if query.get("enabled", True)]
    if not queries:
        print("No enabled patent queries are configured.", file=sys.stderr)
        return 2

    patent_config["max_items_per_query"] = max(1, args.max_items_per_query)
    client = HttpClient(
        config.settings.user_agent,
        timeout_seconds=config.settings.request_timeout_seconds,
    )
    result = collect_patents(client, patent_config, args.max_items_per_query)
    if result.warnings:
        for warning in result.warnings:
            print(f"{warning.source_name}: {warning.message}", file=sys.stderr)
        print(
            f"Patent API smoke test failed: {len(result.warnings)} of {len(queries)} queries returned warnings.",
            file=sys.stderr,
        )
        return 1

    print(
        f"Patent API smoke test passed: {len(queries)} queries accepted; "
        f"{len(result.items)} unique candidates sampled."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
