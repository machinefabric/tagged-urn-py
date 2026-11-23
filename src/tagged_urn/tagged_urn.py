"""Flat Tag-Based URN Identifier System

This module provides a flat, tag-based tagged URN system with configurable
prefixes, wildcard support, and specificity comparison.

What two URNs mean to each other — refinement, equivalence, comparability,
specificity, one key's match — is decided by code generated from the proved
model in ../formal (Lean) by lungo, in the module ``_formal``, not written here.
Each tag is stored as the constraint it writes, the model's own ``Constraint``:
``ConstraintWritten`` — whether the key may be absent, and the values it may
have, one of a set (``ValuesOneOf``) or none of a set (``ValuesNoneOf``) — or
``ConstraintMissing``, which is never stored.
"""

from enum import Enum
from types import MappingProxyType
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from . import _formal
from ._formal import (
    Constraint,
    ConstraintMissing,
    ConstraintWritten,
    Values,
    ValuesNoneOf,
    ValuesOneOf,
)


def unconstrained() -> Constraint:
    """``?k``: any state, absent or any value."""
    return none_of([], True)


def optional_not(value: str) -> Constraint:
    """``k?=v``: absent, or there and not ``v``."""
    return none_of([value], True)


def present() -> Constraint:
    """``k``: there, with any value."""
    return none_of([], False)


def present_not(value: str) -> Constraint:
    """``k!=v``: there, and not ``v``."""
    return none_of([value], False)


def exact(value: str) -> Constraint:
    """``k=v``: there, and exactly ``v``."""
    return one_of([value], False)


def absent() -> Constraint:
    """``!k``: not there."""
    return one_of([], True)


def one_of(values: Iterable[str], or_absent: bool) -> Constraint:
    """``k=a|b``: there, with one of the values; ``k=a|b|!`` when
    ``or_absent``. The values are kept canonical: each once, in increasing
    order."""
    return ConstraintWritten(or_absent, ValuesOneOf(_canonical_values(values)))


def none_of(values: Iterable[str], or_absent: bool) -> Constraint:
    """``k!=a|b``: there, with none of the values; ``k?=a|b`` when
    ``or_absent``. The values are kept canonical: each once, in increasing
    order."""
    return ConstraintWritten(or_absent, ValuesNoneOf(_canonical_values(values)))


def canonical_constraint(constraint: Constraint) -> Constraint:
    """The same constraint with its values canonical, in a list of its own.
    Two constraints that say the same thing are equal once canonical."""
    if isinstance(constraint, ConstraintMissing):
        return ConstraintMissing()
    if isinstance(constraint, ConstraintWritten):
        if isinstance(constraint.values, ValuesOneOf):
            return one_of(constraint.values.vs, constraint.absent)
        if isinstance(constraint.values, ValuesNoneOf):
            return none_of(constraint.values.vs, constraint.absent)
    raise AssertionError(f"tagged-urn: {constraint!r} is not a constraint")


def exact_value(constraint: Optional[Constraint]) -> Optional[str]:
    """The value of ``k=v``, when the constraint is that form."""
    if isinstance(constraint, ConstraintWritten) and not constraint.absent \
            and isinstance(constraint.values, ValuesOneOf) and len(constraint.values.vs) == 1:
        return constraint.values.vs[0]
    return None


def is_empty_form(constraint: Constraint) -> bool:
    """Whether the constraint allows no state at all. No text writes it."""
    return isinstance(constraint, ConstraintWritten) and not constraint.absent \
        and isinstance(constraint.values, ValuesOneOf) and not constraint.values.vs


def _canonical_values(values: Iterable[str]) -> List[str]:
    """Values each once, in increasing order: the order Lean's ``String <``
    uses (Python orders strings by code point)."""
    return sorted(set(values))


# Error classes
class TaggedUrnError(Exception):
    """Base exception for tagged URN errors"""
    pass


class TaggedUrnRelationKind(Enum):
    EQUIVALENT = "equivalent"
    COMPARABLE = "comparable"
    INCOMPARABLE = "incomparable"


class TaggedUrnCoordinateDelta:
    """Coordinate-space edit from one tagged URN to another with the same prefix."""

    def __init__(
        self,
        prefix: str,
        removed: Optional[Dict[str, Constraint]] = None,
        added: Optional[Dict[str, Constraint]] = None,
        relation_kind: TaggedUrnRelationKind = TaggedUrnRelationKind.EQUIVALENT,
    ):
        self.prefix = prefix
        self.removed = dict(removed or {})
        self.added = dict(added or {})
        self.relation_kind = relation_kind

    def is_empty(self) -> bool:
        return not self.removed and not self.added


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
    """Disallowed character in prefix, key or value"""
    pass


class DuplicateKeyError(TaggedUrnError):
    """Same key appears twice"""
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


class DuplicateValueError(TaggedUrnError):
    """A value given twice in one tag's set of values"""
    pass


