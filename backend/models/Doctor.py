from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
import threading
from ..config import get_config

# Configure logger for Doctor class
logger = logging.getLogger(__name__)

class ThreadSafeDoctor:
    def __init__(self, name: str, specialty: str, staff_id: str = None, gender: str = None, age: str = None,
                 years_experience: int = 0, max_patients_per_day: int = 20):
        """
        Initializes a thread-safe Doctor instance.
        
        Args:
            name (str): The doctor's name.
            specialty (str): The doctor's medical specialty.
            staff_id (str, optional): The doctor's staff ID.
            years_experience (int, optional): Years of professional experience.
            max_patients_per_day (int, optional): Maximum patients the doctor can see per day.
        """
        config = get_config()
        
        # Thread-safe locks for doctor operations
        self.consultation_lock = threading.RLock()  # For consultation state
        self.schedule_lock = threading.RLock()      # For scheduling operations
        self.metrics_lock = threading.RLock()       # For performance metrics
        
        # Basic doctor information
        self.name = name
        self.gender = gender
        self.age = age
        self.specialty = self._validate_specialty(specialty)
        self.staff_id = staff_id or f"D{id(self) % 10000:04d}"
        self.years_experience = years_experience
        self.max_patients_per_day = max_patients_per_day
        
        # Status management using configuration
        available_statuses = config.get_doctor_statuses()
        self.status = available_statuses[0] if available_statuses else "Available"
        
        # Current state (thread-safe access needed)
        self.current_patient = None
        self.patients_seen_today = 0
        self.consultation_start_time = None
        
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
            "specialization_cases": 0,
            "concurrent_consultations_handled": 0
        }
        
        # Log doctor initialization
        logger.info(self._format_log_entry("INITIALIZATION", 
            f"Thread-safe doctor initialized - Specialty: {self.specialty}, Experience: {years_experience} years"))
        print(self._format_console_message("INIT", 
            f"Dr. {self.name} ({self.specialty}) joined the hospital [Thread-Safe]"))

    def _validate_specialty(self, specialty: str) -> str:
        """Validates specialty against configuration (thread-safe)."""
        config = get_config()
        available_specialties = config.get_specialties()
        
        for available in available_specialties:
            if specialty.lower() in available.lower() or available.lower() in specialty.lower():
                return available
        
        logger.warning(self._format_log_entry("SPECIALTY_WARNING", 
            f"Specialty '{specialty}' not found in config, defaulting to 'General'"))
        return "General"

    def update_status(self, status: str) -> None:
        """Thread-safe status update."""
        with self.consultation_lock:
            config = get_config()
            available_statuses = config.get_doctor_statuses()
            
            if status not in available_statuses:
                logger.warning(self._format_log_entry("STATUS_WARNING", 
                    f"Status '{status}' not in configured statuses: {available_statuses}"))
            
            previous_status = self.status
            self.status = status
            
            # Log status change with thread information
            thread_name = threading.current_thread().name
            logger.info(self._format_log_entry("STATUS_CHANGE", 
                f"[Thread: {thread_name}] Status changed from '{previous_status}' to '{status}'"))
            print(self._format_console_message("STATUS", 
                f"[{thread_name}] Dr. {self.name} is now {status}"))

    def start_consultation(self, patient) -> bool:
        """
        Thread-safe consultation start with enhanced concurrency handling.
        
        Args:
            patient: The patient object to consult with.
            
        Returns:
            bool: True if consultation started successfully, False otherwise.
        """
        with self.consultation_lock:
            thread_name = threading.current_thread().name
            
            # Check availability
            if not self.is_available():
                logger.warning(self._format_log_entry("CONSULTATION_BLOCKED", 
                    f"[Thread: {thread_name}] Cannot start consultation - Doctor not available"))
                print(self._format_console_message("ERROR", 
                    f"[{thread_name}] Dr. {self.name} is {self.status}, cannot start consultation"))
                return False
            
            # Start consultation
            self.current_patient = patient
            self.consultation_start_time = datetime.now()
            self.update_status("In Consultation")
            
            # Record consultation in history
            consultation_record = {
                "consultation_id": len(self.consultation_history) + 1,
                "patient_id": patient.id,
                "patient_name": patient.name,
                "start_time": self.consultation_start_time,
                "end_time": None,
                "duration_minutes": None,
                "consultation_type": "Regular",
                "notes": [],
                "thread_id": thread_name
            }
            
            self.consultation_history.append(consultation_record)
            
            logger.info(self._format_log_entry("CONSULTATION_START", 
                f"[Thread: {thread_name}] Started consultation with Patient {patient.id} ({patient.name})"))
            print(self._format_console_message("CONSULT", 
                f"[{thread_name}] Dr. {self.name} started consultation with {patient.name}"))
            
            return True

    def end_consultation(self) -> Optional[Dict[str, Any]]:
        """
        Thread-safe consultation end with detailed metrics.
        
        Returns:
            Optional[Dict[str, Any]]: Consultation summary or None if no active consultation.
        """
        with self.consultation_lock:
            thread_name = threading.current_thread().name
            
            if self.status != "In Consultation" or not self.current_patient:
                logger.warning(self._format_log_entry("CONSULTATION_ERROR", 
                    f"[Thread: {thread_name}] No active consultation to end"))
                print(self._format_console_message("ERROR", 
                    f"[{thread_name}] No active consultation to end"))
                return None
            
            # Calculate consultation duration
            end_time = datetime.now()
            consultation_record = None
            
            # Find and update the current consultation record
            for record in reversed(self.consultation_history):
                if (record["patient_id"] == self.current_patient.id and 
                    record["end_time"] is None):
                    record["end_time"] = end_time
                    if self.consultation_start_time:
                        duration = end_time - self.consultation_start_time
                        record["duration_minutes"] = duration.total_seconds() / 60
                    consultation_record = record
                    break
            
            # Update doctor's state
            patient_name = self.current_patient.name
            patient_id = self.current_patient.id
            self.patients_seen_today += 1
            self.current_patient = None
            self.consultation_start_time = None
            self.update_status("Available")
            
            # Update performance metrics (thread-safe)
            self._update_performance_metrics(consultation_record)
            
            logger.info(self._format_log_entry("CONSULTATION_END", 
                f"[Thread: {thread_name}] Ended consultation with Patient {patient_id} ({patient_name}) - "
                f"Duration: {consultation_record['duration_minutes']:.1f} minutes"))
            print(self._format_console_message("CONSULT", 
                f"[{thread_name}] Dr. {self.name} finished consultation with {patient_name}"))
            
            return consultation_record

    def set_shift(self, start_time: datetime, end_time: datetime) -> None:
        """Thread-safe shift setting."""
        with self.schedule_lock:
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
        """Thread-safe break addition."""
        with self.schedule_lock:
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
        Thread-safe comprehensive availability check.
        
        Returns:
            bool: True if doctor is available for new patients, False otherwise.
        """
        with self.consultation_lock:
            now = datetime.now()
            
            # Check if doctor's status allows new patients
            if self.status != "Available":
                return False
            
            # Check if already at patient limit
            if self.patients_seen_today >= self.max_patients_per_day:
                return False
            
            # Check shift hours
            if self.shift_start and self.shift_end:
                current_time = now.time()
                if not (self.shift_start.time() <= current_time <= self.shift_end.time()):
                    return False
            
            # Check if currently on break
            for break_period in self.break_times:
                if break_period["start_time"] <= now <= break_period["end_time"]:
                    return False
            
            return True

    def add_scheduled_appointment(self, patient, appointment_time: datetime, 
                                 duration: timedelta = timedelta(minutes=30)) -> bool:
        """Thread-safe appointment scheduling."""
        with self.schedule_lock:
            end_time = appointment_time + duration
            thread_name = threading.current_thread().name
            
            # Check for schedule conflicts
            for scheduled_time, existing_appointment in self.schedule.items():
                existing_end = scheduled_time + existing_appointment["duration"]
                if (appointment_time < existing_end and end_time > scheduled_time):
                    logger.warning(self._format_log_entry("APPOINTMENT_CONFLICT", 
                        f"[Thread: {thread_name}] Appointment conflicts with existing appointment"))
                    return False
            
            # Check for break conflicts
            for break_period in self.break_times:
                if (appointment_time < break_period["end_time"] and 
                    end_time > break_period["start_time"]):
                    logger.warning(self._format_log_entry("APPOINTMENT_BREAK_CONFLICT", 
                        f"[Thread: {thread_name}] Appointment conflicts with break"))
                    return False
            
            # Create appointment
            appointment = {
                "patient_id": patient.id,
                "patient_name": patient.name,
                "start_time": appointment_time,
                "end_time": end_time,
                "duration": duration,
                "status": "Scheduled",
                "appointment_type": "Regular",
                "thread_id": thread_name
            }
            
            self.schedule[appointment_time] = appointment
            
            logger.info(self._format_log_entry("APPOINTMENT_SCHEDULED", 
                f"[Thread: {thread_name}] Appointment with Patient {patient.id} ({patient.name})"))
            
            return True

    def get_daily_summary(self) -> Dict[str, Any]:
        """Thread-safe daily summary generation."""
        with self.consultation_lock, self.metrics_lock:
            today = datetime.now().date()
            today_consultations = [
                c for c in self.consultation_history 
                if c["start_time"].date() == today
            ]
            
            total_consultation_time = sum(
                (val if val is not None else 0) 
                for val in (c.get("duration_minutes") for c in today_consultations)
            )
            
            avg_consultation_time = (
                total_consultation_time / len(today_consultations) 
                if today_consultations else 0
            )
            
            # Thread usage analysis
            thread_usage = {}
            for consultation in today_consultations:
                thread_id = consultation.get("thread_id", "Unknown")
                thread_usage[thread_id] = thread_usage.get(thread_id, 0) + 1
            
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
                "performance_metrics": self.performance_metrics.copy(),
                "threading_metrics": {
                    "consultations_by_thread": thread_usage,
                    "concurrent_safety_enabled": True,
                    "total_threads_served": len(thread_usage)
                }
            }
            
            return summary

    def _update_performance_metrics(self, consultation_record: Dict[str, Any]) -> None:
        """Thread-safe performance metrics update."""
        with self.metrics_lock:
            self.performance_metrics["total_consultations"] += 1
            
            if consultation_record and consultation_record.get("duration_minutes"):
                # Update running average consultation time
                total_consults = self.performance_metrics["total_consultations"]
                current_avg = self.performance_metrics["average_consultation_time"]
                new_duration = consultation_record["duration_minutes"]
                
                new_avg = ((current_avg * (total_consults - 1)) + new_duration) / total_consults
                self.performance_metrics["average_consultation_time"] = round(new_avg, 2)
            
            # Track concurrent handling
            if consultation_record and consultation_record.get("thread_id"):
                self.performance_metrics["concurrent_consultations_handled"] += 1

    def get_workload_status(self) -> Dict[str, Any]:
        """
        Get current workload status for load balancing in threaded environment.
        
        Returns:
            Dict[str, Any]: Workload information for thread scheduling.
        """
        with self.consultation_lock:
            remaining_capacity = self.max_patients_per_day - self.patients_seen_today
            workload_percentage = (self.patients_seen_today / self.max_patients_per_day) * 100
            
            status = {
                "doctor_name": self.name,
                "specialty": self.specialty,
                "is_available": self.is_available(),
                "current_status": self.status,
                "patients_seen_today": self.patients_seen_today,
                "remaining_capacity": remaining_capacity,
                "workload_percentage": round(workload_percentage, 1),
                "consultation_in_progress": self.current_patient is not None,
                "thread_safe": True
            }
            
            return status

    def can_handle_priority_patient(self, priority_level: int) -> bool:
        """
        Check if doctor can handle a patient with specific priority level.
        Used for intelligent patient-doctor matching in threaded environment.
        
        Args:
            priority_level (int): Patient priority level.
            
        Returns:
            bool: True if doctor can handle this priority level.
        """
        with self.consultation_lock:
            if not self.is_available():
                return False
            
            # Emergency patients (priority 1) can interrupt non-emergency consultations
            if priority_level == 1:
                return True
            
            # Standard patients (priority 2+) need doctor to be completely available
            return self.status == "Available" and self.current_patient is None

    def estimate_availability_time(self) -> Optional[datetime]:
        """
        Estimate when the doctor will next be available.
        Useful for queuing patients in threaded environment.
        
        Returns:
            Optional[datetime]: Estimated availability time or None if available now.
        """
        with self.consultation_lock:
            if self.is_available():
                return datetime.now()
            
            # If in consultation, estimate based on average consultation time
            if self.current_patient and self.consultation_start_time:
                avg_consultation_minutes = self.performance_metrics.get("average_consultation_time", 30)
                estimated_end = self.consultation_start_time + timedelta(minutes=avg_consultation_minutes)
                return estimated_end
            
            # If on break, return break end time
            now = datetime.now()
            for break_period in self.break_times:
                if break_period["start_time"] <= now <= break_period["end_time"]:
                    return break_period["end_time"]
            
            # If off duty, return shift start time (next day)
            if self.shift_start:
                next_shift = datetime.now().replace(hour=self.shift_start.hour, 
                                                   minute=self.shift_start.minute, 
                                                   second=0, microsecond=0)
                if next_shift <= datetime.now():
                    next_shift += timedelta(days=1)
                return next_shift
            
            return None

    def _format_log_entry(self, event_type: str, message: str) -> str:
        """Format log entry with consistent structure."""
        return f"[DOCTOR-{self.staff_id}] [{event_type}] {message}"

    def _format_console_message(self, event_type: str, message: str) -> str:
        """Format console message with improved readability."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] [{event_type}] {message}"

    def __str__(self) -> str:
        """String representation of the ThreadSafeDoctor object."""
        with self.consultation_lock:
            return (f"Dr. {self.name} ({self.specialty}) - Status: {self.status} - "
                    f"Patients Today: {self.patients_seen_today}/{self.max_patients_per_day} [Thread-Safe]")

    def __repr__(self) -> str:
        """Detailed representation of the ThreadSafeDoctor object."""
        return (f"ThreadSafeDoctor(name='{self.name}', specialty='{self.specialty}', "
                f"staff_id='{self.staff_id}', status='{self.status}', "
                f"experience={self.years_experience})")

# For backward compatibility
Doctor = ThreadSafeDoctor