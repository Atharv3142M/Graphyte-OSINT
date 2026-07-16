"""Dispatch investigation usecase - Main orchestration logic."""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from backend.core.domain.investigation import Investigation, Task
from backend.core.domain.playbook import Playbook, PlaybookDefinition
from backend.core.domain.errors import (
    DomainError,
    InvalidTargetError,
    ModuleNotFoundError,
    TaskQueueError,
)
from backend.core.ports.task_queue import ITaskQueue
from backend.core.ports.module_registry import IModuleRegistry
from backend.core.ports.logger import ILogger


class DispatchInvestigationUsecase:
    """
    Orchestrate a new investigation.
    
    This is the main entry point for investigation dispatch.
    Replaces logic that was scattered across:
    - backend/api.py (routes)
    - backend/tasks.py (task registration)
    - backend/playbook.py (routing logic)
    """
    
    def __init__(
        self,
        task_queue: ITaskQueue,
        module_registry: IModuleRegistry,
        playbook_db: Optional[Dict[str, PlaybookDefinition]] = None,
        logger: Optional[ILogger] = None,
    ):
        """
        Initialize usecase with dependencies.
        
        Args:
            task_queue: Task queue adapter (ITaskQueue)
            module_registry: Module registry (IModuleRegistry)
            playbook_db: Playbook definitions database
            logger: Logger (ILogger)
        """
        self.task_queue = task_queue
        self.module_registry = module_registry
        self.playbook_db = playbook_db or {}
        self.logger = logger
    
    async def execute(
        self,
        target: str,
        target_type: str,
        intensity: str = "standard",
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatch a new investigation.
        
        Args:
            target: Investigation target (domain, IP, email, etc.)
            target_type: Type of target
            intensity: Investigation intensity (light, standard, deep)
            tenant_id: Tenant ID for multi-tenancy
        
        Returns:
            Response containing investigation_id, playbook_id, modules, ws_url
        
        Raises:
            InvalidTargetError: If target is invalid
            ModuleNotFoundError: If requested modules not available
            TaskQueueError: If enqueueing fails
        """
        
        # Step 1: Validate target
        self._validate_target(target, target_type)
        self._log_info(f"Dispatching investigation", target=target, type=target_type, intensity=intensity)
        
        # Step 2: Get playbook for target type and intensity
        playbook_def = self._get_playbook_definition(target_type, intensity)
        modules_to_run = playbook_def.get_modules_for(target_type, intensity)
        
        if not modules_to_run:
            raise InvalidTargetError(f"No modules available for {target_type} at {intensity} intensity")
        
        self._log_info(f"Selected modules", modules=modules_to_run)
        
        # Step 3: Verify all modules are registered
        self._verify_modules_registered(modules_to_run)
        
        # Step 4: Create investigation domain object
        investigation = Investigation(
            playbook_id=playbook_def.playbook_id,
            target=target,
            target_type=target_type,
            intensity=intensity,
            tenant_id=tenant_id,
        )
        
        # Step 5: Create tasks and enqueue them
        await self._enqueue_tasks(investigation, modules_to_run, target)
        
        self._log_info(
            f"Investigation dispatched",
            investigation_id=investigation.investigation_id,
            task_count=len(investigation.tasks),
        )
        
        # Step 6: Return response
        return {
            "investigation_id": investigation.investigation_id,
            "playbook_id": investigation.playbook_id,
            "target": investigation.target,
            "modules": modules_to_run,
            "task_ids": [task.task_id for task in investigation.tasks],
            "ws_url": f"/ws/investigations/{investigation.investigation_id}",
            "status": "running",
        }
    
    def _validate_target(self, target: str, target_type: str) -> None:
        """Validate target format and type."""
        if not target or not target.strip():
            raise InvalidTargetError("Target cannot be empty")
        
        target = target.strip()
        
        # Basic validation by type
        validations = {
            "domain": self._validate_domain,
            "ip": self._validate_ip,
            "email": self._validate_email,
            "hash": self._validate_hash,
            "url": self._validate_url,
        }
        
        validator = validations.get(target_type)
        if validator and not validator(target):
            raise InvalidTargetError(f"Invalid {target_type}: {target}")
    
    @staticmethod
    def _validate_domain(domain: str) -> bool:
        """Validate domain format."""
        return "." in domain and len(domain) > 3 and len(domain) < 253
    
    @staticmethod
    def _validate_ip(ip: str) -> bool:
        """Validate IP format."""
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)
    
    @staticmethod
    def _validate_email(email: str) -> bool:
        """Validate email format."""
        return "@" in email and "." in email.split("@")[-1]
    
    @staticmethod
    def _validate_hash(hash_val: str) -> bool:
        """Validate hash format."""
        # Validate common hash formats
        hash_lengths = {32, 40, 64, 128}  # MD5, SHA1, SHA256, SHA512
        return len(hash_val) in hash_lengths and all(c in "0123456789abcdefABCDEF" for c in hash_val)
    
    @staticmethod
    def _validate_url(url: str) -> bool:
        """Validate URL format."""
        return url.startswith(("http://", "https://", "ftp://"))
    
    def _get_playbook_definition(self, target_type: str, intensity: str) -> PlaybookDefinition:
        """Get playbook definition for target type and intensity."""
        # In production, this would load from a database
        # For now, return default playbook
        
        playbook_key = f"{target_type}_{intensity}"
        
        if playbook_key not in self.playbook_db:
            # Return default playbook with all registered modules
            all_modules = [name for name, _ in self.module_registry.list_modules()]
            return PlaybookDefinition(
                playbook_id="default",
                name="Default Playbook",
                description="Default OSINT investigation",
                module_matrix={
                    (target_type, intensity): all_modules,
                },
            )
        
        return self.playbook_db[playbook_key]
    
    def _verify_modules_registered(self, modules: List[str]) -> None:
        """Verify all modules are registered."""
        for module_name in modules:
            if not self.module_registry.is_module_registered(module_name):
                raise ModuleNotFoundError(module_name)
    
    async def _enqueue_tasks(self, investigation: Investigation, modules: List[str], target: str) -> None:
        """Enqueue module tasks to the task queue."""
        for module_name in modules:
            # Create task for investigation
            task = investigation.add_task(
                module_name=module_name,
                payload={"target": target},
            )
            
            try:
                # Enqueue to task queue
                returned_task_id = await self.task_queue.enqueue_task(
                    module_name=module_name,
                    payload={"target": target, "investigation_id": investigation.investigation_id},
                    task_id=task.task_id,
                )
                
                self._log_info(f"Task enqueued", module=module_name, task_id=returned_task_id)
            
            except Exception as e:
                self._log_error(f"Failed to enqueue task: {e}", module=module_name)
                raise TaskQueueError(f"Failed to enqueue {module_name}: {str(e)}")
    
    def _log_info(self, message: str, **kwargs) -> None:
        """Log info message."""
        if self.logger:
            self.logger.info(message, **kwargs)
    
    def _log_error(self, message: str, **kwargs) -> None:
        """Log error message."""
        if self.logger:
            self.logger.error(message, **kwargs)