class ParseState(Enum):
    """Parser states for the state machine.

    The parser reads the six tag forms — the canonical alphabet of the
    constraint truth table — into the constraint each writes:

    +------------------------------+-----------+-------------------+-------+-------------------------------+
    | Authored                     | Canonical | Constraint        | Score | Reading                       |
    +==============================+===========+===================+=======+===============================+
    | ``?x`` ≡ ``x?`` ≡ ``x=?``    | ``?x``    | unconstrained     | 0     | no constraint                 |
    | ``?x=v`` ≡ ``x?=v`` ≡ ``x=?v``| ``x?=v`` | optionalNot v     | 1     | absent OR (present and not v) |
    | ``x`` ≡ ``x=*``              | ``x``     | present           | 2     | present with any value        |
    | ``!x=v`` ≡ ``x!=v`` ≡ ``x=!v``| ``x!=v`` | presentNot v      | 3     | present and not v             |
    | ``x=v``                      | ``x=v``   | exact v           | 4     | present and exactly v         |
    | ``!x`` ≡ ``x!`` ≡ ``x=!``    | ``!x``    | absent            | 5     | absent (must-not-have)        |
    +------------------------------+-----------+-------------------+-------+-------------------------------+

    A quoted value is literal: ``x="?v"`` is the exact value ``?v``, and
    ``x="*"`` the exact value ``*``, never the marker.

    A value may be a set of values separated by ``|``
    (:func:`_canonicalize_set`): ``x=a|b``, ``x!=a|b``, ``x?=a|b``, and
    ``x=a|b|!`` (absent, or one of them).

    Disallowed (hard parse errors): ``?x?``, ``?x?=v``, ``!x!=v``, ``?!x``,
    ``!?x``, ``?x=?v``, ``?x=*``, ``!x=*``, ``x=?*``, ``x=!?``, and an
    empty value.
    """
    EXPECTING_KEY = 1
    AFTER_PREFIX_QUESTION = 2
    AFTER_PREFIX_BANG = 3
    IN_KEY = 4
    IN_KEY_AFTER_QUESTION = 5
    IN_KEY_AFTER_BANG = 6
    EXPECTING_VALUE = 7
    IN_UNQUOTED_VALUE = 8
    IN_QUOTED_VALUE = 9
    IN_QUOTED_VALUE_ESCAPE = 10
    EXPECTING_SEMI_OR_END = 11
    #: After ``|`` in a value: the next member of a set of values.
    EXPECTING_VALUE_MEMBER = 12


def _is_identifier_start(c: str) -> bool:
    """Whether ``c`` may begin a prefix or a key: an ASCII letter."""
    return ('a' <= c <= 'z') or ('A' <= c <= 'Z')


def _is_valid_key_char(c: str) -> bool:
    """Whether ``c`` may stand in a prefix or key after its first character."""
    return _is_identifier_start(c) or ('0' <= c <= '9') or c == '-'


def _identifier(what: str, s: str) -> str:
    """``s`` as an identifier — an ASCII letter, then ASCII letters, digits and
    ``-`` — lowered; ``what`` names it in the error ("prefix", "key")."""
    if not s:
        if what == "prefix":
            raise EmptyPrefixError("Tagged URN prefix cannot be empty")
        raise EmptyTagComponentError(f"empty {what}")
    for pos, c in enumerate(s):
        allowed = _is_identifier_start(c) if pos == 0 else _is_valid_key_char(c)
        if not allowed:
            raise InvalidCharacterError(f"invalid character '{c}' in {what} at position {pos}")
    return s.lower()


def _check_constraint(key: str, constraint: Constraint) -> None:
    """Refuse a constraint a URN cannot write for ``key``: anything but a
    ``ConstraintWritten`` whose values are a ``ValuesOneOf`` or ``ValuesNoneOf``
    of strings, ``ConstraintMissing`` (a key with no constraint is omitted), the
    empty form (no state at all, which no text writes), or an empty value."""
    if not isinstance(constraint, ConstraintWritten):
        raise InvalidTagFormatError(
            f"key '{key}' given {constraint!r}: a tag's value is a written constraint, and a "
            f"key with no constraint is omitted")
    values = constraint.values
    if not isinstance(constraint.absent, bool) \
            or not isinstance(values, (ValuesOneOf, ValuesNoneOf)) \
            or not isinstance(values.vs, (list, tuple)) \
            or not all(isinstance(v, str) for v in values.vs):
        raise InvalidTagFormatError(
            f"key '{key}' given {constraint!r}: a written constraint is whether the key may be "
            f"absent and a ValuesOneOf or ValuesNoneOf of strings")
    if is_empty_form(constraint):
        raise InvalidTagFormatError(
            f"key '{key}' given a constraint no state satisfies: no text writes it")
    if any(not v for v in values.vs):
        raise EmptyTagComponentError(f"empty value for key '{key}'")


def _is_valid_unquoted_value_char(c: str) -> bool:
    r"""Whether ``c`` may stand in an unquoted value: anything but the separators
    ``;`` ``=`` ``|``, the quoting characters ``"`` ``\``, and whitespace."""
    return c not in ';=|"\\' and not c.isspace()


def _ascii_lower(c: str) -> str:
    """An ASCII letter lowered, any other character as it is: unquoted values are
    lowered so."""
    return c.lower() if 'A' <= c <= 'Z' else c


def _needs_quoting(value: str) -> bool:
    """Whether a value must be quoted to read back as itself: it holds a
    character a bare value cannot, an uppercase letter (a bare value is
    lowered), or begins with ``*``, ``?`` or ``!`` (which a bare value reads as
    a sigil or a qualifier)."""
    return any(not _is_valid_unquoted_value_char(c) or c.isupper() for c in value) \
        or value.startswith(('*', '?', '!'))


def _quote_value(value: str) -> str:
    """Quote a value for serialization"""
    result = '"'
    for c in value:
        if c in ('"', '\\'):
            result += '\\'
        result += c
    result += '"'
    return result


def _write_value(value: str) -> str:
    """A value as it is written: bare, or quoted when it must be."""
    return _quote_value(value) if _needs_quoting(value) else value


