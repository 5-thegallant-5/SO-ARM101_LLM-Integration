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
from pathlib import Path
from typing import Dict, Optional

from so_arm100_pybullet import SOARM100Sim


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
        self.connected = True

    def disconnect(self) -> None:
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
            obs[f"{name}.pos"] = _rad_to_deg(rad)
        return obs

    # Action API: accept dict of '<joint>.pos' in DEGREES
    def send_action(self, action: Dict[str, float]) -> None:
        if not self.connected or self.sim is None:
            raise RuntimeError("SO100FollowerSim not connected")

        # Convert to radians and clamp to URDF limits
        targets_rad: Dict[str, float] = {}
        for key, deg_val in action.items():
            if not key.endswith(".pos"):
                continue
            name = key[:-4]  # strip '.pos'
            if name not in self.sim.joint_name_to_index:
                continue
            rad = _deg_to_rad(float(deg_val))
            try:
                lower, upper = self.sim.get_joint_limits(name)
            except Exception:
                lower, upper = (-3.14, 3.14)
            rad = max(lower, min(upper, rad))
            targets_rad[name] = rad

        if targets_rad:
            self.sim.set_positions(targets_rad)
            # Step once to apply; callers can manage pacing if needed
            self.sim.step(sleep=True)

