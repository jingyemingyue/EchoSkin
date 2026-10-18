"""Validate EchoSkin skins, and check them against a ReverbScope checkout.

    python scripts/check_skins.py                         # schema + files only
    python scripts/check_skins.py --reverbscope ../ReverbScope [--strict] [themes/<id> ...]

Errors (exit 1): a skin.json that breaks docs/SKIN_SPEC.md, a missing or
empty theme.qss, a preview.png that is missing or not 1280x800.

Warnings (exit 0, or 1 with --strict), only with --reverbscope:
- a QSS selector naming a widget class, dynamic property / value, or
  objectName that the ReverbScope checkout does not use;
- a token key that is not in reverbscope/ui/theme.py LIGHT_TOKENS / DARK_TOKENS;
- reverbscope.min_version newer than the checkout's pyproject version;
- the checkout seems to have grown a skin loader while the manifest says
  ``"loader": "none"`` (time to update the spec);
- a colour in theme.qss that is not one of the skin's tokens;
- text or muted text below WCAG AA (4.5:1) on the skin's surfaces.

Standard library only, so CI needs no install step.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_VERSIONS = {"1.1"}
PREVIEW_SIZE = (1280, 800)
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
PEP440_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?(?:\.dev(\d+))?$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
TOP_KEYS = {
    "$schema", "spec_version", "id", "name", "version", "author", "license",
    "description", "description_zh", "base_scheme", "reverbscope", "files", "tokens",
}


class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0
        self.gha = os.environ.get("GITHUB_ACTIONS") == "true"

    def _emit(self, kind: str, path: Path | None, message: str) -> None:
        where = ""
        if path is not None:
            try:
                where = str(path.relative_to(ROOT))
            except ValueError:
                where = str(path)
        if self.gha:
            print(f"::{kind} file={where}::{message}")
        else:
            print(f"{kind}: {where}: {message}" if where else f"{kind}: {message}")

    def error(self, path: Path | None, message: str) -> None:
        self.errors += 1
        self._emit("error", path, message)

    def warn(self, path: Path | None, message: str) -> None:
        self.warnings += 1
        self._emit("warning", path, message)


def pep440_key(text: str) -> tuple[int, ...] | None:
    m = PEP440_RE.match(text)
    if not m:
        return None
    major, minor, patch, pre, pre_n, dev = m.groups()
    pre_rank = {"a": 0, "b": 1, "rc": 2, None: 3}[pre]
    return (int(major), int(minor), int(patch), pre_rank, int(pre_n or 0),
            -1 if dev is None else int(dev))


def png_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def relative_luminance(hex_color: str) -> float:
    def channel(i: int) -> float:
        v = int(hex_color[1 + 2 * i: 3 + 2 * i], 16) / 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(0) + 0.7152 * channel(1) + 0.0722 * channel(2)


def contrast(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


# --------------------------------------------------------------------- QSS ---

def qss_selectors(text: str) -> list[str]:
    """Every simple selector of every rule (comments stripped)."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    selectors: list[str] = []
    depth = 0
    buf = ""
    for ch in text:
        if ch == "{":
            if depth == 0:
                selectors.extend(s.strip() for s in buf.split(",") if s.strip())
            depth += 1
            buf = ""
        elif ch == "}":
            depth = max(depth - 1, 0)
            buf = ""
        elif depth == 0:
            buf += ch
    return selectors


ATTR_RE = re.compile(r"\[\s*([A-Za-z_][\w-]*)\s*(?:=\s*\"?([^\"\]]*)\"?)?\s*\]")
TYPE_RE = re.compile(r"(?<![\w#:.\-\[])(Q[A-Z]\w*)")
ID_SEL_RE = re.compile(r"#([A-Za-z_][\w-]*)")


def selector_parts(selector: str) -> tuple[set[str], list[tuple[str, str | None]], set[str]]:
    no_attr = ATTR_RE.sub("", selector)
    no_pseudo = re.sub(r"::?[\w-]+(?:\([^)]*\))?", "", no_attr)
    types = set(TYPE_RE.findall(no_pseudo))
    attrs = [(m.group(1), m.group(2)) for m in ATTR_RE.finditer(selector)]
    ids = set(ID_SEL_RE.findall(no_pseudo))
    return types, attrs, ids


# ------------------------------------------------------------- ReverbScope ---

