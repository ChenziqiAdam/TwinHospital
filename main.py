import sys
import json
import random
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Import our classes
from backend.config import load_config, get_config
from backend.models.Patient import Patient
from backend.models.Doctor import Doctor
from backend.models.Hospital import Hospital

def setup_logging():
    """Setup comprehensive logging system."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)8s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # File handler for detailed logs
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.FileHandler(
        log_dir / f'hospital_simulation_{timestamp}.log',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler for important messages
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Setup specific loggers
    logging.getLogger('Patient').setLevel(logging.INFO)
    logging.getLogger('Doctor').setLevel(logging.INFO)
    logging.getLogger('Hospital').setLevel(logging.INFO)
    
    return logging.getLogger(__name__)

def generate_random_patients(count: int = None) -> List[Patient]:
    """
    Generate random patients using configuration settings.
    
    Args:
        count (int, optional): Number of patients to generate. Uses config if not provided.
        
    Returns:
        List[Patient]: List of generated patients.
    """
    config = get_config()
    
    if count is None:
        count = config.patient_data.number_of_patients
    
    # Sample data for patient generation
    first_names = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
        "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
        "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
        "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna",
        "Steven", "Carol", "Paul", "Ruth", "Andrew", "Sharon", "Joshua", "Michelle"
    ]
    
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
        "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
    ]
    
    patients = []
    used_ids = set()
    
    logger = logging.getLogger(__name__)
    logger.info(f"Generating {count} random patients using configuration")
    
    for i in range(count):
        # Generate unique patient ID
        while True:
            patient_id = random.randint(1000, 9999)
            if patient_id not in used_ids:
                used_ids.add(patient_id)
                break
        
        # Generate patient details
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        name = f"{first_name} {last_name}"
        
        age = random.randint(18, 85)
        gender = random.choice(["Male", "Female", "Other"])
        
        # Generate contact information
        area_codes = ["602", "623", "480", "520", "928"]  # Arizona area codes
        phone = f"({random.choice(area_codes)}) {random.randint(200,999)}-{random.randint(1000,9999)}"
        
        # Assign insurance (70% have insurance)
        insurance = False if random.random() > 0.7 else True
        
        # Create patient
        patient = Patient(
            patient_id=patient_id,
            name=name,
            age=age,
            gender=gender,
            contact=phone,
            insurance=insurance
        )
        
        # Randomly assign medical card (80% already have one)
        if random.random() > 0.2:
            patient.has_medical_card = True
        
        # Set random arrival time within the last hour for realism
        arrival_offset = random.randint(-60, 0)  # 0 to 60 minutes ago
        patient.arrival_time = datetime.now() + timedelta(minutes=arrival_offset)
        
        patients.append(patient)
    
    logger.info(f"Successfully generated {len(patients)} patients")
    return patients

def generate_doctors_from_config() -> List[Doctor]:
    """
    Generate doctors based on configuration settings.
    
    Returns:
        List[Doctor]: List of generated doctors.
    """
    config = get_config()
    logger = logging.getLogger(__name__)
    
    # Doctor names by specialty for realism
    doctor_names = {
        "General": ["Alice Chen", "Robert Mitchell", "Sarah Johnson", "Michael Brown"],
        "Cardiologist": ["David Wang", "Emily Rodriguez", "James Wilson", "Lisa Thompson"],
        "Dermatologist": ["Maria Garcia", "Thomas Anderson", "Jennifer Lee", "Christopher Davis"],
        "Neurologist": ["Steven Kumar", "Rachel Green", "Andrew Martinez", "Diana Foster"],
        "Pediatrician": ["Emma Johnson", "Daniel Kim", "Olivia Smith", "Matthew Taylor"]
    }
    
    specialties = config.get_specialties()
    doctors_per_department = config.hospital_data.doctor_per_department
    
    doctors = []
    staff_id_counter = 1
    
    logger.info(f"Generating doctors for specialties: {specialties}")
    
    for specialty in specialties:
        # Get number of doctors needed for this specialty
        doctors_needed = doctors_per_department.get(specialty, 1)
        
        # Get available names for this specialty
        available_names = doctor_names.get(specialty, doctor_names["General"])
        
        for i in range(doctors_needed):
            # Select name (with fallback if we run out)
            if i < len(available_names):
                name = available_names[i]
            else:
                name = f"Dr. {chr(65 + i)} {specialty}"
            
            # Generate doctor attributes
            staff_id = f"D{staff_id_counter:03d}"
            experience = random.randint(2, 25)
            
            # Specialty-specific patient capacity
            if specialty in ["Emergency", "General"]:
                max_patients = random.randint(25, 35)
            elif specialty in ["Cardiologist", "Neurologist"]:
                max_patients = random.randint(12, 20)  # More complex cases
            else:
                max_patients = random.randint(15, 25)
            
            doctor = Doctor(
                name=name,
                specialty=specialty,
                staff_id=staff_id,
                years_experience=experience,
                max_patients_per_day=max_patients
            )
            
            # Set realistic shift hours
            shift_start = datetime.now().replace(hour=random.choice([7, 8, 9]), minute=0, second=0)
            shift_end = shift_start + timedelta(hours=random.choice([8, 9, 10]))
            doctor.set_shift(shift_start, shift_end)
            
            # Add breaks
            if random.choice([True, False]):
                break_start = shift_start + timedelta(hours=random.randint(3, 5))
                break_end = break_start + timedelta(minutes=random.choice([15, 30, 45]))
                doctor.add_break(break_start, break_end, "Break")
            
            doctors.append(doctor)
            staff_id_counter += 1
    
    logger.info(f"Successfully generated {len(doctors)} doctors")
    return doctors

def setup_hospital_from_config() -> Hospital:
    """
    Setup hospital using configuration settings.
    
    Returns:
        Hospital: Configured hospital instance.
    """
    config = get_config()
    logger = logging.getLogger(__name__)
    
    # Generate doctors
    doctors = generate_doctors_from_config()
    
    # Create hospital
    hospital = Hospital("Twin Digital Medical Center", doctors)
    
    logger.info(f"Hospital setup complete with {len(doctors)} doctors")
    return hospital

def run_simulation(hospital: Hospital, patients: List[Patient], verbose: bool = True) -> None:
    """
    Run comprehensive hospital simulation.
    
    Args:
        hospital (Hospital): The hospital instance.
        patients (List[Patient]): List of patients to process.
        verbose (bool): Whether to show detailed output.
    """
    logger = logging.getLogger(__name__)
    simulation_start = datetime.now()
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'HOSPITAL SIMULATION STARTING':^80}")
        print(f"{'Simulation Time: ' + simulation_start.strftime('%Y-%m-%d %H:%M:%S'):^80}")
        print("="*80)
        print(f"Hospital: {hospital.name}")
        print(f"Doctors: {len(hospital.doctors)}")
        print(f"Patients: {len(patients)}")
        print(f"Departments: {len(hospital.departments)}")
        print("="*80 + "\n")
    
    logger.info(f"Starting simulation with {len(patients)} patients")
    
    # Sort patients by priority (higher priority = lower number = processed first)
    patients.sort(key=lambda p: p.priority)
    
    # Process each patient
    processed_patients = 0
    successful_visits = 0
    
    for i, patient in enumerate(patients):
        try:
            if verbose:
                print(f"\n{'='*20} PATIENT {i+1}/{len(patients)} {'='*20}")
                print(f"Processing: {patient.name} (Priority: {patient.priority})")
            
            hospital.simulate_patient_visit(patient)
            successful_visits += 1
            processed_patients += 1
            
            # Brief pause between patients for realism
            if i < len(patients) - 1:
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error processing patient {patient.name}: {str(e)}")
            if verbose:
                print(f"Error processing patient {patient.name}: {str(e)}")
            processed_patients += 1
    
    simulation_end = datetime.now()
    simulation_duration = simulation_end - simulation_start
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'SIMULATION COMPLETED':^80}")
        print(f"{'Duration: ' + str(simulation_duration):^80}")
        print("="*80)
        print(f"Patients Processed: {processed_patients}/{len(patients)}")
        print(f"Successful Visits: {successful_visits}")
        print(f"Success Rate: {(successful_visits/processed_patients*100):.1f}%")
        print("="*80 + "\n")
    
    logger.info(f"Simulation completed - {processed_patients}/{len(patients)} patients processed in {simulation_duration}")

def display_hospital_statistics(hospital: Hospital) -> None:
    """
    Display comprehensive hospital statistics.
    
    Args:
        hospital (Hospital): The hospital instance.
    """
    print("\n" + "="*80)
    print(f"{'HOSPITAL OPERATIONS STATISTICS':^80}")
    print("="*80)
    
    stats = hospital.generate_hospital_statistics()
    
    # Hospital Overview
    print(f"\n{'HOSPITAL OVERVIEW':^50}")
    print("-" * 50)
    print(f"Hospital Name: {stats['hospital_info']['name']}")
    print(f"Operation Time: {stats['hospital_info']['operation_hours']:.1f} hours")
    print(f"Total Departments: {stats['hospital_info']['departments']}")
    print(f"Medical Staff: {stats['hospital_info']['total_doctors']} doctors")
    
    # Patient Statistics
    print(f"\n{'PATIENT STATISTICS':^50}")
    print("-" * 50)
    print(f"Total Patients Processed: {stats['patient_statistics']['total_processed']}")
    print(f"Currently Active: {stats['patient_statistics']['currently_active']}")
    print(f"Consultations Completed: {stats['patient_statistics']['consultations_completed']}")
    print(f"Medical Tests Performed: {stats['patient_statistics']['tests_performed']}")
    print(f"Prescriptions Dispensed: {stats['patient_statistics']['prescriptions_dispensed']}")
    
    # Financial Summary
    print(f"\n{'FINANCIAL SUMMARY':^50}")
    print("-" * 50)
    print(f"Total Revenue: {stats['financial_summary']['total_revenue']}")
    print(f"Total Expenses: {stats['financial_summary']['total_expenses']}")
    print(f"Net Profit: {stats['financial_summary']['profit']}")
    print(f"Bills Issued: {stats['financial_summary']['bills_issued']}")
    print(f"Payment Rate: {stats['financial_summary']['payment_rate']}")
    
    # Room Utilization
    print(f"\n{'ROOM UTILIZATION':^50}")
    print("-" * 50)
    for room_type, data in stats['resource_utilization']['rooms'].items():
        print(f"{room_type.title():>15}: {data['occupied']}/{data['total']} ({data['utilization_rate']})")
    
    # Doctor Performance
    print(f"\n{'DOCTOR UTILIZATION':^50}")
    print("-" * 50)
    print(f"{'Doctor':<20} {'Specialty':<15} {'Patients':<10} {'Utilization':<12} {'Status'}")
    print("-" * 70)
    for doc in stats['resource_utilization']['doctors']:
        print(f"{doc['name']:<20} {doc['specialty']:<15} {doc['patients_seen']:<10} "
              f"{doc['utilization']:<12} {doc['status']}")
    
    # Operational Metrics
    print(f"\n{'OPERATIONAL METRICS':^50}")
    print("-" * 50)
    for metric, value in stats['operational_metrics'].items():
        metric_name = metric.replace('_', ' ').title()
        print(f"{metric_name:>30}: {value}")
    
    print("\n" + "="*80)

def display_patient_records(patients: List[Patient], detailed: bool = False) -> None:
    """
    Display patient medical records with optional detailed view.
    
    Args:
        patients (List[Patient]): List of patients.
        detailed (bool): Whether to show detailed medical records.
    """
    print("\n" + "="*80)
    print(f"{'PATIENT MEDICAL RECORDS':^80}")
    print("="*80)
    
    for i, patient in enumerate(patients):
        print(f"\n{'='*15} RECORD {i+1}/{len(patients)} {'='*15}")
        
        # Basic patient information
        print(f"Patient: {patient.name} (ID: {patient.id})")
        print(f"Age: {patient.age}, Gender: {patient.gender}")
        print(f"Insurance: {patient.insurance or 'None'}")
        print(f"Status: {patient.status}")
        
        # Visit timing
        if patient.discharge_time:
            duration = patient.discharge_time - patient.arrival_time
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            print(f"Hospital Stay: {int(hours)}h {int(minutes)}m")
        else:
            print("Hospital Stay: In progress")
        
        if detailed:
            # Detailed medical information
            medical_record = patient.medical_record
            
            # Diagnoses
            if medical_record.get("diagnoses"):
                print("\nDiagnoses:")
                for diagnosis in medical_record["diagnoses"]:
                    print(f"  • {diagnosis['diagnosis']} (Dr. {diagnosis['doctor']})")
            
            # Tests performed
            if medical_record.get("tests"):
                print(f"\nTests Performed ({len(medical_record['tests'])}):")
                for test in medical_record["tests"][-3:]:  # Show last 3 tests
                    print(f"  • {test}")
                if len(medical_record['tests']) > 3:
                    print(f"  ... and {len(medical_record['tests']) - 3} more")
            
            # Prescriptions
            if medical_record.get("prescriptions"):
                print(f"\nPrescriptions ({len(medical_record['prescriptions'])}):")
                for prescription in medical_record["prescriptions"]:
                    print(f"  • {prescription}")
            
            # Latest vitals
            if medical_record.get("vitals"):
                latest_vitals = medical_record["vitals"][-1]
                print(f"\nLatest Vitals:")
                print(f"  Temperature: {latest_vitals['temperature']}°C")
                print(f"  Blood Pressure: {latest_vitals['blood_pressure']}")
                print(f"  Heart Rate: {latest_vitals['heart_rate']} bpm")
                print(f"  Respiratory Rate: {latest_vitals['respiratory_rate']}/min")
        
        else:
            # Summary information
            diagnoses_count = len(patient.medical_record.get("diagnoses", []))
            tests_count = len(patient.medical_record.get("tests", []))
            prescriptions_count = len(patient.medical_record.get("prescriptions", []))
            
            print(f"Medical Summary: {diagnoses_count} diagnoses, {tests_count} tests, {prescriptions_count} prescriptions")

def export_simulation_data(hospital: Hospital, patients: List[Patient], filename: str = None) -> str:
    """
    Export simulation data to JSON file.
    
    Args:
        hospital (Hospital): The hospital instance.
        patients (List[Patient]): List of patients.
        filename (str, optional): Output filename.
        
    Returns:
        str: Path to the exported file.
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"hospital_simulation_export_{timestamp}.json"
    
    # Prepare export data
    export_data = {
        "simulation_metadata": {
            "export_time": datetime.now().isoformat(),
            "hospital_name": hospital.name,
            "total_patients": len(patients),
            "total_doctors": len(hospital.doctors),
            "simulation_duration_hours": (datetime.now() - hospital.operation_start_time).total_seconds() / 3600
        },
        "hospital_statistics": hospital.generate_hospital_statistics(),
        "patient_summaries": [patient.get_medical_summary() for patient in patients],
        "doctor_summaries": [doctor.get_daily_summary() for doctor in hospital.doctors]
    }
    
    # Write to file
    export_path = Path("exports")
    export_path.mkdir(exist_ok=True)
    full_path = export_path / filename
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, default=str)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Simulation data exported to {full_path}")
    
    return str(full_path)