def _qualified(qualifier: Optional[str], value: str) -> Constraint:
    """The constraint a value writes under a qualifier (or none)."""
    if qualifier is None:
        return exact(value)
    if qualifier == '?':
        return optional_not(value)
    if qualifier == '!':
        return present_not(value)
    raise AssertionError(f"invalid qualifier {qualifier!r}")


def _refuse_sigil_under_qualifier(qualifier: str, key: str, value: str) -> None:
    """A qualifier and a sigil (``*``, ``?``, ``!``) make incompatible claims."""
    if value in ("*", "?", "!"):
        raise InvalidCharacterError(
            f"qualifier '{qualifier}' on key '{key}' cannot combine with sigil "
            f"value '{value}': use a real value or drop the qualifier"
        )


def _canonical_no_value(qualifier: Optional[str]) -> Constraint:
    """The constraint of a value-less tag, given its qualifier."""
    if qualifier is None:
        return present()
    if qualifier == '?':
        return unconstrained()
    if qualifier == '!':
        return absent()
    raise AssertionError(f"invalid qualifier {qualifier!r}")


def _finish_value(qualifier: Optional[str], key: str, members: List[Tuple[str, bool]],
                  last: Tuple[str, bool]) -> Constraint:
    """The constraint a parsed value writes: a single value as
    :func:`_canonicalize_value` reads it, or a set of values (``members`` read
    before the last ``|``, then ``last``, each with whether it was quoted) as
    :func:`_canonicalize_set` does."""
    if not members:
        value, quoted = last
        return _canonicalize_value(qualifier, quoted, key, value)
    return _canonicalize_set(qualifier, key, members + [last])


def _canonicalize_set(qualifier: Optional[str], key: str, members: List[Tuple[str, bool]]) -> Constraint:
    """The constraint a set of values writes:

    ============  ==========  =====================  ===============
    qualifier     members     constraint             written
    ============  ==========  =====================  ===============
    None          ``a|b``     one of a, b            ``k=a|b``
    None          ``a|b|!``   absent, or one of      ``k=a|b|!``
    ``!``         ``a|b``     there, none of         ``k!=a|b``
    ``?``         ``a|b``     absent, or none of     ``k?=a|b``
    ============  ==========  =====================  ===============

    A bare ``!`` member says "or absent", and only in ``k=``. Every other
    member is a value: a quoted one is literal, and a bare ``*``, ``?``, ``!``
    under a qualifier, or a bare member beginning with ``?`` or ``!``, is
    refused — quote it to mean the value itself. A value given twice is
    refused.
    """
    values: List[str] = []
    or_absent = False
    for member, quoted in members:
        if not member:
            raise EmptyTagComponentError(f"empty value in the set of values for key '{key}'")
        if not quoted and member == "!" and qualifier is None:
            if or_absent:
                raise DuplicateValueError(f"'!' given twice in the set of values for key '{key}'")
            or_absent = True
            continue
        if not quoted and (member == "*" or member.startswith(("?", "!"))):
            raise InvalidCharacterError(
                f"'{member}' cannot stand in the set of values for key '{key}': quote it to mean "
                f"the value itself"
            )
        if member in values:
            raise DuplicateValueError(f"value '{member}' given twice in the set of values for key '{key}'")
        values.append(member)
    if not values:
        raise EmptyTagComponentError(f"the set of values for key '{key}' names no value")
    if qualifier is None:
        return one_of(values, or_absent)
    if qualifier == '?':
        return none_of(values, True)
    if qualifier == '!':
        return none_of(values, False)
    raise AssertionError(f"invalid qualifier {qualifier!r}")


def _canonicalize_value(qualifier: Optional[str], quoted: bool, key: str, value: str) -> Constraint:
    """The constraint a parsed (qualifier, value) pair writes.

    A quoted value is literal: exact, or optionalNot/presentNot under a
    qualifier. An unquoted ``*``, ``?`` or ``!`` is a sigil; an unquoted value
    that begins with ``?`` or ``!`` is that qualifier (``x=?v`` ≡ ``x?=v``). A
    qualifier on an unquoted sigil, or a second qualifier, is refused.
    """
    if not value:
        raise EmptyTagComponentError(f"empty value for key '{key}'")
    if quoted:
        return _qualified(qualifier, value)
    if qualifier is None:
        if value == "*":
            return present()
        if value == "?":
            return unconstrained()
        if value == "!":
            return absent()
        if value[0] in "?!":
            rest = value[1:]
            _refuse_sigil_under_qualifier(value[0], key, rest)
            return _qualified(value[0], rest)
        return exact(value)
    if len(value) > 1 and value[0] in "?!":
        raise InvalidCharacterError(
            f"qualifier '{qualifier}' on key '{key}' cannot combine with a second qualifier "
            f"in value '{value}': quote the value to make it literal"
        )
    _refuse_sigil_under_qualifier(qualifier, key, value)
    return _qualified(qualifier, value)


