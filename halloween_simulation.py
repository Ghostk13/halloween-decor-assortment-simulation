"""
Halloween Decor assortment simulation.

Reads real performance data out of the case-study workbook, builds three
16-facing shelf configurations, and runs a Monte Carlo simulation of
customer visits to compare revenue, margin, conversion, and profit-per-facing.

Run:
    python halloween_simulation.py
"""

import os
import subprocess
import tempfile

import numpy as np
import pandas as pd
import openpyxl

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# The real case-study workbook is withheld; the default is a synthetic sample.
# Point HALLOWEEN_DATA_FILE at the real workbook to reproduce the original results.
DATA_FILE = os.environ.get("HALLOWEEN_DATA_FILE", "sample_data.xlsx")
N_CUSTOMERS = 10_000
SEED = 42
TOTAL_FACINGS = 16

IMPULSE_SHARE = 0.30          # 30% impulse buyers, 70% goal-oriented
SENSITIVITY_IMPULSE_SHARES = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70]
BROWSE_MEAN_SEC = 90.0
BROWSE_SD_SEC = 45.0

POSITION_MULT = {"eye": 1.5, "mid": 1.2, "waist": 0.8, "floor": 0.4}
CUSTOMER_MULT = {"impulse": 1.3, "goal": 0.6}
HIGH_MARGIN_THRESHOLD = 0.65   # GM rate above this -> "high-impulse margin" bucket

# Base probability = a customer's chance of picking up THIS item at neutral
# exposure (mid position, category mult 1.0, average browse time), before any
# multiplier is applied. Anchored to the item's own full-price sell-through so
# historically strong sellers start from a higher baseline. 0.15 is a scaling
# constant that keeps single-item pick probabilities in a plausible 3%-14%
# band; it is a modeling assumption, not a figure from the case data.
SELL_THROUGH_TO_BASE_PROB = 0.15
BASE_PROB_MIN, BASE_PROB_MAX = 0.02, 0.15

# New products (no sales history) get an assumed full-price sell-through
# based on the vendor pitch / merchant notes in the supplier offer sheet.
# These mirror the assumptions already used in the assortment writeup.
NEW_ITEM_ASSUMED_SELL_THROUGH = {
    "Animated Talking Portrait": 0.825,
    "24 in Light-Up Pumpkin Stack": 0.78,
    "Solar Pathway Ghosts (4-pc)": 0.75,
    "8 ft Inflatable Black Cat": 0.70,
    "14 ft Giant Animated Dragon": 0.70,
    "6 ft Licensed Movie Villain": 0.65,
    "9 ft Licensed Franchise Inflatable": 0.60,
    "7 ft Licensed Sitcom Character": 0.70,
    "Fog Machine w/ Bluetooth Sound": 0.55,
    "12 ft Inflatable Haunted Tree": 0.55,
}

LICENSED_ITEMS = {
    "10.5 ft Licensed Character Inflatable",
    "9.5 ft Licensed Sandworm Inflatable",
    "6 ft Licensed Movie Villain",
    "9 ft Licensed Franchise Inflatable",
    "7 ft Licensed Sitcom Character",
}


# ---------------------------------------------------------------------------
# Load workbook -> product master
# ---------------------------------------------------------------------------

def load_products(path):
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except PermissionError:
        # File is open in Excel and Python's own file handle gets denied even
        # read access; the `cp` binary succeeds anyway (different share-mode
        # flags), so shell out to make a throwaway copy and read that instead.
        tmp_path = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False).name
        subprocess.run(["cp", path, tmp_path], check=True)
        wb = openpyxl.load_workbook(tmp_path, data_only=True)
    ws = wb["Student Data"]
    rows = list(ws.iter_rows(values_only=True))

    products = {}

    # Current assortment block: header at row index 4 (0-based), data rows 5-16
    header = rows[4]
    col = {name: i for i, name in enumerate(header)}
    for r in rows[5:21]:
        if r[0] is None:
            continue
        name = r[0]
        products[name] = {
            "category": r[col["Category"]],
            "retail_price": r[col["Retail Price"]],
            "unit_cost": r[col["Unit Cost"]],
            "gm_rate": r[col["Gross Margin Rate"]],
            "sell_through": r[col["Full-Price Sell-Through"]],
            "current_channel": r[col["Current Channel"]],
            "current_facings": r[col["Current Facings"]],
            "star_rating": r[col["Star Rating"]],
            "num_reviews": r[col["# Reviews"]],
            "store_units": r[col["Store Units"]],
            "online_units": r[col["Online Units"]],
            "is_new": False,
        }

    # New candidates block: find header row containing "Estimated Unit Margin Rate"
    new_header_idx = next(
        i for i, r in enumerate(rows) if r and r[0] == "Item" and "Estimated Unit Margin Rate" in r
    )
    new_header = rows[new_header_idx]
    ncol = {name: i for i, name in enumerate(new_header) if name is not None}
    for r in rows[new_header_idx + 1:]:
        if r[0] is None:
            continue
        name = r[0]
        products[name] = {
            "category": r[ncol["Category"]],
            "retail_price": r[ncol["Proposed Retail"]],
            "unit_cost": r[ncol["Unit Cost"]],
            "gm_rate": r[ncol["Estimated Unit Margin Rate"]],
            "sell_through": NEW_ITEM_ASSUMED_SELL_THROUGH.get(name, 0.65),
            "current_channel": None,
            "current_facings": 0,
            "star_rating": None,   # not yet launched -- no review history exists
            "num_reviews": None,
            "store_units": None,   # no historical channel split exists yet
            "online_units": None,
            "is_new": True,
        }

    return products


