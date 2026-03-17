import os
import sqlite3
from pathlib import Path

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values


PRESERVED_TABLES = {"django_migrations"}


def map_sqlite_type(sqlite_type: str) -> str:
    normalized = (sqlite_type or "TEXT").upper()
    if "INT" in normalized:
        return "BIGINT"
    if any(token in normalized for token in ("CHAR", "CLOB", "TEXT", "VARCHAR")):
        return "TEXT"
    if any(token in normalized for token in ("REAL", "FLOA", "DOUB")):
        return "DOUBLE PRECISION"
    if "BLOB" in normalized:
        return "BYTEA"
    if any(token in normalized for token in ("NUMERIC", "DECIMAL", "BOOL")):
        return "NUMERIC"
    if any(token in normalized for token in ("DATE", "TIME")):
        return "TIMESTAMP"
    return "TEXT"


def get_sqlite_tables(cursor: sqlite3.Cursor) -> list[str]:
    return [
        row[0]
        for row in cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    ]


def get_sqlite_columns(cursor: sqlite3.Cursor, table_name: str) -> list[tuple]:
    escaped_table_name = table_name.replace('"', '""')
    return cursor.execute(f'PRAGMA table_info("{escaped_table_name}")').fetchall()


def get_postgres_tables(cursor) -> set[str]:
    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    return {row[0] for row in cursor.fetchall()}


