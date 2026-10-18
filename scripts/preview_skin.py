"""Run ReverbScope's desktop GUI with an EchoSkin skin layered on top (developer preview).

ReverbScope main has NO skin loader (no Settings -> Appearance -> Import Skin,
no --stylesheet option, no environment variable for a style sheet). Its look
comes from ``reverbscope/ui/theme.py``: ``LIGHT_TOKENS`` / ``DARK_TOKENS`` and a
style sheet generated from them by ``stylesheet()``, applied by
``apply_application_chrome()``. Qt's own ``-stylesheet`` argument does not help
either: ``apply_application_chrome`` calls ``app.setStyleSheet`` right after the
application is created and replaces it.

This script is therefore a *development* harness, not a supported API. In its
own process only, it

1. forces the skin's ``base_scheme`` with ``REVERBSCOPE_COLOR_SCHEME``,
2. overlays ``skin.json -> tokens`` onto ``theme.LIGHT_TOKENS`` / ``DARK_TOKENS``
   (so the palette, the generated style sheet, chips, finding cards and
   charts all read the skin's colours), and
3. appends ``theme.qss`` after the stock style sheet (later rules win).

It edits nothing on disk; quitting the process restores the stock look.
These are private module attributes of ReverbScope and may change on main
without notice -- ``scripts/check_skins.py`` and CI exist to catch that.

    # interactive
    python scripts/preview_skin.py themes/midnight-studio --reverbscope ../ReverbScope
    # screenshot (synthetic demo data, no audio hardware)
    QT_QPA_PLATFORM=offscreen python scripts/preview_skin.py themes/midnight-studio \
        --reverbscope ../ReverbScope --demo --view fr --out themes/midnight-studio/preview.png
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path


def _apply_skin(skin_dir: Path) -> dict:
    manifest = json.loads((skin_dir / "skin.json").read_text(encoding="utf-8"))
    qss = (skin_dir / manifest["files"]["stylesheet"]).read_text(encoding="utf-8")
    scheme = manifest.get("base_scheme", "dark")
    os.environ["REVERBSCOPE_COLOR_SCHEME"] = scheme

    from reverbscope.ui import theme

    table = theme.DARK_TOKENS if scheme == "dark" else theme.LIGHT_TOKENS
    overrides = (manifest.get("tokens") or {}).get("colors") or {}
    unknown = sorted(set(overrides) - set(table))
    if unknown:
        print(f"warning: tokens not in ReverbScope theme.py, ignored: {unknown}", file=sys.stderr)
    table.update({k: v for k, v in overrides.items() if k in table})
    # Plot chrome is copied from the token tables at import time.
    plot = theme._DARK if scheme == "dark" else theme._LIGHT  # noqa: SLF001 - dev harness
    plot.update(
        {"bg": table["surface"], "fg": table["text"], "grid": table["grid"], "muted": table["muted"]}
    )
    stock = theme.stylesheet

    def skinned(t: dict[str, str] | None = None) -> str:
        return stock(t) + "\n/* --- EchoSkin: " + manifest["id"] + " --- */\n" + qss

    # apply_application_chrome() and MainWindow.restyle() look stylesheet up
    # in the module, so a theme switch in Settings keeps the skin.
    theme.stylesheet = skinned
    return manifest


def _make_demo(work: Path, lang: str) -> Path:
    """The synthetic demo room as a two-position project (as main's screenshot script does)."""
    from reverbscope.demo import DEMO_ROOM_NAME, run_demo
    from reverbscope.i18n import _
    from reverbscope.io.project_store import add_session, save_project
    from reverbscope.models.project import Project

    demo = work / f"demo-{lang}"
    run_demo(demo)
    save_project(demo, Project(name=_(DEMO_ROOM_NAME)))
    for label in ("A", "B"):
        (demo / f"position-{label.lower()}").rename(demo / f"{label}-1")
        add_session(demo, demo / f"{label}-1", position=label)
    return demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("skin", type=Path, help="skin folder, e.g. themes/midnight-studio")
    parser.add_argument("--reverbscope", type=Path, help="ReverbScope checkout (uses its src/)")
    parser.add_argument("--demo", action="store_true", help="open the synthetic demo project")
    parser.add_argument("--view", default="fr", help="view to show with --demo")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--size", default="1280x800")
    parser.add_argument("--out", type=Path, help="save a screenshot here and quit")
    args = parser.parse_args(argv)

    if args.reverbscope:
        sys.path.insert(0, str((args.reverbscope / "src").resolve()))
    os.environ["REVERBSCOPE_AUDIO_BACKEND"] = "fake"
    work = Path(tempfile.mkdtemp(prefix="echoskin-preview-"))
    os.environ["REVERBSCOPE_HOME"] = str(work / "home")
    try:
        manifest = _apply_skin(args.skin)
        from PySide6.QtWidgets import QApplication

        import reverbscope
        from reverbscope.i18n import activate
        from reverbscope.ui.main_window import MainWindow
        from reverbscope.ui.theme import apply_application_chrome

        print(f"ReverbScope from {Path(reverbscope.__file__).parent}", file=sys.stderr)
        activate(args.lang)
        app = QApplication.instance() or QApplication(sys.argv[:1])
        apply_application_chrome(app)

        def pump(seconds: float) -> None:
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                app.processEvents()
                time.sleep(0.01)

        width, height = (int(v) for v in args.size.lower().split("x"))
        window = MainWindow()
        window.resize(width, height)
        window.setWindowTitle(f"{window.windowTitle()} - EchoSkin: {manifest['name']}")
        window.show()
        pump(0.3)
        if args.demo:
            demo = _make_demo(work, args.lang)
            window.show_project(demo)
            window.model.wait_until_loaded()
            keys = [e.key for e in window.model.entries() if e.result is not None]
            window.model.set_baseline(keys[0])
            window.model.set_current(keys[-1])
            window.model.set_overlay(keys[0], True)
            window.model.set_overlay(keys[-1], True)
            window.show_view(args.view)
            pump(1.0)
        if args.out:
            pump(0.3)
            image = window.grab().toImage()
            if (image.width(), image.height()) != (width, height):
                print(f"warning: grabbed {image.width()}x{image.height()}", file=sys.stderr)
            image.save(str(args.out))
            print(args.out)
            window.close()
            pump(0.2)
            return 0
        return int(app.exec())
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