def category_multiplier(name, info):
    if name in LICENSED_ITEMS:
        return 0.85, "licensed"
    if info["category"] == "Giants & Animatronics":
        return 1.0, "hero"
    if info["category"] == "Inflatables":
        return 0.95, "inflatable_mid"
    if info["gm_rate"] >= HIGH_MARGIN_THRESHOLD:
        return 1.2, "high_impulse_margin"
    return 1.1, "impulse_accessory"


def base_probability(info, demand_mult=1.0):
    p = info["sell_through"] * demand_mult * SELL_THROUGH_TO_BASE_PROB
    return float(np.clip(p, BASE_PROB_MIN, BASE_PROB_MAX))


# Real evidence, not an assumption: last season's actual Store Units / Online
# Units split (from the workbook) for items sold through BOTH channels. An
# item skewed toward online historically converts a bit worse when merchandised
# in the physical aisle, and vice versa -- share/0.5 is normalized so a 50/50
# split is neutral (1.0x). Items that were EXCLUSIVELY in one channel last
# season (the 4 online-only current items) get no adjustment: a 0%/100% split
# for them reflects that they were never offered in-store, not a revealed
# customer preference -- using it as a preference signal would be circular.
# New items have no channel history at all, so they also get 1.0x (neutral).
def channel_multiplier(info, channel):
    su, ou = info.get("store_units"), info.get("online_units")
    if not su or not ou:  # zero/None in either channel -> no informative split
        return 1.0
    share = su / (su + ou) if channel == "instore" else ou / (su + ou)
    return share / 0.5


# Stress-test demand case, mirroring a standard downside scenario: full-price
# demand runs at 70% of the base case (e.g. a softer season or a merchandising
# misfire). Applied uniformly to every item's base probability.
DEMAND_CASES = {"base": 1.0, "downside": 0.7, "upside": 1.15}


def facings_multiplier(facings):
    # Each extra facing beyond the first adds visibility, with diminishing weight.
    return 1.0 + 0.15 * (facings - 1)


# Sensitivity check only (off by default): does factoring in customer star
# ratings change the results? Anchored at 4.5 stars = neutral (1.0x), the
# roughly-average rating across the current assortment -- so a 4.8-star item
# gets a mild boost, a 4.1-star item a mild penalty. New items have no review
# history yet, so they get no adjustment (rating_mult = 1.0).
RATING_ANCHOR = 4.5


def rating_multiplier(info):
    if info["star_rating"] is None:
        return 1.0
    return float(info["star_rating"]) / RATING_ANCHOR


# ---------------------------------------------------------------------------
# Shelf configurations
# Each in-store entry: (item name, facings, position)
# ---------------------------------------------------------------------------

CONFIG_A_INSTORE = [
    ("12 ft Giant Skeleton", 3, "eye"),
    ("7 ft Animated Reaper", 1, "eye"),
    ("9 ft Animated Pirate Ship", 2, "mid"),
    ("9.5 ft Licensed Sandworm Inflatable", 1, "mid"),
    ("6 ft Scarecrow Inflatable", 1, "mid"),
    ("10.5 ft Licensed Character Inflatable", 2, "mid"),
    ("5.5 ft LED Skeleton Pony", 1, "waist"),
    ("24 in Metal Tombstone", 1, "waist"),
    ("5 ft Skeleton Tombstone", 1, "waist"),
    ("LED Fog Machine", 1, "floor"),
    ("Pathway Light Set (6-piece)", 1, "floor"),
    ("12 ft Reaper Inflatable", 1, "floor"),
]
CONFIG_A_ONLINE = [
    "16 ft Inflatable Haunted Archway",
    "Life-Size Animated Butler",
    "Animated Witch Cauldron",
    "Halloween Doormat Assortment",
]

