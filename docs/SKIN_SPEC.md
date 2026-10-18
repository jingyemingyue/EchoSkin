# skin.json specification

Version: **1.1** (tracks ReverbScope `main`, 0.5.0b3)

A skin is a folder `themes/<id>/` with `skin.json`, `theme.qss` and `preview.png`.
`scripts/check_skins.py` is the reference validator for this document.

## Important: ReverbScope main has no skin loader

ReverbScope `main` has **no** Settings → Appearance → Import Skin, no `--stylesheet`
option and no style-sheet environment variable. Its look is generated in
`reverbscope/ui/theme.py` from `LIGHT_TOKENS` / `DARK_TOKENS` and applied by
`apply_application_chrome()`, which replaces any Qt `-stylesheet` argument.

Skins are applied only through the developer harness `scripts/preview_skin.py`,
which overlays `tokens.colors` onto those dicts and appends `theme.qss` in its own
process. It relies on **private** `theme.py` names that may change without notice;
daily CI (`.github/workflows/check-skins.yml`) checks skins against `main` to catch it.
Nothing on disk is modified; quitting restores the stock look.

## Fields

| Field | Req. | Description |
| --- | --- | --- |
| `spec_version` | yes | `"1.1"` |
| `id` | yes | lowercase-hyphen id, must equal the folder name |
| `name`, `author`, `description` | yes | non-empty strings |
| `version` | yes | skin version, semver (`"1.1.0"`) |
| `base_scheme` | yes | `"light"` or `"dark"` — which stock token set the skin overlays |
| `reverbscope.min_version` | yes | PEP 440, e.g. `"0.5.0b3"`; must not be newer than the checked `main` |
| `reverbscope.max_version` | no | version or `null` (no upper bound) |
| `reverbscope.loader` | yes | `"none"` today (harness only); `"builtin"` reserved for a future in-app loader |
| `files.stylesheet` / `files.preview` | yes | exactly `"theme.qss"` / `"preview.png"` |
| `description_zh`, `license`, `$schema` | no | optional metadata |
| `tokens.colors` | no | colour overrides, see below |

## tokens.colors

Keys are exactly ReverbScope main's 19 theme token names; unknown keys are warnings,
missing keys fall back to the stock `base_scheme` value. Values are `#rrggbb`.

`bg`, `surface`, `surface_alt`, `border`, `text`, `muted`, `accent`, `accent_hover`,
`accent_text`, `accent_soft`, `good`, `good_soft`, `warn`, `warn_soft`, `bad`,
`bad_soft`, `info`, `info_soft`, `grid`

Chart **series** colours are not tokens on main and are **not skinnable**; only
`grid` and the surrounding chrome follow the skin.

## theme.qss selectors

`theme.qss` is appended after the stock style sheet (later rules win). Target Qt
widget classes plus the dynamic properties main actually sets, for example:

- `QLabel[role="…"]`: `title`, `page-title`, `subtitle`, `section`, `hint`,
  `kpi-label`, `kpi-value`, `kpi-sub`, `card-title`, `badge`, `pill`, `panel-title`, `count`
- boolean properties (`[x="true"]`): `card`, `primary`, `danger`, `panel`, `page`,
  `report`, `viewbar`, `subviewbar`, `viewtab`, `viewscroll`, `panelswitch`,
  `projecttab`, `strip`, `measurements`, `hover`, `measuring`
- valued properties: `phase`, `banner` (`warn`, `info`, …)

Selectors that main does not use are reported by the checker. Colours in
`theme.qss` should be values from the skin's own `tokens.colors`.

## Validation

`python scripts/check_skins.py --reverbscope <ReverbScope checkout> --strict`

- **Errors:** invalid/missing fields, missing or empty `theme.qss`, `preview.png`
  missing or not 1280×800.
- **Warnings** (fail with `--strict`): unknown selectors or token keys,
  `min_version` newer than main, a loader appearing on main while `loader` is
  `"none"`, QSS colours outside the tokens, text/muted contrast below WCAG AA 4.5:1.

`preview.png` must be a real screenshot, e.g. from
`QT_QPA_PLATFORM=offscreen python scripts/preview_skin.py themes/<id> --reverbscope <checkout> --demo --out themes/<id>/preview.png`.
