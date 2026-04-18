"""Phase 4 tests: legal C++ emission and multi-entry support."""

from listing_to_cpp.generator import generate_cpp
from listing_to_cpp.ir import build_ir
from listing_to_cpp.parser import parse_listing

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_ir():
    return {"symbols": {}, "instructions": [], "io_accesses": [], "warnings": []}


def _ir_from_listing(text: str):
    return build_ir(parse_listing(text))


# ---------------------------------------------------------------------------
# 1. Valid C++ scaffolding
# ---------------------------------------------------------------------------


def test_scaffold_contains_cstdint_include():
    output = generate_cpp(_empty_ir(), 0)
    assert "#include <cstdint>" in output


def test_scaffold_contains_namespace_open_and_close():
    output = generate_cpp(_empty_ir(), 0)
    assert "namespace converted {" in output
    assert "}  // namespace converted" in output


def test_scaffold_contains_context_struct_with_registers():
    output = generate_cpp(_empty_ir(), 0)
    assert "struct Context {" in output
    assert "std::uint8_t A{0};" in output
    assert "std::uint8_t X{0};" in output
    assert "std::uint8_t Y{0};" in output
    assert "std::uint8_t SP{0xFFU};" in output
    assert "std::uint8_t P{0};" in output


def test_scaffold_contains_io_shim_declarations():
    output = generate_cpp(_empty_ir(), 0)
    assert "extern std::uint8_t io_read(std::uint16_t addr);" in output
    assert "extern void io_write(std::uint16_t addr, std::uint8_t val);" in output


def test_scaffold_contains_run_function_forward_decl_and_definition():
    output = generate_cpp(_empty_ir(), 0)
    assert "void run(Context& ctx);" in output
    assert "void run(Context& ctx) {" in output


def test_scaffold_contains_generated_from_lines_constant():
    output = generate_cpp(_empty_ir(), 42)
    assert "constexpr std::uint32_t generated_from_lines = 42;" in output


def test_scaffold_output_ends_with_newline():
    output = generate_cpp(_empty_ir(), 0)
    assert output.endswith("\n")


def test_scaffold_output_is_ascii_only():
    output = generate_cpp(_empty_ir(), 0)
    output.encode("ascii")  # must not raise


# ---------------------------------------------------------------------------
# 2. Symbol constants
# ---------------------------------------------------------------------------


def test_symbol_constants_emitted_for_resolved_equ():
    ir = _ir_from_listing("SCREEN EQU $C000\nCOUNT EQU 16\n")
    output = generate_cpp(ir, 2)
    assert "constexpr std::uint16_t SCREEN = 0xC000U;" in output
    assert "constexpr std::uint8_t COUNT = 0x10U;" in output


def test_symbol_constants_not_emitted_for_location_aliases():
    ir = _ir_from_listing("HERE EQU *\n")
    output = generate_cpp(ir, 1)
    assert "HERE" not in output


def test_symbol_name_sanitized_for_dotted_names():
    ir = _ir_from_listing("MY.SYM EQU $01\n")
    output = generate_cpp(ir, 1)
    # dot replaced with underscore
    assert "MY_SYM" in output


# ---------------------------------------------------------------------------
# 3. Multi-entry support
# ---------------------------------------------------------------------------


def test_multi_entry_labels_produce_entry_point_enum():
    ir = _ir_from_listing("1000 18       MAIN   CLC\n" "1001 60       HELPER RTS\n")
    output = generate_cpp(ir, 2)
    assert "enum class EntryPoint" in output
    assert "ENTRY_MAIN" in output
    assert "ENTRY_HELPER" in output


def test_multi_entry_labels_produce_wrapper_functions():
    ir = _ir_from_listing("1000 18       MAIN   CLC\n" "1001 60       HELPER RTS\n")
    output = generate_cpp(ir, 2)
    assert "void run_MAIN(Context& ctx)" in output
    assert "void run_HELPER(Context& ctx)" in output


def test_multi_entry_run_overload_takes_entry_point_parameter():
    ir = _ir_from_listing("1000 18       MAIN   CLC\n" "1001 60       HELPER RTS\n")
    output = generate_cpp(ir, 2)
    # forward decl with default argument
    assert (
        "void run(Context& ctx, EntryPoint entry = EntryPoint::ENTRY_MAIN);" in output
    )
    # definition without default (C++ rule)
    assert "void run(Context& ctx, EntryPoint entry) {" in output


def test_multi_entry_dispatch_uses_goto():
    ir = _ir_from_listing("1000 18       MAIN   CLC\n" "1001 60       HELPER RTS\n")
    output = generate_cpp(ir, 2)
    assert "goto _lbl_MAIN;" in output
    assert "goto _lbl_HELPER;" in output


def test_multi_entry_goto_labels_appear_in_body():
    ir = _ir_from_listing("1000 18       MAIN   CLC\n" "1001 60       HELPER RTS\n")
    output = generate_cpp(ir, 2)
    assert "_lbl_MAIN:" in output
    assert "_lbl_HELPER:" in output


def test_multi_entry_wrapper_delegates_to_run_with_enum():
    ir = _ir_from_listing("1000 18       MAIN   CLC\n")
    output = generate_cpp(ir, 1)
    assert "run(ctx, EntryPoint::ENTRY_MAIN);" in output


