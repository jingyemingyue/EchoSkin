# Making skins for EchoSkin

## Workflow

1. Copy `themes/midnight-studio/` to `themes/<your-id>/` and rename.
2. Edit `skin.json`: set `id` (must match the folder name), `name`, `author`, `description`.
3. Edit `skin.json → tokens.colors` using ReverbScope main's token names (`bg`, `surface`, `surface_alt`, `border`, `text`, `muted`, `accent`, `accent_hover`, `accent_text`, `accent_soft`, `good`/`warn`/`bad`/`info` and their `_soft` variants, `grid`). Edit `theme.qss` with main's real selectors (see [SKIN_SPEC.md](SKIN_SPEC.md)) and only the token colours.
4. Take a real 1280×800 screenshot with the developer harness: `QT_QPA_PLATFORM=offscreen python scripts/preview_skin.py themes/<your-id> --reverbscope ../ReverbScope --demo --out themes/<your-id>/preview.png`.
5. Validate: `python scripts/check_skins.py --reverbscope ../ReverbScope --strict themes/<your-id>` (0 errors, 0 warnings).
6. Open a PR adding your folder under `themes/`.

## Design guidance

- **One screen, one job.** ReverbScope's redesign is built around a focused dark canvas; skins should respect that, not fight it.
- **Restrained accents.** One accent color, used sparingly. Measurement UI is a tool, not a poster.
- **Readability first.** Text contrast must survive long sessions; test at 100% and 150% display scaling.
- **Plot colors.** Chart series colours are not skinnable on main; keep `grid` subtle but visible on `bg`/`surface`.

## What not to do

- No background photographs behind measurement content — they hurt readability.
- No mockup previews. `preview.png` must be a screenshot of the real app.
- Do not rename `theme.qss` or `preview.png`; the spec and checker require those exact names.
