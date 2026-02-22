"""Flat Tag-Based URN Identifier System

This module provides a flat, tag-based tagged URN system with configurable
prefixes, wildcard support, and specificity comparison.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


# Error classes
class TaggedUrnError(Exception):
    """Base exception for tagged URN errors"""
    pass


class EmptyError(TaggedUrnError):
    """Empty or malformed URN"""
    pass


class MissingPrefixError(TaggedUrnError):
    """URN does not have a prefix (no colon found)"""
    pass


class EmptyPrefixError(TaggedUrnError):
    """Empty prefix (colon at start)"""
    pass


class InvalidTagFormatError(TaggedUrnError):
    """Tag not in key=value format"""
    pass


class EmptyTagComponentError(TaggedUrnError):
    """Empty key or value component"""
    pass


class InvalidCharacterError(TaggedUrnError):
    """Disallowed character in key/value"""
    pass


class DuplicateKeyError(TaggedUrnError):
    """Same key appears twice"""
    pass


class NumericKeyError(TaggedUrnError):
    """Key is purely numeric"""
    pass


class UnterminatedQuoteError(TaggedUrnError):
    """Quoted value never closed"""
    pass


class InvalidEscapeSequenceError(TaggedUrnError):
    """Invalid escape in quoted value (only \" and \\ allowed)"""
    pass


class PrefixMismatchError(TaggedUrnError):
    """Prefix mismatch when comparing URNs from different domains"""
    def __init__(self, expected: str, actual: str):
        self.expected = expected
        self.actual = actual
        super().__init__(f"Cannot compare URNs with different prefixes: '{expected}' vs '{actual}'")


class WhitespaceInInputError(TaggedUrnError):
    """Input has leading or trailing whitespace"""
    pass


class ParseState(Enum):
    """Parser states for the state machine"""
    EXPECTING_KEY = 1
    IN_KEY = 2
    EXPECTING_VALUE = 3
    IN_UNQUOTED_VALUE = 4
    IN_QUOTED_VALUE = 5
    IN_QUOTED_VALUE_ESCAPE = 6
    EXPECTING_SEMI_OR_END = 7


class TaggedUrn:
    """A tagged URN using flat, ordered tags with a configurable prefix

    Examples:
    - `cap:op=generate;ext=pdf;output=binary;target=thumbnail`
    - `myapp:key="Value With Spaces"`
    - `custom:a=1;b=2`
    """

    def __init__(self, prefix: str, tags: Dict[str, str]):
        """Create a new tagged URN from tags with a specified prefix

        Keys are normalized to lowercase; values are preserved as-is
        """
        self.prefix = prefix.lower()
        self.tags = {k.lower(): v for k, v in tags.items()}

    @classmethod
    def empty(cls, prefix: str) -> 'TaggedUrn':
        """Create an empty tagged URN with the specified prefix"""
        return cls(prefix, {})

    @classmethod
    def from_string(cls, s: str) -> 'TaggedUrn':
        """Create a tagged URN from a string representation

        Format: `prefix:key1=value1;key2=value2;...` or `prefix:key1="value with spaces";key2=simple`
        The prefix is required and ends at the first colon
        Trailing semicolons are optional and ignored
        Tags are automatically sorted alphabetically for canonical form

        Case handling:
        - Prefix: Normalized to lowercase
        - Keys: Always normalized to lowercase
        - Unquoted values: Normalized to lowercase
        - Quoted values: Case preserved exactly as specified
        """
        # Fail hard on leading/trailing whitespace
        if s != s.strip():
            raise WhitespaceInInputError(f"Tagged URN has leading or trailing whitespace: '{s}'")

        if not s:
            raise EmptyError("Tagged URN cannot be empty")

        # Find the prefix (everything before the first colon)
        colon_pos = s.find(':')
        if colon_pos == -1:
            raise MissingPrefixError("Tagged URN must have a prefix followed by ':'")

        if colon_pos == 0:
            raise EmptyPrefixError("Tagged URN prefix cannot be empty")

        prefix = s[:colon_pos].lower()
        tags_part = s[colon_pos + 1:]
        tags: Dict[str, str] = {}

        # Handle empty tagged URN (prefix: with no tags)
        if not tags_part or tags_part == ";":
            return cls(prefix, tags)

        state = ParseState.EXPECTING_KEY
        current_key = ""
        current_value = ""
        chars = list(tags_part)
        pos = 0

        while pos < len(chars):
            c = chars[pos]

            if state == ParseState.EXPECTING_KEY:
                if c == ';':
                    # Empty segment, skip
                    pos += 1
                    continue
                elif cls._is_valid_key_char(c):
                    current_key += c.lower()
                    state = ParseState.IN_KEY
                else:
                    raise InvalidCharacterError(f"invalid character '{c}' at position {pos}")

            elif state == ParseState.IN_KEY:
                if c == '=':
                    if not current_key:
                        raise EmptyTagComponentError("empty key")
                    state = ParseState.EXPECTING_VALUE
                elif c == ';':
                    # Value-less tag: treat as wildcard
                    if not current_key:
                        raise EmptyTagComponentError("empty key")
                    current_value = "*"
                    cls._finish_tag(tags, current_key, current_value)
                    current_key = ""
                    current_value = ""
                    state = ParseState.EXPECTING_KEY
                elif cls._is_valid_key_char(c):
                    current_key += c.lower()
                else:
                    raise InvalidCharacterError(f"invalid character '{c}' in key at position {pos}")

            elif state == ParseState.EXPECTING_VALUE:
                if c == '"':
                    state = ParseState.IN_QUOTED_VALUE
                elif c == ';':
                    raise EmptyTagComponentError(f"empty value for key '{current_key}'")
                elif cls._is_valid_unquoted_value_char(c):
                    current_value += c.lower()
                    state = ParseState.IN_UNQUOTED_VALUE
                else:
                    raise InvalidCharacterError(f"invalid character '{c}' in value at position {pos}")

            elif state == ParseState.IN_UNQUOTED_VALUE:
                if c == ';':
                    cls._finish_tag(tags, current_key, current_value)
                    current_key = ""
                    current_value = ""
                    state = ParseState.EXPECTING_KEY
                elif cls._is_valid_unquoted_value_char(c):
                    current_value += c.lower()
                else:
                    raise InvalidCharacterError(f"invalid character '{c}' in unquoted value at position {pos}")

            elif state == ParseState.IN_QUOTED_VALUE:
                if c == '"':
                    state = ParseState.EXPECTING_SEMI_OR_END
                elif c == '\\':
                    state = ParseState.IN_QUOTED_VALUE_ESCAPE
                else:
                    # Any character allowed in quoted value, preserve case
                    current_value += c

            elif state == ParseState.IN_QUOTED_VALUE_ESCAPE:
                if c == '"' or c == '\\':
                    current_value += c
                    state = ParseState.IN_QUOTED_VALUE
                else:
                    raise InvalidEscapeSequenceError(f"Invalid escape sequence at position {pos} (only \\\" and \\\\ allowed)")

            elif state == ParseState.EXPECTING_SEMI_OR_END:
                if c == ';':
                    cls._finish_tag(tags, current_key, current_value)
                    current_key = ""
                    current_value = ""
                    state = ParseState.EXPECTING_KEY
                else:
                    raise InvalidCharacterError(f"expected ';' or end after quoted value, got '{c}' at position {pos}")

            pos += 1

        # Handle end of input
        if state in (ParseState.IN_UNQUOTED_VALUE, ParseState.EXPECTING_SEMI_OR_END):
            cls._finish_tag(tags, current_key, current_value)
        elif state == ParseState.EXPECTING_KEY:
            # Valid - trailing semicolon or empty input after prefix
            pass
        elif state in (ParseState.IN_QUOTED_VALUE, ParseState.IN_QUOTED_VALUE_ESCAPE):
            raise UnterminatedQuoteError(f"Unterminated quote at position {pos}")
        elif state == ParseState.IN_KEY:
            # Value-less tag at end: treat as wildcard
            if not current_key:
                raise EmptyTagComponentError("empty key")
            current_value = "*"
            cls._finish_tag(tags, current_key, current_value)
        elif state == ParseState.EXPECTING_VALUE:
            raise EmptyTagComponentError(f"empty value for key '{current_key}'")

        return cls(prefix, tags)

    @staticmethod
    def _finish_tag(tags: Dict[str, str], key: str, value: str) -> None:
        """Finish a tag by validating and inserting it"""
        if not key:
            raise EmptyTagComponentError("empty key")
        if not value:
            raise EmptyTagComponentError(f"empty value for key '{key}'")

        # Check for duplicate keys
        if key in tags:
            raise DuplicateKeyError(f"Duplicate tag key: {key}")

        # Validate key cannot be purely numeric
        if TaggedUrn._is_purely_numeric(key):
            raise NumericKeyError(f"Tag key cannot be purely numeric: {key}")

        tags[key] = value

    @staticmethod
    def _is_valid_key_char(c: str) -> bool:
        """Check if character is valid for a key"""
        return c.isalnum() or c in ('_', '-', '/', ':', '.')

    @staticmethod
    def _is_valid_unquoted_value_char(c: str) -> bool:
        """Check if character is valid for an unquoted value"""
        return c.isalnum() or c in ('_', '-', '/', ':', '.', '*', '?', '!')

    @staticmethod
    def _is_purely_numeric(s: str) -> bool:
        """Check if a string is purely numeric"""
        return bool(s) and s.isdigit()

    @staticmethod
    def _needs_quoting(value: str) -> bool:
        """Check if a value needs quoting for serialization"""
        return any(c in (';', '=', '"', '\\', ' ') or c.isupper() for c in value)

    @staticmethod
    def _quote_value(value: str) -> str:
        """Quote a value for serialization"""
        result = '"'
        for c in value:
            if c in ('"', '\\'):
                result += '\\'
            result += c
        result += '"'
        return result

    def tags_to_string(self) -> str:
        """Serialize just the tags portion (without prefix)

        Returns the tags in canonical form with proper quoting and sorting.
        This is the portion after the ":" in a full URN string.
        """
        # Sort keys for canonical form
        sorted_tags = sorted(self.tags.items())

        tags_str_list = []
        for k, v in sorted_tags:
            if v == "*":
                # Valueless sugar: key
                tags_str_list.append(k)
            elif v == "?":
                # Explicit: key=?
                tags_str_list.append(f"{k}=?")
            elif v == "!":
                # Explicit: key=!
                tags_str_list.append(f"{k}=!")
            elif self._needs_quoting(v):
                tags_str_list.append(f"{k}={self._quote_value(v)}")
            else:
                tags_str_list.append(f"{k}={v}")

        return ";".join(tags_str_list)

    def to_string(self) -> str:
        """Get the canonical string representation of this tagged URN

        Uses the stored prefix
        Tags are already sorted alphabetically due to dict ordering
        No trailing semicolon in canonical form
        Values are quoted only when necessary (smart quoting)
        Special value serialization:
        - `*` (must-have-any): serialized as value-less tag (just the key)
        - `?` (unspecified): serialized as key=?
        - `!` (must-not-have): serialized as key=!
        """
        tags_str = self.tags_to_string()
        return f"{self.prefix}:{tags_str}"

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:
        return f"TaggedUrn('{self.to_string()}')"

    def get_prefix(self) -> str:
        """Get the prefix of this tagged URN"""
        return self.prefix

    def get_tag(self, key: str) -> Optional[str]:
        """Get a specific tag value

        Key is normalized to lowercase for lookup
        """
        return self.tags.get(key.lower())

    def has_tag(self, key: str, value: str) -> bool:
        """Check if this URN has a specific tag with a specific value

        Key is normalized to lowercase; value comparison is case-sensitive
        """
        return self.tags.get(key.lower()) == value

    def with_tag(self, key: str, value: str) -> 'TaggedUrn':
        """Add or update a tag

        Key is normalized to lowercase; value is preserved as-is
        Returns error if value is empty (use "*" for wildcard)
        """
        if not value:
            raise EmptyTagComponentError(f"empty value for key '{key}' (use '*' for wildcard)")

        new_tags = self.tags.copy()
        new_tags[key.lower()] = value
        return TaggedUrn(self.prefix, new_tags)

    def _with_tag_unchecked(self, key: str, value: str) -> 'TaggedUrn':
        """Add or update a tag (infallible version for internal use where value is known valid)"""
        new_tags = self.tags.copy()
        new_tags[key.lower()] = value
        return TaggedUrn(self.prefix, new_tags)

    def without_tag(self, key: str) -> 'TaggedUrn':
        """Remove a tag

        Key is normalized to lowercase for case-insensitive removal
        """
        new_tags = self.tags.copy()
        new_tags.pop(key.lower(), None)
        return TaggedUrn(self.prefix, new_tags)

    def conforms_to(self, pattern: 'TaggedUrn') -> bool:
        """Check if this URN (instance) satisfies the pattern's constraints.

        Equivalent to pattern.accepts(self).

        IMPORTANT: Both URNs must have the same prefix. Comparing URNs with
        different prefixes is a programming error and will raise an error.
        """
        return self._check_match(self.tags, self.prefix, pattern.tags, pattern.prefix)

    def accepts(self, instance: 'TaggedUrn') -> bool:
        """Check if this URN (pattern) accepts the given instance.

        Equivalent to instance.conforms_to(self).

        IMPORTANT: Both URNs must have the same prefix. Comparing URNs with
        different prefixes is a programming error and will raise an error.
        """
        return self._check_match(instance.tags, instance.prefix, self.tags, self.prefix)

    @staticmethod
    def _check_match(instance_tags: dict, instance_prefix: str,
                     pattern_tags: dict, pattern_prefix: str) -> bool:
        """Core matching: does instance satisfy pattern's constraints?"""
        if instance_prefix != pattern_prefix:
            raise PrefixMismatchError(instance_prefix, pattern_prefix)

        all_keys: Set[str] = set(instance_tags.keys()) | set(pattern_tags.keys())

        for key in all_keys:
            inst = instance_tags.get(key)
            patt = pattern_tags.get(key)

            if not TaggedUrn._values_match(inst, patt):
                return False

        return True

    @staticmethod
    def _values_match(inst: Optional[str], patt: Optional[str]) -> bool:
        """Check if instance value matches pattern constraint

        Full cross-product truth table:
        | Instance | Pattern | Match? | Reason |
        |----------|---------|--------|--------|
        | (none)   | (none)  | OK     | No constraint either side |
        | (none)   | K=?     | OK     | Pattern doesn't care |
        | (none)   | K=!     | OK     | Pattern wants absent, it is |
        | (none)   | K=*     | NO     | Pattern wants present |
        | (none)   | K=v     | NO     | Pattern wants exact value |
        | K=?      | (any)   | OK     | Instance doesn't care |
        | K=!      | (none)  | OK     | Symmetric: absent |
        | K=!      | K=?     | OK     | Pattern doesn't care |
        | K=!      | K=!     | OK     | Both want absent |
        | K=!      | K=*     | NO     | Conflict: absent vs present |
        | K=!      | K=v     | NO     | Conflict: absent vs value |
        | K=*      | (none)  | OK     | Pattern has no constraint |
        | K=*      | K=?     | OK     | Pattern doesn't care |
        | K=*      | K=!     | NO     | Conflict: present vs absent |
        | K=*      | K=*     | OK     | Both accept any presence |
        | K=*      | K=v     | OK     | Instance accepts any, v is fine |
        | K=v      | (none)  | OK     | Pattern has no constraint |
        | K=v      | K=?     | OK     | Pattern doesn't care |
        | K=v      | K=!     | NO     | Conflict: value vs absent |
        | K=v      | K=*     | OK     | Pattern wants any, v satisfies |
        | K=v      | K=v     | OK     | Exact match |
        | K=v      | K=w     | NO     | Value mismatch (v≠w) |
        """
        # Pattern has no constraint (no entry or explicit ?)
        if patt is None or patt == "?":
            return True

        # Instance doesn't care (explicit ?)
        if inst == "?":
            return True

        # Pattern: must-not-have (!)
        if patt == "!":
            if inst is None:
                return True  # Instance absent, pattern wants absent
            elif inst == "!":
                return True  # Both say absent
            else:
                return False  # Instance has value, pattern wants absent

        # Instance: must-not-have conflicts with pattern wanting value
        if inst == "!":
            if patt == "*":
                return False  # Conflict: absent vs present
            else:
                return False  # Conflict: absent vs value

        # Pattern: must-have-any (*)
        if patt == "*":
            if inst is None:
                return False  # Instance missing, pattern wants present
            else:
                return True  # Instance has value, pattern wants any

        # Pattern: exact value
        if inst is None:
            return False  # Instance missing, pattern wants value
        elif inst == "*":
            return True  # Instance accepts any, pattern's value is fine
        else:
            return inst == patt  # Both have values, must match exactly

    def conforms_to_str(self, pattern_str: str) -> bool:
        """Check if this URN (instance) satisfies a string pattern's constraints."""
        pattern = TaggedUrn.from_string(pattern_str)
        return self.conforms_to(pattern)

    def accepts_str(self, instance_str: str) -> bool:
        """Check if this URN (pattern) accepts a string instance."""
        instance = TaggedUrn.from_string(instance_str)
        return self.accepts(instance)

    def specificity(self) -> int:
        """Calculate specificity score for URN matching

        More specific URNs have higher scores and are preferred
        Graded scoring:
        - `K=v` (exact value): 3 points (most specific)
        - `K=*` (must-have-any): 2 points
        - `K=!` (must-not-have): 1 point
        - `K=?` (unspecified): 0 points (least specific)
        """
        score = 0
        for v in self.tags.values():
            if v == "?":
                score += 0
            elif v == "!":
                score += 1
            elif v == "*":
                score += 2
            else:
                score += 3  # exact value
        return score

    def specificity_tuple(self) -> Tuple[int, int, int]:
        """Get specificity as a tuple for tie-breaking

        Returns (exact_count, must_have_any_count, must_not_count)
        Compare tuples lexicographically when sum scores are equal
        """
        exact = 0
        must_have_any = 0
        must_not = 0

        for v in self.tags.values():
            if v == "?":
                pass
            elif v == "!":
                must_not += 1
            elif v == "*":
                must_have_any += 1
            else:
                exact += 1

        return (exact, must_have_any, must_not)

    def is_more_specific_than(self, other: 'TaggedUrn') -> bool:
        """Check if this URN is more specific than another"""
        # First check prefix
        if self.prefix != other.prefix:
            raise PrefixMismatchError(self.prefix, other.prefix)

        return self.specificity() > other.specificity()

    def is_equivalent(self, other: 'TaggedUrn') -> bool:
        """Check if two URNs are equivalent (identical tag sets).

        From order theory: in the specialization partial order defined by
        `accepts`/`conforms_to`, two elements are **equivalent** when each
        accepts the other (antisymmetry: a ≤ b ∧ b ≤ a → a = b).

        This is stricter than `is_comparable` — it requires the tag sets to
        be identical, not just related by specialization.

        ```
        a.is_equivalent(b)  ≡  a.accepts(b) && b.accepts(a)
        ```

        Raises `PrefixMismatchError` if prefixes differ (inherited from
        `accepts`/`conforms_to` — both sides return false on mismatch, but
        since we AND them, the error propagates).
        """
        return self.accepts(other) and other.accepts(self)

    def is_comparable(self, other: 'TaggedUrn') -> bool:
        """Check if two URNs are comparable (one is a specialization of the other).

        From order theory: in a partial order, two elements are **comparable**
        when one is ≤ the other. Elements that are NOT comparable are in
        different branches of the specialization lattice (e.g., `media:pdf;bytes`
        vs `media:txt;textable` — neither accepts the other).

        This is the weakest relation: it finds all URNs on the same
        generalization/specialization chain. Use it when you want to discover
        all handlers that *could* service a request, whether they are more
        general (fallback) or more specific (exact match).

        ```
        a.is_comparable(b)  ≡  a.accepts(b) || b.accepts(a)
        ```

        Raises `PrefixMismatchError` if prefixes differ (inherited from
        `accepts`/`conforms_to`).
        """
        return self.accepts(other) or other.accepts(self)

    def is_equivalent_str(self, other_str: str) -> bool:
        """String variant of `is_equivalent`."""
        other = TaggedUrn.from_string(other_str)
        return self.is_equivalent(other)

    def is_comparable_str(self, other_str: str) -> bool:
        """String variant of `is_comparable`."""
        other = TaggedUrn.from_string(other_str)
        return self.is_comparable(other)

    def with_wildcard_tag(self, key: str) -> 'TaggedUrn':
        """Create a wildcard version by replacing specific values with wildcards"""
        if key in self.tags:
            return self._with_tag_unchecked(key, "*")
        else:
            return self

    def subset(self, keys: List[str]) -> 'TaggedUrn':
        """Create a subset URN with only specified tags"""
        new_tags = {}
        for key in keys:
            if key in self.tags:
                new_tags[key] = self.tags[key]
        return TaggedUrn(self.prefix, new_tags)

    def merge(self, other: 'TaggedUrn') -> 'TaggedUrn':
        """Merge with another URN (other takes precedence for conflicts)

        Both must have the same prefix
        """
        if self.prefix != other.prefix:
            raise PrefixMismatchError(self.prefix, other.prefix)

        new_tags = self.tags.copy()
        new_tags.update(other.tags)
        return TaggedUrn(self.prefix, new_tags)

    @staticmethod
    def canonical(tagged_urn: str) -> str:
        """Get the canonical form of a tagged URN string"""
        urn = TaggedUrn.from_string(tagged_urn)
        return urn.to_string()

    @staticmethod
    def canonical_option(tagged_urn: Optional[str]) -> Optional[str]:
        """Get the canonical form of an optional tagged URN string"""
        if tagged_urn is not None:
            urn = TaggedUrn.from_string(tagged_urn)
            return urn.to_string()
        else:
            return None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TaggedUrn):
            return False
        return self.prefix == other.prefix and self.tags == other.tags

    def __hash__(self) -> int:
        return hash((self.prefix, tuple(sorted(self.tags.items()))))


