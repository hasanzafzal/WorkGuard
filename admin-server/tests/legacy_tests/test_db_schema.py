import os
import psycopg
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "workguard"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def list_database_schema():
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:

                # Get all user tables
                cursor.execute("""
                    SELECT table_schema, table_name
                    FROM information_schema.tables
                    WHERE table_type = 'BASE TABLE'
                      AND table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_schema, table_name;
                """)

                tables = cursor.fetchall()

                print("\n" + "=" * 70)
                print("DATABASE TABLES")
                print("=" * 70)

                if not tables:
                    print("No tables found.")
                    return

                for schema, table in tables:
                    print(f"\n📦 {schema}.{table}")
                    print("-" * 70)

                    # Get columns
                    cursor.execute("""
                        SELECT
                            c.column_name,
                            c.data_type,
                            c.is_nullable,
                            c.column_default
                        FROM information_schema.columns c
                        WHERE c.table_schema = %s
                          AND c.table_name = %s
                        ORDER BY c.ordinal_position;
                    """, (schema, table))

                    columns = cursor.fetchall()

                    for column_name, data_type, nullable, default in columns:
                        print(f"  ├── {column_name}")
                        print(f"  │   Type: {data_type}")
                        print(f"  │   Nullable: {nullable}")

                        if default:
                            print(f"  │   Default: {default}")

                        print("  │")


    except Exception as e:
        print("❌ Failed to read database schema!")
        print(e)


if __name__ == "__main__":
    list_database_schema()
