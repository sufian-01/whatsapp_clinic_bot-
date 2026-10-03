# Performance Audit: Clinic CRM & Telegram Chatbot
**Project:** Clinic Telegram AI Chatbot + Admin CRM (`D:\telegram_bot`)  
**Author:** Senior Backend & Frontend Performance Engineering  
**Date:** October 2026  
**Status:** Audit Complete  

---

## Executive Summary

An in-depth performance audit of the Clinic Management System (`D:\telegram_bot`) was conducted across its FastAPI backend, Google Sheets data repositories, JSON persistence modules, and the vanilla ES-module frontend SPA.

The audit identified critical bottlenecks responsible for slow page loads, occasional UI freezes on `"Loading..."`, redundant network calls, and CPU spikes during routine workflows.

---

## Comprehensive Bottleneck Analysis

### 1. Doctor Portal Views Freezing on "Loading..." During Network Latency or Errors
- **Problem:** When navigating to Doctor Portal views (My Appointments, My Patients, My Slots, Prescriptions), the tables initially render static strings such as `<tr><td colspan="8" class="empty-state">Loading assigned patients...</td></tr>`. If the API request times out or encounters an error, the view displays a toast, but never updates the `<tbody>`. The user remains permanently locked on `"Loading..."`.
- **Root Cause:** Missing skeleton loaders, missing error state rendering in `catch` blocks, and absence of interactive retry buttons in `doctor_appointments.js`, `doctor_patients.js`, `doctor_slots.js`, and `doctor_prescriptions.js`.
- **Affected Endpoint/Page:**
  - `frontend/js/views/doctor_appointments.js` (`#doctor-appointments`)
  - `frontend/js/views/doctor_patients.js` (`#doctor-patients`)
  - `frontend/js/views/doctor_slots.js` (`#doctor-slots`)
  - `frontend/js/views/doctor_prescriptions.js` (`#doctor-prescriptions`)
- **Expected Impact:** 100% elimination of stuck loading screens; immediate visual skeleton feedback and responsive error-retry recovery.
- **Proposed Solution:** Implement `renderTableSkeletons(cols, rows)` during data fetching. In the `catch` block, render a clean error message with an interactive `🔄 Retry Loading` button.
- **Risk Level:** Very Low.

---

### 2. Rapid Keystroke Race Conditions & Excessive Server Requests in Searches
- **Problem:** When users or doctors type in search fields across Doctor Appointments, Doctor Patients, Doctor Prescriptions, and Admin Prescriptions, an un-debounced, un-cancelable asynchronous request is dispatched on every keystroke. Multiple concurrent requests travel over the network, leading to race conditions where an earlier, slower request resolves after a later request and overwrites current search results with stale data.
- **Root Cause:** Direct `addEventListener("input", () => this.loadData())` without input debouncing or request cancellation via `AbortController`.
- **Affected Endpoint/Page:**
  - `GET /api/doctor/appointments`
  - `GET /api/doctor/patients`
  - `GET /api/doctor/slots`
  - `GET /api/doctor/prescriptions`
  - `GET /api/admin/prescriptions`
- **Expected Impact:** 80–90% reduction in unnecessary search API calls. Guaranteed correctness with zero out-of-order response overwrites.
- **Proposed Solution:** Attach an `AbortController` (`this._abortController?.abort()`) to cancel in-flight search requests on new input, and debounce input events with a 250ms delay.
- **Risk Level:** Low.

---

### 3. $O(M \times N)$ Linear Prescription Scans in Doctor Workflow Endpoints
- **Problem:** In `crm_service.py`, `get_doctor_appointments()` iterates through all doctor appointments and queries `self.prescriptions.get_prescription_by_appointment(tkn)`. `PrescriptionService.get_prescription_by_appointment()` performs a linear scan over `self._prescriptions.values()`. For $M$ appointments and $N$ prescriptions, this results in $M \times N$ string comparisons inside a synchronized `RLock` on every doctor dashboard and appointments load.
- **Root Cause:** Lack of an indexed lookup by `appointment_id` in `PrescriptionService`.
- **Affected Endpoint/Page:**
  - `GET /api/doctor/appointments`
  - `GET /api/doctor/dashboard`
  - `GET /api/doctor/appointments/{id}`
- **Expected Impact:** Reduces prescription lookup time from $O(M \times N)$ to $O(M)$ $O(1)$ dictionary lookups, eliminating CPU spikes on clinical views.
- **Proposed Solution:** Maintain an in-memory index `self._by_appointment: dict[str, str]` (mapping `appointment_id.casefold()` to `prescription_id`) in `PrescriptionService`, automatically maintained upon load, draft save, and finalization.
- **Risk Level:** Very Low.

---

### 4. Blocking Synchronous Email Dispatch in Appointment Creation
- **Problem:** When an appointment is booked via CRM manual booking (`create_appointment_manual`), it performs the sheet transaction, records the audit log, and then synchronously calls `self.gmail.send_appointment_confirmation_email(...)`. If the external mail provider takes 2–5 seconds or experiences network latency, the HTTP booking request blocks until email delivery finishes.
- **Root Cause:** Synchronous execution of external network I/O after the critical database transaction is already committed.
- **Affected Endpoint/Page:** `POST /api/admin/appointments`.
- **Expected Impact:** Cuts 1,000ms – 5,000ms off manual appointment booking latency.
- **Proposed Solution:** Allow non-blocking background dispatch for confirmation emails once the booking transaction has been committed and verified.
- **Risk Level:** Low.

