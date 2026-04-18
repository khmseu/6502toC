# Phase 4 Complete: Legal C++ Emission and Multi-Entry Support

Phase 4 implemented legal C++ emission from IR with a multi-entry dispatch strategy and entry wrappers. It also emits I/O shim calls for explicit `0xC000-0xCFFF` accesses, including indexed operands that correctly preserve `ctx.X`/`ctx.Y`, and supports legal byte-extraction expressions for `#<SYM` and `#>SYM` immediates.

**Files created/changed:**

- `src/listing_to_cpp/generator.py`
- `tests/test_generator.py`

**Functions created/changed:**

- `listing_to_cpp.generator.generate_cpp`
- `listing_to_cpp.generator._emit_instruction_lines`
- `listing_to_cpp.generator._emit_immediate_expr`
- `listing_to_cpp.generator._index_register_from_operand`
- `listing_to_cpp.generator._sanitize`

**Tests created/changed:**

- `tests.test_generator.test_cpp_scaffold_contains_namespace_context_and_shims`
- `tests.test_generator.test_multi_entry_emits_enum_dispatch_and_wrappers`
- `tests.test_generator.test_low_high_byte_symbol_immediates_emit_legal_cpp`
- `tests.test_generator.test_indexed_io_write_uses_ctx_x`
- `tests.test_generator.test_indexed_io_read_uses_ctx_y`
- `tests.test_generator.test_symbolic_indexed_io_uses_ctx_register`
- `tests.test_generator.test_non_indexed_io_access_does_not_include_ctx_x_or_ctx_y`
- `tests.test_generator.test_plain_immediate_hex_currently_stubs`
- `tests.test_generator.test_plain_immediate_decimal_currently_stubs`

**Review Status:** APPROVED

**Git Commit Message:**

feat: implement cpp emission with multi-entry dispatch

- generate legal C++ runtime scaffold with context and I/O shim hooks
- emit entry-point enum, dispatch switch/goto flow, and per-entry wrappers
- handle indexed C000-CFFF I/O and byte-wise symbol immediate expressions
