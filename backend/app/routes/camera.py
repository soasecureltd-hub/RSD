"""
Camera health monitoring routes
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from app import schemas, crud
from app.config import settings
from app.db import get_db
from app.dependencies import get_current_user
from app.services.camera_service import CameraHealthMonitor
import asyncio
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import base64

logger = logging.getLogger(__name__)

# Pillow refuses images above this many pixels (decompression-bomb guard).
Image.MAX_IMAGE_PIXELS = settings.MAX_FRAME_PIXELS

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/camera", tags=["camera"])

# Store monitor instances per camera
monitors = {}


def get_monitor(camera_id: str = "CAM-DEFAULT") -> CameraHealthMonitor:
    """Get or create a monitor for a camera"""
    if camera_id not in monitors:
        monitors[camera_id] = CameraHealthMonitor(camera_id)
    return monitors[camera_id]


@router.post("/analyze", response_model=schemas.CameraHealthResponse)
@limiter.limit(settings.RATE_LIMIT_CAMERA_ANALYZE)
async def analyze_frame(
    request: Request,
    camera_input: schemas.CameraHealthInput,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Analyze a camera frame for health metrics

    Args:
        camera_input: Camera ID and base64-encoded frame data
    """
    try:
        monitor = get_monitor(camera_input.camera_id)

        def _decode_and_analyze() -> dict:
            """Decode frame and run blocking CV analysis in a thread."""
            try:
                frame_bytes = base64.b64decode(camera_input.frame_data, validate=True)
            except Exception:
                raise ValueError("Invalid base64 frame data")
            if len(frame_bytes) > settings.MAX_FRAME_BYTES:
                raise ValueError("Frame exceeds maximum allowed size")
            try:
                image = Image.open(BytesIO(frame_bytes))
                image.verify()  # detect truncated/malformed images cheaply
                # verify() leaves the image unusable; reopen to actually read pixels
                image = Image.open(BytesIO(frame_bytes))
            except Image.DecompressionBombError:
                raise ValueError("Frame resolution exceeds allowed limit")
            except Exception:
                raise ValueError("Invalid or unsupported image data")
            frame = np.array(image)
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return monitor.analyze_frame(frame)

        # Run blocking OpenCV/YOLO work off the event-loop thread
        health_data = await asyncio.to_thread(_decode_and_analyze)
        logger.debug(
            "Camera analyze: detection_enabled=%s detections=%d object_counts=%s",
            health_data.get("detection_enabled"),
            len(health_data.get("detections", [])),
            health_data.get("object_counts"),
        )

        # Save to database
        crud.create_camera_health(db, camera_input.camera_id, health_data)

        # Format response
        return schemas.CameraHealthResponse(
            camera_id=health_data["camera_id"],
            health_score=health_data["health_score"],
            metrics=schemas.CameraMetrics(
                blur_score=health_data["metrics"]["blur_score"],
                brightness=health_data["metrics"]["brightness"],
                contrast=health_data["metrics"]["contrast"],
                noise_level=health_data["metrics"]["noise_level"],
                fps=health_data["metrics"]["fps"]
            ),
            issues=health_data["issues"],
            status=health_data["status"],
            timestamp=health_data["timestamp"],
            detections=health_data.get("detections", []),
            object_counts=health_data.get("object_counts", {}),
            detection_enabled=health_data.get("detection_enabled", False)
        )

    except ValueError as e:
        # Safe, client-facing validation messages (bad base64, oversized frame, etc.)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Frame analysis failed for camera %s", camera_input.camera_id)
        raise HTTPException(status_code=400, detail="Could not analyze frame")


@router.get("/health/{camera_id}", response_model=schemas.CameraHealthResponse)
def get_camera_status(
    camera_id: str = "CAM-DEFAULT",
    current_user=Depends(get_current_user),
):
    """Get current camera status"""
    try:
        monitor = get_monitor(camera_id)
        
        # Return empty frame analysis as current status
        empty_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        health_data = monitor.analyze_frame(empty_frame)
        
        return schemas.CameraHealthResponse(
            camera_id=health_data["camera_id"],
            health_score=health_data["health_score"],
            metrics=schemas.CameraMetrics(
                blur_score=health_data["metrics"].get("blur_score", 0),
                brightness=health_data["metrics"].get("brightness", 0),
                contrast=health_data["metrics"].get("contrast", 0),
                noise_level=health_data["metrics"].get("noise_level", 0),
                fps=health_data["metrics"].get("fps", 0)
            ),
            issues=health_data["issues"],
            status=health_data["status"],
            timestamp=health_data["timestamp"],
            detections=health_data.get("detections", []),
            object_counts=health_data.get("object_counts", {}),
            detection_enabled=health_data.get("detection_enabled", False)
        )

    except Exception:
        logger.exception("Failed to get camera status for %s", camera_id)
        raise HTTPException(status_code=400, detail="Could not get camera status")


@router.get("/history/{camera_id}")
def get_camera_history(
    camera_id: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get camera health history"""
    history = crud.get_camera_health_history(db, camera_id, limit=limit)
    return [
        {
            "id": h.id,
            "camera_id": h.camera_id,
            "health_score": h.health_score,
            "blur_score": h.blur_score,
            "brightness": h.brightness,
            "contrast": h.contrast,
            "noise_level": h.noise_level,
            "fps": h.fps,
            "issues": h.issues,
            "created_at": h.created_at
        }
        for h in history
    ]


@router.get("/risk-estimation/{camera_id}")
def get_camera_risk_estimation(
    camera_id: str,
    current_user=Depends(get_current_user),
):
    """Get risk estimation parameters derived from camera data"""
    try:
        monitor = get_monitor(camera_id)
        estimation = monitor.estimate_risk()

        if not estimation:
            return {"status": "error", "message": "Camera is offline or no data available"}

        return {"status": "success", "data": estimation}

    except Exception:
        logger.exception("Risk estimation failed for camera %s", camera_id)
        raise HTTPException(status_code=400, detail="Could not estimate risk")

