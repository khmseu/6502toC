# listing_to_cpp.converter

## Module Purpose

Orchestrates the end-to-end conversion pipeline from listing text to C++ file.

## Public API

### convert_listing_to_cpp(input_path: Path, output_path: Path) -> dict

Reads an input listing and writes generated C++ output.

Return value:

- `{"warnings": list[dict]}`

Pipeline sequence:

1. Read listing text (`ascii`).
2. `parse_listing(listing_text)`.
3. `build_ir(parsed)`.
4. `run_diagnostics(parsed, ir)`.
5. `generate_cpp(ir, source_line_count)`.
6. Write output C++ (`ascii`).
7. Return merged warnings from IR and diagnostics.

## Warning Contract

Returned warning objects are dictionaries and may include keys such as:

- `kind`
- `message`
- `line`
- context-specific address/operand fields
