"""
Standalone simulator that exposes a `robot` object compatible with
`robot.send_action({...})` and `robot.get_observation()` used across the repo.

You can either import this module and use `robot` directly, or run it as a
script to open the GUI and step the simulation.

Import usage:
    from simulation import robot, send_action
    robot.send_action({"shoulder_pan.pos": 0, ...})

Interactive CLI (multithreaded):
    python simulation.py                   # GUI by default
    SO100_SIM_GUI=0 python simulation.py   # headless
  - Commands while running (type and press Enter):
    * set shoulder_pan=10 elbow_flex=-20 wrist_roll=5
    * set shoulder_pan 10 shoulder_lift -5 gripper 30
    * obs    (print current observation)
    * zero   (center arm joints)
    * quit   (exit)
"""

from __future__ import annotations

import argparse
import json
import os
import time
import threading
from typing import Dict, Tuple

from submodules.simulation.so100_follower_sim import SO100FollowerConfig, SO100Follower


# Create a global, connected robot instance using the simulation backend.
# The SO100Follower shim now runs a background stepping thread that
# rate-limits toward desired targets and advances physics at cfg.time_step.
robot_config = SO100FollowerConfig(
    port="SIM",
    id="robot",
    gui=(os.getenv("SO100_SIM_GUI") not in {"0", "false", "False"}),
)
robot = SO100Follower(robot_config)
robot.connect()


def send_action(action: Dict[str, float]) -> None:
    """Convenience passthrough for code that expects a module-level function."""
    robot.send_action(action)


def main() -> None:
    ap = argparse.ArgumentParser(description="SO-ARM100 simulation runner")
    ap.add_argument("--direct", action="store_true", help="Headless mode (no GUI)")
    ap.add_argument("--seconds", type=float, default=0, help="Run for N seconds (0: run until Ctrl+C)")
    args = ap.parse_args()

    if args.direct:
        os.environ["SO100_SIM_GUI"] = "0"

    def apply_delta(pairs: Dict[str, float]):
        # normalize keys to include .pos if missing
        norm: Dict[str, float] = {}
        for k, v in pairs.items():
            key = k if k.endswith(".pos") else f"{k}.pos"
            norm[key] = float(v)
        # The background stepping thread in the shim will consume desired targets
        robot.send_action(norm)

    def center_arm():
        # Zero for arm joints means middle due to shim calibration
        apply_delta({
            "shoulder_pan": 0,
            "shoulder_lift": 0,
            "elbow_flex": 0,
            "wrist_flex": 0,
            "wrist_roll": 0,
        })

    def parse_set_args(tokens: Tuple[str, ...]) -> Dict[str, float]:
        # Supports key=value pairs or key value pairs
        out: Dict[str, float] = {}
        if any("=" in tok for tok in tokens):
            for tok in tokens:
                if "=" in tok:
                    k, v = tok.split("=", 1)
                    out[k] = float(v)
        else:
            if len(tokens) % 2 != 0:
                print("Expected even number of tokens for 'set': key value [key value]...")
                return {}
            it = iter(tokens)
            for k in it:
                v = next(it)
                out[k] = float(v)
        return out

    print("Interactive simulation running. Type 'help' for commands. Ctrl+C to exit.")
    start = time.time()
    try:
        while True:
            if args.seconds and (time.time() - start) >= args.seconds:
                break
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            if line.lower() in {"quit", "exit", "q"}:
                break
            if line.lower() in {"help", "h"}:
                print("Commands:\n  set k=v [k=v...]  or  set k v [k v ...]\n  obs  (print observation)\n  zero (center arm joints)\n  quit")
                continue
            if line.lower() in {"obs", "o"}:
                print(robot.get_observation())
                continue
            if line.lower() in {"zero", "center"}:
                center_arm()
                continue
            if line.lower().startswith("json "):
                try:
                    payload = json.loads(line[5:])
                    if isinstance(payload, dict):
                        apply_delta({str(k): float(v) for k, v in payload.items()})
                    else:
                        print("JSON must be an object of key: value pairs")
                except Exception as e:
                    print("Invalid JSON:", e)
                continue
            if line.lower().startswith("set "):
                toks = tuple(line.split()[1:])
                try:
                    changes = parse_set_args(toks)
                    if changes:
                        apply_delta(changes)
                except Exception as e:
                    print("Invalid set command:", e)
                continue
            print("Unknown command. Type 'help'.")
    finally:
        robot.disconnect()


if __name__ == "__main__":
    main()
