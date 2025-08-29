import json
from datetime import datetime

def generate_report_html(json_data):
    """
    Generates the complete HTML string for the report from JSON data.
    
    Args:
        json_data (dict): The dictionary loaded from the JSON file.
        
    Returns:
        str: A string containing the full HTML report.
    """
    meta = json_data.get("simulation_metadata", {})
    stats = json_data.get("hospital_statistics", {})
    patient_summaries = json_data.get("patient_summaries", [])
    doctor_summaries = json_data.get("doctor_summaries", [])

    # --- Helper function to format dates/times ---
    def format_datetime(dt_str, time_only=False):
        try:
            dt_obj = datetime.fromisoformat(dt_str)
            return dt_obj.strftime('%H:%M:%S') if time_only else dt_obj.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return "N/A"

    # --- Build HTML sections ---

    # Header Section
    header_html = f"""
        <div class="card p-6">
            <h1 class="text-3xl font-bold text-gray-800">{meta.get("hospital_name", "N/A")}</h1>
            <p class="text-lg text-gray-600">Simulation Analysis Report</p>
            <div class="mt-4 border-t pt-4 flex flex-wrap gap-x-8 gap-y-2 text-sm text-gray-500">
                <span><strong>Report Generated:</strong> {format_datetime(meta.get("export_time"))}</span>
                <span><strong>Total Patients:</strong> {meta.get("total_patients", 0)}</span>
                <span><strong>Total Doctors:</strong> {meta.get("total_doctors", 0)}</span>
                <span><strong>Simulation Duration:</strong> {meta.get("simulation_duration_hours", 0) * 60:.2f} minutes</span>
            </div>
        </div>
    """

    # Hospital Statistics Section
    patient_stats = stats.get("patient_statistics", {})
    financial_summary = stats.get("financial_summary", {})
    op_metrics = stats.get("operational_metrics", {})
    hospital_info = stats.get("hospital_info", {})
    
    stats_html = f"""
        <div class="card p-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">Hospital Statistics</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div class="bg-blue-50 p-4 rounded-lg">
                    <h3 class="font-semibold text-blue-800">Patient Flow</h3>
                    <p class="text-3xl font-bold text-blue-900">{patient_stats.get("total_processed", 0)}</p>
                    <p class="text-sm text-blue-700">Total Patients Processed</p>
                    <div class="mt-2 text-sm space-y-1 text-blue-600">
                        <p>Consultations: {patient_stats.get("consultations_completed", 0)}</p>
                        <p>Tests Performed: {patient_stats.get("tests_performed", 0)}</p>
                    </div>
                </div>
                <div class="bg-green-50 p-4 rounded-lg">
                    <h3 class="font-semibold text-green-800">Financial Summary</h3>
                    <p class="text-3xl font-bold text-green-900">{financial_summary.get("profit", "$0.00")}</p>
                    <p class="text-sm text-green-700">Total Profit</p>
                     <div class="mt-2 text-sm space-y-1 text-green-600">
                        <p>Revenue: {financial_summary.get("total_revenue", "$0.00")}</p>
                        <p>Payment Rate: {financial_summary.get("payment_rate", "0.0%")}</p>
                    </div>
                </div>
                <div class="bg-indigo-50 p-4 rounded-lg">
                    <h3 class="font-semibold text-indigo-800">Operational Metrics</h3>
                    <p class="text-3xl font-bold text-indigo-900">{op_metrics.get("avg_patient_processing_time", "N/A")}</p>
                    <p class="text-sm text-indigo-700">Avg. Processing Time</p>
                     <div class="mt-2 text-sm space-y-1 text-indigo-600">
                        <p>Patient Satisfaction: {op_metrics.get("patient_satisfaction_score", "N/A")}</p>
                        <p>Bed Occupancy: {op_metrics.get("bed_occupancy_rate", "0.0%")}</p>
                    </div>
                </div>
                <div class="bg-gray-50 p-4 rounded-lg">
                    <h3 class="font-semibold text-gray-800">General Info</h3>
                    <p class="text-3xl font-bold text-gray-900">{hospital_info.get("departments", 0)}</p>
                    <p class="text-sm text-gray-700">Departments</p>
                     <div class="mt-2 text-sm space-y-1 text-gray-600">
                        <p>Doctors on Staff: {hospital_info.get("total_doctors", 0)}</p>
                        <p>Operation Hours: {hospital_info.get("operation_hours", 0):.2f}</p>
                    </div>
                </div>
            </div>
        </div>
    """
    
    # Resource Utilization Section
    resource_util = stats.get("resource_utilization", {})
    rooms = resource_util.get("rooms", {})
    doctors = resource_util.get("doctors", [])

    rooms_html = ""
    for name, data in rooms.items():
        rooms_html += f"""
            <div class="border p-3 rounded-lg text-center">
                <p class="font-semibold capitalize">{name}</p>
                <p class="text-2xl font-bold">{data.get("utilization_rate", "0.0%")}</p>
                <p class="text-xs text-gray-500">{data.get("occupied", 0)} / {data.get("total", 0)} Occupied</p>
            </div>
        """
    
    doctors_table_rows = ""
    for doc in doctors:
        status_class = 'bg-green-100 text-green-800' if doc.get("status") == 'Available' else 'bg-red-100 text-red-800'
        doctors_table_rows += f"""
            <tr>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{doc.get("name", "N/A")}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.get("specialty", "N/A")}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.get("patients_seen", 0)}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{doc.get("utilization", "0.0%")}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm"><span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full {status_class}">{doc.get("status", "N/A")}</span></td>
            </tr>
        """

    resource_html = f"""
        <div class="card p-6">
            <h2 class="text-2xl font-bold text-gray-800 mb-4">Resource Utilization</h2>
            <h3 class="text-lg font-semibold text-gray-700 mb-3">Rooms</h3>
            <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">{rooms_html}</div>
            <h3 class="text-lg font-semibold text-gray-700 mt-6 mb-3">Doctors</h3>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead><tr>
                        <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                        <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Specialty</th>
                        <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Patients Seen</th>
                        <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Utilization</th>
                        <th class="px-6 py-3 bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    </tr></thead>
                    <tbody class="bg-white divide-y divide-gray-200">{doctors_table_rows}</tbody>
                </table>
            </div>
        </div>
    """

    # Patient Summaries Section
    patients_html = ""
    for p in patient_summaries:
        p_info = p.get("patient_info", {})
        v_info = p.get("visit_info", {})
        m_record = p.get("medical_record", {})
        diagnoses = m_record.get("diagnoses", [{}])
        
        patients_html += f"""
            <div class="border rounded-lg accordion-item">
                <div class="accordion-header p-4 flex justify-between items-center bg-gray-50 rounded-t-lg">
                    <div>
                        <p class="font-semibold text-gray-800">{p_info.get("name", "N/A")} <span class="text-sm font-normal text-gray-500">(ID: {p_info.get("id", "N/A")})</span></p>
                        <p class="text-sm text-gray-600">{diagnoses[0].get("diagnosis", "N/A")}</p>
                    </div>
                    <svg class="w-6 h-6 text-gray-500 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
                <div class="accordion-content">
                    <div class="p-4 border-t grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div><strong>Age:</strong> {p_info.get("age", "N/A")}</div>
                        <div><strong>Gender:</strong> {p_info.get("gender", "N/A")}</div>
                        <div><strong>Priority:</strong> {v_info.get("priority", "N/A")}</div>
                        <div><strong>Arrival:</strong> {format_datetime(v_info.get("arrival_time"), time_only=True)}</div>
                        <div><strong>Discharge:</strong> {format_datetime(v_info.get("discharge_time"), time_only=True)}</div>
                        <div><strong>Waiting Time:</strong> {p.get("waiting_time_seconds", 0)}s</div>
                        <div class="md:col-span-3"><strong>Diagnosis:</strong> {', '.join([f'{d.get("diagnosis", "N/A")} (by Dr. {d.get("doctor", "N/A")})' for d in diagnoses])}</div>
                        <div class="md:col-span-3"><strong>Tests:</strong> {', '.join(m_record.get("tests", [])) or 'None'}</div>
                        <div class="md-col-span-3"><strong>Prescriptions:</strong> {', '.join(m_record.get("prescriptions", [])) or 'None'}</div>
                    </div>
                </div>
            </div>
        """
    patient_summaries_html = f'<div class="card p-6"><h2 class="text-2xl font-bold text-gray-800 mb-4">Patient Summaries</h2><div class="space-y-2">{patients_html}</div></div>'

    # Doctor Summaries Section
    doctors_html = ""
    for d in doctor_summaries:
        d_info = d.get("doctor_info", {})
        d_metrics = d.get("daily_metrics", {})
        d_status = d.get("current_status", {})
        
        doctors_html += f"""
             <div class="border rounded-lg accordion-item">
                <div class="accordion-header p-4 flex justify-between items-center bg-gray-50 rounded-t-lg">
                    <div>
                        <p class="font-semibold text-gray-800">Dr. {d_info.get("name", "N/A")} <span class="text-sm font-normal text-gray-500">({d_info.get("specialty", "N/A")})</span></p>
                        <p class="text-sm text-gray-600">Patients Seen: {d_metrics.get("patients_seen", 0)} | Utilization: {d_metrics.get("utilization_rate", 0.0)}%</p>
                    </div>
                    <svg class="w-6 h-6 text-gray-500 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
                <div class="accordion-content">
                    <div class="p-4 border-t grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div><strong>Staff ID:</strong> {d_info.get("staff_id", "N/A")}</div>
                        <div><strong>Experience:</strong> {d_info.get("experience_years", 0)} years</div>
                        <div><strong>Status:</strong> {d_status.get("status", "N/A")}</div>
                        <div><strong>Shift:</strong> {d_status.get("shift_start", "N/A")} - {d_status.get("shift_end", "N/A")}</div>
                        <div><strong>Avg. Consultation:</strong> {d_metrics.get("average_consultation_time_minutes", 0.0):.1f} min</div>
                    </div>
                </div>
            </div>
        """
    doctor_summaries_html = f'<div class="card p-6"><h2 class="text-2xl font-bold text-gray-800 mb-4">Doctor Summaries</h2><div class="space-y-2">{doctors_html}</div></div>'


    # --- Assemble the final HTML page ---
    full_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hospital Simulation Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #f3f4f6; }}
        .card {{ background-color: white; border-radius: 0.75rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1); }}
        .accordion-header {{ cursor: pointer; }}
        .accordion-content {{ max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; }}
        .accordion-open .accordion-content {{ max-height: 2000px; }}
        .rotate-180 {{ transform: rotate(180deg); }}
        .transition-transform {{ transition: transform 0.3s ease-in-out; }}
    </style>
