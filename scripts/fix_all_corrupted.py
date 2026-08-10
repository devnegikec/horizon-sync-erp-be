"""Fix all corrupted migration files. Removes duplicate guards, fixes indentation, adds index guards."""
import os
import re

DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core-service", "alembic", "versions"
)

TABLE_RE = re.compile(r"^\s+if not inspector\.has_table\('([^']+)'\):\s*$")
INDEX_RE = re.compile(r"^\s+op\.create_index\('([^']+)',\s+'([^']+)',(.*)$")


def fix_file(path):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    # Only process files that have inspector boilerplate
    if "inspector = inspect(op.get_bind())" not in text:
        return False

    lines = text.splitlines(keepends=True)
    new_lines = []
    i = 0
    in_upgrade = False
    upgrade_indent = 4
    has_boilerplate = False

    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(line.lstrip())

        # Detect upgrade start
        if stripped.startswith("def upgrade"):
            in_upgrade = True
            new_lines.append(line)
            i += 1
            continue

        if in_upgrade and not has_boilerplate:
            if stripped and not stripped.startswith("#") and not stripped.startswith("def "):
                upgrade_indent = indent
                # Check if boilerplate already exists
                if "_has_index" not in text:
                    bp = (
                        " " * indent + "inspector = inspect(op.get_bind())\n\n"
                        " " * indent + "def _has_index(table_name: str, index_name: str) -> bool:\n"
                        " " * (indent + 4) + "return any(i['name'] == index_name for i in inspector.get_indexes(table_name))\n\n"
                    )
                    new_lines.append(bp)
                has_boilerplate = True

        # Detect duplicate has_table guards and collapse them
        m = TABLE_RE.match(line)
        if m and in_upgrade:
            table_name = m.group(1)
            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            next_stripped = next_line.lstrip()
            # Check if next line is ALSO a has_table guard for same table
            if f"if not inspector.has_table('{table_name}')" in next_stripped:
                # Skip first guard, keep second
                new_lines.append(line)
                i += 2
                # Now fix indentation of create_table block
                # Find the op.create_table( line
                while i < len(lines):
                    l = lines[i]
                    ls = l.lstrip()
                    if ls.startswith("op.create_table("):
                        # Indent everything inside to be +4 from the single guard
                        guard_indent = indent
                        block_indent = guard_indent + 4
                        new_lines.append(" " * block_indent + ls)
                        i += 1
                        # Continue until we hit a line that ends the block
                        # (a line with less or equal indent to guard, or empty)
                        while i < len(lines):
                            inner = lines[i]
                            inner_stripped = inner.lstrip()
                            inner_indent = len(inner) - len(inner.lstrip())
                            if inner_stripped == "":
                                new_lines.append(inner)
                                i += 1
                                continue
                            # If this line is at or outside the guard indent, block ended
                            if inner_indent <= guard_indent and not inner_stripped.startswith(")"):
                                break
                            # Fix indentation: strip old indent, add block indent
                            content = inner.lstrip()
                            new_lines.append(" " * block_indent + content)
                            i += 1
                        break
                    else:
                        i += 1
                continue
            else:
                # Single guard - keep as-is but may need to fix create_table indent
                new_lines.append(line)
                i += 1
                # Fix create_table indentation inside single guard
                if i < len(lines):
                    cl = lines[i]
                    cs = cl.lstrip()
                    if cs.startswith("op.create_table("):
                        guard_indent = indent
                        if len(cl) - len(cl.lstrip()) <= guard_indent:
                            # Need to indent the block
                            block_indent = guard_indent + 4
                            new_lines.append(" " * block_indent + cs)
                            i += 1
                            while i < len(lines):
                                inner = lines[i]
                                inner_stripped = inner.lstrip()
                                inner_indent = len(inner) - len(inner.lstrip())
                                if inner_stripped == "":
                                    new_lines.append(inner)
                                    i += 1
                                    continue
                                if inner_indent <= guard_indent and not inner_stripped.startswith(")"):
                                    break
                                content = inner.lstrip()
                                new_lines.append(" " * block_indent + content)
                                i += 1
                            continue
                continue

        # Detect unguarded create_index inside upgrade
        m2 = INDEX_RE.match(line)
        if m2 and in_upgrade:
            idx_name = m2.group(1)
            tbl_name = m2.group(2)
            rest = m2.group(3)
            # Only wrap if not already wrapped
            prev = new_lines[-1].lstrip() if new_lines else ""
            if not prev.startswith("if not _has_index"):
                guard_indent = indent
                new_lines.append(" " * guard_indent + f"if not _has_index('{tbl_name}', '{idx_name}'):\n")
                new_lines.append(" " * (guard_indent + 4) + f"op.create_index('{idx_name}', '{tbl_name}'," + rest + "\n")
                i += 1
                continue

        new_lines.append(line)
        i += 1

    result = "".join(new_lines)
    if result == text:
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(result)
    return True


def main():
    fixed = 0
    for fname in sorted(os.listdir(DIR)):
        if not fname.endswith(".py"):
            continue
        path = os.path.join(DIR, fname)
        if fix_file(path):
            print(f"  + {fname}")
            fixed += 1
        else:
            print(f"  - {fname}")
    print(f"\nFixed {fixed} files")


if __name__ == "__main__":
    main()
