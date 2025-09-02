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
from backend.models.Hospital import ThreadSafeHospital

def setup_logging():
    """Setup comprehensive logging system with thread safety."""
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
        log_dir / f'hospital_simulation_threaded_{timestamp}.log',
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
    """
    Generate random patients using configuration settings.
    Enhanced for threading with more diverse patient profiles.
    """
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
    logger.info(f"Generating {count} random patients for threaded simulation")
    
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
    
    logger.info(f"Generating doctors for threaded simulation: {specialties}")
    
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
    
    logger.info(f"Generated {len(doctors)} doctors for threaded hospital operations")
    return doctors

def setup_hospital_from_config() -> ThreadSafeHospital:
    """Setup thread-safe hospital using configuration settings."""
    config = get_config()
    logger = logging.getLogger(__name__)
    
    # Generate doctors
    doctors = generate_doctors_from_config()
    
    # Create thread-safe hospital
    hospital = ThreadSafeHospital("Twin Digital Medical Center", doctors)
    
    logger.info(f"Thread-safe hospital setup complete with {len(doctors)} doctors")
    return hospital

def run_simulation_with_mode(hospital: ThreadSafeHospital, patients: List[Patient], 
                           mode: str = "threaded", max_workers: int = None, verbose: bool = True) -> Dict[str, Any]:
    """
    Run simulation with choice between sequential or threaded mode.
    
    Args:
        hospital (ThreadSafeHospital): The hospital instance.
        patients (List[Patient]): List of patients to process.
        mode (str): Either "sequential" or "threaded".
        max_workers (int): Maximum concurrent workers (threaded mode only).
        verbose (bool): Whether to show detailed output.
        
    Returns:
        Dict[str, Any]: Simulation results.
    """
    if mode == "sequential":
        return run_sequential_simulation(hospital, patients, verbose)
    elif mode == "threaded":
        return run_threaded_simulation(hospital, patients, max_workers, verbose)
    else:
        raise ValueError("Mode must be either 'sequential' or 'threaded'")

def run_sequential_simulation(hospital: ThreadSafeHospital, patients: List[Patient], verbose: bool = True) -> Dict[str, Any]:
    """
    Run sequential simulation for comparison or backward compatibility.
    
    Args:
        hospital (ThreadSafeHospital): The hospital instance.
        patients (List[Patient]): List of patients to process.
        verbose (bool): Whether to show detailed output.
        
    Returns:
        Dict[str, Any]: Simulation results.
    """
    logger = logging.getLogger(__name__)
    simulation_start = datetime.now()
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'SEQUENTIAL HOSPITAL SIMULATION':^80}")
        print(f"{'(For Comparison/Backward Compatibility)':^80}")
        print("="*80)
        print(f"Processing {len(patients)} patients sequentially...")
    
    # Process patients one by one (original behavior)
    processed_patients = 0
    successful_visits = 0
    visit_summaries = []
    
    for i, patient in enumerate(sorted(patients, key=lambda p: p.priority)):
        try:
            if verbose:
                print(f"\nProcessing patient {i+1}/{len(patients)}: {patient.name}")
            
            # Use the backward-compatible method
            hospital.simulate_patient_visit(patient)
            successful_visits += 1
            
            # Create visit summary for consistency
            visit_summary = {
                "patient_id": patient.id,
                "patient_name": patient.name,
                "success": True,
                "mode": "sequential",
                "stages_completed": ["admission", "triage", "registration", "consultation", "discharge"]
            }
            visit_summaries.append(visit_summary)
            
        except Exception as e:
            logger.error(f"Error processing patient {patient.name}: {str(e)}")
            visit_summary = {
                "patient_id": patient.id,
                "patient_name": patient.name,
                "success": False,
                "errors": [str(e)],
                "mode": "sequential"
            }
            visit_summaries.append(visit_summary)
        
        processed_patients += 1
        
        # Brief pause between patients
        if i < len(patients) - 1:
            time.sleep(0.5)
    
    simulation_end = datetime.now()
    simulation_duration = simulation_end - simulation_start
    
    # Create results in same format as threaded simulation
    simulation_results = {
        "simulation_metadata": {
            "start_time": simulation_start,
            "end_time": simulation_end,
            "duration": simulation_duration,
            "duration_minutes": simulation_duration.total_seconds() / 60,
            "hospital_name": hospital.name,
            "threading_mode": "Sequential",
            "max_workers": 1
        },
        "patient_results": visit_summaries,
        "hospital_statistics": hospital.generate_hospital_statistics(),
        "concurrent_statistics": {
            "concurrent_metrics": {
                "total_patients": len(patients),
                "successful_visits": successful_visits,
                "failed_visits": len(patients) - successful_visits,
                "success_rate": f"{(successful_visits / len(patients) * 100):.1f}%",
                "average_visit_duration_minutes": simulation_duration.total_seconds() / 60 / len(patients)
            }
        }
    }
    
    if verbose:
        print(f"\nSequential simulation completed in {simulation_duration}")
        print(f"Processed: {processed_patients}/{len(patients)} patients")
        print(f"Success rate: {(successful_visits/processed_patients*100):.1f}%")
    
    return simulation_results

