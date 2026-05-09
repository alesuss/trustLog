"""
TrustLog - Suite de Pruebas
============================
Pruebas unitarias e integración para los tres patrones GoF implementados.
Ejecutar con: python -m pytest tests/ -v
"""

import pytest
import json
from unittest.mock import MagicMock, patch

from src.models.decision_request import DecisionRequest, DecisionResponse, AuditReport
from src.proxy.ai_request_proxy import AIRequestProxy, RealModelIA
from src.chain.audit_chain import (
    AuditContext, PayloadValidatorHandler, SensitiveVariableFilter,
    BiasAnalyzerHandler, NLPExplainerHandler, HashSignerHandler, run_audit_chain
)
from src.strategy.audit_strategy import (
    AuditEngine, FinancialAuditStrategy, HRAuditStrategy, HealthAuditStrategy
)


# ═══════════════════════════════════════════════
# FIXTURES comunes
# ═══════════════════════════════════════════════

@pytest.fixture
def valid_request():
    return DecisionRequest(
        input_data={
            "monthly_income": 5000,
            "credit_history_years": 7,
            "debt_ratio": 0.25,
            "age": 40,
            "gender_encoded": 1,
        },
        model_version="credit-scoring-v2",
        sector="financial",
    )

@pytest.fixture
def valid_response(valid_request):
    return DecisionResponse(
        request_id=valid_request.request_id,
        result="APPROVED",
        confidence=0.92,
        model_version="credit-scoring-v2",
        raw_coefficients={
            "monthly_income": 0.62,
            "credit_history_years": 0.21,
            "debt_ratio": -0.43,
            "age": 0.08,
            "gender_encoded": 0.03,
        },
    )

@pytest.fixture
def biased_response(valid_request):
    """Respuesta con alto peso de variables sensibles (sesgo evidente)."""
    return DecisionResponse(
        request_id=valid_request.request_id,
        result="DENIED",
        confidence=0.78,
        model_version="credit-scoring-v2",
        raw_coefficients={
            "monthly_income": 0.10,
            "credit_history_years": 0.05,
            "debt_ratio": -0.05,
            "age": 0.40,           # muy alto → sesgo por edad
            "gender_encoded": 0.40, # muy alto → sesgo por género
        },
    )


# ═══════════════════════════════════════════════
# TESTS — Patrón PROXY
# ═══════════════════════════════════════════════

class TestAIRequestProxy:

    def test_singleton_returns_same_instance(self):
        """El Proxy debe ser un Singleton: misma instancia en múltiples llamadas."""
        proxy1 = AIRequestProxy.get_instance()
        proxy2 = AIRequestProxy.get_instance()
        assert proxy1 is proxy2

    def test_intercept_returns_decision_response(self, valid_request):
        """El Proxy debe devolver un DecisionResponse tipado correctamente."""
        proxy = AIRequestProxy.get_instance()
        response = proxy.intercept_request(valid_request)
        assert isinstance(response, DecisionResponse)
        assert response.request_id == valid_request.request_id
        assert response.result in ("APPROVED", "DENIED")
        assert 0.0 <= response.confidence <= 1.0

    def test_intercept_increments_counter(self, valid_request):
        """Cada intercepción debe incrementar el contador."""
        proxy = AIRequestProxy.get_instance()
        before = proxy.intercepted_count
        proxy.intercept_request(valid_request)
        assert proxy.intercepted_count == before + 1

    def test_real_model_approved_for_high_income(self):
        """El modelo real aprueba solicitudes con ingreso > 3000."""
        model = RealModelIA()
        raw = model.request(json.dumps({"monthly_income": 5000}))
        data = json.loads(raw)
        assert data["result"] == "APPROVED"

    def test_real_model_denied_for_low_income(self):
        """El modelo real deniega solicitudes con ingreso <= 3000."""
        model = RealModelIA()
        raw = model.request(json.dumps({"monthly_income": 1500}))
        data = json.loads(raw)
        assert data["result"] == "DENIED"


# ═══════════════════════════════════════════════
# TESTS — Patrón CHAIN OF RESPONSIBILITY
# ═══════════════════════════════════════════════

