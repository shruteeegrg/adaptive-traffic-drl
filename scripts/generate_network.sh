#!/usr/bin/env bash
# Regenerates the single 4-arm signalized intersection network from plain
# node/edge XML, using SUMO's netconvert tool.
#
# The generated intersection.net.xml IS committed to the repo (so nobody
# needs SUMO installed just to read/diff it), but the plain-XML source and
# the command that built it live here so the network is reproducible and
# auditable rather than a hand-edited or mystery binary-ish blob.
#
# Layout: one traffic-light-controlled junction "A1" at the centre, with
# four boundary "spawn/despawn" junctions at the ends of each arm:
#   B1 = east, B2 = north, B3 = west, B4 = south.
#
# Usage: ./scripts/generate_network.sh [output_path]
set -euo pipefail

OUT="${1:-configs/intersection.net.xml}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cat > "$TMP_DIR/intersection.nod.xml" <<'EOF'
<nodes>
    <node id="A1" x="0" y="0" type="traffic_light"/>
    <node id="B1" x="100" y="0" type="priority"/>
    <node id="B2" x="0" y="100" type="priority"/>
    <node id="B3" x="-100" y="0" type="priority"/>
    <node id="B4" x="0" y="-100" type="priority"/>
</nodes>
EOF

cat > "$TMP_DIR/intersection.edg.xml" <<'EOF'
<edges>
    <edge id="A1B1" from="A1" to="B1" numLanes="1" speed="13.9"/>
    <edge id="B1A1" from="B1" to="A1" numLanes="1" speed="13.9"/>
    <edge id="A1B2" from="A1" to="B2" numLanes="1" speed="13.9"/>
    <edge id="B2A1" from="B2" to="A1" numLanes="1" speed="13.9"/>
    <edge id="A1B3" from="A1" to="B3" numLanes="1" speed="13.9"/>
    <edge id="B3A1" from="B3" to="A1" numLanes="1" speed="13.9"/>
    <edge id="A1B4" from="A1" to="B4" numLanes="1" speed="13.9"/>
    <edge id="B4A1" from="B4" to="A1" numLanes="1" speed="13.9"/>
</edges>
EOF

netconvert \
  --node-files="$TMP_DIR/intersection.nod.xml" \
  --edge-files="$TMP_DIR/intersection.edg.xml" \
  --tls.default-type=static \
  -o "$OUT"

echo "Wrote $OUT"
