import time
import os
import yaml
import argparse
from pathlib import Path
from typing import Any, Tuple, Type


CONFIG_VARS = {
    "device_port": ""
}


def main():
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


def robot_rest(robot: Any):
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


def get_config():
    """
    Config handler:
        - Checks if there is an existing config file
        - Creates a config file if none exists
        - Attempts to load file
        - If port does not exist in file, automatically scans and retrieves the port
        - Sets global var device_port to the correct port, before saving into file
    """
    global CONFIG_VARS
    
    print("Loading config")    
    
    # Check for config file
    if not os.path.exists("./config_files/config.yaml"):
        print("No config.yaml file found - creating new file.")
        with open("./config_files/config.yaml", mode="w") as file:
            yaml.safe_dump(CONFIG_VARS, file)
            file.close()
    
    # Try to load config file
    try:
        with open("./config_files/config.yaml", mode="r+") as file:
            config = yaml.safe_load(file)
            
            # Case where device port is an empty string in the YAML file:
            if config["device_port"] == "":
                print("Parameter 'device_port' is empty in 'config.yaml'. Starting port configuration...")
                CONFIG_VARS["device_port"] = find_port()
                
                # Save the result into the file
                file.seek(0)
                yaml.safe_dump(CONFIG_VARS, file)
                
            
            # Case where device port is in the YAML file: 
            else:
                CONFIG_VARS["device_port"] = config["device_port"]
                print(f"Using port {CONFIG_VARS['device_port']} from config.yaml.")

            # Close config.yaml
            file.close()
                
    except Exception as e:
        print("ERROR:", e)



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


def setup_robot(torque: bool = True, use_sim: bool = False):
    """
    Create connection to the SO-ARM100
    """
    SO100FollowerConfig, SO100Follower = _select_backend(use_sim)

    # For simulation, the port value is ignored by the shim but required by the dataclass
    port = "SIM" if use_sim else CONFIG_VARS["device_port"]

    # Optional GUI override for simulation via env var SO100_SIM_GUI ("0" to disable)
    sim_gui = not (os.getenv("SO100_SIM_GUI") in {"0", "false", "False"})

    # Set robot config
    # Both backends accept id and (optionally) calibration_dir; the sim ignores it.
    kwargs: dict = dict(
        port=port,
        id="robot",
        calibration_dir=Path("./config_files/arm_calibration/"),
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



def find_port():
    """
    Find USB port of robot and set global device_port variable.
    Modified from find_port.py from LeRobot library
    """
    # Lazy import to avoid requiring lerobot when running simulation only
    import lerobot.find_port as fp

    print("\nPlease ensure the robot is connected via USB cable. Once done, press Enter.")
    input()
    print("Finding all available ports for the MotorsBus.")
    ports_before = fp.find_available_ports()
    print("Ports registered. Remove the USB cable from your MotorsBus and press Enter when done.")
    input()  # Wait for user to disconnect the device

    time.sleep(0.5)  # Allow some time for port to be released
    ports_after = fp.find_available_ports()
    ports_diff = list(set(ports_before) - set(ports_after))

    if len(ports_diff) == 1:
        port = ports_diff[0]
        print(f"The port of this MotorsBus is '{port}'")
        print("Reconnect the USB cable and press Enter.")
        input() # Wait for the user to reconnect the device
        return port
    elif len(ports_diff) == 0:
        raise OSError(
            f"Could not detect the port. No difference was found ({ports_diff})."
        )
    else:
        raise OSError(
            f"Could not detect the port. More than one port was found ({ports_diff})."
        )




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SO-ARM100 runner (real or simulation)")
    parser.add_argument("--sim", action="store_true", help="Use simulation backend instead of hardware")
    parser.add_argument(
        "--sim-gui",
        choices=["0", "1"],
        help="Override simulation GUI (1=on, 0=off). Only used with --sim.",
    )
    parser.add_argument(
        "--torque",
        dest="torque",
        action="store_true",
        help="Enable torque on hardware (ignored in simulation).",
    )
    parser.add_argument(
        "--no-torque",
        dest="torque",
        action="store_false",
        help="Disable torque on hardware (default).",
    )
    parser.set_defaults(torque=False)

    args = parser.parse_args()

    # If simulation requested, optionally override GUI with env var
    if args.sim and args.sim_gui is not None:
        os.environ["SO100_SIM_GUI"] = args.sim_gui

    # Load config only when targeting hardware
    if not args.sim:
        get_config()

    # Set robot config
    robot, r_config = setup_robot(torque=args.torque, use_sim=bool(args.sim))

    # Run main script
    main()

    # Set to rest position
    robot_rest(robot)

    # Disconnect from arm
    robot.disconnect()
