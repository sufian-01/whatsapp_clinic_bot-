"""Structured doctor lookups backed by a header-driven Google Sheet.

Features:
- Deterministic fuzzy matching using difflib and token-level comparison.
- Disease/symptom keyword-to-specialization mapping.
- Structured doctor directory formatting.
- Date-aware availability lookup from Google Sheet slot records.
- Zero LLM calls to minimize token usage.
"""

from difflib import SequenceMatcher
import re
from threading import RLock
import time
from typing import Protocol


class SheetReader(Protocol):
    def __call__(self) -> list[list[str]]: ...


# ---------------------------------------------------------------------------
# Specialization keyword aliases (deterministic, no LLM)
# ---------------------------------------------------------------------------
_SPECIALIZATION_ALIASES: dict[str, list[str]] = {
    "cardiology": ["cardio", "cardiologist", "heart", "cardiac"],
    "gynecology": ["gynecologist", "gynaecologist", "gyne", "gyno", "women"],
    "general physician": ["general", "gp", "family doctor", "physician"],
    "dermatology": ["dermatologist", "skin", "derma"],
    "orthopedics": ["orthopedic", "ortho", "bone", "joint"],
    "pediatrics": ["pediatrician", "paediatrician", "child", "children", "kids"],
    "neurology": ["neurologist", "neuro", "brain", "nerve"],
    "ophthalmology": ["ophthalmologist", "eye", "opthamology"],
    "ent": ["ear", "nose", "throat", "ent specialist"],
    "psychiatry": ["psychiatrist", "mental health", "psychology", "psychologist"],
    "oncology": ["oncologist", "cancer"],
    "endocrinology": ["endocrinologist", "diabetes", "thyroid", "hormones"],
}

