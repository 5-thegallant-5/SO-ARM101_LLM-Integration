import yaml
from pathlib import Path

BASE_PATH = "./config_files/"

CONFIG_STRUCTURE_PATH = Path(BASE_PATH + "config_structure.yaml")
CONFIG_PATH = Path(BASE_PATH + "config.yaml")


def copy_template_config(config_destination: Path = CONFIG_PATH) -> None:
    """
    TODO Implement function.

    TODO Is this needed?

    Copies the template config file to the specified location.
    """

    pass


def config_file_exists(config_file: Path = CONFIG_PATH) -> bool:
    """
    Checks for config file in the specified location. Returns true if config file is detected
    """

    if config_file.exists():
        return True
    else:
        return False


def verify_config_file_schema(
    config: Path | dict = CONFIG_PATH, template: Path | dict = CONFIG_STRUCTURE_PATH
) -> tuple:
    """
    TODO Implement function.

    Compares structure of config file to template. Returns tuple:
        - Arg0: Successfully verified file? (bool)
        - Arg 1: List of missing or faulty fields.
    """
    pass


def verify_parameter(parameter: dict, config: Path | dict = CONFIG_PATH) -> bool:
    """
    TODO Implement function.

    Verifies the structure of the given parameter from the config structure against the actual config file.
    """

    # 1. === Type validation ===
    try:
        parameter_type_validation(parameter, config) # Will continue if types match
    except AssertionError: # If the type assertion failed:
       return False
    
    # 2. === Nullable field validation ===

    # 3. === Constraint checking ===


def parameter_type_validation(parameter: dict, config: Path | dict = CONFIG_PATH) -> bool:
    """
    Validates the type of the parameter in config against the config definition.
    """
    # Get the name of the parameter from the definition
    param_name = parameter['name']
    param_type = parameter['type']
    
    # Parameter type checking
    match param_type:
        case 'string':
            class_type = str  
        case 'int':
            class_type = int
        case 'float':            
            class_type = float
        case _:
            raise TypeError(f"Error: no type definition in parameter structure for parameter {param_name}")
    
    assert isinstance(config[param_name], class_type), f"Error: parameter {param_name} is not of type {class_type} in config file."
    
    # If no error is raised:
    return True


def repair_config_file(
    broken_params: list,
    config: Path | dict = CONFIG_PATH,
    template: Path | dict = CONFIG_STRUCTURE_PATH,
) -> None:
    """
    TODO Implement function.

    Repairs any broken parameters from the config file, based on the template file.
    """

    pass


def load_config_file(config: Path = CONFIG_PATH) -> dict:
    """
    Opens a specified config file as a dictionary.
    """
    
    file = config.open()
    config_dict = yaml.safe_load(file)

    return config_dict


def get_config(file_location: Path):
    """
    TODO Recreate this function with the above functions to make more modular.

    Config handler:
        - Checks if there is an existing config file
        - Creates a config file if none exists
        - Attempts to load file
        - If port does not exist in file, automatically scans and retrieves the port
        - Sets global var device_port to the correct port, before saving into file
    """
    print("Loading config")

    # # Check for config file
    # if not os.path.exists("./config_files/config.yaml"):
    #     print("No config.yaml file found - creating new file.")
    #     with open("./config_files/config.yaml", mode="w") as file:
    #         yaml.safe_dump(CONFIG_VARS, file)
    #         file.close()

    # # Try to load config file
    # try:
    #     with open("./config_files/config.yaml", mode="r+") as file:
    #         config = yaml.safe_load(file)

    #         # Case where device port is an empty string in the YAML file:
    #         if config["device_port"] == "":
    #             print(
    #                 "Parameter 'device_port' is empty in 'config.yaml'. Starting port configuration..."
    #             )
    #             CONFIG_VARS["device_port"] = find_port()

    #             # Save the result into the file
    #             file.seek(0)
    #             yaml.safe_dump(CONFIG_VARS, file)

    #         # Case where device port is in the YAML file:
    #         else:
    #             CONFIG_VARS["device_port"] = config["device_port"]
    #             print(f"Using port {CONFIG_VARS['device_port']} from config.yaml.")

    #         # Close config.yaml
    #         file.close()

    # except Exception as e:
    #     print("ERROR:", e)