class TestAuditChain:

    def test_payload_validator_passes_valid_request(self, valid_request, valid_response):
        """Payloads con todos los campos requeridos deben pasar la validación."""
        context = AuditContext(valid_request, valid_response)
        handler = PayloadValidatorHandler()
        handler.handle(context)
        assert context.blocked is False
        assert context.validation_details["payload_valid"] is True

    def test_payload_validator_blocks_missing_fields(self, valid_response):
        """Payloads incompletos deben bloquear la cadena."""
        incomplete_request = DecisionRequest(
            input_data={"monthly_income": 3000},  # faltan campos
            model_version="v1",
            sector="financial",
        )
        context = AuditContext(incomplete_request, valid_response)
        handler = PayloadValidatorHandler()
        handler.handle(context)
        assert context.blocked is True
        assert context.validation_passed is False

    def test_bias_analyzer_detects_bias(self, valid_request, biased_response):
        """El analizador debe detectar sesgo cuando DIR < 0.8."""
        context = AuditContext(valid_request, biased_response)
        handler = BiasAnalyzerHandler()
        handler.handle(context)
        assert context.validation_details.get("bias_detected") is True
        assert context.bias_metrics["disparate_impact_ratio"] < 0.80

    def test_bias_analyzer_passes_fair_response(self, valid_request, valid_response):
        """El analizador no debe marcar sesgo en respuestas equitativas."""
        context = AuditContext(valid_request, valid_response)
        handler = BiasAnalyzerHandler()
        handler.handle(context)
        assert context.validation_details.get("bias_detected") is False

    def test_nlp_explainer_generates_text(self, valid_request, valid_response):
        """El handler NLP debe generar texto no vacío."""
        context = AuditContext(valid_request, valid_response)
        handler = NLPExplainerHandler()
        handler.handle(context)
        assert len(context.nlp_explanation) > 0
        assert "aprobada" in context.nlp_explanation.lower() or "denegada" in context.nlp_explanation.lower()

    def test_hash_signer_generates_sha256(self, valid_request, valid_response):
        """El firmador debe generar un hash SHA-256 de 64 caracteres hexadecimales."""
        context = AuditContext(valid_request, valid_response)
        context.bias_metrics = {"disparate_impact_ratio": 0.90}
        context.nlp_explanation = "Aprobado por alto ingreso mensual."
        handler = HashSignerHandler()
        handler.handle(context)
        assert len(context.integrity_hash) == 64
        assert all(c in "0123456789abcdef" for c in context.integrity_hash)

    def test_full_chain_produces_audit_report(self, valid_request, valid_response):
        """La cadena completa debe producir un AuditReport válido."""
        report = run_audit_chain(valid_request, valid_response)
        assert isinstance(report, AuditReport)
        assert report.request_id == valid_request.request_id
        assert report.integrity_hash != ""
        assert report.nlp_explanation != ""

    def test_full_chain_with_biased_data(self, valid_request, biased_response):
        """La cadena completa debe detectar sesgo en datos sesgados."""
        report = run_audit_chain(valid_request, biased_response)
        assert report.bias_detected is True


# ═══════════════════════════════════════════════
# TESTS — Patrón STRATEGY
# ═══════════════════════════════════════════════

def make_report(bias_detected=False, dir_score=0.90, confidence=0.92, result="APPROVED", sector="financial"):
    from datetime import datetime
    import uuid
    return AuditReport(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        model_version="v2",
        sector=sector,
        original_result=result,
        confidence=confidence,
        bias_detected=bias_detected,
        bias_metrics={
            "disparate_impact_ratio": dir_score,
            "sensitive_variable_weight": 0.04,
        },
        nlp_explanation="Solicitud aprobada por alto ingreso.",
        integrity_hash="abc123" * 10,
        validation_passed=not bias_detected,
    )


class TestAuditStrategy:

    def test_engine_for_financial_sector(self):
        """El motor debe cargar la estrategia financiera correctamente."""
        engine = AuditEngine.for_sector("financial")
        assert isinstance(engine._strategy, FinancialAuditStrategy)

    def test_engine_for_hr_sector(self):
        engine = AuditEngine.for_sector("hr")
        assert isinstance(engine._strategy, HRAuditStrategy)

    def test_engine_for_health_sector(self):
        engine = AuditEngine.for_sector("health")
        assert isinstance(engine._strategy, HealthAuditStrategy)

    def test_engine_raises_for_unknown_sector(self):
        with pytest.raises(ValueError, match="no soportado"):
            AuditEngine.for_sector("unknown_sector")

    def test_financial_strategy_low_risk(self):
        """Un reporte sin sesgo en el sector financiero debe ser BAJO riesgo."""
        engine = AuditEngine.for_sector("financial")
        report = make_report(bias_detected=False, dir_score=0.92, confidence=0.90)
        result = engine.analyze(report)
        assert result["sector_analysis"]["risk_level"] == "BAJO"

    def test_financial_strategy_high_risk(self):
        """Un reporte con sesgo fuerte debe ser ALTO o CRÍTICO en finanzas."""
        engine = AuditEngine.for_sector("financial")
        report = make_report(bias_detected=True, dir_score=0.60, confidence=0.85)
        result = engine.analyze(report)
        assert result["sector_analysis"]["risk_level"] in ("ALTO", "CRÍTICO")

    def test_health_strategy_critical_on_low_confidence(self):
        """En salud, confianza < 90% debe generar riesgo CRÍTICO."""
        engine = AuditEngine.for_sector("health")
        report = make_report(confidence=0.75, dir_score=0.95, sector="health")
        result = engine.analyze(report)
        assert result["sector_analysis"]["risk_level"] == "CRÍTICO"

    def test_strategy_can_be_changed_at_runtime(self):
        """La estrategia debe poder cambiarse en tiempo de ejecución."""
        engine = AuditEngine.for_sector("financial")
        engine.set_strategy(HRAuditStrategy())
        assert isinstance(engine._strategy, HRAuditStrategy)

    def test_analysis_result_contains_required_keys(self):
        """El resultado del análisis debe contener las claves mínimas requeridas."""
        engine = AuditEngine.for_sector("financial")
        report = make_report()
        result = engine.analyze(report)
        assert "request_id" in result
        assert "sector_analysis" in result
        assert "audit_summary" in result
        assert "integrity_hash" in result["audit_summary"]