# ---------------------------------------------------------------------------
# Health concern / disease / symptom keyword-to-specialization mapping
# Informational only, not a medical diagnosis
# ---------------------------------------------------------------------------
_HEALTH_CONCERN_MAP: dict[str, list[str]] = {
    "cardiology": [
        "chest pain", "heart attack", "heart problem", "heart pain", "heart",
        "palpitation", "palpitations", "blood pressure", "high bp", "bp",
        "hypertension", "cardiac",
    ],
    "gynecology": [
        "pregnancy", "pregnant", "periods", "period", "menstrual", "menstruation",
        "pcos", "pcod", "women health", "fertility", "uterus", "ovary", "vaginal",
    ],
    "general physician": [
        "fever", "cold", "cough", "flu", "viral", "headache", "body pain",
        "weakness", "fatigue", "vomiting", "loose motion", "diarrhea",
        "stomach pain", "abdominal pain", "gastric", "infection",
    ],
    "dermatology": [
        "skin rash", "skin problem", "skin", "rash", "rashes", "acne", "pimples",
        "itching", "hair fall", "dandruff", "eczema", "psoriasis", "fungal",
    ],
    "orthopedics": [
        "joint pain", "knee pain", "back pain", "shoulder pain", "neck pain",
        "bone fracture", "fracture", "bone", "joint", "arthritis", "spine", "sprain",
    ],
    "pediatrics": [
        "child", "children", "baby", "kid", "kids", "infant", "newborn",
    ],
    "neurology": [
        "migraine", "nerve pain", "nerve", "nerves", "brain", "paralysis",
        "stroke", "seizure", "epilepsy", "tremor", "vertigo", "numbness",
    ],
    "ophthalmology": [
        "eye pain", "eye problem", "eyes", "eye", "vision", "blurry vision",
        "blur", "cataract", "glaucoma",
    ],
    "ent": [
        "ear pain", "sore throat", "ear", "nose", "throat", "tonsils",
        "sinus", "sinusitis", "hearing",
    ],
    "psychiatry": [
        "depression", "anxiety", "stress", "mental health", "mental",
        "insomnia", "sleep disorder", "panic attack",
    ],
    "endocrinology": [
        "high sugar", "blood sugar", "diabetes", "sugar", "thyroid", "hormone", "hormonal",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_doctor_text(value: str) -> str:
    """Lowercase, remove doctor/dr prefixes, punctuation, honorifics, and normalize extra spaces."""
    text = value.casefold()
    text = text.replace("sufiyan", "sufian")
    text = text.replace("sufan", "sufian")
    text = re.sub(r"\b(doctor|dr)\.?\b", " ", text)
    text = re.sub(r"\b(ji|sahab|saheb|sir|madam)\b", " ", text)
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return " ".join(text.split())


def calculate_doctor_similarity(query: str, doc_name: str) -> float:
    """Calculate deterministic similarity score between query and doctor name.

    Handles:
    - Exact name matches
    - Minor typos (e.g., 'Dr Sufan' -> 'Dr. Sufian')
    - Incomplete/first names (e.g., 'dr arjun' -> 'Dr. Arjun Mehta')
    - Extra words like specializations (e.g., 'cardiologist Dr Sufian' -> 'Dr. Sufian')
    """
    q_clean = normalize_doctor_text(query)
    d_clean = normalize_doctor_text(doc_name)
    if not q_clean or not d_clean:
        return 0.0

    if q_clean == d_clean:
        return 1.0

    q_words = q_clean.split()
    d_words = d_clean.split()

    whole_ratio = SequenceMatcher(None, q_clean, d_clean).ratio()

    # Score each doctor word against query words (coverage of doctor's name in query)
    doc_word_scores = []
    for dw in d_words:
        best_qw = max((SequenceMatcher(None, qw, dw).ratio() for qw in q_words), default=0.0)
        doc_word_scores.append(best_qw)
    avg_doc_coverage = sum(doc_word_scores) / len(doc_word_scores) if doc_word_scores else 0.0

    # Score each query word against doctor words
    q_word_scores = []
    for qw in q_words:
        best_dw = max((SequenceMatcher(None, qw, dw).ratio() for dw in d_words), default=0.0)
        q_word_scores.append(best_dw)

    # Incomplete / first name: single word query matching any doctor token
    if len(q_words) == 1:
        single_word_match = max(q_word_scores) if q_word_scores else 0.0
        return max(whole_ratio, single_word_match)

    # Query contains doctor's name parts (e.g. 'cardiologist Dr Sufian')
    if avg_doc_coverage >= 0.85:
        return max(whole_ratio, avg_doc_coverage)

    # First name or any token match within a multi-word conversational query
    # (e.g. 'Dr Arjun kab free hain?', 'Dr Sana available hai?')
    first_name_match = doc_word_scores[0] if doc_word_scores else 0.0
    if first_name_match >= 0.80:
        return max(whole_ratio, avg_doc_coverage, first_name_match * 0.92)

    any_doc_word = max(doc_word_scores) if doc_word_scores else 0.0
    if any_doc_word >= 0.85:
        return max(whole_ratio, avg_doc_coverage, any_doc_word * 0.90)

    avg_query_match = sum(q_word_scores) / len(q_words) if q_words else 0.0
    return max(whole_ratio, avg_doc_coverage, avg_query_match)


def resolve_specialization(text: str) -> str | None:
    """Map free-text specialization keyword to canonical specialization key."""
    lowered = text.casefold().strip()
    for canonical, aliases in _SPECIALIZATION_ALIASES.items():
        if canonical in lowered or any(alias in lowered for alias in aliases):
            return canonical
    return None


def match_health_concern(text: str) -> tuple[str | None, str | None]:
    """Map patient health concern/symptom keyword to (matched_phrase, canonical_specialization).

    Informational keyword lookup only, not medical diagnosis.
    Returns (None, None) if no reliable keyword match exists.
    """
    lowered = text.casefold()
    all_pairs: list[tuple[str, str]] = []
    for canonical, keywords in _HEALTH_CONCERN_MAP.items():
        for kw in keywords:
            all_pairs.append((kw, canonical))
    # Sort longer phrases first to match multi-word phrases before single words
    all_pairs.sort(key=lambda x: len(x[0]), reverse=True)

    for kw, canonical in all_pairs:
        if re.search(r"\b" + re.escape(kw) + r"\b", lowered):
            return kw, canonical
    return None, None


def format_doctor_list_display(doctors: list[dict], intro: str = "Our available doctors are:") -> str:
    """Format doctor listing with name, specialization, fee, and available days."""
    if not doctors:
        return "No doctors are currently available. Please contact the clinic team."

    entries = []
    for idx, d in enumerate(doctors, 1):
        name = d.get("Doctor Name", "Doctor").strip()
        spec = d.get("Specialization", "General").strip()
        days = d.get("Available Days", "").strip() or "All Days"
        fee = d.get("Consultation Fee", "").strip()
        cleaned_fee = fee.replace("Rs.", "").replace("Rs", "").replace("INR", "").replace("₹", "").strip()
        fee_display = f"₹{cleaned_fee}" if cleaned_fee else "N/A"

        entry = (
            f"{idx}. {name}\n"
            f"   {spec} | {fee_display}\n"
            f"   Available: {days}"
        )
        entries.append(entry)

    return f"{intro}\n\n" + "\n\n".join(entries) + "\n\nPlease select a doctor."


# ---------------------------------------------------------------------------
# DoctorDirectory
# ---------------------------------------------------------------------------

class DoctorDirectory:
    def __init__(
        self,
        read_rows: SheetReader,
        append_row=None,
        update_cells=None,
        sheet_range: str = "doctor!A1:Z1000",
        cache_ttl_seconds: float = 60.0,
    ) -> None:
        self._read_rows = read_rows
        self._append_row = append_row
        self._update_cells = update_cells
        self._sheet_range = sheet_range
        self._cache_ttl = cache_ttl_seconds
        self._cache_lock = RLock()
        self._cache_time: float = 0.0
        self._cached_doctors: list[dict[str, str]] | None = None

    def invalidate_cache(self) -> None:
        """Invalidate the in-memory cache to force next read from source."""
        with self._cache_lock:
            self._cached_doctors = None
            self._cache_time = 0.0

    def get_doctors(self, force_refresh: bool = False) -> list[dict[str, str]]:
        """Return all doctor records from the Google Sheet, utilizing in-memory TTL caching."""
        with self._cache_lock:
            now = time.monotonic()
            if not force_refresh and self._cached_doctors is not None and (now - self._cache_time) < self._cache_ttl:
                return [dict(d) for d in self._cached_doctors]

            try:
                rows = self._read_rows()
            except Exception:
                return [dict(d) for d in self._cached_doctors] if self._cached_doctors is not None else []

            if not rows:
                self._cached_doctors = []
                self._cache_time = now
                return []

            headers = [h.strip() for h in rows[0]]
            doctors = [
                {h: (row[i].strip() if i < len(row) else "") for i, h in enumerate(headers)}
                for row in rows[1:]
                if any(cell.strip() for cell in row)
            ]
            self._cached_doctors = doctors
            self._cache_time = now
            return [dict(d) for d in doctors]

    def get_active_doctors(self) -> list[dict[str, str]]:
        """Return only active doctors from the Google Sheet."""
        doctors = self.get_doctors()
        return [
            d for d in doctors
            if d.get("Status", "").strip().casefold() not in ("inactive", "disabled", "unavailable")
        ]

    def get_doctor_by_id(self, doctor_id: str) -> dict[str, str] | None:
        normalized = doctor_id.strip().casefold()
        return next((d for d in self.get_doctors() if d.get("Doctor ID", "").strip().casefold() == normalized), None)

    def get_doctor_by_name(self, name: str) -> list[dict[str, str]]:
        normalized = name.casefold().strip()
        return [d for d in self.get_active_doctors() if d.get("Doctor Name", "").casefold() == normalized]

    def get_doctors_by_specialization(self, specialization: str) -> list[dict[str, str]]:
        """Match active doctors by specialization using bidirectional / prefix substring check."""
        normalized = specialization.casefold().strip()
        result = []
        for d in self.get_active_doctors():
            sheet_spec = d.get("Specialization", "").casefold()
            if (
                normalized in sheet_spec
                or sheet_spec in normalized
                or (len(normalized) >= 5 and sheet_spec.startswith(normalized[:5]))
                or (len(sheet_spec) >= 5 and normalized.startswith(sheet_spec[:5]))
            ):
                result.append(d)
        return result

    def get_doctor_schedule(self, name: str) -> list[dict[str, str]]:
        return [
            {k: d[k] for k in ("Doctor Name", "Available Days", "Start Time", "End Time", "Status") if d.get(k)}
            for d in self.get_doctor_by_name(name)
        ]

    def get_available_doctors_for_date(self, date: str, slot_repository) -> list[dict[str, str]]:
        """Return active doctors who have available slots on the specified date."""
        try:
            _, records = slot_repository._snapshot()
        except Exception:
            return []
        available_names: set[str] = {
            r.get("Doctor Name", "").casefold()
            for r in records
            if r.get("Date") == date and r.get("Status", "").casefold() == "available"
        }
        if not available_names:
            return []
        return [d for d in self.get_active_doctors() if d.get("Doctor Name", "").casefold() in available_names]

    def resolve_doctor(self, text: str) -> dict:
        """Deterministically match text to a doctor using fuzzy and partial matching.

        Returns:
            {"status": "matched", "doctor": {...}, "score": float}
            {"status": "ambiguous", "matches": [...], "score": float}
            {"status": "not_found", "matches": []}
        """
        doctors = self.get_active_doctors()
        if not doctors:
            return {"status": "not_found", "matches": []}

        # Check by Doctor ID (e.g. DOC-001 or doctor:DOC-001)
        raw_clean = text.strip().upper()
        clean_id = raw_clean.removeprefix("DOCTOR:").removeprefix("DOC:").strip()
        for d in doctors:
            doc_id = (d.get("Doctor ID") or "").strip().upper()
            if doc_id and doc_id in (raw_clean, clean_id):
                return {"status": "matched", "doctor": d, "score": 1.0, "matches": [d]}

        normalized_text = normalize_doctor_text(text)

        # Exact match first
        exact = [d for d in doctors if normalize_doctor_text(d.get("Doctor Name", "")) == normalized_text]
        if exact:
            return {"status": "matched", "doctor": exact[0], "score": 1.0}

        # Calculate similarity scores
        scored = [
            (d, calculate_doctor_similarity(text, d.get("Doctor Name", "")))
            for d in doctors
        ]
        scored.sort(key=lambda item: item[1], reverse=True)

        if not scored or scored[0][1] < 0.80:
            return {"status": "not_found", "matches": []}

        best_doc, best_score = scored[0]

        # Check for ambiguity: multiple doctors scoring close to each other
        if len(scored) > 1 and scored[1][1] >= 0.80 and (best_score - scored[1][1]) < 0.08:
            ambiguous_matches = [item[0] for item in scored if item[1] >= 0.80]
            return {"status": "ambiguous", "matches": ambiguous_matches, "score": best_score}

        return {"status": "matched", "doctor": best_doc, "score": best_score}

    def add_doctor(self, data: dict[str, str]) -> dict[str, str]:
        """Add a new doctor to the master sheet."""
        if not self._append_row:
            raise RuntimeError("Doctor appending is not configured")
        rows = self._read_rows() if self._read_rows else []
        headers = [h.strip() for h in rows[0]] if rows else [
            "Doctor ID", "Doctor Name", "Specialization", "Available Days",
            "Start Time", "End Time", "Consultation Fee", "Status"
        ]

        # Generate Doctor ID if needed
        existing = self.get_doctors()
        doc_id = data.get("Doctor ID") or data.get("doctor_id") or ""
        if not doc_id:
            max_num = 0
            for d in existing:
                val = d.get("Doctor ID", "")
                if val.startswith("D") and val[1:].isdigit():
                    max_num = max(max_num, int(val[1:]))
            doc_id = f"D{max_num + 1}"

        status = data.get("Status") or data.get("status") or "Active"
        name = data.get("Doctor Name") or data.get("name") or data.get("doctor_name", "")
        spec = data.get("Specialization") or data.get("specialization", "")
        days = data.get("Available Days") or data.get("available_days", "")
        start_time = data.get("Start Time") or data.get("start_time", "")
        end_time = data.get("End Time") or data.get("end_time", "")
        fee = data.get("Consultation Fee") or data.get("consultation_fee") or data.get("fee", "")
        qual = data.get("Qualification") or data.get("qualification", "")
        reg = data.get("Registration Number") or data.get("registration_number") or data.get("reg_no", "")

        row_map = {
            "Doctor ID": doc_id,
            "Doctor Name": name,
            "Specialization": spec,
            "Qualification": qual,
            "Registration Number": reg,
            "Available Days": days,
            "Start Time": start_time,
            "End Time": end_time,
            "Consultation Fee": fee,
            "Status": status,
        }

        row_values = [row_map.get(h, "") for h in headers]
        self._append_row(row_values, self._sheet_range)
        self.invalidate_cache()
        return row_map

    def update_doctor(self, doctor_id: str, updates: dict[str, str]) -> dict[str, str] | None:
        """Update doctor record by Doctor ID."""
        if not self._update_cells or not self._read_rows:
            raise RuntimeError("Doctor updating is not configured")
        rows = self._read_rows()
        if not rows:
            return None
        headers = [h.strip() for h in rows[0]]
        if "Doctor ID" not in headers:
            return None
        id_index = headers.index("Doctor ID")

        normalized_id = doctor_id.strip().casefold()
        for row_number, row in enumerate(rows[1:], start=2):
            if id_index < len(row) and row[id_index].strip().casefold() == normalized_id:
                # Build updated row
                row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
                for k, v in updates.items():
                    # Map common keys
                    clean_k = k
                    if k in ("name", "doctor_name"):
                        clean_k = "Doctor Name"
                    elif k == "specialization":
                        clean_k = "Specialization"
                    elif k == "available_days":
                        clean_k = "Available Days"
                    elif k == "start_time":
                        clean_k = "Start Time"
                    elif k == "end_time":
                        clean_k = "End Time"
                    elif k in ("fee", "consultation_fee"):
                        clean_k = "Consultation Fee"
                    elif k == "status":
                        clean_k = "Status"
                    elif k == "qualification":
                        clean_k = "Qualification"
                    elif k in ("registration_number", "reg_no", "registration_no"):
                        clean_k = "Registration Number"
                    elif k == "photo":
                        clean_k = "Photo"
                    elif k == "signature":
                        clean_k = "Signature"
                    if clean_k in headers:
                        row_dict[clean_k] = str(v).strip()
                    else:
                        row_dict[clean_k] = str(v).strip()

                values = [row_dict.get(h, "") for h in headers]
                sheet_name = self._sheet_range.split("!", 1)[0]
                last_col = _column_name(len(headers) - 1)
                self._update_cells(f"{sheet_name}!A{row_number}:{last_col}{row_number}", values)
                self.invalidate_cache()
                return row_dict
        return None

    def set_doctor_status(self, doctor_id: str, status: str) -> bool:
        """Activate or deactivate a doctor."""
        updated = self.update_doctor(doctor_id, {"Status": status})
        return updated is not None


def _column_name(index: int) -> str:
    name = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


# ---------------------------------------------------------------------------
# DoctorTools
# ---------------------------------------------------------------------------

class DoctorTools:
    """Thin facade over DoctorDirectory for tool integration."""

    def __init__(self, directory: DoctorDirectory) -> None:
        self._directory = directory

    def invalidate_cache(self) -> None:
        if hasattr(self._directory, "invalidate_cache"):
            self._directory.invalidate_cache()

    def get_doctors(self):
        return self._directory.get_doctors()

    def get_active_doctors(self):
        return self._directory.get_active_doctors()

    def get_doctor_by_id(self, doctor_id: str):
        return self._directory.get_doctor_by_id(doctor_id)

    def search_doctor(self, name: str):
        return self._directory.get_doctor_by_name(name)

    def get_doctors_by_specialization(self, specialization: str):
        return self._directory.get_doctors_by_specialization(specialization)

    def get_doctor_schedule(self, name: str):
        return self._directory.get_doctor_schedule(name)

    def resolve_doctor(self, text: str) -> dict:
        return self._directory.resolve_doctor(text)

    def get_available_doctors_for_date(self, date: str, slot_repository) -> list[dict[str, str]]:
        return self._directory.get_available_doctors_for_date(date, slot_repository)

    def add_doctor(self, data: dict[str, str]):
        return self._directory.add_doctor(data)

    def update_doctor(self, doctor_id: str, updates: dict[str, str]):
        return self._directory.update_doctor(doctor_id, updates)

    def set_doctor_status(self, doctor_id: str, status: str):
        return self._directory.set_doctor_status(doctor_id, status)