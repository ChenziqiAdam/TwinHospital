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
    """Main configuration class."""
    patient_data: PatientConfig = Field(default_factory=PatientConfig)
    doctor_data: DoctorConfig = Field(default_factory=DoctorConfig)
    hospital_data: HospitalConfig = Field(default_factory=HospitalConfig)
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
        llm_config = LLMConfig(**yaml_data.get('llm', {}))
        
        return cls(
            patient_data=patient_config,
            doctor_data=doctor_config,
            hospital_data=hospital_config,
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