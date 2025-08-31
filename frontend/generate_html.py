import json
from datetime import datetime

def generate_hospital_report_html(json_file_path, output_html_path):
    # Load JSON data
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hospital Management Report - {data['simulation_metadata']['hospital_name']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f7fa;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .section {{
            margin-bottom: 40px;
            border-left: 4px solid #667eea;
            padding-left: 20px;
        }}
        
        .section h2 {{
            color: #667eea;
            font-size: 1.8rem;
            margin-bottom: 20px;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: #f8f9ff;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            padding: 20px;
            transition: transform 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .stat-card h3 {{
            color: #667eea;
            font-size: 1.2rem;
            margin-bottom: 15px;
        }}
        
        .stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        
        .stat-item:last-child {{
            border-bottom: none;
        }}
        
        .stat-label {{
            font-weight: 500;
            color: #666;
        }}
        
        .stat-value {{
            font-weight: bold;
            color: #333;
        }}
        
        .patient-card, .doctor-card {{
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        
        .patient-header, .doctor-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        
        .patient-name, .doctor-name {{
            font-size: 1.3rem;
            font-weight: bold;
            color: #333;
        }}
        
        .status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        
        .status.discharged {{
            background-color: #d4edda;
            color: #155724;
        }}
        
        .status.emergency {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        
        .status.available {{
            background-color: #d1ecf1;
            color: #0c5460;
        }}
        
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}
        
        .info-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .info-label {{
            font-size: 0.9rem;
            color: #666;
            margin-bottom: 5px;
        }}
        
        .info-value {{
            font-weight: 500;
            color: #333;
        }}
        
        .symptoms, .medical-history {{
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }}
        
        .symptoms span, .medical-history span {{
            display: inline-block;
            background-color: #007bff;
            color: white;
            padding: 3px 8px;
            border-radius: 12px;
            margin: 2px;
            font-size: 0.85rem;
        }}
        
        .notes {{
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-top: 15px;
        }}
        
        .note-item {{
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #f0f0f0;
        }}
        
        .note-item:last-child {{
            border-bottom: none;
            margin-bottom: 0;
        }}
        
        .note-staff {{
            font-weight: bold;
            color: #856404;
        }}
        
        .note-type {{
            font-size: 0.8rem;
            background-color: #ffc107;
            color: #212529;
            padding: 2px 6px;
            border-radius: 10px;
            margin-left: 10px;
        }}
        
        .vitals {{
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        
        .vitals-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
        }}
        
        .vital-item {{
            text-align: center;
        }}
        
        .vital-label {{
            font-size: 0.8rem;
            color: #666;
        }}
        
        .vital-value {{
            font-weight: bold;
            font-size: 1.1rem;
            color: #0056b3;
        }}
        
        .room-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }}
        
        .room-card {{
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
        }}
        
        .room-type {{
            font-weight: bold;
            color: #667eea;
            text-transform: capitalize;
            margin-bottom: 10px;
        }}
        
        .room-stats {{
            font-size: 0.9rem;
            color: #666;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                margin: 10px;
            }}
            
            .content {{
                padding: 20px;
            }}
            
            .header {{
                padding: 20px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{data['simulation_metadata']['hospital_name']}</h1>
            <p>Hospital Management System Report</p>
            <p>Generated on: {data['simulation_metadata']['export_time']}</p>
        </div>
        
        <div class="content">
            <!-- Simulation Overview -->
            <div class="section">
                <h2>Simulation Overview</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>General Statistics</h3>
                        <div class="stat-item">
                            <span class="stat-label">Total Patients:</span>
                            <span class="stat-value">{data['simulation_metadata']['total_patients']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Total Doctors:</span>
                            <span class="stat-value">{data['simulation_metadata']['total_doctors']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Duration:</span>
                            <span class="stat-value">{data['simulation_metadata']['simulation_duration_hours']:.3f} hours</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Hospital Statistics -->
            <div class="section">
                <h2>Hospital Performance</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Patient Statistics</h3>
                        <div class="stat-item">
                            <span class="stat-label">Total Processed:</span>
                            <span class="stat-value">{data['hospital_statistics']['patient_statistics']['total_processed']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Currently Active:</span>
                            <span class="stat-value">{data['hospital_statistics']['patient_statistics']['currently_active']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Consultations Completed:</span>
                            <span class="stat-value">{data['hospital_statistics']['patient_statistics']['consultations_completed']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Tests Performed:</span>
                            <span class="stat-value">{data['hospital_statistics']['patient_statistics']['tests_performed']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Prescriptions Dispensed:</span>
                            <span class="stat-value">{data['hospital_statistics']['patient_statistics']['prescriptions_dispensed']}</span>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <h3>Financial Summary</h3>
                        <div class="stat-item">
                            <span class="stat-label">Total Revenue:</span>
                            <span class="stat-value">{data['hospital_statistics']['financial_summary']['total_revenue']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Total Expenses:</span>
                            <span class="stat-value">{data['hospital_statistics']['financial_summary']['total_expenses']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Profit:</span>
                            <span class="stat-value">{data['hospital_statistics']['financial_summary']['profit']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Bills Issued:</span>
                            <span class="stat-value">{data['hospital_statistics']['financial_summary']['bills_issued']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Payment Rate:</span>
                            <span class="stat-value">{data['hospital_statistics']['financial_summary']['payment_rate']}</span>
                        </div>
                    </div>
                    
                    <div class="stat-card">
                        <h3>Operational Metrics</h3>
                        <div class="stat-item">
                            <span class="stat-label">Avg Processing Time:</span>
                            <span class="stat-value">{data['hospital_statistics']['operational_metrics']['avg_patient_processing_time']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Patient Satisfaction:</span>
                            <span class="stat-value">{data['hospital_statistics']['operational_metrics']['patient_satisfaction_score']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Bed Occupancy Rate:</span>
                            <span class="stat-value">{data['hospital_statistics']['operational_metrics']['bed_occupancy_rate']}</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Equipment Utilization:</span>
                            <span class="stat-value">{data['hospital_statistics']['operational_metrics']['equipment_utilization']}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Room Utilization -->
            <div class="section">
                <h2>Room Utilization</h2>
                <div class="room-grid">
"""

    # Add room utilization data
    for room_type, room_data in data['hospital_statistics']['resource_utilization']['rooms'].items():
        html_content += f"""
                    <div class="room-card">
                        <div class="room-type">{room_type.replace('_', ' ').title()}</div>
                        <div class="room-stats">
                            <div>Total: {room_data['total']}</div>
                            <div>Available: {room_data['available']}</div>
                            <div>Occupied: {room_data['occupied']}</div>
                            <div>Utilization: {room_data['utilization_rate']}</div>
                        </div>
                    </div>
"""

    html_content += """
                </div>
            </div>
            
            <!-- Doctor Performance -->
            <div class="section">
                <h2>Doctor Performance</h2>
"""

    # Add doctor summaries
    for doctor in data['doctor_summaries']:
        html_content += f"""
                <div class="doctor-card">
                    <div class="doctor-header">
                        <div class="doctor-name">{doctor['doctor_info']['name']}</div>
                        <div class="status available">{doctor['current_status']['status']}</div>
                    </div>
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Specialty</div>
                            <div class="info-value">{doctor['doctor_info']['specialty']}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Experience</div>
                            <div class="info-value">{doctor['doctor_info']['experience_years']} years</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Patients Seen</div>
                            <div class="info-value">{doctor['daily_metrics']['patients_seen']}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Utilization Rate</div>
                            <div class="info-value">{doctor['daily_metrics']['utilization_rate']}%</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Shift Hours</div>
                            <div class="info-value">{doctor['current_status']['shift_start']} - {doctor['current_status']['shift_end']}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Max Capacity</div>
                            <div class="info-value">{doctor['daily_metrics']['max_capacity']}</div>
                        </div>
                    </div>
                </div>
"""

    html_content += """
            </div>
            
            <!-- Patient Records -->
            <div class="section">
                <h2>Patient Records</h2>
"""

    # Add patient summaries
    for patient in data['patient_summaries']:
        priority_class = "emergency" if "Emergency" in patient['visit_info']['priority'] else "discharged"
        
        html_content += f"""
                <div class="patient-card">
                    <div class="patient-header">
                        <div class="patient-name">{patient['patient_info']['name']} (ID: {patient['patient_info']['id']})</div>
                        <div class="status {priority_class}">{patient['visit_info']['current_status']}</div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <div class="info-label">Age</div>
                            <div class="info-value">{patient['patient_info']['age']}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Gender</div>
                            <div class="info-value">{patient['patient_info']['gender']}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Insurance</div>
                            <div class="info-value">{'Yes' if patient['patient_info']['insurance'] else 'No'}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Priority</div>
                            <div class="info-value">{patient['visit_info']['priority']}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Arrival Time</div>
                            <div class="info-value">{patient['visit_info']['arrival_time']}</div>
                        </div>
                        <div class="info-item">
                            <div class="info-label">Discharge Time</div>
                            <div class="info-value">{patient['visit_info']['discharge_time']}</div>
                        </div>
                    </div>
                    
                    <div class="symptoms">
                        <strong>Symptoms:</strong><br>
"""
        
        for symptom in patient['patient_info']['symptoms']:
            html_content += f"<span>{symptom}</span>"
        
        html_content += """
                    </div>
"""

        if patient['patient_info']['medical_history']:
            html_content += """
                    <div class="medical-history">
                        <strong>Medical History:</strong><br>
"""
            for condition in patient['patient_info']['medical_history']:
                html_content += f"<span>{condition}</span>"
            html_content += """
                    </div>
"""

        # Add diagnoses
        if patient['medical_record']['diagnoses']:
            html_content += """
                    <div class="info-grid">
"""
            for diagnosis in patient['medical_record']['diagnoses']:
                html_content += f"""
                        <div class="info-item">
                            <div class="info-label">Diagnosis by {diagnosis['doctor']}</div>
                            <div class="info-value">{diagnosis['diagnosis']}</div>
                        </div>
"""
            html_content += """
                    </div>
"""

        # Add vitals if available
        if patient['medical_record']['vitals']:
            vital = patient['medical_record']['vitals'][-1]  # Get the latest vitals
            html_content += f"""
                    <div class="vitals">
                        <strong>Vital Signs (Recorded by {vital['recorded_by']}):</strong>
                        <div class="vitals-grid">
                            <div class="vital-item">
                                <div class="vital-label">Temperature</div>
                                <div class="vital-value">{vital['temperature']}°C</div>
                            </div>
                            <div class="vital-item">
                                <div class="vital-label">Blood Pressure</div>
                                <div class="vital-value">{vital['blood_pressure']} mmHg</div>
                            </div>
                            <div class="vital-item">
                                <div class="vital-label">Heart Rate</div>
                                <div class="vital-value">{vital['heart_rate']} bpm</div>
                            </div>
                            <div class="vital-item">
                                <div class="vital-label">Respiratory Rate</div>
                                <div class="vital-value">{vital['respiratory_rate']}/min</div>
                            </div>
                        </div>
                    </div>
"""

        # Add tests if available
        if patient['medical_record']['tests']:
            html_content += """
                    <div class="medical-history">
                        <strong>Tests Performed:</strong><br>
"""
            for test in patient['medical_record']['tests']:
                html_content += f"<span>{test}</span>"
            html_content += """
                    </div>
"""

        # Add notes
        if patient['medical_record']['notes']:
            html_content += """
                    <div class="notes">
                        <strong>Medical Notes:</strong>
"""
            for note in patient['medical_record']['notes']:
                html_content += f"""
                        <div class="note-item">
                            <span class="note-staff">{note['staff']}</span>
                            <span class="note-type">{note['type']}</span>
                            <br>
                            {note['content']}
                        </div>
"""
            html_content += """
                    </div>
"""

        html_content += """
                </div>
"""

    html_content += """
            </div>
        </div>
    </div>
</body>
</html>
"""

    # Write HTML file
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Hospital report generated successfully: {output_html_path}")

# Usage example
if __name__ == "__main__":
    # Replace with your JSON file path and desired output path
    json_file_path = "/Users/adamchen/Desktop/VSCode/twinhospital/exports/hospital_simulation_export_20250829_163104.json"  # Path to your JSON file
    output_html_path = "hospital_report.html"  # Output HTML file path
    
    generate_hospital_report_html(json_file_path, output_html_path)