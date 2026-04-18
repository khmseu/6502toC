from pathlib import Path

from .generator import generate_cpp
from .ir import build_ir
from .parser import parse_listing


def convert_listing_to_cpp(input_path: Path, output_path: Path) -> None:
    """Read listing file and write deterministic C++ scaffold."""
    listing_text = Path(input_path).read_text(encoding="ascii")
    parsed = parse_listing(listing_text)
    ir = build_ir(parsed)
    source_line_count = len(listing_text.splitlines())
    cpp_code = generate_cpp(ir, source_line_count)
    Path(output_path).write_text(cpp_code, encoding="ascii")
