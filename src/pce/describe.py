"""Shared helpers for the descriptive scripts: loading, sample definitions, rate tables, style.

Descriptive only (Phase 2): counts, rates and cross-tabs. Standard errors printed here are
naive binomial errors that ignore clustering by game; they are for scale, not inference.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
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
    plt.close(fig)
    print(f"wrote reports/figures/{name}.png")


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
