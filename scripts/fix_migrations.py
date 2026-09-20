"""Make all Alembic migrations idempotent using line-based parsing."""
import os
import sys

MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core-service", "alembic", "versions"
)


def fix_file(path: str) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    text = "".join(lines)
    if "inspector.has_table" in text:
        return False

    if "def upgrade" not in text:
        return False

    # Add inspect import
    has_inspect_import = any("from sqlalchemy import inspect" in l for l in lines)
    if not has_inspect_import:
        for i, line in enumerate(lines):
            if "from sqlalchemy.dialects import postgresql" in line:
                lines.insert(i, "from sqlalchemy import inspect\n")
                break
            elif "import sqlalchemy as sa" in line and i + 1 < len(lines):
                if "from sqlalchemy import inspect" not in lines[i + 1]:
                    lines.insert(i + 1, "from sqlalchemy import inspect\n")
                break

    # Find upgrade() and insert boilerplate
    new_lines = []
    in_upgrade = False
    upgrade_indent = 4
    boilerplate_inserted = False

    for idx, line in enumerate(lines):
        stripped = line.lstrip()

        # Detect upgrade() start
        if stripped.startswith("def upgrade"):
            in_upgrade = True
            new_lines.append(line)
            continue

        if in_upgrade and not boilerplate_inserted:
            if stripped and not stripped.startswith("#"):
                # First non-blank, non-comment line inside upgrade
                indent = len(line) - len(line.lstrip())
                upgrade_indent = indent
                bp = (
                    " " * indent + "inspector = inspect(op.get_bind())\n\n"
                    + " " * indent + "def _has_index(table_name: str, index_name: str) -> bool:\n"
                    + " " * (indent + 4) + "return any(i['name'] == index_name for i in inspector.get_indexes(table_name))\n\n"
                )
                new_lines.append(bp)
                boilerplate_inserted = True

        new_lines.append(line)

    if not boilerplate_inserted:
        return False

    # Second pass: wrap create_table and create_index
    final_lines = []
    i = 0
    while i < len(new_lines):
        line = new_lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(line.lstrip())

        # Wrap op.create_table('name', ...)
        if stripped.startswith("op.create_table("):
            # Find the table name on this line or next
            table_name = None
            if "'" in stripped:
                parts = stripped.split("'")
                if len(parts) >= 3:
                    table_name = parts[1]
            if table_name:
                final_lines.append(" " * indent + f"if not inspector.has_table('{table_name}'):\n")
                final_lines.append(" " * (indent + 4) + stripped)
            else:
                final_lines.append(line)
            i += 1
            continue

        # Wrap op.create_index('idx', 'table', ...)
        if stripped.startswith("op.create_index("):
            # Parse: op.create_index('idx_name', 'table_name', [...])
            idx_name = None
            tbl_name = None
            if "'" in stripped:
                parts = stripped.split("'")
                if len(parts) >= 5:
                    idx_name = parts[1]
                    tbl_name = parts[3]
            if idx_name and tbl_name:
                final_lines.append(" " * indent + f"if not _has_index('{tbl_name}', '{idx_name}'):\n")
                final_lines.append(" " * (indent + 4) + stripped)
            else:
                final_lines.append(line)
            i += 1
            continue

        final_lines.append(line)
        i += 1

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(final_lines)
    return True


def main():
    processed = 0
    skipped = 0
    for fname in sorted(os.listdir(MIGRATIONS_DIR)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(MIGRATIONS_DIR, fname)
        if fix_file(path):
            print(f"  ✓ {fname}")
            processed += 1
        else:
            print(f"  – {fname}")
            skipped += 1
    print(f"\nDone: {processed} modified, {skipped} unchanged")


if __name__ == "__main__":
    main()