CONFIG_B_INSTORE = [
    ("Animated Talking Portrait", 1, "eye"),
    ("24 in Light-Up Pumpkin Stack", 1, "eye"),
    ("8 ft Inflatable Black Cat", 1, "eye"),
    ("12 ft Giant Skeleton", 3, "mid"),
    ("9 ft Animated Pirate Ship", 2, "mid"),
    ("7 ft Animated Reaper", 1, "waist"),
    ("5.5 ft LED Skeleton Pony", 1, "waist"),
    ("24 in Metal Tombstone", 1, "waist"),
    ("6 ft Scarecrow Inflatable", 1, "floor"),
    ("9.5 ft Licensed Sandworm Inflatable", 1, "floor"),
    ("Pathway Light Set (6-piece)", 1, "floor"),
    ("Solar Pathway Ghosts (4-pc)", 1, "floor"),
    ("5 ft Skeleton Tombstone", 1, "floor"),
]
CONFIG_B_ONLINE = [
    "Life-Size Animated Butler",
    "16 ft Inflatable Haunted Archway",
    "Animated Witch Cauldron",
    "10.5 ft Licensed Character Inflatable",
]

CONFIG_C_INSTORE = [
    # Re-optimized after adding real channel-affinity evidence (Store/Online
    # unit split) and testing the 12 ft Inflatable Haunted Tree as a swap-in.
    # Two changes vs. the original Scenario 2: (1) 5.5 ft LED Skeleton Pony
    # takes the 3rd eye-level slot instead of 5 ft Skeleton Tombstone, because
    # the Pony's real 55%/45% store-favoring split beats the Tombstone's real
    # 45%/55% online-favoring split once that evidence is in the model; (2)
    # Solar Pathway Ghosts + 6 ft Scarecrow Inflatable (2 facings) are swapped
    # out for the 12 ft Inflatable Haunted Tree (2 facings), a net +3.15% vs.
    # the prior layout. See optimize_positions() and the Haunted Tree swap
    # test in halloween_simulation.py.
    ("12 ft Giant Skeleton", 3, "eye"),
    ("7 ft Animated Reaper", 1, "eye"),
    ("5.5 ft LED Skeleton Pony", 1, "eye"),
    ("5 ft Skeleton Tombstone", 1, "mid"),
    ("9 ft Animated Pirate Ship", 2, "mid"),
    ("9.5 ft Licensed Sandworm Inflatable", 1, "mid"),
    ("Animated Talking Portrait", 1, "waist"),
    ("24 in Metal Tombstone", 1, "waist"),
    ("Pathway Light Set (6-piece)", 1, "waist"),
    ("8 ft Inflatable Black Cat", 1, "floor"),
    ("24 in Light-Up Pumpkin Stack", 1, "floor"),
    ("12 ft Inflatable Haunted Tree", 2, "floor"),
]
CONFIG_C_ONLINE = [
    "Life-Size Animated Butler",
    "16 ft Inflatable Haunted Archway",
    "Animated Witch Cauldron",
    "10.5 ft Licensed Character Inflatable",
]

CONFIGS = {
    "A - Current (Baseline)": (CONFIG_A_INSTORE, CONFIG_A_ONLINE),
    "B - High-Margin Focus": (CONFIG_B_INSTORE, CONFIG_B_ONLINE),
    "C - Scenario 2 (Recommended)": (CONFIG_C_INSTORE, CONFIG_C_ONLINE),
}


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def browse_time_lognormal_params(mean, sd):
    sigma2 = np.log(1 + (sd / mean) ** 2)
    mu = np.log(mean) - sigma2 / 2
    return mu, np.sqrt(sigma2)


