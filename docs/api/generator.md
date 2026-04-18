# listing_to_cpp.generator

## Module Purpose

Generates legal C++ from the IR.

## Public API

### generate_cpp(ir: dict, source_line_count: int) -> str

Emits deterministic C++ source with:

- `converted` namespace
- `Context` struct (`A`, `X`, `Y`, `SP`, `P`)
- external I/O shim declarations:
  - `io_read(std::uint16_t)`
  - `io_write(std::uint16_t, std::uint8_t)`
- symbol constants from resolved EQU values
- multi-entry dispatch and wrappers
- generated source line counter constant

## Internal Helpers

### _sanitize(name: str) -> str

Converts assembler symbols to valid C++ identifiers.

### _parse_numeric(raw: str) -> int | None

Parses `$HEX`, `0xHEX`, and decimal literals.

### _find_sym_cpp(name: str, resolved_syms: dict) -> str | None

Finds case-insensitive symbol mapping to sanitized C++ name.

### _emit_immediate_expr(operand: str, resolved_syms: dict) -> str | None

Emits C++ expression for supported immediates:

- `#<SYM` low byte extraction
- `#>SYM` high byte extraction

### _index_register_from_operand(operand: str) -> str | None

Extracts indexed suffix and returns `ctx.X` or `ctx.Y`.

### _emit_instruction_lines(instr: dict, io_lookup: dict, resolved_syms: dict) -> list[str]

Emits one instruction translation block.

Translation priorities:

1. Explicit `C000-CFFF` I/O access through shim calls.
2. Supported immediate byte extraction assignments.
3. Fallback stub statement for unsupported forms.

## Multi-Entry Model

When labels exist:

- emits `enum class EntryPoint`
- emits `run(Context&, EntryPoint)` with switch-to-label dispatch
- emits `run_<LABEL>(Context&)` wrapper for each entry
