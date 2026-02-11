import pytest
from tagged_urn import TaggedUrn, TaggedUrnBuilder, UrnMatcher, TaggedUrnError


def test_tagged_urn_creation():
    urn = TaggedUrn.from_string("cap:op=generate;ext=pdf;target=thumbnail;")
    assert urn.get_prefix() == "cap"
    assert urn.get_tag("op") == "generate"
    assert urn.get_tag("target") == "thumbnail"
    assert urn.get_tag("ext") == "pdf"


def test_custom_prefix():
    urn = TaggedUrn.from_string("myapp:op=generate;ext=pdf")
    assert urn.get_prefix() == "myapp"
    assert urn.get_tag("op") == "generate"
    assert str(urn) == "myapp:ext=pdf;op=generate"


def test_prefix_case_insensitive():
    urn1 = TaggedUrn.from_string("CAP:op=test")
    urn2 = TaggedUrn.from_string("cap:op=test")
    urn3 = TaggedUrn.from_string("Cap:op=test")

    assert urn1.get_prefix() == "cap"
    assert urn2.get_prefix() == "cap"
    assert urn3.get_prefix() == "cap"
    assert urn1 == urn2
    assert urn2 == urn3


def test_prefix_mismatch_error():
    urn1 = TaggedUrn.from_string("cap:op=test")
    urn2 = TaggedUrn.from_string("myapp:op=test")

    with pytest.raises(TaggedUrnError) as exc_info:
        urn1.conforms_to(urn2)
    assert exc_info.value.expected == "cap"
    assert exc_info.value.actual == "myapp"


def test_builder_with_prefix():
    urn = TaggedUrnBuilder("custom").tag("key", "value").build()

    assert urn.get_prefix() == "custom"
    assert str(urn) == "custom:key=value"


def test_unquoted_values_lowercased():
    # Unquoted values are normalized to lowercase
    urn = TaggedUrn.from_string("cap:OP=Generate;EXT=PDF;Target=Thumbnail;")

    # Keys are always lowercase
    assert urn.get_tag("op") == "generate"
    assert urn.get_tag("ext") == "pdf"
    assert urn.get_tag("target") == "thumbnail"

    # Key lookup is case-insensitive
    assert urn.get_tag("OP") == "generate"
    assert urn.get_tag("Op") == "generate"

    # Both URNs parse to same lowercase values (same tags, same values)
    urn2 = TaggedUrn.from_string("cap:op=generate;ext=pdf;target=thumbnail;")
    assert str(urn) == str(urn2)
    assert urn == urn2


def test_quoted_values_preserve_case():
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


def test_quoted_value_special_chars():
    # Semicolons in quoted values
    urn = TaggedUrn.from_string(r'cap:key="value;with;semicolons"')
    assert urn.get_tag("key") == "value;with;semicolons"

    # Equals in quoted values
    urn2 = TaggedUrn.from_string(r'cap:key="value=with=equals"')
    assert urn2.get_tag("key") == "value=with=equals"

    # Spaces in quoted values
    urn3 = TaggedUrn.from_string(r'cap:key="hello world"')
    assert urn3.get_tag("key") == "hello world"


def test_quoted_value_escape_sequences():
    # Escaped quotes
    urn = TaggedUrn.from_string(r'cap:key="value\"quoted\""')
    assert urn.get_tag("key") == r'value"quoted"'

    # Escaped backslashes
    urn2 = TaggedUrn.from_string(r'cap:key="path\\file"')
    assert urn2.get_tag("key") == r'path\file'

    # Mixed escapes
    urn3 = TaggedUrn.from_string(r'cap:key="say \"hello\\world\""')
    assert urn3.get_tag("key") == r'say "hello\world"'


def test_mixed_quoted_unquoted():
    urn = TaggedUrn.from_string(r'cap:a="Quoted";b=simple')
    assert urn.get_tag("a") == "Quoted"
    assert urn.get_tag("b") == "simple"


def test_unterminated_quote_error():
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(r'cap:key="unterminated')


def test_invalid_escape_sequence_error():
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(r'cap:key="bad\n"')

    # Invalid escape at end
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(r'cap:key="bad\x"')


def test_serialization_smart_quoting():
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


def test_round_trip_simple():
    original = "cap:op=generate;ext=pdf"
    urn = TaggedUrn.from_string(original)
    serialized = str(urn)
    reparsed = TaggedUrn.from_string(serialized)
    assert urn == reparsed