</head>
<body class="p-4 sm:p-6 md:p-8">
    <div id="report-container" class="max-w-7xl mx-auto space-y-8">
        {header_html}
        {stats_html}
        {resource_html}
        {patient_summaries_html}
        {doctor_summaries_html}
    </div>
    <script>
        document.querySelectorAll('.accordion-header').forEach(header => {{
            header.addEventListener('click', () => {{
                const accordionItem = header.parentElement;
                accordionItem.classList.toggle('accordion-open');
                const icon = header.querySelector('svg');
                icon.classList.toggle('rotate-180');
            }});
        }});
    </script>
</body>
</html>
    """
    return full_html

def create_report_from_file(input_json_path, output_html_path):
    """
    Loads data from a JSON file and writes the generated HTML report to another file.
    
    Args:
        input_json_path (str): The path to the source JSON file.
        output_html_path (str): The path where the output HTML file will be saved.
    """
    try:
        with open(input_json_path, 'r') as f:
            data = json.load(f)
        
        html_content = generate_report_html(data)
        
        with open(output_html_path, 'w') as f:
            f.write(html_content)
            
        print(f"Successfully generated report at: {output_html_path}")

    except FileNotFoundError:
        print(f"Error: The file was not found at {input_json_path}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from the file at {input_json_path}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Main execution block ---
if __name__ == "__main__":
    # This is an example of how to use the function.
    # It assumes you have a file named 'report_data.json' in the same directory.
    
    # # Create a dummy JSON file for demonstration if it doesn't exist.
    # dummy_data = { "simulation_metadata": { "hospital_name": "Demo Hospital" } } # Simplified for brevity
    # try:
    #     with open("report_data.json", "x") as f:
    #         json.dump(dummy_data, f)
    #         print("Created a dummy 'report_data.json' file.")
    # except FileExistsError:
    #     pass # File already exists, no need to create it.

    # Specify the input and output file paths
    json_file = "/Users/adamchen/Desktop/VSCode/twinhospital/exports/hospital_simulation_export_20250829_103045.json"
    html_file = "hospital_report.html"
    
    # Generate the report
    create_report_from_file(json_file, html_file)
