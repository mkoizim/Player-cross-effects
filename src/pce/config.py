"""Paths and pinned configuration."""
from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = tomllib.loads((ROOT / "config.toml").read_text())

RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "reports" / "figures"
TABLES = ROOT / "reports" / "tables"

RETROSHEET = RAW / "retrosheet"
CHADWICK_SRC = RAW / "chadwick-src"
CHADWICK = RAW / "chadwick"

SEASONS = list(range(CFG["seasons"]["first"], CFG["seasons"]["last"] + 1))


def era(season):
    """Era label used throughout the descriptive work (DESIGN.md section 4.2)."""
    if season <= 2014:
        return "2000–14"
    if season <= 2019:
        return "2015–19"
    if season == 2020:
        return "2020"
    return "2021–25"


ERAS = ["2000–14", "2015–19", "2020", "2021–25"]
