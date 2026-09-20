## intersection.net.xml / intersection.rou.xml / intersection.sumocfg

The SUMO network, demand, and simulation-config files for the single
4-arm signalized intersection. These are generated, not hand-edited --
see `scripts/generate_network.sh` and `scripts/generate_routes.py` at the
repo root. Regenerate with:

```bash
export SUMO_HOME=/usr/share/sumo   # or wherever `brew --prefix sumo` points
bash scripts/generate_network.sh configs/intersection.net.xml
python3 scripts/generate_routes.py --out configs/intersection.rou.xml --vehs-per-hour 300
```

## intersection.yaml

The config `traffic_drl/env/traci_env.py` actually reads: which files to
use, the traffic light id, phase indices, step length/episode length, and
the list of approaches (name + incoming edge) the environment reads queue
length from. This is the file to edit to point the environment at a
different network -- not the Python code.

## scenarios/

Named traffic-demand scenarios (`rush_hour.yaml`, `low_traffic.yaml`),
each with its own generated `.rou.xml` (same network, different demand
level), used by `traffic-drl evaluate`/`compare` and the demo app from
Week 8 onward.
