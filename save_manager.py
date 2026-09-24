import json
import os
import random
import time

SAVE_DIR = "saves"


def _path(code):
    return os.path.join(SAVE_DIR, f"{code}.json")


def generate_unique_code():
    """Generates a 6-digit code not already used by an existing save."""
    os.makedirs(SAVE_DIR, exist_ok=True)
    while True:
        code = "".join(str(random.randint(0, 9)) for _ in range(6))
        if not os.path.exists(_path(code)):
            return code


def load(code):
    """Returns {'scene', 'inventory', 'archived'} if the code exists, else None."""
    path = _path(code)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return {
            "scene": data.get("scene", "intro"),
            "inventory": data.get("inventory", []),
            "archived": data.get("archived", False),
        }
    except Exception as e:
        print(f"Error loading save for code '{code}': {e}")
        return None


def save(code, scene, inventory, archived=False):
    """Writes current scene + inventory (and archived status) for this code."""
    os.makedirs(SAVE_DIR, exist_ok=True)
    try:
        with open(_path(code), "w") as f:
            json.dump(
                {
                    "scene": scene,
                    "inventory": list(inventory),
                    "archived": archived,
                    "updated": time.time(),
                },
                f,
            )
    except Exception as e:
        print(f"Error saving progress for code '{code}': {e}")


def archive(code, final_scene, inventory):
    """Marks a code as completed/retired. It can still be loaded (to show the
    congratulations message) but should no longer accept normal play."""
    save(code, final_scene, inventory, archived=True)


def is_archived(code):
    data = load(code)
    return bool(data and data.get("archived"))