class Checkout:
    """What a ReverbScope checkout's GUI actually exposes to a style sheet."""

    def __init__(self, root: Path) -> None:
        self.root = root
        pkg = root / "src" / "reverbscope"
        ui = pkg / "ui"
        if not ui.is_dir():
            raise SystemExit(f"error: {ui} not found; is {root} a ReverbScope checkout?")
        self.version = self._version(root / "pyproject.toml")
        self.types: set[str] = set()
        self.properties: dict[str, set[str]] = {}
        self.object_names: set[str] = set()
        self.tokens: set[str] = set()
        self.loader_hits: list[str] = []
        sources = {p: p.read_text(encoding="utf-8") for p in ui.rglob("*.py")}
        for path, text in sources.items():
            self.types.update(re.findall(r"\b(Q[A-Z]\w+)\b", text))
            for name, value in re.findall(
                r"setProperty\(\s*\"([\w-]+)\"\s*,\s*(\"[^\"]*\"|True|False|[\w.]+)", text
            ):
                values = self.properties.setdefault(name, set())
                if value == "True":
                    values.add("true")
                elif value == "False":
                    values.add("false")
                elif value.startswith('"'):
                    values.add(value.strip('"'))
            # widgets.label(text, "role") sets the role property.
            for role in re.findall(r"\blabel\([^()\n]*?,\s*\"([\w-]+)\"", text):
                self.properties.setdefault("role", set()).add(role)
            self.object_names.update(re.findall(r"setObjectName\(\s*\"([\w-]+)\"", text))
        theme = ui / "theme.py"
        if theme.is_file():
            text = sources[theme]
            # Selectors of the stock style sheet count as supported.
            for name, value in re.findall(r"\[([\w-]+)=\"([^\"]*)\"\]", text):
                self.properties.setdefault(name, set()).add(value)
            self.tokens = self._token_keys(text)
        for path in pkg.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if re.search(r"skin\.json|load_skin|SkinLoader|\.qss\b", text):
                self.loader_hits.append(str(path.relative_to(root)))

    @staticmethod
    def _version(pyproject: Path) -> str | None:
        if not pyproject.is_file():
            return None
        m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', pyproject.read_text(encoding="utf-8"))
        return m.group(1) if m else None

    @staticmethod
    def _token_keys(text: str) -> set[str]:
        keys: set[str] = set()
        for node in ast.walk(ast.parse(text)):
            target = None
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                target, value = node.target.id, node.value
            elif isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
                target, value = node.targets[0].id, node.value
            if target in {"LIGHT_TOKENS", "DARK_TOKENS"} and isinstance(value, ast.Dict):
                keys.update(k.value for k in value.keys if isinstance(k, ast.Constant))
        return keys


# ------------------------------------------------------------------ checks ---

