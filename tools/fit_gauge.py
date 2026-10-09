"""Reproduce the UK_GAUGE_NARROW regression and draw the README figures.

    python tools/fit_gauge.py

Reads data/vintage_screw_table.csv (transcribed from
https://www.thevintagescrewcompany.com/screw-size-guide/) and writes
docs/img/regression_{light,dark}.png plus docs/hole_sizes.md.
"""
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "docs" / "img"

# Rows left out of the fit: the sub-#1 sizes (0, 00, 000, 0000) step at
# ~0.08 mm and follow a different rule, and #6 sits ~0.15 mm off the line.
OUTLIERS = {"6"}
FIT_MIN = 1


# --- formulas, kept identical to screw_holes.scad --------------------------
def shank_uk(g):          # shank_size_uk()
    return (0.06 + g * 0.013) * 25.4


def shank_uk_narrow(g):   # shank_size_uk_narrow()
    return 0.36 * g + 1.30


def holes(shank, thread_k=1.08, pilot_k=0.85):
    """Hole diameters for SCREW_FOR_METAL (the test board's setting)."""
    thread = thread_k * shank
    a, b = min(thread, shank), max(thread, shank)
    return dict(pilot=pilot_k * shank, snug=a + (b - a) / 2, clearance=1.2 * b + 0.1)


# --- data ------------------------------------------------------------------
def load():
    with open(ROOT / "data" / "vintage_screw_table.csv", encoding="utf8") as f:
        rows = list(csv.DictReader(f))
    names = [r["gauge"] for r in rows]  # keep as text: "0000" != "0"
    shank = np.array([r["shank_dia_mm"] for r in rows], float)
    # "0000".."00" are smaller than #0; only plot/fit the plain integer gauges.
    keep = [i for i, n in enumerate(names) if n == "0" or not n.startswith("0")]
    names = [names[i] for i in keep]
    return names, np.array([int(n) for n in names], float), shank[keep]


def fit(names, g, s):
    used = np.array([(gi >= FIT_MIN and n not in OUTLIERS) for n, gi in zip(names, g)])
    m, b = np.polyfit(g[used], s[used], 1)
    resid = s[used] - (m * g[used] + b)
    r2 = 1 - resid.var() / s[used].var()
    return used, m, b, r2, np.abs(resid).max()


# --- plotting --------------------------------------------------------------
THEMES = {
    "light": dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
                  grid="#e1e0d9", axis="#c3c2b7", s1="#2a78d6", s2="#eb6834"),
    "dark":  dict(surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", muted="#898781",
                  grid="#2c2c2a", axis="#383835", s1="#3987e5", s2="#d95926"),
}


def style_axes(ax, t):
    ax.set_facecolor(t["surface"])
    ax.grid(axis="y", color=t["grid"], lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(t["axis"])
    ax.tick_params(colors=t["muted"], length=0, labelsize=10)


def plot(names, g, s, used, m, b, r2, maxres, theme):
    t = THEMES[theme]
    fig, (top, bot) = plt.subplots(2, 1, figsize=(10, 7.2), sharex=True,
                                   gridspec_kw=dict(height_ratios=[2.2, 1], hspace=0.12))
    fig.patch.set_facecolor(t["surface"])
    for ax in (top, bot):
        style_axes(ax, t)

    x = np.linspace(0, 32, 200)
    ring = dict(edgecolors=t["surface"], linewidths=1.5, zorder=3)

    # Top: table vs both formulas.
    top.plot(x, shank_uk(x), color=t["s2"], lw=2, label="UK_GAUGE  (0.06 + 0.013g) in")
    top.plot(x, shank_uk_narrow(x), color=t["s1"], lw=2, label="UK_GAUGE_NARROW  0.36g + 1.30 mm")
    top.scatter(g[used], s[used], s=42, color=t["ink2"], label="Table rows used in fit", **ring)
    top.scatter(g[~used], s[~used], s=42, facecolors=t["surface"], edgecolors=t["muted"],
                linewidths=1.5, zorder=3, label="Excluded rows")
    i6 = names.index("6")
    top.annotate("#6: 3.30 mm\n(excluded, ~0.15 mm low)", (g[i6], s[i6]), xytext=(9.5, 1.7),
                 color=t["ink2"], fontsize=9.5,
                 arrowprops=dict(arrowstyle="-", color=t["muted"], lw=1))
    top.set_ylabel("Shank diameter (mm)", color=t["ink2"], fontsize=10.5)
    top.set_ylim(0, 14)
    leg = top.legend(loc="upper left", frameon=False, fontsize=9.5, labelcolor=t["ink2"])

    # Bottom: residuals (table − formula), same units, so one axis is honest.
    for f, col in ((shank_uk, t["s2"]), (shank_uk_narrow, t["s1"])):
        bot.plot(g[used], s[used] - f(g[used]), color=col, lw=2, marker="o", ms=4.5,
                 mec=t["surface"], mew=1)
    bot.axhline(0, color=t["axis"], lw=1)
    bot.set_ylabel("Table − formula (mm)", color=t["ink2"], fontsize=10.5)
    bot.set_xlabel("Screw gauge (#)", color=t["ink2"], fontsize=10.5)
    bot.set_xlim(-0.5, 33)
    bot.set_xticks(range(0, 33, 4))

    fig.text(0.125, 0.955, "Self tapping screw shank vs gauge", color=t["ink"],
             fontsize=15, weight="bold")
    fig.text(0.125, 0.918,
             f"Linear regression on gauges {FIT_MIN}–32 (minus #6): {m:.4f}·g + {b:.3f} mm, "
             f"R² = {r2:.6f}, max residual {maxres:.3f} mm.",
             color=t["ink2"], fontsize=10)
    fig.subplots_adjust(top=0.89, bottom=0.08, left=0.125, right=0.97)
    out = IMG / f"regression_{theme}.png"
    fig.savefig(out, dpi=160, facecolor=t["surface"])
    plt.close(fig)
    return out


def hole_table():
    lines = ["| Gauge | Shank | Pilot | Snug | Clearance | Head ⌀ |",
             "|---:|---:|---:|---:|---:|---:|"]
    for gauge in (2, 3, 4, 5, 6, 7, 8, 10, 12, 14):
        sh = shank_uk(gauge)
        h = holes(sh)
        head = np.ceil(sh * 13 / 6 * 2) / 2
        lines.append(f"| #{gauge} | {sh:.2f} | {h['pilot']:.2f} | {h['snug']:.2f} | "
                     f"{h['clearance']:.2f} | {head:.1f} |")
    return "\n".join(lines) + "\n"


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    names, g, s = load()
    used, m, b, r2, maxres = fit(names, g, s)
    print(f"fit: {m:.4f} g + {b:.4f}  R2={r2:.6f}  max|res|={maxres:.4f} mm")
    cross = (shank_uk(0) - shank_uk_narrow(0)) / (0.36 - 0.013 * 25.4)
    print(f"NARROW is narrower than UK_GAUGE below #{cross:.1f}")
    for theme in THEMES:
        print("wrote", plot(names, g, s, used, m, b, r2, maxres, theme))
    (ROOT / "docs" / "hole_sizes.md").write_text(hole_table(), encoding="utf8")
    print("wrote docs/hole_sizes.md")


if __name__ == "__main__":
    main()
