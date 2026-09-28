"""
Hindsight Memory Engine for Aegis AI
====================================
Implements persistent, long-term memory architecture for AI agents:
1. Retain: Captures experiences, conversations, preferences, and health facts.
2. Recall: Retrieves relevant memory banks using semantic/keyword scoring.
3. Reflect: Synthesizes patterns, infers habits, assesses risks, and formulates proactive insights.
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ensure standard output can print Unicode characters on Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hindsight_memory.json')

DEFAULT_MEMORY = {
    "P-10021": {
        "user_id": "P-10021",
        "phone": "9440047837",
        "name": "Test User",
        "created_at": "2026-01-15T09:00:00",
        "stats": {
            "login_count": 6,
            "last_login": "2026-09-28T17:45:00",
            "total_appointments": 1,
            "total_interactions": 14
        },
        "preferences": {
            "hospital": "City Hospital",
            "doctor": "Dr. Smith",
            "department": "Cardiology",
            "preferred_time": "Morning (10:00 AM)",
            "communication_preference": "Detailed clinical explanations"
        },
        "health_profile": {
            "conditions": ["Mild Hypertension (diagnosed Jan 2026)"],
            "allergies": ["Penicillin (severe hives / anaphylaxis risk)"],
            "medications": ["Metformin 500mg daily", "Lisinopril 10mg"],
            "symptoms_history": [
                {"date": "2026-09-25T14:30:00", "symptom": "Mild chest tightness after climbing stairs", "status": "monitoring"}
            ]
        },
        "conversations": [
            {
                "timestamp": "2026-09-25T14:30:00",
                "role": "user",
                "message": "I felt some mild chest tightness after climbing stairs today."
            },
            {
                "timestamp": "2026-09-25T14:31:00",
                "role": "assistant",
                "message": "I've noted your mild chest tightness after exertion. Given your mild hypertension, please rest and monitor for 48-72 hours. If it recurs or radiates to your arm/jaw, seek urgent medical care."
            }
        ],
        "interactions": [
            {"timestamp": "2026-03-05T10:00:00", "type": "appointment", "summary": "Routine Checkup with Dr. Smith at City Hospital (Cardiology)"},
            {"timestamp": "2026-05-18T14:43:00", "type": "portal_login", "summary": "Patient accessed health portal"},
            {"timestamp": "2026-09-25T14:30:00", "type": "consultation", "summary": "Reported chest tightness symptom"}
        ]
    }
}


class HindsightMemoryEngine:
    def __init__(self, storage_path: str = MEMORY_FILE):
        self.storage_path = storage_path
        self.memory_banks: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self):
        """Loads persistent memories from disk or initializes defaults."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.memory_banks = json.load(f)
                    return
            except Exception as e:
                print(f"[Hindsight] Warning: Could not read {self.storage_path}: {e}")
        # Initialize with default memory bank
        self.memory_banks = json.loads(json.dumps(DEFAULT_MEMORY))
        self.save()

    def save(self):
        """Persists memory banks to disk."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory_banks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Hindsight] Error saving memory: {e}")

    def get_or_create_user(self, user_id: str, name: str = "Patient", phone: str = "") -> Dict[str, Any]:
        if user_id not in self.memory_banks:
            self.memory_banks[user_id] = {
                "user_id": user_id,
                "phone": phone,
                "name": name,
                "created_at": datetime.now().isoformat(),
                "stats": {
                    "login_count": 1,
                    "last_login": datetime.now().isoformat(),
                    "total_appointments": 0,
                    "total_interactions": 1
                },
                "preferences": {},
                "health_profile": {
                    "conditions": [],
                    "allergies": [],
                    "medications": [],
                    "symptoms_history": []
                },
                "conversations": [],
                "interactions": [
                    {"timestamp": datetime.now().isoformat(), "type": "account_created", "summary": f"Account initialized for {name}"}
                ]
            }
            self.save()
        return self.memory_banks[user_id]

    # ═════════════════════════════════════════════════════════════════════
    # 1. RETAIN: Storing experiences, preferences, and observations
    # ═════════════════════════════════════════════════════════════════════

    def retain_login(self, user_id: str, name: Optional[str] = None):
        """Retains user login interaction and updates visit counters."""
        user = self.get_or_create_user(user_id, name=name or "Patient")
        user["stats"]["login_count"] = user["stats"].get("login_count", 0) + 1
        user["stats"]["last_login"] = datetime.now().isoformat()
        user["stats"]["total_interactions"] = user["stats"].get("total_interactions", 0) + 1
        user["interactions"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "portal_login",
            "summary": f"Login #{user['stats']['login_count']}"
        })
        self.save()

    def retain_preference(self, user_id: str, key: str, value: str):
        """Retains a patient preference."""
        user = self.get_or_create_user(user_id)
        user["preferences"][key] = value
        user["stats"]["total_interactions"] = user["stats"].get("total_interactions", 0) + 1
        self.save()

    def retain_health_info(self, user_id: str, info_type: str, value: str) -> bool:
        """Retains condition, allergy, medication, or symptom."""
        user = self.get_or_create_user(user_id)
        hp = user["health_profile"]

        type_map = {
            "condition": "conditions",
            "allergy": "allergies",
            "medication": "medications",
            "symptom": "symptoms_history"
        }
        category = type_map.get(info_type.lower(), "conditions")

        if category == "symptoms_history":
            hp[category].append({
                "date": datetime.now().isoformat(),
                "symptom": value,
                "status": "active"
            })
        else:
            if value not in hp[category]:
                hp[category].append(value)

        user["interactions"].append({
            "timestamp": datetime.now().isoformat(),
            "type": f"health_{info_type}",
            "summary": f"Added {info_type}: {value}"
        })
        self.save()
        return True

    def retain_appointment(self, user_id: str, appt: Dict[str, Any]):
        """Learns and reflects preferences whenever an appointment is booked."""
        user = self.get_or_create_user(user_id)
        user["stats"]["total_appointments"] = user["stats"].get("total_appointments", 0) + 1

        # Automatically learn preferred hospital, doctor, dept
        if appt.get("hospital"):
            user["preferences"]["hospital"] = appt["hospital"]
        if appt.get("doctor"):
            user["preferences"]["doctor"] = appt["doctor"]
        if appt.get("dept"):
            user["preferences"]["department"] = appt["dept"]

        # Learn timing habit (e.g. Morning / Afternoon / Evening)
        timing = appt.get("timing", "")
        if "T" in timing:
            try:
                time_str = timing.split("T")[1]
                hour = int(time_str.split(":")[0])
                if hour < 12:
                    user["preferences"]["preferred_time"] = f"Morning ({time_str})"
                elif hour < 17:
                    user["preferences"]["preferred_time"] = f"Afternoon ({time_str})"
                else:
                    user["preferences"]["preferred_time"] = f"Evening ({time_str})"
            except Exception:
                pass

        # Retain issue if notable
        issue = appt.get("issue", "")
        if issue:
            user["health_profile"]["symptoms_history"].append({
                "date": datetime.now().isoformat(),
                "symptom": f"Appointment scheduled for: {issue}",
                "status": "scheduled"
            })

        user["interactions"].append({
            "timestamp": datetime.now().isoformat(),
            "type": "appointment",
            "summary": f"Booked with {appt.get('doctor')} at {appt.get('hospital')} ({appt.get('dept')})"
        })
        self.save()

    def retain_conversation(self, user_id: str, role: str, message: str):
        """Retains conversation history for dialogue context and continuity."""
        user = self.get_or_create_user(user_id)
        user["conversations"].append({
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "message": message
        })
        # Keep recent 40 messages to prevent unbounded growth
        if len(user["conversations"]) > 40:
            user["conversations"] = user["conversations"][-40:]
        self.save()

    # ═════════════════════════════════════════════════════════════════════
    # 2. RECALL: Semantic / Keyword Retrieval & Context Assembly
    # ═════════════════════════════════════════════════════════════════════

    def recall_preferences(self, user_id: str) -> Dict[str, str]:
        user = self.get_or_create_user(user_id)
        return user.get("preferences", {})

    def recall_health(self, user_id: str) -> Dict[str, Any]:
        user = self.get_or_create_user(user_id)
        return user.get("health_profile", {})

    def recall_conversation(self, user_id: str, limit: int = 6) -> List[Dict[str, str]]:
        user = self.get_or_create_user(user_id)
        return user.get("conversations", [])[-limit:]

    def recall_relevant_memories(self, user_id: str, query: str) -> Dict[str, Any]:
        """
        Recalls memory snippets specifically relevant to a user query:
        - Checks for drug safety / allergy keywords (penicillin, amoxicillin, augmentin, aspirin, etc.)
        - Checks for appointment / doctor / booking requests
        - Checks for symptom history / previous complaints
        - Checks for preference queries
        """
        user = self.get_or_create_user(user_id)
        query_lower = query.lower()

        recalled = {
            "allergies_triggered": [],
            "medications_relevant": [],
            "preferences_relevant": {},
            "past_symptoms_relevant": [],
            "conversation_recalled": []
        }

        # Allergy recall
        penicillin_family = ["penicillin", "amoxicillin", "ampicillin", "augmentin", "antibiotic", "mox", "clav"]
        allergies = user["health_profile"].get("allergies", [])
        for allergy in allergies:
            allergy_lower = allergy.lower()
            if any(term in query_lower for term in penicillin_family) and "penicillin" in allergy_lower:
                recalled["allergies_triggered"].append(allergy)
            elif any(w in query_lower for w in allergy_lower.split()):
                recalled["allergies_triggered"].append(allergy)

        # Medication recall
        for med in user["health_profile"].get("medications", []):
            if any(w in query_lower for w in med.lower().split()):
                recalled["medications_relevant"].append(med)

        # Symptom / complaint recall
        for sym in user["health_profile"].get("symptoms_history", []):
            s_text = sym.get("symptom", "").lower()
            # Match keywords like chest, pain, tightness, cough, fever, blood pressure
            overlap = set(query_lower.split()) & set(s_text.split())
            if overlap:
                recalled["past_symptoms_relevant"].append(sym)

        # Preference recall if asking about doctor/booking/hospital/timing
        if any(w in query_lower for w in ["doctor", "hospital", "book", "appointment", "timing", "preference", "schedule"]):
            recalled["preferences_relevant"] = user.get("preferences", {})

        # Conversation context
        recent_chats = user.get("conversations", [])
        if any(w in query_lower for w in ["remember", "last time", "earlier", "previous", "yesterday", "persist", "still"]):
            recalled["conversation_recalled"] = recent_chats[-4:]

        return recalled

    # ═════════════════════════════════════════════════════════════════════
    # 3. REFLECT: Synthesizing Insights, Patterns, and Suggestions
    # ═════════════════════════════════════════════════════════════════════

    def reflect(self, user_id: str) -> Dict[str, Any]:
        """
        Synthesizes high-level reflections:
        - Personalized welcoming greeting
        - Proactive clinical suggestions
        - Behavioral preferences summary
        - Clinical safety flags
        """
        user = self.get_or_create_user(user_id)
        name = user.get("name", "Patient")
        stats = user.get("stats", {})
        prefs = user.get("preferences", {})
        hp = user.get("health_profile", {})

        login_count = stats.get("login_count", 1)
        total_appts = stats.get("total_appointments", 0)

        # 1. Greeting reflection
        if login_count == 1:
            greeting = f"Welcome to Aegis AI, {name}! Your smart health memory is active."
        elif login_count < 5:
            greeting = f"Welcome back, {name}! Glad to see you again."
        else:
            preferred_doc = prefs.get("doctor", "your healthcare team")
            greeting = f"Welcome back, {name}! (Visit #{login_count}) - Connected with {preferred_doc}."

        # 2. Smart suggestions reflection
        suggestions = []
        if prefs.get("hospital"):
            suggestions.append({
                "type": "hospital",
                "text": f"Quick book at your preferred center: {prefs['hospital']}",
                "value": prefs['hospital']
            })
        if prefs.get("doctor"):
            dept_txt = f" ({prefs.get('department')})" if prefs.get('department') else ""
            suggestions.append({
                "type": "doctor",
                "text": f"Schedule follow-up with {prefs['doctor']}{dept_txt}",
                "value": prefs['doctor']
            })
        if prefs.get("preferred_time"):
            suggestions.append({
                "type": "time_slot",
                "text": f"Your habitual appointment timing: {prefs['preferred_time']}",
                "value": prefs['preferred_time']
            })

        # Health reminders
        if hp.get("conditions"):
            conds = ", ".join(hp["conditions"])
            suggestions.append({
                "type": "health",
                "text": f"Active health watch: {conds}",
                "value": conds
            })

        if not suggestions:
            suggestions.append({
                "type": "general",
                "text": "Book an appointment or update medical history to activate personalized suggestions.",
                "value": "Initial Setup"
            })

        # 3. Health recall summary
        health_summary = []
        if hp.get("allergies"):
            health_summary.append(f"⚠️ Allergies: {', '.join(hp['allergies'])}")
        if hp.get("conditions"):
            health_summary.append(f"🩺 Chronic Conditions: {', '.join(hp['conditions'])}")
        if hp.get("medications"):
            health_summary.append(f"💊 Current Medications: {', '.join(hp['medications'])}")
        if hp.get("symptoms_history"):
            latest = hp["symptoms_history"][-1]
            health_summary.append(f"📋 Recent Symptom Log: {latest.get('symptom')}")

        if not health_summary:
            health_summary = ["No health history recorded yet. Aegis will learn as you interact."]

        return {
            "greeting": greeting,
            "stats": stats,
            "smart_suggestions": suggestions,
            "health_recall": health_summary,
            "preference_recall": prefs
        }

    # ═════════════════════════════════════════════════════════════════════
    # 4. AGENT RESPONSE GENERATION (BEFORE vs. AFTER HINDSIGHT)
    # ═════════════════════════════════════════════════════════════════════

    def generate_response(self, user_id: str, message: str, use_hindsight: bool = True) -> Dict[str, Any]:
        """
        Generates response under two modes:
        - use_hindsight=False (Before Hindsight):
            Amnesic agent. No memory of user, no allergy recall, no past chats, no preferences.
        - use_hindsight=True (After Hindsight):
            Context-aware agent. Full memory recall, allergy cross-check, continuity of care.
        """
        msg_lower = message.lower().strip()
        user = self.get_or_create_user(user_id)
        prefs = user.get("preferences", {})
        hp = user.get("health_profile", {})

        # ─────────────────────────────────────────────────────────────────
        # CASE A: WITHOUT HINDSIGHT (Before: Amnesia, Generic, Dangerous)
        # ─────────────────────────────────────────────────────────────────
        if not use_hindsight:
            # Patient stating scheduling preference without memory
            if any(w in msg_lower for w in ["prefer", "morning", "afternoon", "evening"]) and any(k in msg_lower for k in ["appointment", "slot", "visit"]):
                return {
                    "mode": "before_hindsight",
                    "hindsight_enabled": False,
                    "recalled_items": [],
                    "response": "Understood. Note that in this mode, memory is disabled, so this preference will not be remembered for future interactions.",
                    "critique": "AMNESIA: Fails to retain patient scheduling preference for future visits."
                }

            # Medication check without memory (e.g. Amoxicillin / Penicillin)
            if any(term in msg_lower for term in ["amoxicillin", "augmentin", "penicillin", "antibiotic"]):
                return {
                    "mode": "before_hindsight",
                    "hindsight_enabled": False,
                    "recalled_items": [],
                    "response": (
                        "Amoxicillin 500mg is a commonly prescribed beta-lactam antibiotic used to treat bacterial "
                        "respiratory infections, ear infections, and dental abscesses. You can take it three times a day "
                        "with water after meals. Always complete the full course prescribed."
                    ),
                    "critique": "CRITICAL RISK: Aegis forgot patient's severe Penicillin allergy! Recommending Amoxicillin could trigger fatal anaphylaxis."
                }

            # Booking appointment without memory
            if any(w in msg_lower for w in ["book", "appointment", "schedule", "visit"]):
                return {
                    "mode": "before_hindsight",
                    "hindsight_enabled": False,
                    "recalled_items": [],
                    "response": (
                        "I can help you book an appointment. Please specify: Which hospital? Which doctor? "
                        "Which medical department? What date and time? And what is your reason for visit?"
                    ),
                    "critique": "FRUSTRATING UX: Aegis has no memory of the patient's preference for morning appointments or preferred doctor."
                }

            # Recalling past conversations / symptoms
            if any(w in msg_lower for w in ["chest", "tightness", "still", "persisting", "last conversation", "remember"]):
                return {
                    "mode": "before_hindsight",
                    "hindsight_enabled": False,
                    "recalled_items": [],
                    "response": (
                        "Hello, I am an AI medical assistant. What symptoms are you experiencing, and when did they start? "
                        "I don't have access to any previous conversations. Please describe your condition in full."
                    ),
                    "critique": "BROKEN CONTINUITY: Forgets patient reported chest tightness 3 days ago and fails to identify symptom worsening."
                }

            # Preferences query
            if any(w in msg_lower for w in ["preference", "what do i like", "preferred"]):
                return {
                    "mode": "before_hindsight",
                    "hindsight_enabled": False,
                    "recalled_items": [],
                    "response": (
                        "I don't have any preferences saved for you. I treat every session as brand new."
                    ),
                    "critique": "ZERO PERSONALIZATION: Fails to retain any patient habits or preferences."
                }

            # Allergy query
            if any(w in msg_lower for w in ["allergy", "allergies"]):
                return {
                    "mode": "before_hindsight",
                    "hindsight_enabled": False,
                    "recalled_items": [],
                    "response": (
                        "I do not have access to your medical records or allergy profile. Please consult your physician or hospital records."
                    ),
                    "critique": "UNINFORMED: Cannot protect patient during drug consultations."
                }

            # Generic fallback
            return {
                "mode": "before_hindsight",
                "hindsight_enabled": False,
                "recalled_items": [],
                "response": (
                    f"Hello! I am Aegis AI. How can I assist you today? Please note I don't retain memory between conversations."
                ),
                "critique": "AMNESIC: Treats returning patient as a complete stranger."
            }

        # ─────────────────────────────────────────────────────────────────
        # CASE B: WITH HINDSIGHT (After: Context-Aware, Safe, Proactive)
        # ─────────────────────────────────────────────────────────────────
        from memory_manager import memory_manager

        # Check if patient is stating a new preference or fact to retain
        useful = memory_manager.identify_useful_memory(message)
        if useful:
            bank_id = memory_manager.get_bank_id_for_user(user_id)
            memory_manager.retain_memory(bank_id, useful['fact'], metadata={"category": useful['category']})
            if useful['category'] == 'preference_timing':
                time_slot = "Morning (10:00 AM)" if "morning" in useful['fact'].lower() else ("Afternoon (2:00 PM)" if "afternoon" in useful['fact'].lower() else "Evening (6:00 PM)")
                prefs['preferred_time'] = time_slot
                self.retain_preference(user_id, 'preferred_time', time_slot)
                pref_desc = "morning appointments" if "morning" in useful['fact'].lower() else "afternoon appointments"
                return {
                    "mode": "after_hindsight",
                    "hindsight_enabled": True,
                    "recalled_items": [useful['fact']],
                    "response": f"Got it. I'll remember that you prefer {pref_desc} for future scheduling.",
                    "advantage": "HINDSIGHT RETAIN: Successfully extracted and stored patient preference in memory bank."
                }

        recalled = self.recall_relevant_memories(user_id, message)
        recalled_summary = []

        # 1. DRUG SAFETY & ALLERGY CHECK
        if any(term in msg_lower for term in ["amoxicillin", "augmentin", "penicillin", "antibiotic", "mox"]):
            allergies = hp.get("allergies", [])
            penicillin_allergy = next((a for a in allergies if "penicillin" in a.lower()), None)
            if penicillin_allergy:
                recalled_summary.append(f"Allergy Bank: {penicillin_allergy}")
                return {
                    "mode": "after_hindsight",
                    "hindsight_enabled": True,
                    "recalled_items": recalled_summary,
                    "response": (
                        f"🚨 **CRITICAL MEDICAL SAFETY ALERT**: Do NOT take Amoxicillin!\n\n"
                        f"My Hindsight memory recalls from your medical record: **{penicillin_allergy}**.\n\n"
                        f"Amoxicillin belongs to the **penicillin class** of antibiotics and carries a severe risk of "
                        f"cross-reactivity, hives, or anaphylaxis. I strongly advise against taking it. "
                        f"Please contact **{prefs.get('doctor', 'Dr. Smith')}** at **{prefs.get('hospital', 'City Hospital')}** "
                        f"to prescribe a safe, non-penicillin alternative (such as Azithromycin or Clarithromycin)."
                    ),
                    "advantage": "LIFE-SAVING: Immediately cross-referenced past allergy memory before providing medication guidance."
                }

        # 2. CONTINUING SYMPTOM & CONVERSATION RECALL
        if any(w in msg_lower for w in ["chest", "tightness", "still", "persisting", "last conversation", "remember"]):
            symptoms = hp.get("symptoms_history", [])
            chest_sym = next((s for s in symptoms if "chest" in s.get("symptom", "").lower()), None)
            recalled_summary.append("Conversation & Clinical History: Mild chest tightness reported on Sep 25")
            if chest_sym:
                return {
                    "mode": "after_hindsight",
                    "hindsight_enabled": True,
                    "recalled_items": recalled_summary,
                    "response": (
                        f"I remember our consultation from **September 25th** where you reported mild chest tightness after climbing stairs.\n\n"
                        f"Because this chest tightness has persisted for **over 72 hours** and your profile notes **{', '.join(hp.get('conditions', ['Hypertension']))}**, "
                        f"this is a clinical escalation. Persistent exertion-related chest tightness requires prompt medical attention.\n\n"
                        f"Would you like me to instantly book an emergency follow-up with your preferred cardiologist **{prefs.get('doctor', 'Dr. Smith')}** at **{prefs.get('hospital', 'City Hospital')}**?"
                    ),
                    "advantage": "CLINICAL CONTINUITY: Connected past report with current worsening to escalate triage level."
                }

        # 3. APPOINTMENT BOOKING WITH RECALLED PREFERENCES
        if any(w in msg_lower for w in ["book", "appointment", "schedule", "visit"]):
            hosp = prefs.get("hospital", "City Hospital")
            doc = prefs.get("doctor", "Dr. Smith")
            dept = prefs.get("department", "Cardiology")
            time_slot = prefs.get("preferred_time", "Morning (10:00 AM)")
            recalled_summary.append(f"Learned Timing: {time_slot}")
            recalled_summary.append(f"Learned Facility: {doc} at {hosp} ({dept})")

            if "morning" in time_slot.lower():
                response_text = f"I remember that you prefer morning appointments. Would you like a morning slot with {doc} at {hosp} ({time_slot})?"
            else:
                response_text = f"Welcome back, **{user.get('name', 'Patient')}**! Based on your learned preferences, would you like to book a {time_slot} slot with {doc} at {hosp}?"

            return {
                "mode": "after_hindsight",
                "hindsight_enabled": True,
                "recalled_items": recalled_summary,
                "response": response_text,
                "advantage": "HINDSIGHT RECALL: Recalled previous scheduling preference and pre-filled appointment details."
            }

        # 4. PREFERENCES RECALL
        if any(w in msg_lower for w in ["preference", "what do i like", "preferred"]):
            pref_lines = [f"• **{k.replace('_', ' ').title()}:** {v}" for k, v in prefs.items()]
            recalled_summary.append("Preferences Bank: Full profile")
            return {
                "mode": "after_hindsight",
                "hindsight_enabled": True,
                "recalled_items": recalled_summary,
                "response": (
                    f"Here are the preferences I have learned from your past visits:\n\n"
                    + "\n".join(pref_lines) +
                    f"\n\nI use these to customize your appointments and health reminders automatically!"
                ),
                "advantage": "TRANSPARENCY: Full visibility into agent's retained mental model."
            }

        # 5. ALLERGY RECALL
        if any(w in msg_lower for w in ["allergy", "allergies"]):
            allergies = hp.get("allergies", [])
            recalled_summary.append(f"Allergies: {', '.join(allergies)}")
            return {
                "mode": "after_hindsight",
                "hindsight_enabled": True,
                "recalled_items": recalled_summary,
                "response": (
                    f"According to your retained medical memory, you have the following recorded allergy:\n\n"
                    f"• **{allergies[0] if allergies else 'None recorded'}**\n\n"
                    f"I check every medication query against this list to ensure your safety."
                ),
                "advantage": "SAFETY: Immediate recall of vital medical contraindications."
            }

        # 6. HEALTH HISTORY RECALL
        if any(w in msg_lower for w in ["history", "health profile", "conditions", "medications"]):
            conds = hp.get("conditions", [])
            meds = hp.get("medications", [])
            allergies = hp.get("allergies", [])
            recalled_summary.append("Health Profile Bank: Conditions, Medications, Allergies")
            return {
                "mode": "after_hindsight",
                "hindsight_enabled": True,
                "recalled_items": recalled_summary,
                "response": (
                    f"Here is your clinical memory profile:\n\n"
                    f"• **Conditions:** {', '.join(conds) if conds else 'None'}\n"
                    f"• **Active Medications:** {', '.join(meds) if meds else 'None'}\n"
                    f"• **Allergies:** {', '.join(allergies) if allergies else 'None'}\n"
                    f"• **Total Recorded Visits:** {user.get('stats', {}).get('login_count', 1)}\n\n"
                    f"You can add or update details at any time from the Hindsight Memory tab."
                ),
                "advantage": "HOLISTIC CARE: Complete longitudinal health memory."
            }

        # 7. GENERAL CONTEXT-AWARE RESPONSE
        recalled_summary.append(f"Patient identity: {user.get('name')}, Logins: {user.get('stats', {}).get('login_count')}")
        return {
            "mode": "after_hindsight",
            "hindsight_enabled": True,
            "recalled_items": recalled_summary,
            "response": (
                f"Hello **{user.get('name', 'Patient')}**! (Visit #{user.get('stats', {}).get('login_count', 1)}). "
                f"I'm keeping track of your health profile (monitoring **{', '.join(hp.get('conditions', ['General Health']))}**). "
                f"How can I assist you with Dr. {prefs.get('doctor', 'Smith')}'s care plan today?"
            ),
            "advantage": "CONTINUOUS CARE: Personalized greeting and active condition awareness."
        }

    # ═════════════════════════════════════════════════════════════════════
    # 5. BEFORE VS. AFTER DEMONSTRATION SUITE
    # ═════════════════════════════════════════════════════════════════════

    def get_demonstration_scenarios(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns the 4 core before-vs-after comparison demonstrations."""
        scenarios = [
            {
                "id": "scenario-1",
                "category": "Medication Safety & Allergy Recall",
                "description": "Patient asks if they can take Amoxicillin for a sore throat/infection.",
                "user_prompt": "Can I take Amoxicillin 500mg for my throat infection?",
                "why_memory_needed": "Critical safety. Without memory of the patient's Penicillin allergy, the agent approves a potentially fatal drug.",
                "before": self.generate_response(user_id, "Can I take Amoxicillin 500mg for my throat infection?", use_hindsight=False),
                "after": self.generate_response(user_id, "Can I take Amoxicillin 500mg for my throat infection?", use_hindsight=True)
            },
            {
                "id": "scenario-2",
                "category": "Remembering Patient Preferences",
                "description": "Patient previously told assistant 'I prefer morning appointments'. Later returns to schedule their appointment.",
                "user_prompt": "Book my next appointment.",
                "why_memory_needed": "User friction. Without memory, the user must re-enter hospital, doctor, and timing preference every single time.",
                "before": self.generate_response(user_id, "Book my next appointment.", use_hindsight=False),
                "after": self.generate_response(user_id, "Book my next appointment.", use_hindsight=True)
            },
            {
                "id": "scenario-3",
                "category": "Recalling Previous Conversations & Symptom Evolution",
                "description": "Patient reports that their chest tightness has not resolved after 3 days.",
                "user_prompt": "My chest tightness is still persisting after 3 days.",
                "why_memory_needed": "Clinical context. Without memory, the AI has no idea what 'still persisting' refers to, treating it as an uncontextualized event.",
                "before": self.generate_response(user_id, "My chest tightness is still persisting after 3 days.", use_hindsight=False),
                "after": self.generate_response(user_id, "My chest tightness is still persisting after 3 days.", use_hindsight=True)
            },
            {
                "id": "scenario-4",
                "category": "Remembering User Interactions & Longitudinal Continuity",
                "description": "Patient logs in and asks for a summary of their health status and preferences.",
                "user_prompt": "What are my preferences and health history?",
                "why_memory_needed": "Long-term relationship. Without memory, the AI behaves like a cold stranger on every single visit.",
                "before": self.generate_response(user_id, "What are my preferences and health history?", use_hindsight=False),
                "after": self.generate_response(user_id, "What are my preferences and health history?", use_hindsight=True)
            }
        ]
        return scenarios


