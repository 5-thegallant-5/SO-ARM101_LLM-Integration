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


# Create a global, connected robot instance using the simulation backend
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

    # Shared state for interactive updates
    action_lock = threading.Lock()
    latest_action: Dict[str, float] = robot.get_observation().copy()
    # What we actually apply to the simulator each step (starts at current obs)
    applied_action: Dict[str, float] = dict(latest_action)
    stop_evt = threading.Event()

    def step_loop():
        nonlocal applied_action
        # Configurable max joint speed in deg/s; defaults to a reasonable rate
        try:
            max_deg_per_s = float(os.getenv("SO100_SIM_MAX_SPEED_DEG_S", "120"))
        except Exception:
            max_deg_per_s = 120.0
        # Determine physics timestep (fallback to 1/240s)
        try:
            dt = float(getattr(getattr(robot, "sim", None), "time_step", 1.0 / 240.0))
        except Exception:
            dt = 1.0 / 240.0
        max_deg_per_step = max(0.0, max_deg_per_s * dt)

        def _rate_limit(curr: float, target: float, max_step: float) -> float:
            delta = target - curr
            if abs(delta) <= max_step:
                return target
            return curr + max_step * (1.0 if delta > 0 else -1.0)

        while not stop_evt.is_set():
            try:
                if robot.sim is None:
                    time.sleep(1.0 / 240.0)
                    continue
                # Snapshot desired targets
                with action_lock:
                    desired = dict(latest_action)

                # Build next applied action by rate-limiting toward desired
                next_action: Dict[str, float] = dict(applied_action)
                # Ensure we consider all keys present in either map
                for key in set(list(applied_action.keys()) + list(desired.keys())):
                    if not key.endswith(".pos"):
                        continue
                    curr = applied_action.get(key, 0.0)
                    tgt = desired.get(key, curr)
                    next_action[key] = _rate_limit(curr, tgt, max_deg_per_step)

                applied_action = next_action
                # Apply and advance physics exactly once per loop
                robot.send_action(applied_action)
            except Exception:
                time.sleep(1.0 / 240.0)

    t = threading.Thread(target=step_loop, name="sim-step", daemon=True)
    t.start()

    def apply_delta(pairs: Dict[str, float]):
        nonlocal latest_action
        # normalize keys to include .pos if missing
        norm: Dict[str, float] = {}
        for k, v in pairs.items():
            key = k if k.endswith(".pos") else f"{k}.pos"
            norm[key] = float(v)
        with action_lock:
            latest_action.update(norm)

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
        stop_evt.set()
        t.join(timeout=1.0)
        robot.disconnect()


if __name__ == "__main__":
    main()
