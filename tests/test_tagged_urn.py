import pytest
from tagged_urn import TaggedUrn, TaggedUrnBuilder, UrnMatcher, TaggedUrnError


# TEST0001: Tagged urn creation
def test_0001_tagged_urn_creation():
    urn = TaggedUrn.from_string("cap:generate;ext=pdf;target=thumbnail;")
    assert urn.get_prefix() == "cap"
    assert urn.has_marker_tag("generate")
    assert urn.get_tag("target") == "thumbnail"
    assert urn.get_tag("ext") == "pdf"


# TEST0002: Custom prefix
def test_0002_custom_prefix():
    urn = TaggedUrn.from_string("myapp:generate;ext=pdf")
    assert urn.get_prefix() == "myapp"
    assert urn.has_marker_tag("generate")
    assert str(urn) == "myapp:ext=pdf;generate"


# TEST0003: Prefix case insensitive
def test_0003_prefix_case_insensitive():
    urn1 = TaggedUrn.from_string("CAP:test")
    urn2 = TaggedUrn.from_string("cap:test")
    urn3 = TaggedUrn.from_string("Cap:test")

    assert urn1.get_prefix() == "cap"
    assert urn2.get_prefix() == "cap"
    assert urn3.get_prefix() == "cap"
    assert urn1 == urn2
    assert urn2 == urn3


# TEST0004: Prefix mismatch error
def test_0004_prefix_mismatch_error():
    urn1 = TaggedUrn.from_string("cap:test")
    urn2 = TaggedUrn.from_string("myapp:test")

    with pytest.raises(TaggedUrnError) as exc_info:
        urn1.conforms_to(urn2)
    assert exc_info.value.expected == "cap"
    assert exc_info.value.actual == "myapp"


# TEST0005: Builder with prefix
def test_0005_builder_with_prefix():
    urn = TaggedUrnBuilder("custom").tag("key", "value").build()

    assert urn.get_prefix() == "custom"
    assert str(urn) == "custom:key=value"


# TEST0006: Unquoted values lowercased
def test_0006_unquoted_values_lowercased():
    # Unquoted values are normalized to lowercase
    urn = TaggedUrn.from_string("cap:ext=pdf;generate;target=thumbnail;")

    # Keys are always lowercase
    assert urn.has_marker_tag("generate")
    assert urn.get_tag("ext") == "pdf"
    assert urn.get_tag("target") == "thumbnail"

    # Key lookup is case-insensitive (uppercase variants of an existing key resolve correctly)
    assert urn.get_tag("EXT") == "pdf"
    assert urn.get_tag("Ext") == "pdf"

    # Tag order in the source string does not affect canonical form —
    # parsed URNs sort tags alphabetically before serializing.
    urn2 = TaggedUrn.from_string("cap:target=thumbnail;ext=pdf;generate;")
    assert str(urn) == str(urn2)
    assert urn == urn2


# TEST0007: Quoted values preserve case
def test_0007_quoted_values_preserve_case():
    # Quoted values preserve their case
    urn = TaggedUrn.from_string(r'cap:key="Value With Spaces"')
    assert urn.get_tag("key") == "Value With Spaces"

    # Key is still lowercase
    urn2 = TaggedUrn.from_string(r'cap:KEY="Value With Spaces"')
    assert urn2.get_tag("key") == "Value With Spaces"

    # Unquoted vs quoted case difference
    unquoted = TaggedUrn.from_string("cap:key=UPPERCASE")
    quoted = TaggedUrn.from_string(r'cap:key="UPPERCASE"')
    assert unquoted.get_tag("key") == "uppercase"  # lowercase
    assert quoted.get_tag("key") == "UPPERCASE"  # preserved
    assert unquoted != quoted  # NOT equal


# TEST0008: Quoted value special chars
def test_0008_quoted_value_special_chars():
    # Semicolons in quoted values
    urn = TaggedUrn.from_string(r'cap:key="value;with;semicolons"')
    assert urn.get_tag("key") == "value;with;semicolons"

    # Equals in quoted values
    urn2 = TaggedUrn.from_string(r'cap:key="value=with=equals"')
    assert urn2.get_tag("key") == "value=with=equals"

    # Spaces in quoted values
    urn3 = TaggedUrn.from_string(r'cap:key="hello world"')
    assert urn3.get_tag("key") == "hello world"


# TEST0009: Quoted value escape sequences
def test_0009_quoted_value_escape_sequences():
    # Escaped quotes
    urn = TaggedUrn.from_string(r'cap:key="value\"quoted\""')
    assert urn.get_tag("key") == r'value"quoted"'

    # Escaped backslashes
    urn2 = TaggedUrn.from_string(r'cap:key="path\\file"')
    assert urn2.get_tag("key") == r'path\file'

    # Mixed escapes
    urn3 = TaggedUrn.from_string(r'cap:key="say \"hello\\world\""')
    assert urn3.get_tag("key") == r'say "hello\world"'


# TEST0010: Mixed quoted unquoted
def test_0010_mixed_quoted_unquoted():
    urn = TaggedUrn.from_string(r'cap:a="Quoted";b=simple')
    assert urn.get_tag("a") == "Quoted"
    assert urn.get_tag("b") == "simple"


# TEST0011: Unterminated quote error
def test_0011_unterminated_quote_error():
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(r'cap:key="unterminated')


# TEST0012: Invalid escape sequence error
def test_0012_invalid_escape_sequence_error():
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(r'cap:key="bad\n"')

    # Invalid escape at end
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(r'cap:key="bad\x"')


# TEST0013: Serialization smart quoting
def test_0013_serialization_smart_quoting():
    # Simple lowercase value - no quoting needed
    urn = TaggedUrnBuilder("cap").tag("key", "simple").build()
    assert str(urn) == "cap:key=simple"

    # Value with spaces - needs quoting
    urn2 = TaggedUrnBuilder("cap").tag("key", "has spaces").build()
    assert str(urn2) == r'cap:key="has spaces"'

    # Value with semicolons - needs quoting
    urn3 = TaggedUrnBuilder("cap").tag("key", "has;semi").build()
    assert str(urn3) == r'cap:key="has;semi"'

    # Value with uppercase - needs quoting to preserve
    urn4 = TaggedUrnBuilder("cap").tag("key", "HasUpper").build()
    assert str(urn4) == r'cap:key="HasUpper"'

    # Value with quotes - needs quoting and escaping
    urn5 = TaggedUrnBuilder("cap").tag("key", r'has"quote').build()
    assert str(urn5) == r'cap:key="has\"quote"'

    # Value with backslashes - needs quoting and escaping
    urn6 = TaggedUrnBuilder("cap").tag("key", r'path\file').build()
    assert str(urn6) == r'cap:key="path\\file"'


# TEST0014: Round trip simple
def test_0014_round_trip_simple():
    original = "cap:generate;ext=pdf"
    urn = TaggedUrn.from_string(original)
    serialized = str(urn)
    reparsed = TaggedUrn.from_string(serialized)
    assert urn == reparsed


# TEST0015: Round trip quoted
def test_0015_round_trip_quoted():
    original = r'cap:key="Value With Spaces"'
    urn = TaggedUrn.from_string(original)
    serialized = str(urn)
    reparsed = TaggedUrn.from_string(serialized)
    assert urn == reparsed
    assert reparsed.get_tag("key") == "Value With Spaces"


# TEST0016: Round trip escapes
def test_0016_round_trip_escapes():
    original = r'cap:key="value\"with\\escapes"'
    urn = TaggedUrn.from_string(original)
    assert urn.get_tag("key") == r'value"with\escapes'
    serialized = str(urn)
    reparsed = TaggedUrn.from_string(serialized)
    assert urn == reparsed


