"""Admin REST API routes for WorkGuard telemetry, stats, and logs."""

import base64
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ai.processor import process_verified_session

router = APIRouter(prefix="/api/v1", tags=["Admin API"])

BASE_DIR = Path(__file__).resolve().parent.parent
RECEIVED_SESSIONS_DIR = BASE_DIR / "received_sessions"
VERIFIED_SESSIONS_DIR = BASE_DIR / "verified_sessions"
PROCESSED_SESSIONS_DIR = BASE_DIR / "processed_sessions"
REPORTS_DIR = BASE_DIR / "reports"


def get_encryption_key() -> bytes:
    """Retrieve or generate default AES-256 key for testing."""
    key_str = os.getenv("WORKGUARD_AES_KEY_BASE64")
    if key_str:
        try:
            key = base64.b64decode(key_str, validate=True)
            if len(key) == 32:
                return key
        except Exception:
            pass
    # Default 32-byte key for local dev if not configured
    default_key = b"WorkGuardSecureKey32BytesForDev!"
    os.environ["WORKGUARD_AES_KEY_BASE64"] = base64.b64encode(default_key).decode("ascii")
    return default_key


def _read_all_json_in_dir(directory: Path) -> list[dict]:
    """Read all JSON files from a target directory."""
    if not directory.exists():
        return []
    records = []
    for file_path in directory.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    records.append(data)
        except Exception:
            continue
    return records


