import os
import yaml
import keypad
import time
import save_manager
import code_audio
from scene_audio import SceneAudio

# Try to import payphone, but handle errors gracefully.
# On PC (no RPi.GPIO installed) this will always fail and fall back
# to DummyPayphone, which is exactly what we want for keyboard testing.
try:
    from payphone import payphone
    print("Payphone initialized successfully")
except Exception as e:
    print(f"Payphone hardware not available, using dummy (expected on PC): {e}")
    class DummyPayphone:
        def start_adventure(self): pass
        def stop_adventure(self): pass
    payphone = DummyPayphone()


class Scene:
    def __init__(self, id, text, connections, hidden_connections=None, items_granted=None,
                 items_required=None, timeout_after_audio=False, timeout_seconds=3,
                 disable_star_hash=False, is_ending=False, pre_audio=None, post_audio=None,
                 assigns_new_code=False):
        self.id = id
        self.text = text
        self.connections = connections
        self.hidden_connections = hidden_connections if hidden_connections else {}
        self.items_granted = items_granted if items_granted else []
        self.items_required = items_required if items_required else []
        self.timeout_after_audio = timeout_after_audio
        self.timeout_seconds = timeout_seconds
        self.disable_star_hash = disable_star_hash
        self.is_ending = is_ending  # marks this scene as a true story completion point
        # pre_audio/post_audio: scene_audio clip ids to play before/after dynamically
        # generated audio (e.g. a spoken code) is inserted into this scene. Only
        # meaningful for system scenes the engine triggers directly (see "new_code").
        self.pre_audio = pre_audio
        self.post_audio = post_audio
        # If true, the engine mints a fresh code the moment a player
        # transitions into this scene (see start_new_session()).
        self.assigns_new_code = assigns_new_code

    def display(self, inventory):
        print("-" * 50)
        print(self.text)
        for key, value in self.connections.items():
            print(f"{key}. {value[0]}")

    def get_next_scene(self, choice, inventory):
        if choice in self.hidden_connections:
            connection = self.hidden_connections[choice]

            if isinstance(connection, dict):
                print(f"DEBUG: Item-based branching for '{choice}', checking inventory: {list(inventory)}")
                best_match = None
                best_count = 0
                for item_list_str, target_scene in connection.items():
                    if item_list_str == "default":
                        continue
                    required_items = [item.strip() for item in item_list_str.split(',')]
                    if all(item in inventory for item in required_items):
                        if len(required_items) > best_count:
                            best_match = target_scene
                            best_count = len(required_items)
                if best_match:
                    return best_match, None
                elif "default" in connection:
                    if isinstance(connection["default"], str):
                        return connection["default"], None
                    else:
                        return None, "Invalid scene transition"
                else:
                    if choice == "timeout":
                        return None, "You need the right items to progress..."
                    else:
                        return None, "You don't have the right items."
            else:
                if isinstance(connection, str):
                    return connection, None
                else:
                    return None, "Invalid scene transition"

        try:
            choice_index = int(choice)
            if choice_index in self.connections:
                connection_data = self.connections[choice_index]

                if len(connection_data) >= 2 and not isinstance(connection_data[1], dict):
                    target_scene_id = connection_data[1]
                    required_items = connection_data[2] if len(connection_data) > 2 else []
                    alt_scene_id = connection_data[3] if len(connection_data) > 3 else None

                    if target_scene_id == "scene2" and "phone_number" not in inventory:
                        return "no_numbers_scene", None

                    if all(item in inventory for item in required_items):
                        return target_scene_id, None
                    elif alt_scene_id:
                        return alt_scene_id, None
                    else:
                        missing_items = [item for item in required_items if item not in inventory]
                        message = f"You can't do that. You need these items: {', '.join(missing_items)}"
                        return None, message

                elif len(connection_data) >= 2 and isinstance(connection_data[1], dict):
                    paths = connection_data[1]
                    for item, scene_id in paths.items():
                        if item in inventory and item != "default":
                            return scene_id, None
                    if "default" in paths:
                        return paths["default"], None
                    else:
                        return None, "You don't have the right item for this action."
            else:
                if "default" in self.hidden_connections:
                    return self.hidden_connections["default"], None

        except ValueError:
            if "wrong_code" in self.hidden_connections:
                return self.hidden_connections["wrong_code"], None
            pass

        return None, "Invalid choice. Try again."