# TEST0017: Prefix required
def test_0017_prefix_required():
    # Missing prefix should fail
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("generate;ext=pdf")

    # Valid prefix should work
    urn = TaggedUrn.from_string("cap:generate;ext=pdf")
    assert urn.has_marker_tag("generate")

    # Case-insensitive prefix
    urn2 = TaggedUrn.from_string("CAP:generate")
    assert urn2.has_marker_tag("generate")


# TEST0018: Trailing semicolon equivalence
def test_0018_trailing_semicolon_equivalence():
    # Both with and without trailing semicolon should be equivalent
    urn1 = TaggedUrn.from_string("cap:generate;ext=pdf")
    urn2 = TaggedUrn.from_string("cap:generate;ext=pdf;")

    # They should be equal
    assert urn1 == urn2

    # They should have same hash
    assert hash(urn1) == hash(urn2)

    # They should have same string representation (canonical form)
    assert str(urn1) == str(urn2)

    # They should match each other
    assert urn1.conforms_to(urn2)
    assert urn2.conforms_to(urn1)


# TEST0019: Canonical string format
def test_0019_canonical_string_format():
    urn = TaggedUrn.from_string("cap:generate;target=thumbnail;ext=pdf")
    # Should be sorted alphabetically and have no trailing semicolon in canonical form
    # Alphabetical order: ext < op < target
    assert str(urn) == "cap:ext=pdf;generate;target=thumbnail"


# TEST0020: Tag matching
def test_0020_tag_matching():
    urn = TaggedUrn.from_string("cap:generate;ext=pdf;target=thumbnail;")

    # Exact match
    request1 = TaggedUrn.from_string("cap:generate;ext=pdf;target=thumbnail;")
    assert urn.conforms_to(request1)

    # Subset match
    request2 = TaggedUrn.from_string("cap:generate")
    assert urn.conforms_to(request2)

    # Wildcard request should match specific URN
    request3 = TaggedUrn.from_string("cap:ext=*")
    assert urn.conforms_to(request3)  # URN has ext=pdf, request accepts any ext

    # No match - conflicting value
    request4 = TaggedUrn.from_string("cap:extract")
    assert not urn.conforms_to(request4)


# TEST0021: Matching case sensitive values
def test_0021_matching_case_sensitive_values():
    # Values with different case should NOT match
    urn1 = TaggedUrn.from_string(r'cap:key="Value"')
    urn2 = TaggedUrn.from_string(r'cap:key="value"')
    assert not urn1.conforms_to(urn2)
    assert not urn2.conforms_to(urn1)

    # Same case should match
    urn3 = TaggedUrn.from_string(r'cap:key="Value"')
    assert urn1.conforms_to(urn3)


# TEST0022: Missing tag handling
def test_0022_missing_tag_handling():
    # NEW SEMANTICS: Missing tag in instance means the tag doesn't exist.
    # Pattern constraints must be satisfied by instance.

    urn = TaggedUrn.from_string("cap:generate")

    # Pattern with tag that instance doesn't have: NO MATCH
    # Pattern ext=pdf requires instance to have ext=pdf, but instance doesn't have ext
    pattern1 = TaggedUrn.from_string("cap:ext=pdf")
    assert not urn.conforms_to(pattern1)  # Instance missing ext, pattern wants ext=pdf

    # Pattern missing tag = no constraint: MATCH
    # Instance has generate, pattern has no constraint on op
    urn2 = TaggedUrn.from_string("cap:generate;ext=pdf")
    pattern2 = TaggedUrn.from_string("cap:generate")
    assert urn2.conforms_to(pattern2)  # Instance has ext=pdf, pattern doesn't constrain ext

    # To match any value of a tag, use explicit ? or *
    pattern3 = TaggedUrn.from_string("cap:ext=?")  # ? = no constraint
    assert urn.conforms_to(pattern3)  # Instance missing ext, pattern doesn't care

    # * means must-have-any - instance must have the tag
    pattern4 = TaggedUrn.from_string("cap:ext=*")
    assert not urn.conforms_to(pattern4)  # Instance missing ext, pattern requires ext to be present


# TEST0023: Specificity
def test_0023_specificity():
    # Six-form per-tag specificity ladder:
    #   ?x        : 0  (no constraint)
    #   x?=v      : 1  (absent OR not v)
    #   x (=x=*)  : 2  (must-have-any)
    #   x!=v      : 3  (present and not v)
    #   x=v       : 4  (must-have-this-value)
    #   !x        : 5  (must-not-have)

    urn1 = TaggedUrn.from_string("cap:general")        # bare marker -> 2
    urn2 = TaggedUrn.from_string("cap:ext=pdf")        # exact -> 4
    urn3 = TaggedUrn.from_string("cap:gen;ext=pdf")    # marker(2) + exact(4)
    urn4 = TaggedUrn.from_string("cap:?ext")           # ?x -> 0
    urn5 = TaggedUrn.from_string("cap:!ext")           # !x -> 5
    urn6 = TaggedUrn.from_string("cap:ext?=pdf")       # x?=v -> 1
    urn7 = TaggedUrn.from_string("cap:ext!=pdf")       # x!=v -> 3

    assert urn1.specificity() == 2
    assert urn2.specificity() == 4
    assert urn3.specificity() == 6
    assert urn4.specificity() == 0
    assert urn5.specificity() == 5
    assert urn6.specificity() == 1
    assert urn7.specificity() == 3

    # Five-tuple counts: (must_not_have, exact, present_not_value,
    # must_have_any, absent_or_not_value).
    assert urn2.specificity_tuple() == (0, 1, 0, 0, 0)
    assert urn3.specificity_tuple() == (0, 1, 0, 1, 0)
    assert urn5.specificity_tuple() == (1, 0, 0, 0, 0)

    assert urn2.is_more_specific_than(urn1)  # exact(4) > marker(2)


# TEST0024: Builder
def test_0024_builder():
    urn = (TaggedUrnBuilder("cap")
           .marker("generate")
           .tag("target", "thumbnail")
           .tag("ext", "pdf")
           .tag("output", "binary")
           .build())

    assert urn.has_marker_tag("generate")
    assert urn.get_tag("output") == "binary"


# TEST0025: Builder preserves case
def test_0025_builder_preserves_case():
    urn = TaggedUrnBuilder("cap").tag("KEY", "ValueWithCase").build()

    # Key is lowercase
    assert urn.get_tag("key") == "ValueWithCase"
    # Value case preserved, so needs quoting
    assert str(urn) == r'cap:key="ValueWithCase"'


# TEST0026: Compatibility
def test_0026_compatibility():
    # TEST526: Test directional accepts between general and specific URNs
    general = TaggedUrn.from_string("cap:generate")
    specific = TaggedUrn.from_string("cap:generate;ext=pdf")

    # General pattern accepts specific instance (no constraint on ext)
    assert general.accepts(specific)
    # Specific does NOT accept general (missing ext in instance fails specific pattern's ext=pdf)
    assert not specific.accepts(general)

    # Unrelated URNs: different op values, neither accepts the other
    urn_extract = TaggedUrn.from_string("cap:image;extract")
    assert not general.accepts(urn_extract)
    assert not urn_extract.accepts(general)

    # Wildcard format tag: general (no format constraint) accepts urn_format
    urn_format = TaggedUrn.from_string("cap:generate;format=*")
    assert general.accepts(urn_format)
    # urn_format does NOT accept general: pattern format=* requires instance to have format tag
    assert not urn_format.accepts(general)