---

### 5. Uncached ReportLab PDF Generation for Finalized Prescriptions
- **Problem:** Generating PDF documents via ReportLab requires font metrics calculation, layout calculations, canvas operations, and disk stream encoding. Currently, calling `/prescriptions/{id}/pdf` or `/prescriptions/{id}/email` recalculates the PDF from scratch every time, even if the prescription is finalized and has not changed.
- **Root Cause:** Absence of disk caching for generated PDFs of finalized prescriptions.
- **Affected Endpoint/Page:**
  - `GET /api/doctor/prescriptions/{id}/pdf`
  - `POST /api/doctor/prescriptions/{id}/email`
  - `GET /api/admin/prescriptions/{id}/pdf`
- **Expected Impact:** Subsequent PDF downloads drop from 300–800ms to < 5ms (instant file streaming).
- **Proposed Solution:** Save generated PDFs as `f"{prescription_id}_v{version}.pdf"`. If the file exists and the prescription status is finalized or amended and version matches, stream the existing file directly.
- **Risk Level:** Very Low.

---

### 6. Google Sheets API Latency & Repeated Sheet Reads
- **Problem:** Google Sheets REST API introduces 250ms – 1,200ms of latency per read. Repeated sequential calls when browsing between CRM views cause sluggish navigation and risk Google Sheets HTTP 429 quota exhaustion.
- **Root Cause:** External SaaS latency of Google Sheets API.
- **Affected Endpoint/Page:**
  - `GET /api/admin/dashboard/stats`
  - `GET /api/admin/patients`
  - `GET /api/admin/doctors`
  - `GET /api/admin/slots`
- **Expected Impact:** Consecutive reads within TTL execute in < 1ms (>99.5% latency reduction).
- **Proposed Solution:** Ensure thread-safe TTL caching (`RLock()`) in `DoctorDirectory` (60s), `PatientRepository` (20s), and `SlotRepository` (20s). Enforce immediate write-through cache invalidation on mutations (`create`, `update`, `cancel`, `reschedule`, `payment`, `status_toggle`). Live slot booking must strictly bypass cache using `force_refresh=True` inside `_booking_lock` to prevent double-booking.
- **Risk Level:** Very Low.

---

### 7. Frontend API Client Missing Signal & Options Passthrough
- **Problem:** `API.listAppointments`, `API.getDoctorAppointments`, `API.getDoctorPatients`, `API.getDoctorSlots`, `API.getDoctorPrescriptions`, and `API.getAdminPrescriptions` only accepted `params` and omitted `options`. Callers could not pass `signal` (from `AbortController`) or custom `timeout`.
- **Root Cause:** Restrictive method parameter signatures in `frontend/js/api.js`.
- **Affected Endpoint/Page:** Frontend API layer (`frontend/js/api.js`).
- **Expected Impact:** Enables uniform request cancellation and timeout configuration across all views.
- **Proposed Solution:** Update all `API` query methods to accept `(params = {}, options = {})` and forward `...options` into `request()`.
- **Risk Level:** Very Low.

---

### 8. Admin Appointments Table Missing Skeleton Loaders & Retry UI
- **Problem:** When loading `#appointments`, the table displays a static `Loading appointments...` message. If the endpoint encounters an error, the error is displayed without an interactive retry button.
- **Root Cause:** Lack of table skeleton rows and retry recovery handling in `appointments.js`.
- **Affected Endpoint/Page:** `frontend/js/views/appointments.js` (`#appointments`).
- **Expected Impact:** Consistent skeleton loading experience and 1-click retry recovery.
- **Proposed Solution:** Render skeleton table rows prior to data fetch, and provide an interactive retry button if the request fails.
- **Risk Level:** Very Low.

---

## Summary Matrix

| # | Bottleneck | Layer | Root Cause | Proposed Solution | Risk Level |
|---|---|---|---|---|---|
| 1 | Doctor Portal Stuck on "Loading..." | Frontend | Missing skeletons, error states & retry buttons | Add skeleton loaders & retry recovery in doctor views | Low |
| 2 | Un-debounced Search Race Conditions | Frontend | Un-debounced input events without AbortController | Debounce (250ms) + AbortController cancellation | Low |
| 3 | $O(M \times N)$ Linear Prescription Scans | Backend | Unindexed prescription lookups by appointment | Build in-memory appointment-to-prescription index | Very Low |
| 4 | Synchronous Email Booking Delay | Backend | Email sent inline before HTTP response returns | Non-blocking background email dispatch | Low |
| 5 | Repeated PDF Generation Overhead | Backend | No caching of finalized immutable PDFs | File-based PDF caching by ID and version | Very Low |
| 6 | Google Sheets Roundtrip Overhead | Backend | Network latency of external Sheets API | Multi-tier TTL caching + immediate write invalidation | Very Low |
| 7 | API Client Missing Signal Passthrough | Frontend | API methods dropping `options` parameter | Forward `(params, options)` to `request()` | Very Low |
| 8 | Appointments View Lacks Skeleton / Retry | Frontend | Static loading text without retry action | Add table skeletons & retry button in appointments view | Very Low |

