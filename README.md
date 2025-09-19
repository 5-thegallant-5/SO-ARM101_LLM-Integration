# SO-ARM101_LLM-Integration
Integrating a Large Language Model (LLM) with a SO-ARM 101 teleoperation unit from LeRobot.

## Install Packages
### Python packages
The main packages required from Python are LeRobot, ffmpeg and PyTorch. I recommend creating a virtual environment for installing the packages. Not needed, but definitely recommended.

```
python -m venv .venv && source .venv/bin/activate
```

Then just run the following:

```
pip install -e .                # editable install
```

For a full list of packages, check the `pyproject.toml` file.