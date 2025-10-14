from main import *


def main():
    pos = robot.get_observation()
    app = start_web_interface(send_action_callback, pos)
    app.run()
    input() # Wait

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