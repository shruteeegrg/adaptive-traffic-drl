SUMO network/route files (`.net.xml`, `.rou.xml`, `.sumocfg`), intersection
layout configs (lane IDs, phases — read by `traffic_drl/env`), and
hyperparameter configs (learning rate, epsilon decay, buffer size, etc.)
go here, added from Week 2 onward.

`scenarios/` holds named traffic-demand scenarios (`rush_hour.yaml`,
`low_traffic.yaml`) used by `traffic-drl evaluate`/`compare` and by the
demo app (Week 8 onward).
