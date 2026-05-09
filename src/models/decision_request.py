"""
TrustLog - Core Data Models
Modelos de datos compartidos por todos los patrones del framework.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
import uuid


@dataclass
class DecisionRequest:
    """Representa una petición enviada a un modelo de IA externo."""
    input_data: Dict[str, Any]
    model_version: str
    sector: str  # "financial", "hr", "health"
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "model_version": self.model_version,
            "sector": self.sector,
            "input_data": self.input_data,
        }


@dataclass
class DecisionResponse:
    """Representa la respuesta del modelo de IA externo."""
    request_id: str
    result: Any
    confidence: float
    model_version: str
    raw_coefficients: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "result": self.result,
            "confidence": self.confidence,
            "model_version": self.model_version,
            "raw_coefficients": self.raw_coefficients,
        }


@dataclass
class AuditReport:
    """
    Ticket de Decisión inmutable generado por TrustLog.
    Representa la evidencia legal de cada auditoría realizada.
    """
    request_id: str
    timestamp: datetime
    model_version: str
    sector: str
    original_result: Any
    confidence: float
    bias_detected: bool
    bias_metrics: Dict[str, float]
    nlp_explanation: str
    integrity_hash: str
    validation_passed: bool
    validation_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "model_version": self.model_version,
            "sector": self.sector,
            "original_result": self.original_result,
            "confidence": self.confidence,
            "bias_detected": self.bias_detected,
            "bias_metrics": self.bias_metrics,
            "nlp_explanation": self.nlp_explanation,
            "integrity_hash": self.integrity_hash,
            "validation_passed": self.validation_passed,
            "validation_details": self.validation_details,
        }
