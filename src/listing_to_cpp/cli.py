import argparse
from pathlib import Path

from .converter import convert_listing_to_cpp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="listing-to-cpp",
        description="Convert a 65C02 listing file to C++ scaffold output.",
    )
    parser.add_argument("input_listing", help="Path to input listing file")
    parser.add_argument("output_cpp", help="Path to output C++ file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    convert_listing_to_cpp(Path(args.input_listing), Path(args.output_cpp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
