/**
 * API client module for Clinic CRM Admin.
 */

import { Auth } from "./auth.js";

const BASE_URL = "/api/admin";

const inflightGetRequests = new Map();

async function executeRequest(url, options, token) {
  const headers = {
    "Accept": "application/json",
    ...options.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let body = options.body;
  if (body && typeof body === "object" && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }

  // Timeout & cancellation handling (default: 15s)
  const timeoutMs = options.timeout !== undefined ? options.timeout : 15000;
  const controller = new AbortController();
  let timedOut = false;
  let timerId = null;

  if (timeoutMs > 0) {
    timerId = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
  }

  // Chain caller signal if provided
  if (options.signal) {
    if (options.signal.aborted) {
      if (timerId) clearTimeout(timerId);
      throw new DOMException("Request was cancelled", "AbortError");
    }
    options.signal.addEventListener("abort", () => {
      controller.abort(options.signal.reason);
    }, { once: true });
  }

  try {
    const fetchOptions = {
      ...options,
      headers,
      body,
      signal: controller.signal,
    };
    delete fetchOptions.params;
    delete fetchOptions.timeout;
    delete fetchOptions.noDedupe;

    const response = await fetch(url.toString(), fetchOptions);

    if (response.status === 401) {
      Auth.clearSession();
      if (!window.location.pathname.includes("login.html")) {
        window.location.href = "/admin/login.html";
      }
      throw new Error("Session expired. Please log in again.");
    }

    let data;
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      let errorMsg = "An unexpected error occurred.";
      if (data && data.detail) {
        if (Array.isArray(data.detail)) {
          errorMsg = data.detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
        } else {
          errorMsg = data.detail;
        }
      } else if (typeof data === "string") {
        errorMsg = data;
      }
      const err = new Error(errorMsg);
      err.status = response.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (err) {
    if (timedOut) {
      const timeoutErr = new Error("Request timed out. Please check your connection and try again.");
      timeoutErr.name = "TimeoutError";
      throw timeoutErr;
    }
    throw err;
  } finally {
    if (timerId) {
      clearTimeout(timerId);
    }
  }
}

async function request(path, options = {}) {
  const prefix = (path.startsWith("/doctor/") || path === "/doctor") ? "/api" : BASE_URL;
  const url = new URL(prefix + path, window.location.origin);
  if (options.params) {
    Object.entries(options.params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        url.searchParams.append(k, v);
      }
    });
  }

  const token = Auth.getToken();
  const method = (options.method || "GET").toUpperCase();

  // In-flight GET request deduplication
  const isGet = method === "GET";
  if (isGet && !options.noDedupe) {
    const dedupeKey = `${url.toString()}|${token || ""}`;
    if (inflightGetRequests.has(dedupeKey)) {
      return inflightGetRequests.get(dedupeKey);
    }

    const reqPromise = executeRequest(url, options, token).finally(() => {
      inflightGetRequests.delete(dedupeKey);
    });

    inflightGetRequests.set(dedupeKey, reqPromise);
    return reqPromise;
  }

  return executeRequest(url, options, token);
}

