"""Config loading shared by the environment, agents, and CLI.

Keeping this in one place is what makes the package "config-driven" in
practice: nothing else in traffic_drl should open a YAML file directly.
"""

from pathlib import Path
import yaml


def load_config(path: str) -> dict:
    """Load a YAML config file and resolve its file-path fields relative
    to the config file's own directory, so configs remain portable
    regardless of the current working directory a command is run from.
    """
    config_path = Path(path).resolve()
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    base_dir = config_path.parent
    for key in ("network_file", "route_file", "sumocfg_file"):
        if key in config and config[key]:
            config[key] = str((base_dir / config[key]).resolve())

    config["_config_dir"] = str(base_dir)
    return config
