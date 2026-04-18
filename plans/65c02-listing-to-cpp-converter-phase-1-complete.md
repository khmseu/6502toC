# Phase 1 Complete: Project Scaffold and CLI Skeleton

Phase 1 established a runnable Python project scaffold with a working CLI and baseline converter pipeline. The CLI now reads a listing file and writes deterministic legal C++ skeleton output, and the requested baseline tests pass.

**Files created/changed:**

- pyproject.toml
- `src/listing_to_cpp/__init__.py`
- `src/listing_to_cpp/cli.py`
- `src/listing_to_cpp/converter.py`
- `src/listing_to_cpp/parser.py`
- `src/listing_to_cpp/ir.py`
- `src/listing_to_cpp/generator.py`
- `tests/conftest.py`
- `tests/test_cli.py`
- `tests/test_converter.py`

**Functions created/changed:**

- listing_to_cpp.cli.main
- listing_to_cpp.converter.convert_listing_to_cpp
- listing_to_cpp.parser.parse_listing
- listing_to_cpp.ir.build_ir
- listing_to_cpp.generator.generate_cpp

**Tests created/changed:**

- tests.test_cli.test_cli_help_shows_usage
- tests.test_cli.test_cli_requires_arguments
- tests.test_cli.test_cli_converts_listing_to_cpp
- tests.test_converter.test_convert_listing_writes_expected_cpp_with_trailing_newline
- tests.test_converter.test_convert_listing_counts_last_line_without_trailing_newline
- tests.test_converter.test_convert_listing_is_deterministic

**Review Status:** APPROVED

**Git Commit Message:**
feat: scaffold listing-to-cpp converter CLI

- add Python project structure and package entrypoint
- implement minimal conversion pipeline to legal C++ skeleton
- add CLI and converter tests with deterministic output checks
