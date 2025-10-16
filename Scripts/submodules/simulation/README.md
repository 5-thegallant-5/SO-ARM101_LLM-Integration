SO-ARM100 PyBullet Simulation

Overview
- Loads and controls the SO-ARM100 (SO100) URDF in PyBullet.
- Provides keyboard control and a simple programmatic demo.
- Designed to serve as a software-only stand‑in for the real arm during development.

Files
- `so_arm100_pybullet.py`: main simulator/controller script.
- `SimulationModels/SO100/so100.urdf`: robot model and meshes.
 - `web_interface_sim.py`: launches the existing Flask WebInterface wired to the simulator.

Requirements
- Python 3.9+
- `pybullet` (e.g., `pip install pybullet`)

Quick Start
- GUI + keyboard control:
  - `python submodules/simulation/so_arm100_pybullet.py --gui --mode keyboard`
  - Keys: `1/2` pan, `q/a` lift, `w/s` elbow, `e/d` wrist flex, `r/f` roll, `t/g` gripper, `z` quit.
- GUI + demo motion:
  - `python submodules/simulation/so_arm100_pybullet.py --gui --mode demo`
- Headless demo:
  - `python submodules/simulation/so_arm100_pybullet.py --direct --mode demo`

Web Interface (sliders)
- Launch the Flask app backed by the simulator:
  - `python submodules/simulation/web_interface_sim.py`
- Open `http://127.0.0.1:5000` in your browser.
- Move sliders to send joint targets (degrees) to the sim.
- Tip: set `SO100_SIM_GUI=0` to run the sim headless.

Options
- `--realtime`: enable real‑time stepping.
- `--time-step <sec>`: physics time step (default `1/240`).
- `--no-plane`: skip loading the ground plane.

Programmatic Usage (minimal)
```py
from submodules.simulation.so_arm100_pybullet import SOARM100Sim

sim = SOARM100Sim(gui=True)
sim.reset_pose()
sim.set_positions({
    "shoulder_pan": 0.2,
    "shoulder_lift": 0.4,
    "elbow_flex": -0.6,
    "wrist_flex": 0.1,
    "wrist_roll": 0.0,
    "gripper": 0.3,
})
for _ in range(1000):
    sim.step()
sim.disconnect()
```
