import json
import os

_PRESETS_DIR = os.path.dirname(os.path.abspath(__file__))

CATEGORIES = {
    "world": "world_presets",
    "agents": "agents_presets",
    "task": "task_presets",
}


def load_preset(category: str, name: str) -> dict:
    """Load a single JSON preset file by category and name, return as dict."""
    subdir = CATEGORIES.get(category)
    if subdir is None:
        raise ValueError(f"Unknown preset category '{category}'. Valid: {list(CATEGORIES.keys())}")
    path = os.path.join(_PRESETS_DIR, subdir, f"{name}.json")
    with open(path) as f:
        return json.load(f)


def blend_presets(category: str, names: list[str]) -> dict:
    """Load multiple presets and merge them sequentially (later overrides earlier)."""
    result = {}
    for name in names:
        preset = load_preset(category, name)
        result.update(preset)
    return result


def to_entries_json(config_dict: dict) -> str:
    """Convert a flat config dict to Unity entries JSON format.

    Input:  {"seed": 42, "tree_generation/density": 0.03}
    Output: '{"entries": [{"key": "seed", "value": "42"}, {"key": "tree_generation/density", "value": "0.03"}]}'

    All values are stringified to match WorldLoadingController's parser.
    """
    entries = [{"key": str(k), "value": str(v)} for k, v in config_dict.items()]
    return json.dumps({"entries": entries})
