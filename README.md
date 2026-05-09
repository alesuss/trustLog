# 🛡️ TrustLog — Framework de Auditoría Algorítmica

> **Transparencia, Equidad e Inmutabilidad para decisiones de Inteligencia Artificial.**

TrustLog es un framework de ingeniería de software que actúa como capa de auditoría en tiempo real sobre modelos de IA de "caja negra". Intercepta cada decisión algorítmica, detecta sesgos matemáticamente, genera explicaciones en lenguaje natural y emite un **Ticket de Decisión** inmutable con firma criptográfica SHA-256.

---

## 📋 Tabla de Contenidos

- [Descripción del Proyecto](#descripción-del-proyecto)
- [Patrones GoF Implementados](#patrones-gof-implementados)
- [Arquitectura](#arquitectura)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Requisitos Previos](#requisitos-previos)
- [Instrucciones de Ejecución](#instrucciones-de-ejecución)
- [Ejecución de Pruebas](#ejecución-de-pruebas)
- [Casos de Uso](#casos-de-uso)
- [Integrantes del Equipo](#integrantes-del-equipo)

---

## Descripción del Proyecto

Las empresas adoptan IA para procesos críticos (créditos, selección de personal, diagnósticos) sin mecanismos de explicabilidad ni auditoría, exponiéndose a riesgos legales y discriminación algorítmica inadvertida.

**TrustLog resuelve esto mediante:**

- 🔍 **Intercepción transparente** (Proxy inverso) de peticiones entre cliente y modelo de IA.
- ⚖️ **Análisis matemático de equidad** (Disparate Impact Ratio, SHAP coefficients).
- 💬 **Explicabilidad en lenguaje natural** (NLP) de las variables que determinaron la decisión.
- 🔒 **Ticket de Decisión inmutable** firmado con SHA-256, válido como evidencia legal.

---

## Patrones GoF Implementados

### 1. 🔷 Proxy (`src/proxy/ai_request_proxy.py`)

**Categoría:** Estructural

**Propósito:** Actuar como intermediario transparente entre el cliente y el modelo de IA externo, sin modificar la infraestructura existente del cliente.

**Implementación:**
- `IModelIA` → interfaz Subject común al Proxy y al modelo real.
- `RealModelIA` → RealSubject que simula el endpoint del modelo externo.
- `AIRequestProxy` → Proxy que intercepta, registra y redirige cada petición.
- Implementado también como **Singleton** para garantizar un único punto de intercepción por proceso.

**Justificación:** El equipo identificó que las empresas clientes no pueden (ni deben) modificar su modelo de IA. El Proxy permite añadir la capa de auditoría de forma no invasiva, cumpliendo el requisito `RFU-004` (intermediario transparente).

```python
proxy = AIRequestProxy.get_instance()
response = proxy.intercept_request(request)
```

---

### 2. ⛓️ Chain of Responsibility (`src/chain/audit_chain.py`)

**Categoría:** Comportamiento

**Propósito:** Aplicar una secuencia de validaciones y transformaciones a cada respuesta interceptada, donde cada handler puede procesar o detener el flujo.

**Cadena implementada:**

```
PayloadValidator → SensitiveVariableFilter → BiasAnalyzer → NLPExplainer → HashSigner
```

| Handler | Responsabilidad | Requisito |
|---|---|---|
| `PayloadValidatorHandler` | Verifica que el payload tenga todos los campos requeridos | RFU-005 |
| `SensitiveVariableFilter` | Detecta variables sensibles (género, edad, raza) con peso significativo | RFU-007 |
| `BiasAnalyzerHandler` | Calcula el Disparate Impact Ratio y detecta discriminación algorítmica | RFU-002 |
| `NLPExplainerHandler` | Traduce coeficientes técnicos a explicaciones en lenguaje humano | RFU-003 |
| `HashSignerHandler` | Genera la firma SHA-256 del reporte (inmutabilidad) | RFU-008 |

**Justificación:** La naturaleza secuencial y extensible de la validación encaja perfectamente con este patrón. Permite agregar nuevos filtros (ej. cumplimiento GDPR) sin modificar los existentes, respetando el principio Open/Closed.

```python
audit_report = run_audit_chain(request, response)
```

---

### 3. 🎯 Strategy (`src/strategy/audit_strategy.py`)

**Categoría:** Comportamiento

**Propósito:** Definir una familia de algoritmos de evaluación de riesgo intercambiables según el sector del negocio (financiero, RRHH, salud).

**Estrategias concretas:**

| Estrategia | Sector | Umbrales | Normativas |
|---|---|---|---|
| `FinancialAuditStrategy` | Créditos / Seguros | DIR ≥ 0.85, Confianza ≥ 70% | GDPR Art. 22, Ley 29733, EEOC |
| `HRAuditStrategy` | Selección de Personal | DIR ≥ 0.80, Género < 2% | Ley 26772, OIT Conv. 111 |
| `HealthAuditStrategy` | Diagnóstico Médico | DIR ≥ 0.90, Confianza ≥ 90% | Ley 29414, HIPAA |

**Justificación:** Cada sector tiene regulaciones y umbrales de riesgo distintos. El patrón Strategy permite que el `AuditEngine` (Context) aplique las reglas correctas dinámicamente, sin condicionales anidados, y permite agregar nuevos sectores sin modificar el código existente.

```python
engine = AuditEngine.for_sector("financial")
result = engine.analyze(audit_report)
```

---

## Arquitectura

```
[Cliente B2B]
      │
      ▼
┌─────────────────────────────────────┐
│  PROXY (Patrón 1)                   │
│  Intercepta y redirige la petición  │
│  sin alterar el flujo del negocio   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  MODELO DE IA EXTERNO               │
│  (AWS SageMaker / OpenAI / Custom)  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  CHAIN OF RESPONSIBILITY (Patrón 2) │
│  Payload → Sesgo → NLP → Hash       │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  STRATEGY (Patrón 3)                │
│  Evaluación de riesgo por sector    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  TICKET DE DECISIÓN (AuditReport)   │
│  SHA-256 · NLP · Métricas · Riesgo  │
└─────────────────────────────────────┘
```

---

## Estructura del Proyecto

```
trustlog/
├── src/
│   ├── models/
│   │   └── decision_request.py     # Modelos de datos: Request, Response, AuditReport
│   ├── proxy/
│   │   └── ai_request_proxy.py     # Patrón Proxy (+ Singleton)
│   ├── chain/
│   │   └── audit_chain.py          # Patrón Chain of Responsibility
│   ├── strategy/
│   │   └── audit_strategy.py       # Patrón Strategy
│   └── main.py                     # Orquestador principal (demo)
├── tests/
│   └── test_patterns.py            # Suite de pruebas unitarias
└── README.md
```

---

## Requisitos Previos

- Python **3.10** o superior
- No requiere dependencias externas (usa solo la biblioteca estándar de Python)

Verificar versión de Python:
```bash
python --version
```

---

## Instrucciones de Ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/trustlog.git
cd trustlog
```

### 2. (Opcional) Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 3. Ejecutar el demo principal

```bash
python -m src.main
```

**Salida esperada:**

```
══════════════════════════════════════════════════════════
  TRUSTLOG — Demo de Auditoría Algorítmica
══════════════════════════════════════════════════════════

📋 CASO 1: Solicitud de crédito bancario

04:29:00 [INFO] PASO 1: Proxy interceptando petición...
04:29:00 [INFO] [PROXY] Petición #1 interceptada
04:29:00 [INFO] PASO 2: Cadena de auditoría procesando respuesta...
04:29:00 [INFO] [PayloadValidator] ✓ Payload válido.
04:29:00 [INFO] [BiasAnalyzer] ✓ Equidad verificada. DIR=0.9197
04:29:00 [INFO] [HashSigner] ✓ SHA-256 generado: 3287f893edb34da8...

📄 EXPLICACIÓN EN LENGUAJE NATURAL:
La solicitud fue aprobada principalmente debido a:
  • Ingreso mensual (influyó positivamente, peso: 62%)
  • Ratio de deuda (influyó negativamente, peso: 43%)
  • Historial crediticio (influyó positivamente, peso: 21%)

🔒 HASH DE INTEGRIDAD: 3287f893edb34da86e1838164721b42a...
⚠️  NIVEL DE RIESGO:    ALTO
```

### 4. Usar TrustLog desde código propio

```python
from src.main import audit_decision

# Auditar una decisión crediticia
ticket = audit_decision(
    input_data={
        "monthly_income": 4500,
        "credit_history_years": 5,
        "debt_ratio": 0.30,
        "age": 35,
        "gender_encoded": 1,
    },
    sector="financial",  # "financial" | "hr" | "health"
)

print(ticket["analisis_sectorial"]["audit_summary"]["nlp_explanation"])
print(ticket["ticket_de_decision"]["integrity_hash"])
```

---

## Ejecución de Pruebas

```bash
# Instalar pytest
pip install pytest

# Ejecutar todas las pruebas
python -m pytest tests/ -v

# Ejecutar pruebas por patrón
python -m pytest tests/ -v -k "TestAIRequestProxy"    # Solo Proxy
python -m pytest tests/ -v -k "TestAuditChain"        # Solo Chain
python -m pytest tests/ -v -k "TestAuditStrategy"     # Solo Strategy
```

**Cobertura de pruebas:**

| Módulo | Tests | Qué se verifica |
|---|---|---|
| Proxy | 5 | Singleton, intercepción, contador, modelo real |
| Chain | 8 | Cada handler por separado + cadena completa |
| Strategy | 9 | Cada estrategia + cambio en runtime + claves de respuesta |

---

## Casos de Uso

### Sector Financiero — Créditos
```python
ticket = audit_decision(
    input_data={"monthly_income": 2000, "credit_history_years": 1,
                "debt_ratio": 0.60, "age": 22, "gender_encoded": 0},
    sector="financial"
)
```

### Sector RRHH — Selección de Personal
```python
ticket = audit_decision(
    input_data={"monthly_income": 3000, "credit_history_years": 3,
                "debt_ratio": 0.20, "age": 28, "gender_encoded": 1},
    sector="hr"
)
```

### Sector Salud — Diagnóstico Asistido
```python
ticket = audit_decision(
    input_data={"monthly_income": 0, "credit_history_years": 0,
                "debt_ratio": 0, "age": 55, "gender_encoded": 0},
    sector="health"
)
```

---

## Integrantes del Equipo

| Nombre | Código | Rol |
|---|---|---|
| Alejandro Jesús Cumpen Cojal | U20251C684 | Líder de Proyecto / UX Designer |
| Enmanuel Mathias Taboada Hernandez | U20251E949 | Líder Técnico / Backend |
| Diego Sahid Horna Diaz | U202512246 | Líder de Dominio / Frontend |
| Jharinara Stefany Lescano Luna | U202427114 | Líder de Calidad / DevOps |

---

**Universidad Peruana de Ciencias Aplicadas — Ingeniería de Software**
*1ASI0720 Diseño y Patrones de Software · 202610 · NRC: 16683*
*Profesor: Javier Teodocio Roque Espinoza*
