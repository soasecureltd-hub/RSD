"""
Real-time Camera Manager Service

Manages multiple camera streams, samples frames periodically,
aggregates observations into risk scores every assessment_interval,
and emits alerts when thresholds are breached.
"""
import asyncio
import cv2
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

from app.services.camera_service import CameraHealthMonitor
from app.services.risk_service import compute_scores, risk_level
from app.config import settings

logger = logging.getLogger(__name__)


class CameraStatus(str, Enum):
    IDLE = "idle"
    MONITORING = "monitoring"
    ERROR = "error"
    OFFLINE = "offline"


@dataclass
class CameraStream:
    """Represents a registered camera stream"""
    camera_id: str
    name: str
    source: str  # RTSP URL or device index (e.g., "0" for webcam)
    location: str = ""
    status: CameraStatus = CameraStatus.IDLE
    monitor: Optional[CameraHealthMonitor] = None
    capture: Optional[object] = None  # cv2.VideoCapture
    last_frame_time: Optional[datetime] = None
    last_risk_assessment: Optional[Dict] = None
    latest_frame: Optional[object] = None  # Most recent raw frame (np.ndarray)
    error_message: str = ""
    frame_count: int = 0
    browser_last_assessment: Optional[datetime] = None


@dataclass
class Alert:
    """Real-time alert"""
    id: str
    camera_id: str
    camera_name: str
    alert_type: str  # risk_spike, threat_detected, camera_offline, threshold_breach
    severity: str  # low, medium, high, critical
    message: str
    details: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False


