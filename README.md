# gov-scout

Live DeFi governance scraper. Queries Snapshot (off-chain) and Tally (on-chain) for active proposals across 10+ major protocols. Writes a structured markdown file consumed by the [defi-intel MCP](https://github.com/defibabylon/defi-intel) `get_governance_activity` tool.

---

## Protocols tracked

| Protocol | Source | Space / Governor |
|----------|--------|-----------------|
| Aave | Snapshot | `aave.eth` |
| Uniswap | Snapshot + Tally | `uniswap` |
| Compound | Snapshot + Tally | `compound-finance.eth` |
| Curve | Snapshot | `curve.eth` |
| Morpho | Snapshot | `morpho.eth` |
| Lido | Snapshot | `lido-snapshot.eth` |
| Safe | Snapshot | `safe.eth` |
| Arbitrum | Snapshot | `arbitrumfoundation.eth` |
| Optimism | Snapshot | `op-gov.eth` |
| Gitcoin | Snapshot | `gitcoin.eth` |

---

## Output

Writes `governance_latest.md` (default: `/root/hub/data/governance_latest.md`) with active proposal titles, vote deadlines, and quorum status. The defi-intel MCP reads this file directly.

Sample output:

```markdown
# Governance Intelligence — 2026-05-26
*Generated 2026-05-26 08:00 UTC | Sources: Snapshot, Tally*

Active proposals tracked: 7 across 6 ecosystems

## Off-Chain Votes (Snapshot)
- **[Aave]** Risk Parameter Update — WBTC LTV Adjustment | ends 2026-05-28 | 82% of quorum
- **[Morpho]** Add cbBTC/USDC market on Base | ends 2026-05-29 | 1,240 votes
- **[Compound]** Set USDC supply cap on Arbitrum | ends 2026-05-27 | 67% of quorum

## On-Chain Votes (Tally)
- **[Compound]** Upgrade Timelock to v2 | ACTIVE | 91.3% FOR
```

---

## Install

```bash
git clone https://github.com/defibabylon/gov-scout
cd gov-scout
pip install -r requirements.txt
cp .env.example .env
python3 gov_scout.py
```

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OUTPUT_FILE` | Optional | Output path (default: `/root/hub/data/governance_latest.md`) |
| `TALLY_API_KEY` | Optional | Tally API key for on-chain votes. Free tier at [tally.xyz/api](https://docs.tally.xyz) |

Snapshot requires no API key.

---

## Cron (every 6 hours)

```bash
0 */6 * * * /usr/bin/python3 /path/to/gov_scout.py >> /var/log/gov-scout.log 2>&1
```

Or as systemd timer — see `gov-scout.service` / `gov-scout.timer` examples in the repo.

---

## Systemd

```ini
[Unit]
Description=gov-scout DeFi governance scraper
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/gov_scout.py
Environment=OUTPUT_FILE=/root/hub/data/governance_latest.md
Environment=TALLY_API_KEY=your_key_here

[Install]
WantedBy=multi-user.target
```

---

## Related

- [defi-intel](https://github.com/defibabylon/defi-intel) — DeFi Intelligence MCP. `get_governance_activity` reads gov-scout output directly.
- [rwa-attest](https://github.com/defibabylon/rwa-attest) — RWA protocol risk scoring engine.
