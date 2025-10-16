SO-ARM100 PyBullet Simulation

Overview
- Loads and controls the SO-ARM100 (SO100) URDF in PyBullet.
- Provides keyboard control and a simple programmatic demo.
- Designed to serve as a software-only stand‑in for the real arm during development.

Files
- `so_arm100_pybullet.py`: main simulator/controller script.
- `SimulationModels/SO100/so100.urdf`: robot model and meshes.

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

USB/Serial Spoofing (mimic the real device)

There are two practical approaches, depending on how your application is structured:

1) Driver shim (recommended)
- Implement a drop‑in Python class that provides the same interface as your hardware driver (e.g., `SO100Follower`) but routes calls to this simulator.
- Advantages: simple, cross‑platform, no OS‑level serial plumbing required.
- Sketch:
```py
from submodules.simulation.so_arm100_pybullet import SOARM100Sim

class SO100FollowerSim:
    def __init__(self, cfg=None):
        self.sim = None
    def connect(self):
        self.sim = SOARM100Sim(gui=True)
        self.sim.reset_pose()
    def disconnect(self):
        if self.sim:
            self.sim.disconnect()
    def get_observation(self):
        # Return a dict compatible with your app
        return {name + ".pos": self.sim.get_joint_state(name) for name in self.sim.joint_names()}
    def send_action(self, action):
        # Expect keys like 'shoulder_pan.pos' with position values
        pos_targets = {}
        for k, v in action.items():
            if k.endswith('.pos'):
                pos_targets[k.replace('.pos', '')] = float(v)
        self.sim.set_positions(pos_targets)
```
- Wire it in via a config flag (e.g., `device_port=SIM`) or env var to choose between real and simulated backends.

2) Virtual serial pair + protocol bridge
- If the existing app must open a serial port, create a virtual serial pair and run a small bridge process that emulates the device protocol on one end while the app connects on the other.

Linux/macOS (socat):
- Install `socat` (`apt install socat` or `brew install socat`).
- Create a paired PTY:
  - `socat -d -d pty,raw,echo=0,link=./ttySIM0 pty,raw,echo=0,link=./ttySIM1`
- Point your app to `./ttySIM0`.
- Run a Python bridge that opens `./ttySIM1` using `pyserial`, parses incoming frames, and translates them to simulator commands (and vice‑versa).

Windows:
- Use `com0com` to create a virtual COM pair (e.g., `COM17` ↔ `COM18`).
- App connects to `COM17`; the bridge connects to `COM18` and emulates the device protocol.

Bridge skeleton (protocol‑agnostic):
```py
import serial, time
from submodules.simulation.so_arm100_pybullet import SOARM100Sim

PORT = './ttySIM1'  # or 'COM18' on Windows
BAUD = 115200

sim = SOARM100Sim(gui=True)
sim.reset_pose()

with serial.Serial(PORT, BAUD, timeout=0.01) as ser:
    while True:
        data = ser.read(1024)
        if data:
            # TODO: parse your device protocol here and call sim.set_positions(...)
            pass
        # Optionally, periodically send observation frames back:
        # obs = ... format per your protocol ...
        # ser.write(obs)
        sim.step()
```

Notes and limitations
- The serial bridge requires implementing the same byte‑level protocol used by the real controller. If that protocol isn’t documented, prefer the driver shim.
- For deterministic testing, disable real‑time (`--realtime` off) and use a fixed timestep.
- The provided simulator uses position control; extend with torque/velocity control as needed.

