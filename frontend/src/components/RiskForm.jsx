import React, { useState } from 'react';
import '../styles/RiskForm.css';

export default function RiskForm({ onSubmit, loading = false }) {
  const [formData, setFormData] = useState({
    facility_name: '',
    physical_security: {
      perimeter_condition: 'Good',
      cctv_coverage: 75,
      cctv_functionality: 85,
      lighting_quality: 'Good',
      entry_exit_control: 'Good',
    },
    access_control: {
      visitor_management: 'Good',
      id_verification: 'Good',
      restricted_area_protection: 'Good',
      after_hours_security: 'Good',
    },
    personnel: {
      guard_count_ratio: 70,
      training_frequency: 'Good',
      background_checks: 'Good',
      shift_coverage: 'Good',
    },
    incident_history: {
      incident_severity_score: 40,
      incident_type_score: 35,
      response_time_score: 60,
      documentation_quality: 'Good',
    },
    emergency_preparedness: {
      emergency_plan: 'Good',
      drill_frequency: 'Good',
      communication_system: 'Good',
      staff_readiness: 'Good',
    },
  });

  const handleInputChange = (section, field, value) => {
    setFormData({
      ...formData,
      [section]: {
        ...formData[section],
        [field]: value,
      },
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const qualityOptions = ['Poor', 'Fair', 'Good', 'Excellent'];

  return (
    <form className="risk-form" onSubmit={handleSubmit}>
      <section className="form-section">
        <h3>Facility Information</h3>
        <div className="form-group">
          <label>Facility Name (Optional)</label>
          <input
            type="text"
            value={formData.facility_name}
            onChange={(e) => setFormData({ ...formData, facility_name: e.target.value })}
            placeholder="e.g., Corporate Headquarters"
          />
        </div>
      </section>

      <section className="form-section">
        <h3>Physical Security</h3>
        <div className="form-group">
          <label>Perimeter Condition</label>
          <select
            value={formData.physical_security.perimeter_condition}
            onChange={(e) => handleInputChange('physical_security', 'perimeter_condition', e.target.value)}
          >
            {qualityOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>CCTV Coverage (%)</label>
          <input
            type="number"
            min="0"
            max="100"
            value={formData.physical_security.cctv_coverage}
            onChange={(e) => handleInputChange('physical_security', 'cctv_coverage', parseFloat(e.target.value))}
          />
        </div>

        <div className="form-group">
          <label>CCTV Functionality (%)</label>
          <input
            type="number"
            min="0"
            max="100"
            value={formData.physical_security.cctv_functionality}
            onChange={(e) => handleInputChange('physical_security', 'cctv_functionality', parseFloat(e.target.value))}
          />
        </div>

        <div className="form-group">
          <label>Lighting Quality</label>
          <select
            value={formData.physical_security.lighting_quality}
            onChange={(e) => handleInputChange('physical_security', 'lighting_quality', e.target.value)}
          >
            {qualityOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label>Entry/Exit Control</label>
          <select
            value={formData.physical_security.entry_exit_control}
            onChange={(e) => handleInputChange('physical_security', 'entry_exit_control', e.target.value)}
          >
            {qualityOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>
      </section>

      <section className="form-section">
        <h3>Access Control</h3>
        {['visitor_management', 'id_verification', 'restricted_area_protection', 'after_hours_security'].map(field => (
          <div key={field} className="form-group">
            <label>{field.replace(/_/g, ' ').toUpperCase()}</label>
            <select
              value={formData.access_control[field]}
              onChange={(e) => handleInputChange('access_control', field, e.target.value)}
            >
              {qualityOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
        ))}
      </section>

      <section className="form-section">
        <h3>Security Personnel</h3>
        <div className="form-group">
          <label>Guard Adequacy Score (0-100)</label>
          <input
            type="number"
            min="0"
            max="100"
            value={formData.personnel.guard_count_ratio}
            onChange={(e) => handleInputChange('personnel', 'guard_count_ratio', parseFloat(e.target.value))}
          />
        </div>

        {['training_frequency', 'background_checks', 'shift_coverage'].map(field => (
          <div key={field} className="form-group">
            <label>{field.replace(/_/g, ' ').toUpperCase()}</label>
            <select
              value={formData.personnel[field]}
              onChange={(e) => handleInputChange('personnel', field, e.target.value)}
            >
              {qualityOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
        ))}
      </section>

      <section className="form-section">
        <h3>Incident History</h3>
        <div className="form-group">
          <label>Incident Severity Score (0-100)</label>
          <input
            type="number"
            min="0"
            max="100"
            value={formData.incident_history.incident_severity_score}
            onChange={(e) => handleInputChange('incident_history', 'incident_severity_score', parseFloat(e.target.value))}
          />
        </div>

        <div className="form-group">
          <label>Incident Type Severity (0-100)</label>
          <input
            type="number"
            min="0"
            max="100"
            value={formData.incident_history.incident_type_score}
            onChange={(e) => handleInputChange('incident_history', 'incident_type_score', parseFloat(e.target.value))}
          />
        </div>

        <div className="form-group">
          <label>Response Time Quality (0-100)</label>
          <input
            type="number"
            min="0"
            max="100"
            value={formData.incident_history.response_time_score}
            onChange={(e) => handleInputChange('incident_history', 'response_time_score', parseFloat(e.target.value))}
          />
        </div>

        <div className="form-group">
          <label>Documentation Quality</label>
          <select
            value={formData.incident_history.documentation_quality}
            onChange={(e) => handleInputChange('incident_history', 'documentation_quality', e.target.value)}
          >
            {qualityOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
          </select>
        </div>
      </section>

      <section className="form-section">
        <h3>Emergency Preparedness</h3>
        {['emergency_plan', 'drill_frequency', 'communication_system', 'staff_readiness'].map(field => (
          <div key={field} className="form-group">
            <label>{field.replace(/_/g, ' ').toUpperCase()}</label>
            <select
              value={formData.emergency_preparedness[field]}
              onChange={(e) => handleInputChange('emergency_preparedness', field, e.target.value)}
            >
              {qualityOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
            </select>
          </div>
        ))}
      </section>

      <button type="submit" disabled={loading} className="submit-btn">
        {loading ? 'Analyzing...' : 'Analyze Risk'}
      </button>
    </form>
  );
}
