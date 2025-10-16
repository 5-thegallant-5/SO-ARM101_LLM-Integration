"""
SO-ARM100 PyBullet simulation and control

Provides a simple wrapper around PyBullet to load the SO-ARM100
URDF, step the simulation, and control joints via position control.

Usage examples:

- Keyboard control (default):
  python submodules/simulation/so_arm100_pybullet.py --gui --mode keyboard

- Programmatic demo (sine wave):
  python submodules/simulation/so_arm100_pybullet.py --gui --mode demo

Controls (keyboard mode, GUI only):
  1/2: shoulder_pan -/+         q/a: shoulder_lift -/+
  w/s: elbow_flex -/+           e/d: wrist_flex -/+
  r/f: wrist_roll -/+           t/g: gripper -/+
  z:   quit

Notes:
- The script loads SO-ARM100 from SimulationModels/SO100/so100.urdf
  relative to this file.
- Joints are controlled with POSITION_CONTROL.
"""

from __future__ import annotations

import argparse
import math
import os
import time
from typing import Dict, Iterable, Optional

import pybullet as p
import pybullet_data


JOINT_KEYS = {
    "shoulder_pan": (ord("1"), ord("2")),
    "shoulder_lift": (ord("q"), ord("a")),
    "elbow_flex": (ord("w"), ord("s")),
    "wrist_flex": (ord("e"), ord("d")),
    "wrist_roll": (ord("r"), ord("f")),
    "gripper": (ord("t"), ord("g")),
}


def _this_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def find_so100_urdf() -> str:
    base = os.path.join(_this_dir(), "SimulationModels", "SO100")
    urdf = os.path.join(base, "so100.urdf")
    if not os.path.isfile(urdf):
        raise FileNotFoundError(f"SO-ARM100 URDF not found at: {urdf}")
    return urdf


class SOARM100Sim:
    def __init__(
        self,
        gui: bool = True,
        real_time: bool = False,
        time_step: float = 1.0 / 240.0,
        use_plane: bool = True,
        use_fixed_base: bool = True,
        minimal_gui: bool = True,
    ) -> None:
        self.client = p.connect(p.GUI if gui else p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.resetSimulation(physicsClientId=self.client)
        p.setGravity(0, 0, -9.81)

        # Configure timing
        self.time_step = time_step
        p.setTimeStep(self.time_step)
        p.setRealTimeSimulation(1 if real_time else 0)

        # Reduce GUI rendering load if requested
        if gui and minimal_gui:
            try:
                p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_RGB_BUFFER_PREVIEW, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_DEPTH_BUFFER_PREVIEW, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_SEGMENTATION_MARK_PREVIEW, 0)
                p.configureDebugVisualizer(p.COV_ENABLE_WIREFRAME, 0)
                # Temporarily disable rendering while loading assets
                p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 0)
            except Exception:
                pass

        # Optionally add a plane
        if use_plane:
            p.loadURDF("plane.urdf")

        # Load robot
        self.urdf_path = find_so100_urdf()
        self.robot_id = p.loadURDF(
            self.urdf_path,
            basePosition=[0, 0, 0],
            baseOrientation=[0, 0, 0, 1],
            useFixedBase=use_fixed_base,
            flags=p.URDF_USE_INERTIA_FROM_FILE | p.URDF_MAINTAIN_LINK_ORDER,
        )

        # Set a default debug visualizer camera if GUI is enabled
        try:
            # Requested settings: dist=1.06, pitch=-35.80, yaw=75.60
            # API: resetDebugVisualizerCamera(distance, yaw, pitch, targetPosition)
            p.resetDebugVisualizerCamera(
                cameraDistance=1.06,
                cameraYaw=75.60,
                cameraPitch=-35.80,
                cameraTargetPosition=[-0.36, 0.0, -0.18],
            )
        except Exception:
            pass

        # Re-enable rendering after setup
        try:
            p.configureDebugVisualizer(p.COV_ENABLE_RENDERING, 1)
        except Exception:
            pass

        # Build joint name -> index map for convenience
        self.joint_name_to_index: Dict[str, int] = {}
        self._populate_joint_mapping()

        # Default PD/force settings
        self.kp = 0.6
        self.kd = 0.05
        self.max_force = 35.0  # matches URDF effort bounds roughly

    def _populate_joint_mapping(self) -> None:
        self.joint_name_to_index.clear()
        num_joints = p.getNumJoints(self.robot_id)
        for j in range(num_joints):
            ji = p.getJointInfo(self.robot_id, j)
            name = ji[1].decode("utf-8")
            joint_type = ji[2]
            # Only map controllable joints (revolute/prismatic)
            if joint_type in (p.JOINT_REVOLUTE, p.JOINT_PRISMATIC):
                self.joint_name_to_index[name] = j

    # ---------- Query helpers ----------
    def joint_names(self) -> Iterable[str]:
        return list(self.joint_name_to_index.keys())

    def get_joint_state(self, name: str) -> float:
        idx = self.joint_name_to_index[name]
        state = p.getJointState(self.robot_id, idx)
        return float(state[0])

    def get_joint_limits(self, name: str) -> tuple[float, float]:
        idx = self.joint_name_to_index[name]
        info = p.getJointInfo(self.robot_id, idx)
        return float(info[8]), float(info[9])  # lower, upper

    # ---------- Control helpers ----------
    def reset_pose(self, joint_positions: Optional[Dict[str, float]] = None) -> None:
        if joint_positions is None:
            joint_positions = {
                "shoulder_pan": 0.0,
                "shoulder_lift": 0.2,
                "elbow_flex": -0.5,
                "wrist_flex": 0.0,
                "wrist_roll": 0.0,
                "gripper": 0.2,
            }
        for name, pos in joint_positions.items():
            if name in self.joint_name_to_index:
                idx = self.joint_name_to_index[name]
                p.resetJointState(self.robot_id, idx, targetValue=float(pos))

    def set_positions(
        self,
        targets: Dict[str, float],
        kp: Optional[float] = None,
        kd: Optional[float] = None,
        max_force: Optional[float] = None,
    ) -> None:
        kp = self.kp if kp is None else kp
        kd = self.kd if kd is None else kd
        max_force = self.max_force if max_force is None else max_force

        indices = []
        positions = []
        forces = []
        for name, pos in targets.items():
            if name not in self.joint_name_to_index:
                continue
            idx = self.joint_name_to_index[name]
            indices.append(idx)
            positions.append(float(pos))
            forces.append(float(max_force))

        if not indices:
            return

        p.setJointMotorControlArray(
            bodyUniqueId=self.robot_id,
            jointIndices=indices,
            controlMode=p.POSITION_CONTROL,
            targetPositions=positions,
            positionGains=[kp] * len(indices),
            velocityGains=[kd] * len(indices),
            forces=forces,
        )

    def step(self, sleep: bool = True) -> None:
        # If RT sim disabled, manually step. Use getRealTimeSimulation() (not isRealTimeSimulation).
        try:
            rt = p.getRealTimeSimulation()
        except AttributeError:
            # Fallback: assume non-real-time if API not available
            rt = 0
        if rt == 0:
            p.stepSimulation()
        if sleep:
            time.sleep(self.time_step)

    def disconnect(self) -> None:
        try:
            p.disconnect()
        except Exception:
            pass

    # ---------- Interactive control ----------
    def keyboard_control(self, step_size: float = 0.02) -> None:
        # Initialize targets from current state
        targets: Dict[str, float] = {}
        for name in self.joint_name_to_index:
            try:
                targets[name] = self.get_joint_state(name)
            except Exception:
                targets[name] = 0.0

        print("Keyboard control active. Press 'z' to quit.")
        print("Keys: 1/2 shoulder_pan, q/a shoulder_lift, w/s elbow_flex, e/d wrist_flex, r/f wrist_roll, t/g gripper")

        while True:
            events = p.getKeyboardEvents()
            if ord("z") in events and events[ord("z")] & p.KEY_WAS_TRIGGERED:
                break

            # For each joint with a key mapping, adjust target when key pressed
            for name, (dec_key, inc_key) in JOINT_KEYS.items():
                if name not in self.joint_name_to_index:
                    continue
                lower, upper = self.get_joint_limits(name)
                val = targets.get(name, 0.0)
                if dec_key in events and events[dec_key] & p.KEY_IS_DOWN:
                    val -= step_size
                if inc_key in events and events[inc_key] & p.KEY_IS_DOWN:
                    val += step_size
                # Clamp to limits
                val = max(lower, min(upper, val))
                targets[name] = val

            # Apply
            self.set_positions(targets)
            self.step(sleep=True)