export const API = {
  // Auth
  async login(username, password) {
    return request("/auth/login", {
      method: "POST",
      body: { username, password },
    });
  },

  async logout() {
    return Auth.logout();
  },

  async getMe() {
    return request("/auth/me");
  },

  // Dashboard
  async getDashboardStats(today) {
    return request("/dashboard/stats", { params: { today } });
  },

  async getTodayAppointments(today) {
    return request("/dashboard/today-appointments", { params: { today } });
  },

  async getRecentPatients(limit = 5) {
    return request("/dashboard/recent-patients", { params: { limit } });
  },

  // Patients
  async listPatients(params = {}, options = {}) {
    return request("/patients", { params, ...options });
  },

  async getPatient(patientId) {
    return request(`/patients/${encodeURIComponent(patientId)}`);
  },

  async createPatient(payload) {
    return request("/patients", {
      method: "POST",
      body: payload,
    });
  },

  async updatePatient(patientId, payload) {
    return request(`/patients/${encodeURIComponent(patientId)}`, {
      method: "PUT",
      body: payload,
    });
  },

  async getPatientAppointments(patientId) {
    return request(`/patients/${encodeURIComponent(patientId)}/appointments`);
  },

  async getPatientPayments(patientId) {
    return request(`/patients/${encodeURIComponent(patientId)}/payments`);
  },

  // Doctors
  async listDoctors(params = {}, options = {}) {
    return request("/doctors", { params, ...options });
  },

  async getDoctor(doctorId) {
    return request(`/doctors/${encodeURIComponent(doctorId)}`);
  },

  async createDoctor(payload) {
    return request("/doctors", {
      method: "POST",
      body: payload,
    });
  },

  async updateDoctor(doctorId, payload) {
    return request(`/doctors/${encodeURIComponent(doctorId)}`, {
      method: "PUT",
      body: payload,
    });
  },

  async setDoctorStatus(doctorId, status) {
    return request(`/doctors/${encodeURIComponent(doctorId)}/status`, {
      method: "PATCH",
      body: { status },
    });
  },

  async getDoctorAvailability(doctorId, fromDate) {
    return request(`/doctors/${encodeURIComponent(doctorId)}/availability`, {
      params: { from_date: fromDate },
    });
  },

  // Appointments
  async listAppointments(params = {}, options = {}) {
    return request("/appointments", { params, ...options });
  },

  async getAppointment(appointmentId) {
    return request(`/appointments/${encodeURIComponent(appointmentId)}`);
  },

  async updateAppointmentStatus(appointmentId, status) {
    return request(`/appointments/${encodeURIComponent(appointmentId)}/status`, {
      method: "PATCH",
      body: { status },
    });
  },

  async rescheduleAppointment(appointmentId, payload) {
    return request(`/appointments/${encodeURIComponent(appointmentId)}/reschedule`, {
      method: "POST",
      body: payload,
    });
  },

  async cancelAppointment(appointmentId, payload = {}) {
    return request(`/appointments/${encodeURIComponent(appointmentId)}/cancel`, {
      method: "POST",
      body: payload,
    });
  },

  // Calendar
  async getCalendarEvents(startDate, endDate, doctor = "") {
    return request("/calendar", {
      params: { start_date: startDate, end_date: endDate, doctor },
    });
  },

  // Slots
  async listSlots(params = {}, options = {}) {
    return request("/slots", { params, ...options });
  },

  async createSlot(payload) {
    return request("/slots", {
      method: "POST",
      body: payload,
    });
  },

  async updateSlot(slotId, payload) {
    return request(`/slots/${encodeURIComponent(slotId)}`, {
      method: "PUT",
      body: payload,
    });
  },

  async setSlotStatus(slotId, status) {
    return request(`/slots/${encodeURIComponent(slotId)}/status`, {
      method: "PATCH",
      body: { status },
    });
  },

  // Payments
  async listPayments(params = {}, options = {}) {
    return request("/payments", { params, ...options });
  },

  async getPayment(paymentId) {
    return request(`/payments/${encodeURIComponent(paymentId)}`);
  },

  async updatePaymentStatus(paymentId, status) {
    return request(`/payments/${encodeURIComponent(paymentId)}/status`, {
      method: "PATCH",
      body: { status },
    });
  },

  async recordPayment(paymentId, payload) {
    return request(`/payments/${encodeURIComponent(paymentId)}/record`, {
      method: "POST",
      body: payload,
    });
  },

  // Appointments (Manual Creation & Invoice)
  async createAppointment(payload) {
    return request("/appointments", {
      method: "POST",
      body: payload,
    });
  },

  getAppointmentInvoiceUrl(appointmentId) {
    return `${BASE_URL}/appointments/${encodeURIComponent(appointmentId)}/invoice`;
  },

  // Patients (Dedup & Deactivation)
  async checkPatientDuplicates(phone = "", email = "") {
    return request("/patients/check-duplicates", {
      params: { phone, email },
    });
  },

  async createPatientWithDedup(payload, force = false) {
    return request(`/patients/with-dedup?force=${force}`, {
      method: "POST",
      body: payload,
    });
  },

  async deactivatePatient(patientId) {
    return request(`/patients/${encodeURIComponent(patientId)}/deactivate`, {
      method: "POST",
    });
  },

  // Doctors (Safety Check)
  async checkDoctorDeactivation(doctorId) {
    return request(`/doctors/${encodeURIComponent(doctorId)}/deactivation-check`);
  },

  // Dashboard & Analytics
  async getAnalytics(params = {}) {
    return request("/dashboard/analytics", { params });
  },

  // Reports
  getReportExportUrl(type, startDate = "", endDate = "") {
    const url = new URL(`${BASE_URL}/reports/export`, window.location.origin);
    url.searchParams.append("type", type);
    if (startDate) url.searchParams.append("start_date", startDate);
    if (endDate) url.searchParams.append("end_date", endDate);
    return url.toString();
  },

  // Audit Logs
  async getAuditLogs(params = {}) {
    return request("/audit-logs", { params });
  },

  // Auth: Change Password
  async changePassword(oldPassword, newPassword) {
    return request("/auth/change-password", {
      method: "POST",
      body: { old_password: oldPassword, new_password: newPassword },
    });
  },

  // Admin: Doctor Accounts Management
  async getDoctorAccounts() {
    return request("/doctor-accounts");
  },

  async createDoctorAccount(payload) {
    return request("/doctor-accounts", {
      method: "POST",
      body: payload,
    });
  },

  async getDoctorAccount(username) {
    return request(`/doctor-accounts/${encodeURIComponent(username)}`);
  },

  async updateDoctorAccount(username, payload) {
    return request(`/doctor-accounts/${encodeURIComponent(username)}`, {
      method: "PATCH",
      body: payload,
    });
  },

  async setDoctorAccountStatus(username, status) {
    return request(`/doctor-accounts/${encodeURIComponent(username)}/status`, {
      method: "PATCH",
      body: { status },
    });
  },

  async resetDoctorPassword(username, newPassword) {
    return request(`/doctor-accounts/${encodeURIComponent(username)}/reset-password`, {
      method: "POST",
      body: { new_password: newPassword },
    });
  },

  // Admin: Prescriptions Oversight
  async getAdminPrescriptions(params = {}, options = {}) {
    return request("/prescriptions", { params, ...options });
  },

  async getAdminPrescription(id) {
    return request(`/prescriptions/${encodeURIComponent(id)}`);
  },

  getAdminPrescriptionPdfUrl(id) {
    return `${BASE_URL}/prescriptions/${encodeURIComponent(id)}/pdf`;
  },

  // Doctor Portal Methods
  async getDoctorProfile() {
    return request("/doctor/profile");
  },

  async getDoctorDashboard(today, options = {}) {
    return request("/doctor/dashboard", { params: { today }, ...options });
  },

  async getDoctorAppointments(params = {}, options = {}) {
    return request("/doctor/appointments", { params, ...options });
  },

  async getDoctorAppointment(id) {
    return request(`/doctor/appointments/${encodeURIComponent(id)}`);
  },

  async getDoctorPatients(params = {}, options = {}) {
    return request("/doctor/patients", { params, ...options });
  },

  async getDoctorPatientDetail(id) {
    return request(`/doctor/patients/${encodeURIComponent(id)}`);
  },

  async getDoctorSlots(params = {}, options = {}) {
    return request("/doctor/slots", { params, ...options });
  },

  async createDoctorSlot(payload) {
    return request("/doctor/slots", {
      method: "POST",
      body: payload,
    });
  },

  async updateDoctorSlot(slotId, payload) {
    return request(`/doctor/slots/${encodeURIComponent(slotId)}`, {
      method: "PATCH",
      body: payload,
    });
  },

  async deleteDoctorSlot(slotId) {
    return request(`/doctor/slots/${encodeURIComponent(slotId)}`, {
      method: "DELETE",
    });
  },

  async getDoctorPrescriptions(params = {}, options = {}) {
    return request("/doctor/prescriptions", { params, ...options });
  },

  async savePrescriptionDraft(payload) {
    return request("/doctor/prescriptions", {
      method: "POST",
      body: payload,
    });
  },

  async getDoctorPrescription(id) {
    return request(`/doctor/prescriptions/${encodeURIComponent(id)}`);
  },

  async finalizePrescription(id) {
    return request(`/doctor/prescriptions/${encodeURIComponent(id)}/finalize`, {
      method: "POST",
    });
  },

  async amendPrescription(id, payload) {
    return request(`/doctor/prescriptions/${encodeURIComponent(id)}/amend`, {
      method: "POST",
      body: payload,
    });
  },

  getDoctorPrescriptionPdfUrl(id) {
    return `/api/doctor/prescriptions/${encodeURIComponent(id)}/pdf`;
  },

  async emailPrescription(id, recipientEmail = "", recipientType = "patient") {
    return request(`/doctor/prescriptions/${encodeURIComponent(id)}/email`, {
      method: "POST",
      body: { recipient_email: recipientEmail, recipient_type: recipientType },
    });
  },
};