def run_threaded_simulation(hospital: ThreadSafeHospital, patients: List[Patient], 
                          max_workers: int = None, verbose: bool = True) -> Dict[str, Any]:
    """
    Run comprehensive threaded hospital simulation.
    
    Args:
        hospital (ThreadSafeHospital): The hospital instance.
        patients (List[Patient]): List of patients to process.
        max_workers (int): Maximum concurrent workers.
        verbose (bool): Whether to show detailed output.
        
    Returns:
        Dict[str, Any]: Comprehensive simulation results.
    """
    logger = logging.getLogger(__name__)
    simulation_start = datetime.now()
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'THREADED HOSPITAL SIMULATION STARTING':^80}")
        print(f"{'Simulation Time: ' + simulation_start.strftime('%Y-%m-%d %H:%M:%S'):^80}")
        print("="*80)
        print(f"Hospital: {hospital.name}")
        print(f"Doctors: {len(hospital.doctors)}")
        print(f"Patients: {len(patients)}")
        print(f"Departments: {len(hospital.departments)}")
        print(f"Max Concurrent Workers: {max_workers or hospital.max_concurrent_patients}")
        print("="*80 + "\n")
    
    logger.info(f"Starting threaded simulation with {len(patients)} patients and {max_workers or hospital.max_concurrent_patients} workers")
    
    # Run concurrent patient processing
    print(f"Processing {len(patients)} patients concurrently...")
    visit_summaries = hospital.process_patients_concurrently(patients, max_workers)
    
    simulation_end = datetime.now()
    simulation_duration = simulation_end - simulation_start
    
    # Generate comprehensive results
    concurrent_stats = hospital.generate_concurrent_statistics(visit_summaries)
    hospital_stats = hospital.generate_hospital_statistics()
    
    simulation_results = {
        "simulation_metadata": {
            "start_time": simulation_start,
            "end_time": simulation_end,
            "duration": simulation_duration,
            "duration_minutes": simulation_duration.total_seconds() / 60,
            "hospital_name": hospital.name,
            "threading_mode": "Enabled",
            "max_workers": max_workers or hospital.max_concurrent_patients
        },
        "patient_results": visit_summaries,
        "concurrent_statistics": concurrent_stats,
        "hospital_statistics": hospital_stats
    }
    
    if verbose:
        print("\n" + "="*80)
        print(f"{'THREADED SIMULATION COMPLETED':^80}")
        print(f"{'Duration: ' + str(simulation_duration):^80}")
        print("="*80)
        
        # Display concurrent processing results
        successful_visits = len([v for v in visit_summaries if v.get("success", False)])
        failed_visits = len(visit_summaries) - successful_visits
        success_rate = (successful_visits / len(visit_summaries) * 100) if visit_summaries else 0
        
        print(f"Patients Processed: {len(visit_summaries)}")
        print(f"Successful Visits: {successful_visits}")
        print(f"Failed Visits: {failed_visits}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Average Visit Duration: {concurrent_stats['concurrent_metrics']['average_visit_duration_minutes']:.1f} minutes")
        print(f"Total Revenue Generated: {concurrent_stats['concurrent_metrics']['total_revenue']}")
        print(f"Threads Used: {concurrent_stats['threading_performance']['threads_used']}")
        print("="*80 + "\n")
    
    logger.info(f"Threaded simulation completed - {len(visit_summaries)} patients processed in {simulation_duration}")
    
    return simulation_results

