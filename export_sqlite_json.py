import json
import sqlite3
from pathlib import Path


def main() -> None:
    workspace_root = Path(__file__).resolve().parent
    database_path = workspace_root / "core" / "db.sqlite3"
    output_path = workspace_root / "database_merged.json"

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    table_names = [
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

    export = {
        "database": str(database_path),
        "table_count": len(table_names),
        "tables": {},
    }

    for table_name in table_names:
        escaped_table_name = table_name.replace('"', '""')
        rows = [
            dict(row)
            for row in cursor.execute(f'SELECT * FROM "{escaped_table_name}"').fetchall()
        ]
        export["tables"][table_name] = {
            "row_count": len(rows),
            "rows": rows,
        }

    output_path.write_text(json.dumps(export, indent=2, ensure_ascii=False), encoding="utf-8")
    connection.close()

    summary = {
        "output": str(output_path),
        "table_count": export["table_count"],
        "rows_per_table": {
            table_name: table_data["row_count"]
            for table_name, table_data in export["tables"].items()
        },
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()