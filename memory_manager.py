"""
Memory Manager Module for Aegis AI
==================================
Integrates the official Vectorize Hindsight Agent Memory Client (`hindsight-client`):
- Official GitHub: https://github.com/vectorize-io/hindsight
- Official Docs:   https://hindsight.vectorize.io/

Architecture:
    User Message
        ↓
    Aegis AI Assistant
        ↓
    MemoryManager
        ├── Retain: Selective retention of preferences, constraints & clinical context
        └── Recall: Multi-strategy retrieval (TEMPR) of relevant past memories
        ↓
    Context-Augmented Response
        ↓
    User

Handles:
- Configuration via environment variables (.env / os.environ)
- Official `Hindsight(base_url, api_key)` client calls (`client.retain`, `client.recall`, `client.reflect`)
- Graceful fallback to persistent local memory when remote Hindsight server is offline/unconfigured
- Audit / Debug logging for developer memory inspection
"""

import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Import official Hindsight client
try:
    from hindsight_client import Hindsight
    HINDSIGHT_CLIENT_AVAILABLE = True
except ImportError:
    HINDSIGHT_CLIENT_AVAILABLE = False
    Hindsight = None

# Local fallback storage file
LOCAL_STORAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hindsight_memory.json')


class MemoryManager:
    """
    Manages long-term agent memory for Aegis AI using Vectorize Hindsight.
    Provides fail-safe retain and recall with graceful fallback.
    """

    def __init__(self):
        self.base_url = os.environ.get("HINDSIGHT_BASE_URL", "http://localhost:8888")
        self.api_key = os.environ.get("HINDSIGHT_API_KEY", None)
        self.default_bank_id = os.environ.get("HINDSIGHT_BANK_ID", "aegis-patient-P-10021")

        self.client: Optional[Any] = None
        self.is_connected: bool = False
        self.debug_log: List[Dict[str, Any]] = []

        self._initialize_hindsight()

    def _initialize_hindsight(self):
        """Initializes connection to official Hindsight service."""
        if not HINDSIGHT_CLIENT_AVAILABLE:
            print("[MemoryManager] Notice: hindsight-client package not installed. Running in local memory fallback mode.")
            self.is_connected = False
            return

        try:
            # Instantiate official Hindsight client
            self.client = Hindsight(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=5.0
            )
            # Lightweight connectivity check
            try:
                version = self.client.get_version()
                self.is_connected = True
                print(f"[MemoryManager] Successfully connected to Hindsight server at {self.base_url} (Version: {getattr(version, 'version', 'active')})")
            except Exception as conn_err:
                self.is_connected = False
                print(f"[MemoryManager] Note: Hindsight server at {self.base_url} is not currently running ({conn_err}). "
                      f"Aegis AI will operate seamlessly in graceful fallback mode using persistent local memory.")
        except Exception as e:
            self.is_connected = False
            print(f"[MemoryManager] Initialization notice: {e}. Running with persistent local memory.")

    def get_bank_id_for_user(self, user_id: str) -> str:
        """Derives namespace bank_id for a given patient."""
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id or "default")
        return f"aegis-patient-{sanitized}"

    # ═════════════════════════════════════════════════════════════════════
    # 1. SELECTIVE RETENTION (Do not store every message blindly)
    # ═════════════════════════════════════════════════════════════════════

    def identify_useful_memory(self, message: str) -> Optional[Dict[str, str]]:
        """
        Analyzes user input to identify meaningful, demo-safe healthcare memory:
        - Patient preferences (timing, doctor, hospital)
        - Communication preferences
        - Safety notes / allergies / chronic conditions
        Filters out ephemeral greetings, thanks, or trivial dialogue.
        """
        msg = message.strip()
        msg_lower = msg.lower()

        # Ignore trivial / conversational filler
        trivial = ["hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye", "goodbye", "yes", "no"]
        if msg_lower in trivial or len(msg) < 4:
            return None

        # 1. Appointment Time Preferences (e.g., "I prefer morning appointments")
        time_match = re.search(r'(prefer|like|want|available|free)\s+(in\s+the\s+)?(morning|afternoon|evening|weekend|weekday|earlier|early|later)s?', msg_lower)
        if time_match or any(k in msg_lower for k in ["morning appointment", "morning slot", "afternoon appointment", "evening slot", "after 5pm", "before noon"]):
            if "morning" in msg_lower:
                return {"category": "preference_timing", "fact": "Patient prefers morning appointments."}
            elif "afternoon" in msg_lower:
                return {"category": "preference_timing", "fact": "Patient prefers afternoon appointments."}
            elif "evening" in msg_lower:
                return {"category": "preference_timing", "fact": "Patient prefers evening appointments."}

        # 2. Doctor & Hospital Preferences
        if any(w in msg_lower for w in ["dr.", "doctor", "hospital", "clinic", "physician", "cardiolog"]):
            doc_match = re.search(r'(dr\.?\s+[a-zA-Z]+)', msg, re.IGNORECASE)
            hosp_match = re.search(r'([a-zA-Z\s]+hospital)', msg, re.IGNORECASE)
            fact_parts = []
            if doc_match:
                fact_parts.append(f"preferred doctor {doc_match.group(1).title()}")
            if hosp_match:
                fact_parts.append(f"preferred facility {hosp_match.group(1).strip().title()}")
            if fact_parts:
                return {"category": "preference_provider", "fact": f"Patient preference: {', '.join(fact_parts)}."}

        # 3. Communication Preferences
        if any(w in msg_lower for w in ["detailed", "concise", "brief", "sms", "email", "whatsapp", "call me"]):
            if "detail" in msg_lower:
                return {"category": "preference_communication", "fact": "Patient prefers detailed clinical explanations."}
            elif "brief" in msg_lower or "concise" in msg_lower:
                return {"category": "preference_communication", "fact": "Patient prefers concise, brief summaries."}

        # 4. Medical Safety & Allergies
        if any(w in msg_lower for w in ["allergic", "allergy", "penicillin", "aspirin", "sulfa"]):
            match = re.search(r'allergic to\s+([a-zA-Z\s]+)', msg_lower)
            allergen = match.group(1).strip().title() if match else "Penicillin"
            return {"category": "medical_safety", "fact": f"Medical Safety: Documented allergy to {allergen}."}

        # 5. Symptom Timeline Reports
        if any(w in msg_lower for w in ["chest tightness", "pain", "headache", "fever", "cough", "pressure"]):
            return {"category": "clinical_history", "fact": f"Clinical Report: Patient reported '{msg}'."}

        return None

    # ═════════════════════════════════════════════════════════════════════
    # 2. RETAIN MEMORY
    # ═════════════════════════════════════════════════════════════════════

    def retain_memory(
        self,
        bank_id: str,
        content: str,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Stores important facts into Hindsight agent memory.
        Uses official `client.retain(bank_id=..., content=...)` when connected,
        and synchronizes with local storage.
        """
        timestamp = datetime.now().isoformat()
        record = {
            "bank_id": bank_id,
            "content": content,
            "context": context,
            "metadata": metadata or {},
            "timestamp": timestamp,
            "backend": "hindsight_remote" if self.is_connected else "hindsight_local_fallback"
        }

        # 1. Official Hindsight Client Retain
        if self.is_connected and self.client:
            try:
                response = self.client.retain(
                    bank_id=bank_id,
                    content=content,
                    context=context,
                    metadata=metadata
                )
                record["hindsight_response"] = str(response)
            except Exception as e:
                print(f"[MemoryManager] Remote retain error: {e}. Falling back to local store.")

        # 2. Local Fallback Sync
        try:
            import hindsight
            # Parse user_id from bank_id (e.g. aegis-patient-P-10021 -> P-10021)
            user_id = bank_id.replace("aegis-patient-", "") if "aegis-patient-" in bank_id else bank_id
            user = hindsight.hindsight.get_or_create_user(user_id)
            user.setdefault("hindsight_facts", []).append({
                "timestamp": timestamp,
                "fact": content,
                "category": (metadata or {}).get("category", "general")
            })
            hindsight.hindsight.save()
        except Exception as e:
            print(f"[MemoryManager] Local sync note: {e}")

        # Record for debug view
        self.debug_log.append({
            "action": "retain",
            "bank_id": bank_id,
            "content": content,
            "timestamp": timestamp,
            "status": "success"
        })

        return {"status": "success", "record": record}

    # ═════════════════════════════════════════════════════════════════════
    # 3. RECALL MEMORY
    # ═════════════════════════════════════════════════════════════════════

    def recall_memory(
        self,
        bank_id: str,
        query: str,
        types: Optional[List[str]] = None,
        max_tokens: int = 4096
    ) -> List[Dict[str, Any]]:
        """
        Retrieves relevant memories for a user query.
        Uses official `client.recall(bank_id=..., query=...)` when connected.
        """
        timestamp = datetime.now().isoformat()
        results: List[Dict[str, Any]] = []

        # 1. Official Hindsight Client Recall
        if self.is_connected and self.client:
            try:
                response = self.client.recall(
                    bank_id=bank_id,
                    query=query,
                    max_tokens=max_tokens
                )
                if hasattr(response, "results") and response.results:
                    for res in response.results:
                        results.append({
                            "text": getattr(res, "text", str(res)),
                            "type": getattr(res, "type", "memory"),
                            "score": getattr(res, "score", 1.0)
                        })
                elif hasattr(response, "to_prompt_string"):
                    results.append({"text": response.to_prompt_string(), "type": "prompt_context", "score": 1.0})
            except Exception as e:
                print(f"[MemoryManager] Remote recall error: {e}. Falling back to local recall.")

        # 2. Local Fallback Recall (keyword & semantic relevance)
        if not results:
            results = self._local_recall(bank_id, query)

        # Record for debug view
        self.debug_log.append({
            "action": "recall",
            "bank_id": bank_id,
            "query": query,
            "recalled_count": len(results),
            "timestamp": timestamp
        })

        return results

    def _local_recall(self, bank_id: str, query: str) -> List[Dict[str, Any]]:
        """Fallback local retrieval matching against patient memory bank."""
        user_id = bank_id.replace("aegis-patient-", "") if "aegis-patient-" in bank_id else bank_id
        q_lower = query.lower()
        recalled = []

        try:
            import hindsight
            user = hindsight.hindsight.get_or_create_user(user_id)
            prefs = user.get("preferences", {})
            hp = user.get("health_profile", {})

            # 1. Timing & Appointment preferences
            if any(w in q_lower for w in ["book", "appointment", "schedule", "when", "time", "morning", "slot", "visit"]):
                if prefs.get("preferred_time"):
                    recalled.append({
                        "text": f"Patient previously preferred: {prefs['preferred_time']}.",
                        "type": "preference_timing",
                        "score": 0.95
                    })
                if prefs.get("doctor"):
                    recalled.append({
                        "text": f"Preferred physician: {prefs['doctor']} ({prefs.get('department', 'General')}) at {prefs.get('hospital', 'City Hospital')}.",
                        "type": "preference_provider",
                        "score": 0.90
                    })

            # 2. Explicit Hindsight facts retained
            facts = user.get("hindsight_facts", [])
            for item in facts:
                fact_text = item.get("fact", "")
                overlap = set(q_lower.split()) & set(fact_text.lower().split())
                if overlap or any(k in q_lower for k in ["preference", "remember", "history", "appointment", "book"]):
                    recalled.append({
                        "text": fact_text,
                        "type": item.get("category", "retained_fact"),
                        "score": 0.85
                    })

            # 3. Allergies & Contraindications
            if any(w in q_lower for w in ["amoxicillin", "penicillin", "augmentin", "antibiotic", "allergy"]):
                for allergy in hp.get("allergies", []):
                    recalled.append({
                        "text": f"Allergy Alert: {allergy}",
                        "type": "medical_safety",
                        "score": 1.0
                    })

            # 4. Recent multi-day symptoms
            if any(w in q_lower for w in ["chest", "tightness", "still", "persisting", "last conversation"]):
                for sym in hp.get("symptoms_history", []):
                    recalled.append({
                        "text": f"Symptom History: {sym.get('symptom')}",
                        "type": "clinical_history",
                        "score": 0.92
                    })

        except Exception as e:
            print(f"[MemoryManager] Local recall parsing note: {e}")

        return recalled

    # ═════════════════════════════════════════════════════════════════════
    # 4. GET RELEVANT MEMORY (Formatted for AI prompt injection)
    # ═════════════════════════════════════════════════════════════════════

    def get_relevant_memory(self, bank_id: str, query: str) -> str:
        """
        Retrieves relevant memories and formats them into an AI prompt context block.
        """
        memories = self.recall_memory(bank_id, query)
        if not memories:
            return ""

        lines = [f"- {m['text']}" for m in memories]
        return "\n".join(lines)

    # ═════════════════════════════════════════════════════════════════════
    # 5. DEBUG & AUDIT LOGS
    # ═════════════════════════════════════════════════════════════════════

    def get_debug_trail(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Returns recent memory operations for the developer/debug view."""
        return self.debug_log[-limit:]


# Global singleton instance
memory_manager = MemoryManager()
