import ollama
import time

from lerobot.robots.so100_follower import SO100FollowerConfig, SO100Follower

robot_config = SO100FollowerConfig(
    port="COM5",
    id="1",
)

def positions(position: int):
    if position == 1:
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
        action = {
            'gripper.pos': 27.6756756756756757
        }

        robot.send_action(action)
        time.sleep(3)

        return "Gripper open"

    elif position == 8:
        action = {
            'gripper.pos': 0.6756756756756757
        }

        robot.send_action(action)
        time.sleep(3)

        return "Gripper Closed"

    else:
        return "Invalid Position"


robot = SO100Follower(robot_config)
robot.connect()
print("Robot Connected")
print(robot.get_observation())

available_functions = {
  'positions': positions,
}

sys_prompt = """ You are in control of a robotic arm. This robotic arm has 7 positions.
Position 1: the Rest position
Position 2: the Control position
Position 3: the Up position
Position 4: the Forward position
Position 5: the Left position
Position 6: the Right position
Position 7: the Open Gripper position"""

user_input = str(input("User: "))

messages = [
    {"role": "system", "content": sys_prompt},
    {"role": "user", "content": user_input},
]

# First response from the bot
response = ollama.chat(model="llama3.2", messages=messages,
tools=[positions])

#bot calling the functions in tools
for tool in response.message.tool_calls or []:
  function_to_call = available_functions.get(tool.function.name)
  if function_to_call:
    print('Function output:', function_to_call(**tool.function.arguments))
  else:
    print('Function not found:', tool.function.name)

# Continue the conversation:
while True:
    user_input = input("You: ")
    if  user_input == "-1":
        break  # exit loop on empty input

    messages.append({"role": "user", "content": user_input})

    answer = ""

    response = ollama.chat(model="llama3.2", messages=messages,
                           tools=[positions])

    # bot calling the functions in tools
    for tool in response.message.tool_calls or []:
        function_to_call = available_functions.get(tool.function.name)
        if function_to_call:
            answer = 'Function output: ' + function_to_call(**tool.function.arguments)
        else:
            answer = 'Function not found: ' + tool.function.name

    print("Bot:", answer)
    messages.append({"role": "assistant", "content": answer})

robot.disconnect()

# prompt = """You are controlling a robotic arm operating in a 10×10 grid workspace.
#     The grid is made of integer coordinates from (0,0) to (9,9).
#     The arm starts at position (""" + str(Arm_pos[0]) + """,""" + str(Arm_pos[1]) + """)
#     and must move to position (""" + str(Target_pos[0]) + """,""" + str(Target_pos[1]) + """).
#     The arm can only move using these four movements:
#     forward,
#     backward,
#     right,
#     left,
#     You can only chose one of the four moves.
#     What is the next move the arm should take?"""
#
# messages = [
#     {
#         'role': 'user',
#         'content': prompt,
#     },
# ]
# response = ollama.chat(model="llama3.2", messages=messages,
# tools=[sequences])
#
# for tool in response.message.tool_calls or []:
#   function_to_call = available_functions.get(tool.function.name)
#   if function_to_call:
#     print('Function output:', function_to_call(**tool.function.arguments))
#   else:
#     print('Function not found:', tool.function.name)
#
# print(response['message']['content'])
#
#
# while Arm_pos != Target_pos:
#     if Arm_pos[0] > 10 or Arm_pos[1] > 10:
#
#         if Arm_pos[0] > 10:
#             Arm_pos[0] = 10
#         elif Arm_pos[1] > 10:
#             Arm_pos[1] = 10
#
#         prompt = "Invalid Move. Moved arm outside of the work space. rest arm to a valid position. "
#     else:
#         prompt = ""
#
#     prompt = prompt + """The arm position is now at (""" + str(Arm_pos[0]) + """,""" + str(Arm_pos[1]) + """)
#     and must move to position (""" + str(Target_pos[0]) + """,""" + str(Target_pos[1]) + """).
#     The arm can only move using these four movements:
#     forward,
#     backward,
#     right,
#     left,
#     You can only chose 1 of the four moves."""
#
#     response = ollama.chat(model="llama3.2", messages= [
#         {
#             'role': 'user',
#             'content': prompt,
#         },
#     ], tools=[movement])
#     for tool in response.message.tool_calls or []:
#         function_to_call = available_functions.get(tool.function.name)
#         if function_to_call:
#             print('Function output:', function_to_call(**tool.function.arguments))
#         else:
#             print('Function not found:', tool.function.name)
#
#     print(Arm_pos, Target_pos)
