"""
Static "3D" render of the Scenario 2 in-store shelf layout (16 facings, 4
tiers). Built as a hand-drawn cavalier/oblique projection using plain 2D
matplotlib patches (explicit back-to-front draw order), rather than
mplot3d -- mplot3d's automatic depth-sorting is unreliable for a scene this
busy (many overlapping boxes + shelf boards) and produces incorrect
occlusion. Drawing our own projection guarantees correct front-to-back
layering because we control the paint order directly.

Run:
    python halloween_shelf_layout_3d.py
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import to_rgb

from halloween_simulation import CONFIG_C_INSTORE, load_products, DATA_FILE

# Home Depot brand palette: white (background), orange (primary), black
# (secondary), warm grey (third category / neutral).
HD_ORANGE = "#F96302"
HD_BLACK = "#1A1A1A"
HD_GREY = "#6D6D6D"

CATEGORY_COLOR = {
    "Giants & Animatronics": HD_ORANGE,
    "Inflatables": HD_ORANGE,
    "Decor & Accessories": HD_ORANGE,
}

CATEGORY_SHORT = {
    "Giants & Animatronics": "GIANTS",
    "Inflatables": "INFLATABLES",
    "Decor & Accessories": "DECOR",
}

POSITION_ORDER = ["floor", "waist", "mid", "eye"]  # bottom to top, physically
POSITION_LABEL = {
    "eye": "EYE LEVEL",
    "mid": "MID SHELF",
    "waist": "WAIST LEVEL",
    "floor": "FLOOR",
}
POSITION_SUBLABEL = {
    "eye": "Highest exposure ×1.5",
    "mid": "×1.2",
    "waist": "×0.8",
    "floor": "Lowest exposure ×0.4",
}

UNIT_WIDTH = 1.55
ITEM_GAP = 0.12
BAR_HEIGHT = 1.55
TIER_GAP = 0.65
DEPTH = 0.9          # pseudo-3D depth (world units)
SHX, SHY = 0.5, 0.3   # cavalier shear: how much depth shifts screen x/y
BOARD_THICKNESS = 0.12
BOARD_OVERHANG = 0.25


def shade(hex_color, factor):
    r, g, b = to_rgb(hex_color)
    if factor >= 1:
        r, g, b = [c + (1 - c) * (factor - 1) for c in (r, g, b)]
    else:
        r, g, b = [c * factor for c in (r, g, b)]
    return (min(r, 1), min(g, 1), min(b, 1))


def proj(x, y, z):
    """Cavalier projection: depth (y) shifts screen position diagonally."""
    return (x + SHX * y, z + SHY * y)


def draw_box(ax, x0, x1, z0, z1, base_color, edge="white", lw=1.0, depth=DEPTH, zorder=1):
    front_c = base_color
    top_c = shade(base_color, 1.35)
    side_c = shade(base_color, 0.62)

    # Right side face
    side_pts = [
        proj(x1, 0, z0), proj(x1, depth, z0),
        proj(x1, depth, z1), proj(x1, 0, z1),
    ]
    ax.add_patch(mpatches.Polygon(side_pts, closed=True, facecolor=side_c, edgecolor=edge, linewidth=lw, zorder=zorder))

    # Top face
    top_pts = [
        proj(x0, 0, z1), proj(x1, 0, z1),
        proj(x1, depth, z1), proj(x0, depth, z1),
    ]
    ax.add_patch(mpatches.Polygon(top_pts, closed=True, facecolor=top_c, edgecolor=edge, linewidth=lw, zorder=zorder + 1))

    # Front face (drawn last -> on top, and it's a plain rectangle for text)
    front_pts = [
        proj(x0, 0, z0), proj(x1, 0, z0),
        proj(x1, 0, z1), proj(x0, 0, z1),
    ]
    ax.add_patch(mpatches.Polygon(front_pts, closed=True, facecolor=front_c, edgecolor=edge, linewidth=lw, zorder=zorder + 2))


def wrap_name(name, width=15):
    words = name.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def build_layout():
    products = load_products(DATA_FILE)

    by_position = {p: [] for p in POSITION_ORDER}
    for name, facings, pos in CONFIG_C_INSTORE:
        by_position[pos].append((name, facings, products[name]))

    max_row_width = max(
        sum(f * UNIT_WIDTH + ITEM_GAP for _, f, _ in items) - ITEM_GAP
        for items in by_position.values()
    )

    fig_w_world = max_row_width + SHX * DEPTH + 3.6   # + left label gutter + right pad
    fig_h_world = len(POSITION_ORDER) * (BAR_HEIGHT + TIER_GAP) + SHY * DEPTH + 1.6

    fig, ax = plt.subplots(figsize=(13.5, 9.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(-3.2, max_row_width + SHX * DEPTH + 0.5)
    ax.set_ylim(-0.3, fig_h_world - 0.9)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(
        (-3.2 + max_row_width + SHX * DEPTH + 0.5) / 2, fig_h_world - 0.55,
        "Scenario 2 — Recommended In-Store Shelf Layout (16 Facings)",
        ha="center", va="center", fontsize=17, fontweight="bold", color=HD_BLACK,
    )
    ax.text(
        (-3.2 + max_row_width + SHX * DEPTH + 0.5) / 2, fig_h_world - 0.98,
        "Re-optimized with real channel evidence: LED Skeleton Pony takes eye-level; Haunted Tree replaces Solar Ghosts + Scarecrow (+13.1% profit/facing vs. baseline)",
        ha="center", va="center", fontsize=10.5, style="italic", color=HD_GREY,
    )

    for t_idx, pos in enumerate(POSITION_ORDER):
        z0 = t_idx * (BAR_HEIGHT + TIER_GAP)
        z1 = z0 + BAR_HEIGHT
        items = by_position[pos]
        row_width = sum(f * UNIT_WIDTH + ITEM_GAP for _, f, _ in items) - ITEM_GAP

        # Shelf board (wide, thin box) directly under this tier's items
        draw_box(
            ax, -BOARD_OVERHANG, row_width + BOARD_OVERHANG,
            z0 - BOARD_THICKNESS, z0,
            "#E8E8E8", edge="#B3B3B3", lw=0.8, depth=DEPTH + 0.35, zorder=2,
        )

        ax.text(
            -1.15, z0 + BAR_HEIGHT / 2 + 0.14, POSITION_LABEL[pos],
            ha="right", va="center", fontsize=13, fontweight="bold", color=HD_BLACK,
        )
        ax.text(
            -1.15, z0 + BAR_HEIGHT / 2 - 0.18, POSITION_SUBLABEL[pos],
            ha="right", va="center", fontsize=9, color=HD_GREY,
        )

        x = 0.0
        for name, facings, info in items:
            w = facings * UNIT_WIDTH
            color = CATEGORY_COLOR.get(info["category"], "#999999")
            draw_box(ax, x, x + w - 0.05, z0, z1, color, zorder=10 + t_idx * 20)

            fx0, fz0 = proj(x, 0, z0)
            fx1, fz1 = proj(x + w - 0.05, 0, z1)
            cx = (fx0 + fx1) / 2

            ax.text(
                cx, fz1 - 0.14,
                CATEGORY_SHORT.get(info["category"], info["category"].upper()),
                ha="center", va="top", fontsize=7, fontweight="bold", color="white",
                alpha=0.85, zorder=200,
            )
            ax.text(
                cx, fz1 - 0.40, wrap_name(name),
                ha="center", va="top", fontsize=9, fontweight="bold", color="white",
                linespacing=1.25, zorder=200,
            )
            ax.text(
                cx, fz0 + 0.42, f"${info['retail_price']:,.2f}",
                ha="center", va="center", fontsize=9.5, fontweight="bold", color="white", zorder=200,
            )
            ax.text(
                cx, fz0 + 0.14,
                f"{facings} facing{'s' if facings > 1 else ''} · {info['gm_rate'] * 100:.0f}% GM",
                ha="center", va="center", fontsize=7.3, color="white", alpha=0.9, zorder=200,
            )

            x += w + ITEM_GAP

    ax.text(
        -3.1, -0.2, f"Total: 16 facings across {len(CONFIG_C_INSTORE)} SKUs",
        ha="left", va="bottom", fontsize=9, color=HD_GREY,
    )

    fig.tight_layout(rect=[0, 0.02, 1, 1])
    return fig


if __name__ == "__main__":
    fig = build_layout()
    fig.savefig("halloween_shelf_layout_3d.png", dpi=200, bbox_inches="tight", facecolor="white")
    print("Saved: halloween_shelf_layout_3d.png")