def test_round_trip_quoted():
    original = r'cap:key="Value With Spaces"'
    urn = TaggedUrn.from_string(original)
    serialized = str(urn)
    reparsed = TaggedUrn.from_string(serialized)
    assert urn == reparsed
    assert reparsed.get_tag("key") == "Value With Spaces"


def test_round_trip_escapes():
    original = r'cap:key="value\"with\\escapes"'
    urn = TaggedUrn.from_string(original)
    assert urn.get_tag("key") == r'value"with\escapes'
    serialized = str(urn)
    reparsed = TaggedUrn.from_string(serialized)
    assert urn == reparsed


def test_prefix_required():
    # Missing prefix should fail
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("op=generate;ext=pdf")

    # Valid prefix should work
    urn = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    assert urn.get_tag("op") == "generate"

    # Case-insensitive prefix
    urn2 = TaggedUrn.from_string("CAP:op=generate")
    assert urn2.get_tag("op") == "generate"


def test_trailing_semicolon_equivalence():
    # Both with and without trailing semicolon should be equivalent
    urn1 = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    urn2 = TaggedUrn.from_string("cap:op=generate;ext=pdf;")

    # They should be equal
    assert urn1 == urn2

    # They should have same hash
    assert hash(urn1) == hash(urn2)

    # They should have same string representation (canonical form)
    assert str(urn1) == str(urn2)

    # They should match each other
    assert urn1.conforms_to(urn2)
    assert urn2.conforms_to(urn1)


def test_canonical_string_format():
    urn = TaggedUrn.from_string("cap:op=generate;target=thumbnail;ext=pdf")
    # Should be sorted alphabetically and have no trailing semicolon in canonical form
    # Alphabetical order: ext < op < target
    assert str(urn) == "cap:ext=pdf;op=generate;target=thumbnail"


def test_tag_matching():
    urn = TaggedUrn.from_string("cap:op=generate;ext=pdf;target=thumbnail;")

    # Exact match
    request1 = TaggedUrn.from_string("cap:op=generate;ext=pdf;target=thumbnail;")
    assert urn.conforms_to(request1)

    # Subset match
    request2 = TaggedUrn.from_string("cap:op=generate")
    assert urn.conforms_to(request2)

    # Wildcard request should match specific URN
    request3 = TaggedUrn.from_string("cap:ext=*")
    assert urn.conforms_to(request3)  # URN has ext=pdf, request accepts any ext

    # No match - conflicting value
    request4 = TaggedUrn.from_string("cap:op=extract")
    assert not urn.conforms_to(request4)


def test_matching_case_sensitive_values():
    # Values with different case should NOT match
    urn1 = TaggedUrn.from_string(r'cap:key="Value"')
    urn2 = TaggedUrn.from_string(r'cap:key="value"')
    assert not urn1.conforms_to(urn2)
    assert not urn2.conforms_to(urn1)

    # Same case should match
    urn3 = TaggedUrn.from_string(r'cap:key="Value"')
    assert urn1.conforms_to(urn3)


def test_missing_tag_handling():
    # NEW SEMANTICS: Missing tag in instance means the tag doesn't exist.
    # Pattern constraints must be satisfied by instance.

    urn = TaggedUrn.from_string("cap:op=generate")

    # Pattern with tag that instance doesn't have: NO MATCH
    # Pattern ext=pdf requires instance to have ext=pdf, but instance doesn't have ext
    pattern1 = TaggedUrn.from_string("cap:ext=pdf")
    assert not urn.conforms_to(pattern1)  # Instance missing ext, pattern wants ext=pdf

    # Pattern missing tag = no constraint: MATCH
    # Instance has op=generate, pattern has no constraint on op
    urn2 = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    pattern2 = TaggedUrn.from_string("cap:op=generate")
    assert urn2.conforms_to(pattern2)  # Instance has ext=pdf, pattern doesn't constrain ext

    # To match any value of a tag, use explicit ? or *
    pattern3 = TaggedUrn.from_string("cap:ext=?")  # ? = no constraint
    assert urn.conforms_to(pattern3)  # Instance missing ext, pattern doesn't care

    # * means must-have-any - instance must have the tag
    pattern4 = TaggedUrn.from_string("cap:ext=*")
    assert not urn.conforms_to(pattern4)  # Instance missing ext, pattern requires ext to be present


