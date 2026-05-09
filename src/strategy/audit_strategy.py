"""
TrustLog - Patrón STRATEGY
============================
Define una familia de algoritmos de auditoría intercambiables según el sector
(financiero, recursos humanos, salud). El cliente usa siempre la misma interfaz
sin conocer qué estrategia concreta se está ejecutando.

Estructura GoF aplicada:
  - AuditStrategy          → Strategy (interfaz)
  - FinancialAuditStrategy → ConcreteStrategy A
  - HRAuditStrategy        → ConcreteStrategy B
  - HealthAuditStrategy    → ConcreteStrategy C
  - AuditEngine            → Context (usa la estrategia)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from src.models.decision_request import AuditReport

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────
# Strategy: interfaz común para todas las estrategias
# ──────────────────────────────────────────────────────
class AuditStrategy(ABC):
    """
    Define el contrato que deben cumplir todas las estrategias de auditoría.
    Cada sector tiene reglas de equidad y umbrales de riesgo propios.
    """

    @abstractmethod
    def evaluate(self, report: AuditReport) -> Tuple[str, Dict[str, Any]]:
        """
        Evalúa el reporte bajo las reglas del sector específico.
        Devuelve: (nivel_de_riesgo, detalles_del_sector)
        """
        pass

    @abstractmethod
    def get_applicable_regulations(self) -> list[str]:
        """Lista de normativas aplicables al sector."""
        pass

    @property
    @abstractmethod
    def sector_name(self) -> str:
        pass


# ──────────────────────────────────────────────────────
# ConcreteStrategy A: Sector Financiero
# ──────────────────────────────────────────────────────
class FinancialAuditStrategy(AuditStrategy):
    """
    Estrategia para auditar decisiones de crédito, préstamos y seguros.
    Aplica la regla 4/5 de la EEOC y verifica cumplimiento GDPR Art. 22.
    Umbral DIR más estricto: 0.85 (sector regulado con alto riesgo legal).
    """

    DIR_THRESHOLD = 0.85
    MAX_SENSITIVE_WEIGHT = 0.05  # máx. 5% de peso en variables sensibles

    @property
    def sector_name(self) -> str:
        return "Financiero / Crédito"

    def get_applicable_regulations(self) -> list[str]:
        return [
            "GDPR Art. 22 - Decisiones automatizadas",
            "Ley N° 29733 - Protección de Datos Personales (Perú)",
            "EEOC - Regla 4/5 de Impacto Dispar",
            "Basel III - Gestión de Riesgo Operativo",
        ]

    def evaluate(self, report: AuditReport) -> Tuple[str, Dict[str, Any]]:
        dir_score = report.bias_metrics.get("disparate_impact_ratio", 1.0)
        sensitive_weight = report.bias_metrics.get("sensitive_variable_weight", 0.0)

        issues = []
        risk_score = 0

        if dir_score < self.DIR_THRESHOLD:
            issues.append(
                f"DIR={dir_score:.3f} por debajo del umbral financiero ({self.DIR_THRESHOLD})"
            )
            risk_score += 3

        if sensitive_weight > self.MAX_SENSITIVE_WEIGHT:
            issues.append(
                f"Variables sensibles con peso {sensitive_weight:.1%} > máximo permitido "
                f"({self.MAX_SENSITIVE_WEIGHT:.1%})"
            )
            risk_score += 2

        if report.confidence < 0.70:
            issues.append(f"Confianza baja ({report.confidence:.1%}): requiere revisión humana.")
            risk_score += 1

        risk_level = "CRÍTICO" if risk_score >= 4 else "ALTO" if risk_score >= 2 else "BAJO"

        details = {
            "sector": self.sector_name,
            "regulations": self.get_applicable_regulations(),
            "risk_score": risk_score,
            "issues": issues,
            "dir_threshold_used": self.DIR_THRESHOLD,
            "recommendation": (
                "Bloquear decisión y derivar a revisor humano."
                if risk_level == "CRÍTICO"
                else "Registrar para auditoría periódica."
            ),
        }

        logger.info(f"[FinancialStrategy] Evaluación completada. Riesgo: {risk_level}")
        return risk_level, details


# ──────────────────────────────────────────────────────
# ConcreteStrategy B: Recursos Humanos
# ──────────────────────────────────────────────────────
class HRAuditStrategy(AuditStrategy):
    """
    Estrategia para auditar selección de personal y evaluaciones laborales.
    Mayor énfasis en variables de género y procedencia geográfica.
    """

    DIR_THRESHOLD = 0.80
    GENDER_WEIGHT_LIMIT = 0.02  # género NO debe influir en selección

    @property
    def sector_name(self) -> str:
        return "Recursos Humanos / Selección de Personal"

    def get_applicable_regulations(self) -> list[str]:
        return [
            "Ley N° 26772 - No Discriminación en Ofertas de Empleo (Perú)",
            "GDPR Art. 9 - Datos de categoría especial",
            "OIT - Convenio 111 sobre Discriminación",
            "ISO 30415 - Diversidad e Inclusión",
        ]

    def evaluate(self, report: AuditReport) -> Tuple[str, Dict[str, Any]]:
        dir_score = report.bias_metrics.get("disparate_impact_ratio", 1.0)
        sensitive_weight = report.bias_metrics.get("sensitive_variable_weight", 0.0)

        issues = []
        risk_score = 0

        if dir_score < self.DIR_THRESHOLD:
            issues.append(f"Impacto dispar detectado: DIR={dir_score:.3f}")
            risk_score += 3

        # En RRHH, cualquier peso de género > 2% es inaceptable
        gender_coef = abs(
            report.bias_metrics.get("gender_encoded", 0) or sensitive_weight * 0.5
        )
        if gender_coef > self.GENDER_WEIGHT_LIMIT:
            issues.append(
                f"Variable 'género' con peso significativo ({gender_coef:.1%}): "
                "viola principio de no discriminación laboral."
            )
            risk_score += 4  # Más grave en RRHH

        risk_level = "CRÍTICO" if risk_score >= 4 else "ALTO" if risk_score >= 2 else "BAJO"

        details = {
            "sector": self.sector_name,
            "regulations": self.get_applicable_regulations(),
            "risk_score": risk_score,
            "issues": issues,
            "gender_weight_limit": self.GENDER_WEIGHT_LIMIT,
            "recommendation": (
                "DETENER proceso de selección. Notificar al área legal."
                if risk_level == "CRÍTICO"
                else "Documentar y revisar en próxima auditoría de RRHH."
            ),
        }

        logger.info(f"[HRStrategy] Evaluación completada. Riesgo: {risk_level}")
        return risk_level, details


# ──────────────────────────────────────────────────────
# ConcreteStrategy C: Salud
# ──────────────────────────────────────────────────────
class HealthAuditStrategy(AuditStrategy):
    """
    Estrategia para auditar diagnósticos asistidos por IA en el sector salud.
    Prioriza confianza alta y cero tolerancia a variables sensibles (raza, edad).
    """

    MIN_CONFIDENCE = 0.90  # diagnósticos requieren alta certeza
    DIR_THRESHOLD = 0.90   # umbral más estricto: vidas en juego

    @property
    def sector_name(self) -> str:
        return "Salud / Diagnóstico Asistido"

    def get_applicable_regulations(self) -> list[str]:
        return [
            "Ley N° 29414 - Derechos de los Pacientes (Perú)",
            "HIPAA - Privacidad de Información Médica",
            "GDPR Art. 9 - Datos de salud (categoría especial)",
            "FDA 21 CFR Part 11 - Registros Electrónicos en Salud",
        ]

    def evaluate(self, report: AuditReport) -> Tuple[str, Dict[str, Any]]:
        dir_score = report.bias_metrics.get("disparate_impact_ratio", 1.0)

        issues = []
        risk_score = 0

        if report.confidence < self.MIN_CONFIDENCE:
            issues.append(
                f"Confianza del diagnóstico ({report.confidence:.1%}) por debajo del mínimo "
                f"clínico ({self.MIN_CONFIDENCE:.0%}). Obligatoria revisión médica."
            )
            risk_score += 5

        if dir_score < self.DIR_THRESHOLD:
            issues.append(
                f"Posible sesgo en diagnóstico: DIR={dir_score:.3f}. "
                "Podría indicar disparidad en tratamiento por grupo demográfico."
            )
            risk_score += 3

        risk_level = "CRÍTICO" if risk_score >= 4 else "ALTO" if risk_score >= 2 else "BAJO"

        details = {
            "sector": self.sector_name,
            "regulations": self.get_applicable_regulations(),
            "risk_score": risk_score,
            "issues": issues,
            "min_confidence_required": self.MIN_CONFIDENCE,
            "recommendation": (
                "BLOQUEAR diagnóstico automático. Derivar a especialista de forma inmediata."
                if risk_level == "CRÍTICO"
                else "Diagnóstico dentro de parámetros. Registrar para trazabilidad."
            ),
        }

        logger.info(f"[HealthStrategy] Evaluación completada. Riesgo: {risk_level}")
        return risk_level, details


# ──────────────────────────────────────────────────────
# Context: AuditEngine usa la estrategia inyectada
# ──────────────────────────────────────────────────────
class AuditEngine:
    """
    Contexto del patrón Strategy.
    Recibe la estrategia apropiada al sector y la ejecuta sobre el reporte.
    Permite cambiar la estrategia en tiempo de ejecución (setStrategy).
    """

    STRATEGY_MAP: Dict[str, AuditStrategy] = {
        "financial": FinancialAuditStrategy(),
        "hr": HRAuditStrategy(),
        "health": HealthAuditStrategy(),
    }

    def __init__(self, strategy: Optional[AuditStrategy] = None):
        self._strategy: Optional[AuditStrategy] = strategy

    def set_strategy(self, strategy: AuditStrategy) -> None:
        """Permite cambiar la estrategia en tiempo de ejecución."""
        self._strategy = strategy
        logger.info(f"[AuditEngine] Estrategia cambiada a: {strategy.sector_name}")

    @classmethod
    def for_sector(cls, sector: str) -> "AuditEngine":
        """Factory method: crea un AuditEngine con la estrategia correcta para el sector."""
        strategy = cls.STRATEGY_MAP.get(sector.lower())
        if not strategy:
            raise ValueError(
                f"Sector '{sector}' no soportado. "
                f"Opciones: {list(cls.STRATEGY_MAP.keys())}"
            )
        return cls(strategy=strategy)

    def analyze(self, report: AuditReport) -> Dict[str, Any]:
        """
        Ejecuta la estrategia activa sobre el reporte de auditoría.
        Devuelve el resultado enriquecido con el análisis sectorial.
        """
        if not self._strategy:
            raise RuntimeError("No hay estrategia configurada. Usa set_strategy() o for_sector().")

        risk_level, details = self._strategy.evaluate(report)

        return {
            "request_id": report.request_id,
            "sector_analysis": {
                "risk_level": risk_level,
                **details,
            },
            "audit_summary": {
                "result": report.original_result,
                "bias_detected": report.bias_detected,
                "validation_passed": report.validation_passed,
                "integrity_hash": report.integrity_hash,
                "nlp_explanation": report.nlp_explanation,
            },
        }



