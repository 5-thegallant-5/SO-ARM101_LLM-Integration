import time
from typing import Dict


def send_action_ramped(robot, target: Dict[str, float], speed: float = 0.5, steps: int | None = None) -> None:
    """
    Move robot towards target positions with simple linear interpolation.
    speed in [0,1] controls total movement duration (slower near 0).
    """
    # Clamp speed to a safe range
    s = max(0.01, min(1.0, float(speed)))
    # Map speed to duration: 0.01 -> ~4.95s, 1.0 -> 1.0s
    total_duration = 1.0 + (1.0 - s) * 4.0
    dt = 0.05  # 20 Hz
    n_steps = steps if steps is not None else max(1, int(total_duration / dt))

    # Read current observation (assumes same keys present)
    current = robot.get_observation()
    keys = target.keys()
    start = {k: current.get(k, 0.0) for k in keys}

    for i in range(1, n_steps + 1):
        alpha = i / n_steps
        interp = {k: start[k] + (target[k] - start[k]) * alpha for k in keys}
        robot.send_action(interp)
        time.sleep(dt)

