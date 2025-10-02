# https://huggingface.co/docs/lerobot/il_robots?teleoperate_so101=Command

from lerobot.robots.so100_follower import SO100Follower, SO100FollowerConfig, SO100FollowerEndEffector, SO100FollowerEndEffectorConfig

robot_config = SO100FollowerConfig(
    port="/dev/tty.usbmodem58FA0924721",
    id="my_robot_arm",
)

robot = SO100Follower(robot_config)
robot.connect()
robot.connect(calibrate=False)
robot.calibrate()
robot.disconnect()

# while True:
#     robot.get_observation()