def display_threaded_statistics(hospital: ThreadSafeHospital, simulation_results: Dict[str, Any]) -> None:
    """
    Display comprehensive statistics for threaded simulation.
    
    Args:
        hospital (ThreadSafeHospital): The hospital instance.
        simulation_results (Dict[str, Any]): Results from the simulation.
    """
    print("\n" + "="*80)
    print(f"{'THREADED HOSPITAL OPERATIONS STATISTICS':^80}")
    print("="*80)
    
    concurrent_stats = simulation_results["concurrent_statistics"]
    hospital_stats = simulation_results["hospital_statistics"]
    
    # Simulation Overview
    print(f"\n{'SIMULATION OVERVIEW':^50}")
    print("-" * 50)
    meta = simulation_results["simulation_metadata"]
    print(f"Hospital Name: {meta['hospital_name']}")
    print(f"Threading Mode: {meta['threading_mode']}")
    print(f"Max Concurrent Workers: {meta['max_workers']}")
    print(f"Total Duration: {meta['duration_minutes']:.1f} minutes")
    print(f"Processing Speed: {len(simulation_results['patient_results']) / meta['duration_minutes']:.1f} patients/minute")
    
    # Concurrent Processing Metrics
    print(f"\n{'CONCURRENT PROCESSING METRICS':^50}")
    print("-" * 50)
    concurrent_metrics = concurrent_stats["concurrent_metrics"]
    for metric, value in concurrent_metrics.items():
        metric_name = metric.replace('_', ' ').title()
        print(f"{metric_name:>30}: {value}")
    
    # Threading Performance
    print(f"\n{'THREADING PERFORMANCE':^50}")
    print("-" * 50)
    threading_perf = concurrent_stats["threading_performance"]
    for metric, value in threading_perf.items():
        metric_name = metric.replace('_', ' ').title()
        print(f"{metric_name:>30}: {value}")
    
    # Stage Completion Rates
    print(f"\n{'STAGE COMPLETION RATES':^50}")
    print("-" * 50)
    stage_rates = concurrent_stats["stage_completion_rates"]
    for stage, rate in stage_rates.items():
        stage_name = stage.replace('_', ' ').title()
        print(f"{stage_name:>30}: {rate}")
    
    # Resource Utilization (Thread-Safe)
    print(f"\n{'RESOURCE UTILIZATION':^50}")
    print("-" * 50)
    room_stats = hospital_stats['resource_utilization']['rooms']
    for room_type, data in room_stats.items():
        print(f"{room_type.title():>15}: {data['occupied']}/{data['total']} ({data['utilization_rate']})")
    
    # Doctor Performance in Threaded Environment
    print(f"\n{'DOCTOR PERFORMANCE (THREADED)':^50}")
    print("-" * 50)
    print(f"{'Doctor':<20} {'Specialty':<15} {'Patients':<10} {'Utilization':<12} {'Status'}")
    print("-" * 70)
    doctor_stats = hospital_stats['resource_utilization']['doctors']
    for doc in doctor_stats:
        print(f"{doc['name']:<20} {doc['specialty']:<15} {doc['patients_seen']:<10} "
              f"{doc['utilization']:<12} {doc['status']}")
    
    # Financial Summary
    print(f"\n{'FINANCIAL SUMMARY':^50}")
    print("-" * 50)
    financial = hospital_stats['financial_summary']
    for metric, value in financial.items():
        metric_name = metric.replace('_', ' ').title()
        print(f"{metric_name:>30}: {value}")
    
    print("\n" + "="*80)

