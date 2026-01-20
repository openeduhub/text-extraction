# API-Dokumentation: text-extraction

## Übersicht

Die **text-extraction** API ist eine RESTful API zur Extraktion von Textinhalten aus URLs. Sie bietet zwei Hauptendpunkte: einen Health Check und einen Textextraktions-Endpunkt mit verschiedenen Extraktionsmethoden und Ausgabeformaten.

**Base URL:** `http://<host>:8000`  
**API Version:** 0.3.0  
**Content-Type:** `application/json`

---

## Authentifizierung

Die API benötigt **keine Authentifizierung**.

---

## Endpunkte

### 1. Health Check

#### `GET /_ping`

Überprüft den Status des Services und gibt Versionsinformationen zurück.

**Verwendung:** Für Liveness und Readiness Probes in Kubernetes

**Request:**
```bash
curl -X GET http://localhost:8000/_ping
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "version": "0.3.0",
  "timestamp": "2026-01-20T08:46:27.123456"
}
```

**Response-Felder:**
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `status` | string | Status des Services ("ok") |
| `version` | string | Versionsnummer des Services |
| `timestamp` | string | ISO 8601 Zeitstempel der Anfrage |

**HTTP Status Codes:**
- `200 OK` - Service läuft normal

---

### 2. Text-Extraktion

#### `POST /from-url`

Extrahiert Textinhalte aus einer gegebenen URL.

**Request:**
```bash
curl -X POST http://localhost:8000/from-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "method": "simple",
    "output_format": "txt",
    "lang": "auto",
    "preference": "none"
  }'
```

**Request-Body (JSON):**

| Parameter | Typ | Erforderlich | Standard | Beschreibung |
|-----------|-----|-------------|----------|-------------|
| `url` | string | ✅ Ja | - | Die URL, von der Text extrahiert werden soll |
| `method` | string | ❌ Nein | "simple" | Extraktionsmethode: `"simple"` oder `"browser"` |
| `output_format` | string | ❌ Nein | "txt" | Ausgabeformat: `"txt"`, `"markdown"` oder `"html"` |
| `lang` | string | ❌ Nein | "auto" | ISO 639-1 Sprachcode (z.B. "de", "en") oder `"auto"` für automatische Erkennung |
| `preference` | string | ❌ Nein | "none" | Extraktions-Präferenz: `"none"`, `"precision"` oder `"recall"` |
| `browser_location` | string | ❌ Nein | null | CDP-Endpoint für externe Browser-Instanz (nur bei `method: "browser"`) |

#### Parameter-Details

**`method`**
- `"simple"` - Schnelle HTML-Extraktion mit trafilatura (Standard)
  - Geeignet für: Statische Websites, schnelle Verarbeitung
  - Durchschnittliche Antwortzeit: 200-500ms
  - Speicherverbrauch: Niedrig
  
- `"browser"` - Headless Browser-basierte Extraktion mit Playwright
  - Geeignet für: JavaScript-lastige Websites, komplexe Layouts
  - Durchschnittliche Antwortzeit: 2-5 Sekunden
  - Speicherverbrauch: Höher (~100-150 MB pro Instanz)

**`output_format`**
- `"txt"` - Reiner Text (via trafilatura)
  - Ausgabe: Bereinigter Text ohne Formatierung
  
- `"markdown"` - Markdown-formatierter Text (via MarkItDown)
  - Ausgabe: Text mit Markdown-Formatierung (Überschriften, Listen, Links, etc.)
  
- `"html"` - Bereinigtes HTML (via trafilatura)
  - Ausgabe: Strukturiertes HTML mit entferntem Rauschen

**`lang`**
- `"auto"` - Automatische Spracherkennung
  - Der Service erkennt die Sprache des extrahierten Textes
  
- ISO 639-1 Code (z.B. `"de"`, `"en"`, `"fr"`)
  - Explizite Sprachvorgabe
  - Wird für Sprachfilterung verwendet

**`preference`**
- `"none"` - Keine spezielle Präferenz (Standard)
  
- `"precision"` - Höhere Genauigkeit, weniger Text
  - Extrahiert nur hochrelevante Inhalte
  
- `"recall"` - Höhere Vollständigkeit, mehr Text
  - Versucht, mehr Inhalte zu extrahieren

**`browser_location`**
- `null` - Startet eine neue Browser-Instanz (Standard)
  
- CDP-Endpoint URL (z.B. `"http://browser-service:3222"`)
  - Verbindet sich mit einer externen Browser-Instanz
  - Nützlich für Ressourcen-Optimierung bei vielen gleichzeitigen Anfragen

---

## Response-Formate

### Erfolgreiche Extraktion (200 OK)

```json
{
  "text": "Dies ist der extrahierte Text aus der Website...",
  "lang": "de",
  "status": 200,
  "version": "0.3.0"
}
```

**Response-Felder:**
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `text` | string | Der extrahierte Textinhalt |
| `lang` | string | Die erkannte oder angegebene Sprache (ISO 639-1 Code) |
| `status` | integer | HTTP Status Code der Zielwebsite |
| `version` | string | Versionsnummer des Services |

---

### Fehlgeschlagene Extraktion (424 Failed Dependency)

```json
{
  "error_message": "No content was extracted. This could be due to no text being present on the page, the website relying on JavaScript, or because the language was not successfully detected. Try setting the lang parameter.",
  "status": 404,
  "reason": "Not Found",
  "version": "0.3.0",
  "content": "<html>...</html>"
}
```

