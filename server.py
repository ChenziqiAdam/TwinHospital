import threading
import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import urllib.parse
import sys
import os
from datetime import datetime
import mimetypes  # 用于静态资源的 MIME 类型推断

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models.Hospital import Hospital
from backend.system import generate_doctors_from_config, generate_random_patients, setup_logging, load_config
from backend.config import get_config


def _now_ts():
    return int(time.time() * 1000)


def _safe_json_loads(data: bytes):
    try:
        return json.loads(data.decode("utf-8")) if data else {}
    except Exception:
        return {}


class GameServer(BaseHTTPRequestHandler):
    hospital = None
    simulation_thread = None
    game_state = {
        'status': 'ready',
        'patients_total': 0,
        'patients_processed': 0
    }

    # 轻量“互动病历”存储（与 TwinCore.sceneEvent 对接）
    # patient_id -> {identity, encounters[], orders[], tests[], prescriptions[], notes[], billing[]}
    interactive_records = {}

    # ============== HTTP 基础 ==============
    def do_OPTIONS(self):
        # 允许前端 fetch 预检通过
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        # ===== API 路由 =====
        if self.path.startswith('/api/game-data'):
            self.serve_game_data()
            return
        elif self.path.startswith('/api/report-data'):
            self.serve_report_data()
            return
        elif self.path.startswith('/api/config'):
            self.serve_config_data()
            return
        elif self.path.startswith('/api/patient/'):
            # 新增：/api/patient/<patientId>/record?visitId=...
            # 仅支持 record 读取
            parsed = urllib.parse.urlparse(self.path)
            parts = parsed.path.strip('/').split('/')
            # 期望 ['api','patient','<id>','record']
            if len(parts) >= 4 and parts[0] == 'api' and parts[1] == 'patient' and parts[3] == 'record':
                patient_id = parts[2]
                q = urllib.parse.parse_qs(parsed.query or '')
                visit_id = (q.get('visitId') or [None])[0]
                self.serve_patient_record_api(patient_id, visit_id)
                return
            else:
                self.send_json_response({'error': 'Unknown API path'}, code=404)
                return

        # ===== HTML 页路由 =====
        elif self.path == '/game.html':
            self.serve_html('game.html')
            return
        elif self.path == '/ing/lobby.html' or self.path == '/lobby.html':
            self.serve_html('ing/lobby.html')
            return
        elif self.path == '/' or self.path == '/report.html':
            self.serve_html('report.html')
            return
        elif self.path.startswith('/patient.html'):
            self.serve_patient_journey()
            return
        elif self.path == 'ing/medical_record.html':
            # 新增：富病历页（位于 frontend/medical_record.html）
            self.serve_html('ing/medical_record.html')
            return

        # ===== 静态资源（js/css/png/sprites 等）=====
        elif self.path.startswith(('/ing/', '/js/', '/assets/', '/img/', '/css/', '/sprites/', '/png/', '/static/')):
            # 将 URL 映射到 frontend 下的同名文件
            local = Path('frontend') / self.path.lstrip('/')
            self.serve_static(local)
            return

        # 兜底：如果请求恰好是 frontend 根下的其它文件（如 /twin-core.js、/favicon.ico）
        else:
            local = Path('frontend') / self.path.lstrip('/')
            if local.is_file():
                self.serve_static(local)
                return
            # 默认父类处理（可能 404）
            return super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        if self.path == '/api/start-simulation':
            self.start_simulation(post_data)
        elif self.path == '/api/reset-simulation':
            self.reset_simulation()
        elif self.path == '/api/scene-event':
            self.handle_scene_event(post_data)
        else:
            # 未知接口
            self.send_json_response({'error': f'Unknown POST path: {self.path}'}, code=404)

    # ============== 静态页（HTML） ==============
    def serve_html(self, filename='game.html'):
        # 兼容传入 'ing/lobby.html' 或 '/ing/lobby.html'
        safe_name = filename.lstrip('/')
        html_path = Path('frontend') / safe_name
        if not html_path.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(f"404 Not Found: {html_path}".encode('utf-8'))
            return

        with open(html_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    # ============== 静态资源（JS/CSS/IMG等） ==============
    def serve_static(self, abs_path: Path):
        """根据文件后缀推断 MIME 并返回静态资源"""
        if not abs_path.is_file():
            self.send_response(404)
            self.end_headers()
            self.wfile.write(f"404 Not Found: {abs_path}".encode('utf-8'))
            return
        ctype, _ = mimetypes.guess_type(str(abs_path))
        self.send_response(200)
        self.send_header('Content-Type', ctype or 'application/octet-stream')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        with open(abs_path, 'rb') as f:
            self.wfile.write(f.read())

    # ============== /patient.html 渲染（保持原样） ==============
    def serve_patient_journey(self):
        query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        patient_id = query_components.get("patient_id", [None])[0]

        if not patient_id:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Patient ID is missing")
            return

        if not GameServer.hospital or not GameServer.hospital.patients:
            self.send_response(503)
            self.end_headers()
            self.wfile.write(b"Simulation not running or no patients")
            return

        try:
            patient_id_int = int(patient_id)
            patient = GameServer.hospital.patients.get(patient_id_int)
        except (ValueError, TypeError):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid Patient ID")
            return

        if not patient:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(f"Patient with ID {patient_id} not found".encode('utf-8'))
            return

        try:
            with open("frontend/patient.html", "r", encoding="utf-8") as f:
                html_template = f.read()
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"patient.html template not found")
            return

        # Generate timeline HTML
        config = get_config()
        all_statuses = config.get_patient_statuses()
        current_status = patient.status
        completed_statuses = {record['from_status'] for record in patient.waiting_history}
        if patient.discharge_time:
            completed_statuses.add(current_status)

        status_tracker_html = ""
        for status in all_statuses:
            status_class = ""
            if status == current_status and not patient.discharge_time:
                status_class = "active"
            elif status in completed_statuses:
                status_class = "completed"
            status_tracker_html += f'''
            <div class="status-step {status_class}">
                <div class="status-dot"></div>
                <div class="status-label">{status}</div>
            </div>
            '''

        # Generate content for each panel
        personal_info_html = f"""
            <table>
                <tr><th>Attribute</th><th>Value</th></tr>
                <tr><td>Name</td><td>{patient.name}</td></tr>
                <tr><td>Age</td><td>{patient.age}</td></tr>
                <tr><td>Gender</td><td>{patient.gender}</td></tr>
                <tr><td>Symptoms</td><td>{', '.join(patient.symptoms)}</td></tr>
            </table>
        """

        financials_html = "<table><tr><th>Bill ID</th><th>Service</th><th>Amount</th><th>Status</th></tr>"
        patient_bills = [b for b in getattr(GameServer.hospital, 'billing_records', []) if
                         b.get('patient_id') == patient.id]
        if not patient_bills:
            financials_html += "<tr><td colspan='4'>No billing records found.</td></tr>"
        else:
            for bill in patient_bills:
                financials_html += f"<tr><td>{bill['bill_id']}</td><td>{bill['service']}</td><td>${bill['amount']}</td><td>{bill['status']}</td></tr>"
        financials_html += "</table>"

        diagnosis_html = "<table><tr><th>Timestamp</th><th>Diagnosis</th><th>Doctor</th></tr>"
        if not patient.medical_record['diagnoses']:
            diagnosis_html += "<tr><td colspan='3'>No diagnoses recorded.</td></tr>"
        else:
            for diagnosis in patient.medical_record['diagnoses']:
                diagnosis_html += f"<tr><td>{diagnosis['timestamp']}</td><td>{diagnosis['diagnosis']}</td><td>{diagnosis['doctor']}</td></tr>"
        diagnosis_html += "</table>"

        test_results_html = "<table><tr><th>Test Result</th></tr>"
        if not patient.medical_record['tests']:
            test_results_html += "<tr><td>No test results found.</td></tr>"
        else:
            for test in patient.medical_record['tests']:
                test_results_html += f"<tr><td>{test}</td></tr>"
        test_results_html += "</table>"

        insurance_html = f"""
            <table>
                <tr><th>Status</th><td>{'Insurance verified' if patient.insurance else 'Not Insured'}</td></tr>
            </table>
        """

        prescriptions_html = "<table><tr><th>Timestamp</th><th>Medication</th><th>Prescribed by</th></tr>"
        if not patient.medical_record['prescriptions']:
            prescriptions_html += "<tr><td colspan='3'>No prescriptions found.</td></tr>"
        else:
            for pres in patient.medical_record['prescriptions']:
                prescriptions_html += f"<tr><td>{pres['timestamp']}</td><td>{pres['medication']}</td><td>{pres['prescribed_by']}</td></tr>"
        prescriptions_html += "</table>"

        vitals_html = "<table><tr><th>Timestamp</th><th>Temp</th><th>BP</th><th>Heart Rate</th></tr>"
        if not patient.medical_record['vitals']:
            vitals_html += "<tr><td colspan='4'>No vitals recorded.</td></tr>"
        else:
            for vital in patient.medical_record['vitals']:
                vitals_html += f"<tr><td>{vital['timestamp']}</td><td>{vital['temperature']}°C</td><td>{vital['blood_pressure']}</td><td>{vital['heart_rate']} bpm</td></tr>"
        vitals_html += "</table>"

        # Replace placeholders
        html_content = html_template.replace("<h1>Welcome, John Doe</h1>", f"<h1>{patient.name}</h1>")
        html_content = html_content.replace("<p>ID: 12345</p>", f"<p>ID: {patient.id}</p>")
        html_content = html_content.replace("<!-- Status tracker will be dynamically generated -->",
                                            status_tracker_html)
        html_content = html_content.replace("<!-- Personal info content will be dynamically generated -->",
                                            personal_info_html)
        html_content = html_content.replace("<!-- Financials content will be dynamically generated -->",
                                            financials_html)
        html_content = html_content.replace("<!-- Diagnosis content will be dynamically generated -->", diagnosis_html)
        html_content = html_content.replace("<!-- Test results content will be dynamically generated -->",
                                            test_results_html)
        html_content = html_content.replace("<!-- Insurance content will be dynamically generated -->", insurance_html)
        html_content = html_content.replace("<!-- Prescriptions content will be dynamically generated -->",
                                            prescriptions_html)
        html_content = html_content.replace("<!-- Vitals content will be dynamically generated -->", vitals_html)

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    # ============== 配置 / 启停模拟（保持原样） ==============
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
            params = _safe_json_loads(post_data)

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
        GameServer.interactive_records = {}
        self.send_json_response({'status': 'reset'})

    # ============== 可视化数据（保持原有逻辑） ==============
    def serve_game_data(self):
        if GameServer.hospital:
            try:
                # Get current hospital state
                current_state = GameServer.hospital._gather_current_state()

                # Transform data for visualization
                visualization_data = {
                    'patients_processed': [],
                    'active_patients': {},
                    'doctor_statuses': []
                }

                # Process patients data
                for patient_id, patient in GameServer.hospital.patients.items():
                    if patient.discharge_time is not None:
                        # Discharged patients
                        visualization_data['patients_processed'].append({
                            'patient_info': {
                                'id': patient.id,
                                'name': patient.name,
                                'age': patient.age,
                                'gender': patient.gender,
                                'symptoms': patient.symptoms,
                                'insurance': patient.insurance
                            },
                            'visit_info': {
                                'current_status': patient.status,
                                'arrival_time': patient.arrival_time.isoformat() if patient.arrival_time else None,
                                'discharge_time': patient.discharge_time.isoformat() if patient.discharge_time else None
                            }
                        })
                    else:
                        # Active patients
                        visualization_data['active_patients'][patient_id] = {
                            'id': patient.id,
                            'name': patient.name,
                            'current_status': patient.status,
                            'age': patient.age,
                            'gender': patient.gender,
                            'symptoms': patient.symptoms
                        }

                # Process doctors data
                for doctor in GameServer.hospital.doctors:
                    visualization_data['doctor_statuses'].append({
                        'name': doctor.name,
                        'specialty': doctor.specialty,
                        'status': doctor.status,
                        'patients_seen': doctor.patients_seen_today,
                        'utilization': f"{(doctor.patients_seen_today / doctor.max_patients_per_day * 100):.1f}%" if doctor.max_patients_per_day > 0 else "0%"
                    })

                # Update processed count
                processed = len(visualization_data['patients_processed'])
                GameServer.game_state['patients_processed'] = processed

                # Check if completed
                if (processed >= GameServer.game_state['patients_total'] and
                        GameServer.game_state['status'] == 'running'):
                    GameServer.game_state['status'] = 'completed'

                if 'hospital_statistics' in current_state and 'financial_summary' in current_state[
                    'hospital_statistics']:
                    summary = current_state['hospital_statistics']['financial_summary']
                    for key in ['total_revenue', 'total_expenses', 'profit']:
                        if key in summary:
                            try:
                                summary[f'{key}_raw'] = float(summary[key].replace('$', '').replace(',', ''))
                            except (ValueError, TypeError):
                                summary[f'{key}_raw'] = 0

                response_data = {
                    'game_state': GameServer.game_state,
                    'real_time_data': visualization_data
                }
            except Exception as e:
                response_data = {
                    'game_state': GameServer.game_state,
                    'real_time_data': {
                        'patients_processed': [],
                        'active_patients': {},
                        'doctor_statuses': []
                    },
                    'error': str(e)
                }
        else:
            response_data = {
                'game_state': GameServer.game_state,
                'real_time_data': {
                    'patients_processed': [],
                    'active_patients': {},
                    'doctor_statuses': []
                }
            }

        self.send_json_response(response_data)

    def serve_report_data(self):
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

                if 'hospital_statistics' in current_state and 'financial_summary' in current_state[
                    'hospital_statistics']:
                    summary = current_state['hospital_statistics']['financial_summary']
                    for key in ['total_revenue', 'total_expenses', 'profit']:
                        if key in summary:
                            try:
                                summary[f'{key}_raw'] = float(summary[key].replace('$', '').replace(',', ''))
                            except (ValueError, TypeError):
                                summary[f'{key}_raw'] = 0

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

    # ============== 新增：前端事件粘合层 ==============
    def handle_scene_event(self, post_data):
        """接受 TwinCore.sceneEvent() 的事件，返回 delta"""
        payload = _safe_json_loads(post_data)
        if not payload:
            self.send_json_response({"ok": False, "error": "Empty or invalid JSON"}, code=400)
            return

        patient_id = payload.get("patient_id") or "P-unknown"
        room = (payload.get("room") or "unknown").lower()
        action = (payload.get("action") or payload.get("type") or "event").lower()

        # 1) 确保有一份服务端“互动病历”容器
        rec = GameServer.interactive_records.get(patient_id)
        if rec is None:
            rec = {
                "identity": {
                    "patient_id": patient_id,
                    "visit_id": payload.get("visit_id"),
                    "created_at": _now_ts()
                },
                "encounters": [],
                "orders": [],
                "tests": [],
                "prescriptions": [],
                "notes": [],
                "billing": []
            }
            GameServer.interactive_records[patient_id] = rec

        # 2) 统一写一条 encounter 记录
        enc = {
            "id": f"enc_{_now_ts()}",
            "room": room,
            "action": action,
            "detail": payload.get("choice") or payload.get("detail") or payload.get("orders"),
            "ts": payload.get("ts") or _now_ts()
        }
        rec["encounters"].append(enc)

        # 3) 最小规则：根据房间/动作，构造 delta
        delta = {"encounters": [enc]}
        notes = []

        if room == "lobby":
            if action in ("register", "dialogue_choice"):
                notes.append({"type": "system", "content": "Registration completed", "ts": _now_ts()})

        elif room == "triage":
            if action in ("describe", "dialogue_choice"):
                notes.append({"type": "system", "content": "Triage description received", "ts": _now_ts()})

        elif room == "consultation":
            if action in ("issue_orders", "order"):
                orders = payload.get("orders") or []
                for od in orders:
                    item = {
                        "id": od.get("id") or f"ord_{_now_ts()}",
                        "type": od.get("type") or "unspecified",
                        "name": od.get("name") or od.get("type") or "Order",
                        "status": "pending",
                        "createdAt": _now_ts()
                    }
                    rec["orders"].append(item)
                delta["orders"] = orders if orders else rec["orders"][-len(orders):]
                # 示例账单
                bill = {
                    "bill_id": f"B{_now_ts()}",
                    "patient_id": patient_id,
                    "service": "Consultation",
                    "amount": 50,
                    "status": "Pending",
                    "timestamp": _now_ts()
                }
                rec["billing"].append(bill)
                delta.setdefault("billing", []).append(bill)
                notes.append({"type": "system", "content": "Doctor issued orders", "ts": _now_ts()})

        elif room == "examination":
            if action in ("submit_order", "start_exam"):
                linked = payload.get("order_id") or payload.get("id")
                test_item = {
                    "id": f"test_{_now_ts()}",
                    "order_id": linked,
                    "name": payload.get("exam_name") or "Physical Examination",
                    "status": "processing",
                    "time": _now_ts()
                }
                rec["tests"].append(test_item)
                delta["tests"] = [test_item]
                notes.append({"type": "system", "content": "Examination started", "ts": _now_ts()})

        elif room == "lab":
            if action in ("submit_sample", "collect", "start_lab"):
                test_item = {
                    "id": f"lab_{_now_ts()}",
                    "name": payload.get("test_name") or "CBC",
                    "status": "processing",
                    "time": _now_ts()
                }
                rec["tests"].append(test_item)
                delta["tests"] = [test_item]
                notes.append({"type": "system", "content": "Sample submitted to lab", "ts": _now_ts()})
            elif action in ("check_result", "finish_lab"):
                test_item = {
                    "id": f"lab_{_now_ts()}",
                    "name": payload.get("test_name") or "CBC",
                    "result": payload.get("result") or "Normal",
                    "normalRange": payload.get("normalRange") or "Within range",
                    "status": "completed",
                    "time": _now_ts()
                }
                rec["tests"].append(test_item)
                delta["tests"] = [test_item]
                # 示例账单
                bill = {
                    "bill_id": f"B{_now_ts()}",
                    "patient_id": patient_id,
                    "service": f"Lab - {test_item['name']}",
                    "amount": 35,
                    "status": "Pending",
                    "timestamp": _now_ts()
                }
                rec["billing"].append(bill)
                delta.setdefault("billing", []).append(bill)
                notes.append({"type": "system", "content": "Lab result updated", "ts": _now_ts()})

        elif room == "pharmacy":
            if action in ("pickup", "dispense"):
                rx_item = {
                    "rxId": f"rx_{_now_ts()}",
                    "name": payload.get("drug_name") or "Acetaminophen",
                    "dosage": payload.get("dosage") or "500mg",
                    "usage": payload.get("usage") or "BID",
                    "count": payload.get("count") or 10,
                    "pickedAt": _now_ts()
                }
                rec["prescriptions"].append(rx_item)
                delta["prescriptions"] = [rx_item]
                # 示例账单
                bill = {
                    "bill_id": f"B{_now_ts()}",
                    "patient_id": patient_id,
                    "service": f"Pharmacy - {rx_item['name']}",
                    "amount": 12,
                    "status": "Pending",
                    "timestamp": _now_ts()
                }
                rec["billing"].append(bill)
                delta.setdefault("billing", []).append(bill)
                notes.append({"type": "system", "content": "Medication dispensed", "ts": _now_ts()})

        # 收集 notes
        if notes:
            rec["notes"].extend(notes)
            delta["notes"] = notes

        # 4) 可选：把账单同步到模拟医院（如果存在）
        if getattr(GameServer, "hospital", None) is not None:
            try:
                if not hasattr(GameServer.hospital, "billing_records") or GameServer.hospital.billing_records is None:
                    GameServer.hospital.billing_records = []
                for b in delta.get("billing", []):
                    GameServer.hospital.billing_records.append({
                        "bill_id": b.get("bill_id"),
                        "patient_id": b.get("patient_id"),
                        "service": b.get("service"),
                        "amount": b.get("amount"),
                        "status": b.get("status"),
                        "timestamp": datetime.fromtimestamp(b.get("timestamp", _now_ts()) / 1000.0)
                    })
            except Exception:
                # 同步失败不影响主流程
                pass

        # 5) 返回 delta + patient 基本信息
        resp = {
            "ok": True,
            "delta": delta,
            "patient": {"id": patient_id},
            "hospital_state": None
        }
        self.send_json_response(resp)

    # ============== 新增：富病历只读接口实现 ==============
    def serve_patient_record_api(self, patient_id: str, visit_id: str | None):
        """
        读取一份“可用于富病历渲染”的聚合数据。
        数据来源优先级：
        1) interactive_records[patient_id]（前端 TwinCore.sceneEvent 同步过来的轻量事件）
        2) hospital（若能找到该患者/账单等）
        字段缺失直接省略，由前端以 N/A 展示。
        """
        # 1) 取 interactive 侧
        inter = GameServer.interactive_records.get(patient_id) or {}

        # 2) 取 hospital 侧（如果有）
        patient_obj = None
        if getattr(GameServer, 'hospital', None) is not None:
            try:
                # hospital.patients 的 key 可能是 int；这里遍历匹配
                for pid, p in GameServer.hospital.patients.items():
                    if str(p.id) == str(patient_id):
                        patient_obj = p
                        break
            except Exception:
                patient_obj = None

        # 3) 组装 patient/visit
        patient_json = {}
        if patient_obj is not None:
            try:
                patient_json.update({
                    "id": patient_obj.id,
                    "name": getattr(patient_obj, 'name', None),
                    "gender": getattr(patient_obj, 'gender', None),
                    "age": getattr(patient_obj, 'age', None),
                })
            except Exception:
                pass

        # 用 interactive 的 identity 兜底 visit_id
        if not patient_json.get("id"):
            patient_json["id"] = inter.get("identity", {}).get("patient_id") or patient_id

        visit_json = {}
        if visit_id:
            visit_json["id"] = visit_id
        else:
            vid = inter.get("identity", {}).get("visit_id")
            if vid:
                visit_json["id"] = vid

        # 4) 组装 summary（后台目前缺，预留空结构）
        summary_json = {}
        # 若你的 Patient.medical_record 里有结构化的 cc/hpi/allergies，可在此填充
        try:
            mr = getattr(patient_obj, 'medical_record', None)
            # 示例：如果你的结构不同，按需调整键名
            # summary_json["cc"] = mr.get("cc")
            # summary_json["hpi"] = mr.get("hpi")
            # summary_json["allergies"] = mr.get("allergies")
            # summary_json["pmh"] = mr.get("pmh")
            # summary_json["meds"] = mr.get("meds")
            _ = mr  # 占位避免未使用告警
        except Exception:
            pass

        # 5) 组装四表：orders/tests/prescriptions/billing
        #   5.1 来自 interactive_records
        orders = []
        tests = []
        prescriptions = []
        billing = []

        try:
            for od in inter.get("orders", []) or []:
                orders.append({
                    "id": od.get("id"),
                    "name": od.get("name") or od.get("type"),
                    "by": None,
                    "ts": od.get("createdAt") or od.get("ts"),
                    "status": od.get("status") or "pending"
                })
        except Exception:
            pass

        try:
            for t in inter.get("tests", []) or []:
                tests.append({
                    "id": t.get("id"),
                    "name": t.get("name"),
                    "key": t.get("result") or t.get("normalRange"),
                    "ts": t.get("time"),
                    "status": t.get("status") or "processing"
                })
        except Exception:
            pass

        try:
            for rx in inter.get("prescriptions", []) or []:
                prescriptions.append({
                    "id": rx.get("rxId"),
                    "medication": rx.get("name"),
                    "sig": f"{rx.get('dosage') or ''} {rx.get('usage') or ''}".strip() or None,
                    "by": None,
                    "status": "已发药" if rx.get("pickedAt") else "未取药",
                    "ts": rx.get("pickedAt")
                })
        except Exception:
            pass

        try:
            for b in inter.get("billing", []) or []:
                billing.append({
                    "id": b.get("bill_id"),
                    "service": b.get("service"),
                    "amount": b.get("amount"),
                    "insurance": 0,            # 轻量事件侧目前没有医保拆分，先置 0
                    "status": b.get("status"),
                    "ts": b.get("timestamp")
                })
        except Exception:
            pass

        #   5.2 从 hospital.billing_records 补充（若存在）
        try:
            for b in getattr(GameServer.hospital, 'billing_records', []) or []:
                if str(b.get('patient_id')) == str(patient_id):
                    # hospital 里的 timestamp 是 datetime
                    ts = b.get('timestamp')
                    if isinstance(ts, datetime):
                        ts_ms = int(ts.timestamp() * 1000)
                    else:
                        ts_ms = None
                    billing.append({
                        "id": b.get("bill_id"),
                        "service": b.get("service"),
                        "amount": b.get("amount"),
                        "insurance": 0,
                        "status": b.get("status"),
                        "ts": ts_ms
                    })
        except Exception:
            pass

        # 6) 返回
        payload = {
            "patient": patient_json or {"id": patient_id},
            "visit": visit_json or None,
            "summary": summary_json or None,
            "orders": orders,
            "tests": tests,
            "prescriptions": prescriptions,
            "billing": billing
        }
        self.send_json_response(payload)

    # ============== 工具：JSON 响应 ==============
    def send_json_response(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())


def start_game_server(port=8000):
    # Initialize configuration
    setup_logging()
    load_config("default.yaml")

    server = HTTPServer(('localhost', port), GameServer)
    print(f"🎮 Enhanced Hospital Activity Visualization Server running at:")
    print(f"   http://localhost:{port}")
    print(f"   http://localhost:{port}/game.html")
    print(f"   http://localhost:{port}/ing/lobby.html")
    print(f"   http://localhost:{port}/medical_record.html")
    print("\nFeatures: Real-time clustered dot visualization of hospital activities")
    print("Press Ctrl+C to stop the server")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Visualization server stopped")
        server.shutdown()


if __name__ == "__main__":
    start_game_server()
