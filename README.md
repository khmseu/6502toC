# 6502toC

A converter that reads 65C02+SWEET16 assembler listing output (EI-style) and emits legal C++ code.

The generated C++ is intended to be correct-enough scaffolding for analysis and iterative refinement, not optimal hand-written output.

## What It Does

- Parses listing text into structured records (markers, EQU, instructions, data directives, comments, unknown lines).
- Builds an intermediate representation (IR) with:
  - symbol resolution for `EQU`
  - instruction extraction
  - explicit I/O access classification for `0xC000-0xCFFF`
  - unresolved indirect access warnings
- Emits legal C++ with:
  - a machine `Context` struct
  - multi-entry dispatch (`EntryPoint` enum + wrappers)
  - I/O shim calls for explicit `0xC000-0xCFFF` reads/writes
  - byte-wise symbol immediate support (`#<SYM`, `#>SYM`)
- Runs diagnostics for likely code/data ambiguity patterns.

## Why `0xC000-0xCFFF` Is Special

This memory range is treated as I/O. Explicit accesses in this segment are emitted through shim functions instead of direct memory expressions:

- `io_read(std::uint16_t addr)`
- `io_write(std::uint16_t addr, std::uint8_t val)`

You provide the shim implementations in your host/runtime.

## Project Layout

- `src/listing_to_cpp/parser.py`: tolerant listing parser
- `src/listing_to_cpp/ir.py`: symbol and operand resolution
- `src/listing_to_cpp/generator.py`: C++ emitter
- `src/listing_to_cpp/diagnostics.py`: warning heuristics
- `src/listing_to_cpp/converter.py`: pipeline orchestration
- `src/listing_to_cpp/cli.py`: CLI entrypoint
- `example/EI.LST`: sample listing input
- `tests/`: unit and integration tests

## Requirements

- Python 3.10+

## Install (Editable)

From repository root:

```bash
python3 -m pip install -e .
```

## CLI Usage

```bash
listing-to-cpp <input-listing> <output-cpp>
```

Example:

```bash
listing-to-cpp example/EI.LST out.cpp
```

Or with module execution:

```bash
python3 -m listing_to_cpp.cli example/EI.LST out.cpp
```

Warnings are printed to stderr in this format:

```text
[jump_to_data_region] JMP at $1000 targets $2001 which overlaps data interval $2000-$2003.
```

## Conversion Pipeline

1. Parse listing text into records.
2. Build IR:
   - resolve `EQU` symbols
   - classify explicit `0xC000-0xCFFF` accesses
   - flag unresolved indirect accesses
3. Run diagnostics:
   - data directives in executable ranges
   - jump/branch targets landing in data intervals
4. Generate C++ source.

## Multi-Entry Strategy

Multiple entry labels are represented with:

- `enum class EntryPoint`
- a single `run(Context&, EntryPoint)` dispatcher
- one wrapper function per entry label (`run_<LABEL>(Context&)`)

This keeps one shared translated body while preserving multiple valid entry points.

## Diagnostics Implemented

- `data_in_executable_region`
  - Triggered when a data directive overlaps the instruction address region.
- `jump_to_data_region`
  - Triggered when `JMP`/`JSR`/branch target overlaps a known data interval.
- `uncertain_indirect_access`
  - Triggered when an indirect memory operand cannot be resolved.

## Current Limits

- Output is legal but often stub-like for many instructions.
- Plain immediates (for example `#$10`) may still be emitted as stubs for some mnemonics.
- SWEET16-specific lowering is not fully implemented.
- Symbol name collisions after C++ sanitization are not yet diagnosed.

## Testing

Run all tests:

```bash
python3 -m pytest -q
```

Current suite should pass with 71 tests.

## Notes

- Input is read as ASCII and output is written as ASCII.
- If code-as-data is intentional in your source, expect warnings that may need manual interpretation.
