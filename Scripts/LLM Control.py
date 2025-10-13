import ollama


# Default setting
STS_ID                      = 1                 # STServo ID : 1
BAUDRATE                    = 1000000           # STServo default baudrate : 1000000
DEVICENAME                  = 'COM5'    # Check which port is being used on your controller
                                                # ex) Windows: "COM1"   Linux: "/dev/ttyUSB0" Mac: "/dev/tty.usbserial-*"
STS_MINIMUM_POSITION_VALUE  =  0          # STServo will rotate between this value
STS_MAXIMUM_POSITION_VALUE  = 300
STS_MOVING_SPEED            = 500        # STServo moving speed
STS_MOVING_ACC              = 50         # STServo moving acc

Arm_pos=[1,1]
Target_pos=[9,6]

def movement(move: str):
    move = move.lower()

    if move == 'forward':
        Arm_pos[1] = Arm_pos[1] + 1
    elif move == 'backward':
        Arm_pos[1] = Arm_pos[1] - 1
    elif move == 'right':
        Arm_pos[0] = Arm_pos[0] + 1
    elif move == 'left':
        Arm_pos[0] = Arm_pos[0] - 1
    else:
        print("Error: Move input incorrect")

    return Arm_pos

def shoulder_pan(move_pos: int):
    if move_pos >= 654 and move_pos <= 3436:

        return "movement complete"

    else:

        return "invalid movement"


def shoulder_lift(move_pos):
    if move_pos >= 835 and move_pos <= 3410:

        return "movement complete"

    else:

        return "invalid movement"


def elbow_flex(move_pos):
    if move_pos >= 780 and move_pos <= 2988:

        return "movement complete"

    else:

        return "invalid movement"


def wrist_flex(move_pos):
    if move_pos >= 659 and move_pos <= 3126:

        return "movement complete"

    else:

        return "invalid movement"


def wrist_roll(move_pos):
    if move_pos >= 0 and move_pos <= 4095:

        return "movement complete"

    else:

        return "invalid movement"

    return move_pos

def gripper(move_pos):
    if move_pos >= 2035 and move_pos <= 3515:

        return "movement complete"

    else:

        return "invalid movement"



available_functions = {
  'movement': movement,
}

prompt = """You are controlling a robotic arm operating in a 10×10 grid workspace. 
    The grid is made of integer coordinates from (0,0) to (9,9). 
    The arm starts at position (""" + str(Arm_pos[0]) + """,""" + str(Arm_pos[1]) + """) 
    and must move to position (""" + str(Target_pos[0]) + """,""" + str(Target_pos[1]) + """).
    The arm can only move using these four movements: 
    forward,
    backward,
    right,
    left,
    You can only chose one of the four moves.
    What is the next move the arm should take?"""

messages = [
    {
        'role': 'user',
        'content': prompt,
    },
]
response = ollama.chat(model="llama3.2", messages=messages,
tools=[movement])

for tool in response.message.tool_calls or []:
  function_to_call = available_functions.get(tool.function.name)
  if function_to_call:
    print('Function output:', function_to_call(**tool.function.arguments))
  else:
    print('Function not found:', tool.function.name)

print(response['message']['content'])


while Arm_pos != Target_pos:
    if Arm_pos[0] > 10 or Arm_pos[1] > 10:

        if Arm_pos[0] > 10:
            Arm_pos[0] = 10
        elif Arm_pos[1] > 10:
            Arm_pos[1] = 10

        prompt = "Invalid Move. Moved arm outside of the work space. rest arm to a valid position. "
    else:
        prompt = ""

    prompt = prompt + """The arm position is now at (""" + str(Arm_pos[0]) + """,""" + str(Arm_pos[1]) + """)
    and must move to position (""" + str(Target_pos[0]) + """,""" + str(Target_pos[1]) + """).
    The arm can only move using these four movements:
    forward,
    backward,
    right,
    left,
    You can only chose 1 of the four moves."""

    response = ollama.chat(model="llama3.2", messages= [
        {
            'role': 'user',
            'content': prompt,
        },
    ], tools=[movement])
    for tool in response.message.tool_calls or []:
        function_to_call = available_functions.get(tool.function.name)
        if function_to_call:
            print('Function output:', function_to_call(**tool.function.arguments))
        else:
            print('Function not found:', tool.function.name)

    print(Arm_pos, Target_pos)
