# Raw experiment outputs

Everything here was produced by `traffic-drl sweep|compare|train` or a script in `scripts/`; the tables in
`docs/results_final.md` and `docs/results_generalist_v2.md` are built from it (`python scripts/build_results.py`).
New runs should write here too (the CLI defaults point at `results/`).

| Folder | Contents |
|---|---|
| `comparisons/<name>/` | `traffic-drl compare` outputs: `compare_summary.csv/.md`, `compare_episodes.csv`. `general` = held-out generalist test, `grid` = demand-by-unevenness regime map, `kt*` = Kathmandu-style traffic, `dq*` = trained specialists |
| `sweeps/<name>/` | `traffic-drl sweep` outputs (`sweep_summary.csv`, `sweep_runs.csv`, `runs/` checkpoints). `first` is the original sweep; `rush_a/b/c`, `tidal`, `mixed*` are early DQN recipes; `v*` are the later recipes (`vd` = learning from demonstrations) |
| `training/` | single training runs and smoke tests (`train10*`, `dqn_rush`, `v2_quick`, `qtable_smoke`, `dqn_smoke`) |
| `tuning/actuated/` | tuning of the density rule on selection seeds |