def test_specificity():
    # NEW GRADED SPECIFICITY:
    # K=v (exact value): 3 points
    # K=* (must-have-any): 2 points
    # K=! (must-not-have): 1 point
    # K=? (unspecified): 0 points

    urn1 = TaggedUrn.from_string("cap:general")  # value-less = * = 2 points
    urn2 = TaggedUrn.from_string("cap:op=generate")  # exact = 3 points
    urn3 = TaggedUrn.from_string("cap:op=*;ext=pdf")  # * + exact = 2 + 3 = 5 points
    urn4 = TaggedUrn.from_string("cap:op=?")  # ? = 0 points
    urn5 = TaggedUrn.from_string("cap:op=!")  # ! = 1 point

    assert urn1.specificity() == 2  # * = 2
    assert urn2.specificity() == 3  # exact = 3
    assert urn3.specificity() == 5  # * + exact = 2 + 3
    assert urn4.specificity() == 0  # ? = 0
    assert urn5.specificity() == 1  # ! = 1

    # Specificity tuple for tie-breaking: (exact_count, must_have_any_count, must_not_count)
    assert urn2.specificity_tuple() == (1, 0, 0)
    assert urn3.specificity_tuple() == (1, 1, 0)
    assert urn5.specificity_tuple() == (0, 0, 1)

    assert urn2.is_more_specific_than(urn1)  # 3 > 2


def test_builder():
    urn = (TaggedUrnBuilder("cap")
           .tag("op", "generate")
           .tag("target", "thumbnail")
           .tag("ext", "pdf")
           .tag("output", "binary")
           .build())

    assert urn.get_tag("op") == "generate"
    assert urn.get_tag("output") == "binary"


def test_builder_preserves_case():
    urn = TaggedUrnBuilder("cap").tag("KEY", "ValueWithCase").build()

    # Key is lowercase
    assert urn.get_tag("key") == "ValueWithCase"
    # Value case preserved, so needs quoting
    assert str(urn) == r'cap:key="ValueWithCase"'


def test_compatibility():
    # TEST526: Test directional accepts between general and specific URNs
    general = TaggedUrn.from_string("cap:op=generate")
    specific = TaggedUrn.from_string("cap:op=generate;ext=pdf")

    # General pattern accepts specific instance (no constraint on ext)
    assert general.accepts(specific)
    # Specific does NOT accept general (missing ext in instance fails specific pattern's ext=pdf)
    assert not specific.accepts(general)

    # Unrelated URNs: different op values, neither accepts the other
    urn_extract = TaggedUrn.from_string("cap:image;op=extract")
    assert not general.accepts(urn_extract)
    assert not urn_extract.accepts(general)

    # Wildcard format tag: general (no format constraint) accepts urn_format
    urn_format = TaggedUrn.from_string("cap:op=generate;format=*")
    assert general.accepts(urn_format)
    # urn_format does NOT accept general: pattern format=* requires instance to have format tag
    assert not urn_format.accepts(general)


def test_best_match():
    urns = [
        TaggedUrn.from_string("cap:op=*"),
        TaggedUrn.from_string("cap:op=generate"),
        TaggedUrn.from_string("cap:op=generate;ext=pdf"),
    ]

    request = TaggedUrn.from_string("cap:op=generate")
    best = UrnMatcher.find_best_match(urns, request)

    # Most specific URN that can handle the request
    # Alphabetical order: ext < op
    assert str(best) == "cap:ext=pdf;op=generate"


def test_merge_and_subset():
    urn1 = TaggedUrn.from_string("cap:op=generate")
    urn2 = TaggedUrn.from_string("cap:ext=pdf;output=binary")

    merged = urn1.merge(urn2)
    # Alphabetical order: ext < op < output
    assert str(merged) == "cap:ext=pdf;op=generate;output=binary"

    subset = merged.subset(["type", "ext"])
    assert str(subset) == "cap:ext=pdf"


def test_merge_prefix_mismatch():
    urn1 = TaggedUrn.from_string("cap:op=generate")
    urn2 = TaggedUrn.from_string("myapp:ext=pdf")

    with pytest.raises(TaggedUrnError):
        urn1.merge(urn2)


def test_wildcard_tag():
    urn = TaggedUrn.from_string("cap:ext=pdf")
    wildcarded = urn.with_wildcard_tag("ext")

    # Wildcard serializes as value-less tag
    assert str(wildcarded) == "cap:ext"

    # Test that wildcarded URN can match more requests
    request = TaggedUrn.from_string("cap:ext=jpg")
    assert not urn.conforms_to(request)
    assert wildcarded.conforms_to(TaggedUrn.from_string("cap:ext"))


