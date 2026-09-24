# Halloween Decor Assortment — Project Handoff

Last updated: 2026-09-23. This documents the Python simulation workstream (which replaced the Simio V19 model) and where it stands.

---

## 1. Goal and constraints

Recommend next season's Halloween Decor assortment for Home Depot (case competition; 8-minute VP presentation + 5-minute Q&A).

- In-store: **exactly 16 facings**
- Online-only: **0–4 items**
- All three categories (Giants & Animatronics, Inflatables, Decor & Accessories) must appear in-store
- Source data: `Halloween_Line Review Case Study_Data - Copy.xlsx` (sheet `Student Data`: 16 current items + 10 new supplier candidates)

## 2. Current recommendation ("Scenario 2", final)

**In-store — 12 SKUs, 16 facings** (defined in `CONFIG_C_INSTORE`, `halloween_simulation.py`)

| Item | Facings | Position |
|---|---:|---|
| 12 ft Giant Skeleton | 3 | Eye |
| 7 ft Animated Reaper | 1 | Eye |
| 5.5 ft LED Skeleton Pony | 1 | Eye |
| 5 ft Skeleton Tombstone | 1 | Mid |
| 9 ft Animated Pirate Ship | 2 | Mid |
| 9.5 ft Licensed Sandworm Inflatable | 1 | Mid |
| Animated Talking Portrait (new) | 1 | Waist |
| 24 in Metal Tombstone | 1 | Waist |
| Pathway Light Set (6-piece) | 1 | Waist |
| 8 ft Inflatable Black Cat (new) | 1 | Floor |
| 24 in Light-Up Pumpkin Stack (new) | 1 | Floor |
| 12 ft Inflatable Haunted Tree (new) | 2 | Floor |

**Online-only (4):** Life-Size Animated Butler, 16 ft Inflatable Haunted Archway, Animated Witch Cauldron, 10.5 ft Licensed Character Inflatable (moved from in-store).

**Removed — weak economics (3):** LED Fog Machine, 12 ft Reaper Inflatable, Halloween Doormat Assortment.
**Displaced by the Haunted Tree swap (2):** 6 ft Scarecrow Inflatable, Solar Pathway Ghosts (4-pc) — solid items, edged out.
**New candidates not selected (5):** 14 ft Giant Animated Dragon, 6 ft Licensed Movie Villain, 9 ft Licensed Franchise Inflatable, 7 ft Licensed Sitcom Character, Fog Machine w/ Bluetooth Sound.

## 3. Headline results (10,000 simulated customers, seed 42)

| | Last season (Config A) | Scenario 2 (Config C) | Gain |
|---|---:|---:|---:|
| In-store GM $ | $979,735 | $1,107,942 | +$128,207 |
| Profit per facing | $61,233 | $69,246 | +13.1% |
| Conversion rate | 64.4% | 66.4% | +2.0 pts |
| Online GM $ | $397,227 | $387,735 | −$9,492 |
| Combined GM $ | $1,376,962 | $1,495,677 | +$118,715 (+8.6%) |

Config B ("High-Margin Focus") is the losing alternative: $52,257/facing (−14.7% vs. baseline).

Robustness checks (all in the report): Scenario 2 leads at every impulse-buyer share from 10% to 70%; leads under the 70%-demand downside case ($48,564/facing vs. $43,001 baseline); adding star ratings moves results by at most 1.23%.

## 4. How the model works

`P(purchase item i) = base_prob × position_mult × customer_type_mult × category_mult × facings_mult × channel_mult × attention_factor`, drawn as an independent Bernoulli per customer per item, then revenue/GM accumulated per customer.

- **base_prob:** item's full-price sell-through × 0.15, clipped to 2%–15%. New items have no history, so sell-through is an *assumption* (`NEW_ITEM_ASSUMED_SELL_THROUGH`, e.g. Talking Portrait 82.5%, Haunted Tree 55%).
- **position_mult:** eye 1.5 / mid 1.2 / waist 0.8 / floor 0.4 (specified inputs).
- **customer_type_mult:** 30% impulse (1.3×), 70% goal-oriented (0.6×).
- **category_mult:** hero 1.0, inflatable 0.95, licensed 0.85, high-margin decor (GM ≥ 65%) 1.2, other decor 1.1.
- **facings_mult:** +15% per facing beyond the first (modeling assumption).
- **channel_mult:** real last-season Store/Online unit split, `share / 0.5`; applied only to items sold through both channels; neutral (1.0) for the 4 previously online-only items (0%/100% reflects availability, not preference) and all new items.
- **attention_factor:** LogNormal(90s, 45s) browse time / 90, clipped 0.6–1.6.
- Online items use the same formula without position/facings multipliers.

**Assumptions that are mine, not from the data:** the 0.15 scaling constant, the +15%/facing multiplier, the new-item sell-through values, and reuse of the same 10,000 visits for the online channel (online traffic is not calibrated). Position/customer/category multipliers were specified in the original brief. Treat outputs as directional, not decimal-precise forecasts.

