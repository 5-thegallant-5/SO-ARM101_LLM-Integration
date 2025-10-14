from flask import Flask

def create_app(onUpdate = None, current_positions = None):
    app = Flask(__name__)
    from .routes import register_routes
    register_routes(app, onUpdate, current_positions)

    return app

app = create_app()
