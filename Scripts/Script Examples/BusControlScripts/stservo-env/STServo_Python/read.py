#!/usr/bin/env python
#
# *********     Gen Write Example      *********
#
#
# Available STServo model on this example : All models using Protocol STS
# This example is tested with a STServo and an URT
#

import sys
import os
import time

if os.name == 'nt':
    import msvcrt
    def getch():
        return msvcrt.getch().decode()
        
else:
    import sys, tty, termios
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    def getch():
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

sys.path.append("..")
from STservo_sdk import *                      # Uses STServo SDK library

# Default setting
STS_ID                      = 5                 # STServo ID : 1
BAUDRATE                    = 1000000           # STServo default baudrate : 1000000
DEVICENAME                  = '/dev/tty.usbmodem58FA0924721'    # Check which port is being used on your controller
                                                # ex) Windows: "COM1"   Linux: "/dev/ttyUSB0" Mac: "/dev/tty.usbserial-*"
def connect():
    # Initialize PortHandler instance
    # Set the port path
    # Get methods and members of PortHandlerLinux or PortHandlerWindows
    portHandler = PortHandler(DEVICENAME)

    # Initialize PacketHandler instance
    # Get methods and members of Protocol
    packetHandler = sts(portHandler)
    
    if portHandler.openPort():
        print("Succeeded to open the port")
    else:
        print("Failed to open the port")
        print("Press any key to terminate...")
        getch()
        quit()

    # Set port baudrate
    if portHandler.setBaudRate(BAUDRATE):
        print("Succeeded to change the baudrate")
    else:
        print("Failed to change the baudrate")
        print("Press any key to terminate...")
        getch()
        quit() 
    
    return (portHandler, packetHandler)


def log_servo_positions(filename: str, packetHandler):
    with open(filename, 'a') as file:
        for i in range(10000):
            angle_values = []
            for servoId in range(0, 7, 1):
                try:
                    pos = packetHandler.ReadPos(servoId)
                    # For all ACTUAL servos
                    if servoId > 0:
                        if  pos[1] == 0:
                            # Add the values to the list
                            angle_values.append(str(pos[0]))
                            print(f"Servo {servoId}:", pos)
                        else:
                            angle_values.append("")
                except:
                    print(f"Servo {servoId}: Fail")
                    angle_values.append("")
                    _, packetHandler = connect()
            
            # Once all motor positions have been measured each, add values to the log file
            outputLine = ",".join(angle_values) + "\n"
            file.write(outputLine)
            print("===============\n\n")
            time.sleep(0.1)
        # Close file once complete
        file.close()

portHandler, packetHandler = connect()

# for i in range(10000):
#     print("State:")
#     for i in range(0, 7, 1):
#         try:
#             pos = packetHandler.ReadPos(i)
#             print(f"Servo {i}:", pos)
#         except:
#             print(f"Servo {i}: Fail")
#             _, packetHandler = connect()
#     print("===============\n\n")
#     time.sleep(0.5)

log_servo_positions("servo_positions.log", packetHandler=packetHandler)
    


# while 1:
#     print("Press any key to continue! (or press ESC to quit!)")
#     if getch() == chr(0x1b):
#         break
#     # Read STServo present position
#     sts_present_position, sts_present_speed, sts_comm_result, sts_error = packetHandler.ReadPosSpeed(STS_ID)
#     if sts_comm_result != COMM_SUCCESS:
#         print(packetHandler.getTxRxResult(sts_comm_result))
#     else:
#         print("[ID:%03d] PresPos:%d PresSpd:%d" % (STS_ID, sts_present_position, sts_present_speed))
#     if sts_error != 0:
#         print(packetHandler.getRxPacketError(sts_error))

# Close port
portHandler.closePort()
