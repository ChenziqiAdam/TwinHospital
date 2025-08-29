from datetime import datetime
from typing import Dict, Any, List, Optional
import logging
from ..config import get_config

# Configure logger for Patient class
logger = logging.getLogger(__name__)

class Patient:
    def __init__(self, patient_id: int, name: str, age: int = None, gender: str = None, 
                 contact: str = None, insurance: bool = True, symptoms: List = None, medical_history: List = None):
        """
        Initializes a Patient instance using configuration settings.
        
        Args:
            patient_id (int): The unique identifier for the patient.
            name (str): The name of the patient.
            age (int, optional): The age of the patient.
            gender (str, optional): The gender of the patient.
            contact (str, optional): Contact information.
            insurance (bool, optional): Insurance status.
        """
        config = get_config()
        
        # Basic patient information
        self.id = patient_id
        self.name = name
        self.age = age
        self.gender = gender
        self.contact = contact
        self.insurance = insurance
        
        # Status management using configuration
        available_statuses = config.get_patient_statuses()
        self.status = available_statuses[0] if available_statuses else "New"  # Default to first status
        
        # Timing information
        self.arrival_time = datetime.now()
        self.discharge_time = None
        
        # Priority system using configuration
        priority_levels = config.get_priority_levels()
        self.priority = 2  # Default to standard priority
        self.priority_description = priority_levels.get(self.priority, "Standard")
        
        # Medical record structure based on configuration
        self.medical_record = self._initialize_medical_record()
        
        # Tracking information
        self.waiting_history = []
        self.has_medical_card = False

        # Symptoms and Medical History
        self.symptoms = symptoms
        self.medical_history = medical_history

        # Consultation history
        self.consultation_history = []
        
        # Log patient arrival with improved formatting
        logger.info(self._format_log_entry("ARRIVAL", f"Patient arrived at hospital"))
        print(self._format_console_message("ARRIVAL", f"Patient {self.name} (ID: {self.id}) has arrived"))

    def _initialize_medical_record(self) -> Dict[str, Any]:
        """Initialize medical record structure based on configuration."""
        config = get_config()
        record_fields = config.patient_data.medical_record
        
        # Create medical record with configured fields
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
        """
        Updates the patient's current status using configured status options.
        
        Args:
            status (str): The new status for the patient.
        """
        config = get_config()
        available_statuses = config.get_patient_statuses()
        
        if status not in available_statuses:
            logger.warning(self._format_log_entry("STATUS_WARNING", 
                f"Status '{status}' not in configured statuses: {available_statuses}"))
        
        previous_status = self.status
        self.status = status
        
        # Record status change in history
        self.waiting_history.append({
            "from_status": previous_status,
            "to_status": status,
            "timestamp": datetime.now()
        })
        
        # Log status change
        logger.info(self._format_log_entry("STATUS_CHANGE", 
            f"Status changed from '{previous_status}' to '{status}'"))
        print(self._format_console_message("STATUS", f"{self.name}'s status: {status}"))

    def set_priority(self, priority_level: int) -> None:
        """
        Sets the patient's priority level using configuration.
        
        Args:
            priority_level (int): The priority level (1-5).
        """
        config = get_config()
        priority_levels = config.get_priority_levels()
        
        if priority_level in priority_levels:
            self.priority = priority_level
            self.priority_description = priority_levels[priority_level]
            logger.info(self._format_log_entry("PRIORITY", 
                f"Priority set to {priority_level} ({self.priority_description})"))
        else:
            logger.warning(self._format_log_entry("PRIORITY_WARNING", 
                f"Invalid priority level {priority_level}. Available: {list(priority_levels.keys())}"))

    def record_vitals(self, temperature: float, blood_pressure: str, 
                     heart_rate: int, respiratory_rate: int) -> None:
        """
        Records patient vitals with improved logging.
        
        Args:
            temperature (float): Body temperature in Celsius.
            blood_pressure (str): Blood pressure reading.
            heart_rate (int): Heart rate in BPM.
            respiratory_rate (int): Respiratory rate per minute.
        """
        vitals_record = {
            "temperature": temperature,
            "blood_pressure": blood_pressure,
            "heart_rate": heart_rate,
            "respiratory_rate": respiratory_rate,
            "timestamp": datetime.now(),
            "recorded_by": "Triage Nurse"
        }
        
        self.medical_record["vitals"].append(vitals_record)
        
        # Log vitals recording
        vitals_summary = f"T: {temperature}°C, BP: {blood_pressure}, HR: {heart_rate}, RR: {respiratory_rate}"
        logger.info(self._format_log_entry("VITALS", f"Vitals recorded - {vitals_summary}"))
        print(self._format_console_message("VITALS", f"Vitals recorded for {self.name}"))

    def add_diagnosis(self, diagnosis: str, doctor_name: str) -> None:
        """
        Adds a diagnosis to the patient's medical record.
        
        Args:
            diagnosis (str): The diagnosis.
            doctor_name (str): The name of the diagnosing doctor.
        """
        diagnosis_record = {
            "diagnosis": diagnosis,
            "doctor": doctor_name,
            "timestamp": datetime.now(),
            "status": "Active"
        }
        
        self.medical_record["diagnoses"].append(diagnosis_record)
        
        logger.info(self._format_log_entry("DIAGNOSIS", 
            f"Diagnosis '{diagnosis}' added by Dr. {doctor_name}"))
        print(self._format_console_message("DIAGNOSIS", 
            f"{self.name} diagnosed with {diagnosis}"))

    def add_note(self, note: str, staff_name: str, note_type: str = "general") -> None:
        """
        Adds a note to the patient's medical record with improved categorization.
        
        Args:
            note (str): The note content.
            staff_name (str): The name of the staff member adding the note.
            note_type (str): The type/category of the note.
        """
        note_record = {
            "content": note,
            "staff": staff_name,
            "type": note_type,
            "timestamp": datetime.now()
        }
        
        self.medical_record["notes"].append(note_record)
        
        logger.info(self._format_log_entry("NOTE", 
            f"Note added by {staff_name} ({note_type}): {note[:50]}..."))

    def discharge(self) -> None:
        """Discharges the patient from the hospital with comprehensive logging."""
        config = get_config()
        available_statuses = config.get_patient_statuses()
        discharge_status = "Discharged" if "Discharged" in available_statuses else available_statuses[-1]
        
        self.update_status(discharge_status)
        self.discharge_time = datetime.now()
        
        # Calculate total time in hospital
        total_duration = self.discharge_time - self.arrival_time
        hours, remainder = divmod(total_duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Add discharge note
        self.add_note(f"Patient discharged after {hours}h {minutes}m in hospital", 
                     "Discharge Coordinator", "discharge")
        
        # Comprehensive logging
        logger.info(self._format_log_entry("DISCHARGE", 
            f"Patient discharged - Total time: {hours}h {minutes}m {seconds}s"))
        print(self._format_console_message("DISCHARGE", 
            f"{self.name} discharged after {hours}h {minutes}m"))

    def calculate_waiting_time(self) -> int:
        """
        Calculates the total waiting time for the patient.
        
        Returns:
            int: Total waiting time in seconds.
        """
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
        """
        Returns a comprehensive medical summary for the patient.
        
        Returns:
            Dict[str, Any]: Medical summary with key information.
        """
        summary = {
            "patient_info": {
                "id": self.id,
                "name": self.name,
                "age": self.age,
                "gender": self.gender,
                "insurance": self.insurance,
                "symptoms": self.symptoms,
                "medical_history": self.medical_history
            },
            "visit_info": {
                "arrival_time": self.arrival_time,
                "discharge_time": self.discharge_time,
                "current_status": self.status,
                "priority": f"{self.priority} ({self.priority_description})"
            },
            "medical_record": self.medical_record,
            "waiting_time_seconds": self.calculate_waiting_time()
        }
        
        return summary

    def _format_log_entry(self, event_type: str, message: str) -> str:
        """Format log entry with consistent structure."""
        return f"[PATIENT-{self.id:04d}] [{event_type}] {message}"

    def _format_console_message(self, event_type: str, message: str) -> str:
        """Format console message with improved readability."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] [{event_type}] {message}"

    def __str__(self) -> str:
        """String representation of the Patient object."""
        return (f"Patient(ID: {self.id}, Name: {self.name}, Status: {self.status}, "
                f"Priority: {self.priority}({self.priority_description}))")

    def __repr__(self) -> str:
        """Detailed representation of the Patient object."""
        return (f"Patient(id={self.id}, name='{self.name}', age={self.age}, "
                f"gender='{self.gender}', status='{self.status}', priority={self.priority})")