def test_empty_tagged_urn():
    # Empty tagged URN is valid
    empty_urn = TaggedUrn.from_string("cap:")
    assert len(empty_urn.tags) == 0
    assert str(empty_urn) == "cap:"

    # NEW SEMANTICS:
    # Empty PATTERN matches any INSTANCE (pattern has no constraints)
    # Empty INSTANCE only matches patterns that have no required tags

    specific_urn = TaggedUrn.from_string("cap:op=generate;ext=pdf")

    # Empty instance vs specific pattern: NO MATCH
    # Pattern requires op=generate and ext=pdf, instance doesn't have them
    assert not empty_urn.conforms_to(specific_urn)

    # Specific instance vs empty pattern: MATCH
    # Pattern has no constraints, instance can have anything
    assert specific_urn.conforms_to(empty_urn)

    # Empty instance vs empty pattern: MATCH
    assert empty_urn.conforms_to(empty_urn)

    # With trailing semicolon
    empty_urn2 = TaggedUrn.from_string("cap:;")
    assert len(empty_urn2.tags) == 0


def test_empty_with_custom_prefix():
    empty_urn = TaggedUrn.from_string("myapp:")
    assert empty_urn.get_prefix() == "myapp"
    assert len(empty_urn.tags) == 0
    assert str(empty_urn) == "myapp:"


def test_extended_character_support():
    # Test forward slashes and colons in tag components
    urn = TaggedUrn.from_string("cap:url=https://example_org/api;path=/some/file")
    assert urn.get_tag("url") == "https://example_org/api"
    assert urn.get_tag("path") == "/some/file"


def test_wildcard_restrictions():
    # Wildcard should be rejected in keys
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:*=value")

    # Wildcard should be accepted in values
    urn = TaggedUrn.from_string("cap:key=*")
    assert urn.get_tag("key") == "*"


def test_duplicate_key_rejection():
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=value1;key=value2")


def test_numeric_key_restriction():
    # Pure numeric keys should be rejected
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:123=value")

    # Mixed alphanumeric keys should be allowed
    assert TaggedUrn.from_string("cap:key123=value")
    assert TaggedUrn.from_string("cap:123key=value")

    # Pure numeric values should be allowed
    assert TaggedUrn.from_string("cap:key=123")


def test_empty_value_error():
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=")
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=;other=value")


def test_has_tag_case_sensitive():
    urn = TaggedUrn.from_string(r'cap:key="Value"')

    # Exact case match works
    assert urn.has_tag("key", "Value")

    # Different case does not match
    assert not urn.has_tag("key", "value")
    assert not urn.has_tag("key", "VALUE")

    # Key lookup is case-insensitive
    assert urn.has_tag("KEY", "Value")
    assert urn.has_tag("Key", "Value")


def test_with_tag_preserves_value():
    urn = TaggedUrn.empty("cap").with_tag("key", "ValueWithCase")
    assert urn.get_tag("key") == "ValueWithCase"


def test_with_tag_rejects_empty_value():
    with pytest.raises(TaggedUrnError) as exc_info:
        TaggedUrn.empty("cap").with_tag("key", "")
    assert "empty value" in str(exc_info.value).lower()


def test_builder_rejects_empty_value():
    with pytest.raises(TaggedUrnError) as exc_info:
        TaggedUrnBuilder("cap").tag("key", "")
    assert "empty value" in str(exc_info.value).lower()


def test_semantic_equivalence():
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

def test_matching_semantics_test1_exact_match():
    # Test 1: Exact match
    # URN:     cap:op=generate;ext=pdf
    # Request: cap:op=generate;ext=pdf
    # Result:  MATCH
    urn = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    request = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    assert urn.conforms_to(request), "Test 1: Exact match should succeed"


def test_matching_semantics_test2_instance_missing_tag():
    # Test 2: Instance missing tag
    # Instance: cap:op=generate
    # Pattern:  cap:op=generate;ext=pdf
    # Result:   NO MATCH (pattern requires ext=pdf, instance doesn't have ext)
    #
    # NEW SEMANTICS: Missing tag in instance means it doesn't exist.
    # Pattern K=v requires instance to have K=v.
    instance = TaggedUrn.from_string("cap:op=generate")
    pattern = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    assert not instance.conforms_to(pattern), "Test 2: Instance missing tag should NOT match when pattern requires it"

    # To accept any ext (or missing), use pattern with ext=?
    pattern_optional = TaggedUrn.from_string("cap:op=generate;ext=?")
    assert instance.conforms_to(pattern_optional), "Pattern with ext=? should match instance without ext"