def display_patient_visit_outcomes(visit_summaries: List[Dict[str, Any]], detailed: bool = False) -> None:
    """
    Display patient visit outcomes from threaded processing.
    
    Args:
        visit_summaries (List[Dict[str, Any]]): List of visit outcome summaries.
        detailed (bool): Whether to show detailed information.
    """
    print("\n" + "="*80)
    print(f"{'PATIENT VISIT OUTCOMES (THREADED)':^80}")
    print("="*80)
    
    successful_visits = [v for v in visit_summaries if v.get("success", False)]
    failed_visits = [v for v in visit_summaries if not v.get("success", False)]
    
    print(f"\nSUMMARY:")
    print(f"Total Visits: {len(visit_summaries)}")
    print(f"Successful: {len(successful_visits)}")
    print(f"Failed: {len(failed_visits)}")
    
    if detailed and successful_visits:
        print(f"\n{'SUCCESSFUL VISITS DETAILS':^50}")
        print("-" * 60)
        print(f"{'Patient':<20} {'Thread':<15} {'Duration':<10} {'Stages':<15} {'Cost'}")
        print("-" * 60)
        
        for visit in successful_visits[:10]:  # Show first 10 for brevity
            stages_count = len(visit.get("stages_completed", []))
            duration = visit.get("duration_minutes", 0)
            cost = visit.get("total_cost", 0)
            thread_id = visit.get("thread_id", "Unknown")[:12]
            
            print(f"{visit['patient_name']:<20} {thread_id:<15} {duration:<10.1f} "
                  f"{stages_count:<15} ${cost}")
        
        if len(successful_visits) > 10:
            print(f"... and {len(successful_visits) - 10} more successful visits")
    
    if failed_visits:
        print(f"\n{'FAILED VISITS':^50}")
        print("-" * 50)
        for visit in failed_visits:
            errors = ', '.join(visit.get("errors", ["Unknown error"]))
            print(f"• {visit['patient_name']}: {errors}")
    
    # Threading efficiency analysis
    if visit_summaries:
        thread_usage = {}
        for visit in visit_summaries:
            thread_id = visit.get("thread_id", "Unknown")
            thread_usage[thread_id] = thread_usage.get(thread_id, 0) + 1
        
        print(f"\n{'THREAD UTILIZATION':^50}")
        print("-" * 50)
        for thread_id, count in sorted(thread_usage.items()):
            print(f"Thread {thread_id}: {count} patients")

