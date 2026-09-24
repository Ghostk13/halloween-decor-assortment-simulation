"""
Renders the Scenario 2 in-store shelf layout (16 facings, 4 position tiers)
as a planogram-style graphic, using the same CONFIG_C_INSTORE roster as the
simulation.

Run:
    python halloween_shelf_layout.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

from halloween_simulation import CONFIG_C_INSTORE, load_products, DATA_FILE

# Home Depot brand palette: white background, every block orange, black text.
HD_ORANGE = "#F96302"
HD_BLACK = "#1A1A1A"
HD_GREY = "#6D6D6D"
HD_WHITE = "#FFFFFF"

CATEGORY_COLOR = {
    "Giants & Animatronics": HD_ORANGE,
    "Inflatables": HD_ORANGE,
    "Decor & Accessories": HD_ORANGE,
}

CATEGORY_ORDER = ["Giants & Animatronics", "Inflatables", "Decor & Accessories"]

POSITION_RANK = {"eye": 0, "mid": 1, "waist": 2, "floor": 3}
POSITION_LABEL = {
    "eye": "EYE LEVEL",
    "mid": "MID SHELF",
    "waist": "WAIST LEVEL",
    "floor": "FLOOR",
}

FACING_WIDTH = 1.55
FACING_GAP = 0.12
ROW_HEIGHT = 1.55
ROW_GAP = 0.35
LEFT_MARGIN = 2.5
TOP_MARGIN = 1.3


def wrap_name(name, width=14):
    words = name.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def build_layout(instore_items=None, title=None, subtitle=None):
    if instore_items is None:
        instore_items = CONFIG_C_INSTORE
    products = load_products(DATA_FILE)

    by_category = {c: [] for c in CATEGORY_ORDER}
    for name, facings, pos in instore_items:
        info = products[name]
        by_category[info["category"]].append((name, facings, pos, info))
    for cat in by_category:
        by_category[cat].sort(key=lambda item: POSITION_RANK[item[2]])

    total_facings_used = sum(f for _, f, _ in instore_items)
    max_row_facings = max(sum(f for _, f, _, _ in items) for items in by_category.values())
    fig_width = LEFT_MARGIN + max_row_facings * (FACING_WIDTH + FACING_GAP) + 1.0
    fig_height = TOP_MARGIN + len(CATEGORY_ORDER) * (ROW_HEIGHT + ROW_GAP) + 1.0

    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_xlim(0, fig_width)
    ax.set_ylim(0, fig_height)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    ax.text(
        fig_width / 2, fig_height - 0.5,
        title or "Scenario 2 — Recommended In-Store Shelf Layout (16 Facings)",
        ha="center", va="center", fontsize=17, fontweight="bold", color=HD_BLACK,
    )
    ax.text(
        fig_width / 2, fig_height - 0.95,
        subtitle or "Re-optimized with real channel evidence: LED Skeleton Pony takes eye-level; Haunted Tree replaces Solar Ghosts + Scarecrow (+13.1% profit/facing vs. baseline)",
        ha="center", va="center", fontsize=10.5, style="italic", color=HD_GREY,
    )

    y = fig_height - TOP_MARGIN - ROW_HEIGHT
    for cat in CATEGORY_ORDER:
        items = by_category[cat]
        row_facings = sum(f for _, f, _, _ in items)

        # Shelf row background band
        ax.add_patch(
            mpatches.Rectangle(
                (0.15, y - 0.12), fig_width - 0.3, ROW_HEIGHT + 0.24,
                facecolor="#F2F2F2", edgecolor="none", zorder=0,
            )
        )
        # Shelf ledge line
        ax.plot([0.15, fig_width - 0.15], [y - 0.12, y - 0.12], color="#C7C7C7", lw=2.5, zorder=1)

        ax.text(
            LEFT_MARGIN - 0.25, y + ROW_HEIGHT / 2 + 0.22,
            wrap_name(cat.upper(), width=8), ha="right", va="center",
            fontsize=13, fontweight="bold", color=HD_BLACK, linespacing=1.3,
        )
        ax.text(
            LEFT_MARGIN - 0.25, y + ROW_HEIGHT / 2 - 0.35,
            f"{row_facings} facing{'s' if row_facings > 1 else ''} · {len(items)} SKU{'s' if len(items) > 1 else ''}",
            ha="right", va="center",
            fontsize=9, color=HD_GREY,
        )

        x = LEFT_MARGIN
        for name, facings, pos, info in items:
            w = facings * FACING_WIDTH + (facings - 1) * (FACING_GAP * 0.4)
            color = CATEGORY_COLOR.get(info["category"], "#999999")

            box = FancyBboxPatch(
                (x, y), w, ROW_HEIGHT,
                boxstyle="round,pad=0,rounding_size=0.08",
                facecolor=color, edgecolor="white", linewidth=1.5, zorder=2,
            )
            ax.add_patch(box)

            ax.text(
                x + w / 2, y + ROW_HEIGHT - 0.32,
                wrap_name(name), ha="center", va="top",
                fontsize=9, fontweight="bold", color="white", zorder=3,
                linespacing=1.25,
            )
            ax.text(
                x + w / 2, y + 0.28,
                f"${info['retail_price']:,.2f}",
                ha="center", va="center", fontsize=9.5, fontweight="bold", color="white", zorder=3,
            )
            ax.text(
                x + w / 2, y + 0.10,
                f"{facings} facing{'s' if facings > 1 else ''} · {info['gm_rate'] * 100:.0f}% GM",
                ha="center", va="center", fontsize=7.5, color="white", alpha=0.9, zorder=3,
            )

            x += w + FACING_GAP

        y -= (ROW_HEIGHT + ROW_GAP)

    ax.text(
        0.15, 0.15,
        f"Total: {total_facings_used} facings across {len(instore_items)} SKUs",
        ha="left", va="bottom", fontsize=9, color=HD_GREY,
    )

    fig.tight_layout(rect=[0, 0.03, 1, 1])
    return fig


if __name__ == "__main__":
    fig = build_layout()
    fig.savefig("halloween_shelf_layout.png", dpi=200, bbox_inches="tight", facecolor="white")
    print("Saved: halloween_shelf_layout.png")