def load_scenes():
    """Loads scenes from YAML files in the 'story' directory and its subdirectories."""
    scenes = {}

    if not os.path.exists("story"):
        print("ERROR: 'story' directory not found!")
        os.makedirs("story", exist_ok=True)
        print("Created directory: story")
        return scenes

    print(f"Files in story directory: {os.listdir('story')}")

    def process_yaml_file(filepath):
        try:
            with open(filepath, "r") as file:
                data = yaml.safe_load(file)
                formatted_connections = {}

                if isinstance(data["connections"], dict):
                    for key, value in data["connections"].items():
                        key_int = int(key)
                        if isinstance(value, str):
                            formatted_connections[key_int] = [f"Go to {value}", value, []]
                        elif isinstance(value, list):
                            if len(value) >= 2 and isinstance(value[1], dict):
                                formatted_connections[key_int] = value
                            else:
                                option_text = value[0]
                                target_scene = value[1]
                                required_items = value[2] if len(value) > 2 else []
                                alt_scene = value[3] if len(value) > 3 else None
                                formatted_connections[key_int] = [option_text, target_scene, required_items, alt_scene]
                        elif isinstance(value, dict) and "text" in value and "paths" in value:
                            formatted_connections[key_int] = [value["text"], value["paths"]]

                elif isinstance(data["connections"], list):
                    for i, scene_id in enumerate(data["connections"], 1):
                        formatted_connections[i] = [f"Go to {scene_id}", scene_id, []]

                scenes[data["id"]] = Scene(
                    id=data["id"],
                    text=data["text"],
                    connections=formatted_connections,
                    hidden_connections=data.get("hidden_connections", {}),
                    items_granted=data.get("items_granted", []),
                    items_required=data.get("items_required", []),
                    timeout_after_audio=data.get("timeout_after_audio", False),
                    timeout_seconds=data.get("timeout_seconds", 3),
                    is_ending=data.get("is_ending", False),
                    pre_audio=data.get("pre_audio"),
                    post_audio=data.get("post_audio"),
                    assigns_new_code=data.get("assigns_new_code", False)
                )
                print(f"Loaded scene: {data['id']} from {filepath}")
        except Exception as e:
            print(f"Error loading {filepath}: {e}")

    for root, dirs, files in os.walk("story"):
        for file in files:
            if file.endswith(".yaml"):
                filepath = os.path.join(root, file)
                process_yaml_file(filepath)

    scenes["no_numbers_scene"] = Scene(
        id="no_numbers_scene",
        text="You look at your phone but there are no numbers saved in your contacts. You need to find a phone number first.",
        connections={1: ["Go back", "intro", []]}
    )

    return scenes


def handle_timed_input(scene, scene_audio):
    timeout_seconds = scene.timeout_seconds

    if scene.timeout_after_audio:
        while scene_audio.is_playing():
            time.sleep(0.1)

    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            choice = keypad.wait_for_single_keypress(timeout=0.1)
            if choice:
                continue
        except Exception as e:
            print(f"DEBUG: Error during keypress check: {e}")
            continue

    return "timeout"


def play_system_scene(scene_id, scenes, scene_audio):
    """Plays a non-navigable 'system' scene's single audio clip (scene_audio/
    <id>.mp3) and blocks until it finishes. Used for one-off messages like
    the archived-code congratulations, which have no injected dynamic audio."""
    scene = scenes.get(scene_id)
    if scene:
        print(scene.text)
    scene_audio.play_scene_audio(scene_id)
    while scene_audio.is_playing():
        time.sleep(0.1)


def start_new_session(scenes, scene_audio):
    """Generates a fresh code, saves an empty session for it, and speaks it
    back to the player using the 'new_code' system scene's pre/post clips
    (story/new_code.yaml). Lands the player on 'hub', not 'intro' — intro is
    the pre-session narrative gate and shouldn't replay right after signup.
    Returns (code, current_scene, inventory)."""
    code = save_manager.generate_unique_code()
    save_manager.save(code, "hub", [])
    print(f"New code generated: {code}")

    new_code_scene = scenes.get("new_code")
    pre = new_code_scene.pre_audio if new_code_scene else None
    post = new_code_scene.post_audio if new_code_scene else None
    if new_code_scene:
        print(new_code_scene.text)

    code_audio.play_code_sequence(pre, code, post, scene_audio.scene_channel)
    return code, "hub", set()

def start_new_session_with_intro2(scenes, scene_audio):
    """Generates a fresh code, saves an empty session for it, and speaks it
    back to the player using the 'intro2' scene's pre/post clips. Lands the player on 'intro2'.
    Returns (code, current_scene, inventory)."""
    code = save_manager.generate_unique_code()
    save_manager.save(code, "intro2", [])
    print(f"New code generated: {code}")

    intro2_scene = scenes.get("intro2")
    pre = intro2_scene.pre_audio if intro2_scene else None
    post = intro2_scene.post_audio if intro2_scene else None
    if intro2_scene:
        print(intro2_scene.text)

    code_audio.play_code_sequence(pre, code, post, scene_audio.scene_channel)
    return code, "intro2", set()

