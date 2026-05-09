"""
TrustLog - Patrón CHAIN OF RESPONSIBILITY
==========================================
Motor de validación secuencial que aplica filtros de ética y privacidad
a cada respuesta interceptada por el Proxy.

Cada handler en la cadena puede:
  - Procesar la solicitud y pasarla al siguiente handler.
  - Detener la cadena si detecta una violación crítica.

Cadena implementada:
  PayloadValidator → SensitiveVariableFilter → BiasAnalyzer → NLPExplainer → HashSigner

Estructura GoF aplicada:
  - AuditHandler        → Handler (interfaz abstracta)
  - Handlers concretos  → ConcreteHandlers
"""

import hashlib
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from src.models.decision_request import AuditReport, DecisionRequest, DecisionResponse

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────
# Context: objeto mutable que recorre toda la cadena
# ──────────────────────────────────────────────────────
class AuditContext:
    """
    Contenedor de estado que fluye por todos los handlers.
    Cada handler puede leer y enriquecer este contexto.
    """

    def __init__(self, request: DecisionRequest, response: DecisionResponse):
        self.request = request
        self.response = response
        self.bias_metrics: Dict[str, float] = {}
        self.nlp_explanation: str = ""
        self.integrity_hash: str = ""
        self.validation_passed: bool = True
        self.validation_details: Dict[str, Any] = {}
        self.blocked: bool = False
        self.block_reason: str = ""


# ──────────────────────────────────────────────────────
# Handler abstracto
# ──────────────────────────────────────────────────────
class AuditHandler(ABC):
    """Clase base de la cadena. Cada handler conoce al siguiente."""

    def __init__(self):
        self._next_handler: Optional["AuditHandler"] = None

    def set_next(self, handler: "AuditHandler") -> "AuditHandler":
        """Encadena el siguiente handler y lo devuelve para fluent API."""
        self._next_handler = handler
        return handler

    def handle(self, context: AuditContext) -> AuditContext:
        """
        Ejecuta la lógica propia y delega al siguiente si existe.
        Los handlers concretos llaman a super().handle(context) al final.
        """
        if self._next_handler and not context.blocked:
            return self._next_handler.handle(context)
        return context

    @abstractmethod
    def process(self, context: AuditContext) -> None:
        """Lógica específica del handler concreto."""
        pass


# ──────────────────────────────────────────────────────
# Handler 1: Validación de formato del payload (RFU-005)
# ──────────────────────────────────────────────────────
class PayloadValidatorHandler(AuditHandler):
    """Verifica que el payload cumpla el contrato de la API antes de continuar."""

    REQUIRED_FIELDS = {"monthly_income", "credit_history_years", "debt_ratio"}

    def process(self, context: AuditContext) -> None:
        missing = self.REQUIRED_FIELDS - set(context.request.input_data.keys())
        if missing:
            context.blocked = True
            context.block_reason = f"Campos requeridos ausentes: {missing}"
            context.validation_passed = False
            logger.warning(f"[PayloadValidator] Bloqueado: {context.block_reason}")
        else:
            context.validation_details["payload_valid"] = True
            logger.info("[PayloadValidator] ✓ Payload válido.")

    def handle(self, context: AuditContext) -> AuditContext:
        self.process(context)
        return super().handle(context)


# ──────────────────────────────────────────────────────
# Handler 2: Filtro de variables sensibles (RFU-007)
# ──────────────────────────────────────────────────────
class SensitiveVariableFilter(AuditHandler):
    """
    Detecta si el modelo utilizó variables sensibles (género, edad, raza)
    con coeficientes significativos que podrían indicar discriminación.
    """

    SENSITIVE_VARS = {"age", "gender_encoded", "race_encoded", "zip_code"}
    SIGNIFICANCE_THRESHOLD = 0.05  # coeficiente > 5% → alerta

    def process(self, context: AuditContext) -> None:
        coefficients = context.response.raw_coefficients
        flagged = {
            var: coef
            for var, coef in coefficients.items()
            if var in self.SENSITIVE_VARS and abs(coef) > self.SIGNIFICANCE_THRESHOLD
        }

        if flagged:
            context.validation_details["sensitive_vars_detected"] = flagged
            logger.warning(
                f"[SensitiveVarFilter] ⚠️  Variables sensibles con peso significativo: {flagged}"
            )
        else:
            context.validation_details["sensitive_vars_detected"] = {}
            logger.info("[SensitiveVarFilter] ✓ Sin variables sensibles significativas.")

    def handle(self, context: AuditContext) -> AuditContext:
        self.process(context)
        return super().handle(context)


