# bridge/fastapi_wrapper.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from agents.scout_v2 import AletheiaScoutV2
from agents.nitpicker_v2 import AletheiaNitpickerV2
from agents.judge_v1 import AletheiaJudge
import time

app = FastAPI(title="Aletheia Core Production API")

# Singleton Instances for the Empire
scout = AletheiaScoutV2()
nitpicker = AletheiaNitpickerV2()
judge = AletheiaJudge()

class AuditRequest(BaseModel):
    payload: str
    origin: str
    action: str
    ip: str

@app.post("/v1/audit")
async def secure_audit(req: AuditRequest):
    start_time = time.time()
    
    # 1. SCOUT PHASE (Grok Pulse Sync)
    threat_score, report = scout.evaluate_threat_context(req.ip, req.payload)
    
    # 2. NITPICKER PHASE (Polymorphic Scrub)
    # We pass the origin to trigger LINEAGE or SKEPTIC modes
    clean_content = nitpicker.sanitize_intent(req.payload, req.origin)
    
    # 3. JUDGE PHASE (Hard Veto)
    is_allowed, veto_msg = judge.verify_action(req.action)
    
    # EMPIRE LOGIC: Total Block if Threat > 5.0 OR Judge Veto
    is_blocked = (threat_score >= 5.0) or (not is_allowed)
    
    latency = (time.time() - start_time) * 1000 # ms
    
    return {
        "decision": "DENIED" if is_blocked else "PROCEED",
        "metadata": {
            "threat_level": threat_score,
            "latency_ms": round(latency, 2),
            "redacted_payload": clean_content if not is_blocked else "BLOCK_ACTIVE"
        },
        "reasoning": report if threat_score >= 5.0 else veto_msg
    }
