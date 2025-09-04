import sys
import json
import random
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import our classes
from backend.config import load_config, get_config
from backend.models.Patient import Patient
from backend.models.Doctor import Doctor
from backend.models.Hospital import Hospital

def setup_logging():
    """Setup comprehensive logging system with thread safety and continuous export."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create formatters with thread information
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)8s] [%(threadName)-15s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] [%(threadName)-10s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # File handler for detailed logs
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = logging.FileHandler(
        log_dir / f'hospital_simulation_continuous_{timestamp}.log',
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
    
    # Setup specific loggers with thread-safe settings
    logging.getLogger('Patient').setLevel(logging.INFO)
    logging.getLogger('Doctor').setLevel(logging.INFO)
    logging.getLogger('Hospital').setLevel(logging.INFO)
    
    return logging.getLogger(__name__)

def generate_random_patients(count: int = None) -> List[Patient]:
    """Generate random patients using configuration settings."""
    config = get_config()
    
    if count is None:
        count = config.patient_data.number_of_patients
    
    # Enhanced patient data for more realistic simulation
    first_names = [
        "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
        "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
        "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
        "Matthew", "Betty", "Anthony", "Helen", "Mark", "Sandra", "Donald", "Donna",
        "Steven", "Carol", "Paul", "Ruth", "Andrew", "Sharon", "Joshua", "Michelle",
        "Emma", "Olivia", "Ava", "Isabella", "Sophia", "Charlotte", "Mia", "Amelia"
    ]
    
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
        "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores"
    ]
    
    # More diverse symptoms for better testing
    possible_symptoms = [
        "Fever", "Cough", "Shortness of breath", "Headache", "Nausea", "Dizziness",
        "Fatigue", "Chest pain", "Abdominal pain", "Back pain", "Sore throat",
        "Runny nose", "Muscle aches", "Joint pain", "Rash", "Insomnia", "Anxiety",
        "Heart palpitations", "Blurred vision", "Numbness", "Swelling", "Constipation"
    ]
    
    possible_conditions = [
        "Diabetes", "Hypertension", "Asthma", "Allergies", "Heart Disease",
        "Arthritis", "Depression", "Anxiety", "Chronic Pain", "High Cholesterol",
        "Thyroid Disease", "Kidney Disease", "COPD", "Osteoporosis"
    ]
    
    patients = []
    used_ids = set()
    
    logger = logging.getLogger(__name__)
    logger.info(f"Generating {count} random patients for continuous export simulation")
    
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
        area_codes = ["602", "623", "480", "520", "928"]
        phone = f"({random.choice(area_codes)}) {random.randint(200,999)}-{random.randint(1000,9999)}"
        
        # Insurance assignment (75% have insurance for more realistic simulation)
        insurance = True if random.random() < 0.75 else False
        
        # Generate symptoms (1-4 random symptoms, weighted towards fewer symptoms)
        num_symptoms = random.choices([1, 2, 3, 4], weights=[40, 35, 20, 5])[0]
        symptoms = random.sample(possible_symptoms, k=num_symptoms)
        
        # Generate medical history (0-3 random conditions)
        num_conditions = random.choices([0, 1, 2, 3], weights=[30, 40, 25, 5])[0]
        medical_history = random.sample(possible_conditions, k=num_conditions)
        
        # Create patient
        patient = Patient(
            patient_id=patient_id,
            name=name,
            age=age,
            gender=gender,
            contact=phone,
            insurance=insurance,
            symptoms=symptoms,
            medical_history=medical_history
        )
        
        # Medical card assignment (85% already have one)
        if random.random() < 0.85:
            patient.has_medical_card = True
        
        # Stagger arrival times for more realistic concurrent simulation
        arrival_offset = random.randint(-120, 30)  # Arrivals spread over 2.5 hours
        patient.arrival_time = datetime.now() + timedelta(minutes=arrival_offset)
        
        patients.append(patient)
    
    logger.info(f"Successfully generated {len(patients)} patients with varied arrival times")
    return patients

def generate_doctors_from_config() -> List[Doctor]:
    """Generate doctors based on configuration with enhanced threading support."""
    config = get_config()
    logger = logging.getLogger(__name__)
    
    # Enhanced doctor names for more realistic simulation
    doctor_names = {
        "General": [
            "Alice Chen", "Robert Mitchell", "Sarah Johnson", "Michael Brown",
            "Laura Wilson", "David Thompson", "Maria Rodriguez", "Kevin Lee"
        ],
        "Cardiologist": [
            "David Wang", "Emily Rodriguez", "James Wilson", "Lisa Thompson",
            "Steven Kim", "Rachel Martinez", "Andrew Foster", "Diana Chen"
        ],
        "Dermatologist": [
            "Maria Garcia", "Thomas Anderson", "Jennifer Lee", "Christopher Davis",
            "Samantha Taylor", "Jonathan Miller", "Rebecca White", "Marcus Johnson"
        ],
        "Neurologist": [
            "Steven Kumar", "Rachel Green", "Andrew Martinez", "Diana Foster",
            "Alexander Petrov", "Catherine Moore", "Benjamin Clark", "Victoria Adams"
        ],
        "Pediatrician": [
            "Emma Johnson", "Daniel Kim", "Olivia Smith", "Matthew Taylor",
            "Isabella Garcia", "Lucas Brown", "Charlotte Wilson", "Ethan Davis"
        ]
    }
    
    specialties = config.get_specialties()
    doctors_per_department = config.hospital_data.doctor_per_department
    
    doctors = []
    staff_id_counter = 1
    
    logger.info(f"Generating doctors for continuous export simulation: {specialties}")
    
    for specialty in specialties:
        doctors_needed = doctors_per_department.get(specialty, 1)
        available_names = doctor_names.get(specialty, doctor_names["General"])
        
        for i in range(doctors_needed):
            # Select name with fallback
            if i < len(available_names):
                name = available_names[i]
            else:
                name = f"Dr. {chr(65 + i)} {specialty}"
            
            # Generate doctor attributes
            staff_id = f"D{staff_id_counter:03d}"
            experience = random.randint(3, 25)
            age = random.randint(28, 65)
            gender = random.choice(["Male", "Female", "Other"])
            
            # Adjust capacity for concurrent operations
            if specialty in ["Emergency", "General"]:
                max_patients = random.randint(20, 30)  # Slightly reduced for threading
            elif specialty in ["Cardiologist", "Neurologist"]:
                max_patients = random.randint(10, 18)
            else:
                max_patients = random.randint(12, 22)
            
            doctor = Doctor(
                name=name,
                specialty=specialty,
                age=age,
                gender=gender,
                staff_id=staff_id,
                years_experience=experience,
                max_patients_per_day=max_patients
            )
            
            # Set realistic shift hours with some overlap for better coverage
            start_hour = config.hospital_data.operation_hours["start"]
            shift_start = datetime.now().replace(hour=start_hour, minute=0, second=0)
            shift_duration = config.hospital_data.operation_hours["duration"]
            shift_end = shift_start + timedelta(hours=shift_duration)
            doctor.set_shift(shift_start, shift_end)
            
            # Add breaks (50% chance)
            if random.choice([True, False]):
                break_start = shift_start + timedelta(hours=random.randint(3, 5))
                break_end = break_start + timedelta(minutes=random.choice([15, 30, 45]))
                doctor.add_break(break_start, break_end, "Break")
            
            doctors.append(doctor)
            staff_id_counter += 1
    
    logger.info(f"Generated {len(doctors)} doctors for continuous export hospital operations")
    return doctors

def setup_hospital() -> Hospital:
    """Setup hospital with continuous export enabled."""
    config = get_config()
    logger = logging.getLogger(__name__)
    
    # Generate doctors
    doctors = generate_doctors_from_config()
    
    # Create thread-safe hospital with continuous export
    hospital = Hospital(
        name="Twin Digital Medical Center",
        doctors=doctors,
        continuous_export_enabled=config.export.enabled,
        export_interval=config.export.export_interval,
        export_on_events=config.export.export_on_events
    )
    
    logger.info(f"Hospital with continuous export setup complete - Export enabled: {config.export.enabled}")
    return hospital

def run_simulation(hospital: Hospital, patients: List[Patient]) -> Dict[str, Any]:
    """Run simulation with live continuous export demonstration."""
    logger = logging.getLogger(__name__)
    simulation_start = datetime.now()
    
    print("\n" + "="*80)
    print(f"{'SIMULATION WITH CONTINUOUS EXPORT':^80}")
    print(f"{'Real-time JSON updates during processing':^80}")
    print("="*80)
    
    export_status = hospital.get_continuous_export_status()
    if export_status['enabled']:
        print(f"🔴 LIVE EXPORT: {export_status['export_file_path']}")
        print(f"📈 Updates every {export_status['export_interval']}s + on events")
    else:
        print("⚠️  Continuous export is disabled")
    
    print(f"\n🏥 Processing {len(patients)} patients with real-time export...")
    
    # Run concurrent patient processing
    visit_summaries = hospital.process_patients_concurrently(patients, max_workers=4)
    
    simulation_end = datetime.now()
    simulation_duration = simulation_end - simulation_start
    
    # Show final export status
    final_export_status = hospital.get_continuous_export_status()
    print(f"\n📊 Final Export Status:")
    print(f"  • File Size: {final_export_status['file_size_bytes']} bytes")
    print(f"  • Last Update: {final_export_status['last_export_time']}")
    
    # Generate final statistics
    concurrent_stats = hospital.generate_concurrent_statistics(visit_summaries)
    hospital_stats = hospital.generate_hospital_statistics()
    
    simulation_results = {
        "simulation_metadata": {
            "start_time": simulation_start,
            "end_time": simulation_end,
            "duration": simulation_duration,
            "duration_minutes": simulation_duration.total_seconds() / 60,
            "hospital_name": hospital.name,
            "threading_mode": "Enabled with Continuous Export",
            "continuous_export": {
                "enabled": final_export_status['enabled'],
                "export_file": str(final_export_status['export_file_path']),
                "file_size_bytes": final_export_status['file_size_bytes']
            }
        },
        "patient_results": visit_summaries,
        "concurrent_statistics": concurrent_stats,
        "hospital_statistics": hospital_stats
    }
    
    logger.info(f"Simulation with continuous export completed - {len(visit_summaries)} patients processed")
    return simulation_results

def monitor_export(export_file_path: Path) -> None:
    """Monitor and display export file changes in real-time."""
    if not export_file_path or not export_file_path.exists():
        print("Export file not found for monitoring")
        return
    
    config = get_config()
    duration_seconds = config.monitoring.duration_seconds if hasattr(config.monitoring, 'duration_seconds') else 120
    print(f"\n📊 Monitoring export file changes for {duration_seconds} seconds...")
    print(f"File: {export_file_path}")
    print("-" * 60)
    
    last_size = 0
    last_modified = 0
    start_time = time.time()
    
    while time.time() - start_time < duration_seconds:
        try:
            current_size = export_file_path.stat().st_size
            current_modified = export_file_path.stat().st_mtime
            
            if current_size != last_size or current_modified != last_modified:
                timestamp = datetime.now().strftime("%H:%M:%S")
                size_change = current_size - last_size
                
                print(f"[{timestamp}] File updated - Size: {current_size} bytes ({size_change:+d})")
                
                last_size = current_size
                last_modified = current_modified
            
            time.sleep(2)  # Check every 2 seconds
            
        except FileNotFoundError:
            print("Export file was deleted or moved")
            break
        except Exception as e:
            print(f"Error monitoring file: {e}")
            break
    
    print("-" * 60)
    print(f"Monitoring completed")

def main():
    """Enhanced main function with continuous export demonstration."""
    print("="*80)
    print(f"{'TWIN DIGITAL HOSPITAL SYSTEM - CONTINUOUS EXPORT EDITION':^80}")
    print(f"{'Real-time JSON Export During Simulation':^80}")
    print("="*80)
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting Twin Digital Hospital System - Continuous Export Edition")
    
    try:
        # Load configuration with continuous export settings
        print("Loading system configuration with continuous export settings...")
        config = load_config("default.yaml")
        
        logger.info("Configuration loaded successfully with continuous export")
        print(f"✅ Configuration loaded: {config.patient_data.number_of_patients} patients, "
              f"{len(config.get_specialties())} specialties")
        print(f"📤 Continuous Export: {'Enabled' if config.export.enabled else 'Disabled'}")
        
        # Setup hospital with continuous export
        print("Initializing hospital system with continuous export...")
        hospital = setup_hospital()
        print(f"✅ Hospital '{hospital.name}' initialized with {len(hospital.doctors)} doctors")
        
        # Generate patients
        print("Generating patient population...")
        patients = generate_random_patients(config.patient_data.number_of_patients)
        print(f"✅ Generated {len(patients)} patients")
        
        # Get export file path for monitoring
        export_status = hospital.get_continuous_export_status()
        export_file_path = Path(export_status['export_file_path']) if export_status['export_file_path'] else None
        
        # Start file monitoring in background thread
        if export_file_path:
            monitor_thread = threading.Thread(
                target=monitor_export,
                args=(export_file_path, config.monitoring.duration_seconds),
                daemon=True
            )
            monitor_thread.start()
        
        # Run simulation with continuous export
        print(f"\n🚀 Starting simulation with live continuous export...")
        simulation_results = run_simulation(hospital, patients)
        
        # Display results
        print("\n" + "="*80)
        print(f"{'SIMULATION RESULTS WITH CONTINUOUS EXPORT':^80}")
        print("="*80)
        
        # Show export file information
        final_export_status = hospital.get_continuous_export_status()
        if final_export_status['file_exists']:
            print(f"📄 Continuous Export File: {final_export_status['export_file_path']}")
            print(f"📊 Final File Size: {final_export_status['file_size_bytes']} bytes")
            print(f"🕐 Last Updated: {final_export_status['last_export_time']}")
            
            # Show a sample of the export data
            try:
                with open(export_file_path, 'r') as f:
                    export_data = json.load(f)
                    
                print(f"\n📋 Export Data Sample:")
                print(f"  • Active Patients: {len(export_data.get('real_time_data', {}).get('active_patients', {}))}")
                print(f"  • Processed Patients: {len(export_data.get('real_time_data', {}).get('patients_processed', []))}")
                print(f"  • Resource Logs: {len(export_data.get('real_time_data', {}).get('resource_logs', []))}")
                print(f"  • Billing Records: {len(export_data.get('real_time_data', {}).get('billing_records', []))}")
                
            except Exception as e:
                print(f"Could not read export file sample: {e}")
        
        # Traditional simulation statistics
        concurrent_metrics = simulation_results["concurrent_statistics"]["concurrent_metrics"]
        print(f"\n🏥 SIMULATION SUMMARY:")
        print(f"   • Processed {concurrent_metrics['total_patients']} patients with live export")
        print(f"   • Success rate: {concurrent_metrics['success_rate']}")
        print(f"   • Total revenue: {concurrent_metrics['total_revenue']}")
        print(f"   • Average visit time: {concurrent_metrics['average_visit_duration_minutes']} minutes")
        
        # Final cleanup
        print("\n🧹 Cleaning up...")
        hospital.cleanup_continuous_export()
        
        print("\n" + "="*80)
        print(f"{'CONTINUOUS EXPORT DEMONSTRATION COMPLETED':^80}")
        print(f"{'Check the export file for real-time data capture':^80}")
        print("="*80)
        
        if export_file_path and export_file_path.exists():
            print(f"\n📁 Your continuous export file: {export_file_path}")
        
        logger.info("Twin Digital Hospital System - Continuous Export Edition completed successfully")
        
    except FileNotFoundError as e:
        error_msg = f"Configuration file not found: {e}"
        print(f"❌ ERROR: {error_msg}")
        print("💡 Make sure 'enhanced_default.yaml' config file exists")
        logger.error(error_msg)
        sys.exit(1)
        
    except Exception as e:
        error_msg = f"Continuous export simulation error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        logger.error(error_msg, exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Run standard simulation with continuous export (default)
    main()