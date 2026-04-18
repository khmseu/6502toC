import os
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str):
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    return subprocess.run(
        [sys.executable, "-m", "listing_to_cpp.cli", *args],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )


def test_cli_runs_with_input_and_output_arguments(tmp_path: Path):
    input_path = tmp_path / "input.lst"
    output_path = tmp_path / "out.cpp"
    input_path.write_text("SAMPLE LISTING\n", encoding="ascii")

    result = run_cli(str(input_path), str(output_path))

    assert result.returncode == 0
    assert output_path.exists()


def test_cli_help_behavior():
    result = run_cli("--help")

    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_cli_argument_error_behavior():
    result = run_cli()

    assert result.returncode != 0
    assert "usage:" in result.stderr.lower()


def test_cli_prints_conversion_warnings_to_stderr(tmp_path: Path):
    input_path = tmp_path / "input.lst"
    output_path = tmp_path / "out.cpp"
    input_path.write_text(
        "1000  4C 01 20          JMP   $2001\n"
        "2000              DB    $01,$02\n",
        encoding="ascii",
    )

    result = run_cli(str(input_path), str(output_path))

    assert result.returncode == 0
    assert output_path.exists()
    assert "jump_to_data_region" in result.stderr
