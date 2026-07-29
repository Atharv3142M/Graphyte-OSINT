"""Result and Artifact domain models."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class Artifact:
    """Represents a single extracted artifact."""
    
    artifact_type: str  # "domain", "ip", "email", "hash", "url", etc.
    value: str
    source_module: str
    confidence: float = 1.0  # 0.0-1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleResult:
    """Result from a single module execution."""
    
    module_name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    artifacts: List[Artifact] = field(default_factory=list)
    duration_ms: float = 0.0
    executed_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_artifact(
        self,
        artifact_type: str,
        value: str,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Artifact:
        """Add an extracted artifact."""
        artifact = Artifact(
            artifact_type=artifact_type,
            value=value,
            source_module=self.module_name,
            confidence=confidence,
            metadata=metadata or {},
        )
        self.artifacts.append(artifact)
        return artifact


@dataclass
class Result:
    """Complete result envelope for an investigation."""
    
    investigation_id: str
    playbook_id: str
    target: str
    modules: List[ModuleResult] = field(default_factory=list)
    artifacts: List[Artifact] = field(default_factory=list)
    execution_summary: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_module_result(self, module_result: ModuleResult) -> None:
        """Add a module result."""
        self.modules.append(module_result)
        # Collect artifacts
        self.artifacts.extend(module_result.artifacts)
    
    def get_modules_by_status(self, success: bool) -> List[ModuleResult]:
        """Get modules by execution status."""
        return [m for m in self.modules if m.success == success]
    
    def get_artifacts_by_type(self, artifact_type: str) -> List[Artifact]:
        """Get artifacts of a specific type."""
        return [a for a in self.artifacts if a.artifact_type == artifact_type]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        successful_modules = self.get_modules_by_status(True)
        failed_modules = self.get_modules_by_status(False)
        total_duration_ms = sum(m.duration_ms for m in self.modules)
        
        return {
            "total_modules": len(self.modules),
            "successful_modules": len(successful_modules),
            "failed_modules": len(failed_modules),
            "total_artifacts": len(self.artifacts),
            "total_duration_ms": total_duration_ms,
            "average_module_duration_ms": total_duration_ms / len(self.modules) if self.modules else 0,
        }