**Optimizer:** `optimize_positions()` is an exact dynamic program that assigns a fixed item roster to position tiers given tier capacities (currently eye 5 / mid 4 / waist 3 / floor 4). It works because items are independent (profit is linear in position_mult). It optimizes *position only*; composition swaps (e.g. the Haunted Tree) were tested by hand.

## 5. Files

| File | Purpose |
|---|---|
| `halloween_simulation.py` | Everything: data load, model, 3 configs, sensitivity, optimizer, rating check, stress test. Run `python halloween_simulation.py` (~seconds) to regenerate all CSVs |
| `halloween_shelf_layout.py` / `.png` | 2D planogram, **grouped by category**, Home Depot palette. `build_layout(instore_items, title, subtitle)` is reusable for any roster |
| `halloween_shelf_layout_3d.py` / `.png` | Pseudo-3D render, still **grouped by shelf position** (not yet restyled to match the 2D) |
| `halloween_shelf_layout_requested_items.png` | 2D layout of an *alternate* 13-item roster (see §6) — not the official recommendation |
| `halloween_decor_report.md` | Full 11-section report (recommendation, placement map, rationale, methodology, results, sensitivity, stress test) |
| `halloween_gm_profit_summary.md` | Per-item GM/profit for in-store, online, removed |
| `halloween_simulation_*.csv` | Results, per-item detail (in-store + online), sensitivity, stress tests, rating check, eye-level ranking, full 26-item product data |
| `Halloween_Decor_Assortment_Summary.docx/.pdf` | Summary document that was already in the folder — **not produced or reviewed in this workstream**, so its numbers may not match the current model |
| `sample_data.xlsx` / `make_sample_data.py` | Synthetic stand-in for the withheld source workbook (`Halloween_Line Review Case Study_Data - Copy.xlsx`). The code reads the sample by default; set `HALLOWEEN_DATA_FILE` to use the real one. All committed outputs and numbers in this document came from the real data |

Left out of the repo (kept locally only): the superseded Simio model files, the case instructions PDF, `files.zip`, and some stray screenshots.

## 6. Open decisions and known gaps

1. **Haunted Tree: in-store or online?** The simulation places it in-store (floor, 2 facings; +3.15% vs. the prior layout). The team's workbook (`Halloween Assortment — Team Calculator & Scenario Comparison.xlsx`, not included in this repo) recommends *online*, citing footprint and an unverified compact-carton claim. The simulation models sales economics only — no shipping, fulfillment, or floor-footprint cost.
2. **Differences vs. the team workbook's "Balanced" scenario:** Balanced puts the Pirate Ship *online*, *removes* the Licensed Character (we move it online), *removes* the Witch Cauldron (we keep it online), and *adds* the 7 ft Sitcom Character in-store (we pass). These have not been reconciled.
3. **Pirate Ship online test — incomplete.** Swapping the Pirate Ship into the online set (Pirate Ship, Archway, Butler, Cauldron) simulates at $570,061 online GM vs. $397,227 last season (+$172,834). This covers only the online side; the Pirate Ship currently earns ~$99K in-store across 2 facings, and the freed facings haven't been backfilled or net-evaluated.
4. **Alternate 13-item roster** (Pirate Ship out; Scarecrow and Solar Ghosts in) was graphed at the user's request with optimizer-chosen positions but **never simulated for profit**.
5. **Report drift:** the report does not yet mention items 3–4 above, doesn't list `halloween_gm_profit_summary.md` or the requested-items graphic in its Files table, and its Section 6 embeds a 2D graphic that no longer shows shelf positions (positions live in Section 2's table and the 3D render).
6. **3D render** hasn't been converted to category grouping.
7. **No PowerPoint exists.** A deck was requested early on but the user redirected to a Markdown report + graphics; `python-pptx` was not installed (install was declined) and Node.js isn't available on this machine.

## 7. Environment notes

- The real workbook is not in the repo; without it, runs use synthetic data and overwrite the committed outputs with illustrative numbers.
- Windows, Git Bash. Use `python`, not `python3` (the latter hits the Microsoft Store stub).
- Git Bash `/tmp` is not visible to Windows Python; write scratch files to a Windows path.
- If the source workbook is open in Excel, Python's `open()` gets `PermissionError`; `load_products()` falls back to copying via `cp` and reading the copy.
- Installed for this work: `pandas`, `openpyxl`, `numpy`, `matplotlib`.
- Not a git repository.

## 8. Suggested next steps

1. Decide Haunted Tree channel (in-store vs. online) — this is the main conflict with the team's own evidence.
2. Run the full net analysis for the Pirate Ship online option (backfill the 2 freed facings via `optimize_positions()` or a candidate swap test, then compare combined profit).
3. Reconcile the remaining differences with the team's "Balanced" scenario, or document why the model diverges.
4. Refresh the report (§6 above), restyle the 3D render if it will be used, and produce slides from the report if a deck is still needed.
