"""Recursa launcher: the entry point PyInstaller freezes.

The app module is imported rather than frozen as the main script, so it is
collected as a readable .py file inside the bundle. Recursa's self-check reads
its own source (several invariant probes inspect code shape); a frozen main
script would ship only bytecode and those probes would fail.

    Recursa                 start the app
    Recursa --selfcheck     run the invariant catalogue headless, exit 0 if all pass
    Recursa --smoke-test    open the main window briefly, close it, exit 0
    --report=PATH           also write the check's output to PATH (a windowed
                            Windows build has no console to print to)
"""
import os
import sys
import tempfile


def _report(text):
    print(text)
    for arg in sys.argv:
        if arg.startswith("--report="):
            with open(arg.split("=", 1)[1], "a", encoding="utf-8") as fh:
                fh.write(text + "\n")


def _app():
    import nj_re_trainer_gui_V9_3 as app
    return app


def selfcheck():
    os.environ["HOME"] = tempfile.mkdtemp(prefix="recursa-selfcheck-")
    os.environ["USERPROFILE"] = os.environ["HOME"]
    app = _app()
    result = app.run_adversarial_catalogue()
    report = app.adversarial_catalogue_report(result)
    _report(report)
    failed = [e["name"] for e in result["entries"] if not e.get("passed")]
    uncaught = [e["name"] for e in result["entries"] if not e.get("caught_injection")]
    if failed or uncaught:
        _report(f"SELFCHECK FAILED {failed} {uncaught}")
        return 1
    _report("SELFCHECK OK")
    return 0


def smoke_test():
    os.environ["HOME"] = tempfile.mkdtemp(prefix="recursa-smoke-")
    os.environ["USERPROFILE"] = os.environ["HOME"]
    app = _app()
    errors = []
    win = app.TrainerApp()
    win.report_callback_exception = lambda *a: errors.append(a)
    for view in ("today", "map", "practice", "insights", "settings"):
        try:
            win.show_view(view)
            for _ in range(15):
                win.update()
        except Exception as e:  # noqa: BLE001
            errors.append((view, e))
    win.destroy()
    if errors:
        _report(f"SMOKE TEST FAILED {errors[:3]}")
        return 1
    _report("SMOKE TEST OK")
    return 0


def main():
    if "--selfcheck" in sys.argv:
        sys.exit(selfcheck())
    if "--smoke-test" in sys.argv:
        sys.exit(smoke_test())
    _app().main()


if __name__ == "__main__":
    main()
