"""The client-style traffic pool: valid, reproducible, covering, and kept apart (train / select / test)."""
import json
import os

import pytest

from traffic_drl import intake, pool

ROOT = os.path.join(os.path.dirname(__file__), "..")
POOL = os.path.join(ROOT, "configs", "scenarios", "client_pool")


def _peak(spec):
    periods = spec["demand"] if isinstance(spec["demand"], list) else [spec["demand"]]
    return max(max(p[a] for a in intake.APPROACHES) for p in periods)


def test_every_drawn_spec_is_a_valid_client_spec():
    for spec in pool.draw_specs(30, 101, "t") + pool.preset_specs():
        intake.preview(spec)          # raises SpecError if a client could not have entered it


def test_draws_are_reproducible_and_seed_dependent():
    assert pool.draw_specs(12, 5, "x") == pool.draw_specs(12, 5, "x")
    assert pool.draw_specs(12, 5, "x") != pool.draw_specs(12, 6, "x")


def test_pool_covers_quiet_to_near_capacity_mixed_fleets_turns_and_flipping():
    specs = pool.draw_specs(30, 101, "t")
    peaks = [_peak(s) for s in specs]
    assert min(peaks) < 200 and max(peaks) > 1000            # the earlier pool had nothing this quiet
    assert any(s["vehicle_mix"] == "cars" for s in specs) and any(isinstance(s["vehicle_mix"], dict) for s in specs)
    assert any("turns" in s for s in specs) and any(isinstance(s["demand"], list) for s in specs)
    assert all(abs(sum(s["vehicle_mix"].values()) - 1) < 0.01 for s in specs if isinstance(s["vehicle_mix"], dict))


def test_every_scenario_lasts_thirty_minutes():
    for s in pool.draw_specs(12, 7, "t") + pool.preset_specs():
        periods = s["demand"] if isinstance(s["demand"], list) else None
        assert (sum(p["minutes"] for p in periods) if periods else s["duration_minutes"]) == 30


def test_write_pool_creates_loadable_scenarios(tmp_path):
    from traffic_drl.config import load_scenario

    paths = pool.write_pool(str(tmp_path), pool.draw_specs(3, 1, "w"))
    assert len(paths) == 3 and all(load_scenario(p)["route_file"].endswith(".rou.xml") for p in paths)
    assert (tmp_path / "specs.json").exists()


@pytest.mark.skipif(not os.path.isdir(POOL), reason="pool not generated")
def test_shipped_splits_are_disjoint_and_match_their_seeds():
    names, specs_by_split = {}, {}
    for split in ("train", "select", "test"):
        specs = json.load(open(os.path.join(POOL, split, "specs.json")))
        specs_by_split[split] = specs
        names[split] = {s["name"] for s in specs}
    assert not (names["train"] & names["select"]) and not (names["train"] & names["test"]) and not (names["select"] & names["test"])
    # no demand pattern is shared between a training scenario and a held-out one
    key = lambda s: json.dumps([s["demand"], s["vehicle_mix"], s.get("turns")], sort_keys=True)   # noqa: E731
    train_keys = {key(s) for s in specs_by_split["train"]}
    assert not any(key(s) in train_keys for s in specs_by_split["select"] + specs_by_split["test"])
    assert pool.draw_specs(30, 101, "train") == specs_by_split["train"]            # regenerating gives the same files
    assert len(specs_by_split["test"]) == 12 + len(pool.PRESETS)
