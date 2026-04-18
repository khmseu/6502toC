# Phase 3 Complete: IR and Address Resolution

Phase 3 implemented meaningful IR construction with symbol resolution and explicit I/O memory access classification for `0xC000-0xCFFF`. It now detects direct and symbolic explicit accesses (including indexed forms) and emits uncertainty warnings for unresolved indirect memory accesses.

**Files created/changed:**

- `src/listing_to_cpp/ir.py`
- `tests/test_converter.py`

**Functions created/changed:**

- `listing_to_cpp.ir.build_ir`
- `listing_to_cpp.ir._parse_numeric_literal`
- `listing_to_cpp.ir._split_operand_base_and_index`
- `listing_to_cpp.ir._resolve_explicit_operand_address`
- `listing_to_cpp.ir._is_unresolved_indirect_operand`

**Tests created/changed:**

- `tests.test_converter.test_build_ir_resolves_equ_symbols_to_numeric_values`
- `tests.test_converter.test_build_ir_detects_explicit_c000_cfff_accesses_direct_and_symbolic`
- `tests.test_converter.test_build_ir_detects_explicit_indexed_c000_cfff_accesses_direct_and_symbolic`
- `tests.test_converter.test_build_ir_resolves_symbols_case_insensitively_for_equ_and_operands`
- `tests.test_converter.test_build_ir_tags_unresolved_indirect_accesses_as_uncertain_warning`

**Review Status:** APPROVED

**Git Commit Message:**

feat: add IR symbol resolution and io classification

- build IR symbols and instruction records from parsed listing data
- classify explicit C000-CFFF accesses for direct and symbolic operands
- add warnings for unresolved indirect memory accesses and case-insensitive symbol lookup