# TEST0027: Best match
def test_0027_best_match():
    urns = [
        TaggedUrn.from_string("cap:op"),
        TaggedUrn.from_string("cap:generate"),
        TaggedUrn.from_string("cap:generate;ext=pdf"),
    ]

    request = TaggedUrn.from_string("cap:generate")
    best = UrnMatcher.find_best_match(urns, request)

    # Most specific URN that can handle the request
    # Alphabetical order: ext < op
    assert str(best) == "cap:ext=pdf;generate"


# TEST0028: Merge and subset
def test_0028_merge_and_subset():
    urn1 = TaggedUrn.from_string("cap:generate")
    urn2 = TaggedUrn.from_string("cap:ext=pdf;output=binary")

    merged = urn1.merge(urn2)
    # Alphabetical order: ext < op < output
    assert str(merged) == "cap:ext=pdf;generate;output=binary"

    subset = merged.subset(["type", "ext"])
    assert str(subset) == "cap:ext=pdf"


# TEST0029: Merge prefix mismatch
def test_0029_merge_prefix_mismatch():
    urn1 = TaggedUrn.from_string("cap:generate")
    urn2 = TaggedUrn.from_string("myapp:ext=pdf")

    with pytest.raises(TaggedUrnError):
        urn1.merge(urn2)


# TEST0030: Wildcard tag
def test_0030_wildcard_tag():
    urn = TaggedUrn.from_string("cap:ext=pdf")
    wildcarded = urn.with_wildcard_tag("ext")

    # Wildcard serializes as value-less tag
    assert str(wildcarded) == "cap:ext"

    # Test that wildcarded URN can match more requests
    request = TaggedUrn.from_string("cap:ext=jpg")
    assert not urn.conforms_to(request)
    assert wildcarded.conforms_to(TaggedUrn.from_string("cap:ext"))


# TEST0031: Empty tagged urn
def test_0031_empty_tagged_urn():
    # Empty tagged URN is valid
    empty_urn = TaggedUrn.from_string("cap:")
    assert len(empty_urn.tags) == 0
    assert str(empty_urn) == "cap:"

    # NEW SEMANTICS:
    # Empty PATTERN matches any INSTANCE (pattern has no constraints)
    # Empty INSTANCE only matches patterns that have no required tags

    specific_urn = TaggedUrn.from_string("cap:generate;ext=pdf")

    # Empty instance vs specific pattern: NO MATCH
    # Pattern requires generate and ext=pdf, instance doesn't have them
    assert not empty_urn.conforms_to(specific_urn)

    # Specific instance vs empty pattern: MATCH
    # Pattern has no constraints, instance can have anything
    assert specific_urn.conforms_to(empty_urn)

    # Empty instance vs empty pattern: MATCH
    assert empty_urn.conforms_to(empty_urn)

    # With trailing semicolon
    empty_urn2 = TaggedUrn.from_string("cap:;")
    assert len(empty_urn2.tags) == 0


# TEST0032: Empty with custom prefix
def test_0032_empty_with_custom_prefix():
    empty_urn = TaggedUrn.from_string("myapp:")
    assert empty_urn.get_prefix() == "myapp"
    assert len(empty_urn.tags) == 0
    assert str(empty_urn) == "myapp:"


# TEST0033: Extended character support
def test_0033_extended_character_support():
    # Test forward slashes and colons in tag components
    urn = TaggedUrn.from_string("cap:url=https://example_org/api;path=/some/file")
    assert urn.get_tag("url") == "https://example_org/api"
    assert urn.get_tag("path") == "/some/file"


# TEST0034: Wildcard restrictions
def test_0034_wildcard_restrictions():
    # Wildcard should be rejected in keys
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:*=value")

    # Wildcard should be accepted in values
    urn = TaggedUrn.from_string("cap:key=*")
    assert urn.get_tag("key") == "*"


# TEST0035: Duplicate key rejection
def test_0035_duplicate_key_rejection():
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=value1;key=value2")


# TEST0036: Numeric key restriction
def test_0036_numeric_key_restriction():
    # Pure numeric keys should be rejected
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:123=value")

    # Mixed alphanumeric keys should be allowed
    assert TaggedUrn.from_string("cap:key123=value")
    assert TaggedUrn.from_string("cap:123key=value")

    # Pure numeric values should be allowed
    assert TaggedUrn.from_string("cap:key=123")


# TEST0037: Empty value error
def test_0037_empty_value_error():
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=")
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=;other=value")


# TEST0038: Has tag case sensitive
def test_0038_has_tag_case_sensitive():
    urn = TaggedUrn.from_string(r'cap:key="Value"')

    # Exact case match works
    assert urn.has_tag("key", "Value")

    # Different case does not match
    assert not urn.has_tag("key", "value")
    assert not urn.has_tag("key", "VALUE")

    # Key lookup is case-insensitive
    assert urn.has_tag("KEY", "Value")
    assert urn.has_tag("Key", "Value")


# TEST0039: With tag preserves value
def test_0039_with_tag_preserves_value():
    urn = TaggedUrn.empty("cap").with_tag("key", "ValueWithCase")
    assert urn.get_tag("key") == "ValueWithCase"


# TEST0040: With tag rejects empty value
def test_0040_with_tag_rejects_empty_value():
    with pytest.raises(TaggedUrnError) as exc_info:
        TaggedUrn.empty("cap").with_tag("key", "")
    assert "empty value" in str(exc_info.value).lower()


# TEST0041: Builder rejects empty value
def test_0041_builder_rejects_empty_value():
    with pytest.raises(TaggedUrnError) as exc_info:
        TaggedUrnBuilder("cap").tag("key", "")
    assert "empty value" in str(exc_info.value).lower()


# TEST0042: Semantic equivalence
def test_0042_semantic_equivalence():
    # Unquoted and quoted simple lowercase values are equivalent
    unquoted = TaggedUrn.from_string("cap:key=simple")
    quoted = TaggedUrn.from_string(r'cap:key="simple"')
    assert unquoted == quoted

    # Both serialize the same way (unquoted)
    assert str(unquoted) == "cap:key=simple"
    assert str(quoted) == "cap:key=simple"


# ============================================================================
# MATCHING SEMANTICS SPECIFICATION TESTS
# These 9 tests verify the exact matching semantics from RULES.md Sections 12-17
# All implementations (Rust, Go, JS, ObjC) must pass these identically
# ============================================================================

def test_0043_matching_semantics_test1_exact_match():
    # Test 1: Exact match
    # URN:     cap:generate;ext=pdf
    # Request: cap:generate;ext=pdf
    # Result:  MATCH
    urn = TaggedUrn.from_string("cap:generate;ext=pdf")
    request = TaggedUrn.from_string("cap:generate;ext=pdf")
    assert urn.conforms_to(request), "Test 1: Exact match should succeed"


# TEST0044: Matching semantics test2 instance missing tag
def test_0044_matching_semantics_test2_instance_missing_tag():
    # Test 2: Instance missing tag
    # Instance: cap:generate;in=media:;out=media:
    # Pattern:  cap:generate;ext=pdf
    # Result:   NO MATCH (pattern requires ext=pdf, instance doesn't have ext)
    #
    # NEW SEMANTICS: Missing tag in instance means it doesn't exist.
    # Pattern K=v requires instance to have K=v.
    instance = TaggedUrn.from_string("cap:generate")
    pattern = TaggedUrn.from_string("cap:generate;ext=pdf")
    assert not instance.conforms_to(pattern), "Test 2: Instance missing tag should NOT match when pattern requires it"

    # To accept any ext (or missing), use pattern with ext=?
    pattern_optional = TaggedUrn.from_string("cap:generate;ext=?")
    assert instance.conforms_to(pattern_optional), "Pattern with ext=? should match instance without ext"


