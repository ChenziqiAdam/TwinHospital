import yaml
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from pathlib import Path

class PatientConfig(BaseModel):
    """Configuration for patients."""
    number_of_patients: int = Field(default=10)
    patient_info: List[str] = Field(default_factory=list)
    priority_levels: Dict[int, str] = Field(default_factory=dict)
    patient_status: List[str] = Field(default_factory=list)
    medical_record: List[str] = Field(default_factory=list)

class DoctorConfig(BaseModel):
    """Configuration for doctors."""
    number_of_doctors: int = Field(default=6)
    doctor_info: List[str] = Field(default_factory=list)
    specialties: List[str] = Field(default_factory=list)
    doctor_status: List[str] = Field(default_factory=list)

class HospitalConfig(BaseModel):
    """Configuration for hospital."""
    hospital_info: List[str] = Field(default_factory=list)
    rooms: Dict[str, int] = Field(default_factory=dict)
    doctor_per_department: Dict[str, int] = Field(default_factory=dict)
    devices: List[str] = Field(default_factory=list)
    tests: Dict[str, List[str]] = Field(default_factory=dict)
    operation_hours: Dict[str, Any] = Field(default_factory=dict)
    timeout: float

class ContinuousExportConfig(BaseModel):
    """Configuration for continuous export functionality."""
    enabled: bool = Field(default=False, description="Enable/disable continuous export")
    export_interval: int = Field(default=30, description="Seconds between automatic exports")
    export_on_events: bool = Field(default=True, description="Export immediately on key events")
    export_directory: str = Field(default="exports", description="Directory to save export files")
    file_name_pattern: str = Field(
        default="continuous_hospital_simulation_{timestamp}.json", 
        description="File naming pattern"
    )
    max_history_entries: int = Field(default=100, description="Maximum historical entries to keep")
    trigger_events: List[str] = Field(
        default_factory=lambda: [
            "patient_admission", "patient_discharge", "billing_event", 
            "payment_processed", "consultation_complete", "test_complete"
        ],
        description="Events that trigger immediate export"
    )
    export_sections: Dict[str, bool] = Field(
        default_factory=lambda: {
            "patients_processed": True,
            "active_patients": True,
            "hospital_statistics": True,
            "resource_logs": True,
            "patient_logs": True,
            "billing_records": True,
            "doctor_statuses": True,
            "room_utilization": True,
            "daily_statistics": True
        },
        description="Data sections to include in export"
    )

class MonitoringConfig(BaseModel):
    """Configuration for system monitoring and alerts."""
    log_level: str = Field(default="INFO", description="Logging level")
    performance_tracking: bool = Field(default=True, description="Enable performance metrics")
    resource_monitoring: bool = Field(default=True, description="Enable resource monitoring")
    thread_safety_logging: bool = Field(default=True, description="Enable thread safety logging")
    alerts: Dict[str, int] = Field(
        default_factory=lambda: {
            "resource_contention_threshold": 80,
            "patient_wait_time_threshold": 60,
            "system_error_threshold": 5,
            "low_doctor_availability_threshold": 20
        },
        description="Alert thresholds"
    )

class LLMConfig(BaseModel):
    """Configuration for the language model."""
    model_name: str = Field(..., description="Name of the language model")
    api_key: str = Field(..., description="API key for the language model")
    base_url: str = Field(..., description="Base URL for the language model API")
    provider: str = Field(..., description="provider for the language model")
    max_tokens: int = Field(7800, description="Maximum number of tokens for the response")
    temperature: float = Field(0.1, description="Sampling temperature for the model")
    frequency_penalty: float = Field(0.0, description="Frequency penalty for the model")
    presence_penalty: float = Field(0.0, description="Presence penalty for the model")
    max_workers: int = Field(4, description="Maximum number of parallel workers")

