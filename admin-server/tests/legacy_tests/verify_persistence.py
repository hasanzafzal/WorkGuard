#!/usr/bin/env python3
"""Verify database persistence."""

from database.connection import get_connection

conn = get_connection()
try:
    with conn.cursor() as cur:
        # Check sessions table
        cur.execute('SELECT session_id, employee_id, start_time, status FROM sessions ORDER BY start_time DESC LIMIT 1')
        session_row = cur.fetchone()
        if session_row:
            print('✅ Session found in DB:')
            print(f'   session_id: {session_row[0]}')
            print(f'   employee_id: {session_row[1]}')
            print(f'   start_time: {session_row[2]}')
            print(f'   status: {session_row[3]}')
        else:
            print('❌ No sessions in database')
        
        # Check employees table
        cur.execute('SELECT employee_id, employee_name, first_seen, last_seen FROM employees ORDER BY last_seen DESC LIMIT 1')
        emp_row = cur.fetchone()
        if emp_row:
            print('\n✅ Employee found in DB:')
            print(f'   employee_id: {emp_row[0]}')
            print(f'   employee_name: {emp_row[1]}')
            print(f'   first_seen: {emp_row[2]}')
            print(f'   last_seen: {emp_row[3]}')
        else:
            print('\n❌ No employees in database')
finally:
    conn.close()