class TaggedUrn:
    """A tagged URN using flat, ordered tags with a configurable prefix

    Examples:
    - `cap:generate;ext=pdf;output=binary;target=thumbnail`
    - `myapp:key="Value With Spaces"`
    - `custom:a=1;b=2`
    """

    def __init__(self, prefix: str, tags: Dict[str, Constraint]):
        """Create a tagged URN from a prefix and its tags.

        The prefix and every key must be identifiers (an ASCII letter, then
        ASCII letters, digits and ``-``) and are lowered; every constraint
        must be one a URN can write (not ``ConstraintMissing``, not the empty
        form, no empty value), and is kept canonical: its values each once, in
        increasing order, in a list of its own.
        """
        self._prefix = _identifier("prefix", prefix)
        normalized: Dict[str, Constraint] = {}
        for k, v in tags.items():
            key = _identifier("key", k)
            _check_constraint(key, v)
            if key in normalized:
                raise DuplicateKeyError(f"Duplicate tag key: {key}")
            normalized[key] = canonical_constraint(v)
        self._tags = normalized
        # The same URN on the proved model's side: its tags with the proof that
        # their keys are strictly increasing. Every semantic question is asked
        # of it. Made here from the same tags as the fields, which are read-only
        # from here on, so the two cannot describe different URNs. Python orders
        # strings by code point, as Lean's String < does, so the model refusing
        # the sorted keys is a broken invariant.
        keys = sorted(self._tags)
        formal = _formal.make(self._prefix, [(k, self._tags[k]) for k in keys])
        if formal is None:
            raise RuntimeError(f"tagged-urn: the model refused {self._prefix}:{keys}, whose keys are sorted")
        self._formal = formal

    @property
    def prefix(self) -> str:
        """The prefix (``media``, ``cap``, …)."""
        return self._prefix

    @property
    def tags(self) -> Mapping[str, Constraint]:
        """The tags, each as the constraint it writes, read-only."""
        return MappingProxyType(self._tags)

    @property
    def formal(self) -> _formal.Wf:
        """This URN on the proved model's side. A module generated from a model that
        builds on tagged-urn's names this type for the model's URNs, so it passes to
        that module's functions as it is."""
        return self._formal

    @classmethod
    def from_formal(cls, formal: _formal.Wf) -> 'TaggedUrn':
        """The URN a model handle stands for, such as one a module generated from
        a model that builds on tagged-urn's made. Its prefix, keys and
        constraints are checked as the constructor checks them
        (``TaggedUrn.Exec.parts``)."""
        prefix, tags = _formal.parts(formal)
        return cls(prefix, dict(tags))

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

        prefix = _identifier("prefix", s[:colon_pos])
        tags_part = s[colon_pos + 1:]
        tags: Dict[str, Constraint] = {}

        # Handle empty tagged URN (prefix: with no tags)
        if not tags_part or tags_part == ";":
            return cls(prefix, tags)

        state = ParseState.EXPECTING_KEY
        current_key = ""
        current_value = ""
        # qualifier: None | '?' | '!' — tracked across the tag,
        # reset on each finish_tag.
        qualifier: Optional[str] = None
        # The members of a set of values read so far (``k=a|b``), each with
        # whether it was quoted; empty while the value is a single one.
        members: List[Tuple[str, bool]] = []
        chars = list(tags_part)
        pos = 0

        def finish(constraint: Constraint) -> None:
            if current_key in tags:
                raise DuplicateKeyError(f"Duplicate tag key: {current_key}")
            tags[current_key] = constraint

        while pos < len(chars):
            c = chars[pos]

            if state == ParseState.EXPECTING_KEY:
                if c == ';':
                    pos += 1
                    continue
                elif c == '?':
                    qualifier = '?'
                    state = ParseState.AFTER_PREFIX_QUESTION
                elif c == '!':
                    qualifier = '!'
                    state = ParseState.AFTER_PREFIX_BANG
                elif _is_identifier_start(c):
                    current_key += c.lower()
                    state = ParseState.IN_KEY
                else:
                    raise InvalidCharacterError(f"invalid character '{c}' at position {pos}")

            elif state in (ParseState.AFTER_PREFIX_QUESTION, ParseState.AFTER_PREFIX_BANG):
                if _is_identifier_start(c):
                    current_key += c.lower()
                    state = ParseState.IN_KEY
                else:
                    raise InvalidCharacterError(
                        f"expected key character after '{qualifier}' qualifier, got '{c}' at position {pos}"
                    )

            elif state == ParseState.IN_KEY:
                if c == '=':
                    state = ParseState.EXPECTING_VALUE
                elif c == '?':
                    if qualifier is not None:
                        raise InvalidCharacterError(
                            f"duplicate qualifier '?' at position {pos}: prefix and infix "
                            f"qualifiers cannot be combined on key '{current_key}'"
                        )
                    qualifier = '?'
                    state = ParseState.IN_KEY_AFTER_QUESTION
                elif c == '!':
                    if qualifier is not None:
                        raise InvalidCharacterError(
                            f"duplicate qualifier '!' at position {pos}: prefix and infix "
                            f"qualifiers cannot be combined on key '{current_key}'"
                        )
                    qualifier = '!'
                    state = ParseState.IN_KEY_AFTER_BANG
                elif c == ';':
                    finish(_canonical_no_value(qualifier))
                    current_key = ""
                    current_value = ""
                    qualifier = None
                    state = ParseState.EXPECTING_KEY
                elif _is_valid_key_char(c):
                    current_key += c.lower()
                else:
                    raise InvalidCharacterError(f"invalid character '{c}' in key at position {pos}")

            elif state in (ParseState.IN_KEY_AFTER_QUESTION, ParseState.IN_KEY_AFTER_BANG):
                if c == '=':
                    state = ParseState.EXPECTING_VALUE
                elif c == ';':
                    finish(_canonical_no_value(qualifier))
                    current_key = ""
                    current_value = ""
                    qualifier = None
                    state = ParseState.EXPECTING_KEY
                else:
                    raise InvalidCharacterError(
                        f"expected '=' or ';' after '{current_key}{qualifier}' suffix qualifier, "
                        f"got '{c}' at position {pos}"
                    )

            elif state in (ParseState.EXPECTING_VALUE, ParseState.EXPECTING_VALUE_MEMBER):
                if c == '"':
                    state = ParseState.IN_QUOTED_VALUE
                elif c == ';':
                    raise EmptyTagComponentError(f"empty value for key '{current_key}'")
                elif _is_valid_unquoted_value_char(c):
                    current_value += _ascii_lower(c)
                    state = ParseState.IN_UNQUOTED_VALUE
                else:
                    raise InvalidCharacterError(f"invalid character '{c}' in value at position {pos}")

            elif state == ParseState.IN_UNQUOTED_VALUE:
                if c == ';':
                    finish(_finish_value(qualifier, current_key, members, (current_value, False)))
                    current_key = ""
                    current_value = ""
                    qualifier = None
                    members = []
                    state = ParseState.EXPECTING_KEY
                elif c == '|':
                    members.append((current_value, False))
                    current_value = ""
                    state = ParseState.EXPECTING_VALUE_MEMBER
                elif _is_valid_unquoted_value_char(c):
                    current_value += _ascii_lower(c)
                else:
                    raise InvalidCharacterError(f"invalid character '{c}' in unquoted value at position {pos}")

            elif state == ParseState.IN_QUOTED_VALUE:
                if c == '"':
                    state = ParseState.EXPECTING_SEMI_OR_END
                elif c == '\\':
                    state = ParseState.IN_QUOTED_VALUE_ESCAPE
                else:
                    current_value += c

            elif state == ParseState.IN_QUOTED_VALUE_ESCAPE:
                if c == '"' or c == '\\':
                    current_value += c
                    state = ParseState.IN_QUOTED_VALUE
                else:
                    raise InvalidEscapeSequenceError(
                        f"Invalid escape sequence at position {pos} (only \\\" and \\\\ allowed)"
                    )

            elif state == ParseState.EXPECTING_SEMI_OR_END:
                if c == ';':
                    finish(_finish_value(qualifier, current_key, members, (current_value, True)))
                    current_key = ""
                    current_value = ""
                    qualifier = None
                    members = []
                    state = ParseState.EXPECTING_KEY
                elif c == '|':
                    members.append((current_value, True))
                    current_value = ""
                    state = ParseState.EXPECTING_VALUE_MEMBER
                else:
                    raise InvalidCharacterError(
                        f"expected ';', '|' or end after quoted value, got '{c}' at position {pos}"
                    )

            pos += 1

        # Handle end of input
        if state == ParseState.IN_UNQUOTED_VALUE:
            finish(_finish_value(qualifier, current_key, members, (current_value, False)))
        elif state == ParseState.EXPECTING_SEMI_OR_END:
            finish(_finish_value(qualifier, current_key, members, (current_value, True)))
        elif state == ParseState.EXPECTING_KEY:
            pass
        elif state in (ParseState.IN_QUOTED_VALUE, ParseState.IN_QUOTED_VALUE_ESCAPE):
            raise UnterminatedQuoteError(f"Unterminated quote at position {pos}")
        elif state in (ParseState.AFTER_PREFIX_QUESTION, ParseState.AFTER_PREFIX_BANG):
            raise EmptyTagComponentError(
                f"qualifier '{qualifier}' at end of input has no key"
            )
        elif state in (ParseState.IN_KEY, ParseState.IN_KEY_AFTER_QUESTION, ParseState.IN_KEY_AFTER_BANG):
            finish(_canonical_no_value(qualifier))
        elif state in (ParseState.EXPECTING_VALUE, ParseState.EXPECTING_VALUE_MEMBER):
            raise EmptyTagComponentError(f"empty value for key '{current_key}'")

        return cls(prefix, tags)

    def tags_to_string(self) -> str:
        """Serialize just the tags portion (without prefix): the tags in key
        order, each in its canonical form, joined by ``;``.

        +--------------------------------+--------------+
        | What the key allows            | Emitted      |
        +================================+==============+
        | there, any value               | ``k``        |
        | any state                      | ``?k``       |
        | absent                         | ``!k``       |
        | absent, or none of a, b        | ``k?=a|b``   |
        | there, none of a, b            | ``k!=a|b``   |
        | there, one of a, b             | ``k=a|b``    |
        | absent, or one of a, b         | ``k=a|b|!``  |
        +--------------------------------+--------------+

        A set's values each once, in increasing order. A value is quoted only
        when it must be to read back as itself: exact ``*`` prints ``k="*"``.
        The prefix forms (``?k``, ``!k``) and infix forms (``k?=v``,
        ``k!=v``) are the canonical outputs whichever alias the input used.
        """
        parts = []
        for k, c in sorted(self._tags.items(), key=lambda item: item[0]):
            vs = c.values.vs
            written = "|".join(_write_value(v) for v in vs)
            one = isinstance(c.values, ValuesOneOf)
            if not c.absent and not one and not vs:
                parts.append(k)
            elif c.absent and not one and not vs:
                parts.append(f"?{k}")
            elif c.absent and one and not vs:
                parts.append(f"!{k}")
            elif c.absent and not one:
                parts.append(f"{k}?={written}")
            elif not c.absent and not one:
                parts.append(f"{k}!={written}")
            elif not c.absent:
                parts.append(f"{k}={written}")
            else:
                parts.append(f"{k}={written}|!")
        return ";".join(parts)

    def to_string(self) -> str:
        """Get the canonical string representation of this tagged URN."""
        tags_str = self.tags_to_string()
        return f"{self.prefix}:{tags_str}"

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:
        return f"TaggedUrn('{self.to_string()}')"

    def get_prefix(self) -> str:
        """Get the prefix of this tagged URN"""
        return self.prefix

    def get_tag(self, key: str) -> Optional[Constraint]:
        """The constraint the URN writes for ``key``, or None when it does not
        mention it. Key is normalized to lowercase for lookup."""
        return self._tags.get(key.lower())

    def constraint(self, key: str) -> Constraint:
        """The constraint the URN writes for ``key``, ``ConstraintMissing`` when
        it does not mention it: the model's form of the key."""
        return self._tags.get(key.lower(), ConstraintMissing())

    def has_tag(self, key: str, value: str) -> bool:
        """Whether this URN writes the exact value ``value`` for ``key``
        (``key=value``). Key is normalized to lowercase; value comparison is
        case-sensitive."""
        return exact_value(self._tags.get(key.lower())) == value

    def has_marker_tag(self, tag_name: str) -> bool:
        """Whether ``tag_name`` is present as a marker (there with any value,
        written as just the key). Example: ``cap:constrained;...`` has marker
        tag "constrained"."""
        return self._tags.get(tag_name.lower()) == present()

    def admits_absence(self, key: str) -> bool:
        """Whether what this URN writes at ``key`` lets the key be absent.

        ``!key``, ``?key``, ``key?=v`` and ``key=v|!`` do, and so does a key the
        URN does not mention, which says nothing of it; ``key``, ``key=v`` and
        ``key!=v`` do not. Decided by the model: absence satisfies the
        constraint (``values_match``).
        """
        return _formal.values_match(absent(), self.constraint(key))

    def with_tag(self, key: str, constraint: Constraint) -> 'TaggedUrn':
        """Add or replace a tag. The key must be an identifier and is lowered;
        the constraint must be one a URN can write."""
        key = _identifier("key", key)
        _check_constraint(key, constraint)
        new_tags = dict(self._tags)
        new_tags[key] = constraint
        return TaggedUrn(self.prefix, new_tags)

    def without_tag(self, key: str) -> 'TaggedUrn':
        """Remove a tag

        Key is normalized to lowercase for case-insensitive removal
        """
        new_tags = dict(self._tags)
        new_tags.pop(key.lower(), None)
        return TaggedUrn(self.prefix, new_tags)

    def conforms_to(self, pattern: 'TaggedUrn') -> bool:
        """Check if this URN (instance) satisfies the pattern's constraints.

        Equivalent to pattern.accepts(self).

        IMPORTANT: Both URNs must have the same prefix. Comparing URNs with
        different prefixes is a programming error and will raise an error.
        """
        return self._check_match(self, pattern)

    def accepts(self, instance: 'TaggedUrn') -> bool:
        """Check if this URN (pattern) accepts the given instance.

        Equivalent to instance.conforms_to(self).

        IMPORTANT: Both URNs must have the same prefix. Comparing URNs with
        different prefixes is a programming error and will raise an error.
        """
        return self._check_match(instance, self)

    @staticmethod
    def _check_match(instance: 'TaggedUrn', pattern: 'TaggedUrn') -> bool:
        """Core matching: does instance satisfy pattern's constraints?

        Decided by the model (``refines``, proved to be refinement); only the
        prefix check is here, because comparing across prefixes is a caller's
        error and says so.
        """
        TaggedUrn._same_prefix(instance, pattern)
        return _formal.refines(instance._formal, pattern._formal)

    def meets(self, other: 'TaggedUrn') -> bool:
        """Whether this URN and ``other`` COULD be about the same thing: some
        thing is described by both. Symmetric — neither is the instance.

        ``conforms_to`` is a guarantee: everything this URN describes, the
        pattern describes. This is the other question the same meanings answer,
        and the one a search asks: ``media:ext`` (some ext) does not conform to
        ``media:document;ext=pdf``, and is not excluded by it either — it meets it.
        Whatever conforms meets; what meets need not conform, and meeting is
        not transitive (a pdf meets "some ext", which meets a png).

        Decided by the model (``TaggedUrn.Exec.meets``).
        """
        TaggedUrn._same_prefix(self, other)
        return _formal.meets(self._formal, other._formal)

    def satisfies(self, pattern: 'TaggedUrn') -> bool:
        """Whether this URN, read as a COMPLETE thing, satisfies ``pattern``.

        A description that omits a key says nothing about it, which is how
        ``conforms_to`` reads both sides. A thing that exists — a value with
        these tags, a cap's own list of tags — omits a key because it does not
        have it. Read so, a thing that does not mention ``x`` satisfies ``!x``.

        Use this where the left side is what something IS; use ``conforms_to``
        where it is what something is declared to take or give. Decided by the
        model (``TaggedUrn.Exec.refinesClosed``).
        """
        TaggedUrn._same_prefix(self, pattern)
        return _formal.refines_closed(self._formal, pattern._formal)

    def may_satisfy(self, pattern: 'TaggedUrn') -> bool:
        """Whether this URN, read as a complete thing, COULD satisfy
        ``pattern``: ``satisfies`` is to this as ``conforms_to`` is to
        ``meets``."""
        TaggedUrn._same_prefix(self, pattern)
        return _formal.meets_closed(self._formal, pattern._formal)

    @classmethod
    def least_upper_bound(cls, prefix: str, urns: List['TaggedUrn']) -> 'TaggedUrn':
        """The most specific URN every one of ``urns`` conforms to: their common
        denominator.

        Key by key, the bound allows every state some input allows, and no
        other: a form holds any set of values, so ``ext=png`` and ``ext=jpeg``
        are bound by ``ext=jpeg|png``, not by ``ext`` (some value); ``ext=png``
        and ``!ext`` by ``ext=png|!``. A key whose bound allows every state is
        left out. When one input holds all the others, the bound is that input.
        The bound of no URNs is the URN with no tags.

        Made by the model (``TaggedUrn.Exec.leastUpperBound``), whose theorems
        say every input conforms to the bound and the bound conforms to every
        such bound of them, and no tag of it is ``ConstraintMissing``. The
        prefix must be an identifier, and every URN must have it; another
        raises ``PrefixMismatchError``.
        """
        prefix = _identifier("prefix", prefix)
        tags = _formal.least_upper_bound(prefix, [u._formal for u in urns])
        if tags is None:
            other = next((u for u in urns if u.prefix != prefix), None)
            if other is None:
                raise RuntimeError(
                    f"tagged-urn: the model made no bound of URNs that all have the prefix {prefix}")
            raise PrefixMismatchError(prefix, other.prefix)
        return cls(prefix, dict(tags))

    @staticmethod
    def _same_prefix(a: 'TaggedUrn', b: 'TaggedUrn') -> None:
        if a.prefix != b.prefix:
            raise PrefixMismatchError(a.prefix, b.prefix)

    @staticmethod
    def _values_match(inst: Constraint, patt: Constraint) -> bool:
        """Whether an instance's constraint satisfies a pattern's at one key
        (``ConstraintMissing`` for a key the URN omits, as :meth:`constraint`
        gives it), as the model decides it.

        Every form has ONE meaning — the set of states the key may be in — and
        the instance satisfies the pattern when every state it allows, the
        pattern allows too (``tagMatch_iff_allows`` in ``formal/``).
        """
        return _formal.values_match(inst, patt)

    @staticmethod
    def _values_meet(a: Constraint, b: Constraint) -> bool:
        """Whether two constraints allow a common state at one key."""
        return _formal.values_meet(a, b)

    @staticmethod
    def _values_match_closed(inst: Constraint, patt: Constraint) -> bool:
        """One key of a complete thing against a pattern: an omitted key is
        absent."""
        return _formal.values_match_closed(inst, patt)

    def conforms_to_str(self, pattern_str: str) -> bool:
        """Check if this URN (instance) satisfies a string pattern's constraints."""
        pattern = TaggedUrn.from_string(pattern_str)
        return self.conforms_to(pattern)

    def accepts_str(self, instance_str: str) -> bool:
        """Check if this URN (pattern) accepts a string instance."""
        instance = TaggedUrn.from_string(instance_str)
        return self.accepts(instance)

    def specificity(self) -> int:
        """Calculate specificity score for URN matching, as the model computes it
        (``TaggedUrn.Exec.specificity``).

        The sum of per-tag scores, each by what the tag allows:

        ============================================  ====================  =====
        What the key allows                           e.g.                  Score
        ============================================  ====================  =====
        absence and every value                       ``?x``                0
        absence and some values, not every value      ``x?=v``, ``x=v|!``   1
        every value                                   ``x``                 2
        two or more values, not every value           ``x!=v``, ``x=a|b``   3
        exactly one value                             ``x=v``               4
        only absence                                  ``!x``                5
        ============================================  ====================  =====

        Higher scores indicate more constrained (more specific) tags; a tag
        that is narrower never scores lower. Identity (``prefix:`` with no
        tags) scores 0.
        """
        return _formal.specificity(self._formal)

    def specificity_tuple(self) -> Tuple[int, int, int, int, int]:
        """How many tags score 5, 4, 3, 2 and 1
        (``TaggedUrn.Exec.tagSpecificity``): ``(absent, exact, present_not,
        present, optional_not)``, named by the written form of each score."""
        counts = [0] * 6
        for c in self._tags.values():
            counts[_formal.tag_specificity(c)] += 1
        return (counts[5], counts[4], counts[3], counts[2], counts[1])

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

        Decided by the model (``equivalent``, proved equal to it). Raises
        `PrefixMismatchError` if prefixes differ.
        """
        TaggedUrn._same_prefix(self, other)
        return _formal.equivalent(self._formal, other._formal)

    def is_comparable(self, other: 'TaggedUrn') -> bool:
        """Check if two URNs are comparable (one is a specialization of the other).

        From order theory: in a partial order, two elements are **comparable**
        when one is ≤ the other. Elements that are NOT comparable are in
        different branches of the specialization lattice (e.g., `media:pdf;bytes`
        vs `media:enc=utf-8;txt` — neither accepts the other).

        This is the weakest relation: it finds all URNs on the same
        generalization/specialization chain. Use it when you want to discover
        all handlers that *could* service a request, whether they are more
        general (fallback) or more specific (exact match).

        ```
        a.is_comparable(b)  ≡  a.accepts(b) || b.accepts(a)
        ```

        Decided by the model (``comparable``, proved equal to it). Raises
        `PrefixMismatchError` if prefixes differ.
        """
        TaggedUrn._same_prefix(self, other)
        return _formal.comparable(self._formal, other._formal)

    def is_equivalent_str(self, other_str: str) -> bool:
        """String variant of `is_equivalent`."""
        other = TaggedUrn.from_string(other_str)
        return self.is_equivalent(other)

    def is_comparable_str(self, other_str: str) -> bool:
        """String variant of `is_comparable`."""
        other = TaggedUrn.from_string(other_str)
        return self.is_comparable(other)

    def delta_from(self, base: "TaggedUrn") -> TaggedUrnCoordinateDelta:
        """Compute the coordinate-space delta from ``base`` to ``self``."""
        if base is None:
            raise TaggedUrnError("cannot derive delta from null URN")
        if self.prefix != base.prefix:
            raise PrefixMismatchError(base.prefix, self.prefix)

        if self.is_equivalent(base):
            relation_kind = TaggedUrnRelationKind.EQUIVALENT
        elif self.is_comparable(base):
            relation_kind = TaggedUrnRelationKind.COMPARABLE
        else:
            relation_kind = TaggedUrnRelationKind.INCOMPARABLE

        removed: Dict[str, Constraint] = {}
        added: Dict[str, Constraint] = {}
        all_keys = set(base.tags.keys()) | set(self.tags.keys())
        for key in all_keys:
            base_value = base.tags.get(key)
            target_value = self.tags.get(key)
            if base_value == target_value:
                continue
            if base_value is not None:
                removed[key] = base_value
            if target_value is not None:
                added[key] = target_value

        return TaggedUrnCoordinateDelta(self.prefix, removed, added, relation_kind)

    def apply_delta(self, delta: TaggedUrnCoordinateDelta) -> "TaggedUrn":
        """Apply a coordinate-space delta to this tagged URN."""
        if delta is None:
            raise TaggedUrnError("cannot apply null delta")
        if self.prefix != delta.prefix:
            raise PrefixMismatchError(delta.prefix, self.prefix)

        next_tags = dict(self._tags)
        for key in delta.removed:
            next_tags.pop(key, None)
        next_tags.update(delta.added)
        return TaggedUrn(self.prefix, next_tags)

    def with_wildcard_tag(self, key: str) -> 'TaggedUrn':
        """The same URN with ``key``, where it has it, made a marker (present)."""
        key = key.lower()
        if key not in self._tags:
            return self
        new_tags = dict(self._tags)
        new_tags[key] = present()
        return TaggedUrn(self.prefix, new_tags)

    def subset(self, keys: List[str]) -> 'TaggedUrn':
        """Create a subset URN with only specified tags"""
        new_tags = {}
        for key in keys:
            key = key.lower()
            if key in self._tags:
                new_tags[key] = self._tags[key]
        return TaggedUrn(self.prefix, new_tags)

    def merge(self, other: 'TaggedUrn') -> 'TaggedUrn':
        """Merge with another URN (other takes precedence for conflicts)

        Both must have the same prefix
        """
        if self.prefix != other.prefix:
            raise PrefixMismatchError(self.prefix, other.prefix)

        new_tags = dict(self._tags)
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
        # The model's forms hold their values in lists, which do not hash; the
        # ordering key holds the same parts, and equal URNs have equal keys.
        return hash(self.ordering_key())

    @staticmethod
    def _form_order(c: Constraint) -> int:
        """A stored constraint's form's place in the order of URNs: the truth
        table's (``?k``, ``k?=…``, ``k=…|!``, ``k``, ``k!=…``, ``k=…``,
        ``!k``)."""
        one = isinstance(c.values, ValuesOneOf)
        vs = c.values.vs
        if c.absent and not one:
            return 1 if vs else 0
        if c.absent and vs:
            return 2
        if not c.absent and not one:
            return 4 if vs else 3
        if not c.absent:
            return 5
        return 6

    def ordering_key(self) -> tuple:
        """The key URNs are ordered by: their parts, never their text. The
        prefix, then the tags in key order, each by its key, then by its
        constraint's form in the truth table's order (``?k``, ``k?=…``,
        ``k=…|!``, ``k``, ``k!=…``, ``k=…``, ``!k``), then by its values in
        order; a URN whose tags are the beginning of another's stands first.
        The text would order ``file;sample`` after ``file-path``, wherever one
        key is the beginning of another."""
        return (
            self.prefix,
            tuple(
                (key, self._form_order(c), tuple(c.values.vs))
                for key, c in sorted(self._tags.items(), key=lambda item: item[0])
            ),
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, TaggedUrn):
            return NotImplemented
        return self.ordering_key() < other.ordering_key()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, TaggedUrn):
            return NotImplemented
        return self.ordering_key() <= other.ordering_key()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, TaggedUrn):
            return NotImplemented
        return self.ordering_key() > other.ordering_key()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, TaggedUrn):
            return NotImplemented
        return self.ordering_key() >= other.ordering_key()


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
        """Create a new builder with a specified prefix (required), which must
        be an identifier and is lowered."""
        self.prefix = _identifier("prefix", prefix)
        self.tags: Dict[str, Constraint] = {}

    def constraint(self, key: str, constraint: Constraint) -> 'TaggedUrnBuilder':
        """Add a tag of any form. The key must be an identifier and is lowered;
        the constraint must be one a URN can write."""
        key = _identifier("key", key)
        _check_constraint(key, constraint)
        if key in self.tags:
            raise DuplicateKeyError(f"Duplicate tag key: {key}")
        self.tags[key] = constraint
        return self

    def tag(self, key: str, value: str) -> 'TaggedUrnBuilder':
        """Add the exact value ``value`` for ``key`` (``key=value``), taken
        literally: ``tag("x", "*")`` is the exact value ``*``, not the marker."""
        return self.constraint(key, exact(value))

    def marker(self, key: str) -> 'TaggedUrnBuilder':
        """Add ``key`` as a marker (there with any value, written as just the key)."""
        return self.constraint(key, present())

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