def export_threaded_simulation_data(hospital: ThreadSafeHospital, simulation_results: Dict[str, Any], 
                                   patients: List[Patient], filename: str = None) -> str:
    """
    Export threaded simulation data to JSON file with original format compatibility.
    
    Args:
        hospital (ThreadSafeHospital): The hospital instance.
        simulation_results (Dict[str, Any]): Complete simulation results.
        patients (List[Patient]): List of patients for summaries.
        filename (str, optional): Output filename.
        
    Returns:
        str: Path to the exported file.
    """
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"threaded_hospital_simulation_{timestamp}.json"
    
    # Prepare export data in original format + threading enhancements
    export_data = {
        # Keep original format for backward compatibility
        "simulation_metadata": {
            "export_time": datetime.now().isoformat(),
            "hospital_name": hospital.name,
            "total_patients": len(patients),
            "total_doctors": len(hospital.doctors),
            "simulation_duration_hours": simulation_results["simulation_metadata"]["duration_minutes"] / 60,
            # Add threading metadata
            "threading_enabled": True,
            "max_concurrent_workers": simulation_results["simulation_metadata"]["max_workers"],
            "simulation_type": "threaded_concurrent"
        },
        
        # Keep original hospital statistics format
        "hospital_statistics": hospital.generate_hospital_statistics(),
        
        # Keep original patient summaries format
        "patient_summaries": [patient.get_medical_summary() for patient in patients],
        
        # Keep original doctor summaries format  
        "doctor_summaries": [doctor.get_daily_summary() for doctor in hospital.doctors],
        
        # Add new threading-specific data
        "threading_analysis": {
            "concurrent_processing_enabled": True,
            "max_workers_used": simulation_results["simulation_metadata"]["max_workers"],
            "resource_contention_logs": len([log for log in hospital.resource_logs if "timeout" in str(log)]),
            "thread_safety_events": len(hospital.resource_logs),
            "concurrent_statistics": simulation_results.get("concurrent_statistics", {}),
            "visit_summaries": simulation_results.get("patient_results", [])
        }
    }
    
    # Write to file
    export_path = Path("exports")
    export_path.mkdir(exist_ok=True)
    full_path = export_path / filename
    
    class DateTimeEncoder(json.JSONEncoder):
        """Custom JSON encoder for datetime objects."""
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, timedelta):
                return str(obj)
            return super().default(obj)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, cls=DateTimeEncoder)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Threaded simulation data exported to {full_path}")
    
    return str(full_path)

def compare_sequential_vs_threaded(patients: List[Patient], hospital: ThreadSafeHospital) -> None:
    """
    Compare performance between sequential and threaded processing.
    
    Args:
        patients (List[Patient]): Patients for comparison.
        hospital (ThreadSafeHospital): Hospital instance.
    """
    print("\n" + "="*80)
    print(f"{'SEQUENTIAL VS THREADED COMPARISON':^80}")
    print("="*80)
    
    # Estimate sequential processing time
    avg_visit_time = 3.5  # minutes per patient (estimated)
    sequential_estimate = len(patients) * avg_visit_time
    
    # Run threaded simulation with timing
    start_time = datetime.now()
    visit_summaries = hospital.process_patients_concurrently(patients, max_workers=4)
    threaded_duration = (datetime.now() - start_time).total_seconds() / 60
    
    # Calculate efficiency metrics
    speedup_factor = sequential_estimate / threaded_duration if threaded_duration > 0 else 0
    efficiency = speedup_factor / 4 * 100  # Assuming 4 workers
    
    print(f"Sequential Processing (Estimated): {sequential_estimate:.1f} minutes")
    print(f"Threaded Processing (Actual): {threaded_duration:.1f} minutes")
    print(f"Speedup Factor: {speedup_factor:.2f}x")
    print(f"Threading Efficiency: {efficiency:.1f}%")
    print(f"Time Saved: {sequential_estimate - threaded_duration:.1f} minutes")
    
    # Resource contention analysis
    successful_visits = len([v for v in visit_summaries if v.get("success", False)])
    print(f"\nResource Management:")
    print(f"Successful Visits: {successful_visits}/{len(patients)}")
    print(f"Resource Contention Events: {len([log for log in hospital.resource_logs if 'timeout' in str(log)])}")
    
    print("\n" + "="*80)

