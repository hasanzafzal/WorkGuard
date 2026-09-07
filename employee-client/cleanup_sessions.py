import sqlite3

DB_PATH = r"C:\Users\omar.mughal\Videos\WorkGuard\employee-client\storage\employee_buffer.db"

with sqlite3.connect(DB_PATH) as conn:
    # Count all pending sessions
    cursor = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE status = 'pending'"
    )
    pending_count = cursor.fetchone()[0]

    print(f"Total pending sessions: {pending_count}")

    # Get the latest pending session
    cursor = conn.execute(
        """
        SELECT id, session_id, created_at
        FROM sessions
        WHERE status = 'pending'
        ORDER BY id DESC
        LIMIT 1
        """
    )

    latest = cursor.fetchone()

    if latest:
        print(
            f"Latest pending session: "
            f"id={latest[0]}, "
            f"session_id={latest[1]}, "
            f"created_at={latest[2]}"
        )

        # Delete all older pending sessions
        deleted = conn.execute(
            """
            DELETE FROM sessions
            WHERE status = 'pending'
              AND id != ?
            """,
            (latest[0],),
        ).rowcount

        conn.commit()

        print(f"Deleted {deleted} old pending sessions.")

        # Show remaining pending count
        cursor = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE status = 'pending'"
        )
        remaining_count = cursor.fetchone()[0]

        print(f"Remaining pending sessions: {remaining_count}")

    else:
        print("No pending sessions found.")