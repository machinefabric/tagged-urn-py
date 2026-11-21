"""Tagged URN - Flat tag-based identifier system

This package provides the fundamental tagged URN system with flat tag-based
naming, wildcard support, and specificity comparison.
"""

from importlib import metadata as _metadata

from .tagged_urn import (
    TaggedUrn,
    TaggedUrnBuilder,
    UrnMatcher,
    TaggedUrnError,
    EmptyError,
    MissingPrefixError,
    EmptyPrefixError,
    InvalidCharacterError,
    EmptyTagComponentError,
    UnterminatedQuoteError,
    InvalidEscapeSequenceError,
    DuplicateKeyError,
    WhitespaceInInputError,
    PrefixMismatchError,
    InvalidTagFormatError,
    Constraint,
    ConstraintMissing,
    ConstraintUnconstrained,
    ConstraintOptionalNot,
    ConstraintPresent,
    ConstraintPresentNot,
    ConstraintExact,
    ConstraintAbsent,
)

# Read from the installed distribution's metadata, never hand-copied: this
# constant sat at 0.14.3800 through every release up to 1.27.122, silently
# reporting a version that had not existed for hundreds of publishes.
# `pyproject.toml` (generated from `version.txt`) is the one declaration.
try:
    __version__ = _metadata.version("tagged-urn")
except _metadata.PackageNotFoundError:
    # Imported straight from `src/` without being installed — the version is
    # genuinely unknown here, and saying so beats asserting a stale number.
    __version__ = "0+unknown"

__all__ = [
    "TaggedUrn",
    "TaggedUrnBuilder",
    "UrnMatcher",
    "TaggedUrnError",
    "EmptyError",
    "MissingPrefixError",
    "EmptyPrefixError",
    "InvalidCharacterError",
    "EmptyTagComponentError",
    "UnterminatedQuoteError",
    "InvalidEscapeSequenceError",
    "DuplicateKeyError",
    "WhitespaceInInputError",
    "PrefixMismatchError",
    "InvalidTagFormatError",
    "Constraint",
    "ConstraintMissing",
    "ConstraintUnconstrained",
    "ConstraintOptionalNot",
    "ConstraintPresent",
    "ConstraintPresentNot",
    "ConstraintExact",
    "ConstraintAbsent",
]