def main():
    """Enhanced main function for threaded hospital simulation."""
    print("="*80)
    print(f"{'TWIN DIGITAL HOSPITAL SYSTEM - THREADED EDITION':^80}")
    print(f"{'Medical Simulation Platform v2.1 (Thread-Safe)':^80}")
    print("="*80)
    
    # Setup logging with thread support
    logger = setup_logging()
    logger.info("Starting Twin Digital Hospital System - Threaded Edition")
    
    try:
        # Load configuration
        print("Loading system configuration...")
        config = load_config("default.yaml")
        logger.info("Configuration loaded successfully")
        print(f"✓ Configuration loaded: {config.patient_data.number_of_patients} patients, "
              f"{len(config.get_specialties())} specialties")
        
        # Setup thread-safe hospital
        print("Initializing thread-safe hospital system...")
        hospital = setup_hospital_from_config()
        print(f"✓ Thread-safe hospital '{hospital.name}' initialized with {len(hospital.doctors)} doctors")
        
        # Generate patients with staggered arrivals
        print("Generating patient population with realistic arrival patterns...")
        patients = generate_random_patients()
        print(f"✓ Generated {len(patients)} patients for concurrent processing")
        
        # Display threading configuration
        max_workers = min(len(hospital.doctors), 6)  # Limit based on doctors available
        print(f"✓ Threading configured: {max_workers} concurrent workers")
        
        # Run simulation (with mode selection)
        simulation_mode = "threaded"  # Can be changed to "sequential" for comparison
        print(f"\nStarting {simulation_mode} medical simulation...")
        simulation_results = run_simulation_with_mode(
            hospital, patients, mode=simulation_mode, max_workers=max_workers, verbose=True
        )
        
        # Display comprehensive results
        print("Generating comprehensive threaded reports...")
        display_threaded_statistics(hospital, simulation_results)
        display_patient_visit_outcomes(simulation_results["patient_results"], detailed=True)
        
        # Performance comparison
        print("Analyzing threading performance benefits...")
        # compare_sequential_vs_threaded(patients[:5], hospital)  # Use subset for comparison
        
        # Export data
        print("\nExporting threaded simulation data...")
        export_path = export_threaded_simulation_data(hospital, simulation_results, patients)
        print(f"✓ Threaded simulation data exported to: {export_path}")
        
        # Final summary with threading insights
        print("\n" + "="*80)
        print(f"{'THREADED SIMULATION COMPLETED SUCCESSFULLY':^80}")
        print(f"{'Enhanced Performance with Concurrent Processing':^80}")
        print(f"{'Check logs folder for detailed thread-safe logs':^80}")
        print(f"{'Check exports folder for threaded data export':^80}")
        print("="*80)
        
        # Display key threading benefits
        concurrent_metrics = simulation_results["concurrent_statistics"]["concurrent_metrics"]
        print(f"\n🚀 THREADING BENEFITS:")
        print(f"   • Processed {concurrent_metrics['total_patients']} patients concurrently")
        print(f"   • Average visit time: {concurrent_metrics['average_visit_duration_minutes']} minutes")
        print(f"   • Success rate: {concurrent_metrics['success_rate']}")
        print(f"   • Total revenue: {concurrent_metrics['total_revenue']}")
        print(f"   • Resource contention handled gracefully with timeouts")
        
        logger.info("Twin Digital Hospital System - Threaded Edition completed successfully")
        
    except FileNotFoundError as e:
        error_msg = f"Configuration file not found: {e}"
        print(f"❌ ERROR: {error_msg}")
        logger.error(error_msg)
        sys.exit(1)
        
    except Exception as e:
        error_msg = f"Threaded simulation error: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        logger.error(error_msg, exc_info=True)
        sys.exit(1)

