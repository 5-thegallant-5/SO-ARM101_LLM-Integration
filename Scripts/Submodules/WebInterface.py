"""
Flask application with six sliders.

This simple web application uses Flask to serve a page containing six HTML
``<input type="range">`` elements (sliders). Each slider is bound to a
JavaScript ``input`` event so that whenever its value changes, the browser
sends a POST request back to the server.  The server collects the current
values of all sliders (sent as JSON) and prints them to the console.

The sliders allow values between -90 and 90 inclusive.  Their current
settings are not persisted across refreshes; each page load resets them to
0 by default.

Run this file directly with ``python app.py``.  Once running, navigate
to ``http://127.0.0.1:5000/`` in your browser.  Adjust the sliders and
observe the server's console output for the current dictionary of values.
"""

from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    """Serve the main page containing six sliders.

    The HTML is rendered directly from a template string for simplicity.
    Each slider has a unique ``id`` attribute so its value can be read
    programmatically.  We attach a JavaScript event handler that fires on
    the ``input`` event (triggered for each incremental change) and
    assembles a dictionary of all slider values.  It then sends this
    dictionary to the server using ``fetch()``.
    """
    return render_template_string(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Flask Sliders</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 2em; }
                .slider-container { margin-bottom: 1.5em; }
                label { display: block; margin-bottom: 0.5em; font-weight: bold; }
                input[type=range] { width: 100%; }
                .value { font-size: 0.9em; color: #555; }
            </style>
        </head>
        <body>
            <h1>Adjust the sliders</h1>
            <div id="sliders">
                {% for i in range(1, 7) %}
                <div class="slider-container">
                    <label for="slider{{ i }}">Motor {{ i }} (-90 to 90): <span class="value" id="value{{ i }}">0</span></label>
                    <input type="range" id="slider{{ i }}" min="-90" max="90" value="0" />
                </div>
                {% endfor %}
            </div>
            <script>
                // Function to collect current slider values into an object
                function collectValues() {
                    const values = {};
                    for (let i = 1; i <= 6; i++) {
                        const slider = document.getElementById('slider' + i);
                        values['slider' + i] = Number(slider.value);
                    }
                    return values;
                }

                // Function to update text next to sliders showing current value
                function updateValueDisplays() {
                    for (let i = 1; i <= 6; i++) {
                        const valSpan = document.getElementById('value' + i);
                        const slider = document.getElementById('slider' + i);
                        valSpan.textContent = slider.value;
                    }
                }

                // Function to send slider values to the server
                function sendUpdate() {
                    const values = collectValues();
                    fetch('/update', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(values)
                    }).then(response => {
                        // Optionally handle response here; we just ignore it.
                    });
                }

                // Attach input event listeners to all sliders
                document.querySelectorAll('input[type=range]').forEach(slider => {
                    slider.addEventListener('input', () => {
                        updateValueDisplays();
                        sendUpdate();
                    });
                });

                // Initialize value displays on first load
                updateValueDisplays();
            </script>
        </body>
        </html>
        """
    )


@app.route("/update", methods=["POST"])
def update():
    """Receive updated slider values and print them to the console.

    The client sends a JSON object mapping slider names to numerical values.
    Here we simply print this dictionary to the server's standard output.  The
    function returns a JSON response indicating success.  No state is stored
    between requests.
    """
    data = request.get_json(force=True) or {}
    # Validate that data contains only numeric values
    values = {k: float(v) if v is not None else None for k, v in data.items()}
    print("Received slider values:", values)
    return jsonify(success=True)


if __name__ == "__main__":
    # Enable debug=True for automatic reload on code changes.  Use host='0.0.0.0'
    # to listen on all interfaces if needed.
    app.run(debug=True)