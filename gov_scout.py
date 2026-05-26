#!/usr/bin/env python3
"""
gov-scout — DeFi governance proposal scraper
Queries Snapshot (off-chain) and Tally (on-chain) for active proposals.
Writes governance_latest.md consumed by defi-intel MCP get_governance_activity tool.

Cron: 0 */6 * * * python3 /path/to/gov_scout.py
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_FILE = Path(os.environ.get("OUTPUT_FILE", "/root/hub/data/governance_latest.md"))
TALLY_API_KEY = os.environ.get("TALLY_API_KEY", "")
SNAPSHOT_URL = "https://hub.snapshot.org/graphql"

SNAPSHOT_SPACES = [
    ("aave.eth",               "Aave"),
    ("uniswap",                "Uniswap"),
    ("compound-finance.eth",   "Compound"),
    ("curve.eth",              "Curve"),
    ("morpho.eth",             "Morpho"),
    ("lido-snapshot.eth",      "Lido"),
    ("safe.eth",               "Safe"),
    ("arbitrumfoundation.eth", "Arbitrum"),
    ("op-gov.eth",             "Optimism"),
    ("gitcoin.eth",            "Gitcoin"),
]

TALLY_GOVERNORS = [
    ("eip155:1:0xc0Da02939E1441F497fd74F78cE7Decb17B66529", "Compound"),
    ("eip155:1:0x408ED6354d4973f66138C91495F2f2FCbd8724C3", "Uniswap"),
]

NOW = datetime.now(timezone.utc)
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M UTC")
TODAY = NOW.strftime("%Y-%m-%d")


def _post_json(url: str, payload: dict, headers: dict = {}) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "User-Agent": "gov-scout/1.0",
        **headers,
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def fetch_snapshot_proposals(space_id: str, limit: int = 5) -> list[dict]:
    query = """
    query($space: String!, $limit: Int!) {
      proposals(
        first: $limit,
        skip: 0,
        where: { space_in: [$space], state: "active" },
        orderBy: "created",
        orderDirection: desc
      ) {
        id title state start end votes scores_total quorum
      }
    }
    """
    try:
        result = _post_json(SNAPSHOT_URL, {"query": query, "variables": {"space": space_id, "limit": limit}})
        return result.get("data", {}).get("proposals", [])
    except Exception as e:
        print(f"[WARN] Snapshot {space_id}: {e}", file=sys.stderr)
        return []


def fetch_tally_proposals(governor_id: str, limit: int = 3) -> list[dict]:
    if not TALLY_API_KEY:
        return []
    url = "https://api.tally.xyz/query"
    query = """
    query($governorId: AccountID!, $limit: Int!) {
      proposals(chainId: "eip155:1", governorId: $governorId, pagination: {limit: $limit}) {
        nodes {
          id title status eta
          voteStats { support weight percent }
        }
      }
    }
    """
    try:
        result = _post_json(
            url,
            {"query": query, "variables": {"governorId": governor_id, "limit": limit}},
            headers={"Api-Key": TALLY_API_KEY},
        )
        return result.get("data", {}).get("proposals", {}).get("nodes", [])
    except Exception as e:
        print(f"[WARN] Tally {governor_id}: {e}", file=sys.stderr)
        return []


def fmt_snapshot_proposal(p: dict, protocol: str) -> str:
    end_ts = p.get("end", 0)
    end_dt = datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d") if end_ts else "?"
    votes = int(p.get("votes", 0))
    scores_total = p.get("scores_total") or 0
    quorum = p.get("quorum") or 0
    quorum_pct = f"{(scores_total / quorum * 100):.0f}% of quorum" if quorum else f"{votes:,} votes"
    title = p.get("title", "Untitled")[:80]
    return f"- **[{protocol}]** {title} | ends {end_dt} | {quorum_pct}"


def fmt_tally_proposal(p: dict, protocol: str) -> str:
    title = p.get("title", "Untitled")[:80]
    status = p.get("status", "?")
    stats = p.get("voteStats", [])
    for stat in stats:
        if stat.get("support") == "FOR":
            pct = stat.get("percent", 0)
            return f"- **[{protocol}]** {title} | {status} | {pct:.1f}% FOR"
    return f"- **[{protocol}]** {title} | {status}"


def build_report(snapshot_results: list[tuple], tally_results: list[tuple]) -> str:
    lines = [
        f"# Governance Intelligence — {TODAY}",
        f"*Generated {TIMESTAMP} | Sources: Snapshot, Tally*",
        "",
    ]

    active_count = sum(len(proposals) for _, proposals in snapshot_results)
    active_count += sum(len(proposals) for _, proposals in tally_results)

    lines.append(f"**Active proposals tracked:** {active_count} across {len(snapshot_results) + len(tally_results)} ecosystems")
    lines.append("")

    # Off-chain (Snapshot)
    snapshot_active = [(name, props) for name, props in snapshot_results if props]
    if snapshot_active:
        lines.append("## Off-Chain Votes (Snapshot)")
        for protocol_name, proposals in snapshot_active:
            for p in proposals:
                lines.append(fmt_snapshot_proposal(p, protocol_name))
        lines.append("")

    # On-chain (Tally)
    tally_active = [(name, props) for name, props in tally_results if props]
    if tally_active:
        lines.append("## On-Chain Votes (Tally)")
        for protocol_name, proposals in tally_active:
            for p in proposals:
                lines.append(fmt_tally_proposal(p, protocol_name))
        lines.append("")

    # Fallback context if no live proposals
    if not snapshot_active and not tally_active:
        lines.append("## Known Active Governance (Fallback)")
        lines.append("- **[Aave]** Gauntlet risk parameter updates — check snapshot.org/aave.eth")
        lines.append("- **[MakerDAO/Sky]** SubDAO expansion ongoing — check forum.makerdao.com")
        lines.append("- **[Uniswap]** v4 deployment votes — check snapshot.org/uniswap")
        lines.append("- **[Liqwid]** Emission schedule votes — check app.liqwid.finance/governance")
        lines.append("")
        lines.append("*Use get_market_narrative('governance [protocol]') for live X sentiment on specific proposals.*")

    return "\n".join(lines)


def main():
    print(f"[gov-scout] Scanning governance — {TIMESTAMP}", file=sys.stderr)

    snapshot_results = []
    for space_id, name in SNAPSHOT_SPACES:
        proposals = fetch_snapshot_proposals(space_id)
        snapshot_results.append((name, proposals))
        active = len(proposals)
        if active:
            print(f"[gov-scout] {name}: {active} active proposals", file=sys.stderr)

    tally_results = []
    for governor_id, name in TALLY_GOVERNORS:
        proposals = fetch_tally_proposals(governor_id)
        tally_results.append((name, proposals))

    report = build_report(snapshot_results, tally_results)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(report, encoding="utf-8")
    print(f"[gov-scout] Written to {OUTPUT_FILE}", file=sys.stderr)

    # Stdout summary for cron/Slack
    total = sum(len(p) for _, p in snapshot_results) + sum(len(p) for _, p in tally_results)
    print(f"🗳️ gov-scout: {total} active governance proposals tracked — {TIMESTAMP}")


if __name__ == "__main__":
    main()