def test_matching_semantics_test3_urn_has_extra_tag():
    # Test 3: URN has extra tag
    # URN:     cap:op=generate;ext=pdf;version=2
    # Request: cap:op=generate;ext=pdf
    # Result:  MATCH (request doesn't constrain version)
    urn = TaggedUrn.from_string("cap:op=generate;ext=pdf;version=2")
    request = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    assert urn.conforms_to(request), "Test 3: URN with extra tag should match"


def test_matching_semantics_test4_request_has_wildcard():
    # Test 4: Request has wildcard
    # URN:     cap:op=generate;ext=pdf
    # Request: cap:op=generate;ext=*
    # Result:  MATCH (request accepts any ext)
    urn = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    request = TaggedUrn.from_string("cap:op=generate;ext=*")
    assert urn.conforms_to(request), "Test 4: Request wildcard should match"


def test_matching_semantics_test5_urn_has_wildcard():
    # Test 5: URN has wildcard
    # URN:     cap:op=generate;ext=*
    # Request: cap:op=generate;ext=pdf
    # Result:  MATCH (URN handles any ext)
    urn = TaggedUrn.from_string("cap:op=generate;ext=*")
    request = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    assert urn.conforms_to(request), "Test 5: URN wildcard should match"


def test_matching_semantics_test6_value_mismatch():
    # Test 6: Value mismatch
    # URN:     cap:op=generate;ext=pdf
    # Request: cap:op=generate;ext=docx
    # Result:  NO MATCH
    urn = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    request = TaggedUrn.from_string("cap:op=generate;ext=docx")
    assert not urn.conforms_to(request), "Test 6: Value mismatch should not match"


def test_matching_semantics_test7_pattern_has_extra_tag():
    # Test 7: Pattern has extra tag that instance doesn't have
    # Instance: cap:op=generate_thumbnail;out="media:binary"
    # Pattern:  cap:op=generate_thumbnail;out="media:binary";ext=wav
    # Result:   NO MATCH (pattern requires ext=wav, instance doesn't have ext)
    #
    # NEW SEMANTICS: Pattern K=v requires instance to have K=v
    instance = TaggedUrn.from_string(r'cap:op=generate_thumbnail;out="media:binary"')
    pattern = TaggedUrn.from_string(r'cap:op=generate_thumbnail;out="media:binary";ext=wav')
    assert not instance.conforms_to(pattern), "Test 7: Instance missing ext should NOT match when pattern requires ext=wav"

    # Instance vs pattern that doesn't constrain ext: MATCH
    pattern_no_ext = TaggedUrn.from_string(r'cap:op=generate_thumbnail;out="media:binary"')
    assert instance.conforms_to(pattern_no_ext)


def test_matching_semantics_test8_empty_pattern_matches_anything():
    # Test 8: Empty PATTERN matches any INSTANCE
    # Instance: cap:op=generate;ext=pdf
    # Pattern:  cap:
    # Result:   MATCH (pattern has no constraints)
    #
    # NEW SEMANTICS: Empty pattern = no constraints = matches any instance
    # But empty instance only matches patterns that don't require tags
    instance = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    empty_pattern = TaggedUrn.from_string("cap:")
    assert instance.conforms_to(empty_pattern), "Test 8: Any instance should match empty pattern"

    # Empty instance vs pattern with requirements: NO MATCH
    empty_instance = TaggedUrn.from_string("cap:")
    pattern = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    assert not empty_instance.conforms_to(pattern), "Empty instance should NOT match pattern with requirements"


def test_matching_semantics_test9_cross_dimension_constraints():
    # Test 9: Cross-dimension constraints
    # Instance: cap:op=generate
    # Pattern:  cap:ext=pdf
    # Result:   NO MATCH (pattern requires ext=pdf, instance doesn't have ext)
    #
    # NEW SEMANTICS: Pattern K=v requires instance to have K=v
    instance = TaggedUrn.from_string("cap:op=generate")
    pattern = TaggedUrn.from_string("cap:ext=pdf")
    assert not instance.conforms_to(pattern), "Test 9: Instance without ext should NOT match pattern requiring ext"

    # Instance with ext vs pattern with different tag only: MATCH
    instance2 = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    pattern2 = TaggedUrn.from_string("cap:ext=pdf")
    assert instance2.conforms_to(pattern2), "Instance with ext=pdf should match pattern requiring ext=pdf"


