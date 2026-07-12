"""Tests for the first-run pixi bootstrap logic."""
import mirscope.bootstrap as bootstrap


def test_skips_when_marker_exists(tmp_path, monkeypatch):
    marker = tmp_path / "done"
    marker.write_text("ok")
    called = {"pixi": False}
    monkeypatch.setattr(bootstrap, "pixi_available", lambda: called.__setitem__("pixi", True))
    bootstrap.ensure_pixi(marker_path=marker)
    assert called["pixi"] is False  # returned before checking pixi


def test_marks_done_when_pixi_available(tmp_path, monkeypatch):
    marker = tmp_path / "done"
    monkeypatch.setattr(bootstrap, "pixi_available", lambda: True)
    bootstrap.ensure_pixi(marker_path=marker)
    assert marker.exists()


def test_disabled_by_env_var(tmp_path, monkeypatch):
    marker = tmp_path / "done"
    monkeypatch.setenv("MIRSCOPE_NO_BOOTSTRAP", "1")
    bootstrap.ensure_pixi(marker_path=marker)
    assert not marker.exists()


def test_declined_installation_marks_done_without_installing(tmp_path, monkeypatch):
    marker = tmp_path / "done"
    monkeypatch.setattr(bootstrap, "pixi_available", lambda: False)
    monkeypatch.setattr(bootstrap.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(bootstrap, "_prompt_yes_no", lambda question: False)
    install_called = {"value": False}
    monkeypatch.setattr(
        bootstrap, "_install_pixi", lambda logger: install_called.__setitem__("value", True)
    )
    bootstrap.ensure_pixi(marker_path=marker)
    assert install_called["value"] is False
    assert marker.exists()


def test_accepted_installation_runs_installers(tmp_path, monkeypatch):
    marker = tmp_path / "done"
    monkeypatch.setattr(bootstrap, "pixi_available", lambda: False)
    monkeypatch.setattr(bootstrap.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(bootstrap, "_prompt_yes_no", lambda question: True)
    steps = []
    monkeypatch.setattr(bootstrap, "_install_pixi", lambda logger: steps.append("install") or True)
    monkeypatch.setattr(bootstrap, "_run_pixi_install", lambda logger: steps.append("run") or True)
    bootstrap.ensure_pixi(marker_path=marker)
    assert steps == ["install", "run"]
    assert marker.exists()


def test_non_interactive_session_skips_prompt(tmp_path, monkeypatch):
    marker = tmp_path / "done"
    monkeypatch.setattr(bootstrap, "pixi_available", lambda: False)
    monkeypatch.setattr(bootstrap.sys.stdin, "isatty", lambda: False)
    prompted = {"value": False}
    monkeypatch.setattr(
        bootstrap, "_prompt_yes_no", lambda q: prompted.__setitem__("value", True) or True
    )
    bootstrap.ensure_pixi(marker_path=marker)
    assert prompted["value"] is False
    assert marker.exists()
