"""Config loading shared by the environment, agents, and CLI.

Keeping this in one place is what makes the package "config-driven" in
practice: nothing else in traffic_drl should open a YAML file directly.
"""

from pathlib import Path
import yaml


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: str) -> dict:
    """Load a YAML config file and resolve its file-path fields relative
    to the config file's own directory, so configs remain portable
    regardless of the current working directory a command is run from.
    """
    config_path = Path(path).resolve()
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    base_dir = config_path.parent
    # `extends: other.yaml` inherits another config (resolved relative to
    # this file) and overrides only what this file sets.
    parent = config.pop("extends", None)
    parent_config = load_config(str(base_dir / parent)) if parent else {}
    for key in ("network_file", "route_file", "sumocfg_file"):
        if key in config and config[key]:
            config[key] = str((base_dir / config[key]).resolve())

    config["_config_dir"] = str(base_dir)
    return _deep_merge(parent_config, config)