def test_matching_different_prefixes_error():
    # URNs with different prefixes should cause an error, not just return false
    urn1 = TaggedUrn.from_string("cap:op=test")
    urn2 = TaggedUrn.from_string("other:op=test")

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

def test_valueless_tag_parsing_single():
    # Single value-less tag
    urn = TaggedUrn.from_string("cap:optimize")
    assert urn.get_tag("optimize") == "*"
    # Serializes as value-less (no =*)
    assert str(urn) == "cap:optimize"


def test_valueless_tag_parsing_multiple():
    # Multiple value-less tags
    urn = TaggedUrn.from_string("cap:fast;optimize;secure")
    assert urn.get_tag("fast") == "*"
    assert urn.get_tag("optimize") == "*"
    assert urn.get_tag("secure") == "*"
    # Serializes alphabetically as value-less
    assert str(urn) == "cap:fast;optimize;secure"


def test_valueless_tag_mixed_with_valued():
    # Mix of value-less and valued tags
    urn = TaggedUrn.from_string("cap:op=generate;optimize;ext=pdf;secure")
    assert urn.get_tag("op") == "generate"
    assert urn.get_tag("optimize") == "*"
    assert urn.get_tag("ext") == "pdf"
    assert urn.get_tag("secure") == "*"
    # Serializes alphabetically
    assert str(urn) == "cap:ext=pdf;op=generate;optimize;secure"


def test_valueless_tag_at_end():
    # Value-less tag at the end (no trailing semicolon)
    urn = TaggedUrn.from_string("cap:op=generate;optimize")
    assert urn.get_tag("op") == "generate"
    assert urn.get_tag("optimize") == "*"
    assert str(urn) == "cap:op=generate;optimize"


def test_valueless_tag_equivalence_to_wildcard():
    # Value-less tag is equivalent to explicit wildcard
    valueless = TaggedUrn.from_string("cap:ext")
    wildcard = TaggedUrn.from_string("cap:ext=*")
    assert valueless == wildcard
    # Both serialize to value-less form
    assert str(valueless) == "cap:ext"
    assert str(wildcard) == "cap:ext"


def test_valueless_tag_matching():
    # Value-less tag (wildcard) matches any value
    urn = TaggedUrn.from_string("cap:op=generate;ext")

    request_pdf = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    request_docx = TaggedUrn.from_string("cap:op=generate;ext=docx")
    request_any = TaggedUrn.from_string("cap:op=generate;ext=anything")

    assert urn.conforms_to(request_pdf)
    assert urn.conforms_to(request_docx)
    assert urn.conforms_to(request_any)


def test_valueless_tag_in_pattern():
    # Pattern with value-less tag (K=*) requires instance to have the tag
    pattern = TaggedUrn.from_string("cap:op=generate;ext")

    instance_pdf = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    instance_docx = TaggedUrn.from_string("cap:op=generate;ext=docx")
    instance_missing = TaggedUrn.from_string("cap:op=generate")

    # NEW SEMANTICS: K=* (valueless tag) means must-have-any
    assert instance_pdf.conforms_to(pattern)  # Has ext=pdf
    assert instance_docx.conforms_to(pattern)  # Has ext=docx
    assert not instance_missing.conforms_to(pattern)  # Missing ext, pattern requires it

    # To accept missing ext, use ? instead
    pattern_optional = TaggedUrn.from_string("cap:op=generate;ext=?")
    assert instance_missing.conforms_to(pattern_optional)


def test_valueless_tag_specificity():
    # NEW GRADED SPECIFICITY:
    # K=v (exact): 3, K=* (must-have-any): 2, K=! (must-not): 1, K=? (unspecified): 0

    urn1 = TaggedUrn.from_string("cap:op=generate")
    urn2 = TaggedUrn.from_string("cap:op=generate;optimize")  # optimize = *
    urn3 = TaggedUrn.from_string("cap:op=generate;ext=pdf")

    assert urn1.specificity() == 3  # 1 exact = 3
    assert urn2.specificity() == 5  # 1 exact + 1 * = 3 + 2 = 5
    assert urn3.specificity() == 6  # 2 exact = 3 + 3 = 6


def test_valueless_tag_roundtrip():
    # Round-trip parsing and serialization
    original = "cap:ext=pdf;op=generate;optimize;secure"
    urn = TaggedUrn.from_string(original)
    serialized = str(urn)
    reparsed = TaggedUrn.from_string(serialized)
    assert urn == reparsed
    assert serialized == original