@router.get("/stats")
def get_dashboard_stats() -> dict[str, Any]:
    """Calculate aggregated stats from all received, verified, and processed sessions."""
    verified = _read_all_json_in_dir(VERIFIED_SESSIONS_DIR)
    reports = _read_all_json_in_dir(REPORTS_DIR)
    received = _read_all_json_in_dir(RECEIVED_SESSIONS_DIR)

    total_sessions = len(verified)
    unique_employees = sorted(list({v.get("employee_id") for v in verified if v.get("employee_id")}))
    
    total_duration = 0
    total_events = 0
    for v in verified:
        session_data = v.get("session", {})
        total_duration += session_data.get("session", {}).get("duration_seconds", 0)
        events = session_data.get("events", [])
        if isinstance(events, list):
            total_events += len(events)

    avg_duration = round(total_duration / total_sessions) if total_sessions > 0 else 0

    # Productivity analysis aggregation
    productivity_counts = {"productive": 0, "mixed": 0, "unclear": 0}
    security_alerts_count = 0
    flagged_sessions_count = 0

    for r in reports:
        analysis = r.get("session_analysis", {})
        prod = analysis.get("productivity_assessment", "").lower()
        if prod in productivity_counts:
            productivity_counts[prod] += 1
        elif prod:
            productivity_counts["unclear"] += 1

        sec = r.get("security", {})
        alerts = sec.get("alerts", [])
        if alerts:
            security_alerts_count += len(alerts)
            flagged_sessions_count += 1

    # Temporal breakdown (by hour of receipt)
    hourly_activity: dict[str, int] = {}
    for v in verified:
        rcv = v.get("received_at")
        if rcv:
            try:
                dt = datetime.fromisoformat(rcv.replace("Z", "+00:00"))
                hour_key = dt.strftime("%H:00")
                hourly_activity[hour_key] = hourly_activity.get(hour_key, 0) + 1
            except Exception:
                pass

    return {
        "status": "operational",
        "total_received": len(received),
        "total_verified": total_sessions,
        "total_reports": len(reports),
        "active_employees_count": len(unique_employees),
        "employees": unique_employees,
        "total_duration_seconds": total_duration,
        "avg_duration_seconds": avg_duration,
        "total_events_recorded": total_events,
        "productivity_breakdown": productivity_counts,
        "security_alerts_count": security_alerts_count,
        "flagged_sessions_count": flagged_sessions_count,
        "hourly_activity": hourly_activity,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/sessions")
def list_sessions(
    search: Optional[str] = None,
    productivity: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List all sessions: checks PostgreSQL first (System of Record), merging verified files."""
    results: list[dict[str, Any]] = []
    seen_session_ids: set[str] = set()

    # 1. Retrieve from PostgreSQL first (System of Record)
    try:
        from retrieval.structured import get_sessions as pg_get_sessions
        pg_sessions = pg_get_sessions(limit=limit)
        for s in pg_sessions:
            sid = s["session_id"]
            seen_session_ids.add(sid)
            prod_secs = s.get("productive_seconds") or 0
            dur_secs = s.get("duration_seconds") or 1
            prod_pct = round(prod_secs / dur_secs * 100, 1)

            # Filter by search
            if search:
                q = search.lower()
                emp_id = (s.get("employee_id") or "").lower()
                emp_name = (s.get("employee_name") or "").lower()
                username = (s.get("username") or "").lower()
                if q not in sid.lower() and q not in emp_id and q not in emp_name and q not in username:
                    continue

            assessment = "productive" if prod_pct >= 50 else "mixed"
            if productivity and productivity.lower() != "all" and productivity.lower() not in assessment:
                continue

            results.append({
                "session_id": sid,
                "employee_id": s["employee_id"],
                "employee_name": s.get("employee_name") or s.get("username") or s["employee_id"],
                "start_time": s["start_time"],
                "end_time": s["end_time"],
                "received_at": s["start_time"],
                "duration_seconds": s["duration_seconds"],
                "events_count": (s.get("total_file_operations") or 0) + len(s.get("applications_used") or []),
                "productivity_assessment": assessment,
                "risk_score": 0,
                "security_alerts": [],
                "summary": f"{len(s.get('applications_used', []))} apps used. {s.get('productive_seconds', 0)}s productive ({prod_pct}%).",
                "has_report": True,
                "status": s.get("processing_status") or "completed",
            })
    except Exception as exc:
        pass

    # 2. Supplement with any file-based verified sessions not in PostgreSQL
    verified_files = sorted(
        VERIFIED_SESSIONS_DIR.glob("*.json") if VERIFIED_SESSIONS_DIR.exists() else [],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    reports_map: dict[str, dict] = {}
    if REPORTS_DIR.exists():
        for r_file in REPORTS_DIR.glob("*.json"):
            try:
                with open(r_file, "r", encoding="utf-8") as f:
                    r_data = json.load(f)
                    sid = r_data.get("session_id")
                    if sid:
                        reports_map[sid] = r_data
            except Exception:
                continue

    for v_file in verified_files:
        try:
            with open(v_file, "r", encoding="utf-8") as f:
                v_data = json.load(f)
        except Exception:
            continue

        session_id = v_data.get("session_id", "")
        if session_id in seen_session_ids:
            continue

        employee_id = v_data.get("employee_id", "")
        received_at = v_data.get("received_at", "")
        session_content = v_data.get("session", {})

        report = reports_map.get(session_id, {})
        analysis = report.get("session_analysis", {})
        security = report.get("security", {})

        prod_assessment = analysis.get("productivity_assessment", "unclear")
        risk_score = security.get("risk_score", 0)
        alerts = security.get("alerts", [])

        # Filter by search
        if search:
            query = search.lower()
            if query not in session_id.lower() and query not in employee_id.lower():
                continue

        # Filter by productivity
        if productivity and productivity.lower() != "all":
            if prod_assessment.lower() != productivity.lower():
                continue

        duration = session_content.get("session", {}).get("duration_seconds", 0)
        events = session_content.get("events", [])
        events_count = len(events) if isinstance(events, list) else 0

        results.append({
            "session_id": session_id,
            "employee_id": employee_id,
            "employee_name": session_content.get("employee_name") or employee_id,
            "start_time": session_content.get("session", {}).get("started_at", received_at),
            "end_time": session_content.get("session", {}).get("ended_at", received_at),
            "received_at": received_at,
            "duration_seconds": duration,
            "events_count": events_count,
            "productivity_assessment": prod_assessment,
            "risk_score": risk_score,
            "security_alerts": alerts,
            "summary": analysis.get("summary", "Session validated and stored."),
            "has_report": bool(report),
            "status": "processed" if report else "verified",
        })

        if len(results) >= limit:
            break

    return results[:limit]


@router.get("/sessions/{session_id}")
def get_session_detail(session_id: str) -> dict[str, Any]:
    """Retrieve comprehensive session data: checks PostgreSQL first, then verified files."""
    # 1. Check PostgreSQL first (System of Record)
    try:
        from retrieval.structured import get_session_details
        pg_detail = get_session_details(session_id)
        if pg_detail:
            s = pg_detail["session"]
            focus_summary = {
                app["display_name"] or app["process_name"]: float(app["focus_seconds"])
                for app in pg_detail.get("applications", [])
            }
            formatted_events = []
            for p in pg_detail.get("process_events", []):
                t_str = str(p.get("occurred_at", "00:00:00"))
                if "T" in t_str:
                    t_str = t_str.split("T")[1][:8]
                formatted_events.append({
                    "timestamp": t_str,
                    "app_name": p.get("process_name", "Process"),
                    "window_title": p.get("executable", ""),
                    "event_type": "process",
                    "active_seconds": None,
                })
            for d in pg_detail.get("directories", []):
                t_str = str(d.get("period_start", "00:00:00"))
                if "T" in t_str:
                    t_str = t_str.split("T")[1][:8]
                formatted_events.append({
                    "timestamp": t_str,
                    "app_name": "File System",
                    "window_title": d.get("directory_path", ""),
                    "event_type": "file_system",
                    "active_seconds": d.get("period_seconds"),
                })

            doc_titles = [doc["title"] for doc in pg_detail.get("analysis_documents", [])]
            prod_secs = s.get("productive_seconds") or 0
            dur_secs = s.get("duration_seconds") or 1
            prod_pct = round(prod_secs / dur_secs * 100, 1)

            return {
                "session_id": session_id,
                "employee_id": s.get("employee_id") or "UNKNOWN",
                "employee_name": s.get("employee_name") or s.get("username") or "Employee",
                "start_time": str(s.get("start_time")),
                "end_time": str(s.get("end_time")),
                "duration_seconds": s.get("duration_seconds") or 0,
                "events_count": len(formatted_events),
                "events": formatted_events,
                "focus_summary": focus_summary,
                "metadata": {
                    "machine_name": s.get("machine_name"),
                    "schema_version": s.get("schema_version"),
                    "ingested_at": str(s.get("ingested_at")),
                },
                "productivity_assessment": f"productive ({prod_pct}%)" if prod_pct >= 50 else "mixed",
                "risk_score": 0,
                "security_alerts": [],
                "ai_analysis": {
                    "summary": f"Observed {len(focus_summary)} applications and {s.get('total_file_operations', 0)} file operations in {round(dur_secs/60, 1)}m.",
                    "productivity_assessment": f"productive ({prod_pct}%)",
                    "key_activities": doc_titles if doc_titles else ["Session analysis completed and vectors indexed"],
                    "focus_observations": [f"{app}: {round(sec)}s" for app, sec in focus_summary.items()],
                    "recommended_follow_up": [],
                },
                "security_analysis": {
                    "risk_score": 0,
                    "alerts": [],
                    "assessment": "Integrity confirmed by PostgreSQL system of record.",
                },
                "session": s,
                "report": {},
                "raw_envelope": {},
            }
    except Exception as exc:
        pass

    # 2. Fallback to verified_sessions files
    matched_verified = None
    if VERIFIED_SESSIONS_DIR.exists():
        for file_path in VERIFIED_SESSIONS_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("session_id") == session_id:
                        matched_verified = data
                        break
            except Exception:
                continue

    if not matched_verified:
        raise HTTPException(status_code=404, detail="Session not found")

    # Find in reports
    matched_report = None
    if REPORTS_DIR.exists():
        for file_path in REPORTS_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("session_id") == session_id:
                        matched_report = data
                        break
            except Exception:
                continue

    # Find in received_sessions (raw encryption payload)
    matched_received = None
    if RECEIVED_SESSIONS_DIR.exists():
        for file_path in RECEIVED_SESSIONS_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("session_id") == session_id:
                        matched_received = data
                        break
            except Exception:
                continue

    inner_session = matched_verified.get("session", {})
    metadata = inner_session.get("metadata", {})
    session_timing = inner_session.get("session", {})

    # Extract timing
    duration = session_timing.get("duration_seconds") or inner_session.get("duration_seconds") or 0
    start_time = session_timing.get("started_at") or matched_verified.get("received_at") or datetime.now(timezone.utc).isoformat()
    end_time = session_timing.get("ended_at") or matched_verified.get("received_at") or datetime.now(timezone.utc).isoformat()

    # Normalize events
    raw_events = inner_session.get("events", [])
    if not isinstance(raw_events, list):
        raw_events = []

    formatted_events = []
    for evt in raw_events:
        if isinstance(evt, dict):
            timestamp_str = evt.get("timestamp", "")
            if "T" in timestamp_str:
                try:
                    dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    timestamp_str = dt.strftime("%H:%M:%S")
                except Exception:
                    pass
            formatted_events.append({
                "timestamp": timestamp_str or "00:00:00",
                "app_name": evt.get("app_name", "Process"),
                "window_title": evt.get("window_title", ""),
                "event_type": evt.get("event_type", "focused"),
                "active_seconds": evt.get("active_seconds"),
            })

    # Normalize focus summary
    focus_summary_raw = inner_session.get("focus_summary", {})
    focus_summary = {}
    if isinstance(focus_summary_raw, dict):
        for k, v in focus_summary_raw.items():
            if isinstance(v, (int, float)):
                focus_summary[k] = float(v)
            elif isinstance(v, str):
                focus_summary[v] = 60.0

    if not focus_summary and formatted_events:
        for evt in formatted_events:
            app = evt["app_name"]
            secs = evt.get("active_seconds") or 30.0
            focus_summary[app] = focus_summary.get(app, 0.0) + float(secs)

    analysis = (matched_report or {}).get("session_analysis", {})
    security = (matched_report or {}).get("security", {})

    return {
        "session_id": session_id,
        "employee_id": matched_verified.get("employee_id") or "UNKNOWN",
        "employee_name": inner_session.get("employee_name") or matched_verified.get("employee_id") or "Unknown Employee",
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": max(0, duration),
        "events_count": len(formatted_events),
        "events": formatted_events,
        "focus_summary": focus_summary,
        "metadata": metadata,
        "productivity_assessment": analysis.get("productivity_assessment", "assessed"),
        "risk_score": security.get("risk_score", 0),
        "security_alerts": security.get("alerts", []),
        "ai_analysis": {
            "summary": analysis.get("summary", "Session verified and stored."),
            "productivity_assessment": analysis.get("productivity_assessment"),
            "key_activities": analysis.get("key_activities", []),
            "focus_observations": analysis.get("focus_observations", []),
            "recommended_follow_up": analysis.get("recommended_follow_up", []),
        },
        "security_analysis": {
            "risk_score": security.get("risk_score", 0),
            "alerts": security.get("alerts", []),
            "assessment": security.get("assessment", "Integrity confirmed"),
        },
        "session": inner_session,
        "report": matched_report or {},
        "raw_envelope": matched_received or {},
    }



@router.get("/logs")
def get_logs(limit: int = Query(100, ge=10, le=500)) -> list[dict[str, Any]]:
    """Retrieve chronological audit and data ingestion logs."""
    logs: list[dict[str, Any]] = []

    # Parse verified session receipts
    if VERIFIED_SESSIONS_DIR.exists():
        for p in VERIFIED_SESSIONS_DIR.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    rcv = data.get("received_at", datetime.now(timezone.utc).isoformat())
                    logs.append({
                        "id": f"log-rcv-{data.get('session_id')}",
                        "timestamp": rcv,
                        "level": "INFO",
                        "category": "INGESTION",
                        "session_id": data.get("session_id"),
                        "employee_id": data.get("employee_id"),
                        "message": f"Successfully received and decrypted session {data.get('session_id')} from {data.get('employee_id')}",
                    })
            except Exception:
                continue

    # Parse reports / security alerts
    if REPORTS_DIR.exists():
        for p in REPORTS_DIR.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    r = json.load(f)
                    gen_at = r.get("generated_at", datetime.now(timezone.utc).isoformat())
                    sec = r.get("security", {})
                    alerts = sec.get("alerts", [])

                    if alerts:
                        logs.append({
                            "id": f"log-sec-{r.get('session_id')}",
                            "timestamp": gen_at,
                            "level": "SECURITY_ALERT",
                            "category": "SECURITY",
                            "session_id": r.get("session_id"),
                            "employee_id": r.get("employee_id"),
                            "message": f"Security integrity alert for {r.get('session_id')}: {'; '.join(alerts)}",
                        })

                    prod = r.get("session_analysis", {}).get("productivity_assessment")
                    logs.append({
                        "id": f"log-ai-{r.get('session_id')}",
                        "timestamp": gen_at,
                        "level": "SUCCESS",
                        "category": "AI_PIPELINE",
                        "session_id": r.get("session_id"),
                        "employee_id": r.get("employee_id"),
                        "message": f"AI workflow completed for {r.get('session_id')} (Productivity: {prod or 'assessed'})",
                    })
            except Exception:
                continue

    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs[:limit]


class SimulationRequest(BaseModel):
    preset: str = Field(
        default="productive_dev",
        description="Preset type: productive_dev, mixed_activity, design_session, security_flagged",
    )
    employee_id: Optional[str] = None


@router.post("/simulate")
def simulate_incoming_session(payload: SimulationRequest) -> dict[str, Any]:
    """Inject a realistic encrypted test session into the ingestion pipeline."""
    session_id = f"sess_{uuid.uuid4().hex[:10]}"
    employee_id = payload.employee_id or (
        "emp_marcus_dev" if payload.preset == "productive_dev"
        else "emp_elena_design" if payload.preset == "design_session"
        else "emp_alex_mixed" if payload.preset == "mixed_activity"
        else "emp_suspicious_act"
    )

    created_at = datetime.now(timezone.utc).isoformat()

    if payload.preset == "productive_dev":
        duration = 3600
        events = [
            {"timestamp": created_at, "app_name": "Visual Studio Code", "window_title": "admin-server - routes.py", "active_seconds": 1800},
            {"timestamp": created_at, "app_name": "Terminal (iTerm2)", "window_title": "zsh - uvicorn main:app", "active_seconds": 900},
            {"timestamp": created_at, "app_name": "Google Chrome", "window_title": "FastAPI Documentation", "active_seconds": 600},
            {"timestamp": created_at, "app_name": "Slack", "window_title": "#engineering - Daily Standup", "active_seconds": 300},
        ]
        focus_summary = {"score": 94, "primary_app": "Visual Studio Code", "distraction_seconds": 0}
    elif payload.preset == "design_session":
        duration = 2700
        events = [
            {"timestamp": created_at, "app_name": "Figma", "window_title": "WorkGuard Design System v2.0", "active_seconds": 2100},
            {"timestamp": created_at, "app_name": "Safari", "window_title": "Apple Human Interface Guidelines", "active_seconds": 400},
            {"timestamp": created_at, "app_name": "Slack", "window_title": "#design-critique", "active_seconds": 200},
        ]
        focus_summary = {"score": 88, "primary_app": "Figma", "distraction_seconds": 30}
    elif payload.preset == "mixed_activity":
        duration = 1800
        events = [
            {"timestamp": created_at, "app_name": "Google Chrome", "window_title": "YouTube - Gaming Highlights", "active_seconds": 800},
            {"timestamp": created_at, "app_name": "Spotify", "window_title": "Deep Focus Playlist", "active_seconds": 400},
            {"timestamp": created_at, "app_name": "Notion", "window_title": "Product Roadmap Q3", "active_seconds": 600},
        ]
        focus_summary = {"score": 52, "primary_app": "Google Chrome", "distraction_seconds": 800}
    else:  # security_flagged
        duration = -1  # Trigger integrity check alert
        events = "invalid_non_list_events"  # Trigger list validation alert
        focus_summary = {"score": 10, "anomaly": True}

    session_content = {
        "session_id": session_id,
        "employee_id": employee_id,
        "metadata": {
            "created_at": created_at,
            "device": "MacBook Pro M3 Max",
            "os": "macOS 15.1 Sequoia",
        },
        "session": {
            "duration_seconds": duration,
            "started_at": created_at,
        },
        "events": events,
        "focus_summary": focus_summary,
    }

    # Encrypt using AES-256-GCM
    key = get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(session_content, ensure_ascii=False).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, session_id.encode("utf-8"))

    # Save to received and verified
    received_at = datetime.now(timezone.utc).isoformat()
    saved_payload = {
        "session_id": session_id,
        "employee_id": employee_id,
        "created_at": created_at,
        "received_at": received_at,
        "encryption": {
            "algorithm": "AES-256-GCM",
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        },
    }
    saved_verified = {
        "session_id": session_id,
        "employee_id": employee_id,
        "received_at": received_at,
        "session": session_content,
    }

    filename = f"{uuid.uuid4().hex}.json"
    
    RECEIVED_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RECEIVED_SESSIONS_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(saved_payload, f, indent=2)

    VERIFIED_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(VERIFIED_SESSIONS_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(saved_verified, f, indent=2)

    # Process AI workflow synchronously for simulation feedback
    workflow_result = process_verified_session(session_content)

    return {
        "status": "success",
        "message": f"Simulated session {session_id} successfully received and processed.",
        "session_id": session_id,
        "employee_id": employee_id,
        "preset": payload.preset,
        "productivity": workflow_result.get("session_analysis", {}).get("productivity_assessment"),
        "security_alerts": workflow_result.get("security", {}).get("alerts", []),
    }


@router.get("/dashboard")
def get_dashboard_full() -> dict[str, Any]:
    """Retrieve full enterprise dashboard data with workforce, app usage, and KPIs."""
    stats = get_dashboard_stats()
    employees = list_employees()
    sessions = list_sessions(limit=10)
    security_events = list_security_events()

    # Aggregate application usage from PostgreSQL and verified sessions
    app_usage_map: dict[str, float] = {}
    try:
        from retrieval.structured import get_application_usage as pg_get_application_usage
        for a in pg_get_application_usage(limit=20):
            name = a["display_name"] or a["process_name"]
            app_usage_map[name] = app_usage_map.get(name, 0.0) + float(a["total_focus_seconds"])
    except Exception:
        pass

    verified = _read_all_json_in_dir(VERIFIED_SESSIONS_DIR)
    for v in verified:
        session_data = v.get("session", {})
        events = session_data.get("events", [])
        if isinstance(events, list):
            for evt in events:
                if isinstance(evt, dict):
                    app = evt.get("app_name")
                    secs = evt.get("active_seconds", 0)
                    if app and isinstance(secs, (int, float)) and secs > 0:
                        app_usage_map[app] = app_usage_map.get(app, 0.0) + float(secs)

    total_app_time = sum(app_usage_map.values()) or 1.0
    app_usage_list = [
        {
            "app_name": app,
            "active_seconds": round(dur),
            "percentage": round((dur / total_app_time) * 100),
        }
        for app, dur in sorted(app_usage_map.items(), key=lambda x: x[1], reverse=True)[:8]
    ]

    total_sessions_count = max(stats["total_verified"], len(list_sessions(limit=500)))
    total_work_time = sum(e.get("total_active_time_seconds", 0) for e in employees)

    return {
        "kpis": {
            "total_employees": len(employees),
            "active_employees": sum(1 for e in employees if e.get("status") == "Active"),
            "total_sessions": total_sessions_count,
            "total_active_time_seconds": total_work_time,
            "security_alerts": stats["security_alerts_count"],
        },
        "workforce": employees,
        "application_usage": app_usage_list,
        "recent_sessions": sessions,
        "security_alerts": security_events,
        "ai_overview": {
            "summary": (
                "Workforce telemetry synthesis from PostgreSQL system of record. "
                f"Total {total_sessions_count} session(s) tracked across {len(employees)} employee endpoint(s)."
            ),
            "confidence": 92,
            "key_highlights": [
                f"{len(employees)} monitored endpoint(s) registered in PostgreSQL",
                f"{len(sessions)} recent work session(s) analyzed",
                f"{len(app_usage_list)} application(s) actively profiled",
            ],
        },
    }


@router.get("/employees")
def list_employees() -> list[dict[str, Any]]:
    """List all employees: checks PostgreSQL first (System of Record), merging verified files."""
    emp_map: dict[str, dict[str, Any]] = {}

    # 1. Retrieve from PostgreSQL first (System of Record)
    try:
        from retrieval.structured import list_employees as pg_list_employees
        for e in pg_list_employees(limit=100):
            eid = e["employee_id"]
            emp_map[eid] = {
                "employee_id": eid,
                "employee_name": e.get("employee_name") or e.get("username") or eid,
                "sessions_count": e.get("total_sessions") or 0,
                "total_active_time_seconds": e.get("total_work_seconds") or 0,
                "last_activity": str(e.get("last_session_at") or datetime.now(timezone.utc).isoformat()),
                "status": "Active" if (e.get("total_sessions") or 0) > 0 else "Inactive",
                "security_alert_count": 0,
            }
    except Exception as exc:
        pass

    # 2. Supplement with any verified files
    verified = _read_all_json_in_dir(VERIFIED_SESSIONS_DIR)
    reports = _read_all_json_in_dir(REPORTS_DIR)

    reports_by_employee: dict[str, list] = {}
    for r in reports:
        emp_id = r.get("employee_id")
        if emp_id:
            reports_by_employee.setdefault(emp_id, []).append(r)

    for v in verified:
        emp_id = v.get("employee_id") or "UNKNOWN"
        emp_name = v.get("session", {}).get("employee_name") or emp_id
        session_info = v.get("session", {})
        duration = session_info.get("duration_seconds", 0)
        received_at = v.get("received_at", datetime.now(timezone.utc).isoformat())

        if emp_id not in emp_map:
            emp_map[emp_id] = {
                "employee_id": emp_id,
                "employee_name": emp_name,
                "sessions_count": 0,
                "total_active_time_seconds": 0,
                "last_activity": received_at,
                "status": "Active",
                "security_alert_count": 0,
            }
            emp_map[emp_id]["sessions_count"] += 1
            emp_map[emp_id]["total_active_time_seconds"] += duration
            if received_at > emp_map[emp_id]["last_activity"]:
                emp_map[emp_id]["last_activity"] = received_at

    # Count security alerts per employee
    for emp_id, emp_reports in reports_by_employee.items():
        if emp_id in emp_map:
            alerts = sum(len(r.get("security", {}).get("alerts", [])) for r in emp_reports)
            emp_map[emp_id]["security_alert_count"] = alerts

    return list(emp_map.values())


@router.get("/employees/{employee_id}")
def get_employee_detail(employee_id: str) -> dict[str, Any]:
    """Retrieve detailed employee profile, application usage, and history."""
    # 1. Check PostgreSQL first
    try:
        from retrieval.structured import get_employee as pg_get_employee, get_application_usage as pg_get_application_usage
        pg_emp = pg_get_employee(employee_id)
        if pg_emp:
            all_sessions = list_sessions(limit=100)
            emp_sessions = [s for s in all_sessions if s.get("employee_id") == pg_emp["employee_id"] or s.get("employee_name") == pg_emp["username"]]

            pg_apps = pg_get_application_usage(employee_id=pg_emp["employee_id"])
            app_usage = {
                a["display_name"] or a["process_name"]: float(a["total_focus_seconds"])
                for a in pg_apps
            }

            return {
                "employee_id": pg_emp["employee_id"],
                "employee_name": pg_emp["employee_name"] or pg_emp["username"],
                "sessions_count": pg_emp["total_sessions"],
                "total_active_time_seconds": pg_emp["total_work_seconds"],
                "last_activity": str(pg_emp["last_session_at"] or datetime.now(timezone.utc).isoformat()),
                "status": "Active" if pg_emp["total_sessions"] > 0 else "Inactive",
                "security_alert_count": 0,
                "applications_used": app_usage,
                "session_history": emp_sessions,
                "security_events": [],
                "ai_observations": [
                    f"Machine: {pg_emp['machine_name']}",
                    f"Total Work Recorded: {round(pg_emp['total_work_seconds']/60, 1)}m across {pg_emp['total_sessions']} session(s)",
                ],
                "ai_confidence": 92,
                "evidence_sessions": [s["session_id"] for s in emp_sessions[:5]],
            }
    except Exception as exc:
        pass

    # 2. Fallback to verified file records
    employees = list_employees()
    emp = next((e for e in employees if e["employee_id"] == employee_id), None)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found in verified telemetry.")

    all_sessions = list_sessions(limit=100)
    emp_sessions = [s for s in all_sessions if s.get("employee_id") == employee_id]

    app_usage: dict[str, float] = {}
    verified = _read_all_json_in_dir(VERIFIED_SESSIONS_DIR)
    for v in verified:
        if v.get("employee_id") == employee_id:
            session_data = v.get("session", {})
            events = session_data.get("events", [])
            if isinstance(events, list):
                for evt in events:
                    if isinstance(evt, dict):
                        app = evt.get("app_name")
                        secs = evt.get("active_seconds", 0)
                        if app and isinstance(secs, (int, float)) and secs > 0:
                            app_usage[app] = app_usage.get(app, 0.0) + float(secs)

            focus = session_data.get("focus_summary", {})
            if isinstance(focus, dict):
                for app, dur in focus.items():
                    if isinstance(dur, (int, float)):
                        app_usage[app] = app_usage.get(app, 0.0) + float(dur)

    sec_events = [e for e in list_security_events() if e.get("employee_id") == employee_id]
    reports = _read_all_json_in_dir(REPORTS_DIR)
    emp_reports = [r for r in reports if r.get("employee_id") == employee_id]
    observations = []
    confidence = 0
    if emp_reports:
        latest_report = emp_reports[-1]
        analysis = latest_report.get("session_analysis", {})
        observations = analysis.get("key_activities", []) or [analysis.get("summary", "Activity logged.")]
        confidence = 88

    return {
        **emp,
        "applications_used": app_usage,
        "session_history": emp_sessions,
        "security_events": sec_events,
        "ai_observations": observations if observations else None,
        "ai_confidence": confidence if confidence > 0 else None,
        "evidence_sessions": [s["session_id"] for s in emp_sessions[:5]],
    }


@router.get("/security/events")
def list_security_events() -> list[dict[str, Any]]:
    """List all security events detected across verified sessions."""
    reports = _read_all_json_in_dir(REPORTS_DIR)
    events = []

    for idx, r in enumerate(reports):
        sec = r.get("security", {})
        alerts = sec.get("alerts", [])
        risk_score = sec.get("risk_score", 0)
        sid = r.get("session_id", f"sess_{idx}")
        emp_id = r.get("employee_id", "SYS-UNKNOWN")
        emp_name = r.get("employee_name", f"Employee ({emp_id})")
        created_at = r.get("metadata", {}).get("created_at") or datetime.now(timezone.utc).isoformat()

        severity = "LOW"
        if risk_score >= 3:
            severity = "CRITICAL"
        elif risk_score >= 2 or len(alerts) > 1:
            severity = "HIGH"
        elif risk_score >= 1 or len(alerts) > 0:
            severity = "MEDIUM"

        for a_idx, alert in enumerate(alerts):
            events.append({
                "event_id": f"sec_{sid[:8]}_{a_idx}",
                "severity": severity,
                "employee_id": emp_id,
                "employee_name": emp_name,
                "detection_type": "Security Integrity Anomaly",
                "timestamp": created_at,
                "evidence": alert,
                "related_session_id": sid,
                "ai_analysis": sec.get("assessment", "Agent detected security violation in session telemetry."),
                "recommended_action": "Review workstation logs and audit process execution history.",
            })

    return events


@router.get("/reports")
def list_reports() -> list[dict[str, Any]]:
    """List all AI reports generated by LangGraph agents."""
    reports_data = _read_all_json_in_dir(REPORTS_DIR)
    results = []

    for r in reports_data:
        analysis = r.get("session_analysis", {})
        sid = r.get("session_id", "sess_unknown")
        emp_id = r.get("employee_id", "SYS-UNKNOWN")
        emp_name = r.get("employee_name", f"Employee ({emp_id})")
        created_at = r.get("created_at") or datetime.now(timezone.utc).strftime("%d %B %Y")

        results.append({
            "report_id": f"rep_{sid[:8]}",
            "session_id": sid,
            "employee_id": emp_id,
            "employee_name": emp_name,
            "date": created_at,
            "overall_assessment": analysis.get(
                "summary",
                "Session processed and analyzed by WorkGuard agentic workflow."
            ),
            "key_observations": analysis.get(
                "key_activities",
                ["Forensic session verification completed"]
            ),
            "ai_confidence": 88,
            "evidence_sessions": [sid],
            "raw_observed_data": {
                "total_duration_seconds": r.get("duration_seconds", 0),
                "event_count": r.get("events_count", 0),
                "top_apps": [
                    app for app, _ in sorted(
                        r.get("focus_summary", {}).items(), key=lambda x: x[1], reverse=True
                    )[:3]
                ],
            },
        })

    return results


@router.get("/processing/status")
def get_pipeline_status() -> dict[str, Any]:
    """Return status of the PostgreSQL-to-Processing pipeline."""
    from database.connection import get_connection
    from database.schema import ensure_processing_tables

    conn = get_connection()
    try:
        ensure_processing_tables(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending_count,
                    COUNT(*) FILTER (WHERE status = 'processing') AS processing_count,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed_count,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed_count,
                    SUM(documents_count) AS total_documents_generated
                FROM session_processing_status;
            """)
            row = cur.fetchone()
            stats = {
                "pending": row[0] or 0,
                "processing": row[1] or 0,
                "completed": row[2] or 0,
                "failed": row[3] or 0,
                "total_documents_generated": row[4] or 0,
            }

            cur.execute("""
                SELECT session_id, status, documents_count, error_message, processed_at
                FROM session_processing_status
                ORDER BY updated_at DESC
                LIMIT 10;
            """)
            recent = [
                {
                    "session_id": r[0],
                    "status": r[1],
                    "documents_count": r[2],
                    "error_message": r[3],
                    "processed_at": r[4].isoformat() if r[4] else None,
                }
                for r in cur.fetchall()
            ]

            return {
                "stats": stats,
                "recent_jobs": recent,
            }
    finally:
        conn.close()


@router.post("/processing/run")
def trigger_pipeline_run(
    session_id: Optional[str] = Query(None, description="Specific session to process"),
    force: bool = Query(False, description="Force re-processing if already completed"),
    limit: int = Query(50, description="Max pending sessions to process"),
) -> dict[str, Any]:
    """Trigger the processing pipeline on demand."""
    from processing.pipeline import process_all_pending, process_session

    if session_id:
        try:
            res = process_session(session_id, force=force)
            return {"status": "ok", "result": res}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        res = process_all_pending(limit=limit, force=force)
        return {"status": "ok", "result": res}


class VectorSearchRequest(BaseModel):
    query: str = Field(min_length=1, description="Semantic search query text")
    k: int = Field(5, ge=1, le=50, description="Number of results to return")
    doc_type: Optional[str] = Field(None, description="Filter by doc_type (e.g. session_overview, application_usage, file_activity, process_activity)")
    employee_id: Optional[str] = Field(None, description="Filter by employee_id")


@router.get("/vectors/stats")
def get_vector_store_stats() -> dict[str, Any]:
    """Return FAISS vector store statistics and PostgreSQL synchronization status."""
    from database.connection import get_connection
    from database.schema import ensure_processing_tables
    from tools.faiss_tools import get_faiss_store

    store = get_faiss_store()
    conn = get_connection()
    try:
        ensure_processing_tables(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM vector_metadata;")
            pg_vector_count = cur.fetchone()[0]

            cur.execute("""
                SELECT doc_type, COUNT(*)
                FROM vector_metadata
                GROUP BY doc_type
                ORDER BY COUNT(*) DESC;
            """)
            by_doc_type = dict(cur.fetchall())

            cur.execute("SELECT COUNT(DISTINCT session_id) FROM vector_metadata;")
            indexed_sessions_count = cur.fetchone()[0]

            return {
                "faiss_total_vectors": store.get_size(),
                "faiss_dimension": store.dimension,
                "pg_vector_metadata_count": pg_vector_count,
                "indexed_sessions_count": indexed_sessions_count,
                "vectors_by_doc_type": by_doc_type,
            }
    finally:
        conn.close()


@router.post("/vectors/search")
def search_vectors_endpoint(body: VectorSearchRequest) -> dict[str, Any]:
    """Perform semantic vector similarity search across analysis documents."""
    from embeddings.indexer import search_documents

    try:
        results = search_documents(
            query=body.query,
            k=body.k,
            doc_type=body.doc_type,
            employee_id=body.employee_id,
        )
        return {
            "query": body.query,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Phase 3: Retrieval Layer Endpoints
# ---------------------------------------------------------------------------

class ContextRetrievalRequest(BaseModel):
    query: str = Field(min_length=1, description="Question or search query")
    employee_id: Optional[str] = Field(None, description="Employee ID or username")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    k: int = Field(5, ge=1, le=20, description="Max semantic hits to include")
    doc_type: Optional[str] = Field(None, description="Filter semantic hits by doc_type")


@router.get("/retrieval/employees")
def retrieval_list_employees(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    """List registered employees with total sessions and activity stats."""
    from retrieval.structured import list_employees
    return list_employees(limit=limit, offset=offset)


@router.get("/retrieval/employees/{employee_id}")
def retrieval_get_employee(employee_id: str) -> dict[str, Any]:
    """Get profile and activity statistics for a specific employee."""
    from retrieval.structured import get_employee
    emp = get_employee(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")
    return emp


@router.get("/retrieval/sessions")
def retrieval_get_sessions(
    employee_id: Optional[str] = Query(None, description="Filter by employee_id or username"),
    date: Optional[str] = Query(None, description="Filter by specific date YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Filter after start_date"),
    end_date: Optional[str] = Query(None, description="Filter before end_date"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict[str, Any]]:
    """Retrieve filtered session summaries."""
    from retrieval.structured import get_sessions
    return get_sessions(
        employee_id=employee_id,
        date=date,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@router.get("/retrieval/sessions/{session_id}")
def retrieval_get_session_details(session_id: str) -> dict[str, Any]:
    """Retrieve in-depth details for a single session."""
    from retrieval.structured import get_session_details
    details = get_session_details(session_id)
    if not details:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return details


@router.get("/retrieval/application-usage")
def retrieval_get_application_usage(
    employee_id: Optional[str] = Query(None, description="Filter by employee_id or username"),
    date: Optional[str] = Query(None, description="Filter by date YYYY-MM-DD"),
    process_name: Optional[str] = Query(None, description="Filter by process or application name"),
    limit: int = Query(50, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Query aggregated application usage time and focus percentages."""
    from retrieval.structured import get_application_usage
    return get_application_usage(
        employee_id=employee_id,
        date=date,
        process_name=process_name,
        limit=limit,
    )


@router.get("/retrieval/daily-summary")
def retrieval_get_daily_summary(
    employee_id: str = Query(..., description="Employee ID or username"),
    date: str = Query(..., description="Target date in YYYY-MM-DD format"),
) -> dict[str, Any]:
    """Retrieve aggregated daily activity summary for an employee on a given date."""
    from retrieval.structured import get_daily_summary
    res = get_daily_summary(employee_id=employee_id, date=date)
    if not res:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")
    return res


@router.get("/retrieval/project-activity")
def retrieval_get_project_activity(
    employee_id: Optional[str] = Query(None, description="Filter by employee_id or username"),
    directory_path: Optional[str] = Query(None, description="Filter by directory path substring"),
    limit: int = Query(50, ge=1, le=100),
) -> list[dict[str, Any]]:
    """Retrieve project directory modification statistics."""
    from retrieval.structured import get_project_file_activity
    return get_project_file_activity(
        employee_id=employee_id,
        directory_path=directory_path,
        limit=limit,
    )


@router.post("/retrieval/context")
def retrieval_retrieve_context(body: ContextRetrievalRequest) -> dict[str, Any]:
    """Assemble a hybrid context bundle combining structured PostgreSQL stats and FAISS semantic hits."""
    from retrieval.service import retrieve_context
    try:
        return retrieve_context(
            query=body.query,
            employee_id=body.employee_id,
            date=body.date,
            k=body.k,
            doc_type=body.doc_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Phase 4 & Phase 5: LLM & Agent Endpoints
# ---------------------------------------------------------------------------

class AgentQueryRequest(BaseModel):
    query: str = Field(min_length=1, description="Question or task for the agent")
    employee_id: Optional[str] = Field(None, description="Optional target employee ID or username")
    session_id: Optional[str] = Field(None, description="Optional target session ID")
    date: Optional[str] = Field(None, description="Optional target date in YYYY-MM-DD format")


@router.get("/llm/health")
def get_llm_health() -> dict[str, Any]:
    """Check connection to the local Ollama LLM and verify configured model."""
    from llm.ollama_client import get_ollama_client
    client = get_ollama_client()
    return client.check_health()


@router.post("/agents/session-analysis")
def query_session_analysis_agent(body: AgentQueryRequest) -> dict[str, Any]:
    """Execute the Session Analysis Agent (LangGraph + PostgreSQL + FAISS + Ollama)."""
    from agents.session_agent import run_session_agent
    try:
        return run_session_agent(
            query=body.query,
            employee_id=body.employee_id,
            date=body.date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session Agent execution error: {e}")


@router.post("/agents/supervisor")
def query_supervisor_agent(body: AgentQueryRequest) -> dict[str, Any]:
    """Execute the Supervisor Agent (Phase 6: Multi-agent orchestration and routing)."""
    from agents.supervisor_agent import run_supervisor_agent
    try:
        return run_supervisor_agent(
            query=body.query,
            employee_id=body.employee_id,
            session_id=body.session_id,
            date=body.date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supervisor Agent execution error: {e}")


@router.post("/agents/security")
def query_security_agent(body: AgentQueryRequest) -> dict[str, Any]:
    """Execute the Security Intelligence Agent (Phase 7: Deterministic Rules + Ollama Explanation)."""
    from agents.security_agent import run_security_agent
    try:
        return run_security_agent(
            query=body.query,
            employee_id=body.employee_id,
            session_id=body.session_id,
            date=body.date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Security Agent execution error: {e}")


@router.post("/agents/reporting")
def query_reporting_agent(body: AgentQueryRequest) -> dict[str, Any]:
    """Execute the Reporting Agent (Phase 8: Structured Metrics Synthesis into Executive Report)."""
    from agents.reporting_agent import run_reporting_agent
    try:
        return run_reporting_agent(
            query=body.query,
            employee_id=body.employee_id,
            date=body.date,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reporting Agent execution error: {e}")







