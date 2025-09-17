import threading
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import sys
import os

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.Hospital import Hospital
from backend.system import generate_doctors_from_config, generate_random_patients, setup_logging, load_config
from backend.config import get_config

class GameServer(BaseHTTPRequestHandler):
    hospital = None
    simulation_thread = None
    game_state = {
        'status': 'ready',
        'patients_total': 0,
        'patients_processed': 0
    }

    def do_GET(self):
        if self.path.startswith('/api/data'):
            self.serve_game_data()
        elif self.path.startswith('/api/config'):
            self.serve_config_data()
        elif self.path == '/' or self.path == '/game.html':
            self.serve_html()
        else:
            super().do_GET()
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        if self.path == '/api/start-simulation':
            self.start_simulation(post_data)
        elif self.path == '/api/reset-simulation':
            self.reset_simulation()

    def serve_html(self):
        try:
            html_path = Path(__file__).parent / 'frontend/game.html'
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "Game HTML file not found")

    def serve_config_data(self):
        """Serve default configuration options for frontend initialization"""
        try:
            config = get_config()
            
            config_data = {
                'specialties': config.get_specialties(),
                'room_types': list(config.hospital_data.rooms.keys()),
                'default_rooms': config.hospital_data.rooms,
                'default_doctor_per_department': config.hospital_data.doctor_per_department,
                'available_devices': config.hospital_data.devices,
                'test_categories': list(config.hospital_data.tests.keys()),
                'operation_hours': config.hospital_data.operation_hours
            }
            
            self.send_json_response(config_data)
        except Exception as e:
            self.send_json_response({'error': str(e)})

    def start_simulation(self, post_data):
        try:
            params = json.loads(post_data.decode('utf-8'))
            
            # Extract basic parameters
            patient_count = int(params.get('patient_count', 20))
            
            # Extract room configuration
            rooms_config = params.get('rooms', {})
            
            # Extract doctor department configuration  
            doctor_departments = params.get('doctor_departments', {})
            
            # Extract devices configuration
            selected_devices = params.get('devices', [])
            
            # Extract operation hours
            operation_hours = params.get('operation_hours', {})
            
            # Update config with custom values
            config = get_config()
            
            # Update room configuration
            if rooms_config:
                config.hospital_data.rooms.update(rooms_config)
            
            # Update doctor per department
            if doctor_departments:
                config.hospital_data.doctor_per_department.update(doctor_departments)
            
            # Update devices
            if selected_devices:
                config.hospital_data.devices = selected_devices
                
            # Update operation hours  
            if operation_hours:
                config.hospital_data.operation_hours.update(operation_hours)
            
            # Generate doctors and patients with updated config
            doctors = generate_doctors_from_config()
            patients = generate_random_patients(patient_count)
            
            # Create new hospital with custom configuration
            GameServer.hospital = Hospital(
                "Custom Game Hospital", 
                doctors, 
                continuous_export_enabled=False  # Disable file export for game mode
            )
            
            GameServer.game_state.update({
                'status': 'running',
                'patients_total': len(patients),
                'patients_processed': 0,
                'custom_config': {
                    'rooms': dict(config.hospital_data.rooms),
                    'departments': dict(config.hospital_data.doctor_per_department),
                    'devices_count': len(config.hospital_data.devices),
                    'operation_hours': dict(config.hospital_data.operation_hours)
                }
            })
            
            # Start simulation in background
            def run_simulation():
                max_workers = min(4, sum(doctor_departments.values()) if doctor_departments else 4)
                GameServer.hospital.process_patients_concurrently(patients, max_workers=max_workers)
                GameServer.game_state['status'] = 'completed'
            
            GameServer.simulation_thread = threading.Thread(target=run_simulation, daemon=True)
            GameServer.simulation_thread.start()
            
            self.send_json_response({
                'status': 'started',
                'config_applied': GameServer.game_state['custom_config']
            })
            
        except Exception as e:
            self.send_json_response({'status': 'error', 'message': str(e)})

    def reset_simulation(self):
        GameServer.hospital = None
        GameServer.simulation_thread = None
        GameServer.game_state = {
            'status': 'ready',
            'patients_total': 0,
            'patients_processed': 0
        }
        self.send_json_response({'status': 'reset'})

    def serve_game_data(self):
        if GameServer.hospital:
            try:
                # Get current hospital state
                current_state = GameServer.hospital._gather_current_state()
                
                # Update processed count
                processed = len([p for p in GameServer.hospital.patients.values() 
                               if p.discharge_time is not None])
                GameServer.game_state['patients_processed'] = processed
                
                # Check if completed
                if (processed >= GameServer.game_state['patients_total'] and 
                    GameServer.game_state['status'] == 'running'):
                    GameServer.game_state['status'] = 'completed'
                
                response_data = {
                    'game_state': GameServer.game_state,
                    'real_time_data': current_state
                }
            except Exception as e:
                response_data = {
                    'game_state': GameServer.game_state,
                    'real_time_data': {},
                    'error': str(e)
                }
        else:
            response_data = {
                'game_state': GameServer.game_state,
                'real_time_data': {}
            }
        
        self.send_json_response(response_data)

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

def start_game_server(port=8000):
    # Initialize configuration
    setup_logging()
    load_config("default.yaml")
    
    server = HTTPServer(('localhost', port), GameServer)
    print(f"🎮 Enhanced Hospital Simulation Game Server running at:")
    print(f"   http://localhost:{port}")
    print(f"   http://localhost:{port}/game.html")
    print("\nFeatures: Customizable rooms, departments, devices, and operation hours")
    print("Press Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Game server stopped")
        server.shutdown()

if __name__ == "__main__":
    start_game_server()