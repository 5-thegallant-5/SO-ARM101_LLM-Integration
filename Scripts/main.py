import time
from pathlib import Path
from lerobot.robots.so100_follower import SO100FollowerConfig, SO100Follower
from submodules.config_module.config_handler import get_config


CONFIG = {}


def main(robot: SO100Follower):
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

    # Set robot to the zero position
    robot.send_action(action)
    input() # Wait

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



def setup_robot(torque: bool  = True):
    """
    Create connection to the SO-ARM100
    """
    
    # Set robot config
    # Resolve calibration directory relative to this file (Scripts)
    scripts_dir = Path(__file__).resolve().parent
    robot_config = SO100FollowerConfig(
        # Get port from config file
        port=CONFIG['device_port'],
        id="robot",
        calibration_dir=scripts_dir / "config_files/arm_calibration/",
    )
    
    robot = SO100Follower(robot_config)
    robot.connect()
    print("Robot Connected")
    
    # Check if torque needs to be disabled
    if not torque:
        robot.bus.disable_torque()
    
    return (robot, robot_config)





if __name__ == "__main__":
    # Load config via centralized handler
    CONFIG = get_config()

    # If no device port is configured or discovery failed, skip connection cleanly
    if not CONFIG.get("device_port"):
        print("No device port configured. Skipping robot connection and exiting.")
        raise SystemExit(0)

    # Set robot config and connect
    robot, r_config = setup_robot(torque=False)

    # Run main script
    main(robot)

    # Set to rest position
    robot_rest(robot)

    # Disconnect from arm
    robot.disconnect()
