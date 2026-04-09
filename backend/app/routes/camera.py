"""
Camera health monitoring routes
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app import schemas, crud
from app.db import get_db
from app.services.camera_service import CameraHealthMonitor
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import base64

router = APIRouter(prefix="/api/camera", tags=["camera"])

# Store monitor instances per camera
monitors = {}


def get_monitor(camera_id: str = "CAM-DEFAULT") -> CameraHealthMonitor:
    """Get or create a monitor for a camera"""
    if camera_id not in monitors:
        monitors[camera_id] = CameraHealthMonitor(camera_id)
    return monitors[camera_id]


@router.post("/analyze", response_model=schemas.CameraHealthResponse)
async def analyze_frame(
    camera_input: schemas.CameraHealthInput,
    db: Session = Depends(get_db)
):
    """
    Analyze a camera frame for health metrics
    
    Args:
        camera_input: Camera ID and base64-encoded frame data
    """
    try:
        # Get or create monitor
        monitor = get_monitor(camera_input.camera_id)
        
        # Decode base64 frame
        frame_bytes = base64.b64decode(camera_input.frame_data)
        image = Image.open(BytesIO(frame_bytes))
        frame = np.array(image)
        
        # Convert RGB to BGR for OpenCV
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        # Analyze frame
        health_data = monitor.analyze_frame(frame)
        print(f"Camera analyze response detection_enabled={health_data.get('detection_enabled')} detections={len(health_data.get('detections', []))} object_counts={health_data.get('object_counts')}")
        
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
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/health/{camera_id}", response_model=schemas.CameraHealthResponse)
def get_camera_status(camera_id: str = "CAM-DEFAULT"):
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
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/{camera_id}")
def get_camera_history(
    camera_id: str,
    limit: int = 100,
    db: Session = Depends(get_db)
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