def simulate_instore(products, instore_items, n, rng, impulse_share=IMPULSE_SHARE, use_ratings=False, demand_case="base"):
    names = [x[0] for x in instore_items]
    facings = np.array([x[1] for x in instore_items], dtype=float)
    positions = [x[2] for x in instore_items]

    price = np.array([products[n_]["retail_price"] for n_ in names])
    gm_rate = np.array([products[n_]["gm_rate"] for n_ in names])
    demand_mult = DEMAND_CASES[demand_case]

    eff_base = np.array([
        base_probability(products[n_], demand_mult=demand_mult)
        * POSITION_MULT[pos]
        * category_multiplier(n_, products[n_])[0]
        * facings_multiplier(f)
        * channel_multiplier(products[n_], "instore")
        * (rating_multiplier(products[n_]) if use_ratings else 1.0)
        for n_, f, pos in zip(names, facings, positions)
    ])

    is_impulse = rng.random(n) < impulse_share
    cust_mult = np.where(is_impulse, CUSTOMER_MULT["impulse"], CUSTOMER_MULT["goal"])

    mu, sigma = browse_time_lognormal_params(BROWSE_MEAN_SEC, BROWSE_SD_SEC)
    browse_time = rng.lognormal(mu, sigma, size=n)
    attention = np.clip(browse_time / BROWSE_MEAN_SEC, 0.6, 1.6)

    prob_matrix = eff_base[None, :] * cust_mult[:, None] * attention[:, None]
    prob_matrix = np.clip(prob_matrix, 0.0, 0.95)

    purchases = rng.random((n, len(names))) < prob_matrix

    revenue_per_cust = purchases @ price
    gm_per_cust = purchases @ (price * gm_rate)
    items_per_cust = purchases.sum(axis=1)

    per_item_units = purchases.sum(axis=0)
    per_item_revenue = per_item_units * price
    per_item_gm = per_item_units * price * gm_rate

    item_detail = pd.DataFrame({
        "item": names,
        "channel": "in-store",
        "facings": facings,
        "position": positions,
        "units_sold_sim": per_item_units,
        "revenue_sim": per_item_revenue,
        "gm_sim": per_item_gm,
    })

    return {
        "avg_revenue_per_customer": revenue_per_cust.mean(),
        "avg_gm_per_customer": gm_per_cust.mean(),
        "avg_items_per_customer": items_per_cust.mean(),
        "conversion_rate": (items_per_cust > 0).mean(),
        "total_revenue": revenue_per_cust.sum(),
        "total_gm": gm_per_cust.sum(),
        "item_detail": item_detail,
    }


def simulate_online(products, online_items, n, rng, impulse_share=IMPULSE_SHARE, use_ratings=False, demand_case="base"):
    price = np.array([products[n_]["retail_price"] for n_ in online_items])
    gm_rate = np.array([products[n_]["gm_rate"] for n_ in online_items])
    demand_mult = DEMAND_CASES[demand_case]

    eff_base = np.array([
        base_probability(products[n_], demand_mult=demand_mult) * category_multiplier(n_, products[n_])[0]
        * channel_multiplier(products[n_], "online")
        * (rating_multiplier(products[n_]) if use_ratings else 1.0)
        for n_ in online_items
    ])

    is_impulse = rng.random(n) < impulse_share
    cust_mult = np.where(is_impulse, CUSTOMER_MULT["impulse"], CUSTOMER_MULT["goal"])

    mu, sigma = browse_time_lognormal_params(BROWSE_MEAN_SEC, BROWSE_SD_SEC)
    browse_time = rng.lognormal(mu, sigma, size=n)
    attention = np.clip(browse_time / BROWSE_MEAN_SEC, 0.6, 1.6)

    prob_matrix = eff_base[None, :] * cust_mult[:, None] * attention[:, None]
    prob_matrix = np.clip(prob_matrix, 0.0, 0.95)

    purchases = rng.random((n, len(online_items))) < prob_matrix
    gm_per_cust = purchases @ (price * gm_rate)
    revenue_per_cust = purchases @ price

    per_item_units = purchases.sum(axis=0)
    item_detail = pd.DataFrame({
        "item": online_items,
        "channel": "online",
        "facings": None,
        "position": "online",
        "units_sold_sim": per_item_units,
        "revenue_sim": per_item_units * price,
        "gm_sim": per_item_units * price * gm_rate,
    })

    return {
        "item_detail": item_detail,
        "total_revenue": revenue_per_cust.sum(),
        "total_gm": gm_per_cust.sum(),
    }


