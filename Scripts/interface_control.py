from main import *
from submodules.WebInterface.interface import create_app
from submodules.WebInterface.routes import *



def main():
    pos = robot.get_observation()
    app = start_web_interface(send_action_callback, pos)
    try:
        app.run()
    finally:
        robot_rest(robot)
        robot.disconnect()


def start_web_interface(onUpdate, current_pos):
    app = create_app(onUpdate=onUpdate, current_positions=current_pos)
    return app


def send_action_callback(positions):
    robot.send_action(positions)
    

if __name__ == "__main__":
    # Load config file
    CONFIG = get_config()
    print(CONFIG)
    
    # Set robot config
    robot, r_config = setup_robot(config=CONFIG)

    # Run main script
    main()