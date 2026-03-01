# tagged-urn-py

Python implementation of the Tagged URN system - a flat tag-based identifier system.

This is a port of the reference Rust implementation [tagged-urn-rs](https://github.com/machinefabric/tagged-urn-rs).

## Overview

Tagged URN provides a flat, tag-based identifier system with:
- Configurable prefixes (e.g., `cap:`, `myapp:`)
- Flat key=value tag pairs
- Wildcard support (`*`)
- Special values (`?` for unspecified, `!` for must-not-have)
- Pattern matching with subtype semantics
- Specificity-based best-match selection

## Format

```
prefix:key1=value1;key2=value2;...
```

Examples:
- `cap:op=generate;ext=pdf;target=thumbnail`
- `myapp:key="Value With Spaces"`
- `custom:a=1;b=2;c`  (value-less tag, equivalent to c=*)

## Case Handling

- **Prefix**: Normalized to lowercase
- **Keys**: Always normalized to lowercase
- **Unquoted values**: Normalized to lowercase
- **Quoted values**: Case preserved exactly

## Installation

```bash
pip install tagged-urn
```

## Usage

```python
from tagged_urn import TaggedUrn, TaggedUrnBuilder

# Parse from string
urn = TaggedUrn.from_string("cap:op=generate;ext=pdf")

# Build programmatically (fluent interface)
urn = (TaggedUrnBuilder("cap")
       .tag("op", "generate")
       .tag("ext", "pdf")
       .build())

# Check if URN matches a pattern
pattern = TaggedUrn.from_string("cap:op=*;ext=pdf")
assert urn.conforms_to(pattern)

# Get specificity score
score = urn.specificity()
```

## Testing

```bash
pytest tests/
```

## License

MIT
