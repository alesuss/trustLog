"""
TrustLog - Orquestador Principal
=================================
Punto de entrada del framework. Conecta los tres patrones GoF en un flujo único:

  [Cliente] → Proxy (intercepta) → Chain (valida/audita) → Strategy (analiza por sector)
                                                         → AuditReport (Ticket de Decisión)
"""

import json
import logging
from typing import Any, Dict

from src.models.decision_request import DecisionRequest
from src.proxy.ai_request_proxy import AIRequestProxy
from src.chain.audit_chain import run_audit_chain
from src.strategy.audit_strategy import AuditEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def audit_decision(input_data: Dict[str, Any], sector: str, model_version: str = "v2.1") -> Dict:
    """
    Función principal del framework TrustLog.
    Orquesta los tres patrones GoF para producir un Ticket de Decisión completo.

    Args:
        input_data:    Datos del solicitante (ej. perfil crediticio).
        sector:        Sector del negocio: "financial", "hr", "health".
        model_version: Versión del modelo de IA externo a auditar.

    Returns:
        Diccionario con el Ticket de Decisión completo + análisis sectorial.
    """
    logger.info("=" * 60)
    logger.info("🔍 TrustLog: Iniciando auditoría algorítmica")
    logger.info("=" * 60)

    # ── Paso 1: PROXY — Interceptar la petición ──────────────────────
    logger.info("PASO 1: Proxy interceptando petición...")
    request = DecisionRequest(
        input_data=input_data,
        model_version=model_version,
        sector=sector,
    )
    proxy = AIRequestProxy.get_instance()
    response = proxy.intercept_request(request)
    logger.info(f"  ↳ Resultado del modelo: {response.result} (confianza: {response.confidence:.1%})")

    # ── Paso 2: CHAIN OF RESPONSIBILITY — Validar y auditar ──────────
    logger.info("PASO 2: Cadena de auditoría procesando respuesta...")
    audit_report = run_audit_chain(request, response)
    logger.info(f"  ↳ Sesgo detectado: {audit_report.bias_detected}")
    logger.info(f"  ↳ Hash SHA-256: {audit_report.integrity_hash[:24]}...")

    # ── Paso 3: STRATEGY — Análisis específico por sector ────────────
    logger.info(f"PASO 3: Aplicando estrategia de auditoría para sector '{sector}'...")
    engine = AuditEngine.for_sector(sector)
    final_analysis = engine.analyze(audit_report)
    risk = final_analysis["sector_analysis"]["risk_level"]
    logger.info(f"  ↳ Nivel de riesgo sectorial: {risk}")

    # ── Resultado final ───────────────────────────────────────────────
    ticket = {
        "ticket_de_decision": audit_report.to_dict(),
        "analisis_sectorial": final_analysis,
    }

    logger.info("=" * 60)
    logger.info(f"✅ Auditoría completada. Riesgo: {risk}")
    logger.info("=" * 60)
    return ticket


# ──────────────────────────────────────────────────────────────────────
# Demo: ejecutar con `python -m src.main`
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n" + "═" * 60)
    print("  TRUSTLOG — Demo de Auditoría Algorítmica")
    print("═" * 60)

    # Caso 1: Solicitud de crédito (sector financiero)
    print("\n📋 CASO 1: Solicitud de crédito bancario\n")
    ticket_1 = audit_decision(
        input_data={
            "monthly_income": 4500,
            "credit_history_years": 5,
            "debt_ratio": 0.30,
            "age": 35,
            "gender_encoded": 1,
        },
        sector="financial",
    )
    print("\n📄 EXPLICACIÓN EN LENGUAJE NATURAL:")
    print(ticket_1["analisis_sectorial"]["audit_summary"]["nlp_explanation"])
    print(f"\n🔒 HASH DE INTEGRIDAD: {ticket_1['ticket_de_decision']['integrity_hash']}")
    print(f"⚠️  NIVEL DE RIESGO:    {ticket_1['analisis_sectorial']['sector_analysis']['risk_level']}")

    # Caso 2: Selección de personal (sector RRHH)
    print("\n\n📋 CASO 2: Filtro de candidatos en RRHH\n")
    ticket_2 = audit_decision(
        input_data={
            "monthly_income": 2800,
            "credit_history_years": 2,
            "debt_ratio": 0.15,
            "age": 28,
            "gender_encoded": 0,
        },
        sector="hr",
    )
    print("\n📄 EXPLICACIÓN EN LENGUAJE NATURAL:")
    print(ticket_2["analisis_sectorial"]["audit_summary"]["nlp_explanation"])
    print(f"\n⚠️  NIVEL DE RIESGO: {ticket_2['analisis_sectorial']['sector_analysis']['risk_level']}")

    issues = ticket_2["analisis_sectorial"]["sector_analysis"].get("issues", [])
    if issues:
        print("🚨 PROBLEMAS DETECTADOS:")
        for issue in issues:
            print(f"   • {issue}")
