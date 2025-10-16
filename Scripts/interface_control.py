from main import *
from submodules.WebInterface.interface import create_app


def main():
    pos = robot.get_observation()
    app = start_web_interface(send_action_callback, pos)
    app.run()
    input() # Wait


def start_web_interface(onUpdate, current_pos):
    app = create_app(onUpdate=onUpdate, current_positions=current_pos)
    return app


def send_action_callback(positions):
    robot.send_action(positions)
    

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
    