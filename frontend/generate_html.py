import json
import datetime
from pathlib import Path

def generate_hospital_report(json_file_path, output_file_path="hospital_report.html"):
    """
    Generate a comprehensive professional HTML report from hospital simulation JSON data.
    Supports both legacy and new real-time data formats.
    
    Args:
        json_file_path (str): Path to the JSON file
        output_file_path (str): Path for the output HTML file
    """
    
    # Read JSON data
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Detect data format and extract sections
    if 'real_time_data' in data:
        # New real-time format
        metadata = data.get('simulation_metadata', {})
        real_time = data.get('real_time_data', {})
        stats = real_time.get('hospital_statistics', {})
        patients = real_time.get('patients_processed', [])
        active_patients = real_time.get('active_patients', {})
        resource_logs = real_time.get('resource_logs', [])
        patient_logs = real_time.get('patient_logs', [])
        billing_records = real_time.get('billing_records', [])
        financial_summary = real_time.get('financial_summary', {})
        doctor_statuses = real_time.get('doctor_statuses', [])
        room_utilization = real_time.get('room_utilization', {})
        daily_stats = real_time.get('daily_statistics', {})
        is_realtime = True
    else:
        # Legacy format
        metadata = data.get('simulation_metadata', {})
        stats = data.get('hospital_statistics', {})
        patients = data.get('patient_summaries', [])
        doctors = data.get('doctor_summaries', [])
        active_patients = {}
        resource_logs = []
        patient_logs = []
        billing_records = []
        financial_summary = stats.get('financial_summary', {})
        doctor_statuses = []
        room_utilization = {}
        daily_stats = {}
        is_realtime = False
    
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
        
        .patient-header.active {{
            background-color: #fff3cd;
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
        
        .status-busy {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        
        .status-discharged {{
            background-color: #cce5ff;
            color: #004085;
        }}
        
        .status-active {{
            background-color: #fff3cd;
            color: #856404;
        }}
        
        .priority-emergency {{ color: #dc3545; font-weight: bold; }}
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
        
        .log-entry {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 8px 10px;
            margin: 5px 0;
            font-size: 0.85em;
            display: grid;
            grid-template-columns: auto 1fr auto auto;
            gap: 10px;
            align-items: center;
        }}
        
        .log-timestamp {{
            font-family: monospace;
            color: #6c757d;
            font-size: 0.8em;
        }}
        
        .bill-record {{
            background: #e8f5e8;
            border: 1px solid #c3e6c3;
            border-radius: 4px;
            padding: 8px 10px;
            margin: 5px 0;
            font-size: 0.85em;
            display: grid;
            grid-template-columns: auto 1fr auto auto auto;
            gap: 10px;
            align-items: center;
        }}
        
        .threading-info {{
            background-color: #f0f8ff;
            border: 1px solid #b8daff;
            border-radius: 4px;
            padding: 8px;
            margin: 8px 0;
            font-size: 0.8em;
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
            
            .log-entry,
            .bill-record {{
                grid-template-columns: 1fr;
                gap: 5px;
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
"""
    
    if is_realtime:
        html_content += f"""
                Real-Time Simulation Report | Last Update: {metadata.get('last_update', 'Unknown')} | 
                Update #{metadata.get('updates_count', 0)} | Started: {metadata.get('simulation_start', 'Unknown')}
"""
    else:
        html_content += f"""
                Simulation Report | Generated: {metadata.get('export_time', 'Unknown')} | 
                Duration: {metadata.get('simulation_duration_hours', 0):.2f} hours
"""
    
    html_content += """
            </div>
        </div>

        <!-- Executive Summary -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('summary')">
                <h2>Executive Summary</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content" id="summary">
"""

    # Handle both data formats for summary
    if is_realtime:
        patient_stats = stats.get('patient_statistics', {})
        html_content += f"""
                <table class="summary-table">
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td><strong>Patients Processed</strong></td>
                        <td>{patient_stats.get('total_processed', 0)}</td>
                        <td><strong>Currently Active</strong></td>
                        <td>{patient_stats.get('currently_active', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Total Revenue</strong></td>
                        <td>${financial_summary.get('total_revenue', 0)}</td>
                        <td><strong>Net Profit</strong></td>
                        <td>${financial_summary.get('profit', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Tests Performed</strong></td>
                        <td>{patient_stats.get('tests_performed', 0)}</td>
                        <td><strong>Bills Issued</strong></td>
                        <td>{financial_summary.get('bills_count', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>Consultations</strong></td>
                        <td>{patient_stats.get('consultations_completed', 0)}</td>
                        <td><strong>Prescriptions</strong></td>
                        <td>{patient_stats.get('prescriptions_dispensed', 0)}</td>
                    </tr>
                </table>
"""
    else:
        # Legacy format summary (keep existing logic)
        patient_stats = stats.get('patient_statistics', {})
        fin_stats = stats.get('financial_summary', {})
        op_stats = stats.get('operational_metrics', {})
        html_content += f"""
                <table class="summary-table">
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                    <tr>
                        <td><strong>Patients Processed</strong></td>
                        <td>{patient_stats.get('total_processed', 0)}</td>
                        <td><strong>Revenue</strong></td>
                        <td>{fin_stats.get('total_revenue', '$0')}</td>
                    </tr>
                    <tr>
                        <td><strong>Tests Performed</strong></td>
                        <td>{patient_stats.get('tests_performed', 0)}</td>
                        <td><strong>Net Profit</strong></td>
                        <td>{fin_stats.get('profit', '$0')}</td>
                    </tr>
                    <tr>
                        <td><strong>Consultations</strong></td>
                        <td>{patient_stats.get('consultations_completed', 0)}</td>
                        <td><strong>Payment Rate</strong></td>
                        <td>{fin_stats.get('payment_rate', '0%')}</td>
                    </tr>
                    <tr>
                        <td><strong>Patient Satisfaction</strong></td>
                        <td>{op_stats.get('patient_satisfaction_score', 'N/A')}</td>
                        <td><strong>Avg. Processing Time</strong></td>
                        <td>{op_stats.get('avg_patient_processing_time', 'N/A')}</td>
                    </tr>
                </table>
"""
    
    html_content += """
            </div>
        </div>
"""

    # Active Patients Section (only for real-time data)
    if is_realtime and active_patients:
        html_content += f"""
        <!-- Active Patients -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('active')">
                <h2>Currently Active Patients ({len(active_patients)})</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content" id="active">
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>Patient ID</th>
                            <th>Name</th>
                            <th>Status</th>
                            <th>Priority</th>
                            <th>Department</th>
                            <th>Arrival Time</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for patient_id, patient_data in active_patients.items():
            priority_class = "priority-emergency" if patient_data.get('priority', 3) == 1 else "priority-standard"
            html_content += f"""
                        <tr>
                            <td>{patient_id}</td>
                            <td>{patient_data.get('name', 'Unknown')}</td>
                            <td><span class="status-badge status-active">{patient_data.get('status', 'Unknown')}</span></td>
                            <td class="{priority_class}">{patient_data.get('priority', 'Unknown')}</td>
                            <td>{patient_data.get('assigned_department', 'Unknown')}</td>
                            <td>{patient_data.get('arrival_time', 'Unknown')}</td>
                        </tr>
"""
        
        html_content += """
                    </tbody>
                </table>
            </div>
        </div>
"""

    # Doctor Status Section
    html_content += """
        <!-- Medical Staff Status -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('doctors')">
                <h2>Medical Staff Status</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="doctors">
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>Doctor</th>
                            <th>Specialty</th>
                            <th>Status</th>
                            <th>Patients Today</th>
"""
    
    if is_realtime:
        html_content += """
                            <th>Availability</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for doctor in doctor_statuses:
            status_class = "status-available" if doctor.get('is_available', True) else "status-busy"
            html_content += f"""
                        <tr>
                            <td>{doctor.get('name', 'Unknown')}</td>
                            <td>{doctor.get('specialty', 'Unknown')}</td>
                            <td><span class="status-badge {status_class}">{doctor.get('status', 'Unknown')}</span></td>
                            <td>{doctor.get('patients_seen_today', 0)}</td>
                            <td>{'Available' if doctor.get('is_available', False) else 'Busy'}</td>
                        </tr>
"""
    else:
        html_content += """
                            <th>Utilization</th>
                            <th>Avg. Consultation</th>
                            <th>Max Capacity</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        # Handle legacy doctor data
        doctor_data = stats.get('resource_utilization', {}).get('doctors', [])
        for doctor in doctor_data:
            status_class = "status-available" if doctor.get('status') == 'Available' else "status-busy"
            html_content += f"""
                        <tr>
                            <td>{doctor.get('name', 'Unknown')}</td>
                            <td>{doctor.get('specialty', 'Unknown')}</td>
                            <td><span class="status-badge {status_class}">{doctor.get('status', 'Unknown')}</span></td>
                            <td>{doctor.get('patients_seen', 0)}</td>
                            <td>{doctor.get('utilization', '0%')}</td>
                            <td>{doctor.get('avg_consultation_time', '0min')}</td>
                            <td>{doctor.get('max_capacity', 0)}</td>
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
"""
    
    if is_realtime:
        html_content += """
                            <th>Maintenance</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for room_type, room_data in room_utilization.items():
            occupied = room_data.get('occupied', 0)
            total = room_data.get('total', 1)
            utilization = (occupied / total * 100) if total > 0 else 0
            html_content += f"""
                        <tr>
                            <td>{room_type.title()}</td>
                            <td>{room_data.get('total', 0)}</td>
                            <td>{room_data.get('available', 0)}</td>
                            <td>{room_data.get('occupied', 0)}</td>
                            <td>{room_data.get('maintenance', 0)}</td>
                        </tr>
"""
    else:
        html_content += """
                            <th>Utilization Rate</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
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
"""

    # Billing Records Section (only for real-time data)
    if is_realtime and billing_records:
        html_content += f"""
        <!-- Billing Records -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('billing')">
                <h2>Billing Records ({len(billing_records)} bills)</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="billing">
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>Bill ID</th>
                            <th>Patient</th>
                            <th>Service</th>
                            <th>Amount</th>
                            <th>Status</th>
                            <th>Insurance</th>
                            <th>Payment Time</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for bill in billing_records:
            html_content += f"""
                        <tr>
                            <td>{bill.get('bill_id', 'Unknown')}</td>
                            <td>{bill.get('patient_name', 'Unknown')} ({bill.get('patient_id', 'N/A')})</td>
                            <td>{bill.get('service', 'Unknown')}</td>
                            <td>${bill.get('amount', 0)}</td>
                            <td><span class="status-badge status-available">{bill.get('status', 'Unknown')}</span></td>
                            <td>{'Yes' if bill.get('insurance', False) else 'No'}</td>
                            <td>{bill.get('payment_time', 'N/A')}</td>
                        </tr>
"""
        
        html_content += """
                    </tbody>
                </table>
            </div>
        </div>
"""

    # Resource Logs Section (only for real-time data)
    if is_realtime and resource_logs:
        html_content += f"""
        <!-- Resource Allocation Logs -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('resource-logs')">
                <h2>Resource Allocation Logs ({len(resource_logs)} events)</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="resource-logs">
                <button class="collapsible-btn" onclick="toggleDetails('resource-log-details')">Show/Hide Detailed Logs</button>
                <div class="hidden-details" id="resource-log-details">
"""
        
        for log in resource_logs:
            action_color = "#28a745" if log.get('action') == 'release' else "#007bff"
            html_content += f"""
                    <div class="log-entry">
                        <div class="log-timestamp">{log.get('timestamp', 'Unknown')}</div>
                        <div><strong>{log.get('resource_name', 'Unknown').title()}</strong> - 
                             <span style="color: {action_color};">{log.get('action', 'Unknown').title()}</span> 
                             (Thread: {log.get('thread_id', 'Unknown')})</div>
                        <div>Available: {log.get('available', 0)}/{log.get('total', 0)}</div>
                        <div>Utilization: {log.get('utilization_rate', 0):.1f}%</div>
                    </div>
"""
        
        html_content += """
                </div>
            </div>
        </div>
"""

    # Patient Logs Section (only for real-time data)
    if is_realtime and patient_logs:
        html_content += f"""
        <!-- Patient Activity Logs -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('patient-logs')">
                <h2>Patient Activity Logs ({len(patient_logs)} events)</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="patient-logs">
                <table class="summary-table">
                    <thead>
                        <tr>
                            <th>Event</th>
                            <th>Patient</th>
                            <th>Timestamp</th>
                            <th>Priority</th>
                            <th>Insurance</th>
                            <th>Stay Duration</th>
                            <th>Thread</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for log in patient_logs:
            event_color = "#28a745" if log.get('event') == 'discharge' else "#007bff"
            stay_duration = f"{log.get('total_stay_hours', 0):.2f}h" if log.get('total_stay_hours') else 'N/A'
            html_content += f"""
                        <tr>
                            <td><span style="color: {event_color}; font-weight: bold;">{log.get('event', 'Unknown').title()}</span></td>
                            <td>{log.get('patient_name', 'Unknown')} ({log.get('patient_id', 'N/A')})</td>
                            <td>{log.get('timestamp', 'Unknown')}</td>
                            <td>{log.get('priority', 'N/A')}</td>
                            <td>{'Yes' if log.get('insurance', False) else 'No'}</td>
                            <td>{stay_duration}</td>
                            <td>{log.get('thread_id', 'N/A')}</td>
                        </tr>
"""
        
        html_content += """
                    </tbody>
                </table>
            </div>
        </div>
"""

    # Patient Details Section
    html_content += f"""
        <!-- Patient Visit Details -->
        <div class="section">
            <div class="section-header" onclick="toggleSection('patients')">
                <h2>Patient Visit Details ({len(patients)} patients)</h2>
                <span class="toggle-icon">▼</span>
            </div>
            <div class="section-content collapsed" id="patients">
"""

    # Add patient details
    for i, patient in enumerate(patients, 1):
        patient_info = patient.get('patient_info', {})
        visit_info = patient.get('visit_info', {})
        medical_record = patient.get('medical_record', {})
        threading_info = patient.get('threading_info', {})
        
        # Format basic info
        symptoms = ', '.join(patient_info.get('symptoms', [])) or 'None reported'
        medical_history = ', '.join(patient_info.get('medical_history', [])) or 'None'
        insurance_status = "Insured" if patient_info.get('insurance', False) else "Uninsured"
        
        # Get diagnosis
        diagnoses = medical_record.get('diagnoses', [])
        diagnosis_info = diagnoses[0] if diagnoses else {}
        
        # Check if patient is active
        current_status = visit_info.get('current_status', '')
        is_active = current_status not in ['Discharged']
        card_class = "patient-header active" if is_active else "patient-header"
        
        html_content += f"""
                <div class="patient-card">
                    <div class="{card_class}" onclick="togglePatient('patient{i}')">
                        <div>
                            <h3>{patient_info.get('name', 'Unknown')} (ID: {patient_info.get('id', 'Unknown')})</h3>
                            <div class="patient-basic-info">
                                Age: {patient_info.get('age', 'Unknown')} | Gender: {patient_info.get('gender', 'Unknown')} | 
                                {insurance_status} | Priority: {visit_info.get('priority', 'Unknown')} | 
                                Status: <span class="status-badge {'status-active' if is_active else 'status-discharged'}">{current_status}</span>
"""
        
        if patient_info.get('assigned_department'):
            html_content += f" | Department: {patient_info.get('assigned_department')}"
        
        html_content += f"""
                            </div>
                        </div>
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="patient-details" id="patient{i}">
                        <div class="detail-grid">
                            <div class="detail-section">
                                <h4>Visit Information</h4>
                                <ul class="detail-list">
                                    <li><strong>Arrival:</strong> {visit_info.get('arrival_time', 'Unknown')}</li>
                                    <li><strong>Discharge:</strong> {visit_info.get('discharge_time', 'Not yet discharged' if not visit_info.get('discharge_time') else visit_info.get('discharge_time'))}</li>
                                    <li><strong>Waiting Time:</strong> {patient.get('waiting_time_seconds', 0)} seconds</li>
                                    <li><strong>Symptoms:</strong> {symptoms}</li>
                                    <li><strong>Medical History:</strong> {medical_history}</li>
"""
        
        if patient_info.get('consultation_history'):
            consultation_history = ', '.join(patient_info.get('consultation_history', []))
            html_content += f"""
                                    <li><strong>Consultation History:</strong> {consultation_history}</li>
"""
        
        html_content += """
                                </ul>
                            </div>
                            
                            <div class="detail-section">
                                <h4>Diagnosis & Treatment</h4>
                                <ul class="detail-list">
"""
        
        if diagnosis_info:
            html_content += f"""
                                    <li><strong>Diagnosis:</strong> {diagnosis_info.get('diagnosis', 'No diagnosis recorded')}</li>
                                    <li><strong>Diagnosing Doctor:</strong> {diagnosis_info.get('doctor', 'Unknown')}</li>
                                    <li><strong>Diagnosis Time:</strong> {diagnosis_info.get('timestamp', 'N/A')}</li>
                                    <li><strong>Status:</strong> {diagnosis_info.get('status', 'N/A')}</li>
"""
            if diagnosis_info.get('thread_id'):
                html_content += f"""
                                    <li><strong>Thread ID:</strong> {diagnosis_info.get('thread_id')}</li>
"""
        else:
            html_content += """
                                    <li><strong>Diagnosis:</strong> No diagnosis recorded yet</li>
"""
        
        html_content += """
                                </ul>
                            </div>
                        </div>
"""

        # Add threading information if available
        if threading_info:
            html_content += f"""
                        <div class="threading-info">
                            <strong>Threading Information:</strong> 
                            Thread Safe: {threading_info.get('thread_safe', 'Unknown')} | 
                            Total Operations: {threading_info.get('total_concurrent_operations', 0)} | 
                            Operations by Thread: {threading_info.get('operations_by_thread', {})} |
                            Processing Thread: {threading_info.get('processing_thread', 'None')}
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
"""
                if vital.get('thread_id'):
                    html_content += f"""
                                <div style="font-size: 0.8em; color: #6c757d; margin-top: 5px;">Thread: {vital.get('thread_id')}</div>
"""
                html_content += """
                            </div>
"""
            html_content += """
                        </div>
"""

        # Add prescriptions
        prescriptions = medical_record.get('prescriptions', [])
        if prescriptions:
            html_content += f"""
                        <div class="detail-section">
                            <h4>Prescriptions ({len(prescriptions)})</h4>
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
                            <h4>Consultations ({len(consultations)})</h4>
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
                                        <div style="font-size: 0.8em; color: #6c757d; margin-bottom: 5px;">
                                            {note.get('timestamp', 'Unknown time')}
"""
                if note.get('thread_id'):
                    html_content += f" | Thread: {note.get('thread_id')}"
                
                html_content += f"""
                                        </div>
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

    html_content += """
            </div>
        </div>
"""

    # Financial Details Section
    html_content += """
        <!-- Financial Performance -->
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
"""
    
    if is_realtime:
        html_content += f"""
                    <tr>
                        <td>Total Revenue</td>
                        <td>${financial_summary.get('total_revenue', 0)}</td>
                        <td>Revenue from all patient services</td>
                    </tr>
                    <tr>
                        <td>Total Expenses</td>
                        <td>${financial_summary.get('total_expenses', 0)}</td>
                        <td>Operational costs and overhead</td>
                    </tr>
                    <tr>
                        <td>Net Profit</td>
                        <td>${financial_summary.get('profit', 0)}</td>
                        <td>Revenue minus expenses</td>
                    </tr>
                    <tr>
                        <td>Bills Count</td>
                        <td>{financial_summary.get('bills_count', 0)}</td>
                        <td>Total number of bills generated</td>
                    </tr>
"""
    else:
        fin_stats = stats.get('financial_summary', {})
        html_content += f"""
                    <tr>
                        <td>Total Revenue</td>
                        <td>{fin_stats.get('total_revenue', '$0')}</td>
                        <td>Revenue from all patient services</td>
                    </tr>
                    <tr>
                        <td>Total Expenses</td>
                        <td>{fin_stats.get('total_expenses', '$0')}</td>
                        <td>Operational costs and overhead</td>
                    </tr>
                    <tr>
                        <td>Net Profit</td>
                        <td>{fin_stats.get('profit', '$0')}</td>
                        <td>Revenue minus expenses</td>
                    </tr>
                    <tr>
                        <td>Bills Issued</td>
                        <td>{fin_stats.get('bills_issued', 0)}</td>
                        <td>Total number of bills generated</td>
                    </tr>
                    <tr>
                        <td>Payment Rate</td>
                        <td>{fin_stats.get('payment_rate', '0%')}</td>
                        <td>Percentage of bills paid</td>
                    </tr>
"""
    
    html_content += """
                </table>
            </div>
        </div>
"""

    # Operational Details Section
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
"""
    
    if hospital_info.get('operation_hours'):
        html_content += f"""
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
"""

    # Add daily statistics if available (real-time format)
    if is_realtime and daily_stats:
        html_content += """
                    <div class="detail-section">
                        <h4>Daily Statistics</h4>
                        <ul class="detail-list">
"""
        html_content += f"""
                            <li><strong>Patients Processed:</strong> {daily_stats.get('patients_processed', 0)}</li>
                            <li><strong>Consultations Completed:</strong> {daily_stats.get('consultations_completed', 0)}</li>
                            <li><strong>Tests Performed:</strong> {daily_stats.get('tests_performed', 0)}</li>
                            <li><strong>Prescriptions Dispensed:</strong> {daily_stats.get('prescriptions_dispensed', 0)}</li>
"""
        html_content += """
                        </ul>
                    </div>
"""

    # Add operational metrics if available (legacy format)
    if not is_realtime:
        operational_metrics = stats.get('operational_metrics', {})
        if operational_metrics:
            html_content += """
                    <div class="detail-section">
                        <h4>Operational Metrics</h4>
                        <ul class="detail-list">
"""
            html_content += f"""
                            <li><strong>Avg. Processing Time:</strong> {operational_metrics.get('avg_patient_processing_time', 'N/A')}</li>
                            <li><strong>Patient Satisfaction:</strong> {operational_metrics.get('patient_satisfaction_score', 'N/A')}</li>
                            <li><strong>Bed Occupancy Rate:</strong> {operational_metrics.get('bed_occupancy_rate', 'N/A')}</li>
                            <li><strong>Equipment Utilization:</strong> {operational_metrics.get('equipment_utilization', 'N/A')}</li>
"""
            html_content += """
                        </ul>
                    </div>
"""

    html_content += """
                </div>
            </div>
        </div>
"""

    # Simulation Metadata Section
    html_content += """
        <!-- Simulation Metadata -->
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
                    </tr>
"""
    
    # Add all metadata fields dynamically
    for key, value in metadata.items():
        display_key = key.replace('_', ' ').title()
        html_content += f"""
                    <tr>
                        <td>{display_key}</td>
                        <td>{value}</td>
                    </tr>
"""
    
    # Add real-time specific metadata
    if is_realtime and real_time.get('snapshot_time'):
        html_content += f"""
                    <tr>
                        <td>Snapshot Time</td>
                        <td>{real_time.get('snapshot_time')}</td>
                    </tr>
"""
    
    html_content += """
                </table>
            </div>
        </div>

        <!-- Footer -->
        <div style="text-align: center; padding: 20px; color: #6c757d; font-size: 0.9em; background: white; border-radius: 8px; margin-top: 20px;">
            <p>Hospital Simulation System Report | Generated: """ + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + f" | Format: {'Real-Time Data' if is_realtime else 'Legacy Export'}" + """</p>
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
    json_file = "/Users/adamchen/Desktop/VSCode/twinhospital/exports/continuous_hospital_simulation_20250904_112303.json"  # Change this to your file name
    
    try:
        output_path = generate_hospital_report(json_file)
    except FileNotFoundError:
        print(f"Error: Could not find the JSON file '{json_file}'")
        print("Please ensure the file path is correct.")
    except json.JSONDecodeError:
        print("Error: Invalid JSON format in the input file.")
    except Exception as e:
        print(f"Error generating report: {str(e)}")