def main():
    scenes = load_scenes()
    print(f"DEBUG: Loaded scenes = {list(scenes.keys())}")

    scene_audio = SceneAudio()

    print("\nGame Controls:")
    print("- Use number keys to select options")
    print("- Press 'h' at any time to hang up the phone")
    print("- Press '*' to start entering a code, then enter your code and press '#' when done")
    print("- Press '#' to view your inventory")
    print("\nWaiting for phone to be lifted...")

    if not os.path.exists("sounds"):
        os.makedirs("sounds", exist_ok=True)
        print("Created 'sounds' directory. Please add mp3 files for each keypad key.")

    if not os.path.exists("scene_audio"):
        os.makedirs("scene_audio", exist_ok=True)
        print("Created 'scene_audio' directory. Please add mp3 files for each scene (format: scene_id.mp3)")

    if not os.path.exists("digit_audio"):
        os.makedirs("digit_audio", exist_ok=True)
        print("Created 'digit_audio' directory. Add spoken-digit clips 0.mp3-9.mp3 here to hear codes read back.")

    while True:
        keypad.wait_for_hook_change(expected_state=True)
        keypad.reset_input_state()
        payphone.start_adventure()

        current_scene = "intro"
        inventory = set()
        code = None  # established only once a real save code is confirmed
        previous_scene = None

        while keypad.is_phone_lifted():
            scene = scenes.get(current_scene)
            if not scene:
                fallback = "intro" if code is None else "hub"
                print(f"Error: Scene '{current_scene}' not found! Resetting to {fallback}.")
                current_scene = fallback
                continue

            if not all(item in inventory for item in scene.items_required):
                missing_items = [item for item in scene.items_required if item not in inventory]
                print(f"You can't go there yet. You need: {', '.join(missing_items)}")
                time.sleep(2)
                current_scene = previous_scene if previous_scene else "intro"
                continue

            scene_audio.play_scene_audio(current_scene)
            scene.display(inventory)

            should_use_timeout = False
            if "timeout" in scene.hidden_connections:
                timeout_connection = scene.hidden_connections["timeout"]
                if isinstance(timeout_connection, dict):
                    if inventory:
                        for item_list_str, target_scene in timeout_connection.items():
                            if item_list_str == "default":
                                continue
                            required_items = [item.strip() for item in item_list_str.split(',')]
                            if all(item in inventory for item in required_items):
                                should_use_timeout = True
                                break
                    if not should_use_timeout and "default" in timeout_connection:
                        should_use_timeout = True
                else:
                    should_use_timeout = True

            if should_use_timeout:
                choice = handle_timed_input(scene, scene_audio)
            else:
                choice = keypad.wait_for_keypress()

            if not keypad.is_phone_lifted() or choice is None:
                print("Phone hung up. Game reset.")
                scene_audio.stop_audio()
                break

            if choice == 'h' or choice == 'H':
                print("Phone hung up. Resetting game...")
                scene_audio.stop_audio()
                break

            if choice == "#":
                print("\nReplaying scene audio...")
                scene_audio.stop_audio()
                scene_audio.play_scene_audio(current_scene)
                continue

            if choice == "*":
                scene_audio.stop_audio()

            previous_scene = current_scene

            for item in scene.items_granted:
                if item not in inventory:
                    inventory.add(item)
                    print(f"You obtained: {item}!")

            # Before a session code is established, a multi-digit entry
            # (typed via * ... #) is an attempted resume code, not ordinary
            # scene navigation — check it against saved sessions first.
            # No code is generated here on a miss; the player just retries
            # or explicitly confirms "I'm new" via call_start -> confirm_new.
            if code is None and len(choice) > 1:
                data = save_manager.load(choice)
                if data and not data["archived"]:
                    scene_audio.stop_audio()
                    code = choice
                    current_scene = data["scene"]
                    inventory = set(data["inventory"])
                    print(f"Resuming code {code} at '{current_scene}'.")
                elif data and data["archived"]:
                    play_system_scene("code_completed", scenes, scene_audio)
                    code, current_scene, inventory = start_new_session(scenes, scene_audio)
                    save_manager.save(code, current_scene, inventory)
                else:
                    print("Code not recognized. Try again, or press any number if you're new.")
                    time.sleep(1.5)
                continue

            next_scene, message = scene.get_next_scene(choice, inventory)

            if next_scene:
                if next_scene != current_scene:
                    scene_audio.stop_audio()
                current_scene = next_scene
                next_scene_obj = scenes.get(current_scene)

                if next_scene_obj and next_scene_obj.assigns_new_code and code is None:
                    if current_scene == "intro2":
                        code, current_scene, inventory = start_new_session_with_intro2(scenes, scene_audio)
                    else:
                        code, current_scene, inventory = start_new_session(scenes, scene_audio)
                    save_manager.save(code, current_scene, inventory)
                elif next_scene_obj and next_scene_obj.is_ending:
                    save_manager.archive(code, current_scene, inventory)
                    print(f"Code {code} archived — story completed.")
                elif code is not None:
                    save_manager.save(code, current_scene, inventory)
                # else: still in the pre-session flow (call_start/confirm_new) —
                # nothing to persist yet
            elif message:
                print(message)
                time.sleep(1.5)
            else:
                print("Invalid choice. Try again.")
                time.sleep(1)

        scene_audio.stop_audio()
        payphone.stop_adventure()
        print("Game reset. Waiting for phone to be lifted...")


if __name__ == "__main__":
    main()