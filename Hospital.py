import random
import time
from datetime import datetime, timedelta
import uuid
from typing import Dict, Any, List, Optional, Tuple
import logging
from config import get_config

# Configure logger for Hospital class
logger = logging.getLogger(__name__)

class Hospital:
    def __init__(self, name: str, doctors: List = None):
        """
        Initializes the Hospital instance using configuration settings.
        
        Args:
            name (str): The name of the hospital.
            doctors (list, optional): A list of Doctor objects in the hospital.
        """
        config = get_config()
        
        # Basic hospital information
        self.id = str(uuid.uuid4())
        self.name = name
        self.doctors = doctors or []
        self.patients = {}  # Dictionary of all patients by ID
        self.active_patients = {}  # Patients currently in the hospital
        
        # Initialize rooms based on configuration
        self.rooms = self._initialize_rooms()
        
        # Initialize medical devices from configuration
        self.medical_devices = self._initialize_devices()
        
        # Initialize departments based on configuration
        self.departments = self._initialize_departments()
        
        # Assign doctors to departments
        self._assign_doctors_to_departments()
        
        # Tracking systems
        self.resource_logs = []
        self.patient_logs = []
        self.operation_logs = []
        
        # Financial tracking
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
        
        # Log hospital initialization
        logger.info(self._format_log_entry("INITIALIZATION", 
            f"Hospital '{name}' initialized with {len(self.doctors)} doctors and {len(self.departments)} departments"))
        print(self._format_console_header())
        print(self._format_console_message("INIT", 
            f"Welcome to {self.name}! Hospital system initialized successfully"))

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
        
        # Ensure essential room types exist even if not in config
        essential_rooms = ["waiting", "consultation", "triage", "registration", "pharmacy"]
        for room_type in essential_rooms:
            if room_type not in rooms:
                rooms[room_type] = {"total": 1, "available": 1, "occupied": 0, "maintenance": 0}
        
        # Create a readable list of rooms with their counts
        room_list = []
        for room_type, room_info in rooms.items():
            room_list.append(f"{room_type}({room_info['total']})")
        
        logger.info(self._format_log_entry("ROOMS_INIT", 
            f"Initialized rooms: {', '.join(room_list)}"
        ))
        
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
        
        logger.info(self._format_log_entry("DEVICES_INIT", 
            f"Initialized medical devices: {', '.join(device_list)}"))
        
        return devices

    def _initialize_departments(self) -> Dict[str, Dict[str, Any]]:
        """Initialize departments based on configuration."""
        config = get_config()
        departments_config = config.hospital_data.doctor_per_department
        
        departments = {}
        for dept_name, capacity in departments_config.items():
            departments[dept_name] = {
                "capacity": capacity * 10,  # Patient capacity per department
                "staff": [],
                "current_patients": 0,
                "equipment": [],
                "specialization": dept_name.lower()
            }
        
        # Add emergency department if not present
        if "Emergency" not in departments:
            departments["Emergency"] = {
                "capacity": 15,
                "staff": [],
                "current_patients": 0,
                "equipment": [],
                "specialization": "emergency"
            }
        
        logger.info(self._format_log_entry("DEPARTMENTS_INIT", 
            f"Initialized departments: {', '.join(departments.keys())}"))
        
        return departments

    def _assign_doctors_to_departments(self) -> None:
        """Assign doctors to appropriate departments based on their specialty."""
        for doctor in self.doctors:
            specialty_lower = doctor.specialty.lower()
            assigned = False
            
            # Try to match specialty with department
            for dept_name, dept_info in self.departments.items():
                dept_specialization = dept_info["specialization"]
                if (specialty_lower in dept_specialization or 
                    dept_specialization in specialty_lower or
                    specialty_lower == dept_name.lower()):
                    dept_info["staff"].append(doctor)
                    assigned = True
                    logger.info(self._format_log_entry("DOCTOR_ASSIGNMENT", 
                        f"Dr. {doctor.name} ({doctor.specialty}) assigned to {dept_name} department"))
                    break
            
            # If no specific department match, assign to General
            if not assigned:
                if "General" not in self.departments:
                    self.departments["General"] = {
                        "capacity": 20,
                        "staff": [],
                        "current_patients": 0,
                        "equipment": [],
                        "specialization": "general"
                    }
                self.departments["General"]["staff"].append(doctor)
                logger.info(self._format_log_entry("DOCTOR_ASSIGNMENT", 
                    f"Dr. {doctor.name} ({doctor.specialty}) assigned to General department"))

    def admit_patient(self, patient) -> bool:
        """
        Admits a new patient to the hospital with comprehensive logging.
        
        Args:
            patient: The patient object to admit.
            
        Returns:
            bool: True if admission was successful, False otherwise.
        """
        if patient.id in self.active_patients:
            logger.warning(self._format_log_entry("ADMISSION_DUPLICATE", 
                f"Patient {patient.id} ({patient.name}) is already admitted"))
            print(self._format_console_message("WARNING", 
                f"Patient {patient.name} is already admitted"))
            return False
        
        # Add to hospital records
        self.patients[patient.id] = patient
        self.active_patients[patient.id] = patient
        
        # Log the admission
        admission_record = {
            "event": "admission",
            "patient_id": patient.id,
            "patient_name": patient.name,
            "timestamp": datetime.now(),
            "priority": patient.priority,
            "insurance": patient.insurance
        }
        
        self.patient_logs.append(admission_record)
        self.daily_statistics["patients_processed"] += 1
        
        logger.info(self._format_log_entry("PATIENT_ADMISSION", 
            f"Patient {patient.id} ({patient.name}) admitted - Priority: {patient.priority}"))
        print(self._format_console_separator())
        print(self._format_console_message("ADMISSION", 
            f"Admitting {patient.name} to {self.name} - Priority Level {patient.priority}"))
        
        return True

    def discharge_patient(self, patient) -> bool:
        """
        Discharges a patient from the hospital with comprehensive tracking.
        
        Args:
            patient: The patient object to discharge.
            
        Returns:
            bool: True if discharge was successful, False otherwise.
        """
        if patient.id not in self.active_patients:
            logger.warning(self._format_log_entry("DISCHARGE_ERROR", 
                f"Patient {patient.id} ({patient.name}) is not currently admitted"))
            print(self._format_console_message("WARNING", 
                f"Patient {patient.name} is not currently admitted"))
            return False
        
        # Process discharge
        patient.discharge()
        
        # Remove from active patients
        del self.active_patients[patient.id]
        
        # Calculate stay duration
        total_stay = (patient.discharge_time - patient.arrival_time).total_seconds() / 3600
        
        # Log the discharge
        discharge_record = {
            "event": "discharge",
            "patient_id": patient.id,
            "patient_name": patient.name,
            "timestamp": patient.discharge_time,
            "total_stay_hours": round(total_stay, 2),
            "diagnoses_count": len(patient.medical_record.get("diagnoses", [])),
            "prescriptions_count": len(patient.medical_record.get("prescriptions", []))
        }
        
        self.patient_logs.append(discharge_record)
        
        logger.info(self._format_log_entry("PATIENT_DISCHARGE", 
            f"Patient {patient.id} ({patient.name}) discharged after {total_stay:.1f} hours"))
        print(self._format_console_separator())
        print(self._format_console_message("DISCHARGE", 
            f"{patient.name} discharged from {self.name} after {total_stay:.1f} hours"))
        
        return True

    def allocate_room(self, room_type: str) -> bool:
        """
        Allocates a room of a given type with enhanced logging and validation.
        
        Args:
            room_type (str): The type of room to allocate.
            
        Returns:
            bool: True if room was allocated, False otherwise.
        """
        if room_type not in self.rooms:
            logger.error(self._format_log_entry("ROOM_ERROR", 
                f"Room type '{room_type}' does not exist"))
            print(self._format_console_message("ERROR", 
                f"Room type '{room_type}' not available"))
            return False
        
        room_info = self.rooms[room_type]
        if room_info["available"] <= 0:
            logger.warning(self._format_log_entry("ROOM_UNAVAILABLE", 
                f"No {room_type} rooms available - All {room_info['total']} rooms occupied"))
            print(self._format_console_message("CAPACITY", 
                f"No {room_type} rooms available"))
            return False
        
        # Allocate room
        room_info["available"] -= 1
        room_info["occupied"] += 1
        
        # Log resource utilization
        utilization_record = {
            "resource_type": "room",
            "resource_name": room_type,
            "action": "allocate",
            "timestamp": datetime.now(),
            "available": room_info["available"],
            "total": room_info["total"],
            "utilization_rate": (room_info["occupied"] / room_info["total"]) * 100
        }
        
        self.resource_logs.append(utilization_record)
        
        logger.info(self._format_log_entry("ROOM_ALLOCATION", 
            f"Allocated {room_type} room - {room_info['available']}/{room_info['total']} remaining"))
        print(self._format_console_message("RESOURCE", 
            f"Allocated {room_type} room ({room_info['available']} remaining)"))
        
        return True

    def release_room(self, room_type: str) -> bool:
        """
        Releases a room back to the available pool with logging.
        
        Args:
            room_type (str): The type of room to release.
            
        Returns:
            bool: True if room was released, False otherwise.
        """
        if room_type not in self.rooms:
            logger.error(self._format_log_entry("ROOM_ERROR", 
                f"Room type '{room_type}' does not exist"))
            return False
        
        room_info = self.rooms[room_type]
        if room_info["occupied"] <= 0:
            logger.warning(self._format_log_entry("ROOM_RELEASE_ERROR", 
                f"No {room_type} rooms to release - All rooms already available"))
            return False
        
        # Release room
        room_info["available"] += 1
        room_info["occupied"] -= 1
        
        # Log resource utilization
        utilization_record = {
            "resource_type": "room",
            "resource_name": room_type,
            "action": "release",
            "timestamp": datetime.now(),
            "available": room_info["available"],
            "total": room_info["total"],
            "utilization_rate": (room_info["occupied"] / room_info["total"]) * 100
        }
        
        self.resource_logs.append(utilization_record)
        
        logger.info(self._format_log_entry("ROOM_RELEASE", 
            f"Released {room_type} room - {room_info['available']}/{room_info['total']} available"))
        print(self._format_console_message("RESOURCE", 
            f"Released {room_type} room ({room_info['available']} available)"))
        
        return True

    def allocate_device(self, device_name: str) -> bool:
        """
        Allocates a medical device for use.
        
        Args:
            device_name (str): The name of the device to allocate.
            
        Returns:
            bool: True if device was allocated, False otherwise.
        """
        if device_name not in self.medical_devices:
            logger.warning(self._format_log_entry("DEVICE_ERROR", 
                f"Medical device '{device_name}' not available in hospital"))
            return False
        
        device_info = self.medical_devices[device_name]
        if device_info["available"] <= 0:
            logger.warning(self._format_log_entry("DEVICE_UNAVAILABLE", 
                f"{device_name} is currently in use or under maintenance"))
            return False
        
        device_info["available"] -= 1
        device_info["in_use"] += 1
        device_info["usage_hours"] += 1
        
        logger.info(self._format_log_entry("DEVICE_ALLOCATION", 
            f"Allocated {device_name} for use"))
        
        return True

    def release_device(self, device_name: str) -> bool:
        """Releases a medical device back to available pool."""
        if device_name not in self.medical_devices:
            return False
        
        device_info = self.medical_devices[device_name]
        if device_info["in_use"] <= 0:
            return False
        
        device_info["available"] += 1
        device_info["in_use"] -= 1
        
        logger.info(self._format_log_entry("DEVICE_RELEASE", 
            f"Released {device_name} from use"))
        
        return True

    def find_available_doctor(self, specialty: str = None, department: str = None):
        """
        Finds an available doctor with enhanced filtering and load balancing.
        
        Args:
            specialty (str, optional): Required specialty.
            department (str, optional): Required department.
            
        Returns:
            Doctor: An available doctor or None if none found.
        """
        potential_doctors = []
        
        if department and department in self.departments:
            potential_doctors = self.departments[department]["staff"]
            logger.debug(self._format_log_entry("DOCTOR_SEARCH", 
                f"Searching in {department} department - {len(potential_doctors)} doctors"))
        elif specialty:
            potential_doctors = [d for d in self.doctors if specialty.lower() in d.specialty.lower()]
            logger.debug(self._format_log_entry("DOCTOR_SEARCH", 
                f"Searching for {specialty} specialty - {len(potential_doctors)} doctors"))
        else:
            potential_doctors = self.doctors
        
        # Filter for available doctors
        available_doctors = [d for d in potential_doctors if d.is_available()]
        
        if not available_doctors:
            logger.warning(self._format_log_entry("DOCTOR_UNAVAILABLE", 
                f"No available doctors found for specialty='{specialty}', department='{department}'"))
            print(self._format_console_message("CAPACITY", 
                "No doctors currently available"))
            return None
        
        # Load balancing: prefer doctors with fewer patients seen today
        available_doctors.sort(key=lambda d: (d.patients_seen_today, -d.years_experience))
        selected_doctor = available_doctors[0]
        
        logger.info(self._format_log_entry("DOCTOR_ASSIGNED", 
            f"Dr. {selected_doctor.name} ({selected_doctor.specialty}) selected - "
            f"Patients today: {selected_doctor.patients_seen_today}"))
        
        return selected_doctor

    def bill_patient(self, patient, amount: float, service_description: str) -> str:
        """
        Creates a detailed billing record for a patient.
        
        Args:
            patient: The patient to bill.
            amount (float): The amount to bill.
            service_description (str): Description of the service.
            
        Returns:
            str: The bill ID.
        """
        bill_id = str(uuid.uuid4())[:8]
        bill = {
            "bill_id": bill_id,
            "patient_id": patient.id,
            "patient_name": patient.name,
            "amount": amount,
            "service": service_description,
            "timestamp": datetime.now(),
            "status": "Pending",
            "insurance": patient.insurance,
            "department": "General"
        }
        
        self.billing_records.append(bill)
        
        logger.info(self._format_log_entry("BILLING", 
            f"Bill {bill_id} created - Patient {patient.id}: ${amount} for {service_description}"))
        print(self._format_console_message("BILLING", 
            f"Bill created for {patient.name}: ${amount} - {service_description}"))
        
        return bill_id

    def process_payment(self, bill_id: str, amount_paid: float) -> bool:
        """
        Processes payment for a bill with enhanced tracking.
        
        Args:
            bill_id (str): The ID of the bill.
            amount_paid (float): The amount paid.
            
        Returns:
            bool: True if payment processed successfully, False otherwise.
        """
        for bill in self.billing_records:
            if bill["bill_id"] == bill_id:
                if amount_paid >= bill["amount"]:
                    bill["status"] = "Paid"
                    bill["amount_paid"] = amount_paid
                    bill["payment_time"] = datetime.now()
                    bill["change"] = amount_paid - bill["amount"]
                    
                    self.revenue += bill["amount"]
                    
                    logger.info(self._format_log_entry("PAYMENT", 
                        f"Payment processed - Bill {bill_id}: ${amount_paid} (Change: ${bill['change']})"))
                    print(self._format_console_message("PAYMENT", 
                        f"Payment processed for {bill['patient_name']}: ${amount_paid}"))
                    
                    return True
                else:
                    bill["status"] = "Partial Payment"
                    bill["amount_paid"] = amount_paid
                    bill["payment_time"] = datetime.now()
                    bill["remaining_balance"] = bill["amount"] - amount_paid
                    
                    self.revenue += amount_paid
                    
                    logger.info(self._format_log_entry("PARTIAL_PAYMENT", 
                        f"Partial payment - Bill {bill_id}: ${amount_paid} (Remaining: ${bill['remaining_balance']})"))
                    
                    return True
        
        logger.error(self._format_log_entry("PAYMENT_ERROR", f"Bill {bill_id} not found"))
        return False

    # Simulation methods with improved logging
    def simulate_patient_visit(self, patient) -> None:
        """
        Simulates a complete patient visit with detailed process logging.
        
        Args:
            patient: The patient object to process.
        """
        visit_start_time = datetime.now()
        
        print(self._format_console_header())
        print(self._format_console_message("VISIT_START", 
            f"Starting visit simulation for {patient.name}"))
        
        # Stage 1: Admit patient
        if not self.admit_patient(patient):
            return
        
        try:
            # Stage 2: Triage
            self._simulate_triage(patient)
            
            # Stage 3: Registration
            self._simulate_registration(patient)
            
            # Stage 4: Waiting and consultation
            needs_tests = self._simulate_consultation(patient)
            
            # Stage 5: Tests if needed
            if needs_tests:
                self._simulate_tests(patient, needs_tests)
                # Follow-up consultation
                self._simulate_follow_up_consultation(patient)
            
            # Stage 6: Pharmacy if prescriptions
            if patient.medical_record.get("prescriptions"):
                self._simulate_pharmacy(patient)
            
        except Exception as e:
            logger.error(self._format_log_entry("VISIT_ERROR", 
                f"Error during patient visit: {str(e)}"))
            print(self._format_console_message("ERROR", 
                f"Error during {patient.name}'s visit: {str(e)}"))
        
        finally:
            # Stage 7: Discharge
            self.discharge_patient(patient)
            
            visit_duration = (datetime.now() - visit_start_time).total_seconds() / 60
            logger.info(self._format_log_entry("VISIT_COMPLETE", 
                f"Patient visit completed in {visit_duration:.1f} minutes"))
            print(self._format_console_message("VISIT_END", 
                f"Visit completed for {patient.name} in {visit_duration:.1f} minutes"))

    def _simulate_triage(self, patient) -> None:
        """Simulate triage process with realistic vital signs."""
        print(self._format_console_message("STAGE", "Stage 1: Triage Assessment"))
        
        if not self.allocate_room("triage"):
            print(self._format_console_message("WAIT", "Waiting for triage room..."))
            time.sleep(2)
            self.allocate_room("triage")
        
        patient.update_status("Triage")
        
        # Generate realistic vitals
        temperature = round(random.uniform(36.1, 38.5), 1)
        systolic = random.randint(110, 140)
        diastolic = random.randint(70, 90)
        blood_pressure = f"{systolic}/{diastolic}"
        heart_rate = random.randint(60, 100)
        respiratory_rate = random.randint(12, 20)
        
        patient.record_vitals(temperature, blood_pressure, heart_rate, respiratory_rate)
        
        # Assess priority based on vitals
        if temperature > 38.0 or systolic > 140 or heart_rate > 100:
            patient.set_priority(2)
            patient.add_note("Elevated vital signs requiring prompt attention", "Triage Nurse")
        elif temperature < 36.5 or systolic < 100 or heart_rate < 60:
            patient.set_priority(2)
            patient.add_note("Concerning vital signs detected", "Triage Nurse")
        
        print(self._format_console_message("VITALS", 
            f"Vitals recorded - T: {temperature}°C, BP: {blood_pressure}, HR: {heart_rate}"))
        print(self._format_console_message("PRIORITY", 
            f"Priority Level: {patient.priority} ({patient.priority_description})"))
        
        self.release_room("triage")
        time.sleep(1)

    def _simulate_registration(self, patient) -> None:
        """Simulate patient registration process."""
        print(self._format_console_message("STAGE", "Stage 2: Patient Registration"))
        
        if not self.allocate_room("registration"):
            print(self._format_console_message("WAIT", "Waiting for registration desk..."))
            time.sleep(1)
            self.allocate_room("registration")
        
        patient.update_status("Registration")
        
        if not patient.has_medical_card:
            print(self._format_console_message("INFO", "Creating new medical card"))
            patient.has_medical_card = True
            patient.add_note("New medical card issued", "Registration Staff", "administrative")
        else:
            print(self._format_console_message("INFO", "Medical card verified"))
        
        if patient.insurance:
            print(self._format_console_message("INFO", f"Insurance verified: {patient.insurance}"))
            patient.add_note(f"Insurance verified: {patient.insurance}", "Registration Staff", "administrative")
        
        self.release_room("registration")
        time.sleep(1)

    def _simulate_consultation(self, patient):
        """Simulate doctor consultation with comprehensive logging."""
        print(self._format_console_message("STAGE", "Stage 3: Medical Consultation"))
        
        # Wait in waiting room
        if self.allocate_room("waiting"):
            patient.update_status("Waiting")
            wait_time = random.randint(1, 3) * patient.priority / 3
            print(self._format_console_message("WAIT", 
                f"Waiting for doctor (estimated: {wait_time:.1f} minutes)"))
            time.sleep(min(wait_time, 2))
        
        # Find available doctor
        doctor = self.find_available_doctor()
        if not doctor:
            print(self._format_console_message("WAIT", "No doctors available, extending wait time"))
            time.sleep(3)
            doctor = self.find_available_doctor()
            if not doctor:
                logger.error(self._format_log_entry("CONSULTATION_ERROR", 
                    "No doctors available after extended wait"))
                return None
        
        # Allocate consultation room
        if not self.allocate_room("consultation"):
            print(self._format_console_message("WAIT", "Waiting for consultation room..."))
            time.sleep(2)
            self.allocate_room("consultation")
        
        # Start consultation
        if doctor.start_consultation(patient):
            self.daily_statistics["consultations_completed"] += 1
            
            print(self._format_console_message("CONSULT", 
                f"Consultation with Dr. {doctor.name} ({doctor.specialty})"))
            
            # Simulate consultation time
            time.sleep(2)
            
            # Determine if tests are needed
            needs_tests = []
            if random.choice([True, False]):
                print(self._format_console_message("INFO", "Doctor recommends additional tests"))
                
                if random.choice([True, False]):
                    test_type = random.choice(["X-Ray", "CT Scan", "Ultrasound", "MRI"])
                    needs_tests.append(("Examination", test_type))
                    patient.medical_record["tests"].append(f"{test_type} ordered by Dr. {doctor.name}")
                    print(self._format_console_message("ORDER", f"{test_type} ordered"))
                
                if random.choice([True, False]) or not needs_tests:
                    lab_test = random.choice(["Blood Work", "Urinalysis", "Throat Culture", "COVID Test"])
                    needs_tests.append(("Lab Test", lab_test))
                    patient.medical_record["tests"].append(f"{lab_test} ordered by Dr. {doctor.name}")
                    print(self._format_console_message("ORDER", f"{lab_test} ordered"))
            else:
                # Direct diagnosis
                diagnosis = random.choice([
                    "Common Cold", "Allergic Rhinitis", "Minor Contusion", 
                    "Tension Headache", "Gastroenteritis"
                ])
                patient.add_diagnosis(diagnosis, doctor.name)
                
                prescription = f"Treatment for {diagnosis}"
                patient.medical_record["prescriptions"].append(prescription)
                
                print(self._format_console_message("DIAGNOSIS", 
                    f"Diagnosed: {diagnosis}"))
                print(self._format_console_message("PRESCRIPTION", 
                    f"Prescribed: {prescription}"))
            
            doctor.end_consultation()
        
        self.release_room("consultation")
        if "waiting" in [r for r in self.rooms.keys()]:
            self.release_room("waiting")
        
        return needs_tests

    def _simulate_tests(self, patient, needs_tests) -> None:
        """Simulate medical tests and examinations."""
        print(self._format_console_message("STAGE", "Stage 4: Medical Tests"))
        
        for test_category, test_name in needs_tests:
            if test_category == "Examination":
                self._simulate_examination(patient, test_name)
            elif test_category == "Lab Test":
                self._simulate_lab_test(patient, test_name)
            
            self.daily_statistics["tests_performed"] += 1

    def _simulate_examination(self, patient, test_name) -> None:
        """Simulate medical examination."""
        print(self._format_console_message("TEST", f"Performing {test_name}"))
        
        if not self.allocate_room("examination"):
            print(self._format_console_message("WAIT", "Waiting for examination room..."))
            time.sleep(1)
            self.allocate_room("examination")
        
        # Allocate device if available
        device_allocated = self.allocate_device(test_name.replace(" ", " ").split()[0] + " Machine")
        
        patient.update_status(f"Undergoing Examination")
        time.sleep(2)
        
        # Generate results
        findings = random.choice([
            "Normal findings",
            "Minor abnormalities noted",
            "Results consistent with symptoms",
            "Further monitoring recommended"
        ])
        
        report = f"{test_name} Report: {findings}"
        patient.medical_record["tests"].append(report)
        patient.add_note(f"{test_name} completed - {findings}", "Radiology Tech", "examination")
        
        print(self._format_console_message("RESULT", f"{test_name} complete - {findings}"))
        
        if device_allocated:
            self.release_device(test_name.replace(" ", " ").split()[0] + " Machine")
        self.release_room("examination")
        
        # Bill for examination
        bill_id = self.bill_patient(patient, random.randint(150, 400), f"{test_name} Examination")
        self.process_payment(bill_id, random.randint(150, 400))

    def _simulate_lab_test(self, patient, test_name) -> None:
        """Simulate laboratory test."""
        print(self._format_console_message("TEST", f"Processing {test_name}"))
        
        if not self.allocate_room("lab"):
            print(self._format_console_message("WAIT", "Waiting for lab facility..."))
            time.sleep(1)
            self.allocate_room("lab")
        
        patient.update_status(f"Undergoing Lab Test")
        time.sleep(2)
        
        # Generate lab results
        results = random.choice([
            "All values within normal range",
            "Slightly elevated markers",
            "Abnormal findings requiring follow-up",
            "Results consistent with clinical presentation"
        ])
        
        report = f"{test_name} Results: {results}"
        patient.medical_record["tests"].append(report)
        patient.add_note(f"{test_name} completed - {results}", "Lab Technician", "laboratory")
        
        print(self._format_console_message("RESULT", f"{test_name} complete - {results}"))
        
        self.release_room("lab")
        
        # Bill for lab test
        bill_id = self.bill_patient(patient, random.randint(75, 200), f"{test_name} Analysis")
        self.process_payment(bill_id, random.randint(75, 200))

    def _simulate_follow_up_consultation(self, patient) -> None:
        """Simulate follow-up consultation to review test results."""
        print(self._format_console_message("STAGE", "Stage 5: Follow-up Consultation"))
        
        # Find the same doctor if available
        doctor = self.find_available_doctor()
        if not doctor:
            print(self._format_console_message("INFO", "Original doctor unavailable, finding alternative"))
            time.sleep(1)
            doctor = self.find_available_doctor()
        
        if doctor and self.allocate_room("consultation"):
            if doctor.start_consultation(patient):
                print(self._format_console_message("REVIEW", 
                    f"Dr. {doctor.name} reviewing test results"))
                
                time.sleep(2)
                
                # Provide diagnosis based on results
                diagnosis = random.choice([
                    "Upper Respiratory Infection",
                    "Hypertension - Stage 1",
                    "Type 2 Diabetes (Early)",
                    "Migraine Disorder",
                    "Acute Gastroenteritis"
                ])
                
                patient.add_diagnosis(diagnosis, doctor.name)
                
                # Prescribe treatment
                prescription = f"Treatment plan for {diagnosis}"
                patient.medical_record["prescriptions"].append(prescription)
                
                print(self._format_console_message("DIAGNOSIS", f"Final diagnosis: {diagnosis}"))
                print(self._format_console_message("TREATMENT", f"Treatment prescribed"))
                
                doctor.end_consultation()
            
            self.release_room("consultation")

    def _simulate_pharmacy(self, patient) -> None:
        """Simulate pharmacy medication dispensing."""
        print(self._format_console_message("STAGE", "Stage 6: Pharmacy"))
        
        if not self.allocate_room("pharmacy"):
            print(self._format_console_message("WAIT", "Waiting at pharmacy..."))
            time.sleep(1)
            self.allocate_room("pharmacy")
        
        patient.update_status("Collecting Medicine from Pharmacy")
        
        total_cost = 0
        for i, prescription in enumerate(patient.medical_record["prescriptions"]):
            medication_cost = random.randint(25, 120)
            total_cost += medication_cost
            
            medication_details = {
                "name": prescription,
                "dosage": random.choice(["Once daily", "Twice daily", "Three times daily", "As needed"]),
                "duration": f"{random.randint(5, 14)} days",
                "cost": medication_cost,
                "special_instructions": random.choice([
                    "Take with food", "Take on empty stomach", 
                    "Avoid alcohol", "No special instructions"
                ])
            }
            
            print(self._format_console_message("DISPENSE", 
                f"Dispensing: {prescription} - ${medication_cost}"))
        
        patient.add_note("All prescribed medications dispensed", "Pharmacist", "pharmacy")
        self.daily_statistics["prescriptions_dispensed"] += 1
        
        # Bill for medications
        bill_id = self.bill_patient(patient, total_cost, "Pharmacy - Prescribed Medications")
        self.process_payment(bill_id, total_cost)
        
        print(self._format_console_message("PHARMACY", 
            f"Medications dispensed - Total: ${total_cost}"))
        
        self.release_room("pharmacy")

    def generate_hospital_statistics(self) -> Dict[str, Any]:
        """Generate comprehensive hospital statistics."""
        if not hasattr(self, 'operation_start_time'):
            self.operation_start_time = datetime.now()
        
        now = datetime.now()
        operation_duration = (now - self.operation_start_time).total_seconds() / 3600
        
        # Room utilization statistics
        room_stats = {}
        for room_type, info in self.rooms.items():
            utilization = (info["occupied"] / info["total"]) * 100 if info["total"] > 0 else 0
            room_stats[room_type] = {
                "total": info["total"],
                "available": info["available"],
                "occupied": info["occupied"],
                "utilization_rate": f"{utilization:.1f}%"
            }
        
        # Doctor utilization statistics
        doctor_stats = []
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
        
        # Financial statistics
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
        return (f"Hospital('{self.name}' - {len(self.doctors)} doctors, "
                f"{len(self.active_patients)} active patients)")

    def __repr__(self) -> str:
        """Detailed representation of the Hospital."""
        return (f"Hospital(id='{self.id}', name='{self.name}', "
                f"doctors={len(self.doctors)}, departments={len(self.departments)})")