import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.orbstack.yml"
SCRIPT = ROOT / "scripts" / "orbstack-test.sh"
FIXTURE = ROOT / "tests" / "fixtures" / "orbstack-library"


def test_compose_uses_only_isolated_bind_mounts():
    content = COMPOSE.read_text(encoding="utf-8")

    assert "./.runtime-test/config:/config" in content
    assert "./.runtime-test/media-run:/media" in content
    assert "/Volumes" not in content
    assert "smb://" not in content.lower()
    assert "docker.sock" not in content
    assert "privileged:" not in content
    assert "cap_add:" not in content


def test_compose_is_localhost_only_and_non_restarting():
    content = COMPOSE.read_text(encoding="utf-8")

    assert '"127.0.0.1:5812:5001"' in content
    assert 'container_name: medienwerkzeug-orbstack-test' in content
    assert 'restart: "no"' in content
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
