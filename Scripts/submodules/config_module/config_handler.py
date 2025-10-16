import time
import yaml
from pathlib import Path
import lerobot.find_port as fp

# Resolve paths relative to the Scripts directory
SCRIPTS_DIR = Path(__file__).resolve().parents[2]
CONFIGS_DIR = SCRIPTS_DIR / "config_files"
CALIBRATION_DIR = CONFIGS_DIR / "arm_calibration"

CONFIG_STRUCTURE_PATH = CONFIGS_DIR / "config_structure.yaml"
CONFIG_PATH = CONFIGS_DIR / "config.yaml"


def copy_template_config(config_destination: Path = CONFIG_PATH) -> None:
    """
    Initializes a new config file based on the config structure schema.

    For each parameter defined in the structure, create a default value:
    - string: empty string
    - int/float: null (None)
    - if nullable is true: keep the empty/null default
    """
    structure = load_config_structure()
    defaults: dict[str, object] = {}
    for param_def in structure.get("parameters", []):
        name = param_def.get("name")
        ptype = param_def.get("type")
        if not name or not ptype:
            continue
        if "default" in param_def:
            defaults[name] = param_def["default"]
            continue
        # Fall back to type-based default
        if ptype == "string":
            defaults[name] = ""
        elif ptype in ("int", "float"):
            defaults[name] = None
        elif ptype == "bool":
            defaults[name] = False
        else:
            defaults[name] = None

    config_destination.parent.mkdir(parents=True, exist_ok=True)
    with config_destination.open("w") as f:
        yaml.safe_dump(defaults, f)


def config_file_exists(config_file: Path = CONFIG_PATH) -> bool:
    """
    Checks for config file in the specified location. Returns true if config file is detected
    """

    if config_file.exists():
        return True
    else:
        return False


def verify_config_file_schema(
    config: dict, template: dict | None = None
) -> tuple[bool, list[str]]:
    """
    Compares structure of config dict to template dict. Returns (ok, issues).
    Only validates presence and basic type conformance for non-empty values.
    """
    if template is None:
        template = load_config_structure()

    issues: list[str] = []
    for param_def in template.get("parameters", []):
        name = param_def.get("name")
        if not name:
            continue
        # Required unless explicitly nullable and empty
        present = name in config
        if not present:
            issues.append(f"missing:{name}")
            continue
        value = config.get(name)
        # Allow empty if nullable True
        if (value in (None, "")) and param_def.get("nullable", False):
            continue
        if value in (None, "") and not param_def.get("nullable", False):
            issues.append(f"empty:{name}")
            continue
        try:
            parameter_type_validation(param_def, config)
        except (AssertionError, TypeError) as e:
            issues.append(f"type:{name}:{e}")
            continue
        # Constraints check for non-empty values
        try:
            validate_constraints(param_def, value)
        except AssertionError as e:
            issues.append(f"constraint:{name}:{e}")
    return (len(issues) == 0, issues)


def verify_parameter(parameter: dict, config: dict) -> bool:
    """
    TODO Implement function.

    Verifies the structure of the given parameter from the config structure against the actual config file.
    """

    # 1. === Type validation ===
    try:
        parameter_type_validation(parameter, config)  # Will continue if types match
    except (AssertionError, TypeError):  # If the type assertion failed:
        return False
    
    # 2. === Nullable field validation ===

    # 3. === Constraint checking ===


def parameter_type_validation(parameter: dict, config: dict) -> bool:
    """
    Validates the type of the parameter in config against the config definition.
    """
    # Get the name of the parameter from the definition
    param_name = parameter.get('name')
    param_type = parameter.get('type')
    if not param_name or not param_type:
        raise TypeError("Invalid parameter definition: missing name or type")
    
    # Parameter type checking
    match param_type:
        case 'string':
            class_type = str
        case 'int':
            class_type = int
        case 'float':
            class_type = float
        case 'bool':
            class_type = bool
        case _:
            raise TypeError(
                f"Error: no type definition in parameter structure for parameter {param_name}"
            )
    
    assert isinstance(config[param_name], class_type), (
        f"Error: parameter {param_name} is not of type {class_type} in config file."
    )
    
    # If no error is raised:
    return True


def repair_config_file(
    broken_params: list[str],
    config: dict,
    template: dict | None = None,
) -> dict:
    """
    Repairs any broken or missing parameters in the config dict, using the template.
    Returns the updated config dict.
    """
    if template is None:
        template = load_config_structure()

    defs_by_name = {d.get("name"): d for d in template.get("parameters", []) if d.get("name")}
    for issue in broken_params:
        kind, _, rest = issue.partition(":")
        name, *_ = rest.split(":", 1)
        d = defs_by_name.get(name)
        if not d:
            continue
        # Use explicit default if present
        if "default" in d:
            config[name] = d["default"]
            continue
        # Reset to type-based default
        ptype = d.get("type")
        if ptype == "string":
            config[name] = ""
        elif ptype in ("int", "float"):
            config[name] = None
        else:
            config[name] = None
    return config


