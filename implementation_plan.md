# Clinic CRM & Telegram AI Chatbot — Rescheduling, Cancellation & Conversational Improvements

## 1. Executive Summary & Architecture

This implementation plan extends the existing `D:\telegram_bot` system with:
1. **End-to-End Appointment Rescheduling** in both Telegram AI Chatbot and Clinic CRM Admin Dashboard.
2. **End-to-End Appointment Cancellation** in both Telegram AI Chatbot and Clinic CRM Admin Dashboard.
3. **Conversational Receptionist Experience** in Telegram:
   - Natural intent recognition in Hindi, Hinglish, and English.
   - Contextual memory without rigid repetitive questioning.
   - Deterministic availability and booking tools with LLM-assisted conversational fluency.
4. **Enhanced Doctor Fuzzy Matching & Natural Date Parsing**:
   - Matches colloquial names ("Dr Arjun", "Sufan", "sana", etc.) with canonical clinic records.
   - Full Hindi/Hinglish date parsing ("kal", "parso", "aaj", "agle Monday", "is Friday", "kal subah").
5. **Shared Business Logic Layer**:
   - Centralized in `CrmService` and repository tools so Telegram and CRM never drift or produce conflicting booking states.

---

## 2. Existing Data Model & Google Sheets Schema

1. **Doctor Sheet (`doctor!A1:Z1000`)**:
   - `Doctor ID`, `Doctor Name`, `Specialization`, `Available Days`, `Start Time`, `End Time`, `Consultation Fee`, `Status` (`Active`/`Inactive`).
2. **Patient Sheet (`patient!A1:Z1000`)**:
   - `Patient ID`, `Name`, `Email`, `Phone`, `Age`, `Gender`, `Doctor`, `Appointment Date` (`YYYY-MM-DD`), `Appointment Time` (`HH:MM`), `Token No` (`TKN-xxxx`), `Amount`, `Payment Method` (`Offline`/`UPI`), `Payment Status` (`Pending`/`Paid`), `Booking Status` (`Confirmed`/`Pending`/`Completed`/`Cancelled`), `Created At`.
3. **Slot Sheet (`appointment_slots!A1:Z5000`)**:
   - `Slot ID`, `Doctor ID`, `Doctor Name`, `Date` (`YYYY-MM-DD`), `Start Time`, `End Time`, `Status` (`Available`/`Booked`/`Unavailable`), `Patient ID`, `Token No`, `Booked At`.

---

## 3. Rescheduling Architecture & Safe Execution Flow

### Constraints & Safety Guarantees:
- **Zero Loss Booking Guarantee**: The old slot is **never** released before the new slot has been locked and confirmed.
- **Atomic-Like Ordering**:
  1. Validate appointment is eligible (`Booking Status` in `{"Confirmed", "Pending"}`). Completed or Cancelled appointments cannot be rescheduled.
  2. Locate the existing appointment and its associated old slot (`Token No`, `Patient ID`, or `Doctor + Date + Time`).
  3. Validate new slot: must exist, must be for the same doctor, must currently be `Available`.
  4. Book new slot (`new_slot_id`) for patient and token using `SlotRepository._booking_lock`.
  5. Update the existing appointment row in `patient` sheet with `new_date` and `new_time`. Preserve `Patient ID`, `Token No`, `Payment Status`, and `Amount`.
  6. Release old slot (`old_slot_id`) only after the new slot and patient record are verified.
  7. If new slot booking fails, abort with clear message; existing appointment and old slot remain completely untouched.

---

## 4. Cancellation Architecture & Safe Execution Flow

### Constraints & Safety Guarantees:
- **History Preservation**: Appointment records are **never deleted**. Status is updated to `Cancelled`.
- **Payment Safety**: No automatic refund is made or claimed; `Payment Status` remains intact for clinic auditing.
- **Slot Release**: The booked slot in `appointment_slots` is safely released back to `Available`.
- **Confirmation Required**: Both Telegram and CRM require explicit confirmation before cancellation occurs.

---

## 5. Telegram Conversational Experience & Intent Routing

### Intent Routing Engine:
- `appointment_reschedule`: Natural triggers ("reschedule", "change appointment", "prepone", "postpone", "date badal", "time badal", "appointment change").
- `appointment_cancel`: Natural triggers ("cancel", "cancellation", "radd", "hatao", "cancel appointment").
- `patient_appointments`: Natural triggers ("my appointment", "my appointments", "meri appointment", "upcoming appointments", "check appointment").
- `doctor_availability`: Doctor factual free slots ("Dr Arjun kab available hain?", "Kal Dr Arjun free hain?", "Aur kab free hain?").
- `doctor_list`: Discovery queries ("Who are your doctors?", "Doctor ki list dikhao").
- `appointment_booking`: Initiates new booking flow.
- `clinic_information` & `other_help`: Answers questions with clinic context and friendly receptionist persona.

### Rescheduling & Cancellation Conversational Flow:
1. Patient Identification:
   - If phone/token is in session state, look up patient's active upcoming appointments.
   - If not in state, politely ask: *"Please provide your registered phone number or appointment token so I can look up your appointment."*
