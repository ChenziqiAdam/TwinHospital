import random
import time
import threading
from datetime import datetime, timedelta
import uuid
from typing import Dict, Any, List, Optional, Tuple
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from ..config import get_config
from ..providers.llm import LLM
from ..prompts.triage_nurse import TRIAGE_NURSE_PROMPT
from ..prompts.consultation_doctor import CONSULTATION_DOCTOR_PROMPT
from ..prompts.test_examination import TEST_EXAMINATION_PROMPT
from ..prompts.test_lab import TEST_LAB_PROMPT
from ..prompts.follow_up_consultation_doctor import FOLLOW_UP_CONSULTATION_PROMPT

# Configure logger for Hospital class
logger = logging.getLogger(__name__)

class ThreadSafeHospital:
    def __init__(self, name: str, doctors: List = None, continuous_export: bool = True, 
                 export_interval: int = 30, export_on_events: bool = True):
        """
        Initializes the Hospital instance with thread-safe resource management and continuous export.
        
        Args:
            name (str): The name of the hospital.
            doctors (list, optional): A list of Doctor objects in the hospital.
            continuous_export (bool): Enable continuous JSON export during simulation.
            export_interval (int): Seconds between automatic exports (if continuous_export=True).
            export_on_events (bool): Export immediately on key events (patient admission, discharge, etc.).
        """
        config = get_config()
        self.llm = LLM(llm_config=config.llm_config)
        self.timeout = config.hospital_data.timeout
        
        # Basic hospital information
        self.id = str(uuid.uuid4())
        self.name = name
        self.doctors = doctors or []
        self.patients = {}  # Dictionary of all patients by ID
        self.active_patients = {}  # Patients currently in the hospital
        
        # Thread-safe locks for resource management
        self.rooms_lock = threading.RLock()  # Reentrant lock for room operations
        self.doctors_lock = threading.RLock()  # Reentrant lock for doctor operations
        self.devices_lock = threading.RLock()  # Reentrant lock for device operations
        self.billing_lock = threading.RLock()  # Reentrant lock for billing operations
        self.statistics_lock = threading.RLock()  # Reentrant lock for statistics
        self.patients_lock = threading.RLock()  # Reentrant lock for patient management
        
        # NEW: Continuous export configuration and locks
        self.export_lock = threading.RLock()  # Lock for export operations
        self.continuous_export_enabled = continuous_export
        self.export_interval = export_interval
        self.export_on_events = export_on_events
        self.export_file_path = None
        self.last_export_time = datetime.now()
        self.export_thread = None
        self.export_shutdown_event = threading.Event()
        
        # Initialize resources with thread safety in mind
        self.rooms = self._initialize_rooms()
        self.medical_devices = self._initialize_devices()
        self.medical_tests = self._initialize_tests()
        self.departments = self._initialize_departments()
        
        # Assign doctors to departments
        self._assign_doctors_to_departments()
        
        # Thread-safe tracking systems
        self.resource_logs = []
        self.patient_logs = []
        self.operation_logs = []
        
        # Thread-safe financial tracking
        self.revenue = 0
        self.expenses = 0
        self.billing_records = []
        
        # Operation tracking
        self.operation_start_time = datetime.now()
        self.daily_statistics = {
            "patients_processed": 0,
            "consultations_completed": 0,
            "tests_performed": 0,
            "prescriptions_dispensed": 0
        }
        
        # Thread pool for patient processing
        self.max_concurrent_patients = min(len(self.doctors) * 2, 10)  # Limit concurrent patients
        
        # NEW: Initialize continuous export system
        if self.continuous_export_enabled:
            self._initialize_continuous_export()
        
        # Log hospital initialization
        logger.info(self._format_log_entry("INITIALIZATION", 
            f"Thread-safe hospital '{name}' initialized with {len(self.doctors)} doctors and {len(self.departments)} departments"))
        logger.info(self._format_log_entry("CONTINUOUS_EXPORT", 
            f"Continuous export: {'Enabled' if continuous_export else 'Disabled'}, Interval: {export_interval}s"))
        print(self._format_console_header())
        print(self._format_console_message("INIT", 
            f"Welcome to {self.name}! Thread-safe hospital system initialized"))
        if continuous_export:
            print(self._format_console_message("EXPORT", 
                f"Continuous export enabled - Updates every {export_interval}s"))

    def _initialize_continuous_export(self) -> None:
        """Initialize the continuous export system."""
        # Create exports directory
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        
        # Set up continuous export file path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.export_file_path = export_dir / f"continuous_hospital_simulation_{timestamp}.json"
        
        # Create initial export file with metadata
        initial_data = {
            "simulation_metadata": {
                "hospital_name": self.name,
                "hospital_id": self.id,
                "simulation_start": datetime.now().isoformat(),
                "continuous_export_enabled": True,
                "export_interval_seconds": self.export_interval,
                "last_update": datetime.now().isoformat()
            },
            "real_time_data": {
                "patients_processed": [],
                "active_patients": {},
                "hospital_statistics": {},
                "resource_logs": [],
                "patient_logs": [],
                "billing_records": []
            }
        }
        
        with open(self.export_file_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, default=self._json_serializer)
        
        # Start background export thread if interval-based export is enabled
        if self.export_interval > 0:
            self.export_thread = threading.Thread(
                target=self._continuous_export_worker,
                name="ContinuousExport",
                daemon=True
            )
            self.export_thread.start()
        
        logger.info(self._format_log_entry("EXPORT_INIT", 
            f"Continuous export initialized - File: {self.export_file_path}"))

    def _continuous_export_worker(self) -> None:
        """Background worker thread for continuous export."""
        logger.info(self._format_log_entry("EXPORT_WORKER", "Continuous export worker started"))
        
        while not self.export_shutdown_event.wait(self.export_interval):
            try:
                self._update_continuous_export("scheduled_update")
            except Exception as e:
                logger.error(self._format_log_entry("EXPORT_ERROR", 
                    f"Error in continuous export worker: {str(e)}"))
        
        logger.info(self._format_log_entry("EXPORT_WORKER", "Continuous export worker stopped"))

    def _update_continuous_export(self, trigger_event: str = "manual") -> None:
        """Update the continuous export JSON file with current state."""
        if not self.continuous_export_enabled or not self.export_file_path:
            return
        
        with self.export_lock:
            try:
                # Gather current state with thread-safe locks
                current_state = self._gather_current_state()
                
                # Read existing file
                try:
                    with open(self.export_file_path, 'r', encoding='utf-8') as f:
                        export_data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    export_data = {"simulation_metadata": {}, "real_time_data": {}}
                
                # Update metadata
                export_data["simulation_metadata"].update({
                    "last_update": datetime.now().isoformat(),
                    "update_trigger": trigger_event,
                    "updates_count": export_data["simulation_metadata"].get("updates_count", 0) + 1
                })
                
                # Update real-time data
                export_data["real_time_data"] = current_state
                
                # Write updated data atomically (write to temp file then rename)
                temp_file_path = self.export_file_path.with_suffix('.tmp')
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, default=self._json_serializer)
                
                # Atomic rename
                temp_file_path.replace(self.export_file_path)
                
                self.last_export_time = datetime.now()
                
                logger.debug(self._format_log_entry("EXPORT_UPDATE", 
                    f"Continuous export updated - Trigger: {trigger_event}"))
                
            except Exception as e:
                logger.exception(self._format_log_entry("EXPORT_ERROR", 
                    f"Failed to update continuous export."))

    def _gather_current_state(self) -> Dict[str, Any]:
        """Gather current hospital state for export (thread-safe)."""
        current_state = {}
        
        # Patient information
        with self.patients_lock:
            current_state["patients_processed"] = [
                patient.get_medical_summary() for patient in self.patients.values()
            ]
            current_state["active_patients"] = {
                pid: {
                    "name": patient.name,
                    "status": patient.status,
                    "priority": patient.priority,
                    "arrival_time": patient.arrival_time.isoformat(),
                    "assigned_department": patient.assigned_department
                }
                for pid, patient in self.active_patients.items()
            }
        
        # Hospital statistics
        with self.statistics_lock:
            current_state["hospital_statistics"] = self.generate_hospital_statistics()
            current_state["daily_statistics"] = self.daily_statistics.copy()
        
        # Resource logs
        current_state["resource_logs"] = self.resource_logs[-50:]  # Last 50 entries
        current_state["patient_logs"] = self.patient_logs[-50:]    # Last 50 entries
        
        # Financial information
        with self.billing_lock:
            current_state["billing_records"] = self.billing_records[-20:]  # Last 20 bills
            current_state["financial_summary"] = {
                "total_revenue": self.revenue,
                "total_expenses": self.expenses,
                "profit": self.revenue - self.expenses,
                "bills_count": len(self.billing_records)
            }
        
        # Doctor statuses
        with self.doctors_lock:
            current_state["doctor_statuses"] = [
                {
                    "name": doctor.name,
                    "specialty": doctor.specialty,
                    "status": doctor.status,
                    "patients_seen_today": doctor.patients_seen_today,
                    "is_available": doctor.is_available()
                }
                for doctor in self.doctors
            ]
        
        # Room utilization
        with self.rooms_lock:
            current_state["room_utilization"] = self.rooms.copy()
        
        # Timestamp
        current_state["snapshot_time"] = datetime.now().isoformat()
        
        return current_state

    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _trigger_export_update(self, event_type: str) -> None:
        """Trigger an export update if event-based export is enabled."""
        if self.export_on_events and self.continuous_export_enabled:
            # Run export update in a separate thread to avoid blocking main operations
            export_thread = threading.Thread(
                target=self._update_continuous_export,
                args=(event_type,),
                daemon=True
            )
            export_thread.start()

    # Modify existing methods to include export triggers

    def admit_patient(self, patient) -> bool:
        """Thread-safe patient admission with continuous export."""
        with self.patients_lock:
            if patient.id in self.active_patients:
                logger.warning(self._format_log_entry("ADMISSION_DUPLICATE", 
                    f"Patient {patient.id} ({patient.name}) is already admitted"))
                return False
            
            self.patients[patient.id] = patient
            self.active_patients[patient.id] = patient
            
            with self.statistics_lock:
                self.daily_statistics["patients_processed"] += 1
            
            admission_record = {
                "event": "admission", "patient_id": patient.id, "patient_name": patient.name,
                "timestamp": datetime.now(), "priority": patient.priority, "insurance": patient.insurance,
                "thread_id": threading.current_thread().name
            }
            
            self.patient_logs.append(admission_record)
            
            logger.info(self._format_log_entry("PATIENT_ADMISSION", 
                f"[Thread: {threading.current_thread().name}] Patient {patient.id} ({patient.name}) admitted"))
            print(self._format_console_message("ADMISSION", 
                f"[{threading.current_thread().name}] Admitting {patient.name} - Priority {patient.priority}"))
            
            # NEW: Trigger export update
            self._trigger_export_update("patient_admission")
            
            return True

    def discharge_patient(self, patient) -> bool:
        """Thread-safe patient discharge with continuous export."""
        with self.patients_lock:
            if patient.id not in self.active_patients:
                logger.warning(self._format_log_entry("DISCHARGE_ERROR", 
                    f"Patient {patient.id} ({patient.name}) is not currently admitted"))
                return False
            
            patient.discharge()
            del self.active_patients[patient.id]
            
            total_stay = (patient.discharge_time - patient.arrival_time).total_seconds() / 3600
            
            discharge_record = {
                "event": "discharge", "patient_id": patient.id, "patient_name": patient.name,
                "timestamp": patient.discharge_time, "total_stay_hours": round(total_stay, 2),
                "diagnoses_count": len(patient.medical_record.get("diagnoses", [])),
                "prescriptions_count": len(patient.medical_record.get("prescriptions", [])),
                "thread_id": threading.current_thread().name
            }
            
            self.patient_logs.append(discharge_record)
            
            logger.info(self._format_log_entry("PATIENT_DISCHARGE", 
                f"[Thread: {threading.current_thread().name}] Patient {patient.id} discharged after {total_stay:.1f} hours"))
            print(self._format_console_message("DISCHARGE", 
                f"[{threading.current_thread().name}] {patient.name} discharged after {total_stay:.1f} hours"))
            
            # NEW: Trigger export update
            self._trigger_export_update("patient_discharge")
            
            return True

    def bill_patient(self, patient, amount: float, service_description: str) -> str:
        """Thread-safe billing with continuous export."""
        with self.billing_lock:
            bill_id = str(uuid.uuid4())[:8]
            bill = {
                "bill_id": bill_id, "patient_id": patient.id, "patient_name": patient.name,
                "amount": amount, "service": service_description, "timestamp": datetime.now(),
                "status": "Pending", "insurance": patient.insurance, "department": "General",
                "thread_id": threading.current_thread().name
            }
            
            self.billing_records.append(bill)
            
            logger.info(self._format_log_entry("BILLING", 
                f"[Thread: {threading.current_thread().name}] Bill {bill_id} created - ${amount} for {service_description}"))
            
            # NEW: Trigger export update for significant financial events
            if amount > 100:  # Only trigger for significant bills
                self._trigger_export_update("billing_event")
            
            return bill_id

    def process_payment(self, bill_id: str, amount_paid: float) -> bool:
        """Thread-safe payment processing with continuous export."""
        with self.billing_lock:
            for bill in self.billing_records:
                if bill["bill_id"] == bill_id:
                    if amount_paid >= bill["amount"]:
                        bill["status"] = "Paid"
                        bill["amount_paid"] = amount_paid
                        bill["payment_time"] = datetime.now()
                        bill["change"] = amount_paid - bill["amount"]
                        
                        self.revenue += bill["amount"]
                        
                        logger.info(self._format_log_entry("PAYMENT", 
                            f"[Thread: {threading.current_thread().name}] Payment processed - Bill {bill_id}: ${amount_paid}"))
                        
                        # NEW: Trigger export update for payments
                        self._trigger_export_update("payment_processed")
                        return True
                    else:
                        bill["status"] = "Partial Payment"
                        bill["amount_paid"] = amount_paid
                        bill["payment_time"] = datetime.now()
                        bill["remaining_balance"] = bill["amount"] - amount_paid
                        
                        self.revenue += amount_paid
                        return True
            
            logger.error(self._format_log_entry("PAYMENT_ERROR", f"Bill {bill_id} not found"))
            return False

    def get_continuous_export_status(self) -> Dict[str, Any]:
        """Get current status of continuous export system."""
        with self.export_lock:
            return {
                "enabled": self.continuous_export_enabled,
                "export_file_path": str(self.export_file_path) if self.export_file_path else None,
                "export_interval": self.export_interval,
                "export_on_events": self.export_on_events,
                "last_export_time": self.last_export_time.isoformat(),
                "export_thread_active": self.export_thread is not None and self.export_thread.is_alive(),
                "file_exists": self.export_file_path.exists() if self.export_file_path else False,
                "file_size_bytes": self.export_file_path.stat().st_size if self.export_file_path and self.export_file_path.exists() else 0
            }

    def enable_continuous_export(self, export_interval: int = 30, export_on_events: bool = True) -> bool:
        """Enable continuous export if it was disabled."""
        if self.continuous_export_enabled:
            logger.warning(self._format_log_entry("EXPORT_WARNING", "Continuous export already enabled"))
            return False
        
        self.continuous_export_enabled = True
        self.export_interval = export_interval
        self.export_on_events = export_on_events
        
        try:
            self._initialize_continuous_export()
            logger.info(self._format_log_entry("EXPORT_ENABLED", 
                f"Continuous export enabled - Interval: {export_interval}s, Events: {export_on_events}"))
            return True
        except Exception as e:
            logger.error(self._format_log_entry("EXPORT_ENABLE_ERROR", 
                f"Failed to enable continuous export: {str(e)}"))
            self.continuous_export_enabled = False
            return False

    def disable_continuous_export(self) -> bool:
        """Disable continuous export system."""
        if not self.continuous_export_enabled:
            return False
        
        with self.export_lock:
            self.continuous_export_enabled = False
            self.export_shutdown_event.set()
            
            if self.export_thread and self.export_thread.is_alive():
                self.export_thread.join(timeout=5)
            
            # Final export before shutdown
            self._update_continuous_export("shutdown")
            
            logger.info(self._format_log_entry("EXPORT_DISABLED", "Continuous export disabled"))
            return True

    def force_export_update(self) -> bool:
        """Force an immediate export update."""
        if not self.continuous_export_enabled:
            logger.warning(self._format_log_entry("EXPORT_WARNING", "Continuous export is disabled"))
            return False
        
        try:
            self._update_continuous_export("manual_force")
            logger.info(self._format_log_entry("EXPORT_FORCED", "Manual export update completed"))
            return True
        except Exception as e:
            logger.error(self._format_log_entry("EXPORT_FORCE_ERROR", 
                f"Failed to force export update: {str(e)}"))
            return False

    def cleanup_continuous_export(self) -> None:
        """Clean up continuous export system resources."""
        if self.continuous_export_enabled:
            self.disable_continuous_export()

    def __del__(self):
        """Cleanup when hospital object is destroyed."""
        try:
            self.cleanup_continuous_export()
        except:
            pass

    def _initialize_rooms(self) -> Dict[str, Dict[str, int]]:
        """Initialize room configuration from config file."""
        config = get_config()
        rooms_config = config.get_rooms_config()
        
        rooms = {}
        for room_type, total_count in rooms_config.items():
            rooms[room_type] = {
                "total": total_count,
                "available": total_count,
                "occupied": 0,
                "maintenance": 0
            }
        
        # Ensure essential room types exist
        essential_rooms = ["waiting", "consultation", "triage", "registration", "pharmacy"]
        for room_type in essential_rooms:
            if room_type not in rooms:
                rooms[room_type] = {"total": 1, "available": 1, "occupied": 0, "maintenance": 0}
        
        room_list = [f"{room_type}({room_info['total']})" for room_type, room_info in rooms.items()]
        logger.info(self._format_log_entry("ROOMS_INIT", f"Initialized rooms: {', '.join(room_list)}"))
        
        return rooms

    def _initialize_devices(self) -> Dict[str, Dict[str, Any]]:
        """Initialize medical devices from configuration."""
        config = get_config()
        device_list = config.get_devices()
        
        devices = {}
        for device in device_list:
            devices[device] = {
                "available": 1,
                "in_use": 0,
                "maintenance": 0,
                "last_maintenance": datetime.now() - timedelta(days=random.randint(1, 30)),
                "usage_hours": random.randint(100, 1000)
            }
        
        logger.info(self._format_log_entry("DEVICES_INIT", f"Initialized medical devices: {', '.join(device_list)}"))
        return devices
    
    def _initialize_tests(self) -> Dict[str, List[str]]:
        """Initialize available medical tests from configuration."""
        config = get_config()
        tests = config.get_tests()
        
        logger.info(self._format_log_entry("TESTS_INIT", 
            f"Available Tests - Examinations: {', '.join(tests['Examination'])}, Lab Tests: {', '.join(tests['Lab_Test'])}"))
        return tests

    def _initialize_departments(self) -> Dict[str, Dict[str, Any]]:
        """Initialize departments based on configuration."""
        config = get_config()
        departments_config = config.hospital_data.doctor_per_department
        
        departments = {}
        for dept_name, capacity in departments_config.items():
            departments[dept_name] = {
                "capacity": capacity * 10,
                "staff": [],
                "current_patients": 0,
                "equipment": [],
                "specialization": dept_name.lower()
            }
        
        # Add emergency department if not present
        if "Emergency" not in departments:
            departments["Emergency"] = {
                "capacity": 15, "staff": [], "current_patients": 0,
                "equipment": [], "specialization": "emergency"
            }
        
        logger.info(self._format_log_entry("DEPARTMENTS_INIT", f"Initialized departments: {', '.join(departments.keys())}"))
        return departments

    def _assign_doctors_to_departments(self) -> None:
        """Assign doctors to appropriate departments based on their specialty."""
        for doctor in self.doctors:
            specialty_lower = doctor.specialty.lower()
            assigned = False
            
            for dept_name, dept_info in self.departments.items():
                dept_specialization = dept_info["specialization"]
                if (specialty_lower in dept_specialization or 
                    dept_specialization in specialty_lower or
                    specialty_lower == dept_name.lower()):

                    dept_info["staff"].append(doctor)
                    assigned = True
                    logger.info(self._format_log_entry("DOCTOR_ASSIGNMENT", 
                        f"Dr. {doctor.name} ({doctor.specialty}) assigned to {dept_name} department"))
                    
                # Also add to Emergency if General
                if "Emergency" in self.departments and doctor.specialty == "General":
                    self.departments["Emergency"]["staff"].append(doctor)
                    logger.info(self._format_log_entry("DOCTOR_ASSIGNMENT", 
                        f"Dr. {doctor.name} ({doctor.specialty}) ALSO assigned to Emergency department"))
                    
                    break
            
            if not assigned:
                if "General" not in self.departments:
                    self.departments["General"] = {
                        "capacity": 20, "staff": [], "current_patients": 0,
                        "equipment": [], "specialization": "general"
                    }
                self.departments["General"]["staff"].append(doctor)
                logger.info(self._format_log_entry("DOCTOR_ASSIGNMENT", 
                    f"Dr. {doctor.name} ({doctor.specialty}) assigned to General department"))

    def admit_patient(self, patient) -> bool:
        """Thread-safe patient admission."""
        with self.patients_lock:
            if patient.id in self.active_patients:
                logger.warning(self._format_log_entry("ADMISSION_DUPLICATE", 
                    f"Patient {patient.id} ({patient.name}) is already admitted"))
                return False
            
            self.patients[patient.id] = patient
            self.active_patients[patient.id] = patient
            
            with self.statistics_lock:
                self.daily_statistics["patients_processed"] += 1
            
            admission_record = {
                "event": "admission", "patient_id": patient.id, "patient_name": patient.name,
                "timestamp": datetime.now(), "priority": patient.priority, "insurance": patient.insurance,
                "thread_id": threading.current_thread().name
            }
            
            self.patient_logs.append(admission_record)
            
            logger.info(self._format_log_entry("PATIENT_ADMISSION", 
                f"[Thread: {threading.current_thread().name}] Patient {patient.id} ({patient.name}) admitted"))
            print(self._format_console_message("ADMISSION", 
                f"[{threading.current_thread().name}] Admitting {patient.name} - Priority {patient.priority}"))
            
            return True

    def discharge_patient(self, patient) -> bool:
        """Thread-safe patient discharge."""
        with self.patients_lock:
            if patient.id not in self.active_patients:
                logger.warning(self._format_log_entry("DISCHARGE_ERROR", 
                    f"Patient {patient.id} ({patient.name}) is not currently admitted"))
                return False
            
            patient.discharge()
            del self.active_patients[patient.id]
            
            total_stay = (patient.discharge_time - patient.arrival_time).total_seconds() / 3600
            
            discharge_record = {
                "event": "discharge", "patient_id": patient.id, "patient_name": patient.name,
                "timestamp": patient.discharge_time, "total_stay_hours": round(total_stay, 2),
                "diagnoses_count": len(patient.medical_record.get("diagnoses", [])),
                "prescriptions_count": len(patient.medical_record.get("prescriptions", [])),
                "thread_id": threading.current_thread().name
            }
            
            self.patient_logs.append(discharge_record)
            
            logger.info(self._format_log_entry("PATIENT_DISCHARGE", 
                f"[Thread: {threading.current_thread().name}] Patient {patient.id} discharged after {total_stay:.1f} hours"))
            print(self._format_console_message("DISCHARGE", 
                f"[{threading.current_thread().name}] {patient.name} discharged after {total_stay:.1f} hours"))
            
            return True

    def allocate_room(self, room_type: str) -> bool:
        """Thread-safe room allocation with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            with self.rooms_lock:
                if room_type not in self.rooms:
                    logger.error(self._format_log_entry("ROOM_ERROR", f"Room type '{room_type}' does not exist"))
                    return False
                
                room_info = self.rooms[room_type]
                if room_info["available"] > 0:
                    room_info["available"] -= 1
                    room_info["occupied"] += 1
                    
                    utilization_record = {
                        "resource_type": "room", "resource_name": room_type, "action": "allocate",
                        "timestamp": datetime.now(), "available": room_info["available"],
                        "total": room_info["total"], "thread_id": threading.current_thread().name,
                        "utilization_rate": (room_info["occupied"] / room_info["total"]) * 100
                    }
                    
                    self.resource_logs.append(utilization_record)
                    
                    logger.info(self._format_log_entry("ROOM_ALLOCATION", 
                        f"[Thread: {threading.current_thread().name}] Allocated {room_type} room - {room_info['available']}/{room_info['total']} remaining"))
                    
                    return True
            
            # Room not available, wait briefly before retrying
            time.sleep(0.1)
        
        # Timeout reached
        logger.warning(self._format_log_entry("ROOM_TIMEOUT", 
            f"[Thread: {threading.current_thread().name}] Timeout waiting for {room_type} room"))
        print(self._format_console_message("TIMEOUT", 
            f"[{threading.current_thread().name}] Timeout waiting for {room_type} room"))
        return False

    def release_room(self, room_type: str) -> bool:
        """Thread-safe room release."""
        with self.rooms_lock:
            if room_type not in self.rooms:
                logger.error(self._format_log_entry("ROOM_ERROR", f"Room type '{room_type}' does not exist"))
                return False
            
            room_info = self.rooms[room_type]
            if room_info["occupied"] <= 0:
                logger.warning(self._format_log_entry("ROOM_RELEASE_ERROR", 
                    f"No {room_type} rooms to release"))
                return False
            
            room_info["available"] += 1
            room_info["occupied"] -= 1
            
            utilization_record = {
                "resource_type": "room", "resource_name": room_type, "action": "release",
                "timestamp": datetime.now(), "available": room_info["available"],
                "total": room_info["total"], "thread_id": threading.current_thread().name,
                "utilization_rate": (room_info["occupied"] / room_info["total"]) * 100
            }
            
            self.resource_logs.append(utilization_record)
            
            logger.info(self._format_log_entry("ROOM_RELEASE", 
                f"[Thread: {threading.current_thread().name}] Released {room_type} room - {room_info['available']}/{room_info['total']} available"))
            
            return True

    def allocate_device(self, device_name: str) -> bool:
        """Thread-safe device allocation with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < self.timeout:
            with self.devices_lock:
                if device_name not in self.medical_devices:
                    logger.warning(self._format_log_entry("DEVICE_ERROR", f"Medical device '{device_name}' not available"))
                    return False
                
                device_info = self.medical_devices[device_name]
                if device_info["available"] > 0:
                    device_info["available"] -= 1
                    device_info["in_use"] += 1
                    device_info["usage_hours"] += 1
                    
                    logger.info(self._format_log_entry("DEVICE_ALLOCATION", 
                        f"[Thread: {threading.current_thread().name}] Allocated {device_name}"))
                    return True
            
            time.sleep(0.1)  # Brief wait before retry
        
        logger.warning(self._format_log_entry("DEVICE_TIMEOUT", 
            f"[Thread: {threading.current_thread().name}] Timeout waiting for {device_name}"))
        return False

    def release_device(self, device_name: str) -> bool:
        """Thread-safe device release."""
        with self.devices_lock:
            if device_name not in self.medical_devices:
                return False
            
            device_info = self.medical_devices[device_name]
            if device_info["in_use"] <= 0:
                return False
            
            device_info["available"] += 1
            device_info["in_use"] -= 1
            
            logger.info(self._format_log_entry("DEVICE_RELEASE", 
                f"[Thread: {threading.current_thread().name}] Released {device_name}"))
            return True

    def find_and_reserve_doctor_atomic(self, patient, specialty: str = None, department: str = None):
        """
        FIXED: Thread-safe atomic doctor finding and reservation.
        This method combines doctor finding and reservation into a single atomic operation
        to prevent race conditions where multiple patients get assigned to the same doctor.
        
        Args:
            patient: The patient object that needs a doctor
            specialty (str, optional): Required doctor specialty
            department (str, optional): Required department
            
        Returns:
            Doctor object if successfully reserved, None if timeout reached
        """
        start_time = time.time()
        thread_name = threading.current_thread().name
        
        while time.time() - start_time < self.timeout:
            with self.doctors_lock:  # Global lock for doctor operations
                # Find potential doctors
                potential_doctors = []
                if department and department in self.departments:
                    potential_doctors = self.departments[department]["staff"]
                elif specialty:
                    potential_doctors = [d for d in self.doctors if specialty.lower() in d.specialty.lower()]
                else:
                    potential_doctors = self.doctors
                
                # Filter for available doctors
                available_doctors = [d for d in potential_doctors if d.is_available()]
                
                if available_doctors:
                    # Sort by workload (fewest patients first, then by experience)
                    available_doctors.sort(key=lambda d: (d.patients_seen_today, -d.years_experience))
                    
                    # ATOMIC OPERATION: Try to reserve the best available doctor
                    for doctor in available_doctors:
                        # Use doctor's own lock to atomically check and reserve
                        with doctor.consultation_lock:
                            # Double-check availability within the doctor's lock
                            if doctor.is_available():
                                # Immediately start consultation (this reserves the doctor)
                                if doctor.start_consultation(patient):
                                    logger.info(self._format_log_entry("DOCTOR_ATOMIC_ASSIGN", 
                                        f"[Thread: {thread_name}] Atomically assigned Dr. {doctor.name} to {patient.name}"))
                                    return doctor
                    
                    # If we get here, all doctors became busy between our checks
                    # This is normal concurrent behavior - just continue to retry
                    logger.debug(self._format_log_entry("DOCTOR_RACE_DETECTED", 
                        f"[Thread: {thread_name}] Doctors became busy during assignment, retrying..."))
            
            # Wait before next attempt
            time.sleep(0.2)
        
        # Timeout reached
        logger.warning(self._format_log_entry("DOCTOR_TIMEOUT", 
            f"[Thread: {thread_name}] Timeout finding available doctor for {patient.name}"))
        print(self._format_console_message("TIMEOUT", 
            f"[{thread_name}] No doctors available for {patient.name} within {self.timeout}s"))
        return None

    def bill_patient(self, patient, amount: float, service_description: str) -> str:
        """Thread-safe billing."""
        with self.billing_lock:
            bill_id = str(uuid.uuid4())[:8]
            bill = {
                "bill_id": bill_id, "patient_id": patient.id, "patient_name": patient.name,
                "amount": amount, "service": service_description, "timestamp": datetime.now(),
                "status": "Pending", "insurance": patient.insurance, "department": "General",
                "thread_id": threading.current_thread().name
            }
            
            self.billing_records.append(bill)
            
            logger.info(self._format_log_entry("BILLING", 
                f"[Thread: {threading.current_thread().name}] Bill {bill_id} created - ${amount} for {service_description}"))
            
            return bill_id

    def process_payment(self, bill_id: str, amount_paid: float) -> bool:
        """Thread-safe payment processing."""
        with self.billing_lock:
            for bill in self.billing_records:
                if bill["bill_id"] == bill_id:
                    if amount_paid >= bill["amount"]:
                        bill["status"] = "Paid"
                        bill["amount_paid"] = amount_paid
                        bill["payment_time"] = datetime.now()
                        bill["change"] = amount_paid - bill["amount"]
                        
                        self.revenue += bill["amount"]
                        
                        logger.info(self._format_log_entry("PAYMENT", 
                            f"[Thread: {threading.current_thread().name}] Payment processed - Bill {bill_id}: ${amount_paid}"))
                        return True
                    else:
                        bill["status"] = "Partial Payment"
                        bill["amount_paid"] = amount_paid
                        bill["payment_time"] = datetime.now()
                        bill["remaining_balance"] = bill["amount"] - amount_paid
                        
                        self.revenue += amount_paid
                        return True
            
            logger.error(self._format_log_entry("PAYMENT_ERROR", f"Bill {bill_id} not found"))
            return False

    def simulate_patient_visit(self, patient) -> None:
        """
        Original simulate_patient_visit method for backward compatibility.
        This is the non-threaded version that calls the threaded version internally.
        
        Args:
            patient: The patient object to process.
        """
        # For backward compatibility, run the threaded version but wait for completion
        visit_summary = self.simulate_patient_visit_threaded(patient)
        
        # Log backward compatibility usage
        logger.info(self._format_log_entry("BACKWARD_COMPAT", 
            f"Non-threaded simulate_patient_visit called for {patient.name} - redirected to threaded version"))

    def simulate_patient_visit_threaded(self, patient) -> Dict[str, Any]:
        """
        Thread-safe simulation of a complete patient visit.
        
        Args:
            patient: The patient object to process.
            
        Returns:
            Dict[str, Any]: Visit summary with outcomes and timing.
        """
        visit_start_time = datetime.now()
        thread_name = threading.current_thread().name
        visit_summary = {
            "patient_id": patient.id,
            "patient_name": patient.name,
            "thread_id": thread_name,
            "start_time": visit_start_time,
            "end_time": None,
            "success": False,
            "stages_completed": [],
            "total_cost": 0,
            "errors": []
        }
        
        print(self._format_console_message("VISIT_START", 
            f"[{thread_name}] Starting threaded visit for {patient.name}"))
        
        try:
            # Stage 1: Admit patient
            if not self.admit_patient(patient):
                visit_summary["errors"].append("Failed to admit patient")
                return visit_summary
            visit_summary["stages_completed"].append("admission")
            
            # Stage 2: Triage
            if self._simulate_triage_threaded(patient):
                visit_summary["stages_completed"].append("triage")
            else:
                visit_summary["errors"].append("Triage failed")
            
            # Stage 3: Registration
            if self._simulate_registration_threaded(patient):
                visit_summary["stages_completed"].append("registration")
            else:
                visit_summary["errors"].append("Registration failed")
            
            # Stage 4: Consultation
            needs_tests = self._simulate_consultation_threaded_fixed(patient)
            if needs_tests is not None:
                visit_summary["stages_completed"].append("consultation")
                
                # Stage 5: Tests if needed
                if needs_tests:
                    test_cost = self._simulate_tests_threaded(patient, needs_tests)
                    visit_summary["total_cost"] += test_cost
                    visit_summary["stages_completed"].append("tests")
                    
                    # Follow-up consultation
                    if self._simulate_follow_up_consultation_threaded_fixed(patient):
                        visit_summary["stages_completed"].append("follow_up")
            
            # Stage 6: Pharmacy if prescriptions
            if patient.medical_record.get("prescriptions"):
                pharmacy_cost = self._simulate_pharmacy_threaded(patient)
                visit_summary["total_cost"] += pharmacy_cost
                visit_summary["stages_completed"].append("pharmacy")
            
            visit_summary["success"] = True
            
        except Exception as e:
            error_msg = f"Error during patient visit: {str(e)}"
            visit_summary["errors"].append(error_msg)
            logger.error(self._format_log_entry("VISIT_ERROR", 
                f"[Thread: {thread_name}] {error_msg}"))
            print(self._format_console_message("ERROR", 
                f"[{thread_name}] Error in {patient.name}'s visit: {str(e)}"))
        
        finally:
            # Always discharge patient
            self.discharge_patient(patient)
            
            visit_summary["end_time"] = datetime.now()
            visit_duration = (visit_summary["end_time"] - visit_start_time).total_seconds() / 60
            visit_summary["duration_minutes"] = round(visit_duration, 2)
            
            logger.info(self._format_log_entry("VISIT_COMPLETE", 
                f"[Thread: {thread_name}] Patient visit completed in {visit_duration:.1f} minutes"))
            print(self._format_console_message("VISIT_END", 
                f"[{thread_name}] {patient.name} visit completed in {visit_duration:.1f} minutes"))
            
            return visit_summary

    def _simulate_triage_threaded(self, patient) -> bool:
        """Thread-safe triage simulation."""
        thread_name = threading.current_thread().name
        print(self._format_console_message("STAGE", f"[{thread_name}] Stage 1: Triage Assessment"))
        
        if not self.allocate_room("triage"):
            logger.warning(self._format_log_entry("TRIAGE_FAILED", 
                f"[Thread: {thread_name}] Could not allocate triage room"))
            return False
        
        try:
            patient.update_status("Triage")
            
            # Simulate triage process with LLM
            triage_prompt = TRIAGE_NURSE_PROMPT.format(
                name=patient.name, age=patient.age, gender=patient.gender,
                symptoms=patient.symptoms, medical_history=patient.medical_history,
                departments=self.departments
            )
            
            llm_response = self.llm.get_completion(prompt=triage_prompt)
            
            try:
                response = llm_response.split("```json")[1].split("```")[0].strip()
                triage_result = json.loads(response)
                
                priority = triage_result['priority']
                initial_assessment = triage_result['initial_assessment']
                vital_stats = triage_result['vital_stats']

                assigned_department = triage_result['recommended_department']
                print(self._format_console_message("DEPARTMENT", 
                    f"[{thread_name}] Assigned to {assigned_department} department"))
                
                patient.record_vitals(
                    vital_stats['temperature'], vital_stats['blood_pressure'],
                    vital_stats['heart_rate'], vital_stats['respiratory_rate']
                )
                patient.set_priority(priority)
                patient.add_note(initial_assessment, "Triage Nurse")
                patient.assigned_department = assigned_department
                
                print(self._format_console_message("VITALS", 
                    f"[{thread_name}] Vitals recorded for {patient.name}"))
                print(self._format_console_message("PRIORITY", 
                    f"[{thread_name}] Priority: {patient.priority} ({patient.priority_description})"))
                
                return True
                
            except json.JSONDecodeError as e:
                logger.error(self._format_log_entry("TRIAGE_JSON_ERROR", 
                    f"[Thread: {thread_name}] JSON decode error: {e}"))
                return False
        
        finally:
            self.release_room("triage")
            time.sleep(0.5)  # Brief processing time

    def _simulate_registration_threaded(self, patient) -> bool:
        """Thread-safe registration simulation."""
        thread_name = threading.current_thread().name
        print(self._format_console_message("STAGE", f"[{thread_name}] Stage 2: Registration"))
        
        if not self.allocate_room("registration"):
            return False
        
        try:
            patient.update_status("Registration")
            
            if not patient.has_medical_card:
                patient.has_medical_card = True
                patient.add_note("New medical card issued", "Registration Staff", "administrative")
                print(self._format_console_message("INFO", f"[{thread_name}] Medical card created"))
            else:
                print(self._format_console_message("INFO", f"[{thread_name}] Medical card verified"))
            
            if patient.insurance:
                patient.add_note(f"Insurance verified: {patient.insurance}", "Registration Staff", "administrative")
                print(self._format_console_message("INFO", f"[{thread_name}] Insurance verified"))
            
            return True
        
        finally:
            self.release_room("registration")
            time.sleep(0.5)

    def _simulate_consultation_threaded_fixed(self, patient):
        """
        FIXED: Thread-safe consultation simulation with atomic doctor assignment.
        This version eliminates the race condition by using atomic doctor reservation.
        """
        thread_name = threading.current_thread().name
        print(self._format_console_message("STAGE", f"[{thread_name}] Stage 3: Consultation"))
        
        # Waiting room
        if self.allocate_room("waiting"):
            patient.update_status("Waiting")
            wait_time = random.randint(1, 3) * patient.priority / 3
            print(self._format_console_message("WAIT", 
                f"[{thread_name}] Waiting for doctor ({wait_time:.1f} min estimate)"))
            time.sleep(min(wait_time, 1))  # Reduced sleep time for simulation
            self.release_room("waiting")
        
        # This combines finding and reserving into a single operation
        doctor = self.find_and_reserve_doctor_atomic(patient, specialty=patient.assigned_department, department=patient.assigned_department)
        if not doctor:
            logger.error(self._format_log_entry("CONSULTATION_ERROR", 
                f"[Thread: {thread_name}] No doctors available for {patient.name}"))
            print(self._format_console_message("ERROR", 
                f"[{thread_name}] No doctors available for {patient.name}"))
            return None
        
        # Allocate consultation room
        if not self.allocate_room("consultation"):
            # Release the doctor since we couldn't get a room
            doctor.end_consultation()
            logger.error(self._format_log_entry("CONSULTATION_ERROR", 
                f"[Thread: {thread_name}] No consultation rooms available"))
            return None
        
        try:
            # Doctor is already reserved via atomic assignment
            # No need to call start_consultation() again
            
            with self.statistics_lock:
                self.daily_statistics["consultations_completed"] += 1
            
            print(self._format_console_message("CONSULT", 
                f"[{thread_name}] Consultation with Dr. {doctor.name} ({doctor.specialty})"))
            
            # Simulate consultation
            time.sleep(1)  # Reduced for simulation speed
            
            # LLM consultation
            consultation_prompt = CONSULTATION_DOCTOR_PROMPT.format(
                doctor_name=doctor.name, doctor_specialty=doctor.specialty,
                doctor_years_experience=doctor.years_experience, patient_name=patient.name,
                patient_age=patient.age, patient_gender=patient.gender,
                patient_symptoms=patient.symptoms, patient_medical_history=patient.medical_history,
                consultation_history=patient.consultation_history, medical_record=patient.medical_record,
                medical_tests=self.medical_tests
            )
            
            llm_response = self.llm.get_completion(prompt=consultation_prompt)
            needs_tests = []
            
            try:
                response = llm_response.split("```json")[1].split("```")[0].strip()
                consultation_result = json.loads(response)
                
                if consultation_result.get("tests_needed"):
                    for test in consultation_result["tests_needed"]:
                        if test in self.medical_tests["Lab_Test"] or test in self.medical_tests["Examination"]:
                            test_type = "Lab Test" if test in self.medical_tests["Lab_Test"] else "Examination"
                            needs_tests.append((test_type, test))
                            patient.medical_record["tests"].append(f"{test} recommended by Dr. {doctor.name}")
                            print(self._format_console_message("RECOMMEND", f"[{thread_name}] {test} recommended"))
                else:
                    diagnosis = consultation_result.get("diagnosis")
                    patient.add_diagnosis(diagnosis, doctor.name)
                    prescription = consultation_result.get("prescription")
                    patient.medical_record["prescriptions"].append(prescription)
                    
                    print(self._format_console_message("DIAGNOSIS", f"[{thread_name}] Diagnosed: {diagnosis}"))
                    print(self._format_console_message("PRESCRIPTION", f"[{thread_name}] Prescribed: {prescription}"))
            
            except json.JSONDecodeError as e:
                logger.error(self._format_log_entry("CONSULTATION_JSON_ERROR", 
                    f"[Thread: {thread_name}] JSON decode error: {e}"))
            
            # End consultation (releases the doctor)
            doctor.end_consultation()
            return needs_tests
        
        finally:
            self.release_room("consultation")

    def _simulate_tests_threaded(self, patient, needs_tests) -> float:
        """Thread-safe test simulation."""
        thread_name = threading.current_thread().name
        print(self._format_console_message("STAGE", f"[{thread_name}] Stage 4: Medical Tests"))
        
        total_cost = 0
        
        for test_category, test_name in needs_tests:
            try:
                if test_category == "Examination":
                    cost = self._simulate_examination_threaded(patient, test_name)
                elif test_category == "Lab Test":
                    cost = self._simulate_lab_test_threaded(patient, test_name)
                else:
                    cost = 0
                
                total_cost += cost
                
                with self.statistics_lock:
                    self.daily_statistics["tests_performed"] += 1
                    
            except Exception as e:
                logger.error(self._format_log_entry("TEST_ERROR", 
                    f"[Thread: {thread_name}] Error in {test_name}: {str(e)}"))
        
        return total_cost

    def _simulate_examination_threaded(self, patient, test_name) -> float:
        """Thread-safe examination simulation."""
        thread_name = threading.current_thread().name
        print(self._format_console_message("TEST", f"[{thread_name}] Performing {test_name}"))
        
        if not self.allocate_room("examination"):
            logger.warning(self._format_log_entry("EXAMINATION_FAILED", 
                f"[Thread: {thread_name}] Could not allocate examination room for {test_name}"))
            return 0
        
        try:
            # Try to allocate device
            device_allocated = self.allocate_device(test_name + " Machine")
            
            patient.update_status("Undergoing Examination")
            time.sleep(1)  # Reduced for simulation
            
            # LLM examination
            examination_prompt = TEST_EXAMINATION_PROMPT.format(
                test_name=test_name, patient_name=patient.name, patient_age=patient.age,
                patient_gender=patient.gender, patient_symptoms=patient.symptoms,
                patient_medical_history=patient.medical_history
            )
            
            llm_response = self.llm.get_completion(prompt=examination_prompt)
            
            try:
                response = llm_response.split("```json")[1].split("```")[0].strip()
                examination_result = json.loads(response)
                
                findings = examination_result['findings']
                bill_amount = int(examination_result['bill'])
                
                report = f"{test_name} Report: {findings}"
                patient.medical_record["tests"].append(report)
                patient.add_note(f"{test_name} completed - {findings}", "Radiology Tech", "examination")
                
                print(self._format_console_message("RESULT", f"[{thread_name}] {test_name} complete"))
                
                # Process billing
                bill_id = self.bill_patient(patient, bill_amount, f"{test_name} Examination")
                self.process_payment(bill_id, bill_amount)
                
                return bill_amount
                
            except json.JSONDecodeError as e:
                logger.error(self._format_log_entry("EXAMINATION_JSON_ERROR", 
                    f"[Thread: {thread_name}] JSON decode error: {e}"))
                return 0
        
        finally:
            if device_allocated:
                self.release_device(test_name + " Machine")
            self.release_room("examination")

    def _simulate_lab_test_threaded(self, patient, test_name) -> float:
        """Thread-safe lab test simulation."""
        thread_name = threading.current_thread().name
        print(self._format_console_message("TEST", f"[{thread_name}] Processing {test_name}"))
        
        if not self.allocate_room("lab"):
            logger.warning(self._format_log_entry("LAB_FAILED", 
                f"[Thread: {thread_name}] Could not allocate lab room for {test_name}"))
            return 0
        
        try:
            patient.update_status("Undergoing Lab Test")
            time.sleep(1)
            
            # LLM lab test
            lab_prompt = TEST_LAB_PROMPT.format(
                test_name=test_name, patient_name=patient.name, patient_age=patient.age,
                patient_gender=patient.gender, patient_symptoms=patient.symptoms,
                patient_medical_history=patient.medical_history
            )
            
            llm_response = self.llm.get_completion(prompt=lab_prompt)
            
            try:
                response = llm_response.split("```json")[1].split("```")[0].strip()
                lab_result = json.loads(response)
                
                results = lab_result['results']
                bill_amount = int(lab_result['bill'])
                
                report = f"{test_name} Results: {results}"
                patient.medical_record["tests"].append(report)
                patient.add_note(f"{test_name} completed - {results}", "Lab Technician", "laboratory")
                
                print(self._format_console_message("RESULT", f"[{thread_name}] {test_name} complete"))
                
                # Process billing
                bill_id = self.bill_patient(patient, bill_amount, f"{test_name} Analysis")
                self.process_payment(bill_id, bill_amount)
                
                return bill_amount
                
            except json.JSONDecodeError as e:
                logger.error(self._format_log_entry("LAB_JSON_ERROR", 
                    f"[Thread: {thread_name}] JSON decode error: {e}"))
                return 0
        
        finally:
            self.release_room("lab")

    def _simulate_follow_up_consultation_threaded_fixed(self, patient) -> bool:
        """
        FIXED: Thread-safe follow-up consultation with atomic doctor assignment.
        """
        thread_name = threading.current_thread().name
        print(self._format_console_message("STAGE", f"[{thread_name}] Stage 5: Follow-up Consultation"))
        
        # Use atomic doctor assignment
        doctor = self.find_and_reserve_doctor_atomic(patient, specialty=patient.assigned_department, department=patient.assigned_department)
        if not doctor:
            logger.warning(self._format_log_entry("FOLLOWUP_FAILED", 
                f"[Thread: {thread_name}] No doctor available for follow-up"))
            return False
        
        if not self.allocate_room("consultation"):
            # Release doctor since we couldn't get a room
            doctor.end_consultation()
            return False
        
        try:
            # Doctor is already reserved via atomic assignment
            print(self._format_console_message("REVIEW", 
                f"[{thread_name}] Dr. {doctor.name} reviewing test results"))
            
            time.sleep(1)
            
            # LLM follow-up consultation
            follow_up_prompt = FOLLOW_UP_CONSULTATION_PROMPT.format(
                doctor_name=doctor.name, doctor_specialty=doctor.specialty,
                doctor_years_experience=doctor.years_experience, patient_name=patient.name,
                patient_age=patient.age, patient_gender=patient.gender,
                patient_symptoms=patient.symptoms, patient_medical_history=patient.medical_history,
                consultation_history=patient.consultation_history, medical_record=patient.medical_record
            )
            
            llm_response = self.llm.get_completion(prompt=follow_up_prompt)
            
            try:
                response = llm_response.split("```json")[1].split("```")[0].strip()
                follow_up_result = json.loads(response)
                
                diagnosis = follow_up_result.get("diagnosis")
                patient.add_diagnosis(diagnosis, doctor.name)
                prescription = follow_up_result.get("prescription")
                patient.medical_record["prescriptions"].append(prescription)
                
                print(self._format_console_message("DIAGNOSIS", f"[{thread_name}] Final diagnosis: {diagnosis}"))
                print(self._format_console_message("TREATMENT", f"[{thread_name}] Treatment prescribed"))
                
            except json.JSONDecodeError as e:
                logger.error(self._format_log_entry("FOLLOWUP_JSON_ERROR", 
                    f"[Thread: {thread_name}] JSON decode error: {e}"))
            
            # End consultation (releases the doctor)
            doctor.end_consultation()
            return True
        
        finally:
            self.release_room("consultation")

    def _simulate_pharmacy_threaded(self, patient) -> float:
        """Thread-safe pharmacy simulation."""
        thread_name = threading.current_thread().name
        print(self._format_console_message("STAGE", f"[{thread_name}] Stage 6: Pharmacy"))
        
        if not self.allocate_room("pharmacy"):
            logger.warning(self._format_log_entry("PHARMACY_FAILED", 
                f"[Thread: {thread_name}] Could not allocate pharmacy"))
            return 0
        
        try:
            patient.update_status("Collecting Medicine from Pharmacy")
            
            total_cost = 0
            for prescription in patient.medical_record["prescriptions"]:
                medication_cost = random.randint(25, 120)
                total_cost += medication_cost
                print(self._format_console_message("DISPENSE", 
                    f"[{thread_name}] Dispensing: {prescription} - ${medication_cost}"))
            
            patient.add_note("All prescribed medications dispensed", "Pharmacist", "pharmacy")
            
            with self.statistics_lock:
                self.daily_statistics["prescriptions_dispensed"] += 1
            
            # Process billing
            bill_id = self.bill_patient(patient, total_cost, "Pharmacy - Prescribed Medications")
            self.process_payment(bill_id, total_cost)
            
            print(self._format_console_message("PHARMACY", 
                f"[{thread_name}] Medications dispensed - Total: ${total_cost}"))
            
            return total_cost
        
        finally:
            self.release_room("pharmacy")

    def process_patients_concurrently(self, patients: List, max_workers: int = None) -> List[Dict[str, Any]]:
        """
        Process multiple patients concurrently using ThreadPoolExecutor.
        
        Args:
            patients (List): List of patients to process.
            max_workers (int): Maximum number of concurrent threads.
            
        Returns:
            List[Dict[str, Any]]: List of visit summaries.
        """
        if max_workers is None:
            max_workers = self.max_concurrent_patients
        
        logger.info(self._format_log_entry("CONCURRENT_START", 
            f"Starting concurrent processing of {len(patients)} patients with {max_workers} workers"))
        
        visit_summaries = []
        
        # Sort patients by priority (emergency patients first)
        patients.sort(key=lambda p: p.priority)
        
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="Patient") as executor:
            # Submit all patient visits
            future_to_patient = {
                executor.submit(self.simulate_patient_visit_threaded, patient): patient 
                for patient in patients
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_patient):
                patient = future_to_patient[future]
                try:
                    visit_summary = future.result()
                    visit_summaries.append(visit_summary)
                    
                    if visit_summary["success"]:
                        logger.info(self._format_log_entry("PATIENT_COMPLETE", 
                            f"Patient {patient.name} processed successfully in {visit_summary['duration_minutes']:.1f} min"))
                    else:
                        logger.warning(self._format_log_entry("PATIENT_FAILED", 
                            f"Patient {patient.name} processing failed: {visit_summary['errors']}"))
                        
                except Exception as e:
                    error_summary = {
                        "patient_id": patient.id, "patient_name": patient.name,
                        "success": False, "errors": [str(e)], "thread_id": "Unknown"
                    }
                    visit_summaries.append(error_summary)
                    logger.error(self._format_log_entry("PATIENT_EXCEPTION", 
                        f"Exception processing patient {patient.name}: {str(e)}"))
        
        logger.info(self._format_log_entry("CONCURRENT_COMPLETE", 
            f"Concurrent processing completed - {len(visit_summaries)} patients processed"))
        
        return visit_summaries

    def generate_hospital_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive hospital statistics (thread-safe version)."""
        with self.statistics_lock:
            if not hasattr(self, 'operation_start_time'):
                self.operation_start_time = datetime.now()
            
            now = datetime.now()
            operation_duration = (now - self.operation_start_time).total_seconds() / 3600
            
            # Thread-safe room utilization statistics
            room_stats = {}
            with self.rooms_lock:
                for room_type, info in self.rooms.items():
                    utilization = (info["occupied"] / info["total"]) * 100 if info["total"] > 0 else 0
                    room_stats[room_type] = {
                        "total": info["total"],
                        "available": info["available"],
                        "occupied": info["occupied"],
                        "utilization_rate": f"{utilization:.1f}%"
                    }
            
            # Thread-safe doctor utilization statistics
            doctor_stats = []
            with self.doctors_lock:
                for doctor in self.doctors:
                    daily_summary = doctor.get_daily_summary()
                    doctor_stats.append({
                        "name": doctor.name,
                        "specialty": doctor.specialty,
                        "patients_seen": doctor.patients_seen_today,
                        "max_capacity": doctor.max_patients_per_day,
                        "utilization": f"{daily_summary['daily_metrics']['utilization_rate']}%",
                        "avg_consultation_time": f"{daily_summary['daily_metrics']['average_consultation_time_minutes']:.1f}min",
                        "status": doctor.status
                    })
            
            # Thread-safe financial statistics
            with self.billing_lock:
                total_bills = len(self.billing_records)
                paid_bills = len([b for b in self.billing_records if b["status"] == "Paid"])
                payment_rate = (paid_bills / total_bills * 100) if total_bills > 0 else 0
            
            statistics = {
                "hospital_info": {
                    "name": self.name,
                    "operation_hours": round(operation_duration, 2),
                    "departments": len(self.departments),
                    "total_doctors": len(self.doctors)
                },
                "patient_statistics": {
                    "total_processed": len(self.patients),
                    "currently_active": len(self.active_patients),
                    "consultations_completed": self.daily_statistics["consultations_completed"],
                    "tests_performed": self.daily_statistics["tests_performed"],
                    "prescriptions_dispensed": self.daily_statistics["prescriptions_dispensed"]
                },
                "financial_summary": {
                    "total_revenue": f"${self.revenue:.2f}",
                    "total_expenses": f"${self.expenses:.2f}",
                    "profit": f"${self.revenue - self.expenses:.2f}",
                    "bills_issued": total_bills,
                    "payment_rate": f"{payment_rate:.1f}%"
                },
                "resource_utilization": {
                    "rooms": room_stats,
                    "doctors": doctor_stats
                },
                "operational_metrics": {
                    "avg_patient_processing_time": "45.3 minutes",
                    "patient_satisfaction_score": "4.2/5.0",
                    "bed_occupancy_rate": "78.5%",
                    "equipment_utilization": "65.2%"
                }
            }
            
            return statistics

    def generate_concurrent_statistics(self, visit_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics from concurrent patient processing."""
        successful_visits = [v for v in visit_summaries if v.get("success", False)]
        failed_visits = [v for v in visit_summaries if not v.get("success", False)]
        
        # Calculate timing statistics
        durations = [v.get("duration_minutes", 0) for v in successful_visits if v.get("duration_minutes")]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Calculate cost statistics
        total_costs = [v.get("total_cost", 0) for v in successful_visits]
        total_revenue = sum(total_costs)
        avg_cost_per_patient = total_revenue / len(successful_visits) if successful_visits else 0
        
        # Stage completion analysis
        stage_completion = {}
        for visit in visit_summaries:
            for stage in visit.get("stages_completed", []):
                stage_completion[stage] = stage_completion.get(stage, 0) + 1
        
        return {
            "concurrent_metrics": {
                "total_patients": len(visit_summaries),
                "successful_visits": len(successful_visits),
                "failed_visits": len(failed_visits),
                "success_rate": f"{(len(successful_visits) / len(visit_summaries) * 100):.1f}%" if visit_summaries else "0%",
                "average_visit_duration_minutes": round(avg_duration, 2),
                "total_revenue": f"${total_revenue:.2f}",
                "average_cost_per_patient": f"${avg_cost_per_patient:.2f}"
            },
            "stage_completion_rates": {
                stage: f"{(count / len(visit_summaries) * 100):.1f}%" 
                for stage, count in stage_completion.items()
            },
            "threading_performance": {
                "max_concurrent_patients": self.max_concurrent_patients,
                "threads_used": len(set(v.get("thread_id", "Unknown") for v in visit_summaries)),
                "resource_contention_events": len([log for log in self.resource_logs if "timeout" in log.get("action", "").lower()])
            }
        }

    def _format_log_entry(self, event_type: str, message: str) -> str:
        """Format log entry with hospital ID."""
        return f"[HOSPITAL-{self.id[:8]}] [{event_type}] {message}"

    def _format_console_header(self) -> str:
        """Format console header for major sections."""
        return "\n" + "="*80 + "\n"

    def _format_console_separator(self) -> str:
        """Format console separator for sections."""
        return "\n" + "-"*50

    def _format_console_message(self, event_type: str, message: str) -> str:
        """Format console message with timestamp and type."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] [{event_type:>12}] {message}"

    def __str__(self) -> str:
        """String representation of the Hospital."""
        return (f"ThreadSafeHospital('{self.name}' - {len(self.doctors)} doctors, "
                f"{len(self.active_patients)} active patients)")

    def __repr__(self) -> str:
        """Detailed representation of the Hospital."""
        return (f"ThreadSafeHospital(id='{self.id}', name='{self.name}', "
                f"doctors={len(self.doctors)}, departments={len(self.departments)})")

# For backward compatibility, alias the new class
Hospital = ThreadSafeHospital