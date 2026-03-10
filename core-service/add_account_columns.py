#!/usr/bin/env python3
"""
Script to add level and is_group columns to accounts table
"""

import sqlalchemy as sa

from app.database import engine


def add_columns():
    # Add columns if they don't exist
    with engine.connect() as conn:
        try:
            # Check if columns exist first
            result = conn.execute(
                sa.text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'accounts' AND column_name IN ('level', 'is_group')"
                )
            )
            existing_cols = [row[0] for row in result.fetchall()]

            if "level" not in existing_cols:
                conn.execute(
                    sa.text(
                        "ALTER TABLE accounts ADD COLUMN level INTEGER NOT NULL DEFAULT 1"
                    )
                )
                print("Added level column")
            else:
                print("level column already exists")

            if "is_group" not in existing_cols:
                conn.execute(
                    sa.text(
                        "ALTER TABLE accounts ADD COLUMN is_group BOOLEAN NOT NULL DEFAULT false"
                    )
                )
                print("Added is_group column")
            else:
                print("is_group column already exists")

            conn.commit()
            print("Database schema updated successfully!")
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()


if __name__ == "__main__":
    add_columns()
