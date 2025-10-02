# https://huggingface.co/docs/lerobot/il_robots?teleoperate_so101=Command

from lerobot.teleoperators.so101_leader import SO101LeaderConfig, SO101Leader
from lerobot.robots.so101_follower import SO101FollowerConfig, SO101Follower

robot_config = SO101FollowerConfig(
    port="/dev/tty.usbmodem58760431541",
    id="my_red_robot_arm",
)

teleop_config = SO101LeaderConfig(
    port="/dev/tty.usbmodem58760431551",
    id="my_blue_leader_arm",
)

robot = SO101Follower(robot_config)
teleop_device = SO101Leader(teleop_config)
robot.connect()
teleop_device.connect()

while True:
    action = teleop_device.get_action()
    robot.send_action(action)
