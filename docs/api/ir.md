# listing_to_cpp.ir

## Module Purpose

Builds an intermediate representation (IR) with resolved symbols, normalized instructions, I/O classifications, and unresolved-indirect warnings.

## Public API

### build_ir(parsed_listing) -> dict

Consumes parser output and returns IR:

- `symbols`: map of EQU symbols with resolved numeric values when possible
- `instructions`: normalized instruction records
- `io_accesses`: explicit `0xC000-0xCFFF` accesses
- `warnings`: IR-level warnings (currently unresolved indirect memory access)

## Internal Helpers

### _parse_numeric(value: str)

Parses numeric literal forms:

- `$HEX`
- `0xHEX`
- decimal

### _split_indexed_operand(operand: str)

Splits `base,index` forms and returns `(base, index|None)`.

### _resolve_operand_address(operand, symbols, symbol_lookup)

Resolves operand to `(address, source)` where source is:

- `direct`
- `symbolic`

Resolution behavior:

- ignores immediates starting with `#`
- handles indexed explicit forms by resolving base operand
- uses case-insensitive symbol lookup

## I/O Classification Rule

If resolved address is within `0xC000 <= addr <= 0xCFFF`, an `io_accesses` item is emitted with:

- `classification: explicit_c000_cfff`
- original operand and mnemonic
- resolved address

## Warnings

`uncertain_indirect_access` is produced when:

- operand looks indirect (contains parentheses)
- target cannot be resolved
