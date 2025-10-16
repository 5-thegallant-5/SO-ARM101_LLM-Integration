import sys
import time
import argparse
from pathlib import Path
from lerobot.robots.so100_follower import SO100FollowerConfig, SO100Follower
from submodules.config_module.config_handler import get_config
from submodules.motion_utils import send_action_ramped


CONFIG = {}


def main(robot: SO100Follower, use_ramped: bool):
    # pos = robot.get_observation()
    # app = start_web_interface(send_action_callback, pos)
    # app.run()
    # Get current position
    print(robot.get_observation())

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
    if use_ramped:
        send_action_ramped(robot, action, speed=CONFIG.get('default_speed', 0.5))
    else:
        robot.send_action(action)
    input() # Wait

    # Get current position
    print(robot.get_observation())
    input() # Wait

    

def robot_rest(robot: SO100Follower, use_ramped: bool):
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
    
    if use_ramped:
        send_action_ramped(robot, pre_rest, speed=CONFIG.get('default_speed', 0.5))
    else:
        robot.send_action(pre_rest)
    time.sleep(3)
    if use_ramped:
        send_action_ramped(robot, true_rest, speed=CONFIG.get('default_speed', 0.5))
    else:
        robot.send_action(true_rest)
    time.sleep(3)



def setup_robot(torque: bool  = True):
    """
    Create connection to the SO-ARM100
    """
    
    # Set robot config
    # Resolve calibration directory relative to this file (Scripts)
    scripts_dir = Path(__file__).resolve().parent
    calibration_dir = scripts_dir / "config_files/arm_calibration/"
    robot_config = SO100FollowerConfig(
        # Get port from config file
        port=CONFIG['device_port'],
        id="robot",
        calibration_dir=calibration_dir,
    )
    
    robot = SO100Follower(robot_config)
    robot.connect()
    print("Robot Connected")
    
    # Check if torque needs to be disabled
    if not torque:
        robot.bus.disable_torque()
    
    return (robot, robot_config)



def send_action_ramped(robot: SO100Follower, target: dict, speed: float = 0.5, steps: int | None = None) -> None:
    """
    Move robot towards target positions with simple linear interpolation.
    speed in [0,1] controls total movement duration (slower near 0).
    """
    # Clamp speed to a safe range
    s = max(0.01, min(1.0, float(speed)))
    # Map speed to duration: 0.01 -> ~4.95s, 1.0 -> 1.0s
    total_duration = 1.0 + (1.0 - s) * 4.0
    dt = 0.05  # 20 Hz
    n_steps = steps if steps is not None else max(1, int(total_duration / dt))

    # Read current observation (assumes same keys present)
    current = robot.get_observation()
    keys = target.keys()
    start = {k: current.get(k, 0.0) for k in keys}

    for i in range(1, n_steps + 1):
        alpha = i / n_steps
        interp = {k: start[k] + (target[k] - start[k]) * alpha for k in keys}
        robot.send_action(interp)
        time.sleep(dt)





def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SO-ARM100 controller")
    torq_group = parser.add_mutually_exclusive_group()
    torq_group.add_argument("--torque", dest="torque", action="store_true", help="Enable torque (default)")
    torq_group.add_argument("--no-torque", dest="torque", action="store_false", help="Disable torque")
    parser.set_defaults(torque=None)
    parser.add_argument("--calibration-file", dest="calibration_file", type=str, default=None,
                        help="Override calibration file name (e.g., robot.json)")
    parser.add_argument("--device-port", dest="device_port", type=str, default=None,
                        help="Override device port (e.g., /dev/ttyUSB0)")
    ramp_group = parser.add_mutually_exclusive_group()
    ramp_group.add_argument("--ramped", dest="ramped", action="store_true", help="Use ramped motion (interpolated)")
    ramp_group.add_argument("--no-ramped", dest="ramped", action="store_false", help="Use direct motion (immediate)")
    parser.set_defaults(ramped=None)
    return parser.parse_args()


def should_use_ramped(args: argparse.Namespace) -> bool:
    # Default to ramped if not explicitly disabled
    return True if args.ramped is None else bool(args.ramped)


def run_controller(args: argparse.Namespace) -> int:
    global CONFIG
    overrides = {
        "torque": args.torque,
        "calibration_file": args.calibration_file,
        "device_port": args.device_port,
    }
    CONFIG = get_config(overrides=overrides)

    if not CONFIG.get("device_port"):
        print("No device port configured. Skipping robot connection and exiting.")
        return 0

    robot, _ = setup_robot(torque=CONFIG.get('torque', True))
    use_ramped = should_use_ramped(args)
    try:
        main(robot, use_ramped)
        robot_rest(robot, use_ramped)
    finally:
        robot.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(run_controller(parse_args()))