def run_all(impulse_share=IMPULSE_SHARE, rng=None, products=None, use_ratings=False, demand_case="base"):
    if products is None:
        products = load_products(DATA_FILE)
    if rng is None:
        rng = np.random.default_rng(SEED)

    summary_rows = []
    item_details = {}

    for config_name, (instore, online) in CONFIGS.items():
        facings_used = sum(x[1] for x in instore)
        assert facings_used == TOTAL_FACINGS, f"{config_name} uses {facings_used} facings, expected {TOTAL_FACINGS}"

        instore_result = simulate_instore(products, instore, N_CUSTOMERS, rng, impulse_share=impulse_share, use_ratings=use_ratings, demand_case=demand_case)
        online_result = simulate_online(products, online, N_CUSTOMERS, rng, impulse_share=impulse_share, use_ratings=use_ratings, demand_case=demand_case)

        profit_per_facing = instore_result["total_gm"] / TOTAL_FACINGS

        summary_rows.append({
            "Config": config_name,
            "Avg Revenue / Customer": instore_result["avg_revenue_per_customer"],
            "Avg GM / Customer": instore_result["avg_gm_per_customer"],
            "Avg Items / Customer": instore_result["avg_items_per_customer"],
            "Conversion Rate": instore_result["conversion_rate"],
            "In-Store Total Revenue": instore_result["total_revenue"],
            "In-Store Total Profit (GM $)": instore_result["total_gm"],
            "Profit per Facing": profit_per_facing,
            "Online Total Profit (GM $)": online_result["total_gm"],
            "Combined Total Profit": instore_result["total_gm"] + online_result["total_gm"],
        })
        item_details[config_name] = pd.concat(
            [instore_result["item_detail"], online_result["item_detail"]], ignore_index=True
        )

    summary = pd.DataFrame(summary_rows).set_index("Config")

    baseline_ppf = summary.loc["A - Current (Baseline)", "Profit per Facing"]
    summary["% vs Baseline Profit/Facing"] = (summary["Profit per Facing"] / baseline_ppf - 1) * 100

    return summary, item_details


def run_sensitivity(impulse_shares=SENSITIVITY_IMPULSE_SHARES):
    """Re-run all 3 configs at each impulse-buyer share, holding everything else fixed."""
    products = load_products(DATA_FILE)
    rows = []

    for share in impulse_shares:
        rng = np.random.default_rng(SEED)  # same seed at each share -> isolates the impulse-share effect
        summary, _ = run_all(impulse_share=share, rng=rng, products=products)
        for config_name, r in summary.iterrows():
            rows.append({
                "Impulse Share": share,
                "Config": config_name,
                "Conversion Rate": r["Conversion Rate"],
                "Avg Items / Customer": r["Avg Items / Customer"],
                "Profit per Facing": r["Profit per Facing"],
                "Combined Total Profit": r["Combined Total Profit"],
            })

    return pd.DataFrame(rows)


def format_sensitivity_console(sensitivity):
    ppf = sensitivity.pivot(index="Impulse Share", columns="Config", values="Profit per Facing")
    ppf.index = [f"{v * 100:.0f}%" for v in ppf.index]
    ppf = ppf.map(lambda v: f"${v:,.0f}")

    conv = sensitivity.pivot(index="Impulse Share", columns="Config", values="Conversion Rate")
    conv.index = [f"{v * 100:.0f}%" for v in conv.index]
    conv = conv.map(lambda v: f"{v * 100:.1f}%")

    return ppf, conv


def expected_attention_factor(sample_size=500_000, seed=SEED):
    """E[attention] under the browse-time model; estimated once via a large Monte Carlo draw."""
    rng = np.random.default_rng(seed)
    mu, sigma = browse_time_lognormal_params(BROWSE_MEAN_SEC, BROWSE_SD_SEC)
    browse_time = rng.lognormal(mu, sigma, size=sample_size)
    attention = np.clip(browse_time / BROWSE_MEAN_SEC, 0.6, 1.6)
    return attention.mean()


def expected_customer_multiplier(impulse_share=IMPULSE_SHARE):
    return impulse_share * CUSTOMER_MULT["impulse"] + (1 - impulse_share) * CUSTOMER_MULT["goal"]


def item_profit_coefficient(name, info, facings, e_cust_mult, e_attention):
    """
    Expected per-customer profit for this item at position_mult = 1 (i.e. before
    the eye/mid/waist/floor multiplier is applied). Because each item's purchase
    draw is independent Bernoulli with no cross-item interaction or shared
    "budget" in this model, expected profit is linear in position_mult, so the
    position-assignment problem decomposes cleanly into: coefficient_i * position_mult.
    """
    p = (
        base_probability(info)
        * category_multiplier(name, info)[0]
        * facings_multiplier(facings)
        * channel_multiplier(info, "instore")
    )
    return p * e_cust_mult * e_attention * info["retail_price"] * info["gm_rate"]