# TEST0045: Matching semantics test3 urn has extra tag
def test_0045_matching_semantics_test3_urn_has_extra_tag():
    # Test 3: URN has extra tag
    # URN:     cap:generate;ext=pdf;version=2
    # Request: cap:generate;ext=pdf
    # Result:  MATCH (request doesn't constrain version)
    urn = TaggedUrn.from_string("cap:generate;ext=pdf;version=2")
    request = TaggedUrn.from_string("cap:generate;ext=pdf")
    assert urn.conforms_to(request), "Test 3: URN with extra tag should match"


# TEST0046: Matching semantics test4 request has wildcard
def test_0046_matching_semantics_test4_request_has_wildcard():
    # Test 4: Request has wildcard
    # URN:     cap:generate;ext=pdf
    # Request: cap:generate;ext=*
    # Result:  MATCH (request accepts any ext)
    urn = TaggedUrn.from_string("cap:generate;ext=pdf")
    request = TaggedUrn.from_string("cap:generate;ext=*")
    assert urn.conforms_to(request), "Test 4: Request wildcard should match"


# TEST0047: Matching semantics test5 urn has wildcard
def test_0047_matching_semantics_test5_urn_has_wildcard():
    # An instance's wildcard promises presence, not the value asked for:
    # "some ext" does not satisfy ext=pdf, and a pdf satisfies "some ext".
    urn = TaggedUrn.from_string("cap:generate;ext=*")
    request = TaggedUrn.from_string("cap:generate;ext=pdf")
    assert not urn.conforms_to(request), "some ext does not satisfy ext=pdf"
    assert request.conforms_to(urn), "ext=pdf satisfies some ext"


# TEST0048: Matching semantics test6 value mismatch
def test_0048_matching_semantics_test6_value_mismatch():
    # Test 6: Value mismatch
    # URN:     cap:generate;ext=pdf
    # Request: cap:generate;ext=docx
    # Result:  NO MATCH
    urn = TaggedUrn.from_string("cap:generate;ext=pdf")
    request = TaggedUrn.from_string("cap:generate;ext=docx")
    assert not urn.conforms_to(request), "Test 6: Value mismatch should not match"


# TEST0049: Matching semantics test7 pattern has extra tag
def test_0049_matching_semantics_test7_pattern_has_extra_tag():
    # Test 7: Pattern has extra tag that instance doesn't have
    # Instance: cap:generate-thumbnail;out="media:binary"
    # Pattern:  cap:generate-thumbnail;out="media:binary";ext=wav
    # Result:   NO MATCH (pattern requires ext=wav, instance doesn't have ext)
    #
    # NEW SEMANTICS: Pattern K=v requires instance to have K=v
    instance = TaggedUrn.from_string(r'cap:generate-thumbnail;out="media:binary"')
    pattern = TaggedUrn.from_string(r'cap:generate-thumbnail;out="media:binary";ext=wav')
    assert not instance.conforms_to(pattern), "Test 7: Instance missing ext should NOT match when pattern requires ext=wav"

    # Instance vs pattern that doesn't constrain ext: MATCH
    pattern_no_ext = TaggedUrn.from_string(r'cap:generate-thumbnail;out="media:binary"')
    assert instance.conforms_to(pattern_no_ext)


# TEST0050: Matching semantics test8 empty pattern matches anything
def test_0050_matching_semantics_test8_empty_pattern_matches_anything():
    # Test 8: Empty PATTERN matches any INSTANCE
    # Instance: cap:generate;ext=pdf
    # Pattern:  cap:
    # Result:   MATCH (pattern has no constraints)
    #
    # NEW SEMANTICS: Empty pattern = no constraints = matches any instance
    # But empty instance only matches patterns that don't require tags
    instance = TaggedUrn.from_string("cap:generate;ext=pdf")
    empty_pattern = TaggedUrn.from_string("cap:")
    assert instance.conforms_to(empty_pattern), "Test 8: Any instance should match empty pattern"

    # Empty instance vs pattern with requirements: NO MATCH
    empty_instance = TaggedUrn.from_string("cap:")
    pattern = TaggedUrn.from_string("cap:generate;ext=pdf")
    assert not empty_instance.conforms_to(pattern), "Empty instance should NOT match pattern with requirements"


# TEST0051: Matching semantics test9 cross dimension constraints
def test_0051_matching_semantics_test9_cross_dimension_constraints():
    # Test 9: Cross-dimension constraints
    # Instance: cap:generate;in=media:;out=media:
    # Pattern:  cap:ext=pdf
    # Result:   NO MATCH (pattern requires ext=pdf, instance doesn't have ext)
    #
    # NEW SEMANTICS: Pattern K=v requires instance to have K=v
    instance = TaggedUrn.from_string("cap:generate")
    pattern = TaggedUrn.from_string("cap:ext=pdf")
    assert not instance.conforms_to(pattern), "Test 9: Instance without ext should NOT match pattern requiring ext"

    # Instance with ext vs pattern with different tag only: MATCH
    instance2 = TaggedUrn.from_string("cap:generate;ext=pdf")
    pattern2 = TaggedUrn.from_string("cap:ext=pdf")
    assert instance2.conforms_to(pattern2), "Instance with ext=pdf should match pattern requiring ext=pdf"


# TEST0052: Matching different prefixes error
def test_0052_matching_different_prefixes_error():
    # URNs with different prefixes should cause an error, not just return false
    urn1 = TaggedUrn.from_string("cap:test")
    urn2 = TaggedUrn.from_string("other:test")

    with pytest.raises(TaggedUrnError):
        urn1.conforms_to(urn2)

    with pytest.raises(TaggedUrnError):
        urn1.accepts(urn2)

    with pytest.raises(TaggedUrnError):
        urn1.is_more_specific_than(urn2)


# ============================================================================
# VALUE-LESS TAG TESTS
# Value-less tags are equivalent to wildcard tags (key=*)
# ============================================================================

def test_0053_valueless_tag_parsing_single():
    # Single value-less tag
    urn = TaggedUrn.from_string("cap:optimize")
    assert urn.get_tag("optimize") == "*"
    # Serializes as value-less (no =*)
    assert str(urn) == "cap:optimize"


# TEST0054: Valueless tag parsing multiple
def test_0054_valueless_tag_parsing_multiple():
    # Multiple value-less tags
    urn = TaggedUrn.from_string("cap:fast;optimize;secure")
    assert urn.get_tag("fast") == "*"
    assert urn.get_tag("optimize") == "*"
    assert urn.get_tag("secure") == "*"
    # Serializes alphabetically as value-less
    assert str(urn) == "cap:fast;optimize;secure"


# TEST0055: Valueless tag mixed with valued
def test_0055_valueless_tag_mixed_with_valued():
    # Mix of value-less and valued tags
    urn = TaggedUrn.from_string("cap:generate;optimize;ext=pdf;secure")
    assert urn.has_marker_tag("generate")
    assert urn.get_tag("optimize") == "*"
    assert urn.get_tag("ext") == "pdf"
    assert urn.get_tag("secure") == "*"
    # Serializes alphabetically
    assert str(urn) == "cap:ext=pdf;generate;optimize;secure"


