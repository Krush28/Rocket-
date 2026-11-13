import re
from typing import Any
from app.db.database import SessionLocal
from app.db.models import ConversationRecord
from app.schemas.chat import ChatResponse

REQUIRED_FIELDS = ("crop", "quantity_kg", "location", "ready_when")
QUESTIONS = {
    "crop": "Which crop have you harvested?",
    "quantity_kg": "How much produce do you have? You can answer in kg, tonnes or quintals.",
    "location": "Where is your farm or produce located? Please share the village or nearest town.",
    "ready_when": "When will the produce be ready for sale — now, or on a later date?",
}
QUESTIONS_HI = {
    "crop": "आपने कौन-सी फसल काटी है?",
    "quantity_kg": "आपके पास कितनी उपज है? किलो, टन या क्विंटल में बताएं।",
    "location": "आपका खेत या उपज कहाँ है? गाँव या नज़दीकी शहर बताएं।",
    "ready_when": "उपज बिक्री के लिए कब तैयार होगी — अभी या किसी बाद की तारीख को?",
}

class ConversationManager:
    """Persisted deterministic intake; a structured multilingual LLM extractor can be added behind this interface."""
    def _session(self, session_id: str) -> dict[str, Any]:
        with SessionLocal() as db:
            record = db.get(ConversationRecord, session_id)
            if not record:
                profile = {"preferred_language": None, "crop": None, "variety": None, "quality_grade": None,
                    "quantity_kg": None, "quantity_original": None, "location": None, "ready_when": None,
                    "selling_preference": None, "can_store": None}
                db.add(ConversationRecord(session_id=session_id, profile=profile, confirmed=False)); db.commit()
                return {"profile": profile, "confirmed": False}
            return {"profile": dict(record.profile or {}), "confirmed": record.confirmed}

    def _save(self, session_id: str, state: dict[str, Any]):
        with SessionLocal() as db:
            record = db.get(ConversationRecord, session_id)
            if record is None:
                record = ConversationRecord(session_id=session_id, profile=state["profile"], confirmed=state["confirmed"]); db.add(record)
            else:
                record.profile = dict(state["profile"]); record.confirmed = state["confirmed"]
            db.commit()

    @staticmethod
    def _detect_language(message: str) -> str:
        return "hi" if re.search(r"[\u0900-\u097F]", message) else "en"

    @staticmethod
    def _extract_quantity(text: str):
        match = re.search(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(kg|kgs|kilograms?|tonnes?|tons?|quintals?|qtl|किलो(?:ग्राम)?|टन|क्विंटल)?", text, re.I)
        if not match: return None, None
        raw = match.group(0).strip(); value = float(match.group(1).replace(",", "")); unit = (match.group(2) or "kg").lower()
        if unit.startswith("ton") or unit == "टन": value *= 1000
        elif unit.startswith(("quintal", "qtl")) or unit == "क्विंटल": value *= 100
        return value, raw

    def _extract(self, message: str, profile: dict):
        text = message.strip(); lower = text.lower(); profile["preferred_language"] = self._detect_language(text)
        quantity, original = self._extract_quantity(text)
        if quantity and quantity > 0: profile["quantity_kg"] = quantity; profile["quantity_original"] = original
        location = re.search(r"(?:near|at|in|from|के पास|में|से)\s+([A-Za-z][A-Za-z .'-]{1,50}|[\u0900-\u097F ]{2,50})", text, re.I)
        if location:
            candidate = location.group(1).strip(" .,!? ")
            if candidate.lower() not in {"the market", "my farm"}: profile["location"] = candidate
        if re.search(r"\b(?:ready now|available now|harvested|today|now)\b", lower) or any(x in lower for x in ("अभी", "आज", "तैयार")): profile["ready_when"] = "Now"
        else:
            date_match = re.search(r"\b(?:tomorrow|next week|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b", lower)
            if date_match: profile["ready_when"] = date_match.group(0)
        crop_match = re.search(r"(?:crop|फसल)\s*[:=-]?\s*([A-Za-z][A-Za-z -]{1,30}|[\u0900-\u097F]{2,20})", text, re.I)
        ignored = {"hi", "hello", "yes", "no", "okay", "ok", "namaste", "yes please"}
        if crop_match: profile["crop"] = crop_match.group(1).strip().title()
        elif not profile.get("crop") and not quantity and lower not in ignored and len(text.split()) <= 3: profile["crop"] = text.strip(" .,!? ").title()
        elif not profile.get("crop"):
            leading_crop = re.match(r"^([A-Za-z][A-Za-z -]{2,30}?)(?=,|\s+\d)", text)
            if leading_crop: profile["crop"] = leading_crop.group(1).strip().title()
        variety = re.search(r"(?:variety|वैरायटी)\s*[:=-]?\s*([A-Za-z0-9 -]{2,30})", text, re.I)
        if variety: profile["variety"] = variety.group(1).strip()
        grade = re.search(r"(?:grade|quality|गुणवत्ता)\s*[:=-]?\s*([A-Za-z0-9 -]{1,20})", text, re.I)
        if grade: profile["quality_grade"] = grade.group(1).strip()
        if any(x in lower for x in ("sell now", "sell immediately", "अभी बेच")): profile["selling_preference"] = "sell_now"
        elif any(x in lower for x in ("wait", "hold", "बाद में बेच")): profile["selling_preference"] = "consider_holding"
        if any(x in lower for x in ("can store", "have storage", "स्टोर कर सकता", "भंडारण है")): profile["can_store"] = True
        elif any(x in lower for x in ("cannot store", "no storage", "भंडारण नहीं")): profile["can_store"] = False

    def reply(self, session_id: str, message: str):
        state = self._session(session_id); state["confirmed"] = False; profile = state["profile"]; self._extract(message, profile)
        missing = [field for field in REQUIRED_FIELDS if not profile.get(field)]
        if missing:
            field = missing[0]; prompts = QUESTIONS_HI if profile.get("preferred_language") == "hi" else QUESTIONS
            reply = prompts[field]
            if field == "quantity_kg" and profile.get("crop"):
                reply = (f"ठीक है — {profile['crop']}। " if profile.get("preferred_language") == "hi" else f"Got it — {profile['crop']}. ") + reply
        else:
            quantity = profile["quantity_kg"]
            reply = ("आपकी जानकारी जाँचें:\n" if profile.get("preferred_language") == "hi" else "Please review your harvest details:\n")
            reply += f"• Crop: {profile['crop']}\n• Quantity: {quantity:g} kg\n• Location: {profile['location']}\n• Ready: {profile['ready_when']}\n\n"
            reply += "क्या यह सही है? पुष्टि के बाद ही बाजार विकल्प खोजे जाएंगे।" if profile.get("preferred_language") == "hi" else "Is this correct? I will search for market options only after you confirm."
        self._save(session_id, state)
        return ChatResponse(session_id=session_id, reply=reply, profile=profile.copy(), missing_fields=missing, ready_for_confirmation=not missing, confirmed=False)

    def confirm(self, session_id: str, confirmed: bool):
        state = self._session(session_id); profile = state["profile"]; missing = [f for f in REQUIRED_FIELDS if not profile.get(f)]
        state["confirmed"] = bool(confirmed and not missing)
        if state["confirmed"]: reply = "Details confirmed. Your profile is ready for market discovery; live market data is not connected yet."
        elif missing: reply = "Please complete the missing harvest details before confirming."
        else: reply = "No problem. Tell me what you would like to correct."
        self._save(session_id, state)
        return ChatResponse(session_id=session_id, reply=reply, profile=profile.copy(), missing_fields=missing, ready_for_confirmation=not missing, confirmed=state["confirmed"])

conversation_manager = ConversationManager()