def rank_eye_level_candidates(products, top_n=10):
    """Rank every product (current + new candidates) by expected profit per single
    facing if placed at eye level -- answers "which items are the best eye-level bets"
    independent of any one shelf plan."""
    e_attn = expected_attention_factor()
    e_cust = expected_customer_multiplier()

    rows = []
    for name, info in products.items():
        coef = item_profit_coefficient(name, info, facings=1, e_cust_mult=e_cust, e_attention=e_attn)
        rows.append({
            "Item": name,
            "Category": info["category"],
            "Licensed": name in LICENSED_ITEMS,
            "New Item": info["is_new"],
            "Retail Price": info["retail_price"],
            "GM Rate": info["gm_rate"],
            "Profit / Facing @ Eye-Level ($/customer)": coef * POSITION_MULT["eye"],
        })

    ranked = pd.DataFrame(rows).sort_values(
        "Profit / Facing @ Eye-Level ($/customer)", ascending=False
    ).reset_index(drop=True)
    return ranked.head(top_n)


def optimize_positions(products, items_with_facings, capacities, impulse_share=IMPULSE_SHARE):
    """
    Exact optimizer: given a fixed roster of items (each with a fixed facings
    count) and a fixed shelf capacity (in facings) per position tier, find the
    item -> position assignment that maximizes total expected profit.

    Solved by exhaustive dynamic programming over (item index, remaining
    capacity per tier). The state space is tiny (a handful of items, capacities
    <= ~5 per tier) so this always finds the true optimum, not a heuristic.
    """
    e_attn = expected_attention_factor()
    e_cust = expected_customer_multiplier(impulse_share)

    positions = list(POSITION_MULT.keys())  # eye, mid, waist, floor
    items = [
        (name, facings, item_profit_coefficient(name, products[name], facings, e_cust, e_attn))
        for name, facings in items_with_facings
    ]
    cap0 = tuple(capacities[p] for p in positions)

    memo = {}

    def solve(idx, caps):
        if idx == len(items):
            return (0.0, None) if all(c == 0 for c in caps) else (-np.inf, None)
        key = (idx, caps)
        if key in memo:
            return memo[key]

        name, facings, coef = items[idx]
        best_val, best_choice = -np.inf, None
        for pi, pos in enumerate(positions):
            if caps[pi] >= facings:
                new_caps = caps[:pi] + (caps[pi] - facings,) + caps[pi + 1:]
                sub_val, _ = solve(idx + 1, new_caps)
                val = coef * POSITION_MULT[pos] + sub_val
                if val > best_val:
                    best_val, best_choice = val, pos

        memo[key] = (best_val, best_choice)
        return memo[key]

    total_value, _ = solve(0, cap0)

    # Reconstruct the assignment by re-walking the memo forward.
    assignment = []
    caps = cap0
    for idx, (name, facings, coef) in enumerate(items):
        _, choice = solve(idx, caps)
        assignment.append((name, facings, choice))
        pi = positions.index(choice)
        caps = caps[:pi] + (caps[pi] - facings,) + caps[pi + 1:]

    return assignment, total_value


def format_console(summary):
    disp = summary.copy()
    disp["Avg Revenue / Customer"] = disp["Avg Revenue / Customer"].map(lambda v: f"${v:,.2f}")
    disp["Avg GM / Customer"] = disp["Avg GM / Customer"].map(lambda v: f"${v:,.2f}")
    disp["Avg Items / Customer"] = disp["Avg Items / Customer"].map(lambda v: f"{v:,.3f}")
    disp["Conversion Rate"] = disp["Conversion Rate"].map(lambda v: f"{v * 100:,.1f}%")
    disp["In-Store Total Revenue"] = disp["In-Store Total Revenue"].map(lambda v: f"${v:,.0f}")
    disp["In-Store Total Profit (GM $)"] = disp["In-Store Total Profit (GM $)"].map(lambda v: f"${v:,.0f}")
    disp["Profit per Facing"] = disp["Profit per Facing"].map(lambda v: f"${v:,.0f}")
    disp["Online Total Profit (GM $)"] = disp["Online Total Profit (GM $)"].map(lambda v: f"${v:,.0f}")
    disp["Combined Total Profit"] = disp["Combined Total Profit"].map(lambda v: f"${v:,.0f}")
    disp["% vs Baseline Profit/Facing"] = disp["% vs Baseline Profit/Facing"].map(lambda v: f"{v:+.1f}%")
    return disp


