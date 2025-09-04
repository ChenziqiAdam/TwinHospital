import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class HospitalExportSystem:
    """
    Handles continuous export and monitoring for hospital simulation data.
    Separated from core hospital operations for better maintainability.
    """
    
    def __init__(self, hospital_name: str, hospital_id: str, 
                 continuous_export_enabled: bool = True, export_interval: int = 30, 
                 export_on_events: bool = True):
        """
        Initialize the export system.
        
        Args:
            hospital_name (str): Name of the hospital
            hospital_id (str): Unique hospital identifier
            continuous_export (bool): Enable continuous JSON export
            export_interval (int): Seconds between automatic exports
            export_on_events (bool): Export immediately on key events
        """
        self.hospital_name = hospital_name
        self.hospital_id = hospital_id
        
        # Export configuration
        self.continuous_export_enabled = continuous_export_enabled
        self.export_interval = export_interval
        self.export_on_events = export_on_events
        
        # Export state
        self.export_file_path = None
        self.last_export_time = datetime.now()
        self.export_thread = None
        self.export_shutdown_event = threading.Event()
        
        # Export locks
        self.export_lock = threading.RLock()
        
        # Simulation state tracking
        self.simulation_completed = False
        self.simulation_start_time = None
        self.simulation_end_time = None
        self.final_export_completed = False
        
        # Initialize export system if enabled
        if self.continuous_export_enabled:
            self._initialize_continuous_export()
    
    def _initialize_continuous_export(self) -> None:
        """Initialize the continuous export system."""
        # Create exports directory
        export_dir = Path("exports")
        export_dir.mkdir(exist_ok=True)
        
        # Set up continuous export file path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.export_file_path = export_dir / f"continuous_hospital_simulation_{timestamp}.json"
        
        # Create initial export file with metadata
        initial_data = {
            "simulation_metadata": {
                "hospital_name": self.hospital_name,
                "hospital_id": self.hospital_id,
                "simulation_start": datetime.now().isoformat(),
                "simulation_end": None,
                "simulation_completed": False,
                "continuous_export_enabled": True,
                "export_interval_seconds": self.export_interval,
                "last_update": datetime.now().isoformat(),
                "final_export_completed": False,
                "updates_count": 0
            },
            "real_time_data": {
                "patients_processed": [],
                "active_patients": {},
                "hospital_statistics": {},
                "resource_logs": [],
                "patient_logs": [],
                "billing_records": [],
                "financial_summary": {},
                "doctor_statuses": [],
                "room_utilization": {}
            }
        }
        
        with open(self.export_file_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=2, default=self._json_serializer)
        
        # Start background export thread if interval-based export is enabled
        if self.export_interval > 0:
            self.export_thread = threading.Thread(
                target=self._continuous_export_worker,
                name="ContinuousExport",
                daemon=True
            )
            self.export_thread.start()
        
        logger.info(f"[EXPORT_SYSTEM] Continuous export initialized - File: {self.export_file_path}")
    
    def _continuous_export_worker(self) -> None:
        """Background worker thread for continuous export."""
        logger.info("[EXPORT_SYSTEM] Continuous export worker started")
        
        while not self.export_shutdown_event.wait(self.export_interval):
            try:
                # Don't export if simulation is completed (final export should handle this)
                if not self.simulation_completed:
                    # This will be called by the hospital to provide current state
                    pass  # Hospital will call update_export_data() periodically
                else:
                    logger.info("[EXPORT_SYSTEM] Simulation completed, stopping scheduled exports")
                    break
            except Exception as e:
                logger.error(f"[EXPORT_SYSTEM] Error in continuous export worker: {str(e)}")
        
        logger.info("[EXPORT_SYSTEM] Continuous export worker stopped")
    
    def update_export_data(self, current_state: Dict[str, Any], trigger_event: str = "scheduled_update", 
                          final_export: bool = False) -> None:
        """
        Update the continuous export JSON file with current state.
        Called by the hospital to provide current data.
        
        Args:
            current_state (Dict[str, Any]): Current hospital state data
            trigger_event (str): Event that triggered this export
            final_export (bool): Whether this is the final export
        """
        if not self.continuous_export_enabled or not self.export_file_path:
            return
        
        with self.export_lock:
            try:
                # Read existing file
                try:
                    with open(self.export_file_path, 'r', encoding='utf-8') as f:
                        export_data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    export_data = {"simulation_metadata": {}, "real_time_data": {}}
                
                # Update metadata
                updates_count = export_data["simulation_metadata"].get("updates_count", 0) + 1
                export_data["simulation_metadata"].update({
                    "last_update": datetime.now().isoformat(),
                    "update_trigger": trigger_event,
                    "updates_count": updates_count
                })
                
                # Handle final export
                if final_export:
                    export_data["simulation_metadata"].update({
                        "simulation_end": datetime.now().isoformat(),
                        "simulation_completed": True,
                        "final_export_completed": True,
                        "final_export_trigger": trigger_event,
                        "final_export_timestamp": datetime.now().isoformat()
                    })
                    self.simulation_completed = True
                    self.simulation_end_time = datetime.now()
                
                # Update real-time data with provided state
                export_data["real_time_data"] = current_state
                
                # Write updated data atomically
                temp_file_path = self.export_file_path.with_suffix('.tmp')
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, default=self._json_serializer)
                
                # Atomic rename
                temp_file_path.replace(self.export_file_path)
                
                self.last_export_time = datetime.now()
                
                if final_export:
                    self.final_export_completed = True
                    logger.info("[EXPORT_SYSTEM] FINAL export completed - All simulation data captured")
                else:
                    logger.debug(f"[EXPORT_SYSTEM] Export updated - Trigger: {trigger_event}")
                
            except Exception as e:
                logger.error(f"[EXPORT_SYSTEM] Failed to update continuous export: {str(e)}")
    
    def trigger_export_update(self, event_type: str, current_state_callback) -> None:
        """
        Trigger an export update if event-based export is enabled.
        
        Args:
            event_type (str): Type of event triggering the export
            current_state_callback: Function that returns current hospital state
        """
        if self.export_on_events and self.continuous_export_enabled and not self.simulation_completed:
            # Get current state from hospital
            current_state = current_state_callback()
            # Update export in separate thread to avoid blocking
            export_thread = threading.Thread(
                target=self.update_export_data,
                args=(current_state, event_type),
                daemon=True
            )
            export_thread.start()
            logger.info(f"[EXPORT_SYSTEM] Event-based export triggered - Event: {event_type}")
    
    def force_export_update(self, current_state: Dict[str, Any]) -> bool:
        """Force an immediate export update."""
        if not self.continuous_export_enabled:
            logger.warning("[EXPORT_SYSTEM] Continuous export is disabled")
            return False
        
        try:
            self.update_export_data(current_state, "manual_force")
            logger.info("[EXPORT_SYSTEM] Manual export update completed")
            return True
        except Exception as e:
            logger.error(f"[EXPORT_SYSTEM] Failed to force export update: {str(e)}")
            return False
    
    def force_final_export(self, current_state: Dict[str, Any]) -> bool:
        """
        Force a final export to ensure all data is captured.
        
        Args:
            current_state (Dict[str, Any]): Final hospital state
            
        Returns:
            bool: True if final export was successful
        """
        if not self.continuous_export_enabled:
            logger.warning("[EXPORT_SYSTEM] Continuous export is disabled - cannot perform final export")
            return False
        
        try:
            # Mark simulation as completed if not already
            if not self.simulation_completed:
                self.simulation_completed = True
                self.simulation_end_time = datetime.now()
            
            # Perform final export
            self.update_export_data(current_state, "manual_final_export", final_export=True)
            
            logger.info("[EXPORT_SYSTEM] Manual final export completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"[EXPORT_SYSTEM] Failed to perform manual final export: {str(e)}")
            return False
    
    def finalize_export(self, current_state: Dict[str, Any]) -> None:
        """
        Finalize the export system when simulation completes.
        
        Args:
            current_state (Dict[str, Any]): Final hospital state
        """
        logger.info("[EXPORT_SYSTEM] Starting export finalization")
        
        # Stop the background export thread
        self.export_shutdown_event.set()
        if self.export_thread and self.export_thread.is_alive():
            self.export_thread.join(timeout=5)
            logger.info("[EXPORT_SYSTEM] Background export thread stopped")
        
        # Ensure final export happens
        if not self.final_export_completed:
            logger.warning("[EXPORT_SYSTEM] Final export not completed - forcing final export")
            self.force_final_export(current_state)
        
        logger.info("[EXPORT_SYSTEM] Export finalization completed")
    
    def get_export_status(self) -> Dict[str, Any]:
        """Get current status of continuous export system."""
        return {
            "enabled": self.continuous_export_enabled,
            "export_file_path": str(self.export_file_path) if self.export_file_path else None,
            "export_interval": self.export_interval,
            "export_on_events": self.export_on_events,
            "last_export_time": self.last_export_time.isoformat(),
            "export_thread_active": hasattr(self, 'export_thread') and self.export_thread is not None and self.export_thread.is_alive(),
            "file_exists": self.export_file_path.exists() if self.export_file_path else False,
            "file_size_bytes": self.export_file_path.stat().st_size if self.export_file_path and self.export_file_path.exists() else 0,
            "simulation_completed": self.simulation_completed,
            "final_export_completed": self.final_export_completed
        }
    
    def get_export_completion_status(self) -> Dict[str, Any]:
        """
        Check if the export file contains the final complete data.
        
        Returns:
            Dict[str, Any]: Export completion status information
        """
        if not self.export_file_path or not self.export_file_path.exists():
            return {"file_exists": False, "completion_status": "no_file"}
        
        try:
            with open(self.export_file_path, 'r', encoding='utf-8') as f:
                export_data = json.load(f)
            
            metadata = export_data.get("simulation_metadata", {})
            
            return {
                "file_exists": True,
                "simulation_completed": metadata.get("simulation_completed", False),
                "final_export_completed": metadata.get("final_export_completed", False),
                "simulation_start": metadata.get("simulation_start"),
                "simulation_end": metadata.get("simulation_end"),
                "last_update": metadata.get("last_update"),
                "updates_count": metadata.get("updates_count", 0),
                "final_export_trigger": metadata.get("final_export_trigger"),
                "completion_status": self._determine_completion_status(metadata)
            }
        
        except Exception as e:
            logger.error(f"[EXPORT_SYSTEM] Error checking completion status: {str(e)}")
            return {"file_exists": True, "completion_status": "error", "error": str(e)}
    
    def _determine_completion_status(self, metadata: Dict[str, Any]) -> str:
        """Determine the completion status of the export."""
        if metadata.get("final_export_completed", False):
            return "complete_final_export"
        elif metadata.get("simulation_completed", False):
            return "simulation_complete_no_final_export"
        else:
            return "simulation_in_progress"
    
    def verify_export_integrity(self) -> Dict[str, Any]:
        """
        Verify that the final export contains all expected data.
        
        Returns:
            Dict[str, Any]: Integrity check results
        """
        completion_status = self.get_export_completion_status()
        
        if not completion_status["file_exists"]:
            return {"integrity_status": "no_file", "issues": ["Export file does not exist"]}
        
        try:
            with open(self.export_file_path, 'r', encoding='utf-8') as f:
                export_data = json.load(f)
            
            issues = []
            warnings = []
            
            # Check simulation completion
            if not completion_status["simulation_completed"]:
                issues.append("Simulation not marked as completed")
            
            if not completion_status["final_export_completed"]:
                issues.append("Final export not performed - data may be incomplete")
            
            # Check data sections
            real_time_data = export_data.get("real_time_data", {})
            
            expected_sections = ["patients_processed", "hospital_statistics", "financial_summary"]
            for section in expected_sections:
                if section not in real_time_data:
                    issues.append(f"Missing data section: {section}")
            
            # Check for final summary
            if "final_simulation_summary" not in real_time_data:
                warnings.append("Final simulation summary missing (may indicate incomplete export)")
            
            # Determine overall integrity
            if issues:
                integrity_status = "incomplete"
            elif warnings:
                integrity_status = "complete_with_warnings"
            else:
                integrity_status = "complete_and_verified"
            
            return {
                "integrity_status": integrity_status,
                "completion_status": completion_status["completion_status"],
                "issues": issues,
                "warnings": warnings,
                "file_size_bytes": self.export_file_path.stat().st_size,
                "verification_time": datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                "integrity_status": "verification_error",
                "error": str(e),
                "verification_time": datetime.now().isoformat()
            }
    
    def enable_continuous_export(self, export_interval: int = 30, export_on_events: bool = True) -> bool:
        """Enable continuous export if it was disabled."""
        if self.continuous_export_enabled:
            logger.warning("[EXPORT_SYSTEM] Continuous export already enabled")
            return False
        
        self.continuous_export_enabled = True
        self.export_interval = export_interval
        self.export_on_events = export_on_events
        
        try:
            self._initialize_continuous_export()
            logger.info(f"[EXPORT_SYSTEM] Continuous export enabled - Interval: {export_interval}s, Events: {export_on_events}")
            return True
        except Exception as e:
            logger.error(f"[EXPORT_SYSTEM] Failed to enable continuous export: {str(e)}")
            self.continuous_export_enabled = False
            return False
    
    def disable_continuous_export(self) -> bool:
        """Disable continuous export system."""
        if not self.continuous_export_enabled:
            return False
        
        with self.export_lock:
            self.continuous_export_enabled = False
            self.export_shutdown_event.set()
            
            if self.export_thread and self.export_thread.is_alive():
                self.export_thread.join(timeout=5)
            
            logger.info("[EXPORT_SYSTEM] Continuous export disabled")
            return True
    
    def cleanup(self) -> None:
        """Clean up export system resources."""
        if self.continuous_export_enabled:
            logger.info("[EXPORT_SYSTEM] Starting cleanup")
            
            # Stop background thread
            self.export_shutdown_event.set()
            if self.export_thread and self.export_thread.is_alive():
                self.export_thread.join(timeout=10)
            
            logger.info("[EXPORT_SYSTEM] Cleanup completed")
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, timedelta):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    def __del__(self):
        """Cleanup when export system is destroyed."""
        try:
            self.cleanup()
        except:
            pass