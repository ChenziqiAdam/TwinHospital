from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from ..config import get_config

# Configure logger for Doctor class
logger = logging.getLogger(__name__)

class Doctor:
    def __init__(self, name: str, specialty: str, staff_id: str = None, 
                 years_experience: int = 0, max_patients_per_day: int = 20):
        """
        Initializes a Doctor instance using configuration settings.
        
        Args:
            name (str): The doctor's name.
            specialty (str): The doctor's medical specialty.
            staff_id (str, optional): The doctor's staff ID.
            years_experience (int, optional): Years of professional experience.
            max_patients_per_day (int, optional): Maximum patients the doctor can see per day.
        """
        config = get_config()
        
        # Basic doctor information
        self.name = name
        self.specialty = self._validate_specialty(specialty)
        self.staff_id = staff_id or f"D{id(self) % 10000:04d}"
        self.years_experience = years_experience
        self.max_patients_per_day = max_patients_per_day
        
        # Status management using configuration
        available_statuses = config.get_doctor_statuses()
        self.status = available_statuses[0] if available_statuses else "Available"
        
        # Current state
        self.current_patient = None
        self.patients_seen_today = 0
        
        # Schedule and history tracking
        self.schedule = {}
        self.consultation_history = []
        self.shift_start = None
        self.shift_end = None
        self.break_times = []
        
        # Performance metrics
        self.performance_metrics = {
            "total_consultations": 0,
            "average_consultation_time": 0,
            "patient_satisfaction_score": 0.0,
            "specialization_cases": 0
        }
        
        # Log doctor initialization
        logger.info(self._format_log_entry("INITIALIZATION", 
            f"Doctor initialized - Specialty: {self.specialty}, Experience: {years_experience} years"))
        print(self._format_console_message("INIT", 
            f"Dr. {self.name} ({self.specialty}) joined the hospital"))

    def _validate_specialty(self, specialty: str) -> str:
        """
        Validates if the specialty is in the configured list.
        
        Args:
            specialty (str): The specialty to validate.
            
        Returns:
            str: Validated specialty or 'General' as fallback.
        """
        config = get_config()
        available_specialties = config.get_specialties()
        
        # Check if specialty matches any available specialty (case-insensitive)
        for available in available_specialties:
            if specialty.lower() in available.lower() or available.lower() in specialty.lower():
                return available
        
        logger.warning(self._format_log_entry("SPECIALTY_WARNING", 
            f"Specialty '{specialty}' not found in config, defaulting to 'General'"))
        return "General"

    def update_status(self, status: str) -> None:
        """
        Updates the doctor's current status using configured status options.
        
        Args:
            status (str): The new status for the doctor.
        """
        config = get_config()
        available_statuses = config.get_doctor_statuses()
        
        if status not in available_statuses:
            logger.warning(self._format_log_entry("STATUS_WARNING", 
                f"Status '{status}' not in configured statuses: {available_statuses}"))
        
        previous_status = self.status
        self.status = status
        
        # Log status change
        logger.info(self._format_log_entry("STATUS_CHANGE", 
            f"Status changed from '{previous_status}' to '{status}'"))
        print(self._format_console_message("STATUS", 
            f"Dr. {self.name} is now {status}"))

    def start_consultation(self, patient) -> bool:
        """
        Starts a consultation with a patient with comprehensive logging.
        
        Args:
            patient: The patient object to consult with.
            
        Returns:
            bool: True if consultation started successfully, False otherwise.
        """
        if self.status != "Available":
            logger.warning(self._format_log_entry("CONSULTATION_BLOCKED", 
                f"Cannot start consultation - Doctor status: {self.status}"))
            print(self._format_console_message("ERROR", 
                f"Dr. {self.name} is {self.status}, cannot start consultation"))
            return False
        
        if not self.is_available():
            logger.warning(self._format_log_entry("CONSULTATION_BLOCKED", 
                "Doctor not available due to capacity or schedule constraints"))
            return False
        
        # Start consultation
        self.current_patient = patient
        self.update_status("In Consultation")
        consultation_start = datetime.now()
        
        # Record consultation in history
        consultation_record = {
            "consultation_id": len(self.consultation_history) + 1,
            "patient_id": patient.id,
            "patient_name": patient.name,
            "start_time": consultation_start,
            "end_time": None,
            "duration_minutes": None,
            "consultation_type": "Regular",
            "notes": []
        }
        
        self.consultation_history.append(consultation_record)
        
        logger.info(self._format_log_entry("CONSULTATION_START", 
            f"Started consultation with Patient {patient.id} ({patient.name})"))
        print(self._format_console_message("CONSULT", 
            f"Dr. {self.name} started consultation with {patient.name}"))
        
        return True

    def end_consultation(self) -> Optional[Dict[str, Any]]:
        """
        Ends the current consultation with detailed metrics logging.
        
        Returns:
            Optional[Dict[str, Any]]: Consultation summary or None if no active consultation.
        """
        if self.status != "In Consultation" or not self.current_patient:
            logger.warning(self._format_log_entry("CONSULTATION_ERROR", 
                "No active consultation to end"))
            print(self._format_console_message("ERROR", 
                "No active consultation to end"))
            return None
        
        # Calculate consultation duration
        end_time = datetime.now()
        consultation_record = None
        
        # Find and update the current consultation record
        for record in reversed(self.consultation_history):
            if (record["patient_id"] == self.current_patient.id and 
                record["end_time"] is None):
                record["end_time"] = end_time
                duration = end_time - record["start_time"]
                record["duration_minutes"] = duration.total_seconds() / 60
                consultation_record = record
                break
        
        # Update doctor's state
        patient_name = self.current_patient.name
        patient_id = self.current_patient.id
        self.patients_seen_today += 1
        self.current_patient = None
        self.update_status("Available")
        
        # Update performance metrics
        self._update_performance_metrics(consultation_record)
        
        logger.info(self._format_log_entry("CONSULTATION_END", 
            f"Ended consultation with Patient {patient_id} ({patient_name}) - "
            f"Duration: {consultation_record['duration_minutes']:.1f} minutes"))
        print(self._format_console_message("CONSULT", 
            f"Dr. {self.name} finished consultation with {patient_name}"))
        
        return consultation_record

    def set_shift(self, start_time: datetime, end_time: datetime) -> None:
        """
        Sets the doctor's shift hours with validation.
        
        Args:
            start_time (datetime): Shift start time.
            end_time (datetime): Shift end time.
        """
        if start_time >= end_time:
            logger.error(self._format_log_entry("SHIFT_ERROR", 
                "Invalid shift times - start time must be before end time"))
            return
        
        self.shift_start = start_time
        self.shift_end = end_time
        
        shift_duration = (end_time - start_time).total_seconds() / 3600
        
        logger.info(self._format_log_entry("SHIFT_SET", 
            f"Shift scheduled: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} "
            f"({shift_duration:.1f} hours)"))
        print(self._format_console_message("SHIFT", 
            f"Dr. {self.name}'s shift: {start_time.strftime('%H:%M')} to {end_time.strftime('%H:%M')}"))

    def add_break(self, break_start: datetime, break_end: datetime, break_type: str = "Break") -> bool:
        """
        Adds a break period to the doctor's schedule.
        
        Args:
            break_start (datetime): Break start time.
            break_end (datetime): Break end time.
            break_type (str): Type of break (Break, Lunch, Meeting, etc.).
            
        Returns:
            bool: True if break was added successfully, False if there's a conflict.
        """
        # Check for conflicts with existing breaks or appointments
        for existing_break in self.break_times:
            if (break_start < existing_break["end_time"] and 
                break_end > existing_break["start_time"]):
                logger.warning(self._format_log_entry("BREAK_CONFLICT", 
                    f"Break conflicts with existing {existing_break['type']} at "
                    f"{existing_break['start_time'].strftime('%H:%M')}"))
                return False
        
        break_record = {
            "start_time": break_start,
            "end_time": break_end,
            "type": break_type,
            "duration_minutes": (break_end - break_start).total_seconds() / 60
        }
        
        self.break_times.append(break_record)
        
        logger.info(self._format_log_entry("BREAK_ADDED", 
            f"{break_type} scheduled: {break_start.strftime('%H:%M')} - {break_end.strftime('%H:%M')}"))
        
        return True

    def is_available(self) -> bool:
        """
        Comprehensive availability check considering all factors.
        
        Returns:
            bool: True if doctor is available for new patients, False otherwise.
        """
        now = datetime.now()
        
        # Check if doctor's status allows new patients
        config = get_config()
        available_statuses = ["Available"] # Only "Available" status allows new patients
        if self.status not in available_statuses:
            return False
        
        # Check shift hours
        if self.shift_start and self.shift_end:
            current_time = now.time()
            if not (self.shift_start.time() <= current_time <= self.shift_end.time()):
                return False
        
        # Check daily patient limit
        if self.patients_seen_today >= self.max_patients_per_day:
            return False
        
        # Check if currently on break
        for break_period in self.break_times:
            if break_period["start_time"] <= now <= break_period["end_time"]:
                return False
        
        return True

    def add_scheduled_appointment(self, patient, appointment_time: datetime, 
                                 duration: timedelta = timedelta(minutes=30)) -> bool:
        """
        Schedules an appointment with enhanced conflict checking.
        
        Args:
            patient: The patient object.
            appointment_time (datetime): The scheduled appointment time.
            duration (timedelta): Duration of the appointment.
            
        Returns:
            bool: True if appointment was scheduled successfully, False if there's a conflict.
        """
        end_time = appointment_time + duration
        
        # Check for schedule conflicts
        for scheduled_time, existing_appointment in self.schedule.items():
            existing_end = scheduled_time + existing_appointment["duration"]
            if (appointment_time < existing_end and end_time > scheduled_time):
                logger.warning(self._format_log_entry("APPOINTMENT_CONFLICT", 
                    f"Appointment conflicts with existing appointment at {scheduled_time}"))
                print(self._format_console_message("CONFLICT", 
                    f"Schedule conflict for Dr. {self.name} at {appointment_time}"))
                return False
        
        # Check for break conflicts
        for break_period in self.break_times:
            if (appointment_time < break_period["end_time"] and 
                end_time > break_period["start_time"]):
                logger.warning(self._format_log_entry("APPOINTMENT_BREAK_CONFLICT", 
                    f"Appointment conflicts with {break_period['type']} at {break_period['start_time']}"))
                return False
        
        # Create appointment
        appointment = {
            "patient_id": patient.id,
            "patient_name": patient.name,
            "start_time": appointment_time,
            "end_time": end_time,
            "duration": duration,
            "status": "Scheduled",
            "appointment_type": "Regular"
        }
        
        self.schedule[appointment_time] = appointment
        
        logger.info(self._format_log_entry("APPOINTMENT_SCHEDULED", 
            f"Appointment with Patient {patient.id} ({patient.name}) at {appointment_time}"))
        print(self._format_console_message("APPOINTMENT", 
            f"Appointment scheduled for {patient.name} with Dr. {self.name}"))
        
        return True

    def get_daily_summary(self) -> Dict[str, Any]:
        """
        Generates a comprehensive daily summary for the doctor.
        
        Returns:
            Dict[str, Any]: Daily summary with key metrics.
        """
        today = datetime.now().date()
        today_consultations = [
            c for c in self.consultation_history 
            if c["start_time"].date() == today
        ]
        
        total_consultation_time = sum(
            c.get("duration_minutes", 0) for c in today_consultations
        )
        
        avg_consultation_time = (
            total_consultation_time / len(today_consultations) 
            if today_consultations else 0
        )
        
        summary = {
            "doctor_info": {
                "name": self.name,
                "specialty": self.specialty,
                "staff_id": self.staff_id,
                "experience_years": self.years_experience
            },
            "daily_metrics": {
                "date": today.isoformat(),
                "patients_seen": self.patients_seen_today,
                "max_capacity": self.max_patients_per_day,
                "utilization_rate": round((self.patients_seen_today / self.max_patients_per_day) * 100, 1),
                "total_consultation_time_minutes": round(total_consultation_time, 1),
                "average_consultation_time_minutes": round(avg_consultation_time, 1)
            },
            "current_status": {
                "status": self.status,
                "current_patient": self.current_patient.name if self.current_patient else None,
                "shift_start": self.shift_start.strftime('%H:%M') if self.shift_start else None,
                "shift_end": self.shift_end.strftime('%H:%M') if self.shift_end else None,
                "is_available": self.is_available()
            },
            "performance_metrics": self.performance_metrics
        }
        
        return summary

    def _update_performance_metrics(self, consultation_record: Dict[str, Any]) -> None:
        """Update performance metrics based on completed consultation."""
        self.performance_metrics["total_consultations"] += 1
        
        if consultation_record and consultation_record.get("duration_minutes"):
            # Update running average consultation time
            total_consults = self.performance_metrics["total_consultations"]
            current_avg = self.performance_metrics["average_consultation_time"]
            new_duration = consultation_record["duration_minutes"]
            
            new_avg = ((current_avg * (total_consults - 1)) + new_duration) / total_consults
            self.performance_metrics["average_consultation_time"] = round(new_avg, 2)

    def _format_log_entry(self, event_type: str, message: str) -> str:
        """Format log entry with consistent structure."""
        return f"[DOCTOR-{self.staff_id}] [{event_type}] {message}"

    def _format_console_message(self, event_type: str, message: str) -> str:
        """Format console message with improved readability."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] [{event_type}] {message}"

    def __str__(self) -> str:
        """String representation of the Doctor object."""
        return (f"Dr. {self.name} ({self.specialty}) - Status: {self.status} - "
                f"Patients Today: {self.patients_seen_today}/{self.max_patients_per_day}")

    def __repr__(self) -> str:
        """Detailed representation of the Doctor object."""
        return (f"Doctor(name='{self.name}', specialty='{self.specialty}', "
                f"staff_id='{self.staff_id}', status='{self.status}', "
                f"experience={self.years_experience})")