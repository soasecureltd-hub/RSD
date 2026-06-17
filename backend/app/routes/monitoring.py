"""
Real-time monitoring routes

- Camera registration and management
- WebSocket for real-time alerts and risk scores
- Alert management
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import base64
import cv2
import numpy as np
import logging
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image

from app.db import get_db
from app.services.camera_manager import camera_manager
from app.dependencies import get_current_user, authenticate_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# ============ Schemas ============

class CameraRegisterRequest(BaseModel):
    camera_id: str
    name: str
    source: str  # RTSP URL or "0" for webcam
    location: Optional[str] = ""


class CameraUpdateRequest(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None


class MonitoringSettingsRequest(BaseModel):
    assessment_interval: Optional[int] = None  # seconds
    frame_sample_interval: Optional[int] = None  # seconds
    risk_threshold: Optional[float] = None


class PushFrameRequest(BaseModel):
    frame_data: str  # base64-encoded JPEG from browser webcam


# ============ Camera Management ============

@router.post("/cameras", status_code=201)
async def register_camera(
    request: CameraRegisterRequest,
    current_user=Depends(get_current_user)
):
    """Register a new camera for monitoring"""
    try:
        stream = camera_manager.register_camera(
            camera_id=request.camera_id,
            name=request.name,
            source=request.source,
            location=request.location
        )
        return {
            "message": f"Camera '{request.name}' registered successfully",
            "camera_id": stream.camera_id,
            "status": stream.status.value
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/cameras/{camera_id}")
async def remove_camera(camera_id: str, current_user=Depends(get_current_user)):
    """Remove a registered camera"""
    try:
        camera_manager.remove_camera(camera_id)
        return {"message": f"Camera '{camera_id}' removed"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/cameras")
async def list_cameras(current_user=Depends(get_current_user)):
    """Get status of all registered cameras"""
    return {
        "cameras": camera_manager.get_all_cameras_status(),
        "total": len(camera_manager.cameras)
    }


@router.get("/cameras/{camera_id}")
async def get_camera(camera_id: str, current_user=Depends(get_current_user)):
    """Get status of a specific camera"""
    try:
        return camera_manager.get_camera_status(camera_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============ Monitoring Control ============

@router.post("/cameras/{camera_id}/start")
async def start_monitoring(camera_id: str, current_user=Depends(get_current_user)):
    """Start real-time monitoring for a camera"""
    try:
        await camera_manager.start_monitoring(camera_id)
        return {"message": f"Monitoring started for '{camera_id}'", "status": "monitoring"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/cameras/{camera_id}/stop")
async def stop_monitoring(camera_id: str, current_user=Depends(get_current_user)):
    """Stop monitoring a camera"""
    try:
        await camera_manager.stop_monitoring(camera_id)
        return {"message": f"Monitoring stopped for '{camera_id}'", "status": "idle"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============ Browser Camera Frame Push ============

@router.post("/cameras/{camera_id}/push-frame")
async def push_frame(
    camera_id: str,
    request: PushFrameRequest,
    current_user=Depends(get_current_user),
):
    """
    Receive a webcam frame from the browser for a browser-source camera.
    Runs the full analysis pipeline (health, YOLO, zone intrusion, risk scoring).
    """
    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")

    stream = camera_manager.cameras[camera_id]
    if stream.status.value != "monitoring":
        raise HTTPException(status_code=400, detail="Camera is not in monitoring state")

    try:
        b64 = request.frame_data
        b64 += "=" * ((4 - len(b64) % 4) % 4)
        frame_bytes = base64.b64decode(b64)
        image = Image.open(BytesIO(frame_bytes))
        frame = np.array(image)
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid frame data")

    # Update stream state
    stream.latest_frame = frame.copy()
    stream.last_frame_time = datetime.now(timezone.utc)
    stream.frame_count += 1

    # Run full analysis in thread pool
    analysis = await asyncio.to_thread(stream.monitor.analyze_frame, frame)

    # Record zone intrusion events into the facility event log
    for intrusion in analysis.get("zone_intrusions", []):
        camera_manager.record_event(camera_id, "zone_intrusion", "high", intrusion)

    # Check for immediate threats (records threat/crowd/after-hours events internally)
    await camera_manager._check_immediate_threats(camera_id, analysis)

    # Periodic per-camera risk assessment
    now = datetime.now(timezone.utc)
    last = stream.browser_last_assessment
    elapsed = (now - last).total_seconds() if last else camera_manager.assessment_interval + 1
    if elapsed >= camera_manager.assessment_interval:
        await camera_manager._compute_risk_assessment(camera_id)
        stream.browser_last_assessment = now

    # Update facility-level live risk (debounced to once per 60s)
    await camera_manager.maybe_update_facility_risk()

    return {
        "health_score": analysis.get("health_score"),
        "object_counts": analysis.get("object_counts", {}),
        "zone_intrusions": analysis.get("zone_intrusions", []),
        "issues": analysis.get("issues", []),
    }


# ============ Facility Live Risk ============

@router.get("/live-risk")
async def get_live_risk(current_user=Depends(get_current_user)):
    """
    Return the latest facility-level live risk score aggregated across all cameras.
    If no computation has run yet, computes it on-demand.
    """
    if camera_manager.live_risk is None:
        risk = camera_manager.compute_facility_live_risk()
        if risk:
            camera_manager.live_risk = risk
    return camera_manager.live_risk or {"message": "No cameras registered yet"}


@router.get("/live-risk/history")
async def get_live_risk_history(
    limit: int = 60,
    current_user=Depends(get_current_user),
):
    """Return time-series of facility risk scores (most recent `limit` entries)."""
    history = list(camera_manager.live_risk_history)[-limit:]
    return {"history": history, "total": len(history)}


# ============ Live Video Feed ============

async def _generate_mjpeg(camera_id: str):
    """Generator that yields MJPEG frames from the latest stored frame"""
    stream = camera_manager.cameras.get(camera_id)
    if not stream:
        return

    while True:
        if stream.latest_frame is None:
            await asyncio.sleep(0.5)
            continue

        frame = stream.latest_frame.copy()

        # Draw detections on frame if available
        if stream.monitor and stream.monitor.detected_objects:
            for det in stream.monitor.detected_objects:
                box = det.get("box", [])
                if len(box) == 4:
                    x1, y1, x2, y2 = [int(v) for v in box]
                    cls_name = det.get("class", "")
                    conf = det.get("confidence", 0)

                    # Color: red for threats, green for people, blue for others
                    threat_objects = {"knife", "baseball bat", "scissors", "fire"}
                    if cls_name in threat_objects:
                        color = (0, 0, 255)  # Red
                    elif cls_name == "person":
                        color = (0, 255, 0)  # Green
                    else:
                        color = (255, 180, 0)  # Blue

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f"{cls_name} {conf:.0%}"
                    cv2.putText(frame, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Add overlay info
        if stream.last_risk_assessment:
            score = stream.last_risk_assessment.get("overall_score", 0)
            level = stream.last_risk_assessment.get("risk_level", "N/A")
            overlay_text = f"Risk: {score:.1f} ({level})"
            cv2.putText(frame, overlay_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        # Add camera name
        cv2.putText(frame, stream.name, (10, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )

        # ~15 FPS for the stream
        await asyncio.sleep(0.066)


@router.get("/cameras/{camera_id}/feed")
async def camera_feed(camera_id: str, token: str = Query(...)):
    """
    Live MJPEG video feed from a camera.
    Shows detections overlaid on the live stream.

    Auth is supplied via a `?token=<jwt>` query parameter because <img>/MJPEG
    requests cannot set an Authorization header.
    """
    db = next(get_db())
    try:
        if authenticate_token(token, db) is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    finally:
        db.close()

    if camera_id not in camera_manager.cameras:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")

    stream = camera_manager.cameras[camera_id]
    if stream.status.value != "monitoring":
        raise HTTPException(status_code=400, detail="Camera is not actively monitoring")

    return StreamingResponse(
        _generate_mjpeg(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ============ Alerts ============

@router.get("/alerts")
async def get_alerts(
    limit: int = 50,
    severity: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """Get recent alerts"""
    return {
        "alerts": camera_manager.get_alerts(limit=limit, severity=severity),
        "total": len(camera_manager.alerts)
    }


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, current_user=Depends(get_current_user)):
    """Acknowledge an alert"""
    if camera_manager.acknowledge_alert(alert_id):
        return {"message": "Alert acknowledged"}
    raise HTTPException(status_code=404, detail="Alert not found")


# ============ Settings ============

@router.get("/settings")
async def get_settings(current_user=Depends(get_current_user)):
    """Get current monitoring settings"""
    return {
        "assessment_interval": camera_manager.assessment_interval,
        "frame_sample_interval": camera_manager.frame_sample_interval,
        "risk_threshold": camera_manager.risk_threshold
    }


@router.put("/settings")
async def update_settings(
    request: MonitoringSettingsRequest,
    current_user=Depends(get_current_user)
):
    """Update monitoring settings"""
    if request.assessment_interval is not None:
        camera_manager.assessment_interval = request.assessment_interval
    if request.frame_sample_interval is not None:
        camera_manager.frame_sample_interval = request.frame_sample_interval
    if request.risk_threshold is not None:
        camera_manager.risk_threshold = request.risk_threshold

    return {
        "message": "Settings updated",
        "assessment_interval": camera_manager.assessment_interval,
        "frame_sample_interval": camera_manager.frame_sample_interval,
        "risk_threshold": camera_manager.risk_threshold
    }


# ============ WebSocket ============

@router.websocket("/ws")
async def monitoring_websocket(websocket: WebSocket, token: str = Query(default="")):
    """
    WebSocket endpoint for real-time monitoring updates.

    Auth via `?token=<jwt>` query parameter. Unauthenticated connections are
    rejected before any data is sent.

    Clients receive:
    - risk_assessment: periodic risk score updates
    - alert: real-time security alerts
    - camera_status: camera state changes
    """
    db = next(get_db())
    try:
        user = authenticate_token(token, db)
    finally:
        db.close()
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    camera_manager.add_websocket_client(websocket)
    logger.info("WebSocket client connected: %s", user.email)

    try:
        # Send current state on connect
        await websocket.send_json({
            "type": "initial_state",
            "data": {
                "cameras": camera_manager.get_all_cameras_status(),
                "alerts": camera_manager.get_alerts(limit=20),
                "settings": {
                    "assessment_interval": camera_manager.assessment_interval,
                    "frame_sample_interval": camera_manager.frame_sample_interval,
                    "risk_threshold": camera_manager.risk_threshold
                }
            }
        })

        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_json()
            # Handle client commands
            if data.get("action") == "acknowledge_alert":
                alert_id = data.get("alert_id")
                if alert_id:
                    camera_manager.acknowledge_alert(alert_id)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        camera_manager.remove_websocket_client(websocket)
