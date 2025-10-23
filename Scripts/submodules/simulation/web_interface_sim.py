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
import pathlib
from typing import Dict

# Ensure the Scripts folder is used as the base directory for imports and paths.
# This makes the script resilient regardless of the current working directory.
_here = pathlib.Path(__file__).resolve()
_scripts_dir = None
for p in _here.parents:
    if p.name == "Scripts":
        _scripts_dir = p
        break
if _scripts_dir is None:
    # Fallback if running from an unexpected location; assume three levels up
    # .../Scripts/submodules/simulation/web_interface_sim.py
    _scripts_dir = _here.parent.parent.parent

# Add Scripts to sys.path so we can import via `submodules...`
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from submodules.simulation.so100_follower_sim import (  # type: ignore
    SO100FollowerConfig,
    SO100Follower,
)


def _load_web_interface_create_app():
    """Import create_app from WebInterface with a compatible import path.

    The WebInterface package uses absolute imports like `from routes import ...`,
    so we temporarily add its directory to sys.path and import `interface`.
    """
    import importlib

    # WebInterface lives under Scripts/submodules/WebInterface
    web_dir = _scripts_dir / "submodules" / "WebInterface"
    if str(web_dir) not in sys.path:
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

    # No background thread here: SO100FollowerSim manages stepping internally

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
        # Forward UI values (degrees) directly to the simulator follower
        robot.send_action(dict(values))

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
        robot.disconnect()


if __name__ == "__main__":
    main()
