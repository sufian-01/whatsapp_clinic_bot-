/**
 * API client module for Clinic CRM Admin.
 */

import { Auth } from "./auth.js";

const BASE_URL = "/api/admin";

async function request(path, options = {}) {
  const url = new URL(BASE_URL + path, window.location.origin);
  if (options.params) {
    Object.entries(options.params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        url.searchParams.append(k, v);
      }
    });
  }

  const headers = {
    "Accept": "application/json",
    ...options.headers,
  };

  const token = Auth.getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }

  const response = await fetch(url.toString(), {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Session expired or invalid
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
  async listPatients(params = {}) {
    return request("/patients", { params });
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
  async listDoctors(params = {}) {
    return request("/doctors", { params });
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
  async listAppointments(params = {}) {
    return request("/appointments", { params });
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
  async listSlots(params = {}) {
    return request("/slots", { params });
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
  async listPayments(params = {}) {
    return request("/payments", { params });
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
};

