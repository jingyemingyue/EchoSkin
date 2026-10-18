# skin.json specification

Version: 1.0

Every EchoSkin theme is a folder containing `skin.json`, `theme.qss`, and `preview.png`. This document defines `skin.json`.

## Required fields

| Field | Type | Description |
| --- | --- | --- |
| `id` | string | Unique skin id, lowercase, hyphens only, e.g. `"midnight-studio"` |
| `name` | string | Display name, e.g. `"Midnight Studio"` |
| `version` | string | Skin version (semver), e.g. `"1.0.0"` |
| `author` | string | Author name or handle |
| `description` | string | One-line English description |
| `reverbscope.min_version` | string | Minimum supported ReverbScope version, e.g. `"0.5.0b3"` |
| `files.stylesheet` | string | QSS filename, must be `"theme.qss"` |
| `files.preview` | string | Preview image filename, must be `"preview.png"` |

## Optional fields

| Field | Type | Description |
| --- | --- | --- |
| `description_zh` | string | One-line Chinese description |
| `license` | string | Skin license, default `"MIT"` |
| `reverbscope.max_version` | string \| null | Maximum tested version, `null` = no upper bound |
| `tokens` | object | Design tokens consumed by the skin loader (see below) |

## Design tokens

`tokens` mirrors ReverbScope's `ui/design/tokens.py`. The skin loader applies them to widgets and pyqtgraph plots that QSS cannot reach. All token fields are optional; missing fields fall back to ReverbScope defaults.

```json
"tokens": {
  "colors": {
    "background": "#0e1116",
    "surface": "#161b22",
    "surface_raised": "#1c2330",
    "text_primary": "#e6e9ee",
    "text_secondary": "#9aa4b2",
    "accent": "#1a7f8e",
    "accent_hover": "#22a0b2",
    "success": "#3fb950",
    "warning": "#d29922",
    "error": "#f85149",
    "plot_curve": "#1a7f8e",
    "plot_grid": "#2a3340"
  },
  "typography": {
    "title_size_px": 20,
    "title_weight": 700,
    "kpi_size_px": 28,
    "kpi_weight": 600,
    "body_size_px": 13
  },
  "page_margin": 20,
  "section_gap": 16,
  "corner_radius": 6
}
```

Rules:
- Colors must be `#rrggbb` hex.
- `plot_curve` / `plot_grid` style pyqtgraph curves and grids.
- QSS (`theme.qss`) and tokens must agree — do not define a color in one place and contradict it in the other.

## Validation

A skin folder is valid when:
1. `skin.json` parses and contains all required fields.
2. `theme.qss` exists and is non-empty.
3. `preview.png` exists, is 1280×800, and is a real screenshot (not a mockup).
4. `id` matches the folder name.
