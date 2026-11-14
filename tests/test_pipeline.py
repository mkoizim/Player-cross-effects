"""Checks on parsed and derived tables. Run after `make data`."""
import numpy as np
import pandas as pd
import pytest

from pce.config import INTERIM, PROCESSED, SEASONS

pytestmark = pytest.mark.skipif(not (PROCESSED / "pa.parquet").exists(), reason="run `make data` first")


@pytest.fixture(scope="module")
def pa():
    return pd.read_parquet(PROCESSED / "pa.parquet")


@pytest.fixture(scope="module")
def lineup():
    return pd.read_parquet(PROCESSED / "lineup.parquet")


def test_pa_totals_match_retrosheet_game_logs(pa):
    """Independent check: event-file PAs equal AB+BB+HBP+SH+SF+CI from the game logs, every season."""
    gl = pd.concat([pd.read_parquet(INTERIM / f"gamelog_{s}.parquet") for s in SEASONS])
    ours = pa.groupby("season").size()
    theirs = gl.groupby("season").pa.sum()
    assert (ours == theirs.reindex(ours.index)).all()


def test_team_pa_match_game_logs_by_team_season(pa):
    gl = pd.concat([pd.read_parquet(INTERIM / f"gamelog_{s}.parquet") for s in SEASONS])
    ours = pa.groupby(["season", "bat_team"]).size()
    theirs = gl.groupby(["season", "team"]).pa.sum()
    theirs.index.names = ours.index.names
    assert (ours == theirs.reindex(ours.index)).all()


def test_game_counts(pa):
    n = pa.groupby("season").game_id.nunique()
    assert n[2020] == 898
    assert n.drop(2020).between(2426, 2431).all()


def test_lineups_complete(lineup):
    assert len(lineup) % 9 == 0
    assert lineup.stype.isin(["L", "R", "S", "P"]).all()
    assert (lineup.groupby(["game_id", "team"]).slot.nunique() == 9).all()


def test_no_pitchers_batting_under_universal_dh(lineup):
    assert (lineup[lineup.season >= 2022].stype != "P").all()


def test_neighbors_are_cyclic_lineup_lookups(pa, lineup):
    s = pa.sample(5000, random_state=0)
    key = lineup.set_index(["game_id", "team", "slot"]).stype
    for col, off in (("next1_s", 1), ("next2_s", 2), ("prev1_s", -1), ("prev2_s", -2)):
        tgt = (s.slot - 1 + off) % 9 + 1
        want = key.reindex(pd.MultiIndex.from_arrays([s.game_id, s.bat_team, tgt])).to_numpy()
        assert (s[col].to_numpy() == want).all()


def test_linear_weights_ordered_and_scaled(pa):
    w = pd.read_parquet(PROCESSED / "weights.parquet")
    assert (w.w_hr > w.w_3b).all() and (w.w_3b > w.w_2b).all() and (w.w_2b > w.w_1b).all()
    assert (w.w_1b > w.w_hbp).all() and (w.w_hbp > w.w_bb).all() and (w.w_bb > 0.6).all()
    lg = pa.groupby("season").agg(n=("woba_num", "sum"), d=("woba_den", "sum"))
    assert np.allclose(lg.n / lg.d, w.set_index("season").lg_woba, atol=1e-9)


def test_one_starter_per_team_game():
    ap = pd.read_parquet(PROCESSED / "appearances.parquet")
    assert (ap[ap.is_starter].groupby(["game_id", "fld_team"]).size() == 1).all()


def test_three_batter_rule_visible_in_data():
    """Outings the rule forbids were common before 2020 and near zero after (injury exceptions remain)."""
    ap = pd.read_parquet(PROCESSED / "appearances.parquet")
    r = ap[~ap.is_starter & ~ap.position_player].groupby("season").short_stint.mean()
    assert r[r.index <= 2019].min() > 0.03
    assert r[r.index >= 2021].max() < 0.005


def test_talent_uses_prior_seasons_only():
    """A player with no earlier season in the data must sit exactly at his group mean."""
    t = pd.read_parquet(PROCESSED / "talent_bat.parquet")
    first = t[t.season == t.season.min()]
    assert (first.prior_n == 0).all()
    assert (first.groupby("grp").overall.nunique() == 1).all()


def test_expected_matchup_value_is_calibrated(pa):
    e = pd.read_parquet(PROCESSED / "pa_e2.parquet")
    d = pa.merge(e, on=["season", "game_id", "event_id"])
    d = d[(d.season >= 2003) & (d.woba_den == 1)]
    dec = d.groupby(pd.qcut(d.e2, 10, labels=False)).agg(e2=("e2", "mean"), y=("woba_num", "mean"))
    slope = np.polyfit(dec.e2, dec.y, 1)[0]
    assert 0.85 < slope < 1.1


def test_shapley_is_efficient_and_null_lineup_is_zero():
    from pce.lineup import TERMS, onehot, loadings, shapley, spillover
    rng = np.random.default_rng(0)
    beta = pd.Series(rng.normal(size=len(TERMS)), index=TERMS)
    w = np.linspace(0.9, 1.1, 9)
    q = np.array([0.35, 0.55, 0.10])
    assert spillover("RRRRRRRRR", beta, w) == 0
    for types in ("LRLRSLRRL", "LLLRRRSRR"):
        phi = shapley(types, beta, w, q)
        empty = float(loadings(np.tile(q, (9, 1)), np.full(9, q[0]), w) @ beta.to_numpy())
        assert np.isclose(phi.sum(), spillover(types, beta, w) - empty)
