"""Tests for the first-run pixi bootstrap logic."""
import os

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
    monkeypatch.setattr(bootstrap, "pixi_env_bin_dirs", lambda: [])
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
    monkeypatch.setattr(bootstrap, "pixi_env_bin_dirs", lambda: [])
    monkeypatch.setattr(bootstrap.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(bootstrap, "_prompt_yes_no", lambda question: True)
    steps = []
    monkeypatch.setattr(bootstrap, "_install_pixi", lambda logger: steps.append("install") or True)
    monkeypatch.setattr(bootstrap, "_run_pixi_install", lambda logger: steps.append("run") or True)
    bootstrap.ensure_pixi(marker_path=marker)
    assert steps == ["install", "run"]
    assert marker.exists()


def test_run_setup_success_with_pixi_present(monkeypatch):
    monkeypatch.setattr(bootstrap, "pixi_available", lambda: True)
    monkeypatch.setattr(bootstrap, "_run_pixi_install", lambda logger: True)
    monkeypatch.setattr(bootstrap, "_verify_mafft", lambda logger: True)
    assert bootstrap.run_setup([]) == 0


def test_run_setup_installs_pixi_when_missing(monkeypatch):
    monkeypatch.setattr(bootstrap, "pixi_available", lambda: False)
    monkeypatch.setattr(bootstrap.sys.stdin, "isatty", lambda: False)
    steps = []
    monkeypatch.setattr(
        bootstrap, "_install_pixi", lambda logger: steps.append("install") or True
    )
    monkeypatch.setattr(
        bootstrap, "_run_pixi_install", lambda logger: steps.append("run") or True
    )
    monkeypatch.setattr(bootstrap, "_verify_mafft", lambda logger: True)
    assert bootstrap.run_setup([]) == 0
    assert steps == ["install", "run"]


def test_run_setup_returns_error_when_pixi_install_fails(monkeypatch):
    monkeypatch.setattr(bootstrap, "pixi_available", lambda: True)
    monkeypatch.setattr(bootstrap, "_run_pixi_install", lambda logger: False)
    assert bootstrap.run_setup([]) == 1


def test_run_setup_clean_removes_pixi_env(tmp_path, monkeypatch):
    managed = tmp_path / "_env"
    (managed / ".pixi" / "envs").mkdir(parents=True)
    (managed / "pixi.toml").write_text("[workspace]\n")  # shipped manifest
    monkeypatch.setattr(bootstrap, "managed_env_dir", lambda: managed)
    assert bootstrap.run_setup(["--clean"]) == 0
    assert not (managed / ".pixi").exists()
    # The shipped manifest is preserved so setup can run again.
    assert (managed / "pixi.toml").exists()


def test_find_pixi_toml_walks_up_to_repo():
    # In this editable/repo checkout the project pixi.toml is found by walk-up.
    manifest = bootstrap.find_pixi_toml()
    assert manifest is not None
    assert manifest.name == "pixi.toml"


def test_activate_pixi_env_prepends_bin_to_path(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setattr(bootstrap, "pixi_env_bin_dirs", lambda: [bin_dir])
    monkeypatch.setenv("PATH", "/usr/bin")
    activated = bootstrap.activate_pixi_env()
    assert activated == bin_dir
    assert bootstrap.os.environ["PATH"].split(os.pathsep)[0] == str(bin_dir)


def test_activate_pixi_env_returns_none_when_no_env(monkeypatch):
    monkeypatch.setattr(bootstrap, "pixi_env_bin_dirs", lambda: [])
    assert bootstrap.activate_pixi_env() is None


def test_managed_env_dir_is_inside_package():
    managed = bootstrap.managed_env_dir()
    assert managed.name == "_env"
    assert managed.parent.name == "mirscope"


def test_non_interactive_session_skips_prompt(tmp_path, monkeypatch):
    marker = tmp_path / "done"
    monkeypatch.setattr(bootstrap, "pixi_available", lambda: False)
    monkeypatch.setattr(bootstrap, "pixi_env_bin_dirs", lambda: [])
    monkeypatch.setattr(bootstrap.sys.stdin, "isatty", lambda: False)
    prompted = {"value": False}
    monkeypatch.setattr(
        bootstrap, "_prompt_yes_no", lambda q: prompted.__setitem__("value", True) or True
    )
    bootstrap.ensure_pixi(marker_path=marker)
    assert prompted["value"] is False
    assert marker.exists()
