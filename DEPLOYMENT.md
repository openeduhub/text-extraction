# Technische Deployment-Dokumentation: text-extraction

## Übersicht

**text-extraction** ist ein Microservice zur Extraktion von Textinhalten aus URLs. Der Service nutzt [trafilatura](https://github.com/adbar/trafilatura) für einfache HTML-Extraktion und [MarkItDown](https://github.com/microsoft/markitdown) für erweiterte Formatierungen. Für JavaScript-lastige Websites wird ein Headless Browser (Chromium via Playwright) eingesetzt.

**Version:** 0.3.0  
**Sprache:** Python 3.13  
**Framework:** FastAPI  
**Server:** Uvicorn

---

## Abhängigkeiten und Anforderungen

### Externe Abhängigkeiten
- **Keine** - Der Service ist vollständig eigenständig
- Alle Abhängigkeiten sind in der `pyproject.toml` definiert und werden beim Build installiert

### Interne Abhängigkeiten
- **Playwright/Chromium:** Wird automatisch installiert, benötigt aber Systemlibraries
  - Auf Linux: `libglib2.0-0`, `libx11-6`, `libxrandr2`, etc.
  - Das bereitgestellte Docker-Image basiert auf `ghcr.io/astral-sh/uv:python3.13-bookworm-slim` und enthält alle notwendigen Abhängigkeiten

### Netzwerk-Anforderungen
- **Inbound:** Port 8000 (HTTP)
- **Outbound:** HTTP/HTTPS zu beliebigen URLs (für Textextraktion)
- **Keine** Datenbankverbindungen erforderlich

---

## Konfiguration und Umgebungsvariablen

### Kommandozeilen-Parameter

Der Service wird über folgende Parameter konfiguriert:

```bash
uv run text-extraction [OPTIONS]
```

| Parameter | Standard | Beschreibung |
|-----------|----------|-------------|
| `--port` | 8000 | Port, auf dem der Service lauscht |
| `--host` | 0.0.0.0 | Host-Adresse zum Binden (0.0.0.0 für alle Interfaces) |
| `--lang` | de_DE | Standard-Sprache für Spracherkennung |
| `--version` | - | Zeigt die Versionsnummer an |

### Beispiel für Kubernetes-Deployment

```yaml
containers:
- name: text-extraction
  image: text-extraction:0.3.0
  args:
    - "uv"
    - "run"
    - "text-extraction"
    - "--host"
    - "0.0.0.0"
    - "--port"
    - "8000"
  ports:
  - containerPort: 8000
    name: http
```

---

## Performance-Charakteristiken

### Durchsatzleistung

| Szenario | Durchschnittliche Antwortzeit | Durchsatz |
|----------|-------------------------------|-----------|
| Einfache HTML-Extraktion (simple) | 200-500ms | ~2-5 Anfragen/Sekunde |
| Browser-basierte Extraktion (browser) | 2-5 Sekunden | ~0.2-0.5 Anfragen/Sekunde |
| Health Check (`/_ping`) | <10ms | >100 Anfragen/Sekunde |

---

## Sicherheitsaspekte

### Eingabe-Validierung
- **URL-Validierung:** Alle URLs werden validiert, bevor sie verarbeitet werden
- **Timeout-Schutz:** Anfragen haben implizite Timeouts
- **Rate Limiting:** Kann über die Python-API implementiert werden (siehe README.md)

### Netzwerk-Sicherheit
- **Keine Authentifizierung:** Der Service hat keine eingebaute Authentifizierung
- **HTTPS:** Wird nicht vom Service selbst bereitgestellt

### Datenschutz
- **Keine Datenspeicherung:** Der Service speichert keine Anfragen oder Ergebnisse
- **Durchlaufverkehr:** Alle Daten werden in-Memory verarbeitet und nicht persistiert
- **Externe URLs:** Der Service greift auf beliebige URLs zu - stelle sicher, dass dies in deiner Umgebung erlaubt ist

---

## Deployment auf Kubernetes

### Voraussetzungen
- Kubernetes Cluster (1.20+)
- Docker Registry mit dem text-extraction Image
- kubectl konfiguriert

### Basis-Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: text-extraction
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: text-extraction
  template:
    metadata:
      labels:
        app: text-extraction
    spec:
      containers:
      - name: text-extraction
        image: your-registry/text-extraction:0.3.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: http
        args:
          - "uv"
          - "run"
          - "text-extraction"
          - "--host"
          - "0.0.0.0"
          - "--port"
          - "8000"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /_ping
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /_ping
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 2
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
          readOnlyRootFilesystem: true
          allowPrivilegeEscalation: false
          capabilities:
            drop:
              - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        emptyDir: {}
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: text-extraction
  namespace: default
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
  selector:
    app: text-extraction
```

### Ingress (mit HTTPS)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: text-extraction
  namespace: default
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - text-extraction.example.com
    secretName: text-extraction-tls
  rules:
  - host: text-extraction.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: text-extraction
            port:
              number: 80
```

---

## Monitoring und Logging

### Health Check Endpoint

Der Service stellt einen Health Check Endpoint bereit:

```
GET /_ping
```

**Response:**
```json
{
  "status": "ok",
  "version": "0.3.0",
  "timestamp": "2026-01-20T08:46:27.123456"
}
```

### Logging

Der Service nutzt `loguru` für strukturiertes Logging. Logs werden auf `stdout` ausgegeben und können von Kubernetes gesammelt werden.

**Empfohlene Logging-Konfiguration:**
- Nutze einen Log Aggregator (ELK Stack, Loki, Splunk, etc.)
- Setze Log Level auf `INFO` für Produktion
- Überwache auf Fehler und Timeouts

### Metriken

Der Service exponiert keine Prometheus-Metriken nativ. Für Monitoring empfehlen wir:
- **Request-Latenz:** Über Ingress/Load Balancer Logs
- **Error Rate:** Über Application Logs
- **Resource Usage:** Über Kubernetes Metrics Server

---

## Troubleshooting

### Service startet nicht
- **Symptom:** Pod bleibt in `CrashLoopBackOff`
- **Lösung:** Überprüfe Logs mit `kubectl logs <pod-name>`
- **Häufige Ursachen:**
  - Ungültige Kommandozeilen-Parameter
  - Fehlende Systemlibraries für Playwright

### Hohe Speichernutzung
- **Symptom:** Pod wird wegen OOMKilled beendet
- **Lösung:** Erhöhe Memory Limits oder reduziere Anzahl gleichzeitiger Browser-Instanzen
- **Ursache:** Browser-Methode verbraucht mehr Speicher als Simple-Methode

### Timeouts bei URL-Extraktion
- **Symptom:** Anfragen schlagen fehl oder dauern sehr lange
- **Lösung:** Überprüfe Netzwerk-Konnektivität und Firewall-Regeln
- **Ursache:** Zielwebsite ist langsam oder nicht erreichbar

### Browser-Fehler
- **Symptom:** Fehler bei Browser-Methode
- **Lösung:** Stelle sicher, dass Chromium-Abhängigkeiten installiert sind
- **Ursache:** Fehlende Systemlibraries oder Sandbox-Probleme