def get_postgres_columns(pg_cursor, table_name: str) -> set[str]:
    pg_cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        """,
        (table_name,),
    )
    return {row[0] for row in pg_cursor.fetchall()}


def create_missing_table(pg_cursor, table_name: str, sqlite_columns: list[tuple]) -> None:
    column_definitions = []
    primary_key_columns = []

    for _, column_name, column_type, not_null, _, primary_key_position in sqlite_columns:
        definition = sql.SQL("{} {}").format(
            sql.Identifier(column_name),
            sql.SQL(map_sqlite_type(column_type)),
        )
        if not_null:
            definition += sql.SQL(" NOT NULL")
        column_definitions.append(definition)
        if primary_key_position:
            primary_key_columns.append(sql.Identifier(column_name))

    if primary_key_columns:
        column_definitions.append(
            sql.SQL("PRIMARY KEY ({})").format(sql.SQL(", ").join(primary_key_columns))
        )

    pg_cursor.execute(
        sql.SQL("CREATE TABLE {} ({})").format(
            sql.Identifier(table_name),
            sql.SQL(", ").join(column_definitions),
        )
    )


def add_missing_columns(pg_cursor, table_name: str, sqlite_columns: list[tuple]) -> list[str]:
    postgres_columns = get_postgres_columns(pg_cursor, table_name)
    added_columns = []

    for _, column_name, column_type, _, _, _ in sqlite_columns:
        if column_name in postgres_columns:
            continue

        pg_cursor.execute(
            sql.SQL("ALTER TABLE {} ADD COLUMN {} {}").format(
                sql.Identifier(table_name),
                sql.Identifier(column_name),
                sql.SQL(map_sqlite_type(column_type)),
            )
        )
        added_columns.append(column_name)

    return added_columns


def truncate_tables(pg_cursor, table_names: list[str]) -> None:
    if not table_names:
        return

    qualified_tables = [
        sql.SQL("{}.{}").format(sql.Identifier("public"), sql.Identifier(table_name))
        for table_name in table_names
    ]
    pg_cursor.execute(
        sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
            sql.SQL(", ").join(qualified_tables)
        )
    )


def get_postgres_column_types(pg_cursor, table_name: str) -> dict[str, str]:
    pg_cursor.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    )
    return {column_name: data_type for column_name, data_type in pg_cursor.fetchall()}


def normalize_row_values(row: tuple, column_names: list[str], column_types: dict[str, str]) -> tuple:
    normalized_row = []
    for column_name, value in zip(column_names, row):
        if value is None:
            normalized_row.append(None)
            continue

        column_type = column_types.get(column_name)
        if column_type == "boolean":
            normalized_row.append(bool(value))
            continue

        normalized_row.append(value)

    return tuple(normalized_row)


def fetch_sqlite_rows(
    sqlite_cursor: sqlite3.Cursor,
    table_name: str,
    sqlite_columns: list[tuple],
) -> tuple[list[str], list[tuple]]:
    column_names = [column[1] for column in sqlite_columns]
    escaped_table_name = table_name.replace('"', '""')
    escaped_column_names = [column_name.replace('"', '""') for column_name in column_names]
    select_sql = 'SELECT {} FROM "{}"'.format(
        ', '.join(f'"{column_name}"' for column_name in escaped_column_names),
        escaped_table_name,
    )
    rows = sqlite_cursor.execute(select_sql).fetchall()
    return column_names, rows


def insert_table_rows(
    sqlite_cursor: sqlite3.Cursor,
    pg_connection,
    pg_cursor,
    table_name: str,
    sqlite_columns: list[tuple],
) -> int:
    column_names, rows = fetch_sqlite_rows(sqlite_cursor, table_name, sqlite_columns)
    if not rows:
        return 0

    column_types = get_postgres_column_types(pg_cursor, table_name)
    normalized_rows = [normalize_row_values(row, column_names, column_types) for row in rows]
    insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(sql.Identifier(column_name) for column_name in column_names),
    )
    execute_values(pg_cursor, insert_sql.as_string(pg_connection), normalized_rows, page_size=500)
    return len(normalized_rows)


def merge_table_rows(
    sqlite_cursor: sqlite3.Cursor,
    pg_connection,
    pg_cursor,
    table_name: str,
    sqlite_columns: list[tuple],
) -> int:
    column_names, rows = fetch_sqlite_rows(sqlite_cursor, table_name, sqlite_columns)
    if not rows:
        return 0

    column_types = get_postgres_column_types(pg_cursor, table_name)
    normalized_rows = [normalize_row_values(row, column_names, column_types) for row in rows]
    insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES %s ON CONFLICT DO NOTHING").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(sql.Identifier(column_name) for column_name in column_names),
    )
    execute_values(pg_cursor, insert_sql.as_string(pg_connection), normalized_rows, page_size=500)
    return len(normalized_rows)


def reset_sequences(sqlite_cursor: sqlite3.Cursor, pg_cursor, table_name: str, sqlite_columns: list[tuple]) -> None:
    primary_key_columns = [column for column in sqlite_columns if column[5]]
    if len(primary_key_columns) != 1:
        return

    _, column_name, column_type, _, _, _ = primary_key_columns[0]
    if "INT" not in (column_type or "").upper():
        return

    relation_name = 'public.' + '"' + table_name.replace('"', '""') + '"'
    pg_cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", (relation_name, column_name))
    sequence_name_row = pg_cursor.fetchone()
    if not sequence_name_row or not sequence_name_row[0]:
        return

    escaped_table_name = table_name.replace('"', '""')
    escaped_column_name = column_name.replace('"', '""')
    max_primary_key = sqlite_cursor.execute(
        f'SELECT MAX("{escaped_column_name}") FROM "{escaped_table_name}"'
    ).fetchone()[0]
    if max_primary_key is None:
        pg_cursor.execute("SELECT setval(%s, %s, %s)", (sequence_name_row[0], 1, False))
        return

    pg_cursor.execute("SELECT setval(%s, %s, %s)", (sequence_name_row[0], max_primary_key, True))


def main() -> None:
    workspace_root = Path(__file__).resolve().parent
    sqlite_path = workspace_root / "core" / "db.sqlite3"

    pg_config = {
        "dbname": os.getenv("POSTGRES_DB", "recomart_db"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
    }

    sqlite_connection = sqlite3.connect(sqlite_path)
    sqlite_cursor = sqlite_connection.cursor()

    pg_connection = psycopg2.connect(**pg_config)
    pg_connection.autocommit = False
    pg_cursor = pg_connection.cursor()

    imported_counts = {}
    created_tables = []
    extended_tables = {}

    try:
        sqlite_tables = get_sqlite_tables(sqlite_cursor)
        existing_postgres_tables = get_postgres_tables(pg_cursor)

        for table_name in sqlite_tables:
            sqlite_columns = get_sqlite_columns(sqlite_cursor, table_name)
            if table_name not in existing_postgres_tables:
                create_missing_table(pg_cursor, table_name, sqlite_columns)
                created_tables.append(table_name)
                continue

            added_columns = add_missing_columns(pg_cursor, table_name, sqlite_columns)
            if added_columns:
                extended_tables[table_name] = added_columns

        all_target_tables = get_sqlite_tables(sqlite_cursor)
        replace_tables = [table_name for table_name in all_target_tables if table_name not in PRESERVED_TABLES]
        preserved_tables = [table_name for table_name in all_target_tables if table_name in PRESERVED_TABLES]

        pg_cursor.execute("SET session_replication_role = replica")
        truncate_tables(pg_cursor, replace_tables)

        for table_name in replace_tables:
            sqlite_columns = get_sqlite_columns(sqlite_cursor, table_name)
            imported_counts[table_name] = insert_table_rows(
                sqlite_cursor,
                pg_connection,
                pg_cursor,
                table_name,
                sqlite_columns,
            )
            reset_sequences(sqlite_cursor, pg_cursor, table_name, sqlite_columns)

        for table_name in preserved_tables:
            sqlite_columns = get_sqlite_columns(sqlite_cursor, table_name)
            imported_counts[table_name] = merge_table_rows(
                sqlite_cursor,
                pg_connection,
                pg_cursor,
                table_name,
                sqlite_columns,
            )

        pg_cursor.execute("SET session_replication_role = origin")
        pg_connection.commit()
    except Exception:
        pg_connection.rollback()
        try:
            pg_cursor.execute("SET session_replication_role = origin")
            pg_connection.commit()
        except Exception:
            pg_connection.rollback()
        raise
    finally:
        pg_cursor.close()
        pg_connection.close()
        sqlite_connection.close()

    summary = {
        "sqlite_database": str(sqlite_path),
        "postgres_database": pg_config["dbname"],
        "created_tables": created_tables,
        "extended_tables": extended_tables,
        "table_count": len(imported_counts),
        "imported_rows": imported_counts,
    }
    print(summary)


if __name__ == "__main__":
    main()