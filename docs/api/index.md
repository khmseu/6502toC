# API Reference

This section documents the Python modules in the conversion pipeline.

## Modules

- [listing_to_cpp.__init__](./init.md)
- [listing_to_cpp.cli](./cli.md)
- [listing_to_cpp.converter](./converter.md)
- [listing_to_cpp.parser](./parser.md)
- [listing_to_cpp.ir](./ir.md)
- [listing_to_cpp.generator](./generator.md)
- [listing_to_cpp.diagnostics](./diagnostics.md)

## Pipeline Order

1. `parse_listing(text)`
2. `build_ir(parsed_listing)`
3. `run_diagnostics(parsed_listing, ir)`
4. `generate_cpp(ir, source_line_count)`
5. `convert_listing_to_cpp(input_path, output_path)`
6. `main(argv)`
