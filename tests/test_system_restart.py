from unittest.mock import patch

from flask import Flask

from gui.api.system_api import _restart_server_process, system_api


def test_docker_restart_exits_for_container_supervisor_without_spawning_process():
    with patch("gui.api.system_api.time.sleep"), \
         patch("gui.api.system_api.get_runtime_capabilities", return_value={"runtime": "docker"}), \
         patch("gui.api.system_api.subprocess.Popen") as popen_mock, \
         patch("gui.api.system_api.os._exit") as exit_mock:
        _restart_server_process()

    popen_mock.assert_not_called()
    exit_mock.assert_called_once_with(0)


def test_desktop_restart_spawns_successor_before_exiting():
    with patch("gui.api.system_api.time.sleep"), \
         patch("gui.api.system_api.get_runtime_capabilities", return_value={"runtime": "desktop"}), \
         patch("gui.api.system_api.subprocess.Popen") as popen_mock, \
         patch("gui.api.system_api.os._exit") as exit_mock:
        _restart_server_process()

    args = popen_mock.call_args.args[0]
    assert args[-1] == "--restarted"
    popen_mock.assert_called_once()
    exit_mock.assert_called_once_with(0)


def test_restart_endpoint_schedules_runtime_aware_restart():
    app = Flask(__name__)
    app.register_blueprint(system_api, url_prefix="/api")

    with patch("gui.core.jobs.get_all_jobs", return_value=[]), \
         patch("gui.api.system_api.threading.Thread") as thread_mock:
        response = app.test_client().post("/api/system/restart")

    assert response.status_code == 200
    assert response.get_json() == {"status": "restarting"}
    assert thread_mock.call_args.kwargs["target"] is _restart_server_process
    assert thread_mock.call_args.kwargs["daemon"] is True
    thread_mock.return_value.start.assert_called_once_with()