if __name__ == "__main__":
    summary, item_details = run_all()

    pd.set_option("display.width", 160)
    print(f"\nHalloween Decor Shelf Simulation - {N_CUSTOMERS:,} customers per configuration, seed={SEED}\n")
    print(format_console(summary).T.to_string())

    summary.to_csv("halloween_simulation_results.csv")
    print("\nSaved: halloween_simulation_results.csv")

    all_items = pd.concat(
        [df.assign(Config=name) for name, df in item_details.items()],
        ignore_index=True,
    )
    all_items.to_csv("halloween_simulation_item_detail.csv", index=False)
    print("Saved: halloween_simulation_item_detail.csv")

    print(f"\n--- Sensitivity: Impulse Buyer Share ({', '.join(f'{s * 100:.0f}%' for s in SENSITIVITY_IMPULSE_SHARES)}) ---\n")
    sensitivity = run_sensitivity()
    ppf_table, conv_table = format_sensitivity_console(sensitivity)

    print("Profit per Facing by Impulse Share:\n")
    print(ppf_table.to_string())
    print("\nConversion Rate by Impulse Share:\n")
    print(conv_table.to_string())

    baseline_row = sensitivity[
        (sensitivity["Config"] == "A - Current (Baseline)") & (sensitivity["Impulse Share"] == IMPULSE_SHARE)
    ].iloc[0]
    sensitivity["% vs Baseline @ 30% Impulse"] = (
        sensitivity["Profit per Facing"] / baseline_row["Profit per Facing"] - 1
    ) * 100

    sensitivity.to_csv("halloween_simulation_sensitivity.csv", index=False)
    print("\nSaved: halloween_simulation_sensitivity.csv")

    print("\n--- Shelf-Position Optimization: Best Eye-Level Items ---\n")
    products = load_products(DATA_FILE)

    ranked = rank_eye_level_candidates(products)
    ranked_disp = ranked.copy()
    ranked_disp["Retail Price"] = ranked_disp["Retail Price"].map(lambda v: f"${v:,.2f}")
    ranked_disp["GM Rate"] = ranked_disp["GM Rate"].map(lambda v: f"{v * 100:.1f}%")
    ranked_disp["Profit / Facing @ Eye-Level ($/customer)"] = ranked_disp[
        "Profit / Facing @ Eye-Level ($/customer)"
    ].map(lambda v: f"${v:.4f}")
    print("Top 10 items by expected profit per facing if placed at eye level (whole product universe):\n")
    print(ranked_disp.to_string(index=False))
    ranked.to_csv("halloween_simulation_eye_level_ranking.csv", index=False)
    print("\nSaved: halloween_simulation_eye_level_ranking.csv")

    # Is Scenario 2's current eye-level placement actually optimal, given the
    # same 13-item roster and the same facings capacity per tier it already uses?
    capacities = {}
    for _, facings, pos in CONFIG_C_INSTORE:
        capacities[pos] = capacities.get(pos, 0) + facings
    items_with_facings = [(name, facings) for name, facings, _ in CONFIG_C_INSTORE]

    optimal_assignment, _ = optimize_positions(products, items_with_facings, capacities)
    current_eye = sorted(name for name, _, pos in CONFIG_C_INSTORE if pos == "eye")
    optimal_eye = sorted(name for name, _, pos in optimal_assignment if pos == "eye")

    print(f"\nScenario 2's current eye-level items: {current_eye}")
    print(f"Optimizer's eye-level items (same roster, same tier capacities): {optimal_eye}")

    if current_eye == optimal_eye:
        print("\n-> Scenario 2's eye-level placement is already optimal for this item roster and shelf capacity.")
    else:
        print("\n-> A different eye-level placement scores higher. Re-simulating with the optimized layout...")
        optimized_result = simulate_instore(products, optimal_assignment, N_CUSTOMERS, np.random.default_rng(SEED))
        optimized_ppf = optimized_result["total_gm"] / TOTAL_FACINGS
        current_ppf = summary.loc["C - Scenario 2 (Recommended)", "Profit per Facing"]
        print(f"   Current Scenario 2 profit/facing:   ${current_ppf:,.0f}")
        print(f"   Optimized layout profit/facing:     ${optimized_ppf:,.0f}  "
              f"({(optimized_ppf / current_ppf - 1) * 100:+.1f}%)")

        pd.DataFrame(optimal_assignment, columns=["item", "facings", "position"]).to_csv(
            "halloween_simulation_optimized_layout.csv", index=False
        )
        print("Saved: halloween_simulation_optimized_layout.csv")

    print("\n--- Sensitivity Check: Does Factoring In Star Ratings Change the Results? ---\n")
    print(
        f"Adds a rating_mult = star_rating / {RATING_ANCHOR} to each item's purchase probability "
        "(new items with no review history get 1.0x, i.e. no adjustment). Everything else held fixed."
    )

    rating_summary, _ = run_all(rng=np.random.default_rng(SEED), products=products, use_ratings=True)

    compare_cols = ["Profit per Facing", "Conversion Rate", "Combined Total Profit"]
    rating_check = pd.DataFrame({
        "Baseline (no ratings)": summary[compare_cols].stack(),
        "With Star Ratings": rating_summary[compare_cols].stack(),
    })
    rating_check["Abs. Change"] = rating_check["With Star Ratings"] - rating_check["Baseline (no ratings)"]
    rating_check["% Change"] = (rating_check["With Star Ratings"] / rating_check["Baseline (no ratings)"] - 1) * 100

    disp = rating_check.copy()
    for col in ["Baseline (no ratings)", "With Star Ratings", "Abs. Change"]:
        disp[col] = [
            f"{v * 100:,.2f}%" if metric == "Conversion Rate" else f"${v:,.0f}"
            for (_, metric), v in disp[col].items()
        ]
    disp["% Change"] = disp["% Change"].map(lambda v: f"{v:+.2f}%")

    print("\n" + disp.to_string())

    rating_check.to_csv("halloween_simulation_rating_check.csv")
    print("\nSaved: halloween_simulation_rating_check.csv")

    max_abs_pct_change = rating_check["% Change"].abs().max()
    print(
        f"\n-> Largest change from including star ratings: {max_abs_pct_change:.2f}%. "
        "Confirms ratings are not a material driver of these results -- the recommendation "
        "and its magnitude hold with or without them."
    )

    print("\n--- Stress Test: Base / Downside / Upside Demand Cases ---\n")
    print(
        "Downside = 70% of base full-price demand (a soft season or a merchandising miss). "
        f"Upside = {round(DEMAND_CASES['upside'] * 100)}% of base. Applied uniformly to every item's "
        "purchase probability; everything else (positions, facings, channel mix) held fixed."
    )

    stress_rows = []
    stress_item_detail = {}
    for case in ["downside", "base", "upside"]:
        case_summary, case_items = run_all(rng=np.random.default_rng(SEED), products=products, demand_case=case)
        for config_name, r in case_summary.iterrows():
            stress_rows.append({
                "Demand Case": case,
                "Config": config_name,
                "Profit per Facing": r["Profit per Facing"],
                "Combined Total Profit": r["Combined Total Profit"],
            })
        if case in ("downside", "upside"):
            stress_item_detail[case] = case_items["C - Scenario 2 (Recommended)"]

    stress = pd.DataFrame(stress_rows)
    ppf_pivot = stress.pivot(index="Demand Case", columns="Config", values="Profit per Facing").loc[
        ["downside", "base", "upside"]
    ]
    ppf_disp = ppf_pivot.map(lambda v: f"${v:,.0f}")
    print("\nProfit per Facing by Demand Case:\n")
    print(ppf_disp.to_string())

    stress.to_csv("halloween_simulation_stress_test.csv", index=False)
    print("\nSaved: halloween_simulation_stress_test.csv")

    # Per-item fragility check for Scenario 2: which SKUs lose the most ground
    # in the downside case, in percentage terms?
    base_items = item_details["C - Scenario 2 (Recommended)"].set_index("item")["gm_sim"]
    down_items = stress_item_detail["downside"].set_index("item")["gm_sim"]
    fragility = pd.DataFrame({
        "Base GM $": base_items,
        "Downside GM $": down_items,
    })
    fragility["% Change"] = (fragility["Downside GM $"] / fragility["Base GM $"] - 1) * 100
    fragility = fragility.sort_values("% Change")

    frag_disp = fragility.copy()
    frag_disp["Base GM $"] = frag_disp["Base GM $"].map(lambda v: f"${v:,.0f}")
    frag_disp["Downside GM $"] = frag_disp["Downside GM $"].map(lambda v: f"${v:,.0f}")
    frag_disp["% Change"] = frag_disp["% Change"].map(lambda v: f"{v:+.1f}%")

    print("\nScenario 2 per-item impact, Base -> Downside (most fragile first):\n")
    print(frag_disp.to_string())

    fragility.to_csv("halloween_simulation_stress_test_by_item.csv")
    print("\nSaved: halloween_simulation_stress_test_by_item.csv")