class UrnMatcher:
    """URN matching and selection utilities"""

    @staticmethod
    def find_best_match(urns: List[TaggedUrn], request: TaggedUrn) -> Optional[TaggedUrn]:
        """Find the most specific URN that conforms to a request's constraints.

        URNs are instances (capabilities), request is the pattern (requirement).
        """
        best: Optional[TaggedUrn] = None
        best_specificity = 0

        for urn in urns:
            if urn.conforms_to(request):
                specificity = urn.specificity()
                if best is None or specificity > best_specificity:
                    best = urn
                    best_specificity = specificity

        return best

    @staticmethod
    def find_all_matches(urns: List[TaggedUrn], request: TaggedUrn) -> List[TaggedUrn]:
        """Find all URNs that conform to a request's constraints, sorted by specificity.

        URNs are instances (capabilities), request is the pattern (requirement).
        """
        results: List[TaggedUrn] = []

        for urn in urns:
            if urn.conforms_to(request):
                results.append(urn)

        # Sort by specificity (most specific first)
        results.sort(key=lambda urn: urn.specificity(), reverse=True)
        return results

    @staticmethod
    def are_compatible(urns1: List[TaggedUrn], urns2: List[TaggedUrn]) -> bool:
        """Check if two URN sets are compatible

        Two URNs are compatible if either accepts the other (bidirectional accepts).
        All URNs in both sets must have the same prefix.
        """
        for u1 in urns1:
            for u2 in urns2:
                if u1.accepts(u2) or u2.accepts(u1):
                    return True
        return False


class TaggedUrnBuilder:
    """Builder for creating tagged URNs fluently"""

    def __init__(self, prefix: str):
        """Create a new builder with a specified prefix (required)"""
        self.prefix = prefix.lower()
        self.tags: Dict[str, str] = {}

    def tag(self, key: str, value: str) -> 'TaggedUrnBuilder':
        """Add a tag with key (normalized to lowercase) and value (preserved as-is)

        Returns error if value is empty (use "*" for wildcard)
        """
        if not value:
            raise EmptyTagComponentError(f"empty value for key '{key}' (use '*' for wildcard)")
        self.tags[key.lower()] = value
        return self

    def solo_tag(self, key: str) -> 'TaggedUrnBuilder':
        """Add a tag with key (normalized to lowercase) and wildcard value"""
        self.tags[key.lower()] = "*"
        return self

    def build(self) -> TaggedUrn:
        """Build the tagged URN

        Raises error if no tags were added
        """
        if not self.tags:
            raise EmptyError("Tagged URN cannot be empty")
        return TaggedUrn(self.prefix, self.tags)

    def build_allow_empty(self) -> TaggedUrn:
        """Build allowing empty tags (creates an empty URN that matches everything)"""
        return TaggedUrn(self.prefix, self.tags)
