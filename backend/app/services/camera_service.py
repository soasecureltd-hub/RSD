"""
Camera health monitoring service
Ported from old camera.py
Includes object detection via YOLOv8
"""
import cv2
import numpy as np
from datetime import datetime, timezone
from typing import Dict, List
from collections import deque
from pathlib import Path
import time
import os
from app.config import settings

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


class CameraHealthMonitor:
    """Monitor camera health using computer vision and object detection"""
    
    def __init__(self, camera_id: str, history_size: int = 30, enable_detection: bool = True):
        """Initialize health monitor with optional object detection"""
        self.camera_id = camera_id
        self.history_size = history_size
        
        # Health metrics history
        self.blur_history = deque(maxlen=history_size)
        self.brightness_history = deque(maxlen=history_size)
        self.contrast_history = deque(maxlen=history_size)
        self.noise_history = deque(maxlen=history_size)
        self.fps_history = deque(maxlen=history_size)
        
        # Frame tracking
        self.last_frame = None
        self.last_frame_time = None
        self.frame_count = 0
        self.total_frames = 0
        
        # Alert thresholds
        self.thresholds = {
            "blur_min": 100,
            "brightness_min": 50,
            "brightness_max": 200,
            "contrast_min": 30,
            "fps_min": 15,
            "obstruction_threshold": 0.8
        }
        
        # Object detection
        self.detection_enabled = enable_detection and YOLO_AVAILABLE
        self.model = None
        if self.detection_enabled:
            try:
                # Resolve model path relative to this service file to avoid cwd issues
                model_file = Path(__file__).resolve().parents[2] / 'yolov8n.pt'
                if not model_file.exists():
                    raise FileNotFoundError(f"YOLO model file not found: {model_file}")

                self.model = YOLO(str(model_file))  # Nano model - lightweight
                print(f"YOLO model loaded from {model_file}")
            except Exception as e:
                print(f"Warning: Could not load YOLO model: {e}")
                self.detection_enabled = False
        
        self.is_online = False
        self.last_check_time = None
        self.alerts = []
        self.detected_objects = []
        self.object_counts = {}
    
    def analyze_frame(self, frame: np.ndarray) -> Dict:
        """Analyze a single frame and return health metrics + detections"""
        if frame is None or frame.size == 0:
            return self._create_offline_status()
        
        self.is_online = True
        self.last_check_time = datetime.now(timezone.utc)
        self.total_frames += 1
        
        # Convert to grayscale for health analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate health metrics
        blur_score = self._calculate_blur(gray)
        brightness = self._calculate_brightness(gray)
        contrast = self._calculate_contrast(gray)
        noise_level = self._calculate_noise(gray)
        fps = self._calculate_fps()
        obstruction_score = self._detect_obstruction(gray)
        
        # Store in history
        self.blur_history.append(blur_score)
        self.brightness_history.append(brightness)
        self.contrast_history.append(contrast)
        self.noise_history.append(noise_level)
        self.fps_history.append(fps)
        
        # Detect issues
        issues = self._detect_issues(blur_score, brightness, contrast, noise_level, fps, obstruction_score)
        
        # Calculate health score
        health_score = self._calculate_health_score(blur_score, brightness, contrast, noise_level, fps)
        
        # Generate alerts
        self._generate_alerts(issues)
        
        # Object detection
        detections = []
        object_counts = {}
        if self.detection_enabled and self.model:
            detections, object_counts = self._detect_objects(frame)
        
        # Store frame for next comparison
        self.last_frame = gray.copy()
        self.detected_objects = detections
        self.object_counts = object_counts
        
        return {
            "camera_id": self.camera_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "online",
            "health_score": round(health_score, 2),
            "metrics": {
                "blur_score": round(blur_score, 2),
                "brightness": round(brightness, 2),
                "contrast": round(contrast, 2),
                "noise_level": round(noise_level, 2),
                "fps": round(fps, 2),
                "obstruction_score": round(obstruction_score, 2)
            },
            "issues": issues,
            "alerts": self.alerts[-5:],
            "frame_count": self.total_frames,
            "detections": detections,
            "object_counts": object_counts,
            "detection_enabled": self.detection_enabled
        }
    
    def _detect_objects(self, frame: np.ndarray) -> tuple:
        """
        Detect objects in frame using YOLOv8
        
        Returns:
            Tuple of (detections_list, object_counts_dict)
        """
        try:
            # Run inference
            results = self.model(frame, verbose=False)
            
            detections = []
            counts = {}
            
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        
                        # Get class name
                        class_name = result.names[cls_id] if cls_id in result.names else f"class_{cls_id}"
                        
                        # Only keep detections above configured confidence threshold
                        if conf > settings.YOLO_CONFIDENCE_THRESHOLD:
                            detection = {
                                "class": class_name,
                                "confidence": round(conf, 3),
                                "box": [float(x) for x in box.xyxy[0].tolist()]
                            }
                            detections.append(detection)
                            
                            # Count by class
                            counts[class_name] = counts.get(class_name, 0) + 1
            
            return detections, counts
        
        except Exception as e:
            print(f"Error in object detection: {e}")
            return [], {}
    
    def _calculate_blur(self, gray: np.ndarray) -> float:
        """Calculate blur using Laplacian variance"""
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        return laplacian.var()
    
    def _calculate_brightness(self, gray: np.ndarray) -> float:
        """Calculate average brightness (0-255)"""
        return np.mean(gray)
    
    def _calculate_contrast(self, gray: np.ndarray) -> float:
        """Calculate contrast using standard deviation"""
        return np.std(gray)
    
    def _calculate_noise(self, gray: np.ndarray) -> float:
        """Estimate noise level"""
        kernel = np.array([[-1, -1, -1],
                          [-1,  8, -1],
                          [-1, -1, -1]])
        filtered = cv2.filter2D(gray, -1, kernel)
        return np.std(filtered)
    
    def _calculate_fps(self) -> float:
        """Calculate frames per second"""
        current_time = time.time()
        
        if self.last_frame_time is None:
            self.last_frame_time = current_time
            return 0.0
        
        time_diff = current_time - self.last_frame_time
        fps = 1.0 / time_diff if time_diff > 0 else 0.0
        self.last_frame_time = current_time
        return fps
    
    def _detect_obstruction(self, gray: np.ndarray) -> float:
        """Detect if lens is obstructed"""
        if self.last_frame is None:
            return 0.0
        
        diff = cv2.absdiff(gray, self.last_frame)
        mean_diff = np.mean(diff)
        std_dev = np.std(gray)
        
        if std_dev < 10:
            return 1.0
        elif mean_diff < 5:
            return 0.8
        else:
            return 0.0
    
    def _detect_issues(self, blur: float, brightness: float, contrast: float, 
                      noise: float, fps: float, obstruction: float) -> List[str]:
        """Detect specific issues"""
        issues = []
        
        if blur < self.thresholds["blur_min"]:
            issues.append("blurry_image")
        if brightness < self.thresholds["brightness_min"]:
            issues.append("too_dark")
        elif brightness > self.thresholds["brightness_max"]:
            issues.append("overexposed")
        if contrast < self.thresholds["contrast_min"]:
            issues.append("low_contrast")
        if noise > 50:
            issues.append("high_noise")
        if fps < self.thresholds["fps_min"] and fps > 0:
            issues.append("low_fps")
        if obstruction > self.thresholds["obstruction_threshold"]:
            issues.append("lens_obstruction")
        
        return issues
    
    def _calculate_health_score(self, blur: float, brightness: float, 
                                contrast: float, noise: float, fps: float) -> float:
        """Calculate overall health score (0-100)"""
        score = 100.0
        
        if blur < 50:
            score -= 30
        elif blur < 100:
            score -= 20
        elif blur < 200:
            score -= 10
        
        if brightness < 40 or brightness > 220:
            score -= 20
        elif brightness < 50 or brightness > 200:
            score -= 10
        
        if contrast < 20:
            score -= 20
        elif contrast < 30:
            score -= 10
        
        if noise > 60:
            score -= 15
        elif noise > 50:
            score -= 10
        
        if fps > 0 and fps < 10:
            score -= 15
        elif fps > 0 and fps < 15:
            score -= 10
        
        return max(0, score)
    
    def _generate_alerts(self, issues: List[str]):
        """Generate alerts for detected issues"""
        severity_map = {
            "blurry_image": "medium",
            "too_dark": "high",
            "overexposed": "medium",
            "low_contrast": "low",
            "high_noise": "low",
            "low_fps": "medium",
            "lens_obstruction": "critical"
        }
        
        for issue in issues:
            alert = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "issue": issue,
                "severity": severity_map.get(issue, "low"),
                "message": self._get_issue_message(issue)
            }
            self.alerts.append(alert)
    
    def _get_issue_message(self, issue: str) -> str:
        """Get human-readable message for issue"""
        messages = {
            "blurry_image": "Camera image is out of focus or blurry",
            "too_dark": "Camera image is too dark - check lighting or camera settings",
            "overexposed": "Camera image is overexposed - reduce exposure or add shade",
            "low_contrast": "Image has low contrast - may be foggy or need cleaning",
            "high_noise": "High noise detected - possible low light or sensor issue",
            "low_fps": "Frame rate is below normal - check network or camera load",
            "lens_obstruction": "Lens may be obstructed, dirty, or covered"
        }
        return messages.get(issue, "Unknown issue detected")
    
    def _create_offline_status(self) -> Dict:
        """Create status for offline camera"""
        return {
            "camera_id": self.camera_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "offline",
            "health_score": 0,
            "metrics": {},
            "issues": ["offline"],
            "alerts": [],
            "frame_count": self.total_frames,
            "detections": [],
            "object_counts": {},
            "detection_enabled": self.detection_enabled
        }

    def estimate_risk(self) -> Dict:
        """Estimate risk assessment parameters based on camera data"""
        if not self.is_online:
            return {}

        # 1. Physical Security
        # Calculate latest health to derive functionality
        latest_health = 100.0
        if self.blur_history and self.brightness_history and self.contrast_history and self.noise_history and self.fps_history:
            latest_health = self._calculate_health_score(
                self.blur_history[-1],
                self.brightness_history[-1],
                self.contrast_history[-1],
                self.noise_history[-1],
                self.fps_history[-1]
            )
        
        avg_brightness = np.mean(self.brightness_history) if self.brightness_history else 0
        if 80 <= avg_brightness <= 180:
            lighting = "Good"
        elif 50 <= avg_brightness <= 200:
            lighting = "Fair"
        else:
            lighting = "Poor"
            
        person_count = self.object_counts.get("person", 0)
        
        current_hour = datetime.now(timezone.utc).hour
        after_hours = current_hour >= 19 or current_hour < 6
        
        incident_severity = 40
        incident_type = 35
        # Check for threat objects
        threat_objects = ["knife", "baseball bat", "gun", "fire", "scissors", "bottle"]
        detected_threats = [obj for obj in self.detected_objects if obj["class"] in threat_objects]
        if detected_threats:
            incident_severity += 40
            incident_type += 40

        # Check for obstruction in recent alerts
        obstruction = any(a["issue"] == "lens_obstruction" for a in self.alerts[-5:])

        return {
            "physical_security": {
                "cctv_functionality": min(100, max(0, latest_health)),
                "cctv_coverage": 50 if obstruction else 100,
                "lighting_quality": lighting,
                "entry_exit_control": "Fair" if person_count > 5 else "Good",
                "perimeter_condition": "Fair" if obstruction else "Good"
            },
            "access_control": {
                "after_hours_security": "Poor" if (after_hours and person_count > 0) else "Good",
                "restricted_area_protection": "Fair" if person_count > 0 else "Good",
                "visitor_management": "Good",
                "id_verification": "Good"
            },
            "personnel": {
                "shift_coverage": "Good" if person_count > 0 else "Fair",
                "guard_count_ratio": min(100, person_count * 10 + 50) if person_count > 0 else 50,
                "training_frequency": "Good",
                "background_checks": "Good"
            },
            "incident_history": {
                "incident_severity_score": min(100, incident_severity),
                "incident_type_score": min(100, incident_type),
                "response_time_score": 60,
                "documentation_quality": "Good"
            },
            "emergency_preparedness": {
                "emergency_plan": "Good",
                "drill_frequency": "Good",
                "communication_system": "Good",
                "staff_readiness": "Good"
            }
        }
