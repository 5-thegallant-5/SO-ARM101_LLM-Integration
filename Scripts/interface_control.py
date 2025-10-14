import lerobot.find_port as fp
import time
import os
import yaml
from pathlib import Path
from lerobot.robots.so100_follower import SO100FollowerConfig, SO100Follower
from submodules.WebInterface.interface import create_app


CONFIG_VARS = {
    "device_port": ""
}


def main():
    pos = robot.get_observation()
    app = start_web_interface(send_action_callback, pos)
    app.run()
    input() # Wait


def send_action_callback(positions):
    robot.send_action(positions)
    

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



def setup_robot(torque: bool  = True):
    """
    Create connection to the SO-ARM100
    """
    
    # Set robot config
    robot_config = SO100FollowerConfig(
        # Get port from config variables
        port=CONFIG_VARS['device_port'],
        id="robot",
        calibration_dir=Path("./config_files/arm_calibration/"),
    )
    
    robot = SO100Follower(robot_config)
    robot.connect()
    print("Robot Connected")
    
    # Check if torque needs to be disabled
    if not torque:
        robot.bus.disable_torque()
    
    return (robot, robot_config)



def find_port():
    """
    Find USB port of robot and set global device_port variable.
    Modified from find_port.py from LeRobot library
    """
    
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


def start_web_interface(onUpdate, current_pos):
    app = create_app(onUpdate=onUpdate, current_positions=current_pos)
    return app
 

if __name__ == "__main__":
    # Load config file
    get_config()
    
    # Set robot config
    robot, r_config = setup_robot()

    # Run main script    
    main()

    # Set to rest position
    robot_rest(robot)
    
    # Disconnect from arm
    robot.disconnect()