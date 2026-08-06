"""Fix migrations: wrap create_table with inspector.has_table."""
import os

MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core-service", "alembic", "versions"
)


def fix_file(path: str) -> bool:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Only fix files that have boilerplate but no has_table guards
    if "inspector.has_table" in text:
        return False
    if "inspector = inspect(op.get_bind())" not in text:
        return False

    lines = text.splitlines(keepends=True)
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(line.lstrip())

        # Detect: op.create_table(
        if stripped.rstrip() == "op.create_table(":
            # Look ahead for table name
            table_name = None
            for j in range(i + 1, min(i + 5, len(lines))):
                s = lines[j].strip()
                if s.startswith("'") and s.endswith("',"):
                    table_name = s[1:-2]
                    break
            if table_name:
                new_lines.append(" " * indent + f"if not inspector.has_table('{table_name}'):\n")
                new_lines.append(" " * (indent + 4) + stripped.rstrip() + "\n")
                i += 1
                continue

        new_lines.append(line)
        i += 1

    if new_lines == lines:
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return True


def main():
    processed = 0
    for fname in sorted(os.listdir(MIGRATIONS_DIR)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(MIGRATIONS_DIR, fname)
        if fix_file(path):
            print(f"  + {fname}")
            processed += 1
        else:
            print(f"  - {fname}")
    print(f"\nFixed: {processed} files")


if __name__ == "__main__":
    main()
