# #!/usr/bin/env python
# #
# # *********     Gen Write Example      *********
# #
# #
# # Available STServo model on this example : All models using Protocol STS
# # This example is tested with a STServo and an URT
# #
#
# import sys
# import os
#
# if os.name == 'nt':
#     import msvcrt
#     def getch():
#         return msvcrt.getch().decode()
#
# else:
#     import sys, tty, termios
#     fd = sys.stdin.fileno()
#     old_settings = termios.tcgetattr(fd)
#     def getch():
#         try:
#             tty.setraw(sys.stdin.fileno())
#             ch = sys.stdin.read(1)
#         finally:
#             termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
#         return ch
#
# sys.path.append("..")
# from STservo_sdk import *                 # Uses STServo SDK library
import time

from lerobot.robots.so100_follower import SO100FollowerConfig, SO100Follower
from lerobot.teleoperators.so100_leader import SO100LeaderConfig, SO100Leader
robot_config = SO100FollowerConfig(
    port="COM5",
    id="1",
)

# teleop_config = SO100LeaderConfig(
#     port="COM6",
#     id="2",
# )

# teleop_device = SO100Leader(teleop_config)
# teleop_device.connect()
robot = SO100Follower(robot_config)
robot.connect()
print("Robot Connected")
print(robot.get_observation())

# action = teleop_device.get_action()
# print(action)
action = {
'shoulder_pan.pos': 0,
'shoulder_lift.pos':0,
'elbow_flex.pos': 0,
#'wrist_flex.pos': 0,
'wrist_roll.pos': 0,
'gripper.pos': 0
}

pre_rest = {
    'shoulder_pan.pos': -0.5032350826743368,
    'shoulder_lift.pos': -60.932038834951456,
    'elbow_flex.pos': 61.8659420289855,
    'wrist_flex.pos': 77.70571544385894,
    'wrist_roll.pos': 0.024420024420024333,
    'gripper.pos': 0.5405405405405406
}

true_rest = {
    'shoulder_pan.pos': -0.6470165348670065,
    'shoulder_lift.pos': -88.73786407766991,
    'elbow_flex.pos': 99.54710144927537,
    'wrist_flex.pos': 77.70571544385894,
    'wrist_roll.pos': 0.024420024420024333,
    'gripper.pos': 0.5405405405405406
}

robot.send_action(action)

time.sleep(1)

move_pos = input("")

print(robot.get_observation())

move_pos = input("")

robot.send_action(pre_rest)

time.sleep(3)

robot.send_action(true_rest)

time.sleep(3)

robot.disconnect()

# teleop_device.disconnect()

# # Default setting
# STS_ID                      = 1                 # STServo ID : 1
# BAUDRATE                    = 1000000           # STServo default baudrate : 1000000
# DEVICENAME                  = 'COM5'    # Check which port is being used on your controller
#                                                 # ex) Windows: "COM1"   Linux: "/dev/ttyUSB0" Mac: "/dev/tty.usbserial-*"
# STS_MINIMUM_POSITION_VALUE  =  0          # STServo will rotate between this value
# STS_MAXIMUM_POSITION_VALUE  = 300
# STS_MOVING_SPEED            = 500        # STServo moving speed
# STS_MOVING_ACC              = 50         # STServo moving acc
#
# index = 0
# sts_goal_position = [STS_MINIMUM_POSITION_VALUE, STS_MAXIMUM_POSITION_VALUE]         # Goal position
#
# # Initialize PortHandler instance
# # Set the port path
# # Get methods and members of PortHandlerLinux or PortHandlerWindows
# portHandler = PortHandler(DEVICENAME)
#
# # Initialize PacketHandler instance
# # Get methods and members of Protocol
# packetHandler = sts(portHandler)
#
# # Open port
# if portHandler.openPort():
#     print("Succeeded to open the port")
# else:
#     print("Failed to open the port")
#     print("Press any key to terminate...")
#     getch()
#     quit()
#
# # Set port baudrate
# if portHandler.setBaudRate(BAUDRATE):
#     print("Succeeded to change the baudrate")
# else:
#     print("Failed to change the baudrate")
#     print("Press any key to terminate...")
#     getch()
#     quit()
#
# # while 1:
# #     print("Press any key to continue! (or press ESC to quit!)")
# #     if getch() == chr(0x1b):
# #         break
#
# #     # Write STServo goal position/moving speed/moving acc
# #     sts_comm_result, sts_error = packetHandler.WritePosEx(STS_ID, sts_goal_position[index], STS_MOVING_SPEED, STS_MOVING_ACC)
# #     if sts_comm_result != COMM_SUCCESS:
# #         print("%s" % packetHandler.getTxRxResult(sts_comm_result))
# #     if sts_error != 0:
# #         print("%s" % packetHandler.getRxPacketError(sts_error))
#
# #     # Change goal position
# #     if index == 0:
# #         index = 1
# #     else:
# #         index = 0
# while True:
#     move_pos = int(input(""))
#
#     if move_pos == -1:
#         break
#
#     sts_comm_result, sts_error = packetHandler.WritePosEx(STS_ID, move_pos, STS_MOVING_SPEED, STS_MOVING_ACC)
#     if sts_comm_result != COMM_SUCCESS:
#         print("%s" % packetHandler.getTxRxResult(sts_comm_result))
#     if sts_error != 0:
#         print("%s" % packetHandler.getRxPacketError(sts_error))
#
# # Close port
# portHandler.closePort()