# TEST0056: Valueless tag at end
def test_0056_valueless_tag_at_end():
    # Value-less tag at the end (no trailing semicolon)
    urn = TaggedUrn.from_string("cap:generate;optimize")
    assert urn.has_marker_tag("generate")
    assert urn.get_tag("optimize") == "*"
    assert str(urn) == "cap:generate;optimize"


# TEST0057: Valueless tag equivalence to wildcard
def test_0057_valueless_tag_equivalence_to_wildcard():
    # Value-less tag is equivalent to explicit wildcard
    valueless = TaggedUrn.from_string("cap:ext")
    wildcard = TaggedUrn.from_string("cap:ext=*")
    assert valueless == wildcard
    # Both serialize to value-less form
    assert str(valueless) == "cap:ext"
    assert str(wildcard) == "cap:ext"


# TEST0058: Valueless tag matching
def test_0058_valueless_tag_matching():
    # A valueless tag promises presence, not a value. Reading `ext` as
    # "whatever the pattern wants" made `ext` and `ext=pdf` equivalent and
    # refinement non-transitive; refinement is inclusion of what each form
    # allows (tagged-urn formal, `tagMatch_iff_allows`).
    urn = TaggedUrn.from_string("cap:generate;ext")

    request_pdf = TaggedUrn.from_string("cap:generate;ext=pdf")
    request_docx = TaggedUrn.from_string("cap:generate;ext=docx")

    assert not urn.conforms_to(request_pdf), "some ext is not a promise of pdf"
    assert not urn.conforms_to(request_docx), "some ext is not a promise of docx"
    assert request_pdf.conforms_to(urn), "a pdf is some ext"
    assert not urn.is_equivalent(request_pdf), "ext and ext=pdf are different tag sets"


# TEST0059: Valueless tag in pattern
def test_0059_valueless_tag_in_pattern():
    # Pattern with value-less tag (K=*) requires instance to have the tag
    pattern = TaggedUrn.from_string("cap:generate;ext")

    instance_pdf = TaggedUrn.from_string("cap:generate;ext=pdf")
    instance_docx = TaggedUrn.from_string("cap:generate;ext=docx")
    instance_missing = TaggedUrn.from_string("cap:generate")

    # NEW SEMANTICS: K=* (valueless tag) means must-have-any
    assert instance_pdf.conforms_to(pattern)  # Has ext=pdf
    assert instance_docx.conforms_to(pattern)  # Has ext=docx
    assert not instance_missing.conforms_to(pattern)  # Missing ext, pattern requires it

    # To accept missing ext, use ? instead
    pattern_optional = TaggedUrn.from_string("cap:generate;ext=?")
    assert instance_missing.conforms_to(pattern_optional)


# TEST0060: Valueless tag specificity
def test_0060_valueless_tag_specificity():
    # Six-form ladder: ?x=0, x?=v=1, x=*=2, x!=v=3, x=v=4, !x=5.
    urn1 = TaggedUrn.from_string("cap:generate")          # 1 marker
    urn2 = TaggedUrn.from_string("cap:generate;optimize") # 2 markers
    urn3 = TaggedUrn.from_string("cap:generate;ext=pdf")  # 1 marker + 1 exact

    assert urn1.specificity() == 2  # 1 marker = 2
    assert urn2.specificity() == 4  # 2 markers = 2 + 2 = 4
    assert urn3.specificity() == 6  # 1 marker + 1 exact = 2 + 4 = 6


# TEST0061: Valueless tag roundtrip
def test_0061_valueless_tag_roundtrip():
    # Round-trip parsing and serialization
    original = "cap:ext=pdf;generate;optimize;secure"
    urn = TaggedUrn.from_string(original)
    serialized = str(urn)
    reparsed = TaggedUrn.from_string(serialized)
    assert urn == reparsed
    assert serialized == original


# TEST0062: Valueless tag case normalization
def test_0062_valueless_tag_case_normalization():
    # Value-less tags are normalized to lowercase like other keys
    urn = TaggedUrn.from_string("cap:OPTIMIZE;Fast;SECURE")
    assert urn.get_tag("optimize") == "*"
    assert urn.get_tag("fast") == "*"
    assert urn.get_tag("secure") == "*"
    assert str(urn) == "cap:fast;optimize;secure"


# TEST0063: Empty value still error
def test_0063_empty_value_still_error():
    # Empty value with = is still an error (different from value-less)
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=")
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=;other=value")


# TEST0064: Valueless tag compatibility
def test_0064_valueless_tag_compatibility():
    # TEST564: Value-less tags (wildcard) accept any specific value
    urn_wildcard = TaggedUrn.from_string("cap:generate;ext")  # ext=*
    urn_pdf = TaggedUrn.from_string("cap:generate;ext=pdf")
    urn_docx = TaggedUrn.from_string("cap:generate;ext=docx")

    # Wildcard pattern accepts specific instances
    assert urn_wildcard.accepts(urn_pdf)
    assert urn_wildcard.accepts(urn_docx)
    # A specific pattern does NOT accept the wildcard: "some ext" is not a pdf.
    assert not urn_pdf.accepts(urn_wildcard)
    assert not urn_docx.accepts(urn_wildcard)
    # Different specific values: neither accepts the other
    assert not urn_pdf.accepts(urn_docx)
    assert not urn_docx.accepts(urn_pdf)


# TEST0065: Valueless numeric key still rejected
def test_0065_valueless_numeric_key_still_rejected():
    # Purely numeric keys are still rejected for value-less tags
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:123")
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:generate;456")


# TEST0066: Whitespace in input rejected
def test_0066_whitespace_in_input_rejected():
    # Leading whitespace fails hard
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(" cap:test")

    # Trailing whitespace fails hard
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:in=media:;out=media:;test ")

    # Both leading and trailing whitespace fails hard
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(" cap:in=media:;out=media:;test ")

    # Tab and newline also count as whitespace
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("\tcap:test")
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:in=media:;out=media:;test\n")

    # Clean input works
    assert TaggedUrn.from_string("cap:test")


# ============================================================================
# NEW SEMANTICS TESTS: ? (unspecified) and ! (must-not-have)
# ============================================================================

def test_0067_unspecified_question_mark_parsing():
    # All three input aliases (?x, x?, x=?) parse to stored value "?"
    # and serialize as the canonical prefix form `?x`.
    urn = TaggedUrn.from_string("cap:ext=?")
    assert urn.get_tag("ext") == "?"
    assert str(urn) == "cap:?ext"


# TEST0068: Must not have exclamation parsing
def test_0068_must_not_have_exclamation_parsing():
    # All three input aliases (!x, x!, x=!) parse to stored value "!"
    # and serialize as the canonical prefix form `!x`.
    urn = TaggedUrn.from_string("cap:ext=!")
    assert urn.get_tag("ext") == "!"
    assert str(urn) == "cap:!ext"


# TEST0069: Question mark pattern matches anything
def test_0069_question_mark_pattern_matches_anything():
    # Pattern with K=? matches any instance (with or without K)
    pattern = TaggedUrn.from_string("cap:ext=?")

    instance_pdf = TaggedUrn.from_string("cap:ext=pdf")
    instance_docx = TaggedUrn.from_string("cap:ext=docx")
    instance_missing = TaggedUrn.from_string("cap:")
    instance_wildcard = TaggedUrn.from_string("cap:ext=*")
    instance_must_not = TaggedUrn.from_string("cap:ext=!")

    assert instance_pdf.conforms_to(pattern), "ext=pdf should match ext=?"
    assert instance_docx.conforms_to(pattern), "ext=docx should match ext=?"
    assert instance_missing.conforms_to(pattern), "(no ext) should match ext=?"
    assert instance_wildcard.conforms_to(pattern), "ext=* should match ext=?"
    assert instance_must_not.conforms_to(pattern), "ext=! should match ext=?"