def test_valueless_tag_case_normalization():
    # Value-less tags are normalized to lowercase like other keys
    urn = TaggedUrn.from_string("cap:OPTIMIZE;Fast;SECURE")
    assert urn.get_tag("optimize") == "*"
    assert urn.get_tag("fast") == "*"
    assert urn.get_tag("secure") == "*"
    assert str(urn) == "cap:fast;optimize;secure"


def test_empty_value_still_error():
    # Empty value with = is still an error (different from value-less)
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=")
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:key=;other=value")


def test_valueless_tag_compatibility():
    # TEST564: Value-less tags (wildcard) accept any specific value
    urn_wildcard = TaggedUrn.from_string("cap:op=generate;ext")  # ext=*
    urn_pdf = TaggedUrn.from_string("cap:op=generate;ext=pdf")
    urn_docx = TaggedUrn.from_string("cap:op=generate;ext=docx")

    # Wildcard pattern accepts specific instances
    assert urn_wildcard.accepts(urn_pdf)
    assert urn_wildcard.accepts(urn_docx)
    # Specific instances also accept wildcard (instance * matches pattern's exact value)
    assert urn_pdf.accepts(urn_wildcard)
    assert urn_docx.accepts(urn_wildcard)
    # Different specific values: neither accepts the other
    assert not urn_pdf.accepts(urn_docx)
    assert not urn_docx.accepts(urn_pdf)


def test_valueless_numeric_key_still_rejected():
    # Purely numeric keys are still rejected for value-less tags
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:123")
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:op=generate;456")


def test_whitespace_in_input_rejected():
    # Leading whitespace fails hard
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(" cap:op=test")

    # Trailing whitespace fails hard
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:op=test ")

    # Both leading and trailing whitespace fails hard
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string(" cap:op=test ")

    # Tab and newline also count as whitespace
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("\tcap:op=test")
    with pytest.raises(TaggedUrnError):
        TaggedUrn.from_string("cap:op=test\n")

    # Clean input works
    assert TaggedUrn.from_string("cap:op=test")


# ============================================================================
# NEW SEMANTICS TESTS: ? (unspecified) and ! (must-not-have)
# ============================================================================

def test_unspecified_question_mark_parsing():
    # ? parses as unspecified
    urn = TaggedUrn.from_string("cap:ext=?")
    assert urn.get_tag("ext") == "?"
    # Serializes as key=?
    assert str(urn) == "cap:ext=?"


def test_must_not_have_exclamation_parsing():
    # ! parses as must-not-have
    urn = TaggedUrn.from_string("cap:ext=!")
    assert urn.get_tag("ext") == "!"
    # Serializes as key=!
    assert str(urn) == "cap:ext=!"


def test_question_mark_pattern_matches_anything():
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


def test_question_mark_in_instance():
    # Instance with K=? matches any pattern constraint
    instance = TaggedUrn.from_string("cap:ext=?")

    pattern_pdf = TaggedUrn.from_string("cap:ext=pdf")
    pattern_wildcard = TaggedUrn.from_string("cap:ext=*")
    pattern_must_not = TaggedUrn.from_string("cap:ext=!")
    pattern_question = TaggedUrn.from_string("cap:ext=?")
    pattern_missing = TaggedUrn.from_string("cap:")

    assert instance.conforms_to(pattern_pdf), "ext=? should match ext=pdf"
    assert instance.conforms_to(pattern_wildcard), "ext=? should match ext=*"
    assert instance.conforms_to(pattern_must_not), "ext=? should match ext=!"
    assert instance.conforms_to(pattern_question), "ext=? should match ext=?"
    assert instance.conforms_to(pattern_missing), "ext=? should match (no ext)"


def test_must_not_have_pattern_requires_absent():
    # Pattern with K=! requires instance to NOT have K
    pattern = TaggedUrn.from_string("cap:ext=!")

    instance_missing = TaggedUrn.from_string("cap:")
    instance_pdf = TaggedUrn.from_string("cap:ext=pdf")
    instance_wildcard = TaggedUrn.from_string("cap:ext=*")
    instance_must_not = TaggedUrn.from_string("cap:ext=!")

    assert instance_missing.conforms_to(pattern), "(no ext) should match ext=!"
    assert not instance_pdf.conforms_to(pattern), "ext=pdf should NOT match ext=!"
    assert not instance_wildcard.conforms_to(pattern), "ext=* should NOT match ext=!"
    assert instance_must_not.conforms_to(pattern), "ext=! should match ext=!"


def test_must_not_have_in_instance():
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


