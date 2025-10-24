# LLM Control.py: Allows for the llama3.2 LLM model being run through Ollama on the same computer
# to manipulate the SO-100 Robotic Arm via set positions in accordance to the general instructions that the user provides
# Author: Stuart Kennedy U3239456


# THIRD PARTY APPLICATION NEEDED. needs the Ollama application running the llama3.2 model to work.
# Download Ollama here: https://ollama.com, Run this command in cmd "Ollama run Llama3.2"

import ollama
import time

from lerobot.robots.so100_follower import SO100FollowerConfig, SO100Follower

## if Ollama with llama3.2 installed is running on a server on the same network you uncomment this code
## Allows connection to an Ollama application running on a different computer on the same network
# client = ollama.Client(
#   host='http://localhost:11434'
# )

#Configure the SO-100 Arm will need to change port based on the port being used by the device
robot_config = SO100FollowerConfig(
    port="COM5",
    id="1",
)

#the function the LLM can call to change which position the arm is in
def positions(position: int):
    if position == 1:
        #puts the arm in the rest position
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

        return "Robot at the Rest Position"

    elif position == 2:
        #puts the arm in the control position where all joints are set to 0
        action = {
            "shoulder_pan.pos": 0,
            "shoulder_lift.pos": 0,
            "elbow_flex.pos": 0,
            'wrist_flex.pos': 0,
            "wrist_roll.pos": 0,
            "gripper.pos": 0,
        }

        robot.send_action(action)
        time.sleep(3)

        return "Robot at the Control Position"

    elif position == 3:
        #set the arm to be pointing straight up in the air
        action = {
            'shoulder_pan.pos': -2.3005032350826724,
            'shoulder_lift.pos': 4.776699029126206,
            'elbow_flex.pos': -88.8586956521739,
            'wrist_flex.pos': 6.201864612890134,
            'wrist_roll.pos': 0.073260073260073,
            'gripper.pos': 0.6756756756756757
        }

        robot.send_action(action)
        time.sleep(3)

        return "Robot at the Up Position"

    elif position == 4:
        #sets the arm to be pointing directly forward
        action = {
            'shoulder_pan.pos': -1.3659237958303407,
            'shoulder_lift.pos': 75.92233009708738,
            'elbow_flex.pos': -84.60144927536231,
            'wrist_flex.pos': 6.52614511552494,
            'wrist_roll.pos': 0.219780219780219,
            'gripper.pos': 0.6756756756756757
        }

        robot.send_action(action)
        time.sleep(3)

        return "Robot at the Forward Position"

    elif position == 5:
        #sets the end-affector to be in the most left position of the work place
        action = {
            'shoulder_pan.pos': -74.40690150970525,
            'shoulder_lift.pos': 74.99029126213591,
            'elbow_flex.pos': -84.51086956521739,
            'wrist_flex.pos': 6.52614511552494,
            'wrist_roll.pos': 0.219780219780219,
            'gripper.pos': 0.6756756756756757
        }

        robot.send_action(action)
        time.sleep(3)

        return "Robot at the Left Position"

    elif position == 6:
        #set the end-affector to be in the most right position in the workplace
        action = {
            'shoulder_pan.pos': 69.66211358734725,
            'shoulder_lift.pos': 80.73786407766988,
            'elbow_flex.pos': -84.69202898550725,
            'wrist_flex.pos': 6.52614511552494,
            'wrist_roll.pos': 0.219780219780219,
            'gripper.pos': 0.6756756756756757
        }

        robot.send_action(action)
        time.sleep(3)

        return "Robot at the Right Position"

    elif position == 7:
        #opens the gripper at the end-affector
        action = {
            'gripper.pos': 27.6756756756756757
        }

        robot.send_action(action)
        time.sleep(3)

        return "Gripper open"

    elif position == 8:
        #closes the gripper at the end-affector
        action = {
            'gripper.pos': 0.6756756756756757
        }

        robot.send_action(action)
        time.sleep(3)

        return "Gripper Closed"

    else:
        #if sent a position outside the scope return "Invalid Position"
        return "Invalid Position"


#configers & Connects the SO-100 arm
robot = SO100Follower(robot_config)
robot.connect()
print("Robot Connected")
#Gets the observation of what position each of the SO-100's joints are in
print(robot.get_observation())

#details the available functions for the LLM to use
available_functions = {
  'positions': positions,
}

#the system prompt sent to the LLM
sys_prompt = """ You are in control of a robotic arm. This robotic arm has 7 positions.
Position 1: the Rest position
Position 2: the Control position
Position 3: the Up position
Position 4: the Forward position
Position 5: the Left position
Position 6: the Right position
Position 7: the Open Gripper position"""

#the user input of the LLM's first task
user_input = str(input("User: "))

#compiles the message being sent to the LLM
messages = [
    {"role": "system", "content": sys_prompt},
    {"role": "user", "content": user_input},
]

# First response from the LLM. change ollama.chat to client.chat if connecting to Ollama via same network
response = ollama.chat(model="llama3.2", messages=messages,
tools=[positions])

#LLM calling the functions in tools
for tool in response.message.tool_calls or []:
  function_to_call = available_functions.get(tool.function.name)
  if function_to_call:
    print('Function output:', function_to_call(**tool.function.arguments))
  else:
    print('Function not found:', tool.function.name)

# Continue giving LLM tasks unless User inputs -1
while True:
    #gets new task from the user
    user_input = input("User: ")

    if  user_input == "-1":
        break  # exit loop on input of -1

    #Appends new task to the message being sent to the LLM
    messages.append({"role": "user", "content": user_input})

    answer = ""

    #Gets the next response from the LLM. change ollama.chat to client.chat if connecting to Ollama via same network
    response = ollama.chat(model="llama3.2", messages=messages,
                           tools=[positions])

    # LLM calling the functions in tools
    for tool in response.message.tool_calls or []:
        function_to_call = available_functions.get(tool.function.name)
        if function_to_call:
            answer = 'Function output: ' + function_to_call(**tool.function.arguments)
        else:
            answer = 'Function not found: ' + tool.function.name

    print("Bot:", answer)

    #appends the LLM's answers to the messages being sent
    messages.append({"role": "assistant", "content": answer})

#disconects the robot
robot.disconnect()