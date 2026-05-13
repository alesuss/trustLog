# 🛡️ TrustLog — Framework de Auditoría Algorítmica

> **Transparencia, Equidad e Inmutabilidad para decisiones de Inteligencia Artificial.**

TrustLog es un framework implementado en **Java** que actúa como capa de auditoría en tiempo real sobre modelos de IA de "caja negra". Intercepta cada decisión algorítmica mediante un Proxy coordinador, aplica una cadena de validaciones, evalúa el riesgo con una estrategia intercambiable y emite un **Ticket de Decisión** con firma de integridad.

---

## 📋 Tabla de Contenidos

- [Descripción del Proyecto](#descripción-del-proyecto)
- [Patrones GoF Implementados](#patrones-gof-implementados)
- [Arquitectura](#arquitectura)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Requisitos Previos](#requisitos-previos)
- [Instrucciones de Ejecución](#instrucciones-de-ejecución)
- [Casos de Uso](#casos-de-uso)
- [Integrantes del Equipo](#integrantes-del-equipo)

---

## Descripción del Proyecto

Las empresas adoptan IA para procesos críticos (créditos, selección de personal, diagnósticos) sin mecanismos de explicabilidad ni auditoría, exponiéndose a riesgos legales y discriminación algorítmica inadvertida.

**TrustLog resuelve esto mediante:**

- 🔍 **Intercepción transparente** (Proxy inverso + Singleton) de peticiones entre cliente y modelo de IA.
- 🚦 **Control de tráfico y permisos** antes de redirigir al modelo real (`TrafficController`, `AccountManager`).
- ⛓️ **Cadena de validaciones** secuencial y extensible sobre cada reporte de auditoría.
- ⚖️ **Evaluación de sesgo** configurable mediante estrategias intercambiables en tiempo de ejecución.
- 🔒 **Hash de integridad** generado por `SecurityManager` sobre el `AuditReport` final.

---

## Patrones GoF Implementados

### 1. 🔷 Proxy (`Proxy`)

**Categoría:** Estructural

**Propósito:** Actuar como intermediario transparente entre el cliente y el modelo de IA externo (`RealModelIA`), sin que el cliente perciba diferencia alguna.

**Implementación:**
- `IModelIA` → interfaz Subject compartida por el Proxy y el modelo real.
- `RealModelIA` → RealSubject que simula el endpoint del modelo externo.
- `Proxy` → intercepta la petición, coordina todos los componentes de auditoría y redirige al modelo real al final.
- Implementado también como **Singleton** (`getInstance()`) para garantizar un único punto de intercepción por proceso.

**Componentes de soporte coordinados por el Proxy:**

| Componente | Responsabilidad |
|---|---|
| `TrafficController` | Verifica la tasa de peticiones del usuario antes de procesar |
| `AccountManager` | Valida el permiso de acceso al recurso del modelo de IA |
| `SecurityManager` | Genera el hash de integridad SHA-256 del `AuditReport` |
| `AuditEngine` | Ejecuta la estrategia de evaluación de riesgo activa |

```java
IModelIA sistema = Proxy.getInstance();
String respuesta = sistema.request("Analizar riesgo crediticio");
```

---

### 2. ⛓️ Chain of Responsibility (`AuditHandler`)

**Categoría:** Comportamiento

**Propósito:** Aplicar una secuencia de validaciones y transformaciones al `AuditReport` de cada petición interceptada, donde cada handler puede procesar y pasar el flujo al siguiente.

**Cadena implementada:**

```
PayloadValidator → [extensible: nuevos handlers]
```

| Handler | Responsabilidad |
|---|---|
| `PayloadValidator` | Verifica que el reporte de auditoría tenga los campos requeridos |

> **Extensibilidad:** La cadena se construye enlazando objetos `AuditHandler` mediante `setNext()`. Agregar nuevos filtros (ej. `BiasAnalyzerHandler`, `NLPExplainerHandler`) no requiere modificar los handlers existentes, respetando el principio Open/Closed.

```java
// Construcción de la cadena
AuditHandler chain = new PayloadValidator();
// chain.setNext(new BiasAnalyzerHandler()); // fácil de extender

chain.handle(report);
```

---

### 3. 🎯 Strategy (`AuditStrategy`)

**Categoría:** Comportamiento

**Propósito:** Definir una familia de algoritmos de evaluación de riesgo intercambiables según el contexto del negocio, sin modificar el `AuditEngine` (Context).

**Implementación:**

| Clase | Rol |
|---|---|
| `AuditStrategy` | Interfaz que declara `evaluate(AuditReport report)` |
| `ConcreteStrategy` | Estrategia activa: marca sesgo si `confidenceLevel < 0.85` |
| `AuditEngine` | Context que delega la evaluación a la estrategia configurada |

**Justificación:** El `AuditEngine` aplica la regla de negocio correcta dinámicamente mediante `setStrategy()`, sin condicionales anidados. Permite agregar nuevas estrategias sectoriales (financiera, RRHH, salud) sin modificar código existente.

```java
AuditEngine engine = new AuditEngine();
engine.setStrategy(new ConcreteStrategy());
engine.analyzeInterference(report);
```

---

## Arquitectura

```
[Cliente]
    │
    │  IModelIA.request(inputData)
    ▼
┌──────────────────────────────────────────┐
│  PROXY — Singleton (Patrón 1)            │
│                                          │
│  1. TrafficController.throttle()         │
│  2. AccountManager.checkPermission()     │
│  3. AuditReport creado                   │
│  4. Chain.handle(report)  (Patrón 2)     │
│  5. AuditEngine.analyzeInterference()    │
│     └─ ConcreteStrategy.evaluate()       │
│        (Patrón 3)                        │
│  6. SecurityManager.generateHash()       │
│  7. RealModelIA.request(inputData)       │
└──────────────────┬───────────────────────┘
                   │
                   ▼
         [Respuesta al Cliente]
```

---

## Estructura del Proyecto

```
trustlog/
└── Main.java          # Todas las clases en un único archivo compilable
    ├── IModelIA           (interfaz Subject)
    ├── RealModelIA        (RealSubject)
    ├── AuditReport        (modelo de datos del ticket de auditoría)
    ├── SecurityManager    (generación de hash de integridad)
    ├── TrafficController  (control de tasa de peticiones)
    ├── AccountManager     (control de permisos de acceso)
    ├── AuditStrategy      (interfaz Strategy)
    ├── ConcreteStrategy   (evaluación de sesgo por nivel de confianza)
    ├── AuditEngine        (Context del patrón Strategy)
    ├── AuditHandler       (handler abstracto de la cadena)
    ├── PayloadValidator   (primer eslabón de la cadena)
    ├── Proxy              (Proxy + Singleton, coordinador central)
    └── Main               (clase principal — punto de entrada)
```

---

## Requisitos Previos

- **Java 11** o superior (compatible con Java 8+)
- No requiere dependencias externas ni herramientas de build adicionales

Verificar versión de Java:
```bash
java -version
```

---

## Instrucciones de Ejecución

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/trustlog.git
cd trustlog
```

### 2. Compilar el archivo

```bash
javac Main.java
```

### 3. Ejecutar el programa

```bash
java Main
```

**Salida esperada:**

```
--- [Proxy]: Interceptando Petición ---
[TrafficController]: Verificando tasa de peticiones para USER-777
[AccountManager]: Permiso concedido para IA_Model
[Chain]: Validando Payload... ✓
[AuditEngine]: Ejecutando estrategia para Financial
[Security]: Hash de integridad: SHA-256-<hash>
[Proxy]: Redirigiendo a RealModelIA...

[Cliente] Respuesta recibida: Respuesta de IA Real para: Analizar riesgo crediticio
```

---

## Casos de Uso

### Uso básico — petición al modelo auditado

```java
// El cliente interactúa con el Proxy como si fuera el modelo real
IModelIA sistema = Proxy.getInstance();
String respuesta = sistema.request("Analizar riesgo crediticio");
System.out.println(respuesta);
```

### Cambiar la estrategia de evaluación en tiempo de ejecución

```java
AuditEngine engine = new AuditEngine();

// Estrategia estricta para sector salud
engine.setStrategy(report -> {
    if (report.confidenceLevel < 0.90) report.biasDetected = true;
});
engine.analyzeInterference(report);
```

### Extender la cadena con un nuevo handler

```java
// Crear nuevo handler
class BiasAnalyzerHandler extends AuditHandler {
    protected void process(AuditReport report) {
        System.out.println("[Chain]: Analizando sesgo... ✓");
        if (report.confidenceLevel < 0.80) report.biasDetected = true;
    }
}

// Encadenar después del PayloadValidator
AuditHandler validator = new PayloadValidator();
validator.setNext(new BiasAnalyzerHandler());
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

**Universidad Peruana de Ciencias Aplicadas — Ingeniería de Software**
*1ASI0720 Diseño y Patrones de Software · 202610 · NRC: 16683*
*Profesor: Javier Teodocio Roque Espinoza*