**Response-Felder:**
| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `error_message` | string | Detaillierte Fehlermeldung |
| `status` | integer | HTTP Status Code der Zielwebsite (falls verfügbar) |
| `reason` | string | HTTP Reason Phrase der Zielwebsite (falls verfügbar) |
| `version` | string | Versionsnummer des Services |
| `content` | string | Der Response-Inhalt der Zielwebsite (falls verfügbar) |

---

## HTTP Status Codes

| Code | Beschreibung |
|------|-------------|
| `200 OK` | Textextraktion erfolgreich |
| `424 Failed Dependency` | Textextraktion fehlgeschlagen (keine Inhalte extrahiert) |
| `422 Unprocessable Entity` | Ungültige Request-Parameter |
| `500 Internal Server Error` | Interner Fehler des Services |

---

## Fehlerbehandlung

### Häufige Fehlerszenarien

**1. Ungültige URL**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "url"],
      "msg": "Invalid URL format",
      "input": "not-a-url"
    }
  ]
}
```
**Lösung:** Stelle sicher, dass die URL mit `http://` oder `https://` beginnt.

---

**2. Website nicht erreichbar**
```json
{
  "error_message": "No content was extracted. This could be due to no text being present on the page, the website relying on JavaScript, or because the website returned an error status code 404.",
  "status": 404,
  "reason": "Not Found",
  "version": "0.3.0",
  "content": null
}
```
**Lösung:** Überprüfe, ob die URL korrekt ist und die Website erreichbar ist.

---

**3. Spracherkennung fehlgeschlagen**
```json
{
  "error_message": "No content was extracted. This could be due to no text being present on the page, the website relying on JavaScript, or because the language was not successfully detected. Try setting the lang parameter.",
  "status": 200,
  "reason": null,
  "version": "0.3.0",
  "content": null
}
```
**Lösung:** Setze den `lang` Parameter explizit auf die Sprache der Website.

---

**4. Browser-Fehler**
```json
{
  "error_message": "No content was extracted. This could be due to no text being present on the page, the website relying on JavaScript, or because the website returned an error status code 500.",
  "status": 500,
  "reason": "Internal Server Error",
  "version": "0.3.0",
  "content": null
}
```
**Lösung:** Versuche die `simple` Methode oder überprüfe die Browser-Konfiguration.

---

## Verwendungsbeispiele

### Beispiel 1: Einfache Textextraktion

```bash
curl -X POST http://localhost:8000/from-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.example.com"
  }'
```

**Response:**
```json
{
  "text": "Example Domain\n\nThis domain is for use in examples and documentation...",
  "lang": "en",
  "status": 200,
  "version": "0.3.0"
}
```

---

### Beispiel 2: Markdown-Ausgabe mit Spracherkennung

```bash
curl -X POST http://localhost:8000/from-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.wikipedia.org/wiki/Python",
    "output_format": "markdown",
    "lang": "auto"
  }'
```

**Response:**
```json
{
  "text": "# Python\n\n**Python** is a high-level, general-purpose programming language...\n\n## History\n\nPython was created in 1989...",
  "lang": "en",
  "status": 200,
  "version": "0.3.0"
}
```

---

### Beispiel 3: Browser-Methode für JavaScript-lastige Website

```bash
curl -X POST http://localhost:8000/from-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.example-spa.com",
    "method": "browser",
    "output_format": "txt",
    "lang": "de"
  }'
```

**Response:**
```json
{
  "text": "Dynamischer Inhalt, der nur mit JavaScript geladen wird...",
  "lang": "de",
  "status": 200,
  "version": "0.3.0"
}
```

---

### Beispiel 4: Externe Browser-Instanz

```bash
curl -X POST http://localhost:8000/from-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.example.com",
    "method": "browser",
    "browser_location": "http://browser-service:3222"
  }'
```

---

### Beispiel 5: Precision-Präferenz

```bash
curl -X POST http://localhost:8000/from-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.example.com",
    "preference": "precision"
  }'
```

---

## Rate Limiting

Der Service selbst implementiert kein Rate Limiting.

---

## Performance-Tipps

### Optimale Konfiguration nach Anwendungsfall

**Schnelle Extraktion (Priorität: Geschwindigkeit)**
```json
{
  "url": "https://example.com",
  "method": "simple",
  "output_format": "txt",
  "lang": "auto"
}
```
- Durchschnittliche Antwortzeit: 200-500ms
- Speicherverbrauch: Niedrig

---

**Hohe Qualität (Priorität: Genauigkeit)**
```json
{
  "url": "https://example.com",
  "method": "browser",
  "output_format": "markdown",
  "lang": "auto",
  "preference": "precision"
}
```
- Durchschnittliche Antwortzeit: 2-5 Sekunden
- Speicherverbrauch: Höher
- Bessere Extraktion von JavaScript-Inhalten

---

**Maximale Vollständigkeit (Priorität: Umfang)**
```json
{
  "url": "https://example.com",
  "method": "browser",
  "output_format": "markdown",
  "lang": "auto",
  "preference": "recall"
}
```
- Durchschnittliche Antwortzeit: 2-5 Sekunden
- Speicherverbrauch: Höher
- Versucht, mehr Inhalte zu extrahieren

---

## Swagger/OpenAPI Dokumentation

**URL:** `http://<host>:8000/docs`