class CameraManager:
    """
    Manages multiple camera streams for real-time risk assessment.

    - Registers cameras (RTSP or webcam)
    - Runs background analysis loops per camera
    - Aggregates detections into risk scores every assessment_interval
    - Broadcasts alerts via connected WebSocket clients
    """

    def __init__(self):
        self.cameras: Dict[str, CameraStream] = {}
        self.alerts: List[Alert] = []
        self.websocket_clients: List = []
        self.assessment_interval: int = 600  # 10 minutes in seconds
        self.frame_sample_interval: int = 5  # sample a frame every 5 seconds
        self.risk_threshold: float = 65.0  # alert if risk score exceeds this
        self._tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._alert_counter = 0

    def register_camera(
        self,
        camera_id: str,
        name: str,
        source: str,
        location: str = ""
    ) -> CameraStream:
        """Register a new camera for monitoring"""
        if camera_id in self.cameras:
            raise ValueError(f"Camera '{camera_id}' already registered")

        stream = CameraStream(
            camera_id=camera_id,
            name=name,
            source=source,
            location=location,
            monitor=CameraHealthMonitor(
                camera_id=camera_id,
                history_size=settings.CAMERA_HISTORY_SIZE,
                enable_detection=True
            )
        )
        self.cameras[camera_id] = stream
        logger.info(f"Camera registered: {camera_id} ({name}) - source: {source}")
        return stream

    def remove_camera(self, camera_id: str):
        """Remove a camera and stop its monitoring"""
        if camera_id not in self.cameras:
            raise ValueError(f"Camera '{camera_id}' not found")

        # Stop monitoring task if running
        if camera_id in self._tasks:
            self._tasks[camera_id].cancel()
            del self._tasks[camera_id]

        # Release capture
        stream = self.cameras[camera_id]
        if stream.capture is not None:
            stream.capture.release()

        del self.cameras[camera_id]
        logger.info(f"Camera removed: {camera_id}")

    async def start_monitoring(self, camera_id: str):
        """Start the monitoring loop for a camera"""
        if camera_id not in self.cameras:
            raise ValueError(f"Camera '{camera_id}' not found")

        stream = self.cameras[camera_id]

        # Browser cameras receive frames pushed from the client — no VideoCapture needed
        if stream.source == "browser":
            stream.status = CameraStatus.MONITORING
            stream.error_message = ""
            logger.info(f"Browser camera monitoring started: {camera_id}")
            return

        # Open video capture
        source = int(stream.source) if stream.source.isdigit() else stream.source
        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            stream.status = CameraStatus.ERROR
            stream.error_message = f"Cannot open video source: {stream.source}"
            await self._emit_alert(
                camera_id=camera_id,
                alert_type="camera_offline",
                severity="high",
                message=f"Camera '{stream.name}' cannot be opened",
                details={"source": stream.source, "error": stream.error_message}
            )
            return

        stream.capture = cap
        stream.status = CameraStatus.MONITORING
        stream.error_message = ""

        # Start background task
        task = asyncio.create_task(self._monitoring_loop(camera_id))
        self._tasks[camera_id] = task
        self._running = True
        logger.info(f"Monitoring started for camera: {camera_id}")

    async def stop_monitoring(self, camera_id: str):
        """Stop monitoring a camera"""
        if camera_id in self._tasks:
            self._tasks[camera_id].cancel()
            del self._tasks[camera_id]

        if camera_id in self.cameras:
            stream = self.cameras[camera_id]
            if stream.capture is not None:
                stream.capture.release()
                stream.capture = None
            stream.status = CameraStatus.IDLE
            logger.info(f"Monitoring stopped for camera: {camera_id}")

    async def _monitoring_loop(self, camera_id: str):
        """
        Main monitoring loop for a single camera.
        Samples frames at frame_sample_interval, computes risk every assessment_interval.
        """
        stream = self.cameras[camera_id]
        frames_since_assessment = 0
        last_assessment_time = datetime.now(timezone.utc)

        try:
            while True:
                # Read frame
                frame = await asyncio.to_thread(self._read_frame, stream)

                if frame is None:
                    stream.status = CameraStatus.OFFLINE
                    await self._emit_alert(
                        camera_id=camera_id,
                        alert_type="camera_offline",
                        severity="high",
                        message=f"Camera '{stream.name}' feed lost",
                        details={"last_frame": stream.last_frame_time.isoformat() if stream.last_frame_time else None}
                    )
                    # Retry after a delay
                    await asyncio.sleep(30)
                    # Try to reconnect
                    source = int(stream.source) if stream.source.isdigit() else stream.source
                    stream.capture = cv2.VideoCapture(source)
                    continue

                stream.last_frame_time = datetime.now(timezone.utc)
                stream.frame_count += 1
                frames_since_assessment += 1
                stream.latest_frame = frame.copy()

                # Analyze frame
                analysis = await asyncio.to_thread(stream.monitor.analyze_frame, frame)

                # Check for immediate threats (threat objects detected)
                await self._check_immediate_threats(camera_id, analysis)

                # Check if it's time for a risk assessment
                elapsed = (datetime.now(timezone.utc) - last_assessment_time).total_seconds()
                if elapsed >= self.assessment_interval:
                    await self._compute_risk_assessment(camera_id)
                    last_assessment_time = datetime.now(timezone.utc)
                    frames_since_assessment = 0

                # Wait before next frame sample
                await asyncio.sleep(self.frame_sample_interval)

        except asyncio.CancelledError:
            logger.info(f"Monitoring loop cancelled for camera: {camera_id}")
        except Exception as e:
            stream.status = CameraStatus.ERROR
            stream.error_message = str(e)
            logger.error(f"Error in monitoring loop for {camera_id}: {e}")
            await self._emit_alert(
                camera_id=camera_id,
                alert_type="camera_offline",
                severity="critical",
                message=f"Camera '{stream.name}' monitoring crashed: {str(e)}",
                details={"error": str(e)}
            )

    def _read_frame(self, stream: CameraStream) -> Optional[np.ndarray]:
        """Read a frame from the camera (runs in thread pool)"""
        if stream.capture is None or not stream.capture.isOpened():
            return None

        ret, frame = stream.capture.read()
        if not ret:
            return None
        return frame

    async def _check_immediate_threats(self, camera_id: str, analysis: Dict):
        """Check for immediate security threats in frame analysis"""
        stream = self.cameras[camera_id]
        detections = analysis.get("detections", [])

        threat_objects = {"knife", "baseball bat", "scissors", "fire"}
        detected_threats = [d for d in detections if d.get("class") in threat_objects]

        if detected_threats:
            threat_names = [d["class"] for d in detected_threats]
            await self._emit_alert(
                camera_id=camera_id,
                alert_type="threat_detected",
                severity="critical",
                message=f"Threat detected on '{stream.name}': {', '.join(threat_names)}",
                details={
                    "threats": detected_threats,
                    "object_counts": analysis.get("object_counts", {})
                }
            )

        # Check for unusual crowd (more than 10 people)
        person_count = analysis.get("object_counts", {}).get("person", 0)
        if person_count > 10:
            await self._emit_alert(
                camera_id=camera_id,
                alert_type="crowd_detected",
                severity="medium",
                message=f"Unusual crowd on '{stream.name}': {person_count} people detected",
                details={"person_count": person_count}
            )

    async def _compute_risk_assessment(self, camera_id: str):
        """
        Compute a risk assessment from camera observations.
        Maps the camera's detections and health into the standard risk categories.
        """
        stream = self.cameras[camera_id]
        if stream.monitor is None:
            return

        # Get risk estimation from camera monitor
        risk_data = stream.monitor.estimate_risk()
        if not risk_data:
            return

        # Compute scores using the standard risk service
        # Map the camera data to the format expected by compute_scores
        formatted_data = {
            "Physical Security": risk_data.get("physical_security", {}),
            "Access Control": risk_data.get("access_control", {}),
            "Personnel": risk_data.get("personnel", {}),
            "Incident History": risk_data.get("incident_history", {}),
            "Emergency Preparedness": risk_data.get("emergency_preparedness", {})
        }

        category_scores, contributions, overall_score = compute_scores(formatted_data)
        _, level, _ = risk_level(overall_score)

        assessment = {
            "camera_id": camera_id,
            "camera_name": stream.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category_scores": category_scores,
            "contributions": contributions,
            "overall_score": overall_score,
            "risk_level": level,
            "object_counts": stream.monitor.object_counts,
            "health_score": stream.monitor._calculate_health_score(
                stream.monitor.blur_history[-1] if stream.monitor.blur_history else 100,
                stream.monitor.brightness_history[-1] if stream.monitor.brightness_history else 128,
                stream.monitor.contrast_history[-1] if stream.monitor.contrast_history else 50,
                stream.monitor.noise_history[-1] if stream.monitor.noise_history else 20,
                stream.monitor.fps_history[-1] if stream.monitor.fps_history else 30
            )
        }

        stream.last_risk_assessment = assessment

        # Check threshold
        if overall_score >= self.risk_threshold:
            await self._emit_alert(
                camera_id=camera_id,
                alert_type="threshold_breach",
                severity="high" if overall_score < 80 else "critical",
                message=f"Risk score {overall_score:.1f} ({level}) on '{stream.name}'",
                details=assessment
            )

        # Broadcast assessment to WebSocket clients
        await self._broadcast({
            "type": "risk_assessment",
            "data": assessment
        })

        logger.info(f"Risk assessment for {camera_id}: score={overall_score:.1f}, level={level}")

    async def _emit_alert(
        self,
        camera_id: str,
        alert_type: str,
        severity: str,
        message: str,
        details: Dict = None
    ):
        """Create and broadcast an alert"""
        self._alert_counter += 1
        alert = Alert(
            id=f"alert_{self._alert_counter}",
            camera_id=camera_id,
            camera_name=self.cameras[camera_id].name if camera_id in self.cameras else camera_id,
            alert_type=alert_type,
            severity=severity,
            message=message,
            details=details or {}
        )
        self.alerts.append(alert)

        # Keep only last 100 alerts in memory
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]

        # Broadcast to WebSocket clients
        await self._broadcast({
            "type": "alert",
            "data": {
                "id": alert.id,
                "camera_id": alert.camera_id,
                "camera_name": alert.camera_name,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "details": alert.details,
                "timestamp": alert.timestamp.isoformat(),
                "acknowledged": alert.acknowledged
            }
        })

    async def _broadcast(self, message: Dict):
        """Broadcast message to all connected WebSocket clients"""
        disconnected = []
        for ws in self.websocket_clients:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected clients
        for ws in disconnected:
            self.websocket_clients.remove(ws)

    def add_websocket_client(self, ws):
        """Register a WebSocket client for real-time updates"""
        self.websocket_clients.append(ws)

    def remove_websocket_client(self, ws):
        """Remove a WebSocket client"""
        if ws in self.websocket_clients:
            self.websocket_clients.remove(ws)

    def get_camera_status(self, camera_id: str) -> Dict:
        """Get current status of a camera"""
        if camera_id not in self.cameras:
            raise ValueError(f"Camera '{camera_id}' not found")

        stream = self.cameras[camera_id]
        return {
            "camera_id": stream.camera_id,
            "name": stream.name,
            "source": stream.source,
            "location": stream.location,
            "status": stream.status.value,
            "last_frame_time": stream.last_frame_time.isoformat() if stream.last_frame_time else None,
            "frame_count": stream.frame_count,
            "error_message": stream.error_message,
            "last_risk_assessment": stream.last_risk_assessment
        }

    def get_all_cameras_status(self) -> List[Dict]:
        """Get status of all registered cameras"""
        return [self.get_camera_status(cid) for cid in self.cameras]

    def get_alerts(self, limit: int = 50, severity: str = None) -> List[Dict]:
        """Get recent alerts, optionally filtered by severity"""
        alerts = self.alerts
        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return [
            {
                "id": a.id,
                "camera_id": a.camera_id,
                "camera_name": a.camera_name,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
                "details": a.details,
                "timestamp": a.timestamp.isoformat(),
                "acknowledged": a.acknowledged
            }
            for a in alerts[-limit:]
        ]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    async def shutdown(self):
        """Stop all monitoring and release resources"""
        for camera_id in list(self._tasks.keys()):
            await self.stop_monitoring(camera_id)
        self._running = False
        logger.info("Camera manager shut down")


# Singleton instance
camera_manager = CameraManager()
