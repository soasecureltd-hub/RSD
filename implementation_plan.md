# Goal: Automate Risk Assessment Data Capture Using Camera Features

The objective is to leverage the existing `CameraHealth` and computer vision (YOLOv8 + OpenCV) capabilities to automatically populate the data points required for the `Risk Assessment` computation. Currently, the camera captures health metrics (blur, brightness, etc.) and object detections (people, cars, etc.), while the risk form is filled out manually.

## User Review Required
> [!IMPORTANT]
> The standard YOLOv8 model detects generic objects (e.g., "person", "car", "knife"). It does not specifically classify "security guards" vs "visitors", nor does it inherently know the facility's "Emergency Plan". 
> 
> We need to establish heuristics (rules) to map what the camera *can* see to the risk score inputs. Please review the proposed mapping below and let me know if you agree or if you have specific rules you want to apply.

## Proposed Mapping (Camera Data -> Risk Score Input)

### 1. Physical Security
* **CCTV Functionality**: Mapped directly from the camera's overall `health_score` (0-100).
* **CCTV Coverage**: Estimated by subtracting the `obstruction_score` penalty from 100%.
* **Lighting Quality**: Derived from OpenCV `brightness` metric.
  * Brightness between 80-180 -> "Good" / "Excellent"
  * Brightness < 50 or > 200 -> "Poor"
* **Entry/Exit Control**: Derived from tracking the frequency of `person` detections. High unmonitored traffic could lower the score to "Fair".

### 2. Access Control
* **After Hours Security**: We can use the system clock combined with YOLO `person` detection. If a person is detected outside of business hours (e.g., 7 PM - 6 AM), we automatically flag this as "Poor".
* **Restricted Area Protection**: If the camera is designated as being in a restricted area and detects a `person` without a `guard` present, the score lowers.

### 3. Personnel
* **Guard Count Ratio & Shift Coverage**: Standard YOLO detects "person". We can either assume a baseline presence of people as staff/guards, or we can use the frequency of `person` detections during night shifts to score "shift_coverage". *(Open Question: Do you want to try to distinguish guards from regular people?)*

### 4. Incident History
* **Incident Severity/Type**: If YOLO detects objects like a "knife", "baseball bat", or if we detect erratic high-speed movement (indicative of running/fleeing), we can automatically increase the incident severity scores.

## Proposed Implementation Steps

### Backend (`backend/app/services/camera_service.py` & `routes`)
1. **[NEW] Endpoint `/api/camera/risk-estimation/{camera_id}`**: 
   * A new route that aggregates the last N frames of camera data (from history) and applies the mapping rules defined above.
   * Returns a JSON payload formatted exactly like `RiskAssessmentInput`.

### Frontend (`frontend/src/components/RiskForm.jsx` & `apiClient.js`)
1. **[MODIFY] `apiClient.js`**:
   * Add the new endpoint to fetch the camera-based risk estimation.
2. **[MODIFY] `RiskForm.jsx`**:
   * Add a prominent **"Auto-Fill from Camera Data"** button.
   * When clicked, it fetches the estimation from the backend and populates the form fields, allowing the user to review and tweak them before final submission.
3. **[MODIFY] `Dashboard.jsx`**:
   * Ensure the camera feed can run in the background or alongside the risk form so data is actively gathered.

## Open Questions
> [!WARNING]
> 1. Are there specific working hours we should use for the "After Hours" calculation? (e.g., 9 AM to 5 PM?)
> 2. For items the camera cannot easily see (like "Background Checks", "Emergency Plan", "Documentation Quality"), should we leave them as their default values ("Good") for the user to manually adjust?

## Verification Plan
1. Start the camera and simulate different environments (cover the lens for poor coverage, turn off lights for poor lighting, walk into the frame for person detection).
2. Click "Auto-Fill" on the Risk Form and verify that the values correctly reflect the camera's observations.
3. Submit the form and verify the Risk Score is accurately calculated.
