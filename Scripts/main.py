import sys
import time
import argparse
import argparse
from pathlib import Path
from typing import Any, Tuple, Type
import os

from lerobot.robots.so100_follower import SO100FollowerConfig, SO100Follower

from submodules.config_module.config_handler import get_config
from submodules.motion_utils import send_action_ramped


CONFIG = {}


def main(robot: SO100Follower):
    print(robot.get_observation())
    input()
    
    # Determine angles for the robot to assume
    action = {
        "shoulder_pan.pos": 0,
        "shoulder_lift.pos": 0,
        "elbow_flex.pos": 0,
        'wrist_flex.pos': 0,
        "wrist_roll.pos": 0,
        "gripper.pos": 0,
    }

    # Set robot to the zero position (ramped or direct)
    robot.send_action(action)

    # Get current position
    print(robot.get_observation())
    input() # Wait

    

def robot_rest(robot: SO100Follower):
    """
    Rest position for robot.
        - Brings the robot to a safe initial position
        - Lowers into a true rest position 
    """
    
    pre_rest = {
        "shoulder_pan.pos": -0.5032350826743368,
        "shoulder_lift.pos": -60.932038834951456,
        "elbow_flex.pos": 61.8659420289855,
        "wrist_flex.pos": 77.70571544385894,
        "wrist_roll.pos": 0.024420024420024333,
        "gripper.pos": 0.5405405405405406,
    }

    true_rest = {
        "shoulder_pan.pos": -0.6470165348670065,
        "shoulder_lift.pos": -88.73786407766991,
        "elbow_flex.pos": 99.54710144927537,
        "wrist_flex.pos": 77.70571544385894,
        "wrist_roll.pos": 0.024420024420024333,
        "gripper.pos": 0.5405405405405406,
    }
    
    robot.send_action(pre_rest)
    time.sleep(3)
    robot.send_action(true_rest)
    time.sleep(3)



def _select_backend(use_sim: bool) -> Tuple[Type[Any], Type[Any]]:
    """
    Return (SO100FollowerConfig, SO100Follower) classes for the desired backend.
    Lazy-imports to avoid pulling in unused dependencies.
    """
    if use_sim:
        from submodules.simulation.so100_follower_sim import (
            SO100FollowerConfig,
            SO100Follower,
        )
    else:
        from lerobot.robots.so100_follower import (
            SO100FollowerConfig,
            SO100Follower,
        )
    return SO100FollowerConfig, SO100Follower


def setup_robot(torque: bool  = True, use_sim: bool = False, config=CONFIG):
    """
    Create connection to the SO-ARM100
    """
    SO100FollowerConfig, SO100Follower = _select_backend(use_sim)

    # For simulation, the port value is ignored by the shim but required by the dataclass
    port = "SIM" if use_sim else config["device_port"]

    # Optional GUI override for simulation via env var SO100_SIM_GUI ("0" to disable)
    sim_gui = not (os.getenv("SO100_SIM_GUI") in {"0", "false", "False"})

    # Set robot config
    # Resolve calibration directory relative to this file (Scripts)
    scripts_dir = Path(__file__).resolve().parent

    kwargs: dict = dict(
        port=port,
        id="robot",
        calibration_dir=scripts_dir / "config_files/arm_calibration/",
    )

    # Only the simulation shim supports a gui flag; add when applicable
    if use_sim:
        kwargs["gui"] = sim_gui

    robot_config = SO100FollowerConfig(**kwargs)

    robot = SO100Follower(robot_config)
    robot.connect()
    print("Robot Connected")
    
    # Check if torque needs to be disabled
    if not torque:
        # The simulation shim exposes a no-op bus.disable_torque for API compatibility
        try:
            robot.bus.disable_torque()
        except Exception:
            pass
    
    return (robot, robot_config)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SO-ARM100 controller")
    torq_group = parser.add_mutually_exclusive_group()
    parser.add_argument("--sim", action="store_true", help="Use simulation backend instead of hardware")
    parser.add_argument(
        "--sim-gui",
        choices=["0", "1"],
        help="Override simulation GUI (1=on, 0=off). Only used with --sim.",
    )
    torq_group.add_argument("--torque", dest="torque", action="store_true", help="Enable torque (default)")
    torq_group.add_argument("--no-torque", dest="torque", action="store_false", help="Disable torque")
    parser.set_defaults(torque=None)
    parser.add_argument("--calibration-file", dest="calibration_file", type=str, default=None,
                        help="Override calibration file name (e.g., robot.json)")
    parser.add_argument("--device-port", dest="device_port", type=str, default=None,
                        help="Override device port (e.g., /dev/ttyUSB0)")
    return parser.parse_args()



def run_controller(args: argparse.Namespace) -> int:
    global CONFIG
    overrides = {
        "torque": args.torque,
        "calibration_file": args.calibration_file,
        "device_port": args.device_port,
    }
    # If simulation requested, optionally override GUI with env var
    if args.sim and args.sim_gui is not None:
        os.environ["SO100_SIM_GUI"] = args.sim_gui

    # Load config only when targeting hardware
    if not args.sim:
        CONFIG = get_config(overrides=overrides)

        if not CONFIG.get("device_port"):
            print("No device port configured. Skipping robot connection and exiting.")
            return 0

    robot, _ = setup_robot(torque=CONFIG.get('torque', True), use_sim=bool(args.sim))
    try:
        main(robot)
    finally:
        robot_rest(robot)
        robot.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(run_controller(parse_args()))
