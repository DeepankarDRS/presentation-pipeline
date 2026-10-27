"""Chart node free replay: scripts.node_replay --kind chart (kept for the commands in docs/eval/chart-node/)."""

import sys

from scripts import node_replay

if __name__ == "__main__":
    if "--kind" not in sys.argv:
        sys.argv[1:1] = ["--kind", "chart"]
    raise SystemExit(node_replay.main())
