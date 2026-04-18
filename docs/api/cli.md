# listing_to_cpp.cli

## Module Purpose

Command-line interface for converting a listing file into C++ output.

## Public API

### build_parser() -> argparse.ArgumentParser

Builds and returns the argument parser.

Arguments configured:

- `input_listing`: path to source listing file
- `output_cpp`: path for generated C++ output

### main(argv: list[str] | None = None) -> int

Runs CLI parsing, executes conversion, and prints warnings to stderr.

Behavior:

1. Parses command-line arguments.
2. Calls `convert_listing_to_cpp(Path(input_listing), Path(output_cpp))`.
3. Prints warning lines in format `[kind] message` to stderr.
4. Returns `0` on success.

## Side Effects

- Writes generated C++ to the specified output path via converter.
- Emits diagnostics to stderr.

## Entry Point

The package script `listing-to-cpp` maps to `listing_to_cpp.cli:main`.