def test_single_label_also_generates_wrapper():
    ir = _ir_from_listing("1000 60       ENTRY  RTS\n")
    output = generate_cpp(ir, 1)
    assert "void run_ENTRY(Context& ctx)" in output
    assert "ENTRY_ENTRY" in output


# ---------------------------------------------------------------------------
# 4. Byte-wise operations on word-like symbols
# ---------------------------------------------------------------------------


def test_lo_byte_operand_emits_and_0xff():
    listing = "SCREEN EQU $C000\n1000 A9 00   LDA   #<SCREEN\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 2)
    assert "& 0xFFU" in output


def test_lo_byte_operand_emits_static_cast():
    listing = "SCREEN EQU $C000\n1000 A9 00   LDA   #<SCREEN\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 2)
    assert "static_cast<std::uint8_t>(SCREEN & 0xFFU)" in output


def test_hi_byte_operand_emits_shift_right_8():
    listing = "SCREEN EQU $C000\n1000 A9 C0   LDA   #>SCREEN\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 2)
    assert ">> 8" in output


def test_hi_byte_operand_emits_static_cast():
    listing = "SCREEN EQU $C000\n1000 A9 C0   LDA   #>SCREEN\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 2)
    assert "static_cast<std::uint8_t>((SCREEN >> 8) & 0xFFU)" in output


def test_lo_byte_result_assigned_to_accumulator():
    listing = "SCREEN EQU $C000\n1000 A9 00   LDA   #<SCREEN\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 2)
    assert "ctx.A = static_cast<std::uint8_t>(SCREEN & 0xFFU);" in output


def test_hi_byte_result_assigned_to_accumulator():
    listing = "SCREEN EQU $C000\n1000 A9 C0   LDA   #>SCREEN\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 2)
    assert "ctx.A = static_cast<std::uint8_t>((SCREEN >> 8) & 0xFFU);" in output


# ---------------------------------------------------------------------------
# 5. C000-CFFF I/O shim integration
# ---------------------------------------------------------------------------


def test_sta_to_c000_cfff_uses_io_write():
    listing = "1000 8D 00 C0   STA   $C000\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "io_write(0xC000U, ctx.A);" in output


def test_lda_from_c000_cfff_uses_io_read():
    listing = "1000 AD 00 C0   LDA   $C000\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "ctx.A = io_read(0xC000U);" in output


def test_stx_to_c000_cfff_uses_io_write_with_x():
    listing = "1000 8E 00 C0   STX   $C000\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "io_write(0xC000U, ctx.X);" in output


def test_ldx_from_c000_cfff_uses_io_read_into_x():
    listing = "1000 AE 00 C0   LDX   $C000\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "ctx.X = io_read(0xC000U);" in output


def test_symbolic_io_access_uses_correct_resolved_address():
    listing = "SCREEN EQU $C000\n1000 8D 00 C0   STA   SCREEN\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 2)
    assert "io_write(0xC000U, ctx.A);" in output


def test_io_access_comment_includes_original_operand():
    listing = "1000 8D 00 C0   STA   $C000\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    # comment with original mnemonic/operand should appear
    assert "STA" in output
    assert "$C000" in output


# ---------------------------------------------------------------------------
# 6. Indexed I/O access – runtime index register preserved
# ---------------------------------------------------------------------------


def test_sta_indexed_x_to_c000_uses_ctx_x_offset():
    listing = "1000 9D 00 C0   STA   $C000,X\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "io_write(0xC000U + ctx.X, ctx.A);" in output


def test_lda_indexed_x_from_c000_uses_ctx_x_offset():
    listing = "1000 BD 00 C0   LDA   $C000,X\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "ctx.A = io_read(0xC000U + ctx.X);" in output


def test_sta_indexed_y_to_c000_uses_ctx_y_offset():
    listing = "1000 99 00 C0   STA   $C000,Y\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "io_write(0xC000U + ctx.Y, ctx.A);" in output


def test_lda_indexed_y_from_c000_uses_ctx_y_offset():
    listing = "1000 B9 00 C0   LDA   $C000,Y\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "ctx.A = io_read(0xC000U + ctx.Y);" in output


def test_symbolic_indexed_io_access_preserves_ctx_x():
    listing = "SCREEN EQU $C000\n1000 9D 00 C0   STA   SCREEN,X\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 2)
    assert "io_write(0xC000U + ctx.X, ctx.A);" in output


def test_non_indexed_io_access_does_not_include_ctx_x_or_ctx_y():
    listing = "1000 8D 00 C0   STA   $C000\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "io_write(0xC000U, ctx.A);" in output
    assert "ctx.X" not in output.split("io_write")[1].split(";")[0]


# ---------------------------------------------------------------------------
# 7. Plain-immediate fallback behavior
# ---------------------------------------------------------------------------


def test_plain_immediate_hex_lda_stubs_to_runtime_warning():
    """LDA #$10 plain hex immediate: loads A and updates NZ flags."""
    listing = "1000 A9 10   LDA   #$10\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "ctx.A = 0x10U" in output
    assert "/* LDA #$10 */" in output


def test_plain_immediate_decimal_lda_emits_load():
    """LDA #16 (plain decimal immediate) loads A and updates NZ flags."""
    listing = "1000 A9 10   LDA   #16\n"
    ir = _ir_from_listing(listing)
    output = generate_cpp(ir, 1)
    assert "ctx.A = 0x10U" in output
    assert "/* LDA #16 */" in output
