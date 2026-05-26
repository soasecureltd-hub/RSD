"""
Real-time monitoring routes

- Camera registration and management
- WebSocket for real-time alerts and risk scores
- Alert management
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import cv2
import logging

from app.services.camera_manager import camera_manager
from app.dependencies import get_current_user

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
async def camera_feed(camera_id: str):
    """
    Live MJPEG video feed from a camera.
    Shows detections overlaid on the live stream.
    No auth required for stream (token would complicate <img> tags).
    """
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
async def monitoring_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time monitoring updates.

    Clients receive:
    - risk_assessment: periodic risk score updates
    - alert: real-time security alerts
    - camera_status: camera state changes
    """
    await websocket.accept()
    camera_manager.add_websocket_client(websocket)
    logger.info("WebSocket client connected")

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
