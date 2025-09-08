import json
import datetime
import threading
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse
import os

class HospitalReportServer(SimpleHTTPRequestHandler):
    """Custom HTTP server to serve JSON data and HTML."""
    
    def __init__(self, *args, json_file_path=None, **kwargs):
        self.json_file_path = json_file_path
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == self.json_file_path:
            print(f"Serving JSON data from {self.json_file_path}")
            self.serve_json_data()
        else:
            super().do_GET()
    
    def serve_json_data(self):
        """Serve the current JSON data with CORS headers."""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            
            self.wfile.write(json.dumps(data).encode('utf-8'))
            
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            error_data = {"error": str(e), "timestamp": datetime.datetime.now().isoformat()}
            self.wfile.write(json.dumps(error_data).encode('utf-8'))

def generate_realtime_hospital_report(json_file_path, output_file_path="realtime_hospital_report.html", 
                                    update_interval=5, port=8000):
    """
    Generate a real-time updating HTML report from hospital simulation JSON data.
    
    Args:
        json_file_path (str): Path to the JSON file
        output_file_path (str): Path for the output HTML file
        update_interval (int): Update interval in seconds
        port (int): Port for the local HTTP server
    """
    
    # Read initial JSON data
    try:
        with open(json_file_path, 'r', encoding='utf-8') as file:
            initial_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading initial data: {e}")
        return None
    
    # Detect data format
    is_realtime = 'real_time_data' in initial_data
    metadata = initial_data.get('simulation_metadata', {})

    json_data_path = "exports/" + json_file_path.split('/')[-1]
    
    # Generate the real-time HTML content
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real-Time Hospital Simulation - {metadata.get('hospital_name', 'Unknown Hospital')}</title>
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
            position: relative;
        }}
        
        .real-time-indicator {{
            position: absolute;
            top: 15px;
            right: 20px;
            display: flex;
            align-items: center;
            font-size: 0.9em;
        }}
        
        .status-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }}
        
        .status-dot.connected {{
            background-color: #28a745;
        }}
        
        .status-dot.disconnected {{
            background-color: #dc3545;
        }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
            100% {{ opacity: 1; }}
        }}
        
        .last-update {{
            font-size: 0.8em;
            opacity: 0.9;
            margin-top: 5px;
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
        
        .section-header h2 {{
            color: #495057;
            font-size: 1.2em;
            margin: 0;
        }}
        
        .section-content {{
            padding: 20px;
        }}
        
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        
        .metric-card {{
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 15px;
            text-align: center;
            transition: all 0.3s ease;
        }}
        
        .metric-card.updated {{
            background-color: #e8f5e8;
            border-color: #28a745;
            animation: highlight 2s ease;
        }}
        
        @keyframes highlight {{
            0% {{ background-color: #fff3cd; }}
            100% {{ background-color: #e8f5e8; }}
        }}
        
        .metric-value {{
            font-size: 1.8em;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }}
        
        .metric-label {{
            font-size: 0.9em;
            color: #6c757d;
        }}
        
        .table-container {{
            overflow-x: auto;
            border-radius: 6px;
            border: 1px solid #dee2e6;
        }}
        
        .data-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        
        .data-table th,
        .data-table td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        
        .data-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }}
        
        .data-table tr:hover {{
            background-color: #f8f9fa;
        }}
        
        .status-badge {{
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        
        .status-available {{ background-color: #d4edda; color: #155724; }}
        .status-busy {{ background-color: #f8d7da; color: #721c24; }}
        .status-active {{ background-color: #fff3cd; color: #856404; }}
        .status-discharged {{ background-color: #cce5ff; color: #004085; }}
        
        .error-message {{
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            padding: 10px;
            margin: 10px 0;
        }}
        
        .loading {{
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            color: #6c757d;
        }}
        
        .spinner {{
            border: 2px solid #f3f3f3;
            border-top: 2px solid #007bff;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            margin-right: 10px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        .controls {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #e9ecef;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
        }}
        
        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .btn {{
            padding: 6px 12px;
            border: 1px solid #007bff;
            background: #007bff;
            color: white;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s ease;
        }}
        
        .btn:hover {{
            background: #0056b3;
        }}
        
        .btn.btn-secondary {{
            background: #6c757d;
            border-color: #6c757d;
        }}
        
        .btn.btn-secondary:hover {{
            background: #545b62;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 4px;
            background-color: #e9ecef;
            border-radius: 2px;
            overflow: hidden;
            margin-top: 10px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #007bff, #28a745);
            transition: width 0.5s ease;
            border-radius: 2px;
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 10px; }}
            .metric-grid {{ grid-template-columns: 1fr; }}
            .controls {{ flex-direction: column; align-items: stretch; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div>
                <h1 id="hospital-name">{metadata.get('hospital_name', 'Hospital Simulation')}</h1>
                <div class="last-update">
                    Real-Time Hospital Monitoring System
                </div>
            </div>
            <div class="real-time-indicator">
                <div class="status-dot connected" id="connection-status"></div>
                <div>
                    <div id="status-text">Connected</div>
                    <div class="last-update" id="last-update">Last Update: Loading...</div>
                </div>
            </div>
        </div>

        <!-- Controls -->
        <div class="controls">
            <div class="control-group">
                <label for="update-interval">Update Interval:</label>
                <select id="update-interval">
                    <option value="1">1 second</option>
                    <option value="2">2 seconds</option>
                    <option value="5" selected>5 seconds</option>
                    <option value="10">10 seconds</option>
                    <option value="30">30 seconds</option>
                </select>
                <button class="btn" id="toggle-auto-update">Pause Updates</button>
            </div>
            <div class="control-group">
                <button class="btn btn-secondary" onclick="refreshData()">Refresh Now</button>
                <button class="btn btn-secondary" onclick="exportCurrentData()">Export Current Data</button>
            </div>
        </div>

        <!-- Executive Summary -->
        <div class="section">
            <div class="section-header">
                <h2>Executive Summary</h2>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill"></div>
                </div>
            </div>
            <div class="section-content">
                <div class="metric-grid" id="summary-metrics">
                    <!-- Metrics will be populated by JavaScript -->
                </div>
            </div>
        </div>

        <!-- Active Patients -->
        <div class="section">
            <div class="section-header">
                <h2>Active Patients (<span id="active-patients-count">0</span>)</h2>
            </div>
            <div class="section-content">
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Name</th>
                                <th>Status</th>
                                <th>Priority</th>
                                <th>Department</th>
                                <th>Arrival Time</th>
                            </tr>
                        </thead>
                        <tbody id="active-patients-table">
                            <tr>
                                <td colspan="6" class="loading">
                                    <div class="spinner"></div>
                                    Loading active patients...
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Medical Staff Status -->
        <div class="section">
            <div class="section-header">
                <h2>Medical Staff Status</h2>
            </div>
            <div class="section-content">
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Doctor</th>
                                <th>Specialty</th>
                                <th>Status</th>
                                <th>Patients Today</th>
                                <th>Available</th>
                            </tr>
                        </thead>
                        <tbody id="doctors-table">
                            <tr>
                                <td colspan="5" class="loading">
                                    <div class="spinner"></div>
                                    Loading medical staff...
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Resource Utilization -->
        <div class="section">
            <div class="section-header">
                <h2>Resource Utilization</h2>
            </div>
            <div class="section-content">
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Room Type</th>
                                <th>Total</th>
                                <th>Available</th>
                                <th>Occupied</th>
                                <th>Utilization %</th>
                            </tr>
                        </thead>
                        <tbody id="resources-table">
                            <tr>
                                <td colspan="5" class="loading">
                                    <div class="spinner"></div>
                                    Loading resources...
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Recent Activity Log -->
        <div class="section">
            <div class="section-header">
                <h2>Recent Activity (Last 10)</h2>
            </div>
            <div class="section-content">
                <div id="activity-log">
                    <div class="loading">
                        <div class="spinner"></div>
                        Loading recent activity...
                    </div>
                </div>
            </div>
        </div>

        <!-- Error Display -->
        <div id="error-display" style="display: none;">
            <div class="error-message">
                <strong>Connection Error:</strong> <span id="error-message"></span>
            </div>
        </div>
    </div>

    <script>
        let currentData = null;
        let lastUpdateTime = null;
        let updateInterval = {update_interval}; // seconds
        let autoUpdate = true;
        let updateTimer = null;
        let progressTimer = null;
        let previousMetrics = {{}};

        // Initialize the real-time monitor
        function initRealTimeMonitor() {{
            setupEventListeners();
            startAutoUpdate();
            refreshData();
        }}

        function setupEventListeners() {{
            document.getElementById('update-interval').addEventListener('change', function() {{
                updateInterval = parseInt(this.value);
                if (autoUpdate) {{
                    startAutoUpdate();
                }}
            }});

            document.getElementById('toggle-auto-update').addEventListener('click', function() {{
                autoUpdate = !autoUpdate;
                if (autoUpdate) {{
                    this.textContent = 'Pause Updates';
                    startAutoUpdate();
                }} else {{
                    this.textContent = 'Resume Updates';
                    stopAutoUpdate();
                }}
            }});
        }}

        function startAutoUpdate() {{
            stopAutoUpdate(); // Clear any existing timer
            updateTimer = setInterval(refreshData, updateInterval * 1000);
            startProgressBar();
        }}

        function stopAutoUpdate() {{
            if (updateTimer) {{
                clearInterval(updateTimer);
                updateTimer = null;
            }}
            if (progressTimer) {{
                clearInterval(progressTimer);
                progressTimer = null;
            }}
        }}

        function startProgressBar() {{
            let progress = 0;
            const progressBar = document.getElementById('progress-fill');
            
            if (progressTimer) clearInterval(progressTimer);
            
            progressTimer = setInterval(() => {{
                progress += (100 / updateInterval);
                if (progress >= 100) {{
                    progress = 0;
                }}
                progressBar.style.width = progress + '%';
            }}, 1000);
        }}

        function refreshData() {{
            fetch('{json_data_path}?t=' + new Date().getTime())
                .then(response => {{
                    if (!response.ok) {{
                        throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                    }}
                    return response.json();
                }})
                .then(data => {{
                    if (data.error) {{
                        throw new Error(data.error);
                    }}
                    updateDisplay(data);
                    updateConnectionStatus(true);
                    hideError();
                }})
                .catch(error => {{
                    console.error('Error fetching data:', error);
                    updateConnectionStatus(false);
                    showError(error.message);
                }});
        }}

        function updateDisplay(data) {{
            currentData = data;
            lastUpdateTime = new Date();
            
            // Update metadata
            const metadata = data.simulation_metadata || {{}};
            const realTimeData = data.real_time_data || {{}};
            
            document.getElementById('hospital-name').textContent = 
                metadata.hospital_name || 'Hospital Simulation';
            
            // Update summary metrics
            updateSummaryMetrics(realTimeData);
            
            // Update active patients
            updateActivePatients(realTimeData.active_patients || {{}});
            
            // Update doctors
            updateDoctorsTable(realTimeData.doctor_statuses || []);
            
            // Update resources
            updateResourcesTable(realTimeData.room_utilization || {{}});
            
            // Update activity log
            updateActivityLog(realTimeData.patient_logs || []);
            
            // Update last update time
            document.getElementById('last-update').textContent = 
                'Last Update: ' + lastUpdateTime.toLocaleTimeString();
        }}

        function updateSummaryMetrics(realTimeData) {{
            const stats = realTimeData.hospital_statistics?.patient_statistics || {{}};
            const financial = realTimeData.financial_summary || {{}};
            
            const metrics = [
                {{ label: 'Patients Processed', value: stats.total_processed || 0, key: 'patients_processed' }},
                {{ label: 'Currently Active', value: stats.currently_active || 0, key: 'active_patients' }},
                {{ label: 'Total Revenue', value: '$' + (financial.total_revenue || 0), key: 'revenue' }},
                {{ label: 'Consultations', value: stats.consultations_completed || 0, key: 'consultations' }},
                {{ label: 'Tests Performed', value: stats.tests_performed || 0, key: 'tests' }},
                {{ label: 'Net Profit', value: '$' + (financial.profit || 0), key: 'profit' }}
            ];

            const metricsContainer = document.getElementById('summary-metrics');
            metricsContainer.innerHTML = '';

            metrics.forEach(metric => {{
                const card = document.createElement('div');
                card.className = 'metric-card';
                
                // Check if value changed
                if (previousMetrics[metric.key] !== undefined && 
                    previousMetrics[metric.key] !== metric.value) {{
                    card.classList.add('updated');
                }}
                previousMetrics[metric.key] = metric.value;
                
                card.innerHTML = `
                    <div class="metric-value">${{metric.value}}</div>
                    <div class="metric-label">${{metric.label}}</div>
                `;
                metricsContainer.appendChild(card);
            }});
        }}

        function updateActivePatients(activePatients) {{
            const count = Object.keys(activePatients).length;
            document.getElementById('active-patients-count').textContent = count;
            
            const tbody = document.getElementById('active-patients-table');
            
            if (count === 0) {{
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #6c757d;">No active patients</td></tr>';
                return;
            }}
            
            tbody.innerHTML = '';
            
            Object.entries(activePatients).forEach(([id, patient]) => {{
                const row = document.createElement('tr');
                const priorityClass = patient.priority === 1 ? 'style="color: #dc3545; font-weight: bold;"' : '';
                
                row.innerHTML = `
                    <td>${{id}}</td>
                    <td>${{patient.name || 'Unknown'}}</td>
                    <td><span class="status-badge status-active">${{patient.status || 'Unknown'}}</span></td>
                    <td>${{patient.priority || 'Unknown'}}</td>
                    <td>${{patient.assigned_department || 'Unknown'}}</td>
                    <td>${{formatTime(patient.arrival_time)}}</td>
                `;
                tbody.appendChild(row);
            }});
        }}

        function updateDoctorsTable(doctors) {{
            const tbody = document.getElementById('doctors-table');
            
            if (doctors.length === 0) {{
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #6c757d;">No doctor data available</td></tr>';
                return;
            }}
            
            tbody.innerHTML = '';
            
            doctors.forEach(doctor => {{
                const row = document.createElement('tr');
                const statusClass = doctor.is_available ? 'status-available' : 'status-busy';
                
                row.innerHTML = `
                    <td>${{doctor.name || 'Unknown'}}</td>
                    <td>${{doctor.specialty || 'Unknown'}}</td>
                    <td><span class="status-badge ${{statusClass}}">${{doctor.status || 'Unknown'}}</span></td>
                    <td>${{doctor.patients_seen_today || 0}}</td>
                    <td>${{doctor.is_available ? 'Yes' : 'No'}}</td>
                `;
                tbody.appendChild(row);
            }});
        }}

        function updateResourcesTable(roomUtilization) {{
            const tbody = document.getElementById('resources-table');
            
            if (Object.keys(roomUtilization).length === 0) {{
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #6c757d;">No resource data available</td></tr>';
                return;
            }}
            
            tbody.innerHTML = '';
            
            Object.entries(roomUtilization).forEach(([roomType, data]) => {{
                const row = document.createElement('tr');
                const utilization = data.total > 0 ? ((data.occupied / data.total) * 100).toFixed(1) : 0;
                
                row.innerHTML = `
                    <td>${{roomType.charAt(0).toUpperCase() + roomType.slice(1)}}</td>
                    <td>${{data.total || 0}}</td>
                    <td>${{data.available || 0}}</td>
                    <td>${{data.occupied || 0}}</td>
                    <td>${{utilization}}%</td>
                `;
                tbody.appendChild(row);
            }});
        }}

        function updateActivityLog(patientLogs) {{
            const container = document.getElementById('activity-log');
            
            if (patientLogs.length === 0) {{
                container.innerHTML = '<div style="text-align: center; color: #6c757d;">No recent activity</div>';
                return;
            }}
            
            // Show last 10 activities
            const recentLogs = patientLogs.slice(-10).reverse();
            
            container.innerHTML = '';
            
            recentLogs.forEach(log => {{
                const logItem = document.createElement('div');
                logItem.className = 'log-entry';
                logItem.style.cssText = 'background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; padding: 8px 10px; margin: 5px 0; font-size: 0.85em;';
                
                const eventColor = log.event === 'discharge' ? '#28a745' : '#007bff';
                
                logItem.innerHTML = `
                    <div style="font-weight: bold; color: ${{eventColor}};">${{log.event?.toUpperCase() || 'UNKNOWN'}}</div>
                    <div>${{log.patient_name || 'Unknown'}} (ID: ${{log.patient_id || 'N/A'}})</div>
                    <div style="color: #6c757d; font-size: 0.9em;">${{formatTime(log.timestamp)}}</div>
                    <div style="color: #6c757d; font-size: 0.8em;">Thread: ${{log.thread_id || 'N/A'}}</div>
                `;
                container.appendChild(logItem);
            }});
        }}

        function updateConnectionStatus(connected) {{
            const statusDot = document.getElementById('connection-status');
            const statusText = document.getElementById('status-text');
            
            if (connected) {{
                statusDot.className = 'status-dot connected';
                statusText.textContent = 'Connected';
            }} else {{
                statusDot.className = 'status-dot disconnected';
                statusText.textContent = 'Disconnected';
            }}
        }}

        function showError(message) {{
            document.getElementById('error-message').textContent = message;
            document.getElementById('error-display').style.display = 'block';
        }}

        function hideError() {{
            document.getElementById('error-display').style.display = 'none';
        }}

        function formatTime(timestamp) {{
            if (!timestamp) return 'N/A';
            return new Date(timestamp).toLocaleTimeString();
        }}

        function exportCurrentData() {{
            if (!currentData) {{
                alert('No data available to export');
                return;
            }}
            
            const dataStr = JSON.stringify(currentData, null, 2);
            const dataBlob = new Blob([dataStr], {{ type: 'application/json' }});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `hospital_data_export_${{new Date().toISOString().slice(0, 19).replace(/:/g, '-')}}.json`;
            link.click();
            URL.revokeObjectURL(url);
        }}

        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', initRealTimeMonitor);
    </script>
</body>
</html>'''

    # Write HTML file
    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)
    
    print(f"Real-time hospital report generated: {output_file_path}")
    print(f"Starting HTTP server on http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    
    # Start the HTTP server
    def start_server():        
        def handler(*args, **kwargs):
            return HospitalReportServer(*args, json_file_path=json_file_path, **kwargs)
        
        server = HTTPServer(('localhost', port), handler)
        
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped by user")
            server.shutdown()
    
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    print(f"Open http://localhost:{port}/{Path(output_file_path).name} in your browser")
    
    return output_file_path, server_thread

# Example usage
if __name__ == "__main__":
    json_file = "path/to/your/continuous_hospital_simulation.json"
    
    try:
        output_path, server_thread = generate_realtime_hospital_report(
            json_file, 
            update_interval=5,  # Update every 5 seconds
            port=8000
        )
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except FileNotFoundError:
        print(f"Error: Could not find the JSON file '{json_file}'")
        print("Please ensure the file path is correct.")
    except Exception as e:
        print(f"Error: {str(e)}")