def run_load_test(hospital: ThreadSafeHospital, num_patients: int = 20, max_workers: int = 8) -> None:
    """
    Run a load test to evaluate system performance under high concurrent load.
    
    Args:
        hospital (ThreadSafeHospital): Hospital instance.
        num_patients (int): Number of patients for load test.
        max_workers (int): Maximum concurrent workers.
    """
    print("\n" + "="*80)
    print(f"{'LOAD TEST - HIGH CONCURRENCY SIMULATION':^80}")
    print("="*80)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting load test with {num_patients} patients and {max_workers} workers")
    
    # Generate patients for load test
    load_test_patients = generate_random_patients(num_patients)
    
    # Run simulation with high concurrency
    print(f"Running high-load simulation with {num_patients} patients...")
    start_time = datetime.now()
    
    visit_summaries = hospital.process_patients_concurrently(load_test_patients, max_workers)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Analyze results
    successful = len([v for v in visit_summaries if v.get("success", False)])
    failed = len(visit_summaries) - successful
    
    print(f"\n{'LOAD TEST RESULTS':^50}")
    print("-" * 50)
    print(f"Patients Processed: {len(visit_summaries)}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Throughput: {len(visit_summaries) / duration:.2f} patients/second")
    print(f"Success Rate: {(successful / len(visit_summaries) * 100):.1f}%")
    print(f"Failed Visits: {failed}")
    
    # Resource contention analysis
    timeout_events = len([log for log in hospital.resource_logs if "timeout" in str(log).lower()])
    print(f"Resource Timeouts: {timeout_events}")
    print(f"System Stability: {'Good' if timeout_events < len(visit_summaries) * 0.1 else 'Needs Optimization'}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    # Enhanced command line arguments for different simulation modes
    if len(sys.argv) > 1:
        if sys.argv[1] == "--load-test":
            # Run load test mode
            logger = setup_logging()
            config = load_config("default.yaml")
            hospital = setup_hospital_from_config()
            
            num_patients = int(sys.argv[2]) if len(sys.argv) > 2 else 20
            max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
            
            run_load_test(hospital, num_patients, max_workers)
            
        elif sys.argv[1] == "--sequential":
            # Run in sequential mode for comparison
            logger = setup_logging()
            config = load_config("default.yaml")
            hospital = setup_hospital_from_config()
            patients = generate_random_patients()
            
            print("Running in SEQUENTIAL mode for comparison...")
            simulation_results = run_sequential_simulation(hospital, patients, verbose=True)
            display_threaded_statistics(hospital, simulation_results)
            export_path = export_threaded_simulation_data(hospital, simulation_results, patients)
            print(f"✓ Sequential simulation data exported to: {export_path}")
            
        elif sys.argv[1] == "--compare":
            # Run both modes for performance comparison
            logger = setup_logging()
            config = load_config("default.yaml")
            
            # Test with smaller patient set for comparison
            test_patients = generate_random_patients(8)
            
            print("\n" + "="*80)
            print(f"{'PERFORMANCE COMPARISON: SEQUENTIAL VS THREADED':^80}")
            print("="*80)
            
            # Sequential test
            hospital_seq = setup_hospital_from_config()
            print("\n1. Running Sequential Simulation...")
            seq_start = datetime.now()
            seq_results = run_sequential_simulation(hospital_seq, test_patients, verbose=False)
            seq_duration = (datetime.now() - seq_start).total_seconds()
            
            # Threaded test  
            hospital_thread = setup_hospital_from_config()
            print("\n2. Running Threaded Simulation...")
            thread_start = datetime.now()
            thread_results = run_threaded_simulation(hospital_thread, test_patients, max_workers=4, verbose=False)
            thread_duration = (datetime.now() - thread_start).total_seconds()
            
            # Comparison results
            speedup = seq_duration / thread_duration if thread_duration > 0 else 0
            print(f"\n{'COMPARISON RESULTS':^50}")
            print("-" * 50)
            print(f"Sequential Time: {seq_duration:.1f} seconds")
            print(f"Threaded Time: {thread_duration:.1f} seconds")
            print(f"Speedup Factor: {speedup:.2f}x")
            print(f"Efficiency: {speedup/4*100:.1f}% (with 4 workers)")
            print(f"Time Saved: {seq_duration - thread_duration:.1f} seconds")
            
        else:
            print("Usage:")
            print("  python main.py                    # Run threaded simulation (default)")
            print("  python main.py --sequential       # Run sequential simulation")  
            print("  python main.py --compare          # Compare both modes")
            print("  python main.py --load-test [patients] [workers]  # Load test")
    else:
        # Run standard threaded simulation (default)
        main()