2. Appointment Selection:
   - If multiple appointments: display buttons with Doctor, Date, Time, Token.
   - If single appointment: display details and ask confirmation to proceed.
3. Rescheduling:
   - Ask preferred date. Check actual availability. Show available times.
   - Before applying change, show summary comparison:
     - Old appointment: Date, Time
     - New appointment: Date, Time
     - Buttons: `[Confirm Reschedule]`, `[Keep Existing Appointment]`.
4. Cancellation:
   - Show appointment details and ask:
     - *"Are you sure you want to cancel this appointment?"*
     - Buttons: `[Confirm Cancellation]`, `[Keep Appointment]`.

---

## 6. Doctor Fuzzy Matching & Date Parsing Enhancements

1. **Doctor Name Matching (`app/tools/doctors.py`)**:
   - Normalize prefixes ("dr", "doctor", "dr.", punctuation, extra spaces).
   - Normalize phonetic/transcription variants ("sufan" $\rightarrow$ "sufian", "sufiyan" $\rightarrow$ "sufian").
   - Match first names ("arjun" $\rightarrow$ "Dr. Arjun Mehta", "sana" $\rightarrow$ "Dr. Sana Khan").
   - Resolve ambiguity: if score differential $< 0.08$, present matches as selection buttons; never guess blindly.
2. **Date Parsing (`app/tools/date_utils.py`)**:
   - English: "today", "tomorrow", "day after tomorrow", "this Friday", "next Monday", "30 September", "2026-10-05".
   - Hindi/Hinglish: "aaj", "kal", "parso", "agle Monday", "agle somvar", "is Friday", "kal subah", "kal shaam", "kal dopahar".
   - Timezone-aware using clinic local time (`Asia/Kolkata`).

---

## 7. CRM Frontend & Backend API

### New Endpoints:
- `POST /api/admin/appointments/{appointment_id}/reschedule`:
  - Request: `{"new_slot_id": "...", "new_date": "...", "new_time": "..."}`
  - Response: `{success: true, appointment: {...}}`
- `POST /api/admin/appointments/{appointment_id}/cancel`:
  - Request: `{"reason": "..."}`
  - Response: `{success: true, appointment_id: "...", status: "Cancelled"}`

### CRM UI:
- **Reschedule Modal**:
  - Displays current appointment (Doctor, Date, Time, Token).
  - Date picker to browse target dates.
  - Dynamically fetches and displays real available slots for that doctor.
  - Preview Old vs New appointment with confirmation.
- **Cancel Modal**:
  - Displays appointment details with warning.
  - Explicit confirmation button before status update.

---

## 8. Testing & Validation Plan

1. **Unit & Integration Tests (`tests/test_reschedule_cancel.py`)**:
   - Reschedule with valid slot: verifies slot booking, appointment update, and old slot release.
   - Reschedule with already-booked slot: fails safely without touching existing appointment.
   - Reschedule completed or cancelled appointment: rejected with 400.
   - Cancel appointment: updates status to `Cancelled`, releases slot, preserves patient row.
   - Cancel completed appointment: rejected.
   - Non-existent appointment / slot safety handling.
2. **Telegram Conversational Tests**:
   - Intent recognition for Hindi, Hinglish, and English ("Meri appointment reschedule karni hai", "cancel my appointment", "kal dr arjun free hain?").
   - Date parsing for "kal", "parso", "agle monday", "kal subah".
   - Interactive button callbacks (`reschedule_confirm`, `cancel_confirm`, `reschedule_slot:...`).
3. **Regression Tests**:
   - All 196 tests in test suite pass with 0 failures (`python -m pytest tests/`).

---

## 9. Implementation & Verification Status

- [x] **CrmService Reschedule & Cancel Business Logic**: Implemented zero-loss atomic slot reservation, patient record update, old slot release, and cancellation with slot release.
- [x] **Admin REST API**: `POST /api/admin/appointments/{id}/reschedule` and `POST /api/admin/appointments/{id}/cancel` wired with auth, validation, and error reporting.
- [x] **Clinic CRM Frontend**: Interactive Reschedule Modal (date picker, live slot fetching, preview, submit) and Cancel Modal (warning, reason input, confirm) added in `appointments.js` and `api.js`.
- [x] **Telegram Intent Classification**: Multi-lingual router in `router.py` accurately routes reschedule, cancel, and appointment inquiries in English, Hindi, and Hinglish.
- [x] **LangGraph Conversational Receptionist**: `reschedule_node`, `cancel_node`, and `my_appointments_node` implemented with multi-step flows, slot chips, and clear confirmations in `nodes.py`.
- [x] **Telegram Keyboards & Handlers**: Inline menus for appointment selection, slot selection, and explicit confirmations added in `keyboards.py` and `handlers.py`.
- [x] **Automated Test Suite**: Added `tests/test_reschedule_cancel.py` covering all flows. Full suite of 196 tests passing.
