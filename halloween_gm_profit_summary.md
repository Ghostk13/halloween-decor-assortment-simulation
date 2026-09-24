# Halloween Decor — GM & Profit by Item

All figures are simulated gross margin (GM $) over the same 10,000-customer Monte Carlo run used throughout this analysis (seed=42), reflecting each item's actual position, facings, channel-affinity multiplier, and margin rate under the final Scenario 2 recommendation. Source: `halloween_simulation_item_detail.csv`.

---

## In-Store (12 SKUs, 16 facings) — $1,107,942 total GM

| Item | Position | Facings | Margin Rate | Units Sold (sim) | Revenue (sim) | GM $ (sim) | GM $ / Facing |
|---|---|---:|---:|---:|---:|---:|---:|
| 12 ft Giant Skeleton | Eye | 3 | 56.8% | 1,975 | $590,525 | $335,294 | $111,765 |
| 7 ft Animated Reaper | Eye | 1 | 58.5% | 1,479 | $412,641 | $241,557 | $241,557 |
| 5.5 ft LED Skeleton Pony | Eye | 1 | 63.8% | 1,627 | $209,883 | $133,956 | $133,956 |
| 5 ft Skeleton Tombstone | Mid | 1 | 61.2% | 1,125 | $167,625 | $102,625 | $102,625 |
| 9 ft Animated Pirate Ship | Mid | 2 | 42.4% | 587 | $234,213 | $99,203 | $49,602 |
| 9.5 ft Licensed Sandworm Inflatable | Mid | 1 | 33.9% | 706 | $189,914 | $64,403 | $64,403 |
| Animated Talking Portrait | Waist | 1 | 82.5% | 942 | $37,661 | $31,067 | $31,067 |
| Pathway Light Set (6-piece) | Waist | 1 | 62.9% | 1,180 | $41,276 | $25,968 | $25,968 |
| 24 in Metal Tombstone | Waist | 1 | 81.1% | 1,229 | $30,700 | $24,897 | $24,897 |
| 12 ft Inflatable Haunted Tree | Floor | 2 | 50.8% | 296 | $52,984 | $26,936 | $13,468 |
| 8 ft Inflatable Black Cat | Floor | 1 | 49.4% | 331 | $26,149 | $12,909 | $12,909 |
| 24 in Light-Up Pumpkin Stack | Floor | 1 | 70.0% | 435 | $13,041 | $9,126 | $9,126 |
| **Total** | | **16** | | | **$2,006,613** | **$1,107,942** | |

---

## Online-Only (4 SKUs) — $387,735 total GM

| Item | Margin Rate | Units Sold (sim) | Revenue (sim) | GM $ (sim) |
|---|---:|---:|---:|---:|
| Life-Size Animated Butler | 60.4% | 998 | $398,202 | $240,623 |
| 16 ft Inflatable Haunted Archway | 48.4% | 920 | $183,080 | $88,594 |
| Animated Witch Cauldron | 58.9% | 1,116 | $88,164 | $51,969 |
| 10.5 ft Licensed Character Inflatable | 4.2% | 1,040 | $154,960 | $6,549 |
| **Total** | | | **$824,406** | **$387,735** |

---

## Removed / Not Selected — $65,294 combined GM if kept at their last simulated position

These are not part of the recommended assortment. GM $ shown is what each generated in the simulation at the position it last held — included for reference, not part of the $1,495,677 combined total above.

### Removed for weak economics (3 SKUs)

| Item | Margin Rate | GM $ (sim, at 1 facing) | Why removed |
|---|---:|---:|---|
| LED Fog Machine | 5.0% | $608 | 32% sell-through, almost no margin dollars |
| 12 ft Reaper Inflatable | 2.5% | $612 | 50% sell-through, worst margin in current lineup |
| Halloween Doormat Assortment | 17.2% | $22,370* | 45% sell-through even online, weakest item in the file |

\* Doormat was never in any simulated config (already online-only, and the online configs tested didn't include it) — this is its actual historical GM $ from last season, not a simulated figure.

### Displaced by the Haunted Tree swap (2 SKUs) — not weak, just edged out

| Item | Margin Rate | GM $ (sim, at 1 facing) | Note |
|---|---:|---:|---|
| 6 ft Scarecrow Inflatable | 35.9% | $30,981 | Simulated at its last in-store position (mid, baseline config) — a solid performer, displaced only because the Haunted Tree + this facing's reallocation scored higher |
| Solar Pathway Ghosts (4-pc) | 64.4% | $10,723 | Simulated at floor position (its only tested placement) — also solid, same story |

---

## Grand Total (Recommended Assortment Only)

| | GM $ |
|---|---:|
| In-Store | $1,107,942 |
| Online | $387,735 |
| **Combined** | **$1,495,677** |

Full detail (all configs, all items, includes units/revenue): [`halloween_simulation_item_detail.csv`](halloween_simulation_item_detail.csv)
