from pathlib import Path

from .diagnostics import run_diagnostics
from .generator import generate_cpp
from .ir import build_ir
from .parser import parse_listing


def convert_listing_to_cpp(input_path: Path, output_path: Path) -> dict:
    """Read listing file and write deterministic C++ scaffold.

    Returns a dict with key ``warnings`` containing all diagnostic warnings
    collected during conversion (IR + heuristic diagnostics combined).
    """
    listing_text = Path(input_path).read_text(encoding="ascii")
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    diagnostic_warnings = run_diagnostics(parsed, ir)
    source_line_count = len(listing_text.splitlines())
    cpp_code = generate_cpp(ir, source_line_count)
    Path(output_path).write_text(cpp_code, encoding="ascii")
    return {
        "warnings": ir.get("warnings", []) + diagnostic_warnings,
    }
