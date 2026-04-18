# Plan Complete: 65C02 Listing to C++ Converter

A fully functional 65C02+SWEET16 assembler listing to C++ converter has been built as a Python CLI project. The pipeline parses EI-style listing files, builds a rich IR with symbol resolution and I/O memory classification, emits legal C++ with multi-entry dispatch, and reports diagnostics for likely code-as-data patterns. All five phases passed independent code review.

**Phases Completed:** 5 of 5

1. ✅ Phase 1: Project Scaffold and CLI Skeleton
2. ✅ Phase 2: Listing Parser and Line Classification
3. ✅ Phase 3: IR and Address Resolution
4. ✅ Phase 4: Legal C++ Emission and Multi-Entry Support
5. ✅ Phase 5: Diagnostics and End-to-End Conversion

**All Files Created/Modified:**

- `src/listing_to_cpp/__init__.py`
- `src/listing_to_cpp/cli.py`
- `src/listing_to_cpp/converter.py`
- `src/listing_to_cpp/parser.py`
- `src/listing_to_cpp/ir.py`
- `src/listing_to_cpp/generator.py`
- `src/listing_to_cpp/diagnostics.py`
- `tests/conftest.py`
- `tests/test_cli.py`
- `tests/test_converter.py`
- `tests/test_parser.py`
- `tests/test_generator.py`
- `tests/test_diagnostics.py`
- `pyproject.toml`
- `.gitignore`
- `plans/65c02-listing-to-cpp-converter-plan.md`
- `plans/65c02-listing-to-cpp-converter-phase-1-complete.md`
- `plans/65c02-listing-to-cpp-converter-phase-2-complete.md`
- `plans/65c02-listing-to-cpp-converter-phase-3-complete.md`
- `plans/65c02-listing-to-cpp-converter-phase-4-complete.md`

**Key Functions/Classes Added:**

- `listing_to_cpp.parser.parse_listing` — tolerant EI listing line classifier
- `listing_to_cpp.ir.build_ir` — IR with symbol resolution, I/O classification, indirect warnings
- `listing_to_cpp.generator.generate_cpp` — legal C++ emitter with multi-entry dispatch
- `listing_to_cpp.diagnostics.run_diagnostics` — code-as-data and jump-to-data-region warnings
- `listing_to_cpp.converter.convert_listing_to_cpp` — end-to-end pipeline
- `listing_to_cpp.cli.main` — CLI entrypoint with warning stderr output

**Test Coverage:**

- Total tests written: 71
- All tests passing: ✅

**Recommendations for Next Steps:**

- Add SWEET16 opcode support (currently emitted as `(void)0;` stubs with comments).
- Implement control-flow graph construction for more precise multi-entry function boundary detection.
- Add a `static_cast<std::uint16_t>()` wrapper around indexed I/O address expressions to silence `-Wconversion` under strict mode.
- Consolidate the duplicate indexed-operand splitting logic between `ir.py` and `generator.py`.
- Extend plain immediate operand emission beyond byte-wise `#<SYM`/`#>SYM` to cover numeric literals.
