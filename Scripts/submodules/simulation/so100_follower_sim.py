"""
SO100Follower-compatible simulation shim for SO-ARM100.

This module provides drop-in classes with the same API surface used by the
project (connect, disconnect, get_observation, send_action, and bus.disable_torque),
but routes all commands to the PyBullet simulator in
`submodules/simulation/so_arm100_pybullet.py`.

Usage (replace imports in your app):
    from submodules.simulation.so100_follower_sim import SO100FollowerConfig, SO100Follower

Notes:
- send_action expects degrees for `.pos` values (like the real driver).
- get_observation returns degrees for `.pos` keys to match existing code.
- Torque control is not simulated; `bus.disable_torque()` is a no-op.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
import threading
import time
from pathlib import Path
from typing import Dict, Optional

if os.getcwd().endswith("simulation"):
    from so_arm100_pybullet import SOARM100Sim
else:
    from .so_arm100_pybullet import SOARM100Sim


def _deg_to_rad(v: float) -> float:
    return v * math.pi / 180.0


def _rad_to_deg(v: float) -> float:
    return v * 180.0 / math.pi


@dataclass
class SO100FollowerConfig:
    port: str
    id: str = "robot"
    calibration_dir: Optional[Path] = None
    gui: bool = True
    realtime: bool = False
    time_step: float = 1.0 / 240.0


class _BusStub:
    def disable_torque(self) -> None:
        # Not applicable for simulation; present for API compatibility
        return None


class SO100Follower:
    def __init__(self, cfg: SO100FollowerConfig) -> None:
        self.cfg = cfg
        self.sim: Optional[SOARM100Sim] = None
        self.bus = _BusStub()
        self.connected = False
        # Per-joint zero offset (radians) so that UI 0 == middle of motion
        self._zero_offset_rad: Dict[str, float] = {}
        # Joints to calibrate with 0 at middle (exclude gripper)
        self._arm_joints = {
            "shoulder_pan",
            "shoulder_lift",
            "elbow_flex",
            "wrist_flex",
            "wrist_roll",
        }
        # Background stepping thread state
        self._step_thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()
        self._action_lock = threading.Lock()
        # Degrees maps for desired and currently applied actions ('.pos' keys)
        self._desired_deg: Dict[str, float] = {}
        self._applied_deg: Dict[str, float] = {}

    def connect(self) -> None:
        # If the real code decides GUI based on port or env, honor an override
        gui = self.cfg.gui
        if os.getenv("SO100_SIM_GUI") in {"0", "false", "False"}:
            gui = False

        self.sim = SOARM100Sim(
            gui=gui,
            real_time=self.cfg.realtime,
            time_step=self.cfg.time_step,
            use_plane=True,
            use_fixed_base=True,
        )
        self.sim.reset_pose()
        # Build zero offsets at joint midpoints so that 0 deg == middle
        self._zero_offset_rad.clear()
        for name in self.sim.joint_names():
            try:
                lower, upper = self.sim.get_joint_limits(name)
            except Exception:
                lower, upper = (-3.14159, 3.14159)
            mid = 0.5 * (lower + upper)
            self._zero_offset_rad[name] = mid

        # Reset sim to middle positions for a neutral start
        try:
            self.sim.set_positions({n: off for n, off in self._zero_offset_rad.items()})
            # Step a few frames to settle
            for _ in range(5):
                self.sim.step(sleep=True)
        except Exception:
            pass
        self.connected = True
        # Initialize desired/applied from current observation and start stepping
        try:
            obs = self.get_observation()
        except Exception:
            obs = {}
        with self._action_lock:
            self._desired_deg = dict(obs)
            self._applied_deg = dict(obs)
        self._start_stepping_thread()

    def disconnect(self) -> None:
        # Stop background thread
        self._stop_stepping_thread()
        if self.sim is not None:
            self.sim.disconnect()
        self.sim = None
        self.connected = False

    # Observation API: return a dict of '<joint>.pos' in DEGREES
    def get_observation(self) -> Dict[str, float]:
        if not self.connected or self.sim is None:
            raise RuntimeError("SO100FollowerSim not connected")
        obs: Dict[str, float] = {}
        for name in self.sim.joint_names():
            try:
                rad = self.sim.get_joint_state(name)
            except Exception:
                rad = 0.0
            # Report degrees relative to middle for arm joints, absolute for gripper
            if name in self._arm_joints:
                rad -= self._zero_offset_rad.get(name, 0.0)
            obs[f"{name}.pos"] = _rad_to_deg(rad)
        return obs

    # Action API: accept dict of '<joint>.pos' in DEGREES
    def send_action(self, action: Dict[str, float]) -> None:
        if not self.connected or self.sim is None:
            raise RuntimeError("SO100FollowerSim not connected")
        # Store desired degrees; background thread will rate-limit and step
        with self._action_lock:
            for key, deg_val in action.items():
                if not key.endswith(".pos"):
                    continue
                self._desired_deg[key] = float(deg_val)

    # Internal: start/stop stepping thread
    def _start_stepping_thread(self) -> None:
        if self._step_thread and self._step_thread.is_alive():
            return
        self._stop_evt.clear()
        t = threading.Thread(target=self._step_loop, name="so100-sim-step", daemon=True)
        self._step_thread = t
        t.start()

    def _stop_stepping_thread(self) -> None:
        self._stop_evt.set()
        t = self._step_thread
        if t and t.is_alive():
            t.join(timeout=1.0)
        self._step_thread = None

    def _step_loop(self) -> None:
        # Rate limit in deg/s, default 120
        try:
            max_deg_per_s = float(os.getenv("SO100_SIM_MAX_SPEED_DEG_S", "120"))
        except Exception:
            max_deg_per_s = 120.0
        dt = float(self.cfg.time_step or 1.0 / 240.0)
        max_deg_per_step = max(0.0, max_deg_per_s * dt)

        def _rate_limit(curr: float, target: float, max_step: float) -> float:
            delta = target - curr
            if abs(delta) <= max_step:
                return target
            return curr + max_step * (1.0 if delta > 0 else -1.0)

        while not self._stop_evt.is_set():
            try:
                if self.sim is None:
                    time.sleep(dt)
                    continue
                # Snapshot desired and current applied
                with self._action_lock:
                    desired = dict(self._desired_deg)
                    applied = dict(self._applied_deg)

                # Build next applied by rate-limiting toward desired
                next_applied: Dict[str, float] = dict(applied)
                for key in set(list(applied.keys()) + list(desired.keys())):
                    if not key.endswith(".pos"):
                        continue
                    curr = applied.get(key, 0.0)
                    tgt = desired.get(key, curr)
                    next_applied[key] = _rate_limit(curr, tgt, max_deg_per_step)

                # Convert to radians and clamp to URDF limits
                targets_rad: Dict[str, float] = {}
                for key, deg_val in next_applied.items():
                    if not key.endswith(".pos"):
                        continue
                    name = key[:-4]
                    if name not in self.sim.joint_name_to_index:
                        continue
                    if name in self._arm_joints:
                        rad = self._zero_offset_rad.get(name, 0.0) + _deg_to_rad(float(deg_val))
                    else:
                        rad = _deg_to_rad(float(deg_val))
                    try:
                        lower, upper = self.sim.get_joint_limits(name)
                    except Exception:
                        lower, upper = (-3.14, 3.14)
                    rad = max(lower, min(upper, rad))
                    targets_rad[name] = rad

                if targets_rad:
                    self.sim.set_positions(targets_rad)
                # Commit the applied map
                with self._action_lock:
                    self._applied_deg = dict(next_applied)

                # Advance physics one step, sleeping to maintain dt
                try:
                    self.sim.step(sleep=True)
                except Exception:
                    time.sleep(dt)
            except Exception:
                time.sleep(dt)