# ──────────────────────────────────────────────────────
# Handler 3: Analizador de Equidad / Sesgo (RFU-002)
# ──────────────────────────────────────────────────────
class BiasAnalyzerHandler(AuditHandler):
    """
    Calcula métricas matemáticas de equidad algorítmica:
      - Disparate Impact Ratio (DIR): proporción de resultados favorables entre grupos.
      - Si DIR < 0.8 (regla 4/5 de la EEOC) → sesgo detectado.

    En producción, se compararían resultados reales por grupo demográfico.
    Aquí simulamos el cálculo con los coeficientes disponibles.
    """

    DIR_THRESHOLD = 0.80  # Estándar EEOC / GDPR

    def process(self, context: AuditContext) -> None:
        coefficients = context.response.raw_coefficients
        sensitive_impact = sum(
            abs(v)
            for k, v in coefficients.items()
            if k in SensitiveVariableFilter.SENSITIVE_VARS
        )
        total_impact = sum(abs(v) for v in coefficients.values()) or 1

        # DIR simulado: ratio del impacto no-sensible vs. total
        dir_score = round(1 - (sensitive_impact / total_impact), 4)
        bias_detected = dir_score < self.DIR_THRESHOLD

        context.bias_metrics = {
            "disparate_impact_ratio": dir_score,
            "sensitive_variable_weight": round(sensitive_impact / total_impact, 4),
            "bias_threshold": self.DIR_THRESHOLD,
        }

        if bias_detected:
            context.validation_details["bias_detected"] = True
            context.validation_details["bias_level"] = "HIGH" if dir_score < 0.6 else "MEDIUM"
            logger.warning(
                f"[BiasAnalyzer] 🚨 Sesgo detectado. DIR={dir_score} < {self.DIR_THRESHOLD}"
            )
        else:
            context.validation_details["bias_detected"] = False
            logger.info(f"[BiasAnalyzer] ✓ Equidad verificada. DIR={dir_score}")

    def handle(self, context: AuditContext) -> AuditContext:
        self.process(context)
        return super().handle(context)


# ──────────────────────────────────────────────────────
# Handler 4: Generador de Explicabilidad NLP (RFU-003)
# ──────────────────────────────────────────────────────
class NLPExplainerHandler(AuditHandler):
    """
    Traduce los coeficientes técnicos del modelo a lenguaje humano comprensible.
    Implementa la lógica de explicabilidad (como SHAP/LIME simplificado).
    """

    FRIENDLY_NAMES = {
        "monthly_income": "ingreso mensual",
        "credit_history_years": "historial crediticio",
        "debt_ratio": "ratio de deuda",
        "age": "edad",
        "gender_encoded": "género",
        "race_encoded": "procedencia",
        "zip_code": "zona geográfica",
    }

    def process(self, context: AuditContext) -> None:
        coefficients = context.response.raw_coefficients
        result = context.response.result

        # Ordenar por impacto absoluto (más influyentes primero)
        sorted_vars = sorted(coefficients.items(), key=lambda x: abs(x[1]), reverse=True)

        decision_word = "aprobada" if result == "APPROVED" else "denegada"
        lines = [f"La solicitud fue {decision_word} principalmente debido a:"]

        for var, coef in sorted_vars[:3]:  # Top 3 variables
            friendly = self.FRIENDLY_NAMES.get(var, var)
            direction = "positivamente" if coef > 0 else "negativamente"
            lines.append(f"  • {friendly.capitalize()} (influyó {direction}, peso: {abs(coef):.0%})")

        if context.validation_details.get("bias_detected"):
            lines.append(
                "\n⚠️  ALERTA: Se detectaron variables sensibles con peso significativo. "
                "Esta decisión requiere revisión manual."
            )

        context.nlp_explanation = "\n".join(lines)
        logger.info("[NLPExplainer] ✓ Explicación generada en lenguaje natural.")

    def handle(self, context: AuditContext) -> AuditContext:
        self.process(context)
        return super().handle(context)


# ──────────────────────────────────────────────────────
# Handler 5: Firmador Criptográfico (RFU-008, RFU-010)
# ──────────────────────────────────────────────────────
class HashSignerHandler(AuditHandler):
    """
    Genera la huella criptográfica SHA-256 del reporte completo.
    Esta firma hace inmutable el Ticket de Decisión (RNF-003).
    """

    def process(self, context: AuditContext) -> None:
        payload = {
            "request_id": context.request.request_id,
            "timestamp": context.request.timestamp.isoformat(),
            "model_version": context.response.model_version,
            "result": context.response.result,
            "confidence": context.response.confidence,
            "bias_metrics": context.bias_metrics,
            "nlp_explanation": context.nlp_explanation,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        context.integrity_hash = hashlib.sha256(raw.encode()).hexdigest()
        logger.info(f"[HashSigner] ✓ SHA-256 generado: {context.integrity_hash[:16]}...")

    def handle(self, context: AuditContext) -> AuditContext:
        self.process(context)
        return super().handle(context)


# ──────────────────────────────────────────────────────
# Factory: construye la cadena completa
# ──────────────────────────────────────────────────────
def build_audit_chain() -> AuditHandler:
    """
    Ensambla y devuelve la cadena de handlers lista para usar.
    Orden: PayloadValidator → SensitiveVarFilter → BiasAnalyzer → NLPExplainer → HashSigner
    """
    head = PayloadValidatorHandler()
    head.set_next(SensitiveVariableFilter()) \
        .set_next(BiasAnalyzerHandler()) \
        .set_next(NLPExplainerHandler()) \
        .set_next(HashSignerHandler())
    return head


def run_audit_chain(request: DecisionRequest, response: DecisionResponse) -> AuditReport:
    """
    Punto de entrada para ejecutar la cadena completa.
    Devuelve un AuditReport (Ticket de Decisión) listo para persistencia.
    """
    context = AuditContext(request, response)
    chain = build_audit_chain()
    chain.handle(context)

    return AuditReport(
        request_id=request.request_id,
        timestamp=request.timestamp,
        model_version=response.model_version,
        sector=request.sector,
        original_result=response.result,
        confidence=response.confidence,
        bias_detected=context.validation_details.get("bias_detected", False),
        bias_metrics=context.bias_metrics,
        nlp_explanation=context.nlp_explanation,
        integrity_hash=context.integrity_hash,
        validation_passed=context.validation_passed,
        validation_details=context.validation_details,
    )
