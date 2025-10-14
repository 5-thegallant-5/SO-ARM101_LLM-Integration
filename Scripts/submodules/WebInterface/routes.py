from flask import render_template, request, jsonify

def register_routes(app, onUpdate, current_positions):
    @app.route("/")
    def index():
        return render_template("index.html", current_positions)

    @app.route("/update", methods=["POST"])
    def update():
        data = request.get_json(force=True) or {}
        values = {k: float(v) if v is not None else None for k, v in data.items()}
        # print("Received slider values:", values)
        
        # If an 'onUpdate' function is provided, call that function, using the values as a parameter
        if onUpdate is not None:
            onUpdate(values)
            
        return jsonify(success=True)
