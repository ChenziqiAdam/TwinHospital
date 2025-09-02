from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
import threading
from ..config import get_config

# Configure logger for Patient class
logger = logging.getLogger(__name__)

class ThreadSafePatient:
    def __init__(self, patient_id: int, name: str, age: int = None, gender: str = None, 
                 contact: str = None, insurance: bool = True, symptoms: List = None, 
                 medical_history: List = None, assigned_department: str = None, consultation_history: List[Any] = None):
        """
        Initializes a thread-safe Patient instance.
        
        Args:
            patient_id (int): The unique identifier for the patient.
            name (str): The name of the patient.
            age (int, optional): The age of the patient.
            gender (str, optional): The gender of the patient.
            contact (str, optional): Contact information.
            insurance (bool, optional): Insurance status.
            symptoms (List, optional): List of patient symptoms.
            medical_history (List, optional): List of medical history items.
            consultation_history (List, optional): Previous consultation history.
        """
        config = get_config()
        
        # Thread-safe locks for patient operations
        self.status_lock = threading.RLock()        # For status updates
        self.medical_record_lock = threading.RLock() # For medical record updates
        self.vitals_lock = threading.RLock()        # For vital signs
        
        # Basic patient information
        self.id = patient_id
        self.name = name
        self.age = age
        self.gender = gender
        self.contact = contact
        self.insurance = insurance
        
        # Status management using configuration
        available_statuses = config.get_patient_statuses()
        self.status = available_statuses[0] if available_statuses else "New"
        
        # Timing information
        self.arrival_time = datetime.now()
        self.discharge_time = None
        
        # Priority system using configuration
        priority_levels = config.get_priority_levels()
        self.priority = 2  # Default to standard priority
        self.priority_description = priority_levels.get(self.priority, "Standard")
        
        # Medical record structure (thread-safe access needed)
        self.medical_record = self._initialize_medical_record()
        
        # Tracking information
        self.waiting_history = []
        self.has_medical_card = False
        
        # Symptoms and Medical History
        self.symptoms = symptoms or []
        self.medical_history = medical_history or []

        # Department assignment
        self.assigned_department = assigned_department or "General"
        
        # Consultation history
        self.consultation_history = consultation_history or []
        
        # Threading tracking
        self.processing_thread = None
        self.concurrent_operations = []
        
        # Log patient arrival
        logger.info(self._format_log_entry("ARRIVAL", 
            f"Thread-safe patient arrived at hospital"))
        print(self._format_console_message("ARRIVAL", 
            f"Patient {self.name} (ID: {self.id}) has arrived [Thread-Safe]"))

    def _initialize_medical_record(self) -> Dict[str, Any]:
        """Initialize thread-safe medical record structure."""
        config = get_config()
        record_fields = config.patient_data.medical_record
        
        medical_record = {}
        for field in record_fields:
            if field in ["diagnoses", "prescriptions", "lab tests"]:
                medical_record[field] = []
            elif field == "vitals":
                medical_record[field] = []
            elif field == "consultations":
                medical_record[field] = []
            elif field == "notes":
                medical_record[field] = []
            else:
                medical_record[field] = []
        
        # Ensure essential fields exist
        essential_fields = ["diagnoses", "prescriptions", "tests", "vitals", "consultations", "notes"]
        for field in essential_fields:
            if field not in medical_record:
                medical_record[field] = []
        
        return medical_record

    def update_status(self, status: str) -> None:
        """Thread-safe status update."""
        with self.status_lock:
            config = get_config()
            available_statuses = config.get_patient_statuses()
            
            if status not in available_statuses:
                logger.warning(self._format_log_entry("STATUS_WARNING", 
                    f"Status '{status}' not in configured statuses: {available_statuses}"))
            
            previous_status = self.status
            self.status = status
            
            # Record status change in history with thread information
            thread_name = threading.current_thread().name
            status_change = {
                "from_status": previous_status,
                "to_status": status,
                "timestamp": datetime.now(),
                "thread_id": thread_name
            }
            
            self.waiting_history.append(status_change)
            
            # Track concurrent operations
            operation_record = {
                "operation": "status_update",
                "thread_id": thread_name,
                "timestamp": datetime.now(),
                "details": f"{previous_status} -> {status}"
            }
            self.concurrent_operations.append(operation_record)
            
            logger.info(self._format_log_entry("STATUS_CHANGE", 
                f"[Thread: {thread_name}] Status changed from '{previous_status}' to '{status}'"))
            print(self._format_console_message("STATUS", 
                f"[{thread_name}] {self.name}'s status: {status}"))

    def set_priority(self, priority_level: int) -> None:
        """Thread-safe priority setting."""
        with self.status_lock:
            config = get_config()
            priority_levels = config.get_priority_levels()
            
            if priority_level in priority_levels:
                old_priority = self.priority
                self.priority = priority_level
                self.priority_description = priority_levels[priority_level]
                
                thread_name = threading.current_thread().name
                logger.info(self._format_log_entry("PRIORITY", 
                    f"[Thread: {thread_name}] Priority changed from {old_priority} to {priority_level} ({self.priority_description})"))
            else:
                logger.warning(self._format_log_entry("PRIORITY_WARNING", 
                    f"Invalid priority level {priority_level}. Available: {list(priority_levels.keys())}"))

    def record_vitals(self, temperature: float, blood_pressure: str, 
                     heart_rate: int, respiratory_rate: int) -> None:
        """Thread-safe vital signs recording."""
        with self.vitals_lock:
            thread_name = threading.current_thread().name
            
            vitals_record = {
                "temperature": temperature,
                "blood_pressure": blood_pressure,
                "heart_rate": heart_rate,
                "respiratory_rate": respiratory_rate,
                "timestamp": datetime.now(),
                "recorded_by": "Triage Nurse",
                "thread_id": thread_name
            }
            
            with self.medical_record_lock:
                self.medical_record["vitals"].append(vitals_record)
            
            # Track operation
            operation_record = {
                "operation": "vitals_recording",
                "thread_id": thread_name,
                "timestamp": datetime.now(),
                "details": f"T: {temperature}°C, BP: {blood_pressure}, HR: {heart_rate}"
            }
            self.concurrent_operations.append(operation_record)
            
            vitals_summary = f"T: {temperature}°C, BP: {blood_pressure}, HR: {heart_rate}, RR: {respiratory_rate}"
            logger.info(self._format_log_entry("VITALS", 
                f"[Thread: {thread_name}] Vitals recorded - {vitals_summary}"))
            print(self._format_console_message("VITALS", 
                f"[{thread_name}] Vitals recorded for {self.name}"))

    def add_diagnosis(self, diagnosis: str, doctor_name: str) -> None:
        """Thread-safe diagnosis addition."""
        with self.medical_record_lock:
            thread_name = threading.current_thread().name
            
            diagnosis_record = {
                "diagnosis": diagnosis,
                "doctor": doctor_name,
                "timestamp": datetime.now(),
                "status": "Active",
                "thread_id": thread_name
            }
            
            self.medical_record["diagnoses"].append(diagnosis_record)
            
            # Track operation
            operation_record = {
                "operation": "diagnosis_added",
                "thread_id": thread_name,
                "timestamp": datetime.now(),
                "details": f"Diagnosis: {diagnosis} by Dr. {doctor_name}"
            }
            self.concurrent_operations.append(operation_record)
            
            logger.info(self._format_log_entry("DIAGNOSIS", 
                f"[Thread: {thread_name}] Diagnosis '{diagnosis}' added by Dr. {doctor_name}"))
            print(self._format_console_message("DIAGNOSIS", 
                f"[{thread_name}] {self.name} diagnosed with {diagnosis}"))

    def add_note(self, note: str, staff_name: str, note_type: str = "general") -> None:
        """Thread-safe note addition."""
        with self.medical_record_lock:
            thread_name = threading.current_thread().name
            
            note_record = {
                "content": note,
                "staff": staff_name,
                "type": note_type,
                "timestamp": datetime.now(),
                "thread_id": thread_name
            }
            
            self.medical_record["notes"].append(note_record)
            
            # Track operation
            operation_record = {
                "operation": "note_added",
                "thread_id": thread_name,
                "timestamp": datetime.now(),
                "details": f"Note by {staff_name}: {note[:30]}..."
            }
            self.concurrent_operations.append(operation_record)
            
            logger.info(self._format_log_entry("NOTE", 
                f"[Thread: {thread_name}] Note added by {staff_name} ({note_type}): {note[:50]}..."))

    def discharge(self) -> None:
        """Thread-safe patient discharge."""
        with self.status_lock, self.medical_record_lock:
            config = get_config()
            available_statuses = config.get_patient_statuses()
            discharge_status = "Discharged" if "Discharged" in available_statuses else available_statuses[-1]
            
            self.update_status(discharge_status)
            self.discharge_time = datetime.now()
            
            # Calculate total time in hospital
            total_duration = self.discharge_time - self.arrival_time
            hours, remainder = divmod(total_duration.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            thread_name = threading.current_thread().name
            
            # Add discharge note
            self.add_note(f"Patient discharged after {hours}h {minutes}m in hospital", 
                         "Discharge Coordinator", "discharge")
            
            # Track final operation
            operation_record = {
                "operation": "discharge",
                "thread_id": thread_name,
                "timestamp": self.discharge_time,
                "details": f"Total stay: {hours}h {minutes}m"
            }
            self.concurrent_operations.append(operation_record)
            
            logger.info(self._format_log_entry("DISCHARGE", 
                f"[Thread: {thread_name}] Patient discharged - Total time: {hours}h {minutes}m {seconds}s"))
            print(self._format_console_message("DISCHARGE", 
                f"[{thread_name}] {self.name} discharged after {hours}h {minutes}m"))

    def calculate_waiting_time(self) -> int:
        """Thread-safe waiting time calculation."""
        with self.status_lock:
            waiting_time = 0
            current_waiting_start = None
            
            for record in self.waiting_history:
                if record["to_status"] == "Waiting" and current_waiting_start is None:
                    current_waiting_start = record["timestamp"]
                elif record["from_status"] == "Waiting" and current_waiting_start is not None:
                    waiting_duration = (record["timestamp"] - current_waiting_start).seconds
                    waiting_time += waiting_duration
                    current_waiting_start = None
            
            return waiting_time

    def get_medical_summary(self) -> Dict[str, Any]:
        """Thread-safe comprehensive medical summary."""
        with self.medical_record_lock, self.status_lock:
            # Calculate threading metrics
            thread_operations = {}
            for operation in self.concurrent_operations:
                thread_id = operation.get("thread_id", "Unknown")
                thread_operations[thread_id] = thread_operations.get(thread_id, 0) + 1
            
            summary = {
                "patient_info": {
                    "id": self.id,
                    "name": self.name,
                    "age": self.age,
                    "gender": self.gender,
                    "insurance": self.insurance,
                    "symptoms": self.symptoms,
                    "medical_history": self.medical_history,
                    "consultation_history": self.consultation_history,
                    "assigned_department": self.assigned_department
                },
                "visit_info": {
                    "arrival_time": self.arrival_time,
                    "discharge_time": self.discharge_time,
                    "current_status": self.status,
                    "priority": f"{self.priority} ({self.priority_description})"
                },
                "medical_record": self._get_medical_record_copy(),
                "waiting_time_seconds": self.calculate_waiting_time(),
                "threading_info": {
                    "thread_safe": True,
                    "operations_by_thread": thread_operations,
                    "total_concurrent_operations": len(self.concurrent_operations),
                    "processing_thread": self.processing_thread
                }
            }
            
            return summary

    def _get_medical_record_copy(self) -> Dict[str, Any]:
        """Get a thread-safe copy of the medical record."""
        # Already called within medical_record_lock context
        return {
            "diagnoses": self.medical_record["diagnoses"].copy(),
            "prescriptions": self.medical_record["prescriptions"].copy(),
            "tests": self.medical_record["tests"].copy(),
            "vitals": self.medical_record["vitals"].copy(),
            "consultations": self.medical_record["consultations"].copy(),
            "notes": self.medical_record["notes"].copy()
        }

    def get_current_status_info(self) -> Dict[str, Any]:
        """
        Get current status information for thread coordination.
        
        Returns:
            Dict[str, Any]: Current status and threading information.
        """
        with self.status_lock:
            return {
                "patient_id": self.id,
                "patient_name": self.name,
                "current_status": self.status,
                "priority": self.priority,
                "priority_description": self.priority_description,
                "processing_thread": threading.current_thread().name,
                "is_discharged": self.discharge_time is not None,
                "concurrent_operations_count": len(self.concurrent_operations)
            }

    def can_accept_concurrent_operation(self, operation_type: str) -> bool:
        """
        Check if patient can accept a concurrent operation.
        
        Args:
            operation_type (str): Type of operation to check.
            
        Returns:
            bool: True if operation can proceed concurrently.
        """
        with self.status_lock:
            # Patients can handle multiple note additions and status updates
            concurrent_safe_operations = ["add_note", "status_update", "vitals_recording"]
            
            # But only one medical procedure at a time
            exclusive_operations = ["consultation", "examination", "lab_test", "discharge"]
            
            if operation_type in concurrent_safe_operations:
                return True
            
            if operation_type in exclusive_operations:
                # Check if any exclusive operation is currently in progress
                current_exclusive_ops = [
                    op for op in self.concurrent_operations[-5:]  # Check last 5 operations
                    if op.get("operation") in exclusive_operations and
                    (datetime.now() - op.get("timestamp", datetime.now())).seconds < 300  # Active in last 5 minutes
                ]
                return len(current_exclusive_ops) == 0
            
            return True

    def add_prescription_thread_safe(self, prescription: str, doctor_name: str) -> None:
        """Thread-safe prescription addition."""
        with self.medical_record_lock:
            thread_name = threading.current_thread().name
            
            prescription_record = {
                "medication": prescription,
                "prescribed_by": doctor_name,
                "timestamp": datetime.now(),
                "status": "Active",
                "thread_id": thread_name
            }
            
            # Add to prescriptions list (backward compatibility)
            self.medical_record["prescriptions"].append(prescription)
            
            # Track operation
            operation_record = {
                "operation": "prescription_added",
                "thread_id": thread_name,
                "timestamp": datetime.now(),
                "details": f"Prescription: {prescription} by Dr. {doctor_name}"
            }
            self.concurrent_operations.append(operation_record)
            
            logger.info(self._format_log_entry("PRESCRIPTION", 
                f"[Thread: {thread_name}] Prescription '{prescription}' added by Dr. {doctor_name}"))

    def add_test_result_thread_safe(self, test_name: str, results: str, staff_name: str) -> None:
        """Thread-safe test result addition."""
        with self.medical_record_lock:
            thread_name = threading.current_thread().name
            
            test_record = {
                "test_name": test_name,
                "results": results,
                "performed_by": staff_name,
                "timestamp": datetime.now(),
                "thread_id": thread_name
            }
            
            # Add to tests list (backward compatibility)
            self.medical_record["tests"].append(f"{test_name}: {results}")
            
            # Track operation
            operation_record = {
                "operation": "test_result_added",
                "thread_id": thread_name,
                "timestamp": datetime.now(),
                "details": f"Test: {test_name} by {staff_name}"
            }
            self.concurrent_operations.append(operation_record)
            
            logger.info(self._format_log_entry("TEST_RESULT", 
                f"[Thread: {thread_name}] Test result '{test_name}' added by {staff_name}"))

    def get_threading_analysis(self) -> Dict[str, Any]:
        """
        Analyze threading operations for this patient.
        
        Returns:
            Dict[str, Any]: Threading analysis data.
        """
        with self.medical_record_lock:
            # Analyze thread usage
            thread_usage = {}
            operation_types = {}
            
            for operation in self.concurrent_operations:
                thread_id = operation.get("thread_id", "Unknown")
                op_type = operation.get("operation", "Unknown")
                
                thread_usage[thread_id] = thread_usage.get(thread_id, 0) + 1
                operation_types[op_type] = operation_types.get(op_type, 0) + 1
            
            # Calculate timing metrics
            if self.concurrent_operations:
                first_op = min(self.concurrent_operations, key=lambda x: x.get("timestamp", datetime.now()))
                last_op = max(self.concurrent_operations, key=lambda x: x.get("timestamp", datetime.now()))
                
                total_processing_time = (
                    last_op.get("timestamp", datetime.now()) - 
                    first_op.get("timestamp", datetime.now())
                ).total_seconds()
            else:
                total_processing_time = 0
            
            return {
                "patient_id": self.id,
                "patient_name": self.name,
                "thread_usage": thread_usage,
                "operation_types": operation_types,
                "total_operations": len(self.concurrent_operations),
                "unique_threads": len(thread_usage),
                "processing_time_seconds": total_processing_time,
                "operations_per_second": len(self.concurrent_operations) / total_processing_time if total_processing_time > 0 else 0,
                "thread_safety_enabled": True
            }

    def _format_log_entry(self, event_type: str, message: str) -> str:
        """Format log entry with consistent structure."""
        return f"[PATIENT-{self.id:04d}] [{event_type}] {message}"

    def _format_console_message(self, event_type: str, message: str) -> str:
        """Format console message with improved readability."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] [{event_type}] {message}"

    def __str__(self) -> str:
        """String representation of the ThreadSafePatient object."""
        with self.status_lock:
            return (f"Patient(ID: {self.id}, Name: {self.name}, Status: {self.status}, "
                    f"Priority: {self.priority}({self.priority_description})) [Thread-Safe]")

    def __repr__(self) -> str:
        """Detailed representation of the ThreadSafePatient object."""
        return (f"ThreadSafePatient(id={self.id}, name='{self.name}', age={self.age}, "
                f"gender='{self.gender}', status='{self.status}', priority={self.priority})")

# For backward compatibility
Patient = ThreadSafePatient