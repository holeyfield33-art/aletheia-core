# SDK Integration Guide — Aletheia Core v1.9.2

How to call the Aletheia Core audit API from your application code.

---

## Prerequisites

- A running Aletheia Core instance (self-hosted or hosted API)
- An API key (created via `POST /v1/keys` with RBAC admin credentials)
- Base URL of your deployment (e.g. `https://your-app.onrender.com`)

---

## Python

### Using `httpx` (recommended)

```python
import httpx

ALETHEIA_URL = "https://your-app.onrender.com"
API_KEY = "your-api-key"


def audit_action(payload: str, origin: str, action: str) -> dict:
    """Send an action through the Aletheia audit pipeline.

    Returns the full response dict including decision and receipt.
    Raises httpx.HTTPStatusError on 4xx/5xx responses.
    """
    response = httpx.post(
        f"{ALETHEIA_URL}/v1/audit",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        },
        json={
            "payload": payload,
            "origin": origin,
            "action": action,
        },
        timeout=10.0,
    )
    response.raise_for_status()
    return response.json()


# Usage
result = audit_action(
    payload="Summarize Q4 financial report",
    origin="agent-finance",
    action="Read_Report",
)

if result["decision"] == "PROCEED":
    print("Action allowed — execute downstream logic")
    print(f"Receipt signature: {result['receipt']['signature']}")
else:
    print(f"Action blocked: {result.get('reason', 'policy violation')}")
```

### Using `requests`

```python
import requests

ALETHEIA_URL = "https://your-app.onrender.com"
API_KEY = "your-api-key"


def audit_action(payload: str, origin: str, action: str) -> dict:
    response = requests.post(
        f"{ALETHEIA_URL}/v1/audit",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        },
        json={
            "payload": payload,
            "origin": origin,
            "action": action,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()
```

### Async Python (httpx)

```python
import httpx


async def audit_action_async(payload: str, origin: str, action: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{ALETHEIA_URL}/v1/audit",
            headers={
                "Content-Type": "application/json",
                "X-API-Key": API_KEY,
            },
            json={
                "payload": payload,
                "origin": origin,
                "action": action,
            },
        )
        response.raise_for_status()
        return response.json()
```

---

## Node.js / TypeScript

### Using `fetch` (Node 18+)

```typescript
const ALETHEIA_URL = "https://your-app.onrender.com";
const API_KEY = "your-api-key";

interface AuditResult {
  decision: "PROCEED" | "DENIED" | "SANDBOX_BLOCKED" | "RATE_LIMITED";
  metadata: {
    threat_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
    latency_ms: number;
    request_id: string;
    client_id: string;
  };
  receipt: {
    decision: string;
    policy_hash: string;
    payload_sha256: string;
    action: string;
    origin: string;
    signature: string;
    issued_at: string;
  };
  reason?: string;
}

async function auditAction(
  payload: string,
  origin: string,
  action: string,
): Promise<AuditResult> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10_000);

  try {
    const response = await fetch(`${ALETHEIA_URL}/v1/audit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify({ payload, origin, action }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(
        `Audit failed: ${response.status} ${JSON.stringify(body)}`,
      );
    }

    return (await response.json()) as AuditResult;
  } finally {
    clearTimeout(timeoutId);
  }
}

// Usage
const result = await auditAction(
  "Summarize Q4 financial report",
  "agent-finance",
  "Read_Report",
);

if (result.decision === "PROCEED") {
  console.log("Action allowed");
} else {
  console.log(`Action blocked: ${result.reason}`);
}
```

---

## Go

```go
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

const (
	aletheiaURL = "https://your-app.onrender.com"
	apiKey      = "your-api-key"
)

type AuditRequest struct {
	Payload string `json:"payload"`
	Origin  string `json:"origin"`
	Action  string `json:"action"`
}

type AuditResult struct {
	Decision string                 `json:"decision"`
	Metadata map[string]interface{} `json:"metadata"`
	Receipt  map[string]interface{} `json:"receipt"`
	Reason   string                 `json:"reason,omitempty"`
}

func auditAction(payload, origin, action string) (*AuditResult, error) {
	body, _ := json.Marshal(AuditRequest{
		Payload: payload,
		Origin:  origin,
		Action:  action,
	})

	req, err := http.NewRequest("POST", aletheiaURL+"/v1/audit", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-Key", apiKey)

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	respBody, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("audit failed: %d %s", resp.StatusCode, string(respBody))
	}

	var result AuditResult
	if err := json.Unmarshal(respBody, &result); err != nil {
		return nil, err
	}
	return &result, nil
}

func main() {
	result, err := auditAction(
		"Summarize Q4 financial report",
		"agent-finance",
		"Read_Report",
	)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	fmt.Printf("Decision: %s\n", result.Decision)
}
```

---

## cURL

```bash
# Basic audit request
curl -X POST https://your-app.onrender.com/v1/audit \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ALETHEIA_API_KEY" \
  -d '{"payload":"Summarize Q4 report","origin":"agent-01","action":"Read_Report"}'

# Health check
curl https://your-app.onrender.com/health

# Readiness check
curl https://your-app.onrender.com/ready

# Rotate secrets (admin — requires SECRETS_ROTATE permission)
curl -X POST https://your-app.onrender.com/v1/rotate \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Create API key (admin)
curl -X POST https://your-app.onrender.com/v1/keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"name":"my-agent","plan":"trial"}'
```

---

## Integration Patterns

### Pre-execution gate

Call `/v1/audit` before every agent action. Only proceed if `decision == "PROCEED"`.

```python
result = audit_action(payload=agent_instruction, origin="my-agent", action=action_id)
if result["decision"] != "PROCEED":
    raise PermissionError(f"Action blocked by Aletheia: {result.get('reason')}")
# ... proceed with execution
```

### Receipt verification

Store the `receipt` object from every response. The HMAC signature binds the decision to the policy hash and payload fingerprint — use it to prove that a specific action was evaluated before execution.

### Handling rate limits

```python
import time

result = audit_action(...)
if result.get("decision") == "RATE_LIMITED":
    retry_after = int(response.headers.get("Retry-After", 5))
    time.sleep(retry_after)
    result = audit_action(...)  # retry
```

### Health check integration

Poll `/health` or `/ready` from your orchestrator. If `status` is `degraded` or `ready` is `false`, consider pausing agent actions or routing to a fallback.
