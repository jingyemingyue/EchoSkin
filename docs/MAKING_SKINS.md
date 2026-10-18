# Making skins for EchoSkin

## Workflow

1. Copy `themes/midnight-studio/` to `themes/<your-id>/` and rename.
2. Edit `skin.json`: set `id` (must match the folder name), `name`, `author`, `description`.
3. Edit `theme.qss` with your colors. Keep the token values in `skin.json` in sync.
4. Take a real screenshot at 1280×800 running ReverbScope with your skin; save as `preview.png`.
5. Validate: `python tools/validate_skin.py themes/<your-id>/` (coming soon — for now check the list in SKIN_SPEC.md manually).
6. Open a PR adding your folder under `themes/`.

## Design guidance

- **One screen, one job.** ReverbScope's redesign is built around a focused dark canvas; skins should respect that, not fight it.
- **Restrained accents.** One accent color, used sparingly. Measurement UI is a tool, not a poster.
- **Readability first.** Text contrast must survive long sessions; test at 100% and 150% display scaling.
- **Plot colors.** `plot_curve` must stay distinguishable against `plot_grid` on `background`. Colorblind-safe palettes preferred.

## What not to do

- No background photographs behind measurement content — they hurt readability.
- No mockup previews. `preview.png` must be a screenshot of the real app.
- Do not rename `theme.qss` or `preview.png`; the loader expects those exact names.