def main():
    """Main function to run the hospital simulation."""
    print("="*80)
    print(f"{'TWIN DIGITAL HOSPITAL SYSTEM':^80}")
    print(f"{'Medical Simulation Platform v2.0':^80}")
    print("="*80)
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Twin Digital Hospital System")
    
    try:
        # Load configuration
        print("Loading system configuration...")
        config = load_config("default.yaml")
        logger.info(f"Configuration loaded successfully")
        print(f"✓ Configuration loaded: {config.patient_data.number_of_patients} patients, "
              f"{len(config.get_specialties())} specialties")
        
        # Setup hospital
        print("Initializing hospital system...")
        hospital = setup_hospital_from_config()
        print(f"✓ Hospital '{hospital.name}' initialized with {len(hospital.doctors)} doctors")
        
        # Generate patients
        print("Generating patient population...")
        patients = generate_random_patients()
        print(f"✓ Generated {len(patients)} patients for simulation")
        
        # Run simulation
        print("\nStarting medical simulation...")
        run_simulation(hospital, patients, verbose=True)
        
        # Display results
        print("Generating comprehensive reports...")
        display_hospital_statistics(hospital)
        display_patient_records(patients, detailed=False)
        
        # Export data
        print("\nExporting simulation data...")
        export_path = export_simulation_data(hospital, patients)
        print(f"✓ Simulation data exported to: {export_path}")
        
        # Final summary
        print("\n" + "="*80)
        print(f"{'SIMULATION COMPLETED SUCCESSFULLY':^80}")
        print(f"{'Check logs folder for detailed logs':^80}")
        print(f"{'Check exports folder for data export':^80}")
        print("="*80)
        
        logger.info("Twin Digital Hospital System simulation completed successfully")
        
    except FileNotFoundError as e:
        error_msg = f"Configuration file not found: {e}"
        print(f"❌ ERROR: {error_msg}")
        logger.error(error_msg)
        sys.exit(1)
        
    except Exception as e:
        error_msg = f"Simulation error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        logger.error(error_msg, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()