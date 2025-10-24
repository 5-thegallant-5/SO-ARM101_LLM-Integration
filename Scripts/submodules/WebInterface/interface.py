from flask import Flask
import logging


def create_app(onUpdate = None, current_positions = None):
    app = Flask(__name__)
    
    from submodules.WebInterface.routes import register_routes
    register_routes(app, onUpdate, current_positions)

    return app



if __name__ == "__main__":
    default_positions = {
        "shoulder_pan.pos": 0,
        "shoulder_lift.pos": 0,
        "elbow_flex.pos": 0,
        'wrist_flex.pos': 0,
        "wrist_roll.pos": 0,
        "gripper.pos": 0,
    }

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    app = create_app(current_positions=default_positions)
    app.run()