def run_demo(sim: SOARM100Sim, duration: float = 15.0) -> None:
    start = time.time()
    sim.reset_pose()
    while time.time() - start < duration:
        t = time.time() - start
        # Simple periodic motion within joint limits
        targets = {
            "shoulder_pan": 0.4 * math.sin(0.5 * t),
            "shoulder_lift": 0.4 + 0.25 * math.sin(0.6 * t + 1.0),
            "elbow_flex": -0.6 + 0.4 * math.sin(0.7 * t + 0.3),
            "wrist_flex": 0.25 * math.sin(0.9 * t + 0.5),
            "wrist_roll": 0.6 * math.sin(1.2 * t),
            "gripper": 0.4 + 0.3 * (0.5 * (1 + math.sin(1.5 * t))),
        }
        sim.set_positions(targets)
        sim.step(sleep=True)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="SO-ARM100 PyBullet simulation")
    ap.add_argument("--gui", action="store_true", help="Run with GUI (default)")
    ap.add_argument("--direct", action="store_true", help="Run headless (DIRECT)")
    ap.add_argument("--mode", choices=["keyboard", "demo"], default="keyboard", help="Control mode")
    ap.add_argument("--realtime", action="store_true", help="Enable real-time simulation")
    ap.add_argument("--no-plane", action="store_true", help="Do not load ground plane")
    ap.add_argument("--time-step", type=float, default=1.0 / 240.0, help="Physics time step")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    gui = True
    if args.direct:
        gui = False
    elif args.gui:
        gui = True

    sim = SOARM100Sim(
        gui=gui,
        real_time=args.realtime,
        time_step=args.time_step,
        use_plane=not args.no_plane,
        use_fixed_base=True,
    )
    try:
        if args.mode == "keyboard":
            if not gui:
                print("Keyboard mode requires GUI; falling back to demo mode.")
                run_demo(sim)
            else:
                sim.reset_pose()
                sim.keyboard_control()
        else:
            run_demo(sim)
    finally:
        sim.disconnect()


if __name__ == "__main__":
    main()
