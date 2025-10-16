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
        while not stop_evt.is_set():
            try:
                if robot.sim is None:
                    time.sleep(1.0 / 240.0)
                    continue

                # Snapshot latest desired action
                with action_lock:
                    desired = dict(latest_action)

                # Apply desired action directly without rate limiting
                applied_action = desired
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
