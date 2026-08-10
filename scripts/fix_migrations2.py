"""Fix migrations where create_table table name is on next line."""
import os
import re

MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core-service", "alembic", "versions"
)


def fix_file(path: str) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    if "inspector.has_table" not in text:
        return False  # script 1 didn't touch it

    if "op.create_table(\n" in text and "inspector.has_table" in text:
        lines = text.splitlines(keepends=True)
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            indent = len(line) - len(line.lstrip())

            # Detect bare op.create_table( followed by 'name' on next line
            if stripped == "op.create_table(\n" or stripped.startswith("op.create_table(\n"):
                # Look ahead for table name
                table_name = None
                for j in range(i + 1, min(i + 5, len(lines))):
                    m = re.search(r"^\s+'([^']+)',", lines[j])
                    if m:
                        table_name = m.group(1)
                        break
                if table_name:
                    new_lines.append(" " * indent + f"if not inspector.has_table('{table_name}'):\n")
                    new_lines.append(" " * (indent + 4) + stripped)
                    i += 1
                    continue

            # Detect bare op.create_index( followed by args on next lines
            if stripped == "op.create_index(\n" or stripped.startswith("op.create_index(\n"):
                idx_name = None
                tbl_name = None
                for j in range(i + 1, min(i + 6, len(lines))):
                    m = re.search(r"^\s+'([^']+)',", lines[j])
                    if m and idx_name is None:
                        idx_name = m.group(1)
                    elif m and tbl_name is None:
                        tbl_name = m.group(1)
                        break
                if idx_name and tbl_name:
                    new_lines.append(" " * indent + f"if not _has_index('{tbl_name}', '{idx_name}'):\n")
                    new_lines.append(" " * (indent + 4) + stripped)
                    i += 1
                    continue

            new_lines.append(line)
            i += 1

        with open(path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    return False


def main():
    processed = 0
    for fname in sorted(os.listdir(MIGRATIONS_DIR)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(MIGRATIONS_DIR, fname)
        if fix_file(path):
            print(f"  ✓ {fname}")
            processed += 1
        else:
            print(f"  – {fname}")
    print(f"\nDone: {processed} files fixed")


if __name__ == "__main__":
    main()
