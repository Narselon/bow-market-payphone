# Payphone save/resume test fork

This is a standalone fork for testing the new code-based save/resume/archive
system on a PC, before moving it onto the real payphone hardware. It is not
meant to be merged into your main repo directly — copy files over once you've
verified the behavior you want.

## Running on PC

```
pip install pygame pyyaml
python3 -u engine.py
```

No `RPi.GPIO` is required — `keypad.py` and `payphone.py`'s absence are both
handled gracefully:
- `payphone.py` isn't included in this fork at all, so the `from payphone
  import payphone` import fails and engine.py falls back to a no-op
  `DummyPayphone` automatically. No light/ring behavior to worry about while
  testing on PC.
- `keypad.py` detects the missing `RPi.GPIO` module and switches into its
  built-in PC simulation mode.

## Keyboard controls (PC simulation mode quirks)

- **Hook switch**: the terminal will prompt "Press Enter to simulate lifting
  the phone" / "...placing the phone back". Just press Enter each time, or
  type `skip` to bypass the hook check instantly (useful for rapid iteration).
- **Keypad**: type a single character then press Enter, for *each* key press.
  This matches how the real keypad delivers one key at a time, so a 6-digit
  code means typing a digit + Enter, six times in a row. Tedious but
  deliberate — it exercises the exact same code path as the real hardware.
- To enter a code and submit it, type each digit (Enter after each), then
  type `#` + Enter to submit. To request a brand-new code instead of
  resuming one, just type `#` + Enter immediately with nothing typed first.

## What the test scenario covers

`story/intro.yaml`, `find_item.yaml`, and `ending.yaml` are a minimal 3-scene
loop, not your real story — they exist purely to validate the save/resume/
archive mechanism end-to-end before you plug in real content:

1. Pick up → get a fresh 6-digit code (spoken back if `digit_audio/0.mp3`-
   `9.mp3` exist; otherwise it just prints to the console — no crash either
   way).
2. Press `1` → grants `widget`, then auto-returns to `intro` after 3s.
3. Press `0` at any point → confirms hub navigation never drops inventory.
4. Press `2` → reaches `ending.yaml`, which has `is_ending: true`. This
   archives the code (`save_manager.archive`) and grants `plothole`.
5. Hang up, lift again, re-enter the same code → since it's archived, you
   should see "Congratulations..." printed and immediately receive a new
   code, starting fresh at `intro` with an empty inventory.
6. Hang up, lift again, enter a code you never used → "Code not recognized"
   and a new session starts, same as pressing `#` with nothing typed.

## Swapping in your real scenario

Replace everything under `story/` with your actual scenes. The only new
requirement versus your existing story files: mark whichever scene(s)
represent true story completion with `is_ending: true` in their YAML. Every
other scene works exactly as before — this fork doesn't change any existing
scene-authoring conventions.

## Known gaps before converting to the real payphone

- `digit_audio/0.mp3` through `9.mp3` (spoken digits) aren't included —
  without them, codes are only shown in the console, not spoken aloud.
- No audio file backs the "congratulations, already completed" message —
  it's console-only right now (see `start_new_session` / the `archived`
  branch in `engine.py`'s `main()`). Add a scene-audio-style clip and a
  `scene_audio.play_scene_audio(...)`-style call there if you want it heard.
- `saves/*.json` accumulate indefinitely — fine for testing, but you may
  want a cleanup/expiry policy once this is live on real hardware.