# Singleton instance
hindsight = HindsightMemoryEngine()


def print_demonstration():
    """Prints a clear, comprehensive Before vs. After demonstration to the console."""
    sep = "=" * 78
    subsep = "-" * 78

    print("\n" + sep)
    print("      AEGIS AI - HINDSIGHT AGENT MEMORY SYSTEM DEMONSTRATION")
    print(sep)
    print("Architecture: Retain -> Recall -> Reflect (vectorize-io / Hindsight)")
    print("Identified 4 Critical Healthcare Memory Domains:")
    print("  1. Remembering previous user interactions (visit frequency & logins)")
    print("  2. Remembering patient/user preferences (Dr. Smith at City Hospital)")
    print("  3. Recalling previous conversations (multi-day symptom evolution)")
    print("  4. Using past information for clinical safety (Penicillin allergy check)")
    print(sep + "\n")

    scenarios = hindsight.get_demonstration_scenarios("P-10021")

    for idx, s in enumerate(scenarios, 1):
        print(f"[{idx}/4] USE CASE: {s['category'].upper()}")
        print(subsep)
        print(f"[-] Patient Query:    \"{s['user_prompt']}\"")
        print(f"[*] Why Memory Needed: {s['why_memory_needed']}\n")

        print("  [X] BEFORE HINDSIGHT (Amnesic Agent - Memory Disabled):")
        print(f"      Response: {s['before']['response']}")
        print(f"      [!] Failure Point: {s['before']['critique']}\n")

        print("  [V] AFTER HINDSIGHT (Memory-Augmented Agent - Active):")
        recalled = s['after'].get('recalled_items', [])
        if recalled:
            print(f"      [Recalled Memory]: {', '.join(recalled)}")
        # Format response lines
        for line in s['after']['response'].split("\n"):
            if line.strip():
                clean_line = line.replace('**', '').replace('🚨 ', '[ALERT] ').replace('• ', '  - ')
                print(f"      {clean_line}")
        print(f"      [+] Clinical Advantage: {s['after']['advantage']}\n")
        print(subsep + "\n")

    print(sep)
    print("SUMMARY: BEFORE vs. AFTER HINDSIGHT")
    print(sep)
    print("• Before Hindsight: Amnesic. Treats every query as day zero. Forgets life-saving")
    print("  allergies (approves Amoxicillin), interrogates user for preferences, and loses")
    print("  track of worsening symptom timelines.")
    print("• After Hindsight: Context-aware. Instantly blocks contraindicated medications,")
    print("  auto-configures appointments with Dr. Smith, connects multi-day symptoms,")
    print("  and establishes longitudinal care continuity.")
    print(sep + "\n")


if __name__ == '__main__':
    print_demonstration()