def test_full_cross_product_matching():
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
    check("cap:", "cap:k=!", True, "(none)/K=!")
    check("cap:", "cap:k", False, "(none)/K=*")  # K is valueless = *
    check("cap:", "cap:k=v", False, "(none)/K=v")

    # Instance K=?, Pattern variations
    check("cap:k=?", "cap:", True, "K=?/(none)")
    check("cap:k=?", "cap:k=?", True, "K=?/K=?")
    check("cap:k=?", "cap:k=!", True, "K=?/K=!")
    check("cap:k=?", "cap:k", True, "K=?/K=*")
    check("cap:k=?", "cap:k=v", True, "K=?/K=v")

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
    check("cap:k", "cap:k=v", True, "K=*/K=v")

    # Instance K=v, Pattern variations
    check("cap:k=v", "cap:", True, "K=v/(none)")
    check("cap:k=v", "cap:k=?", True, "K=v/K=?")
    check("cap:k=v", "cap:k=!", False, "K=v/K=!")
    check("cap:k=v", "cap:k", True, "K=v/K=*")
    check("cap:k=v", "cap:k=v", True, "K=v/K=v")
    check("cap:k=v", "cap:k=w", False, "K=v/K=w")


def test_mixed_special_values():
    # Test URNs with multiple special values
    pattern = TaggedUrn.from_string("cap:required;optional=?;forbidden=!;exact=pdf")

    # Instance that satisfies all constraints
    good_instance = TaggedUrn.from_string("cap:required=yes;optional=maybe;exact=pdf")
    assert good_instance.conforms_to(pattern)

    # Instance missing required tag
    missing_required = TaggedUrn.from_string("cap:optional=maybe;exact=pdf")
    assert not missing_required.conforms_to(pattern)

    # Instance has forbidden tag
    has_forbidden = TaggedUrn.from_string("cap:required=yes;forbidden=oops;exact=pdf")
    assert not has_forbidden.conforms_to(pattern)

    # Instance with wrong exact value
    wrong_exact = TaggedUrn.from_string("cap:required=yes;exact=doc")
    assert not wrong_exact.conforms_to(pattern)


def test_serialization_round_trip_special_values():
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


def test_compatibility_with_special_values():
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

    # ! vs ?: bidirectional (? accepts everything)
    assert unspecified.accepts(must_not)
    assert must_not.accepts(unspecified)

    # ! vs missing: missing has no ext constraint, ! has ext=!
    # missing.accepts(must_not): pattern=missing has no ext constraint -> True
    assert missing.accepts(must_not)
    # must_not.accepts(missing): pattern=must_not has ext=!, instance=missing has no ext -> True (absent matches !)
    assert must_not.accepts(missing)

    # ! vs !: both accept each other
    assert must_not.accepts(must_not)

    # * vs specific: * accepts specific (pattern * matches any value)
    assert must_have.accepts(specific)
    # specific accepts *: pattern specific=pdf, instance *=any -> True (* in instance matches any pattern value)
    assert specific.accepts(must_have)

    # * vs *: both accept each other
    assert must_have.accepts(must_have)

    # ? accepts everything
    assert unspecified.accepts(must_not)
    assert unspecified.accepts(must_have)
    assert unspecified.accepts(specific)
    assert unspecified.accepts(unspecified)
    assert unspecified.accepts(missing)


def test_specificity_with_special_values():
    # Verify graded specificity scoring
    exact = TaggedUrn.from_string("cap:a=x;b=y;c=z")  # 3*3 = 9
    must_have = TaggedUrn.from_string("cap:a;b;c")  # 3*2 = 6
    must_not = TaggedUrn.from_string("cap:a=!;b=!;c=!")  # 3*1 = 3
    unspecified = TaggedUrn.from_string("cap:a=?;b=?;c=?")  # 3*0 = 0
    mixed = TaggedUrn.from_string("cap:a=x;b;c=!;d=?")  # 3+2+1+0 = 6

    assert exact.specificity() == 9
    assert must_have.specificity() == 6
    assert must_not.specificity() == 3
    assert unspecified.specificity() == 0
    assert mixed.specificity() == 6

    # Test specificity tuples
    assert exact.specificity_tuple() == (3, 0, 0)
    assert must_have.specificity_tuple() == (0, 3, 0)
    assert must_not.specificity_tuple() == (0, 0, 3)
    assert unspecified.specificity_tuple() == (0, 0, 0)
    assert mixed.specificity_tuple() == (1, 1, 1)
