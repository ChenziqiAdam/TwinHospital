import json
import datetime
from pathlib import Path

def generate_hospital_report(json_file_path, output_file_path="hospital_report.html"):
    """
    Generate a comprehensive professional HTML report from hospital simulation JSON data.
    
    Args:
        json_file_path (str): Path to the JSON file
        output_file_path (str): Path for the output HTML file
    """
    
    # Read JSON data
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Extract data sections
    metadata = data.get('simulation_metadata', {})
    stats = data.get('hospital_statistics', {})
    patients = data.get('patient_summaries', [])
    doctors = data.get('doctor_summaries', [])
    
    # Generate HTML content
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hospital Simulation Report - {metadata.get('hospital_name', 'Unknown Hospital')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.5;
            color: #333;
            background-color: #f8f9fa;
            font-size: 14px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 25px;
            border-radius: 8px;
            margin-bottom: 25px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        
        .header h1 {{
            font-size: 1.8em;
            margin-bottom: 8px;
        }}
        
        .header .subtitle {{
            font-size: 1em;
            opacity: 0.9;
        }}
        
        .section {{
            background: white;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            border: 1px solid #e9ecef;
        }}
        
        .section-header {{
            background-color: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #dee2e6;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .section-header:hover {{
            background-color: #e9ecef;
        }}
        
        .section-header h2 {{
            color: #495057;
            font-size: 1.2em;
            margin: 0;
        }}
        
        .toggle-icon {{
            font-size: 1.2em;
            transition: transform 0.3s ease;
        }}
        
        .section-header.collapsed .toggle-icon {{
            transform: rotate(-90deg);
        }}
        
        .section-content {{
            padding: 20px;
            display: block;
        }}
        
        .section-content.collapsed {{
            display: none;
        }}
        
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        
        .summary-table th,
        .summary-table td {{
            padding: 8px 12px;
            text-align: left;
            border: 1px solid #dee2e6;
            font-size: 0.9em;
        }}
        
        .summary-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        
        .summary-table tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        
        .summary-table tr:hover {{
            background-color: #e3f2fd;
        }}
        
        .patient-card {{
            border: 1px solid #dee2e6;
            border-radius: 6px;
            margin-bottom: 15px;
            background: white;
        }}
        
        .patient-header {{
            background-color: #e8f4fd;
            padding: 12px 15px;
            border-bottom: 1px solid #dee2e6;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .patient-header:hover {{
            background-color: #d1ecf1;
        }}
        
        .patient-header h3 {{
            font-size: 1.1em;
            margin: 0;
            color: #2c3e50;
        }}
        
        .patient-basic-info {{
            font-size: 0.9em;
            color: #6c757d;
            margin-top: 3px;
        }}
        
        .patient-details {{
            padding: 15px;
            display: none;
        }}
        
        .patient-details.expanded {{
            display: block;
        }}
        
        .detail-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}
        
        .detail-section {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 12px;
        }}
        
        .detail-section h4 {{
            color: #495057;
            margin-bottom: 8px;
            font-size: 1em;
            border-bottom: 1px solid #dee2e6;
            padding-bottom: 5px;
        }}
        
        .detail-list {{
            list-style: none;
            padding: 0;
        }}
        
        .detail-list li {{
            margin-bottom: 6px;
            padding: 4px 0;
            font-size: 0.9em;
        }}
        
        .detail-list li strong {{
            color: #495057;
            font-weight: 600;
        }}
        
        .test-results {{
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 10px;
            margin: 8px 0;
            font-size: 0.85em;
        }}
        
        .notes-section {{
            background-color: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 10px;
            margin: 8px 0;
            border-radius: 0 4px 4px 0;
        }}
        
        .note-item {{
            margin-bottom: 8px;
            padding: 6px;
            background: white;
            border-radius: 4px;
            font-size: 0.85em;
        }}
        
        .note-header {{
            font-weight: 600;
            color: #495057;
            margin-bottom: 3px;
        }}
        
        .status-badge {{
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        
        .status-available {{
            background-color: #d4edda;
            color: #155724;
        }}
        
        .status-discharged {{
            background-color: #cce5ff;
            color: #004085;
        }}
        
        .priority-high {{ color: #dc3545; font-weight: bold; }}
        .priority-standard {{ color: #28a745; }}
        .priority-low {{ color: #6c757d; }}
        
        .collapsible-btn {{
            background: none;
            border: none;
            color: #007bff;
            cursor: pointer;
            text-decoration: underline;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        .collapsible-btn:hover {{
            color: #0056b3;
        }}
        
        .hidden-details {{
            display: none;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #dee2e6;
        }}
        
        @media (max-width: 768px) {{
            .detail-grid {{
                grid-template-columns: 1fr;
            }}
            
            .summary-table {{
                font-size: 0.8em;
            }}
            
            .container {{
                padding: 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header Section -->
        <div class="header">
            <h1>{metadata.get('hospital_name', 'Hospital Simulation Report')}</h1>
            <div class="subtitle">
                Simulation Report | Generated: {metadata.get('export_time', 'Unknown')} | 
                Duration: {metadata.get('simulation_duration_hours', 0):.2f} hours | 
                Patients: {metadata.get('total_patients', 0)} | Doctors: {metadata.get('total_doctors', 0)}
            </div>
        </div>

        <!-- Executive Summary -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('summary')">
                <h2>Executive Summary</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content" id="summary">
                <table class="summary-table">
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td><strong>Patients Processed</strong></td>
                        <td>{stats.get('patient_statistics', {}).get('total_processed', 0)}</td>
                        <td><strong>Revenue</strong></td>
                        <td>{stats.get('financial_summary', {}).get('total_revenue', '$0')}</td>
                    </tr>
                    <tr>
                        <td><strong>Tests Performed</strong></td>
                        <td>{stats.get('patient_statistics', {}).get('tests_performed', 0)}</td>
                        <td><strong>Net Profit</strong></td>
                        <td>{stats.get('financial_summary', {}).get('profit', '$0')}</td>
                    </tr>
                    <tr>
                        <td><strong>Consultations</strong></td>
                        <td>{stats.get('patient_statistics', {}).get('consultations_completed', 0)}</td>
                        <td><strong>Payment Rate</strong></td>
                        <td>{stats.get('financial_summary', {}).get('payment_rate', '0%')}</td>
                    </tr>
                    <tr>
                        <td><strong>Patient Satisfaction</strong></td>
                        <td>{stats.get('operational_metrics', {}).get('patient_satisfaction_score', 'N/A')}</td>
                        <td><strong>Avg. Processing Time</strong></td>
                        <td>{stats.get('operational_metrics', {}).get('avg_patient_processing_time', 'N/A')}</td>
                    </tr>
                </table>
            </div>
        </div>

        <!-- Financial Details -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('financial')">
                <h2>Financial Performance</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="financial">
                <table class="summary-table">
                    <tr>
                        <th>Financial Metric</th>
                        <th>Value</th>
                        <th>Details</th>
                    </tr>
                    <tr>
                        <td>Total Revenue</td>
                        <td>{stats.get('financial_summary', {}).get('total_revenue', '$0')}</td>
                        <td>Revenue from all patient services</td>
                    </tr>
                    <tr>
                        <td>Total Expenses</td>
                        <td>{stats.get('financial_summary', {}).get('total_expenses', '$0')}</td>
                        <td>Operational costs and overhead</td>
                    </tr>
                    <tr>
                        <td>Net Profit</td>
                        <td>{stats.get('financial_summary', {}).get('profit', '$0')}</td>
                        <td>Revenue minus expenses</td>
                    </tr>
                    <tr>
                        <td>Bills Issued</td>
                        <td>{stats.get('financial_summary', {}).get('bills_issued', 0)}</td>
                        <td>Total number of bills generated</td>
                    </tr>
                    <tr>
                        <td>Payment Rate</td>
                        <td>{stats.get('financial_summary', {}).get('payment_rate', '0%')}</td>
                        <td>Percentage of bills paid</td>
                    </tr>
                </table>
            </div>
        </div>

        <!-- Doctor Performance -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('doctors')">
                <h2>Medical Staff Performance</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="doctors">
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>Doctor</th>
                            <th>Specialty</th>
                            <th>Experience</th>
                            <th>Patients Seen</th>
                            <th>Utilization</th>
                            <th>Avg. Consultation</th>
                            <th>Status</th>
                            <th>Shift</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    # Add doctor rows
    for doctor in doctors:
        doctor_info = doctor.get('doctor_info', {})
        daily_metrics = doctor.get('daily_metrics', {})
        current_status = doctor.get('current_status', {})
        
        status_class = "status-available" if current_status.get('is_available', True) else "status-busy"
        
        html_content += f"""
                        <tr>
                            <td>{doctor_info.get('name', 'Unknown')}</td>
                            <td>{doctor_info.get('specialty', 'Unknown')}</td>
                            <td>{doctor_info.get('experience_years', 0)} years</td>
                            <td>{daily_metrics.get('patients_seen', 0)}</td>
                            <td>{daily_metrics.get('utilization_rate', 0):.1f}%</td>
                            <td>{daily_metrics.get('average_consultation_time_minutes', 0):.1f} min</td>
                            <td><span class="status-badge {status_class}">{current_status.get('status', 'Unknown')}</span></td>
                            <td>{current_status.get('shift_start', 'N/A')} - {current_status.get('shift_end', 'N/A')}</td>
                        </tr>
"""

    html_content += """
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Resource Utilization -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('resources')">
                <h2>Resource Utilization</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="resources">
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>Room Type</th>
                            <th>Total</th>
                            <th>Available</th>
                            <th>Occupied</th>
                            <th>Utilization Rate</th>
                        </tr>
                    </thead>
                    <tbody>
"""

    # Add room utilization data
    rooms = stats.get('resource_utilization', {}).get('rooms', {})
    for room_type, room_data in rooms.items():
        html_content += f"""
                        <tr>
                            <td>{room_type.title()}</td>
                            <td>{room_data.get('total', 0)}</td>
                            <td>{room_data.get('available', 0)}</td>
                            <td>{room_data.get('occupied', 0)}</td>
                            <td>{room_data.get('utilization_rate', '0%')}</td>
                        </tr>
"""

    html_content += """
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Patient Details -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('patients')">
                <h2>Patient Visit Details ({} patients)</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="patients">
""".format(len(patients))

    # Add patient details
    for i, patient in enumerate(patients, 1):
        patient_info = patient.get('patient_info', {})
        visit_info = patient.get('visit_info', {})
        medical_record = patient.get('medical_record', {})
        
        # Format basic info
        symptoms = ', '.join(patient_info.get('symptoms', [])) or 'None reported'
        medical_history = ', '.join(patient_info.get('medical_history', [])) or 'None'
        insurance_status = "Insured" if patient_info.get('insurance', False) else "Uninsured"
        assigned_department = patient_info.get('assigned_department', 'General') or 'General'
        
        # Get diagnosis
        diagnoses = medical_record.get('diagnoses', [])
        diagnosis_info = diagnoses[0] if diagnoses else {}
        
        # Calculate stay duration
        arrival = visit_info.get('arrival_time', '')
        discharge = visit_info.get('discharge_time', '')
        
        html_content += f"""
                <div class="patient-card">
                    <div class="patient-header" onclick="togglePatient('patient{i}')">
                        <div>
                            <h3>{patient_info.get('name', 'Unknown')} (ID: {patient_info.get('id', 'Unknown')})</h3>
                            <div class="patient-basic-info">
                                Age: {patient_info.get('age', 'Unknown')} | Gender: {patient_info.get('gender', 'Unknown')} | 
                                {insurance_status} | Priority: {visit_info.get('priority', 'Unknown')} | 
                                Status: <span class="status-badge status-discharged">{visit_info.get('current_status', 'Unknown')}</span>
                            </div>
                        </div>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="patient-details" id="patient{i}">
                        <div class="detail-grid">
                            <div class="detail-section">
                                <h4>Visit Information</h4>
                                <ul class="detail-list">
                                    <li><strong>Arrival:</strong> {arrival}</li>
                                    <li><strong>Discharge:</strong> {discharge}</li>
                                    <li><strong>Waiting Time:</strong> {patient.get('waiting_time_seconds', 0)} seconds</li>
                                    <li><strong>Symptoms:</strong> {symptoms}</li>
                                    <li><strong>Medical History:</strong> {medical_history}</li>
                                    <li><strong>Assigned Departments:</strong> {assigned_department}</li>
                                </ul>
                            </div>
                            
                            <div class="detail-section">
                                <h4>Diagnosis & Treatment</h4>
                                <ul class="detail-list">
                                    <li><strong>Diagnosis:</strong> {diagnosis_info.get('diagnosis', 'No diagnosis recorded')}</li>
                                    <li><strong>Diagnosing Doctor:</strong> {diagnosis_info.get('doctor', 'Unknown')}</li>
                                    <li><strong>Diagnosis Time:</strong> {diagnosis_info.get('timestamp', 'N/A')}</li>
                                    <li><strong>Status:</strong> {diagnosis_info.get('status', 'N/A')}</li>
                                </ul>
                            </div>
                        </div>
"""

        # Add vitals if available
        vitals = medical_record.get('vitals', [])
        if vitals:
            html_content += """
                        <div class="detail-section">
                            <h4>Vital Signs</h4>
"""
            for vital in vitals:
                html_content += f"""
                            <div style="margin-bottom: 10px; padding: 8px; background: white; border-radius: 4px;">
                                <div style="font-weight: 600; margin-bottom: 5px;">Recorded by {vital.get('recorded_by', 'Unknown')} at {vital.get('timestamp', 'Unknown')}</div>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; font-size: 0.85em;">
                                    <div>Temp: {vital.get('temperature', 'N/A')}°C</div>
                                    <div>BP: {vital.get('blood_pressure', 'N/A')} mmHg</div>
                                    <div>HR: {vital.get('heart_rate', 'N/A')} bpm</div>
                                    <div>RR: {vital.get('respiratory_rate', 'N/A')} /min</div>
                                </div>
                            </div>
"""
            html_content += """
                        </div>
"""

        # Add prescriptions
        prescriptions = medical_record.get('prescriptions', [])
        if prescriptions:
            html_content += """
                        <div class="detail-section">
                            <h4>Prescriptions</h4>
"""
            for j, prescription in enumerate(prescriptions, 1):
                html_content += f"""
                            <div class="test-results">
                                <strong>Prescription {j}:</strong><br>
                                {prescription}
                            </div>
"""
            html_content += """
                        </div>
"""

        # Add test results
        tests = medical_record.get('tests', [])
        if tests:
            html_content += f"""
                        <div class="detail-section">
                            <h4>Test Results ({len(tests)} tests)</h4>
                            <button class="collapsible-btn" onclick="toggleDetails('tests{i}')">Show/Hide Test Details</button>
                            <div class="hidden-details" id="tests{i}">
"""
            for j, test in enumerate(tests, 1):
                html_content += f"""
                                <div class="test-results">
                                    <strong>Test {j}:</strong><br>
                                    {test}
                                </div>
"""
            html_content += """
                            </div>
                        </div>
"""

        # Add consultation details if any
        consultations = medical_record.get('consultations', [])
        if consultations:
            html_content += f"""
                        <div class="detail-section">
                            <h4>Consultations ({len(consultations)} consultations)</h4>
"""
            for j, consultation in enumerate(consultations, 1):
                html_content += f"""
                            <div class="test-results">
                                <strong>Consultation {j}:</strong><br>
                                {consultation}
                            </div>
"""
            html_content += """
                        </div>
"""

        # Add notes
        notes = medical_record.get('notes', [])
        if notes:
            html_content += f"""
                        <div class="detail-section">
                            <h4>Medical Notes ({len(notes)} notes)</h4>
                            <button class="collapsible-btn" onclick="toggleDetails('notes{i}')">Show/Hide Notes Details</button>
                            <div class="hidden-details" id="notes{i}">
                                <div class="notes-section">
"""
            for note in notes:
                html_content += f"""
                                    <div class="note-item">
                                        <div class="note-header">{note.get('staff', 'Unknown Staff')} - {note.get('type', 'General').title()} Note</div>
                                        <div style="font-size: 0.8em; color: #6c757d; margin-bottom: 5px;">{note.get('timestamp', 'Unknown time')}</div>
                                        <div>{note.get('content', 'No content')}</div>
                                    </div>
"""
            html_content += """
                                </div>
                            </div>
                        </div>
"""
        
        html_content += """
                    </div>
                </div>
"""

    # Add operational details
    html_content += """
        <!-- Operational Details -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('operational')">
                <h2>Operational Details</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="operational">
                <div class="detail-grid">
                    <div class="detail-section">
                        <h4>Hospital Information</h4>
                        <ul class="detail-list">
"""
    
    hospital_info = stats.get('hospital_info', {})
    html_content += f"""
                            <li><strong>Hospital Name:</strong> {hospital_info.get('name', 'Unknown')}</li>
                            <li><strong>Total Departments:</strong> {hospital_info.get('departments', 0)}</li>
                            <li><strong>Total Doctors:</strong> {hospital_info.get('total_doctors', 0)}</li>
                            <li><strong>Operation Hours:</strong> {hospital_info.get('operation_hours', 0)} hours</li>
"""
    
    html_content += """
                        </ul>
                    </div>
                    <div class="detail-section">
                        <h4>Patient Statistics</h4>
                        <ul class="detail-list">
"""
    
    patient_stats = stats.get('patient_statistics', {})
    html_content += f"""
                            <li><strong>Total Processed:</strong> {patient_stats.get('total_processed', 0)}</li>
                            <li><strong>Currently Active:</strong> {patient_stats.get('currently_active', 0)}</li>
                            <li><strong>Consultations Completed:</strong> {patient_stats.get('consultations_completed', 0)}</li>
                            <li><strong>Tests Performed:</strong> {patient_stats.get('tests_performed', 0)}</li>
                            <li><strong>Prescriptions Dispensed:</strong> {patient_stats.get('prescriptions_dispensed', 0)}</li>
"""
    
    html_content += """
                        </ul>
                    </div>
                    <div class="detail-section">
                        <h4>Operational Metrics</h4>
                        <ul class="detail-list">
"""
    
    operational_metrics = stats.get('operational_metrics', {})
    html_content += f"""
                            <li><strong>Avg. Processing Time:</strong> {operational_metrics.get('avg_patient_processing_time', 'N/A')}</li>
                            <li><strong>Patient Satisfaction:</strong> {operational_metrics.get('patient_satisfaction_score', 'N/A')}</li>
                            <li><strong>Bed Occupancy Rate:</strong> {operational_metrics.get('bed_occupancy_rate', 'N/A')}</li>
                            <li><strong>Equipment Utilization:</strong> {operational_metrics.get('equipment_utilization', 'N/A')}</li>
"""
    
    html_content += """
                        </ul>
                    </div>
                </div>
            </div>
        </div>

        <!-- Doctor Details -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('doctor-details')">
                <h2>Detailed Doctor Information</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="doctor-details">
"""

    # Add detailed doctor information
    for doctor in doctors:
        doctor_info = doctor.get('doctor_info', {})
        daily_metrics = doctor.get('daily_metrics', {})
        current_status = doctor.get('current_status', {})
        performance = doctor.get('performance_metrics', {})
        
        html_content += f"""
                <div class="detail-section" style="margin-bottom: 15px;">
                    <h4>{doctor_info.get('name', 'Unknown')} - {doctor_info.get('specialty', 'Unknown')}</h4>
                    <div class="detail-grid" style="grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));">
                        <div>
                            <strong>Basic Info:</strong><br>
                            Staff ID: {doctor_info.get('staff_id', 'Unknown')}<br>
                            Experience: {doctor_info.get('experience_years', 0)} years<br>
                            Current Status: {current_status.get('status', 'Unknown')}
                        </div>
                        <div>
                            <strong>Daily Metrics:</strong><br>
                            Patients Seen: {daily_metrics.get('patients_seen', 0)}<br>
                            Max Capacity: {daily_metrics.get('max_capacity', 0)}<br>
                            Utilization: {daily_metrics.get('utilization_rate', 0):.1f}%
                        </div>
                        <div>
                            <strong>Performance:</strong><br>
                            Total Consultations: {performance.get('total_consultations', 0)}<br>
                            Avg Consultation Time: {performance.get('average_consultation_time', 0):.2f} min<br>
                            Specialization Cases: {performance.get('specialization_cases', 0)}
                        </div>
                        <div>
                            <strong>Schedule:</strong><br>
                            Shift Start: {current_status.get('shift_start', 'N/A')}<br>
                            Shift End: {current_status.get('shift_end', 'N/A')}<br>
                            Available: {'Yes' if current_status.get('is_available', False) else 'No'}
                        </div>
                    </div>
                </div>
"""

    html_content += """
            </div>
        </div>

        <!-- System Metadata -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('metadata')">
                <h2>Simulation Metadata</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="metadata">
                <table class="summary-table">
                    <tr>
                        <th>Parameter</th>
                        <th>Value</th>
                    </tr>"""

    # Add metadata rows dynamically
    html_content += f"""
                    <tr>
                        <td>Export Time</td>
                        <td>{metadata.get('export_time', 'Unknown')}</td>
                    </tr>
                    <tr>
                        <td>Hospital Name</td>
                        <td>{metadata.get('hospital_name', 'Unknown')}</td>
                    </tr>
                    <tr>
                        <td>Total Patients</td>
                        <td>{metadata.get('total_patients', 0)}</td>
                    </tr>
                    <tr>
                        <td>Total Doctors</td>
                        <td>{metadata.get('total_doctors', 0)}</td>
                    </tr>
                    <tr>
                        <td>Simulation Duration</td>
                        <td>{metadata.get('simulation_duration_hours', 0):.4f} hours</td>
                    </tr>
                </table>
            </div>
        </div>

        <!-- Footer -->
        <div style="text-align: center; padding: 20px; color: #6c757d; font-size: 0.9em; background: white; border-radius: 8px; margin-top: 20px;">
            <p>Hospital Simulation System Report | Generated: """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </div>
    </div>

    <script>
        function toggleSection(sectionId) {{
            const content = document.getElementById(sectionId);
            const header = content.previousElementSibling;
            const icon = header.querySelector('.toggle-icon');
            
            if (content.classList.contains('collapsed')) {{
                content.classList.remove('collapsed');
                header.classList.remove('collapsed');
                icon.style.transform = 'rotate(0deg)';
            }} else {{
                content.classList.add('collapsed');
                header.classList.add('collapsed');
                icon.style.transform = 'rotate(-90deg)';
            }}
        }}

        function togglePatient(patientId) {{
            const details = document.getElementById(patientId);
            const header = details.previousElementSibling;
            const icon = header.querySelector('.toggle-icon');
            
            if (details.classList.contains('expanded')) {{
                details.classList.remove('expanded');
                icon.style.transform = 'rotate(-90deg)';
            }} else {{
                details.classList.add('expanded');
                icon.style.transform = 'rotate(0deg)';
            }}
        }}

        function toggleDetails(detailId) {{
            const details = document.getElementById(detailId);
            if (details.style.display === 'none' || details.style.display === '') {{
                details.style.display = 'block';
            }} else {{
                details.style.display = 'none';
            }}
        }}

        // Initialize collapsed state
        document.addEventListener('DOMContentLoaded', function() {{
            // Set initial state for section headers
            const collapsedSections = document.querySelectorAll('.section-content.collapsed');
            collapsedSections.forEach(section => {{
                const header = section.previousElementSibling;
                header.classList.add('collapsed');
            }});
        }});
    </script>
</body>
</html>
"""

    # Write HTML file
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)
    
    print(f"Comprehensive hospital report generated successfully: {output_file_path}")
    return output_file_path

# Example usage
if __name__ == "__main__":
    # Replace with your actual JSON file path
    json_file = "/Users/adamchen/Desktop/VSCode/twinhospital/exports/threaded_hospital_simulation_20250902_112412.json"
    
    try:
        output_path = generate_hospital_report(json_file)
        print(f"\nReport generated at: {output_path}")
        print("Open the HTML file in your web browser to view the report.")
        print("\nReport includes:")
        print("- Executive summary with key metrics")
        print("- Financial performance details")
        print("- Complete doctor performance data")
        print("- Resource utilization tables")
        print("- Detailed patient records with all medical info")
        print("- All test results, prescriptions, notes, and vitals")
        print("- Collapsible sections for easy navigation")
        print("- Mobile-responsive design")
    except FileNotFoundError:
        print(f"Error: Could not find the JSON file '{json_file}'")
        print("Please ensure the file path is correct.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in the input file.")
    except Exception as e:
        print(f"Error generating report: {str(e)}")