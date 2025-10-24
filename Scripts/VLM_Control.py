# VLM_Control.py: Allows for the llama3.2-vision VLM model being run through Ollama on the same computer
# to manipulate the SO-100 Robotic Arm via joint manipulation and visual feedback
# in accordance to the general instructions that the user provides
# Author: Stuart Kennedy U3239456


# THIRD PARTY APPLICATION NEEDED. needs the Ollama application running the llama3.2-vision model to work.
# Download Ollama here: https://ollama.com, Run this command in cmd "Ollama run Llama3.2-vision"

import json
import ollama
import time
import cv2
import os
from pydantic import BaseModel, Field
from lerobot.robots.so100_follower import SO100FollowerConfig, SO100Follower
from pathlib import Path

# Configure the SO-100 Arm will need to change port based on the port being used by the device
robot_config = SO100FollowerConfig(
    port="COM5",
    id="1",
)

#sets the so-100's webcam to cap. will need to change the int in VideoCapture() to be the so100's webcam
cap = cv2.VideoCapture(2)

#Json Schema that will format the output of the VLM as a dictionary that send.action() can read
class Action(BaseModel):
    shoulder_pan_pos: float = Field(..., alias='shoulder_pan.pos', description="Rotation angle of the shoulder pan joint.")
    shoulder_lift_pos: float = Field(..., alias='shoulder_lift.pos', description="Lift angle of the shoulder joint.")
    elbow_flex_pos: float = Field(..., alias='elbow_flex.pos', description="Bend angle of the elbow joint.")
    wrist_flex_pos: float = Field(..., alias='wrist_flex.pos', description="Flexion angle of the wrist joint.")
    wrist_roll_pos: float = Field(..., alias='wrist_roll.pos', description="Rotation angle of the wrist joint.")
    gripper_pos: float = Field(..., alias='gripper.pos', description="Opening or closing position of the gripper.")


#function that moves the SOO-100 arm based on the dictionary that it is given
def movement(action: dict):

    robot.send_action(action)
    time.sleep(3)

    return action


#configures and connects the SO-100 arm to the computer
robot = SO100Follower(robot_config)
robot.connect()
print("Robot Connected")
#Get the current joint position of the SO-100 arm
current_pos = robot.get_observation()
print(current_pos)

#function that will put the SO-100 arm into the rest position
def rest():
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

    robot.send_action(pre_rest)
    time.sleep(3)
    robot.send_action(true_rest)

    return "Goodbye"

#function that sends a message to the VLM and outputs the response
def vlm_response(message):

    response = ollama.chat(model="llama3.2-vision", messages=message, format=Action.model_json_schema())

    #deletes the Frame image from the webcam once the image has been sent to the VLM
    try:
        os.remove(frame_path)
    except FileNotFoundError:
        print(f"Error: File '{frame_path}' not found.")
    except PermissionError:
        print(f"Error: Permission denied to delete '{frame_path}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return response

#The System prompt to the VLM
sys_prompt = """You are in control of a robotic arm. The arm has six joints.
You will be given an image of the arm’s current workspace and a generalized instruction describing the desired task.

Your job is to determine the *target joint positions* required for the arm to complete the task.

- Do NOT describe the movement in words.
- Do NOT repeat the current position.
- Output only a JSON dictionary showing the *desired next position values* for each joint key.
- Each key should match the format of the current position dictionary (e.g., 'shoulder_pan.pos', 'shoulder_lift.pos', etc.).
- Each value should represent the target angle or position (in degrees or radians, consistent with the input) the joint should move to.
- the maximum value for each joint is 98 and the minimum value is -98
- if you plan on moving a joint move it by at least 10 degrees
- shoulder_pan is the rotation angle of the shoulder pan joint. with 98 being most right and -98 being most left
- shoulder_lift is the lift angle of the shoulder joint.
- elbow_flex is the bend angle of the elbow joint.
- wrist_flex is the flexion angle of the wrist joint.
- wrist_roll is the rotation angle of the wrist joint.
- gripper is the opening or closing position of the gripper.
"""

#Gets the first task from the user
user_input = str(input("User: "))

#obtains a frame from the webcam and saves it to 'frame_cache/frame.jpeg'
ret, frame = cap.read()
frame_path = "frame_cache/frame.jpeg"
cv2.imwrite(frame_path, frame)
img_path = Path(frame_path).read_bytes()

# the message sent to the VLM including the image of the frame from the webcam
message = [
    {"role": "system", "content": sys_prompt},
    {"role": "user", "content": user_input, "images": [img_path]}
]

#gets the VLM response from the vlm_response function
vlm_content = vlm_response(message).message.content

#prints the vlm_response
print(vlm_content)
#converts the vlm_response into a dictionary
vlm_dict = json.loads(vlm_content)
print(vlm_dict)
#moves the arm in accordance to the vlm_response
movement(vlm_dict)

#takes tasks from the User until the user inputs -1
while True:
    user_input = input("You: ")
    if user_input == "-1":
        print(rest())
        robot.disconnect()
        break

    # obtains a frame from the webcam and saves it to 'frame_cache/frame.jpeg'
    ret, frame = cap.read()
    frame_path = "frame_cache/frame.png"
    cv2.imwrite(frame_path, frame)
    img_path = Path(frame_path).read_bytes()

    #compiles the next message being sent to the VLM
    message = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_input, "images": img_path}
    ]

    #Get the response from the vlm
    answer = vlm_response(message).message.content
    print("Bot:", answer)