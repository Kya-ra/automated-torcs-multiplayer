# `menu_multiplayer.py`

Prototype multiplayer frontend in `launch_menu/menu_multiplayer.py` (kept separate from `menu.py`).

## What Works

- Singleplayer launches backend with player count `1`.
- Multiplayer lets you choose `1..6` players.
- One `.py` file can be selected per active player.
- Launch validates selected files and starts `test.py`.

## Current Limitation

- Player count is connected to backend.
- Selected script paths are not used by backend yet (`test.py` does not parse them yet).

## Run

```bash
python3 launch_menu/menu_multiplayer.py
```

## Notes

- Uses `launch_menu/fonts/Serpentine Bold.otf` if available, otherwise falls back to Arial.