# TEST0070: Question mark in instance
def test_0070_question_mark_in_instance():
    # An instance with K=? promises nothing about K, so it satisfies exactly
    # the patterns that ask for nothing. Satisfying every pattern made
    # refinement non-transitive: missing ⪯ ?k ⪯ k=v, yet missing ⋠ k=v.
    instance = TaggedUrn.from_string("cap:ext=?")

    pattern_pdf = TaggedUrn.from_string("cap:ext=pdf")
    pattern_wildcard = TaggedUrn.from_string("cap:ext=*")
    pattern_must_not = TaggedUrn.from_string("cap:ext=!")
    pattern_question = TaggedUrn.from_string("cap:ext=?")
    pattern_missing = TaggedUrn.from_string("cap:")

    assert not instance.conforms_to(pattern_pdf), "ext=? promises no pdf"
    assert not instance.conforms_to(pattern_wildcard), "ext=? promises no presence"
    assert not instance.conforms_to(pattern_must_not), "ext=? promises no absence"
    assert instance.conforms_to(pattern_question), "ext=? should match ext=?"
    assert instance.conforms_to(pattern_missing), "ext=? should match (no ext)"


# TEST0071: Must not have pattern requires absent
def test_0071_must_not_have_pattern_requires_absent():
    # Pattern with K=! requires the instance to SAY K is absent: a key an
    # instance does not mention is not a promise that it is absent.
    pattern = TaggedUrn.from_string("cap:ext=!")

    instance_missing = TaggedUrn.from_string("cap:")
    instance_pdf = TaggedUrn.from_string("cap:ext=pdf")
    instance_wildcard = TaggedUrn.from_string("cap:ext=*")
    instance_must_not = TaggedUrn.from_string("cap:ext=!")

    assert not instance_missing.conforms_to(pattern), "(no ext) does not promise ext is absent"
    assert not instance_pdf.conforms_to(pattern), "ext=pdf should NOT match ext=!"
    assert not instance_wildcard.conforms_to(pattern), "ext=* should NOT match ext=!"
    assert instance_must_not.conforms_to(pattern), "ext=! should match ext=!"


# TEST0072: Must not have in instance
def test_0072_must_not_have_in_instance():
    # Instance with K=! conflicts with patterns requiring K
    instance = TaggedUrn.from_string("cap:ext=!")

    pattern_pdf = TaggedUrn.from_string("cap:ext=pdf")
    pattern_wildcard = TaggedUrn.from_string("cap:ext=*")
    pattern_must_not = TaggedUrn.from_string("cap:ext=!")
    pattern_question = TaggedUrn.from_string("cap:ext=?")
    pattern_missing = TaggedUrn.from_string("cap:")

    assert not instance.conforms_to(pattern_pdf), "ext=! should NOT match ext=pdf"
    assert not instance.conforms_to(pattern_wildcard), "ext=! should NOT match ext=*"
    assert instance.conforms_to(pattern_must_not), "ext=! should match ext=!"
    assert instance.conforms_to(pattern_question), "ext=! should match ext=?"
    assert instance.conforms_to(pattern_missing), "ext=! should match (no ext)"


# TEST0073: Full cross product matching
def test_0073_full_cross_product_matching():
    # Comprehensive test of all instance/pattern combinations
    # Based on the truth table in the plan

    # Helper to test a single case
    def check(instance, pattern, expected, msg):
        inst = TaggedUrn.from_string(instance)
        patt = TaggedUrn.from_string(pattern)
        assert inst.conforms_to(patt) == expected, f"{msg}: instance={instance}, pattern={pattern}"

    # Instance missing, Pattern variations
    check("cap:", "cap:", True, "(none)/(none)")
    check("cap:", "cap:k=?", True, "(none)/K=?")
    check("cap:", "cap:k=!", False, "(none)/K=!")
    check("cap:", "cap:k", False, "(none)/K=*")  # K is valueless = *
    check("cap:", "cap:k=v", False, "(none)/K=v")

    # Instance K=?, Pattern variations
    check("cap:k=?", "cap:", True, "K=?/(none)")
    check("cap:k=?", "cap:k=?", True, "K=?/K=?")
    check("cap:k=?", "cap:k=!", False, "K=?/K=!")
    check("cap:k=?", "cap:k", False, "K=?/K=*")
    check("cap:k=?", "cap:k=v", False, "K=?/K=v")

    # Instance K=!, Pattern variations
    check("cap:k=!", "cap:", True, "K=!/(none)")
    check("cap:k=!", "cap:k=?", True, "K=!/K=?")
    check("cap:k=!", "cap:k=!", True, "K=!/K=!")
    check("cap:k=!", "cap:k", False, "K=!/K=*")
    check("cap:k=!", "cap:k=v", False, "K=!/K=v")

    # Instance K=*, Pattern variations
    check("cap:k", "cap:", True, "K=*/(none)")
    check("cap:k", "cap:k=?", True, "K=*/K=?")
    check("cap:k", "cap:k=!", False, "K=*/K=!")
    check("cap:k", "cap:k", True, "K=*/K=*")
    check("cap:k", "cap:k=v", False, "K=*/K=v")

    # Instance K=v, Pattern variations
    check("cap:k=v", "cap:", True, "K=v/(none)")
    check("cap:k=v", "cap:k=?", True, "K=v/K=?")
    check("cap:k=v", "cap:k=!", False, "K=v/K=!")
    check("cap:k=v", "cap:k", True, "K=v/K=*")
    check("cap:k=v", "cap:k=v", True, "K=v/K=v")
    check("cap:k=v", "cap:k=w", False, "K=v/K=w")


# TEST0074: Mixed special values
def test_0074_mixed_special_values():
    # Test URNs with multiple special values
    pattern = TaggedUrn.from_string("cap:required;optional=?;forbidden=!;exact=pdf")

    # Instance that satisfies all constraints — including stating that the
    # forbidden key is absent, which leaving it out does not promise.
    good_instance = TaggedUrn.from_string("cap:required=yes;optional=maybe;forbidden=!;exact=pdf")
    assert good_instance.conforms_to(pattern)
    silent_on_forbidden = TaggedUrn.from_string("cap:required=yes;optional=maybe;exact=pdf")
    assert not silent_on_forbidden.conforms_to(pattern)

    # Instance missing required tag
    missing_required = TaggedUrn.from_string("cap:optional=maybe;exact=pdf")
    assert not missing_required.conforms_to(pattern)

    # Instance has forbidden tag
    has_forbidden = TaggedUrn.from_string("cap:required=yes;forbidden=oops;exact=pdf")
    assert not has_forbidden.conforms_to(pattern)

    # Instance with wrong exact value
    wrong_exact = TaggedUrn.from_string("cap:required=yes;exact=doc")
    assert not wrong_exact.conforms_to(pattern)


# TEST0075: Serialization round trip special values
def test_0075_serialization_round_trip_special_values():
    # All special values round-trip correctly
    originals = [
        "cap:ext=?",
        "cap:ext=!",
        "cap:ext",  # * serializes as valueless
        "cap:a=?;b=!;c;d=exact",
    ]

    for original in originals:
        urn = TaggedUrn.from_string(original)
        serialized = str(urn)
        reparsed = TaggedUrn.from_string(serialized)
        assert urn == reparsed, f"Round-trip failed for: {original}"


