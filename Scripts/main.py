from lerobot import find_port as fp
import time
import os
import yaml

def main():
    print("Hello from so-arm101-llm-integration!")
    
    # Check for config file
    
    
    # Try to load config file
    try:
        with open("./config.yaml") as f:
            config = yaml.safe_load(f)
            if config["device_port"] == "":
                pass
            else:
                pass
            
    except:
        pass
    print(config)
    

'''
Find USB port of robot and set global USB variable - modified from find_port.py
'''
def find_port():
    print("Finding all available ports for the MotorsBus.")
    ports_before = fp.find_available_ports()
    print("Ports before disconnecting:", ports_before)

    print("Remove the USB cable from your MotorsBus and press Enter when done.")
    input()  # Wait for user to disconnect the device

    time.sleep(0.5)  # Allow some time for port to be released
    ports_after = find_port.find_available_ports()
    ports_diff = list(set(ports_before) - set(ports_after))

    if len(ports_diff) == 1:
        port = ports_diff[0]
        print(f"The port of this MotorsBus is '{port}'")
        print("Reconnect the USB cable and press enter")
        input()
        return port
    elif len(ports_diff) == 0:
        raise OSError(f"Could not detect the port. No difference was found ({ports_diff}).")
    else:
        raise OSError(f"Could not detect the port. More than one port was found ({ports_diff}).")
    
    


if __name__ == "__main__":
    main()
