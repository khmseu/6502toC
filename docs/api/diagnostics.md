# listing_to_cpp.diagnostics

## Module Purpose

Runs heuristic diagnostics for likely code/data ambiguity patterns.

## Public API

### run_diagnostics(parsed_listing: dict, ir: dict) -> list[dict]

Returns warning dictionaries produced by heuristic checks.

Current heuristics:

1. `data_in_executable_region`
   - Data directive intervals overlapping the instruction address span.
2. `jump_to_data_region`
   - Branch/jump targets overlapping known data intervals.

## Internal Helpers

### _parse_hex_address(addr: str | None) -> int | None

Parses hex addresses from parser-style address fields.

### _parse_numeric_token(token: str | None) -> int | None

Parses `$HEX`, `0xHEX`, decimal tokens.

### _string_literal_length(operand: str) -> int | None

Returns string payload length for quoted `ASC`/`STR` operands.

### _count_csv_values(operand: str) -> int | None

Counts comma-separated values for `DB`/`DW` sizing.

### _data_size_bytes(record: dict) -> int

Computes data directive size:

- `DB`: number of entries
- `DW`: 2 * number of entries
- `DS`: requested count
- `ASC`/`STR`: string length
- fallback: 1 byte

### _data_interval(record: dict) -> tuple[int, int] | None

Computes inclusive address interval `[start, end]`.

### _resolve_target(operand: str, symbol_lookup: dict) -> int | None

Resolves branch/jump target from numeric or symbolic operand.

## Warning Shape

Common warning fields:

- `kind`
- `message`
- `line`

Additional context fields vary by heuristic and include addresses and intervals.
