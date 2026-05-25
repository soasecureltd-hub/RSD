# Live Risk Estimation using Camera Data

I have successfully updated the camera assessment section to automatically capture and compute the data points used for the risk score, while leaving the existing manual risk assessment form completely untouched.

## Changes Implemented

### 1. Backend: Camera Risk Estimation Engine
I added a new method to the `CameraHealthMonitor` service in `backend/app/services/camera_service.py`. This engine takes the real-time data that the camera is already capturing and translates it into the fields needed for a risk assessment:
* **CCTV Functionality:** Extracted directly from the overall camera health score.
* **CCTV Coverage:** Modeled based on whether a `lens_obstruction` issue was recently detected.
* **Lighting Quality:** Computed from OpenCV's image brightness analysis (mapping specific brightness bounds to "Good", "Fair", or "Poor").
* **Entry/Exit Control:** Derived dynamically by tracking the frequency of YOLOv8 "person" detections.
* **After Hours Security:** Evaluates the current system time against active detections. If a person is detected outside of business hours, the score lowers to "Poor".
* **Incident Severity:** Analyzes the detected objects for threat-indicators (e.g., "knife", "gun", "baseball bat", "fire"). If detected, the severity score automatically increases.

### 2. Backend: New API Endpoint
I created a dedicated endpoint `/api/camera/risk-estimation/{camera_id}` in `backend/app/routes/camera.py`. This ensures the camera-based risk parameters are cleanly separated and can be fetched on-demand.

### 3. Frontend: Live Updates in Camera Dashboard
I updated the `apiClient.js` to support the new endpoint and modified the `CameraHealth.jsx` component. Now, every time the camera captures a frame (every 3 seconds), it also silently fetches the live risk estimation and displays it seamlessly at the bottom of the camera dashboard under a new **"Live Risk Estimation"** section. 

> [!NOTE]
> As requested, **zero changes** were made to the `RiskForm.jsx` component or the manual risk assessment inputs. This entire feature operates solely within the Camera Health domain.
