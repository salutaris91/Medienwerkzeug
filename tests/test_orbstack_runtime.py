import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.orbstack.yml"
SCRIPT = ROOT / "scripts" / "orbstack-test.sh"
FIXTURE = ROOT / "tests" / "fixtures" / "orbstack-library"
GITIGNORE = ROOT / ".gitignore"


def test_compose_uses_only_isolated_bind_mounts():
    content = COMPOSE.read_text(encoding="utf-8")

    assert '${MW_TEST_CONFIG_DIR:?MW_TEST_CONFIG_DIR is required}:/config' in content
    assert "./.runtime-test/media-run:/media" in content
    assert "/Volumes" not in content
    assert "smb://" not in content.lower()
    assert "docker.sock" not in content
    assert "privileged:" not in content
    assert "cap_add:" not in content
    assert "/.runtime-test-shared/" in GITIGNORE.read_text(encoding="utf-8")


def test_compose_is_localhost_only_and_matches_nas_restart_policy():
    content = COMPOSE.read_text(encoding="utf-8")

    assert '"127.0.0.1:5812:5001"' in content
    assert 'container_name: medienwerkzeug-orbstack-test' in content
    assert "platform: linux/amd64" in content
    assert "restart: unless-stopped" in content
    assert "MW_RUNTIME: docker" in content


def test_shell_script_has_valid_syntax():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_reset_dry_run_names_only_the_isolated_target():
    result = subprocess.run(
        ["bash", str(SCRIPT), "reset", "--dry-run"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert str(ROOT / ".runtime-test" / "media-run") in result.stdout
    assert "Dry run: no files changed." in result.stdout


def test_linked_worktree_shares_config_but_keeps_resettable_media_local(tmp_path):
    repository = tmp_path / "repository"
    linked_worktree = tmp_path / "linked-worktree"
    script_target = repository / "scripts" / "orbstack-test.sh"
    fixture_target = repository / "tests" / "fixtures" / "orbstack-library"
    script_target.parent.mkdir(parents=True)
    fixture_target.mkdir(parents=True)
    shutil.copy2(SCRIPT, script_target)
    (fixture_target / "fixture.txt").write_text("original\n", encoding="utf-8")

    commands = [
        ["git", "init"],
        ["git", "add", "scripts/orbstack-test.sh", "tests/fixtures/orbstack-library/fixture.txt"],
        [
            "git",
            "-c",
            "user.name=Runtime Test",
            "-c",
            "user.email=runtime@example.invalid",
            "commit",
            "-m",
            "add runtime fixture",
        ],
        ["git", "worktree", "add", "-b", "runtime-test", str(linked_worktree)],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    linked_script = linked_worktree / "scripts" / "orbstack-test.sh"
    init_result = subprocess.run(
        ["bash", str(linked_script), "init"],
        cwd=linked_worktree,
        check=False,
        capture_output=True,
        text=True,
    )
    assert init_result.returncode == 0, init_result.stderr

    shared_config = repository / ".runtime-test-shared" / "config"
    local_media = linked_worktree / ".runtime-test" / "media-run"
    runtime_env = linked_worktree / ".runtime-test" / "runtime.env"
    assert shared_config.is_dir()
    assert (local_media / "fixture.txt").read_text(encoding="utf-8") == "original\n"
    assert f"MW_TEST_CONFIG_DIR={shared_config}" in runtime_env.read_text(encoding="utf-8")

    runtime_env.write_text(
        "MW_TEST_UID=501\n"
        "MW_TEST_GID=20\n"
        "MW_TEST_IMAGE=medienwerkzeug:existing\n"
        "MW_TEST_SOURCE=branch-existing-deadbee\n",
        encoding="utf-8",
    )
    status_result = subprocess.run(
        ["bash", str(linked_script), "status"],
        cwd=linked_worktree,
        check=False,
        capture_output=True,
        text=True,
    )
    upgraded_env = runtime_env.read_text(encoding="utf-8")
    assert status_result.returncode == 0, status_result.stderr
    assert "MW_TEST_IMAGE=medienwerkzeug:existing" in upgraded_env
    assert "MW_TEST_SOURCE=branch-existing-deadbee" in upgraded_env
    assert f"MW_TEST_CONFIG_DIR={shared_config}" in upgraded_env

    config_sentinel = shared_config / "settings.json"
    config_sentinel.write_text('{"onboarding": "complete"}\n', encoding="utf-8")
    (local_media / "fixture.txt").write_text("changed\n", encoding="utf-8")
    reset_result = subprocess.run(
        ["bash", str(linked_script), "reset", "--yes"],
        cwd=linked_worktree,
        check=False,
        capture_output=True,
        text=True,
    )

    assert reset_result.returncode == 0, reset_result.stderr
    assert config_sentinel.read_text(encoding="utf-8") == '{"onboarding": "complete"}\n'
    assert (local_media / "fixture.txt").read_text(encoding="utf-8") == "original\n"


def test_fixture_covers_fsk_and_season_edge_cases():
    paths = {path.relative_to(FIXTURE).as_posix() for path in FIXTURE.rglob("*")}

    assert "Filme/Beispiel Film (2024)/movie.nfo" in paths
    assert "Filme/Film ohne FSK (2023)/movie.nfo" in paths
    assert "Filme/Film mit ungültiger FSK (2022)/movie.nfo" in paths
    assert "Serien/Beispielserie/tvshow.nfo" in paths
    assert "Serien/Beispielserie/Staffel 01/Beispielserie S01E01.nfo" in paths
    assert "Serien/Beispielserie/Staffel 01/Beispielserie S01E02.nfo" in paths
    assert "Serien/Beispielserie/Staffel Backup/Beispielserie Bonus.mkv" in paths
    assert "Serien/Serie ohne tvshow/Staffel 01/Serie ohne tvshow S01E01.nfo" in paths