def check_manifest(skin: Path, report: Report) -> dict | None:
    path = skin / "skin.json"
    if not path.is_file():
        report.error(path, "skin.json is missing")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.error(path, f"not valid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        report.error(path, "top level must be an object")
        return None

    def need_str(key: str, obj: dict, label: str) -> str | None:
        value = obj.get(key)
        if not isinstance(value, str) or not value.strip():
            report.error(path, f"`{label}` is required and must be a non-empty string")
            return None
        return value

    for key in sorted(set(data) - TOP_KEYS):
        report.warn(path, f"unknown field `{key}`")
    spec = data.get("spec_version")
    if spec not in SPEC_VERSIONS:
        report.error(path, f"`spec_version` must be one of {sorted(SPEC_VERSIONS)}, got {spec!r}")
    skin_id = need_str("id", data, "id")
    if skin_id and not ID_RE.match(skin_id):
        report.error(path, "`id` must be lowercase letters, digits and single hyphens")
    if skin_id and skin_id != skin.name:
        report.error(path, f"`id` {skin_id!r} must match the folder name {skin.name!r}")
    for key in ("name", "author", "description"):
        need_str(key, data, key)
    version = need_str("version", data, "version")
    if version and not SEMVER_RE.match(version):
        report.error(path, "`version` must be semver, e.g. 1.0.0")
    for key in ("description_zh", "license"):
        if key in data and not isinstance(data[key], str):
            report.error(path, f"`{key}` must be a string")
    if data.get("base_scheme") not in {"light", "dark"}:
        report.error(path, "`base_scheme` must be \"light\" or \"dark\"")

    rs = data.get("reverbscope")
    if not isinstance(rs, dict):
        report.error(path, "`reverbscope` object is required")
        rs = {}
    low = need_str("min_version", rs, "reverbscope.min_version") if rs else None
    if low and pep440_key(low) is None:
        report.error(path, "`reverbscope.min_version` must look like 0.5.0b3")
    high = rs.get("max_version")
    if high is not None and (not isinstance(high, str) or pep440_key(high) is None):
        report.error(path, "`reverbscope.max_version` must be null or a version like 0.5.0")
    if low and high and pep440_key(low) and pep440_key(high) and pep440_key(low) > pep440_key(high):
        report.error(path, "`reverbscope.min_version` is newer than `max_version`")
    if rs.get("loader", "none") not in {"none", "builtin"}:
        report.error(path, "`reverbscope.loader` must be \"none\" or \"builtin\"")

    files = data.get("files")
    if not isinstance(files, dict):
        report.error(path, "`files` object is required")
    else:
        if files.get("stylesheet") != "theme.qss":
            report.error(path, "`files.stylesheet` must be \"theme.qss\"")
        if files.get("preview") != "preview.png":
            report.error(path, "`files.preview` must be \"preview.png\"")

    tokens = data.get("tokens", {})
    if not isinstance(tokens, dict):
        report.error(path, "`tokens` must be an object")
    else:
        for key in sorted(set(tokens) - {"colors"}):
            report.warn(path, f"unknown tokens field `{key}` (spec 1.1 defines only `colors`)")
        colors = tokens.get("colors", {})
        if not isinstance(colors, dict):
            report.error(path, "`tokens.colors` must be an object")
        else:
            for key, value in colors.items():
                if not isinstance(value, str) or not HEX_RE.match(value):
                    report.error(path, f"`tokens.colors.{key}` must be #rrggbb, got {value!r}")
    return data


def check_files(skin: Path, report: Report) -> None:
    qss = skin / "theme.qss"
    if not qss.is_file() or not re.sub(r"/\*.*?\*/", "", qss.read_text(encoding="utf-8"), flags=re.S).strip():
        report.error(qss, "theme.qss is missing or has no rules")
    preview = skin / "preview.png"
    if not preview.is_file():
        report.error(preview, "preview.png is missing (a real screenshot is required)")
    else:
        size = png_size(preview)
        if size is None:
            report.error(preview, "preview.png is not a PNG")
        elif size != PREVIEW_SIZE:
            report.error(preview, f"preview.png is {size[0]}x{size[1]}, must be 1280x800")


def check_against(skin: Path, data: dict, rs: Checkout, report: Report) -> None:
    manifest = skin / "skin.json"
    low = (data.get("reverbscope") or {}).get("min_version")
    if rs.version and low and pep440_key(low) and pep440_key(rs.version):
        if pep440_key(low) > pep440_key(rs.version):
            report.warn(manifest, f"min_version {low} is newer than ReverbScope main ({rs.version})")
    loader = (data.get("reverbscope") or {}).get("loader", "none")
    if loader == "none" and rs.loader_hits:
        report.warn(manifest, "ReverbScope may have a skin loader now ("
                    + ", ".join(rs.loader_hits[:3]) + "); review docs/SKIN_SPEC.md")
    if loader == "builtin" and not rs.loader_hits:
        report.warn(manifest, "`loader: builtin` but no skin loader found in ReverbScope")

    colors = ((data.get("tokens") or {}).get("colors") or {})
    if rs.tokens:
        for key in sorted(set(colors) - rs.tokens):
            report.warn(manifest, f"token `{key}` is not in ReverbScope ui/theme.py")
    elif colors:
        report.warn(manifest, "ReverbScope ui/theme.py tokens not found; token keys unchecked")

    qss_path = skin / "theme.qss"
    if not qss_path.is_file():
        return
    text = qss_path.read_text(encoding="utf-8")
    seen: set[str] = set()
    for selector in qss_selectors(text):
        types, attrs, ids = selector_parts(selector)
        for name in sorted(types - rs.types):
            msg = f"selector `{selector}`: widget class {name} is not used by ReverbScope's GUI"
            if msg not in seen:
                seen.add(msg)
                report.warn(qss_path, msg)
        for prop, value in attrs:
            if prop not in rs.properties:
                msg = f"selector `{selector}`: property `{prop}` is never set by ReverbScope"
            elif value is not None and rs.properties[prop] and value not in rs.properties[prop]:
                known = ", ".join(sorted(rs.properties[prop]))
                msg = f"selector `{selector}`: `{prop}` is never \"{value}\" (known: {known})"
            else:
                continue
            if msg not in seen:
                seen.add(msg)
                report.warn(qss_path, msg)
        for name in sorted(ids - rs.object_names):
            msg = f"selector `{selector}`: objectName #{name} is not set by ReverbScope"
            if msg not in seen:
                seen.add(msg)
                report.warn(qss_path, msg)
    body = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    palette = {v.lower() for v in colors.values() if isinstance(v, str)}
    for hex_color in sorted({c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b", body)}):
        if palette and hex_color not in palette:
            report.warn(qss_path, f"colour {hex_color} is not one of the skin's tokens")

    full = {k: v for k, v in colors.items() if isinstance(v, str) and HEX_RE.match(v)}
    for fg, bg in (("text", "bg"), ("text", "surface"), ("text", "surface_alt"),
                   ("muted", "surface"), ("muted", "bg"), ("accent_text", "accent")):
        if fg in full and bg in full and contrast(full[fg], full[bg]) < 4.5:
            ratio = contrast(full[fg], full[bg])
            report.warn(manifest, f"contrast {fg} on {bg} is {ratio:.2f}:1, below WCAG AA 4.5:1")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skins", nargs="*", type=Path, help="skin folders (default: themes/*)")
    parser.add_argument("--reverbscope", type=Path, help="path to a ReverbScope checkout")
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args(argv)

    skins = args.skins or sorted(p for p in (ROOT / "themes").iterdir() if p.is_dir())
    report = Report()
    rs = Checkout(args.reverbscope.resolve()) if args.reverbscope else None
    if rs:
        print(f"ReverbScope checkout {rs.root} (version {rs.version or 'unknown'}), "
              f"{len(rs.properties)} dynamic properties, {len(rs.object_names)} objectNames, "
              f"{len(rs.tokens)} tokens, skin loader: {'maybe' if rs.loader_hits else 'none'}")
    for skin in skins:
        skin = skin.resolve()
        data = check_manifest(skin, report)
        check_files(skin, report)
        if rs and data is not None:
            check_against(skin, data, rs, report)
    print(f"{len(skins)} skin(s): {report.errors} error(s), {report.warnings} warning(s)")
    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