# TEST0076: Compatibility with special values
def test_0076_compatibility_with_special_values():
    # TEST576: Test bidirectional accepts with special values
    must_not = TaggedUrn.from_string("cap:ext=!")
    must_have = TaggedUrn.from_string("cap:ext=*")
    specific = TaggedUrn.from_string("cap:ext=pdf")
    unspecified = TaggedUrn.from_string("cap:ext=?")
    missing = TaggedUrn.from_string("cap:")

    # ! vs *: neither accepts the other (! conflicts with *)
    assert not must_not.accepts(must_have)
    assert not must_have.accepts(must_not)

    # ! vs specific: neither accepts the other
    assert not must_not.accepts(specific)
    assert not specific.accepts(must_not)

    # ! vs ?: ? accepts everything; ! does not accept ?, which promises nothing
    # about absence.
    assert unspecified.accepts(must_not)
    assert not must_not.accepts(unspecified)

    # ! vs missing: missing has no ext constraint, ! has ext=!
    # missing.accepts(must_not): pattern=missing has no ext constraint -> True
    assert missing.accepts(must_not)
    # must_not.accepts(missing): an instance that does not mention ext has not
    # said it is absent -> False
    assert not must_not.accepts(missing)

    # ! vs !: both accept each other
    assert must_not.accepts(must_not)

    # * vs specific: * accepts specific (pattern * matches any value)
    assert must_have.accepts(specific)
    # specific does not accept *: "some ext" is not a promise of pdf
    assert not specific.accepts(must_have)

    # * vs *: both accept each other
    assert must_have.accepts(must_have)

    # ? accepts everything
    assert unspecified.accepts(must_not)
    assert unspecified.accepts(must_have)
    assert unspecified.accepts(specific)
    assert unspecified.accepts(unspecified)
    assert unspecified.accepts(missing)


# TEST0077: Specificity with special values
def test_0077_specificity_with_special_values():
    # Six-form ladder: ?x=0, x?=v=1, x=*=2, x!=v=3, x=v=4, !x=5.
    exact = TaggedUrn.from_string("cap:a=x;b=y;c=z")          # 3 * 4 = 12
    must_have = TaggedUrn.from_string("cap:a;b;c")            # 3 * 2 = 6
    must_not = TaggedUrn.from_string("cap:!a;!b;!c")          # 3 * 5 = 15
    unspecified = TaggedUrn.from_string("cap:?a;?b;?c")       # 3 * 0 = 0
    # mixed: a=x (4) + b (2) + !c (5) + ?d (0) = 11
    mixed = TaggedUrn.from_string("cap:!c;?d;a=x;b")

    assert exact.specificity() == 12
    assert must_have.specificity() == 6
    assert must_not.specificity() == 15
    assert unspecified.specificity() == 0
    assert mixed.specificity() == 11

    # Five-tuple counts: (must_not_have, exact, present_not_value,
    # must_have_any, absent_or_not_value).
    assert exact.specificity_tuple() == (0, 3, 0, 0, 0)
    assert must_have.specificity_tuple() == (0, 0, 0, 3, 0)
    assert must_not.specificity_tuple() == (3, 0, 0, 0, 0)
    assert unspecified.specificity_tuple() == (0, 0, 0, 0, 0)
    assert mixed.specificity_tuple() == (1, 1, 0, 1, 0)


# =========================================================================
# ORDER-THEORETIC RELATIONS: is_equivalent, is_comparable
# =========================================================================

# TEST578: Equivalent URNs with identical tag sets
def test_578_equivalent_identical_tags():
    a = TaggedUrn.from_string("cap:generate;ext=pdf")
    b = TaggedUrn.from_string("cap:ext=pdf;generate")  # same tags, different order
    assert a.is_equivalent(b)
    assert b.is_equivalent(a)  # symmetric


# TEST579: Non-equivalent URNs where one is more specific
def test_579_not_equivalent_when_one_more_specific():
    general = TaggedUrn.from_string("media:")
    specific = TaggedUrn.from_string("media:pdf")
    assert not general.is_equivalent(specific)
    assert not specific.is_equivalent(general)


# TEST580: Comparable URNs on the same specialization chain
def test_580_comparable_specialization_chain():
    general = TaggedUrn.from_string("media:")
    specific = TaggedUrn.from_string("media:pdf")
    # general.accepts(specific) = True (wildcard ⊆ pdf)
    # specific.accepts(general) = False (pdf missing from general)
    # OR → True
    assert general.is_comparable(specific)
    assert specific.is_comparable(general)  # symmetric


# TEST581: Incomparable URNs in different branches of the lattice
def test_581_incomparable_different_branches():
    pdf = TaggedUrn.from_string("media:pdf")
    txt = TaggedUrn.from_string("media:enc=utf-8;txt")
    # pdf.accepts(txt) = False (pdf missing from txt)
    # txt.accepts(pdf) = False (txt missing from pdf)
    # OR → False
    assert not pdf.is_comparable(txt)
    assert not txt.is_comparable(pdf)


# TEST582: Equivalent implies comparable but not vice versa
def test_582_equivalent_implies_comparable():
    a = TaggedUrn.from_string("cap:test;ext=pdf")
    b = TaggedUrn.from_string("cap:test;ext=pdf")
    # equivalent → comparable (AND implies OR)
    assert a.is_equivalent(b)
    assert a.is_comparable(b)

    # comparable but NOT equivalent
    general = TaggedUrn.from_string("cap:test")
    specific = TaggedUrn.from_string("cap:test;ext=pdf")
    assert not general.is_equivalent(specific)
    assert general.is_comparable(specific)


# TEST583: Prefix mismatch raises error for both relations
def test_583_prefix_mismatch_errors():
    cap = TaggedUrn.from_string("cap:test")
    media = TaggedUrn.from_string("media:")
    with pytest.raises(TaggedUrnError):
        cap.is_equivalent(media)
    with pytest.raises(TaggedUrnError):
        cap.is_comparable(media)


# TEST584: Empty tag set is comparable to everything with same prefix
def test_584_empty_tags_comparable_to_all():
    empty = TaggedUrn.from_string("media:")
    specific = TaggedUrn.from_string("media:pdf;thumbnail")
    # empty.accepts(specific) = True (empty has no constraints)
    assert empty.is_comparable(specific)
    # but NOT equivalent (specific has tags empty doesn't)
    assert not empty.is_equivalent(specific)
    # empty is equivalent to itself
    empty2 = TaggedUrn.from_string("media:")
    assert empty.is_equivalent(empty2)


# TEST585: String variants of is_equivalent and is_comparable
def test_585_string_variants():
    urn = TaggedUrn.from_string("media:pdf")
    assert urn.is_equivalent_str("media:pdf")  # same tags
    assert not urn.is_equivalent_str("media:")  # different
    assert urn.is_comparable_str("media:")  # on same chain
    assert not urn.is_comparable_str("media:enc=utf-8;txt")  # different branch


