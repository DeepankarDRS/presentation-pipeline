"""Tests for the screenshot service's PowerPoint COM process cleanup safety net.

This covers only the pure PID-tracking logic (_list_powerpnt_pids, _kill_pids,
_kill_new_powerpnt_processes), which is testable via mocked subprocess calls
without needing comtypes or an actual PowerPoint install.
"""

from unittest.mock import MagicMock, patch

from src.compiler.screenshot import (
    _kill_new_powerpnt_processes,
    _kill_pids,
    _list_powerpnt_pids,
)

_TASKLIST_CSV = (
    '"POWERPNT.EXE","1234","Console","1","150,000 K"\r\n'
    '"POWERPNT.EXE","5678","Console","1","148,000 K"\r\n'
)


@patch("src.compiler.screenshot.subprocess.run")
def test_list_powerpnt_pids_parses_tasklist_csv(mock_run):
    mock_run.return_value = MagicMock(stdout=_TASKLIST_CSV, returncode=0)
    pids = _list_powerpnt_pids()
    assert pids == {"1234", "5678"}


@patch("src.compiler.screenshot.subprocess.run")
def test_list_powerpnt_pids_empty_when_none_running(mock_run):
    mock_run.return_value = MagicMock(stdout="INFO: No tasks are running which match the specified criteria.", returncode=0)
    pids = _list_powerpnt_pids()
    assert pids == set()


@patch("src.compiler.screenshot.subprocess.run")
def test_list_powerpnt_pids_returns_empty_on_exception(mock_run):
    mock_run.side_effect = OSError("tasklist not found")
    pids = _list_powerpnt_pids()
    assert pids == set()


@patch("src.compiler.screenshot.subprocess.run")
def test_kill_pids_calls_taskkill_for_each_pid(mock_run):
    _kill_pids({"111", "222"})
    called_pids = {c.args[0][2] for c in mock_run.call_args_list}
    assert called_pids == {"111", "222"}
    for c in mock_run.call_args_list:
        assert c.args[0][0] == "taskkill"
        assert "/F" in c.args[0]


@patch("src.compiler.screenshot.subprocess.run")
def test_kill_pids_does_not_raise_on_failure(mock_run):
    mock_run.side_effect = OSError("taskkill failed")
    _kill_pids({"999"})  # must not raise


@patch("src.compiler.screenshot.time.sleep")
@patch("src.compiler.screenshot._kill_pids")
@patch("src.compiler.screenshot._list_powerpnt_pids")
def test_kill_new_powerpnt_processes_only_targets_new_pids(mock_list, mock_kill, mock_sleep):
    """A PID that existed before the call (e.g. the user's own open PowerPoint) must never be touched."""
    mock_list.return_value = {"100", "200", "300"}  # 100 pre-existed; 200, 300 are new

    _kill_new_powerpnt_processes(pids_before={"100"})

    mock_kill.assert_called_once_with({"200", "300"})


@patch("src.compiler.screenshot.time.sleep")
@patch("src.compiler.screenshot._kill_pids")
@patch("src.compiler.screenshot._list_powerpnt_pids")
def test_kill_new_powerpnt_processes_noop_when_nothing_new(mock_list, mock_kill, mock_sleep):
    mock_list.return_value = {"100"}

    _kill_new_powerpnt_processes(pids_before={"100"})

    mock_kill.assert_not_called()
