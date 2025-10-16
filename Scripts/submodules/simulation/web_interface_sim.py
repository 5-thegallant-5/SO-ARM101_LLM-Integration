"""
Launch the existing WebInterface, backed by the SO-ARM100 PyBullet simulator.

This does not modify any entrypoints. It wires the Flask app's update callback
to the simulation shim so you can control the robot from the browser.

Run:
  python submodules/simulation/web_interface_sim.py

Options:
- Set env SO100_SIM_GUI=0 to run the simulator headless (no GUI window).
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Dict

if os.getcwd().endswith("simulation"):
    from so100_follower_sim import SO100FollowerConfig, SO100Follower
else:
    from .so100_follower_sim import SO100FollowerConfig, SO100Follower


def _load_web_interface_create_app():
    """Import create_app from WebInterface with a compatible import path.

    The WebInterface package uses absolute imports like `from routes import ...`,
    so we temporarily add its directory to sys.path and import `interface`.
    """
    import importlib
    import pathlib

    here = pathlib.Path(__file__).resolve()
    web_dir = here.parent.parent / "WebInterface"
    sys.path.insert(0, str(web_dir))
    try:
        interface = importlib.import_module("interface")
        return interface.create_app
    finally:
        # Keep web_dir in sys.path for templates/static resolution.
        pass


def main() -> None:
    # Build simulated robot
    cfg = SO100FollowerConfig(port="SIM", gui=True)
    robot = SO100Follower(cfg)
    robot.connect()

    # Background stepping thread for smoother sim and single-threaded PyBullet access
    stop_evt = threading.Event()
    action_lock = threading.Lock()
    latest_action: Dict[str, float] = robot.get_observation().copy()
    applied_action: Dict[str, float] = dict(latest_action)

    def _step_loop():
        nonlocal applied_action
        # Configurable max joint speed in deg/s (defaults to 120)
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

                # Snapshot latest desired action
                with action_lock:
                    desired = dict(latest_action)

                # Rate-limit toward desired for smooth motion
                next_action: Dict[str, float] = dict(applied_action)
                for key in set(list(applied_action.keys()) + list(desired.keys())):
                    if not key.endswith(".pos"):
                        continue
                    curr = applied_action.get(key, 0.0)
                    tgt = desired.get(key, curr)
                    next_action[key] = _rate_limit(curr, tgt, max_deg_per_step)

                applied_action = next_action
                # Apply and advance one physics step via send_action
                robot.send_action(applied_action)
            except Exception:
                # Keep stepping even if occasional errors occur
                time.sleep(1.0 / 240.0)

    step_thread = threading.Thread(target=_step_loop, name="sim-step", daemon=True)
    step_thread.start()

    # Prepare initial positions for the UI (degrees)
    try:
        current = robot.get_observation()
    except Exception:
        current = {
            "shoulder_pan.pos": 0,
            "shoulder_lift.pos": 0,
            "elbow_flex.pos": 0,
            "wrist_flex.pos": 0,
            "wrist_roll.pos": 0,
            "gripper.pos": 0,
        }

    # Callback to receive slider updates from the UI
    def on_update(values: Dict[str, float]):
        # Values are already numeric from the UI; interpreted as degrees
        # Store for the step thread to apply (avoids multi-threaded PyBullet calls)
        nonlocal latest_action
        with action_lock:
            latest_action = dict(values)

    # Import and start the Flask app
    create_app = _load_web_interface_create_app()
    app = create_app(onUpdate=on_update, current_positions=current)

    try:
        # Reduce Flask werkzeug logs a bit in sim mode
        import logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        # Bind to localhost; change host/port if needed
        app.run(host="127.0.0.1", port=5000)
    finally:
        stop_evt.set()
        step_thread.join(timeout=1.0)
        robot.disconnect()


if __name__ == "__main__":
    main()