# TEST586: Special values (*, !, ?) with is_equivalent and is_comparable
def test_586_special_values():
    must_have = TaggedUrn.from_string("cap:ext")  # ext=*
    exact = TaggedUrn.from_string("cap:ext=pdf")  # ext=pdf
    must_not = TaggedUrn.from_string("cap:ext=!")  # ext=!
    unspecified = TaggedUrn.from_string("cap:ext=?")  # ext=?

    # must_have (*) and exact (pdf): comparable — a pdf is some ext — and NOT
    # equivalent: equivalence is "the same tag set" (tagged-urn formal,
    # `equivalent_iff_same_forms`).
    assert not must_have.is_equivalent(exact)
    assert must_have.is_comparable(exact)

    # must_not (!) and exact (pdf): incomparable (conflict both directions)
    assert not must_not.is_comparable(exact)
    assert not must_not.is_equivalent(exact)

    # must_not (!) and must_have (*): incomparable (conflict both directions)
    assert not must_not.is_comparable(must_have)
    assert not must_not.is_equivalent(must_have)

    # unspecified (?) accepts everything, and is equivalent only to what also
    # constrains nothing.
    assert not unspecified.is_equivalent(exact)
    assert not unspecified.is_equivalent(must_have)
    assert not unspecified.is_equivalent(must_not)
    assert unspecified.is_comparable(exact)
    assert unspecified.is_equivalent(TaggedUrn.from_string("cap:"))


# =========================================================================
# BUILDER TESTS (mirroring Rust implementation)
# =========================================================================

# TEST587: Builder fluent API for tag manipulation
def test_587_builder_fluent_api():
    urn = (TaggedUrnBuilder("cap")
           .marker("generate")
           .tag("target", "thumbnail")
           .tag("format", "pdf")
           .tag("output", "binary")
           .build())

    assert urn.has_marker_tag("generate")
    assert urn.get_tag("target") == "thumbnail"
    assert urn.get_tag("format") == "pdf"
    assert urn.get_tag("output") == "binary"


# TEST588: Builder with custom tags
def test_588_builder_custom_tags():
    urn = (TaggedUrnBuilder("cap")
           .tag("engine", "v2")
           .tag("quality", "high")
           .marker("compress")
           .build())

    assert urn.get_tag("engine") == "v2"
    assert urn.get_tag("quality") == "high"
    assert urn.has_marker_tag("compress")


# TEST589: Builder tag overrides (last value wins)
def test_589_builder_tag_overrides():
    urn = (TaggedUrnBuilder("cap")
           .marker("convert")
           .tag("format", "jpg")
           .build())

    assert urn.has_marker_tag("convert")
    assert urn.get_tag("format") == "jpg"


# TEST590: Builder empty build raises error (tags required)
def test_590_builder_empty_build():
    # Empty builder raises error - tags are required
    with pytest.raises(TaggedUrnError):
        TaggedUrnBuilder("cap").build()


# TEST591: Builder with single tag
def test_591_builder_single_tag():
    urn = TaggedUrnBuilder("cap").tag("type", "utility").build()

    assert str(urn) == "cap:type=utility"
    assert urn.get_tag("type") == "utility"
    # Six-form ladder: exact value = 4 points.
    assert urn.specificity() == 4


# TEST592: Builder with complex multi-tag URN
def test_592_builder_complex():
    urn = (TaggedUrnBuilder("cap")
           .tag("type", "media")
           .marker("transcode")
           .tag("target", "video")
           .tag("format", "mp4")
           .tag("codec", "h264")
           .tag("quality", "1080p")
           .tag("framerate", "30fps")
           .tag("output", "binary")
           .build())

    assert urn.get_tag("type") == "media"
    assert urn.has_marker_tag("transcode")
    assert urn.get_tag("target") == "video"
    assert urn.get_tag("format") == "mp4"
    assert urn.get_tag("codec") == "h264"
    assert urn.get_tag("quality") == "1080p"
    assert urn.get_tag("framerate") == "30fps"
    assert urn.get_tag("output") == "binary"

    # Six-form ladder: 7 exact-valued tags × 4 + 1 marker (transcode) × 2 = 28 + 2 = 30.
    assert urn.specificity() == 30


# TEST593: Builder with wildcards
def test_593_builder_wildcards():
    urn = (TaggedUrnBuilder("cap")
           .marker("convert")
           .marker("ext")
           .marker("quality")
           .build())

    # Three markers serialize as value-less, sorted alphabetically.
    assert str(urn) == "cap:convert;ext;quality"
    # GRADED SPECIFICITY: 3 markers × 2 points each = 6
    assert urn.specificity() == 6

    assert urn.has_marker_tag("convert")
    assert urn.has_marker_tag("ext")
    assert urn.has_marker_tag("quality")

    assert urn.get_tag("ext") == "*"
    assert urn.get_tag("quality") == "*"


# TEST594: Builder with custom prefix
def test_594_builder_custom_prefix():
    urn = TaggedUrnBuilder("myapp").tag("key", "value").build()

    assert urn.prefix == "myapp"
    assert str(urn) == "myapp:key=value"


# TEST595: Builder matching with built URN
def test_595_builder_matching_with_built_urn():
    # Create a specific instance
    specific_instance = (TaggedUrnBuilder("cap")
                         .tag("op", "generate")
                         .tag("target", "thumbnail")
                         .tag("format", "pdf")
                         .build())

    # Create a more general pattern (fewer constraints)
    general_pattern = TaggedUrnBuilder("cap").tag("op", "generate").build()

    # Create a pattern with wildcard (ext=* means must-have-any)
    wildcard_pattern = (TaggedUrnBuilder("cap")
                        .tag("op", "generate")
                        .tag("target", "thumbnail")
                        .marker("ext")
                        .build())

    # Specific instance should match general pattern (pattern has fewer constraints)
    assert specific_instance.conforms_to(general_pattern)

    # NEW SEMANTICS: wildcardPattern has ext=* which means instance MUST have ext
    # specificInstance doesn't have ext, so this should NOT match
    assert not specific_instance.conforms_to(wildcard_pattern)

    # Check specificity
    assert specific_instance.is_more_specific_than(general_pattern)

    # Six-form ladder: exact = 4 points, * (must-have-any) = 2 points.
    assert specific_instance.specificity() == 12  # 3 exact × 4 = 12
    assert general_pattern.specificity() == 4     # 1 exact × 4 = 4
    assert wildcard_pattern.specificity() == 10   # 2 exact × 4 + 1 * × 2 = 8 + 2 = 10


# TEST599: every row of the proved model's table.
#
# The rules are proved in ../formal (Lean); this is what ties them to this
# mirror: every row of ../formal/conformance.json (written by the model,
# `lake exe conformance`) is parsed by this parser and must get the model's
# verdict — for the guarantee (conforms_to), the possibility (meets), and the
# complete reading of the instance (satisfies, may_satisfy). The same table
# runs in every mirror.
def test_599_every_row_of_the_models_table():
    import json
    import pathlib

    table_path = pathlib.Path(__file__).resolve().parents[2] / "formal" / "conformance.json"
    table = json.loads(table_path.read_text())
    wrong = []
    for row in table["refines"]:
        a = TaggedUrn.from_string(row["instance"])
        b = TaggedUrn.from_string(row["pattern"])
        if a.conforms_to(b) != row["refines"]:
            wrong.append(f"{row['instance']} ⪯ {row['pattern']}: model {row['refines']}")
        if a.is_equivalent(b) != row["equivalent"]:
            wrong.append(f"{row['instance']} ≡ {row['pattern']}: model {row['equivalent']}")
        for name, got in (("meets", a.meets(b)), ("satisfies", a.satisfies(b)),
                          ("may_satisfy", a.may_satisfy(b))):
            if got != row[name]:
                wrong.append(f"{row['instance']} {name} {row['pattern']}: model {row[name]}")
    for row in table["scores"]:
        if TaggedUrn.from_string(row["urn"]).specificity() != row["score"]:
            wrong.append(f"specificity {row['urn']}: model {row['score']}")
    assert len(table["refines"]) > 4000 and len(table["scores"]) > 60, "the table is the full one"
    assert not wrong, f"{len(wrong)} answer(s) differ from the model, e.g. {wrong[:8]}"
