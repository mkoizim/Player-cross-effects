"""Parse Retrosheet regular-season event files with the Chadwick tools.

Outputs, per season, in data/interim/:
  events_YYYY.parquet   one row per event (cwevent), selected columns
  games_YYYY.parquet    one row per game (cwgame): date, teams, starters, lineups
  roster_YYYY.parquet   one row per player-team: bats, throws, listed position
  gamelog_YYYY.parquet  Retrosheet game log team batting totals (validation only)
"""
from __future__ import annotations

import io
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

from .config import CHADWICK, INTERIM, RETROSHEET, SEASONS

EVENT_COLS = [
    "GAME_ID", "INN_CT", "BAT_HOME_ID", "OUTS_CT", "AWAY_SCORE_CT", "HOME_SCORE_CT",
    "BAT_ID", "BAT_HAND_CD", "PIT_ID", "PIT_HAND_CD", "PH_FL", "BAT_FLD_CD",
    "BAT_LINEUP_ID", "EVENT_CD", "BAT_EVENT_FL", "AB_FL", "H_CD", "SH_FL", "SF_FL",
    "EVENT_OUTS_CT", "EVENT_ID", "BAT_TEAM_ID", "FLD_TEAM_ID", "INN_PA_CT",
    "START_BASES_CD", "END_BASES_CD", "EVENT_RUNS_CT", "FATE_RUNS_CT",
]
FLAG_COLS = ["PH_FL", "BAT_EVENT_FL", "AB_FL", "SH_FL", "SF_FL"]

# Retrosheet game-log layout (1-indexed field numbers from the published spec).
GL_FIELDS = {"date": 1, "away": 4, "home": 7}
GL_OFF = {"ab": 0, "sh": 6, "sf": 7, "hbp": 8, "bb": 9, "ci": 15}  # offsets from AB
GL_AWAY_AB, GL_HOME_AB = 22, 50


def _cw(tool: str, season: int, args: list[str]) -> pd.DataFrame:
    d = RETROSHEET / "seasons" / str(season)
    files = sorted(p.name for p in d.glob(f"{season}*.EV[AN]"))  # regular season only
    env = dict(os.environ, LD_LIBRARY_PATH=str(CHADWICK / "lib"))
    out = subprocess.run(
        [str(CHADWICK / "bin" / tool), "-q", "-n", "-y", str(season), *args, *files],
        cwd=d, env=env, check=True, capture_output=True,
    ).stdout
    return pd.read_csv(io.BytesIO(out), low_memory=False)


def parse_season(season: int) -> str:
    INTERIM.mkdir(parents=True, exist_ok=True)

    ev = _cw("cwevent", season, ["-f", "0-96", "-x", "0-62"])[EVENT_COLS]
    for c in FLAG_COLS:
        ev[c] = ev[c] == "T"
    ev.columns = [c.lower() for c in ev.columns]
    ev.insert(0, "season", season)
    ev.to_parquet(INTERIM / f"events_{season}.parquet", index=False)

    gm = _cw("cwgame", season, [])
    keep = ["GAME_ID", "GAME_DT", "GAME_CT", "AWAY_TEAM_ID", "HOME_TEAM_ID", "PARK_ID",
            "AWAY_START_PIT_ID", "HOME_START_PIT_ID", "INN_CT"]
    keep += [c for c in gm.columns if "_LINEUP" in c]
    gm = gm[keep]
    gm.columns = [c.lower() for c in gm.columns]
    gm.insert(0, "season", season)
    gm.to_parquet(INTERIM / f"games_{season}.parquet", index=False)

    d = RETROSHEET / "seasons" / str(season)
    ros = pd.concat(
        [pd.read_csv(p, header=None, names=["player_id", "last", "first", "bats", "throws", "team", "pos"])
         for p in sorted(d.glob("*.ROS"))],
        ignore_index=True,
    )
    ros.insert(0, "season", season)
    ros.to_parquet(INTERIM / f"roster_{season}.parquet", index=False)

    gl_path = next(p for p in d.iterdir() if p.name.upper() == f"GL{season}.TXT")  # case varies by season
    gl = pd.read_csv(gl_path, header=None, low_memory=False)
    rows = []
    for side, ab0 in (("away", GL_AWAY_AB), ("home", GL_HOME_AB)):
        t = pd.DataFrame({"date": gl[GL_FIELDS["date"] - 1], "team": gl[GL_FIELDS[side] - 1]})
        for k, off in GL_OFF.items():
            t[k] = pd.to_numeric(gl[ab0 - 1 + off], errors="coerce").fillna(0).astype(int)
        rows.append(t)
    glt = pd.concat(rows, ignore_index=True)
    glt["pa"] = glt[list(GL_OFF)].sum(axis=1)
    glt.insert(0, "season", season)
    glt.to_parquet(INTERIM / f"gamelog_{season}.parquet", index=False)

    return f"{season}: {len(ev):>7,} events  {len(gm):>5,} games"


def main() -> None:
    with ProcessPoolExecutor(max_workers=4) as ex:
        for msg in ex.map(parse_season, SEASONS):
            print(msg)


if __name__ == "__main__":
    main()
