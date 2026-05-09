"""
TrustLog - Patrón PROXY
=======================
Intercepta peticiones en tiempo real entre el cliente y el modelo de IA externo.
El cliente no sabe que existe un intermediario; el Proxy actúa de forma transparente.

Estructura GoF aplicada:
  - IModelIA      → Subject (interfaz común)
  - RealModelIA   → RealSubject (modelo de IA real)
  - Proxy         → Proxy (añade auditoría sin modificar el flujo)
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from src.models.decision_request import DecisionRequest, DecisionResponse

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Subject: interfaz común para el Proxy y el Real
# ──────────────────────────────────────────────
class IModelIA(ABC):
    """Interfaz que deben implementar tanto el modelo real como el Proxy."""

    @abstractmethod
    def request(self, input_data: str) -> str:
        """Envía datos al modelo y devuelve su decisión cruda."""
        pass


# ──────────────────────────────────────────────
# RealSubject: modelo de IA externo simulado
# ──────────────────────────────────────────────
class RealModelIA(IModelIA):
    """
    Simula el endpoint de un modelo de IA externo (ej. AWS SageMaker, OpenAI).
    En producción, este método realizaría la llamada HTTP real.
    """

    def __init__(self, model_name: str = "credit-scoring-v2"):
        self.model_name = model_name

    def request(self, input_data: str) -> str:
        """
        Simula la respuesta de un clasificador de crédito.
        Devuelve JSON con resultado, confianza y coeficientes técnicos.
        """
        import json, random

        data = json.loads(input_data)
        # Simulación determinista: ingreso > 3000 → aprobado
        income = data.get("monthly_income", 0)
        approved = income > 3000

        return json.dumps({
            "result": "APPROVED" if approved else "DENIED",
            "confidence": round(0.75 + random.uniform(0, 0.2), 3),
            "model_version": self.model_name,
            "raw_coefficients": {
                "monthly_income": 0.62,
                "credit_history_years": 0.21,
                "debt_ratio": -0.43,
                "age": 0.08,       # variable sensible
                "gender_encoded": 0.03,  # variable sensible
            },
        })


# ──────────────────────────────────────────────
# Proxy: interceptor transparente con auditoría
# ──────────────────────────────────────────────
class AIRequestProxy(IModelIA):
    """
    Proxy que intercepta cada petición al modelo de IA real.
    Responsabilidades:
      1. Registrar la petición con timestamp e ID único.
      2. Redirigir al modelo real sin alterar el payload.
      3. Capturar la respuesta y prepararla para la cadena de validación.
      4. Notificar si el servicio externo no responde (timeout simulado).

    Implementado como Singleton para garantizar una única instancia
    de intercepción por proceso.
    """

    _instance: Optional["AIRequestProxy"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, real_service: Optional[IModelIA] = None):
        # Evita reinicialización en llamadas repetidas al constructor
        if hasattr(self, "_initialized"):
            return
        self._real_service: IModelIA = real_service or RealModelIA()
        self._intercepted_count: int = 0
        self._timeout_limit_ms: int = 15_000  # 15 segundos máximo (RNF-001)
        self._initialized = True
        logger.info("AIRequestProxy inicializado (Singleton activo).")

    # ── Método principal del Proxy ──────────────────────────────────────────
    def request(self, input_data: str) -> str:
        """
        Intercepta la petición, la registra y la redirige al modelo real.
        Devuelve la respuesta cruda del modelo externo.
        """
        self._intercepted_count += 1
        logger.info(
            f"[PROXY] Petición #{self._intercepted_count} interceptada "
            f"| {datetime.utcnow().isoformat()}"
        )
        self._log_request(input_data)

        try:
            response_raw = self._real_service.request(input_data)
            logger.info("[PROXY] Respuesta recibida del modelo real.")
            return response_raw

        except TimeoutError:
            self._notify_service_disruption()
            raise

    def intercept_request(self, req: DecisionRequest) -> DecisionResponse:
        """
        Versión tipada del interceptor: acepta un DecisionRequest y
        devuelve un DecisionResponse estructurado listo para la cadena.
        """
        raw_json = self.request(json.dumps(req.input_data))
        raw_data = json.loads(raw_json)

        return DecisionResponse(
            request_id=req.request_id,
            result=raw_data["result"],
            confidence=raw_data["confidence"],
            model_version=raw_data["model_version"],
            raw_coefficients=raw_data.get("raw_coefficients", {}),
        )

    # ── Métodos privados de soporte ─────────────────────────────────────────
    def _log_request(self, input_data: str) -> None:
        """Registra un hash SHA-256 de la petición para trazabilidad."""
        digest = hashlib.sha256(input_data.encode()).hexdigest()
        logger.debug(f"[PROXY] SHA-256 del payload: {digest[:16]}...")

    def _notify_service_disruption(self) -> None:
        """Notifica al sistema cuando el servicio externo no responde (RFU-009)."""
        logger.error(
            "[PROXY] ⚠️  Servicio de IA externo no disponible. "
            "Notificación enviada al equipo de operaciones."
        )

    @staticmethod
    def get_instance() -> "AIRequestProxy":
        """Acceso seguro a la instancia Singleton."""
        if AIRequestProxy._instance is None:
            AIRequestProxy()
        return AIRequestProxy._instance

    @property
    def intercepted_count(self) -> int:
        return self._intercepted_count
