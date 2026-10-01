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
- `cap:generate;ext=pdf;target=thumbnail`
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
urn = TaggedUrn.from_string("cap:generate;ext=pdf")

# Build programmatically (fluent interface)
urn = (TaggedUrnBuilder("cap")
       .marker("generate")
       .tag("ext", "pdf")
       .build())

# Check if URN matches a pattern (the pattern requires the `generate`
# marker; the URN's `ext=pdf` is unconstrained because the pattern has
# no `ext` tag).
pattern = TaggedUrn.from_string("cap:generate")
assert urn.conforms_to(pattern)

# conforms_to is a guarantee. "Some ext" is not guaranteed to be a pdf, and it
# could be one: that is meets.
some_ext = TaggedUrn.from_string("media:ext")
pdf = TaggedUrn.from_string("media:ext=pdf")
assert not some_ext.conforms_to(pdf)
assert some_ext.meets(pdf)

# A description that omits a key says nothing about it; a complete thing — a
# value's media, a cap's own tags — does not have it: that is satisfies.
uncompressed = TaggedUrn.from_string("media:ext=pdf;!compressed")
assert not pdf.conforms_to(uncompressed)
assert pdf.satisfies(uncompressed)

# Get specificity score
score = urn.specificity()
```

## Testing

```bash
pytest tests/
```

## License

MIT
