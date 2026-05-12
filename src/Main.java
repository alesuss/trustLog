import java.util.*;

// ==========================================
// 1. INTERFACES Y MODELOS BASE
// ==========================================
interface IModelIA {
    String request(String inputData);
}

class RealModelIA implements IModelIA {
    public @Override String request(String inputData) {
        return "Respuesta de IA Real para: " + inputData;
    }
}

class AuditReport {
    public String transactionId = UUID.randomUUID().toString();
    public String sector;
    public double confidenceLevel;
    public String integrityHash;
    public boolean biasDetected = false;

    public AuditReport(String sector, double confidence) {
        this.sector = sector;
        this.confidenceLevel = confidence;
    }
}

// ==========================================
// 2. COMPONENTES DE SOPORTE
// ==========================================

class SecurityManager {
    public String generateReportHash(Object document) {
        return "SHA-256-" + Integer.toHexString(document.hashCode());
    }
    public boolean verifyToken(String token) { return token != null; }
}

class TrafficController {
    public boolean throttle(String userId) {
        System.out.println("[TrafficController]: Verificando tasa de peticiones para " + userId);
        return true; 
    }
}

class AccountManager {
    public boolean checkAccessPermission(String resource) {
        System.out.println("[AccountManager]: Permiso concedido para " + resource);
        return true;
    }
}

// ==========================================
// 3. ESTRATEGIAS Y MOTOR (AuditEngine)
// ==========================================

interface AuditStrategy {
    void evaluate(AuditReport report);
}

class ConcreteStrategy implements AuditStrategy {
    public @Override void evaluate(AuditReport report) {
        if (report.confidenceLevel < 0.85) report.biasDetected = true;
    }
}

class AuditEngine {
    private AuditStrategy strategy;

    public void setStrategy(AuditStrategy s) { this.strategy = s; }

    public void analyzeInterference(AuditReport report) {
        System.out.println("[AuditEngine]: Ejecutando estrategia para " + report.sector);
        if (strategy != null) strategy.evaluate(report);
    }
}

// ==========================================
// 4. CADENA DE RESPONSABILIDAD (Handlers)
// ==========================================
abstract class AuditHandler {
    protected AuditHandler next;
    public void setNext(AuditHandler n) { this.next = n; }
    public void handle(AuditReport report) {
        process(report);
        if (next != null) next.handle(report);
    }
    protected abstract void process(AuditReport report);
}

class PayloadValidator extends AuditHandler {
    protected @Override void process(AuditReport report) {
        System.out.println("[Chain]: Validando Payload... ✓");
    }
}

// ==========================================
// 5. EL PROXY (SINGLETON & COORDINADOR)
// ==========================================
class Proxy implements IModelIA {
    private static Proxy instance;
    private IModelIA realService = new RealModelIA();
    private SecurityManager security = new SecurityManager();
    private TrafficController traffic = new TrafficController();
    private AccountManager account = new AccountManager();
    private AuditEngine auditEngine = new AuditEngine();
    private AuditHandler chain;

    private Proxy() {
        this.chain = new PayloadValidator(); // Iniciar cadena
        realService = new RealModelIA();
    security = new SecurityManager();
    traffic = new TrafficController();
    account = new AccountManager();
    auditEngine = new AuditEngine();
    }

    public static synchronized Proxy getInstance() {
        if (instance == null) instance = new Proxy();
        return instance;
    }

    @Override
    public String request(String inputData) {
        System.out.println("\n--- [Proxy]: Interceptando Petición ---");
        
        // 1. Validaciones del Diagrama
        if (!traffic.throttle("USER-777")) return "Error: Too many requests";
        if (!account.checkAccessPermission("IA_Model")) return "Error: Access Denied";

        // 2. Proceso de Auditoría
        AuditReport report = new AuditReport("Financial", 0.80);
        chain.handle(report);
        
        auditEngine.setStrategy(new ConcreteStrategy());
        auditEngine.analyzeInterference(report);

        // 3. Seguridad
        report.integrityHash = security.generateReportHash(report);
        System.out.println("[Security]: Hash de integridad: " + report.integrityHash);

        // 4. Redirección al Sujeto Real
        System.out.println("[Proxy]: Redirigiendo a RealModelIA...");
        return realService.request(inputData);
    }
}

// ==========================================
// 6. EJECUCIÓN
// ==========================================
public class Main {
    public static void main(String[] args) {
        // El cliente usa el Proxy como si fuera el modelo real
        IModelIA sistema = Proxy.getInstance();
        
        String respuesta = sistema.request("Analizar riesgo crediticio");
        
        System.out.println("\n[Cliente] Respuesta recibida: " + respuesta);
    }
}