def load_config_file(config: Path = CONFIG_PATH) -> dict:
    """
    Opens a specified config file as a dictionary.
    """
    
    with config.open() as file:
        config_dict = yaml.safe_load(file) or {}
    return config_dict


def save_config_file(config_dict: dict, config_path: Path = CONFIG_PATH) -> None:
    """
    Writes the config dict to disk at the given path.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w") as f:
        yaml.safe_dump(config_dict, f)


def load_config_structure(structure_path: Path = CONFIG_STRUCTURE_PATH) -> dict:
    """
    Load the config structure YAML.
    """
    with structure_path.open() as f:
        return yaml.safe_load(f) or {}


def discover_port() -> str:
    """
    Discover the USB port for the MotorsBus by diffing connected ports.
    Interacts with the user to unplug/replug the device.
    """
    print("\nPlease ensure the robot is connected via USB cable. Once done, press Enter.")
    input()
    print("Finding all available ports for the MotorsBus.")
    ports_before = fp.find_available_ports()
    print("Ports registered. Remove the USB cable from your MotorsBus and press Enter when done.")
    input()
    time.sleep(0.5)
    ports_after = fp.find_available_ports()
    ports_diff = list(set(ports_before) - set(ports_after))
    if len(ports_diff) == 1:
        port = ports_diff[0]
        print(f"The port of this MotorsBus is '{port}'")
        print("Reconnect the USB cable and press Enter.")
        input()
        return port
    elif len(ports_diff) == 0:
        raise OSError(
            f"Could not detect the port. No difference was found ({ports_diff})."
        )
    else:
        raise OSError(
            f"Could not detect the port. More than one port was found ({ports_diff})."
        )


def get_config(config_path: Path = CONFIG_PATH, overrides: dict | None = None) -> dict:
    """
    Load and validate the config, creating/repairing it as needed using the configured structure.
    Also discovers and persists the device port when missing.
    """
    print("Loading config")

    # Ensure a config file exists
    if not config_file_exists(config_path):
        print("No config.yaml file found - creating new file.")
        copy_template_config(config_path)

    # Load the current config
    cfg = load_config_file(config_path)

    # Validate and repair basic schema issues
    ok, issues = verify_config_file_schema(cfg)
    if not ok:
        cfg = repair_config_file(issues, cfg)
        save_config_file(cfg, config_path)

    # Apply runtime overrides (if provided)
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                cfg[k] = v

    # Ensure required fields are populated or handled
    # device_port: if empty, discover it and persist
    if cfg.get("device_port") in (None, ""):
        print("Parameter 'device_port' is empty in 'config.yaml'. Starting port configuration...")
        try:
            cfg["device_port"] = discover_port()
            save_config_file(cfg, config_path)
            print(f"Device port set to {cfg['device_port']}")
        except Exception as e:
            # Gracefully allow running without a device port
            print(f"Port discovery failed: {e}. Skipping device connection.")
    else:
        print(f"Using port {cfg['device_port']} from config.yaml.")

    # calibration_file existence enforcement
    calib_file = cfg.get("calibration_file")
    if calib_file in (None, ""):
        # Already handled as empty via schema; attempt repair to default was run earlier
        pass
    else:
        path = CALIBRATION_DIR / str(calib_file)
        if not path.exists():
            # Try default from structure
            tmpl = load_config_structure()
            default_name = None
            for p in tmpl.get("parameters", []):
                if p.get("name") == "calibration_file":
                    default_name = p.get("default")
                    break
            if default_name:
                default_path = CALIBRATION_DIR / str(default_name)
                if default_path.exists():
                    print(
                        f"Calibration file '{path.name}' not found. Falling back to default '{default_name}'."
                    )
                    cfg["calibration_file"] = default_name
                    save_config_file(cfg, config_path)
                else:
                    raise FileNotFoundError(
                        f"Calibration file not found: {path}. Default '{default_name}' also missing at {default_path}."
                    )
            else:
                raise FileNotFoundError(
                    f"Calibration file not found: {path} and no default specified in structure."
                )

    return cfg


def validate_constraints(parameter: dict, value: object) -> None:
    """
    Validate constraints defined in the parameter schema against the value.
    Supported:
    - For strings: 'pattern' (regex), 'enum' (list of allowed)
    - For int/float: 'min', 'max' (inclusive)
    """
    ptype = parameter.get("type")
    if value in (None, ""):
        return
    if ptype == "string":
        import re
        enum = parameter.get("enum")
        if enum is not None:
            assert value in enum, f"value '{value}' not in enum {enum}"
        pattern = parameter.get("pattern")
        if pattern:
            assert re.fullmatch(pattern, str(value)) is not None, (
                f"value '{value}' does not match pattern {pattern}"
            )
    elif ptype in ("int", "float"):
        min_v = parameter.get("min")
        max_v = parameter.get("max")
        if min_v is not None:
            assert value >= min_v, f"value {value} < min {min_v}"
        if max_v is not None:
            assert value <= max_v, f"value {value} > max {max_v}"
