"""Layout document migrations.

The document carries ``schemaVersion``. Adding an optional field with a default
does **not** need a version bump — old documents still parse, because the schema
applies the default. Bumping the version is reserved for changes that alter
*meaning*: renamed fields, changed units, or a changed default that moves
geometry.

Every future migration must be added here as a step function and mirrored in the
TypeScript engine (``layout-core/migrate.ts``); a document that parses on one side
and not the other is a defect.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 3
"""

from __future__ import annotations

from typing import Any

from app.layout_design.schema import CURRENT_SCHEMA_VERSION


class UnsupportedSchemaVersionError(ValueError):
    """Raised when a document was produced by a newer build than this one."""

    def __init__(self, version: int) -> None:
        super().__init__(
            f"Document schemaVersion {version} is newer than this build supports "
            f"(max {CURRENT_SCHEMA_VERSION})"
        )
        self.version = version


def migrate_document(raw: dict[str, Any]) -> dict[str, Any]:
    """Bring a raw document up to :data:`CURRENT_SCHEMA_VERSION`.

    Unknown/absent versions default to the current version so that a hand-written
    document without a version still imports.

    Args:
        raw: The parsed JSON document.

    Returns:
        A document at the current schema version. The input is not mutated.

    Raises:
        UnsupportedSchemaVersionError: If the document is newer than this build.
    """
    document = dict(raw)
    version = document.get("schemaVersion", CURRENT_SCHEMA_VERSION)

    if not isinstance(version, int):
        # Leave it to the schema to report a malformed version.
        return document

    if version > CURRENT_SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(version)

    # v1 is the first version, so there is nothing to upgrade yet. Future steps
    # chain here, e.g.:
    #   if version < 2:
    #       document = _v1_to_v2(document)
    #       version = 2

    document["schemaVersion"] = CURRENT_SCHEMA_VERSION
    return document