class Config(BaseModel):
    """Main configuration class with continuous export support."""
    patient_data: PatientConfig = Field(default_factory=PatientConfig)
    doctor_data: DoctorConfig = Field(default_factory=DoctorConfig)
    hospital_data: HospitalConfig = Field(default_factory=HospitalConfig)
    continuous_export: ContinuousExportConfig = Field(default_factory=ContinuousExportConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    llm_config: LLMConfig = Field(default_factory=LLMConfig)

    @classmethod
    def load_from_yaml(cls, config_path: str) -> 'Config':
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as file:
            yaml_data = yaml.safe_load(file)
        
        # Convert YAML data to match our model structure
        patient_config = PatientConfig(**yaml_data.get('patient_data', {}))
        doctor_config = DoctorConfig(**yaml_data.get('doctor_data', {}))
        hospital_config = HospitalConfig(**yaml_data.get('hospital_data', {}))
        
        # NEW: Handle continuous export configuration
        continuous_export_config = ContinuousExportConfig(**yaml_data.get('continuous_export', {}))
        
        # NEW: Handle monitoring configuration
        monitoring_config = MonitoringConfig(**yaml_data.get('monitoring', {}))
        
        # Handle LLM configuration
        llm_config = LLMConfig(**yaml_data.get('llm', {}))
        
        return cls(
            patient_data=patient_config,
            doctor_data=doctor_config,
            hospital_data=hospital_config,
            continuous_export=continuous_export_config,
            monitoring=monitoring_config,
            llm_config=llm_config
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return self.dict()
    
    def get_patient_statuses(self) -> List[str]:
        """Get available patient statuses."""
        return self.patient_data.patient_status
    
    def get_doctor_statuses(self) -> List[str]:
        """Get available doctor statuses."""
        return self.doctor_data.doctor_status
    
    def get_specialties(self) -> List[str]:
        """Get available doctor specialties."""
        return self.doctor_data.specialties
    
    def get_priority_levels(self) -> Dict[int, str]:
        """Get priority levels mapping."""
        return self.patient_data.priority_levels
    
    def get_rooms_config(self) -> Dict[str, int]:
        """Get rooms configuration."""
        return self.hospital_data.rooms
    
    def get_devices(self) -> List[str]:
        """Get available medical devices."""
        return self.hospital_data.devices
    
    def get_tests(self) -> Dict[str, List[str]]:
        """Get available medical tests."""
        return self.hospital_data.tests
    
    # NEW: Continuous export configuration methods
    def get_continuous_export_config(self) -> ContinuousExportConfig:
        """Get continuous export configuration."""
        return self.continuous_export
    
    def is_continuous_export_enabled(self) -> bool:
        """Check if continuous export is enabled."""
        return self.continuous_export.enabled
    
    def get_export_interval(self) -> int:
        """Get export interval in seconds."""
        return self.continuous_export.export_interval
    
    def should_export_on_events(self) -> bool:
        """Check if export should be triggered on events."""
        return self.continuous_export.export_on_events
    
    def get_export_trigger_events(self) -> List[str]:
        """Get list of events that trigger export."""
        return self.continuous_export.trigger_events
    
    def get_export_sections(self) -> Dict[str, bool]:
        """Get export sections configuration."""
        return self.continuous_export.export_sections
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration."""
        return self.monitoring
    
    def should_enable_performance_tracking(self) -> bool:
        """Check if performance tracking is enabled."""
        return self.monitoring.performance_tracking
    
    def get_alert_thresholds(self) -> Dict[str, int]:
        """Get alert thresholds."""
        return self.monitoring.alerts

# Global configuration instance
_config: Optional[Config] = None

def load_config(config_path: str = "default.yaml") -> Config:
    """Load and return global configuration."""
    global _config
    _config = Config.load_from_yaml(config_path)
    return _config

def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

def get_export_config() -> ContinuousExportConfig:
    """Convenient method to get continuous export config."""
    config = get_config()
    return config.get_continuous_export_config()

def get_monitoring_config() -> MonitoringConfig:
    """Convenient method to get monitoring config."""
    config = get_config()
    return config.get_monitoring_config()