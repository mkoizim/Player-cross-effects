"""Shared helpers for the descriptive scripts: loading, sample definitions, rate tables, style.

Descriptive only (Phase 2): counts, rates and cross-tabs. Standard errors printed here are
naive binomial errors that ignore clustering by game; they are for scale, not inference.
"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import ERAS, FIGURES, PROCESSED, TABLES

# Palette: first three categorical slots of the reference palette (validated all-pairs).
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
ERA_COLOR = {"2000–14": AQUA, "2015–19": BLUE, "2021–25": ORANGE}
MAIN_ERAS = ["2000–14", "2015–19", "2021–25"]   # 2020 is tabulated but not plotted


def style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.titlesize": 11,
        "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.axisbelow": True, "xtick.color": INK2, "ytick.color": INK2,
        "xtick.major.size": 0, "ytick.major.size": 0,
        "lines.linewidth": 2, "lines.markersize": 6, "legend.frameon": False,
    })


def save(fig, name: str, note: str | None = None) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    if note:
        fig.text(0.01, 0.005, note, fontsize=7.5, color=INK2, ha="left", va="bottom")
    fig.savefig(FIGURES / f"{name}.png", dpi=200, bbox_inches="tight")
    (FIGURES / f"{name}.json").write_text(json.dumps(figure_contents(fig), indent=1, ensure_ascii=False) + "\n")
    plt.close(fig)
    print(f"wrote reports/figures/{name}.png (+ .json record of what it plots)")


def _num(v):
    """Round to 6 significant digits so the record compares data, not float noise."""
    v = float(v)
    return v if not np.isfinite(v) or v == 0 else float(f"{v:.6g}")


def _nums(a):
    return np.vectorize(_num, otypes=[float])(np.asarray(a, dtype=float)).tolist() if np.size(a) else []


def _color(c):
    return mcolors.to_hex(c, keep_alpha=True)


def _text(t):
    return {"text": t.get_text(), "at": _nums(t.get_position()), "color": _color(t.get_color()),
            "size": _num(t.get_fontsize()), "weight": str(t.get_fontweight())}


def _ticks(axis):
    lo, hi = sorted(axis.get_view_interval())
    locs = [x for x in axis.get_majorticklocs() if lo - 1e-9 * (hi - lo) <= x <= hi + 1e-9 * (hi - lo)]
    return {"at": _nums(locs), "labels": list(axis.get_major_formatter().format_ticks(locs))}


def figure_contents(fig) -> dict:
    """What a figure shows, independent of how it is rasterized: every plotted value, colour,
    axis range, tick and text. Saved next to each PNG and checked byte-for-byte by
    `make check-reports`, because PNG pixels differ between machines (fonts, anti-aliasing)."""
    out = {"size_in": _nums(fig.get_size_inches()), "suptitle": fig.get_suptitle(),
           "texts": [_text(t) for t in fig.texts], "axes": []}
    for ax in fig.axes:
        a = {"title": {k: ax.get_title(loc=k) for k in ("left", "center", "right") if ax.get_title(loc=k)},
             "xlabel": ax.get_xlabel(), "ylabel": ax.get_ylabel(),
             "xlim": _nums(ax.get_xlim()), "ylim": _nums(ax.get_ylim()),
             "xscale": ax.get_xscale(), "yscale": ax.get_yscale(),
             "xticks": _ticks(ax.xaxis), "yticks": _ticks(ax.yaxis),
             "lines": [{"label": ln.get_label(), "x": _nums(ln.get_xdata(orig=False)),
                        "y": _nums(ln.get_ydata(orig=False)), "color": _color(ln.get_color()),
                        "style": str(ln.get_linestyle()), "width": _num(ln.get_linewidth()),
                        "marker": str(ln.get_marker())} for ln in ax.get_lines()],
             "patches": [{"type": type(p).__name__, "label": p.get_label(),
                          "box": _nums(p.get_bbox().bounds) if hasattr(p, "get_bbox") else [],
                          "color": _color(p.get_facecolor())} for p in ax.patches],
             "collections": [], "texts": [], "legend": None}
        for c in ax.collections:
            d = {"type": type(c).__name__, "label": c.get_label(),
                 "colors": sorted({_color(x) for x in c.get_facecolor()} | {_color(x) for x in c.get_edgecolor()})}
            if hasattr(c, "get_segments"):
                d["segments"] = [_nums(s) for s in c.get_segments()]
            else:
                d["offsets"] = _nums(c.get_offsets())
                d["sizes"] = _nums(c.get_sizes())
            a["collections"].append(d)
        for t in ax.texts:
            d = _text(t)
            if hasattr(t, "xy"):  # annotation: anchor point plus offset
                d["xy"], d["offset"], d["offset_units"] = _nums(t.xy), _nums(t.xyann), str(t.anncoords)
            a["texts"].append(d)
        if (leg := ax.get_legend()) is not None:
            a["legend"] = {"title": leg.get_title().get_text(), "entries": [t.get_text() for t in leg.get_texts()]}
        out["axes"].append(a)
    return out


def write_table(df: pd.DataFrame, name: str, index: bool = False) -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLES / f"{name}.csv", index=index, float_format="%.4f")
    print(f"wrote reports/tables/{name}.csv")
    with pd.option_context("display.width", 220, "display.max_columns", 30,
                           "display.max_rows", 200, "display.float_format", "{:.4f}".format):
        print(df.to_string(index=index))


def load(table: str, columns: list[str] | None = None) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / f"{table}.parquet", columns=columns)


def pool(t: pd.Series) -> pd.Series:
    """Neighbor type as a manager weighing a lefty sees it: switch hitters bat right."""
    return t.replace({"S": "R"})


def relief_lhh(extra: list[str] | None = None) -> pd.DataFrame:
    """Primary descriptive sample: PAs in a lineup slot whose *starter* bats left only
    (intent-to-treat by slot), against a true reliever. `cfg` is the started type of the
    next two slots, switch hitters pooled with right-handed."""
    cols = ["season", "era", "slot_stype", "vs_starter", "pit_is_position_player", "vs_lhp",
            "next1_s", "next2_s", "outs", "inning", "woba_num", "woba_den"] + (extra or [])
    pa = load("pa", list(dict.fromkeys(cols)))
    d = pa[(pa.slot_stype == "L") & ~pa.vs_starter & ~pa.pit_is_position_player].copy()
    d["cfg"] = pool(d.next1_s) + pool(d.next2_s)
    return d


def rate(df: pd.DataFrame, by: list[str], col: str = "vs_lhp") -> pd.DataFrame:
    g = df.groupby(by, observed=True)[col].agg(n="size", rate="mean").reset_index()
    g["se_naive"] = np.sqrt(g.rate * (1 - g.rate) / g.n)
    return g


def woba(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = df.groupby(by, observed=True).agg(pa=("woba_den", "size"), num=("woba_num", "sum"),
                                          den=("woba_den", "sum")).reset_index()
    g["woba"] = g.num / g.den
    return g.drop(columns=["num", "den"])


def end_labels(ax, items, gap_frac: float = 0.055) -> None:
    """Direct labels at line ends, pushed apart vertically so they never overlap.
    items: (x, y, text). Call after the y-limits are final."""
    lo, hi = ax.get_ylim()
    gap = (hi - lo) * gap_frac
    placed = []
    for x, y, text in sorted(items, key=lambda t: t[1]):
        yy = y if not placed else max(y, placed[-1] + gap)
        placed.append(yy)
        ax.annotate(text, (x, yy), xytext=(9, 0), textcoords="offset points", va="center",
                    fontsize=9, color=INK)


CFG_ORDER = ["RR", "RL", "LR", "LL"]
CFG_LABEL = {"RR": "R, R", "RL": "R, L", "LR": "L, R", "LL": "L, L"}
__all__ = [n for n in dir() if not n.startswith("_")]
