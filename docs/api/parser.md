# listing_to_cpp.parser

## Module Purpose

Parses EI-style assembler listing text into tolerant, typed records.

## Public API

### parse_listing(text: str) -> dict

Parses listing text and returns:

- `raw`: original input text
- `records`: ordered list of parsed line records

Recognized record types:

- `source_marker`
- `include_marker`
- `header_marker`
- `equ`
- `instruction`
- `data_directive`
- `comment`
- `unknown`

## Internal Helpers

### _is_mnemonic(token: str) -> bool

Checks token membership in known 65C02 mnemonic set.

### _parse_code_record(raw_line: str, line_number: int)

Attempts to parse address-based instruction or data-directive lines.

Highlights:

- Tolerates variable whitespace.
- Stops byte parsing before data directive tokens (`DB`, `DW`, `DS`, `ASC`, `STR`).
- Supports optional labels and comments.

## Record Shapes

Common keys include:

- `type`
- `line`
- `raw`

Type-specific keys include:

- `equ`: `name`, `value`, `is_current_location_alias`
- `instruction`: `address`, `bytes`, `label`, `mnemonic`, `operand`, `comment`
- `data_directive`: `address`, `label`, `directive`, `operand`
