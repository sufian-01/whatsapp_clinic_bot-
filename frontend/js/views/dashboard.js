/**
 * Dashboard View Module - Clinic Operations Overview.
 */

import { API } from "../api.js";
import { escapeHtml, formatCurrency, formatDate, formatTime, renderBadge, showToast } from "../utils.js";
import { AppointmentsView } from "./appointments.js";
import { PatientsView } from "./patients.js";

export const DashboardView = {
  container: null,

  async init() {
    this.container = document.getElementById("view-dashboard");
    if (!this.container) return;
    await this.render();
  },

  async render() {
    this.container.innerHTML = `
      <div class="view-header" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom: 24px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">Clinical Operations Overview</h2>
          <p style="font-size: 13px; color: var(--text-secondary);">Real-time aggregated metrics and patient flow from clinic Google Sheets</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
          <button id="quick-book-appt-btn" class="btn btn-primary btn-sm">
            <span>➕</span> Book Appointment
          </button>
          <button id="quick-add-patient-btn" class="btn btn-secondary btn-sm">
            <span>👤</span> Register Patient
          </button>
          <button id="dashboard-refresh-btn" class="btn btn-secondary btn-sm" title="Refresh Live Data">
            <span>🔄</span> Refresh
          </button>
        </div>
      </div>

      <!-- 6 Primary Metric Cards -->
      <div id="dashboard-metrics-container" class="metrics-grid">
        <div class="metric-card"><div class="metric-label">Loading stats...</div></div>
      </div>

      <!-- Main Dashboard Split Layout -->
      <div class="dashboard-split-layout">
        <!-- Main Column: Today's Appointments & Recent Appointments -->
        <div class="dashboard-main-col" style="display:flex; flex-direction:column; gap:24px;">
          <!-- Card 1: Today's Appointments -->
          <div class="card">
            <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="card-title">📅 Today's Appointments</span>
                <span id="today-count-badge" class="badge badge-info">0 Scheduled</span>
              </div>
              <span id="today-date-badge" class="badge badge-completed">Today</span>
            </div>
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Token</th>
                    <th>Patient Name</th>
                    <th>Doctor</th>
                    <th>Time</th>
                    <th>Status</th>
                    <th>Payment</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="today-appointments-tbody">
                  <tr><td colspan="7" class="empty-state-cell">Loading today's schedule...</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Card 2: Recent Appointments -->
          <div class="card">
            <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
              <span class="card-title">📋 Recent Appointments</span>
              <a href="#appointments" class="btn btn-secondary btn-sm" style="font-size:12px; padding:4px 10px;">
                View All Appointments →
              </a>
            </div>
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Token</th>
                    <th>Patient Name</th>
                    <th>Doctor</th>
                    <th>Date</th>
                    <th>Time</th>
                    <th>Status</th>
                    <th>Payment</th>
                  </tr>
                </thead>
                <tbody id="recent-appointments-tbody">
                  <tr><td colspan="7" class="empty-state-cell">Loading recent appointments...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Side Column: Clinical Capacity & Recent Patients -->
        <div class="dashboard-side-col" style="display:flex; flex-direction:column; gap:24px;">
          <!-- Card: Clinical Capacity & Navigation -->
          <div class="card">
            <div class="card-header">
              <span class="card-title">🏥 Clinical Capacity</span>
            </div>
            <div class="card-body" style="padding: 16px;">
              <div style="display:flex; justify-content:space-between; align-items:center; padding-bottom: 12px; border-bottom: 1px solid var(--border-light);">
                <span style="font-size:13px; color:var(--text-secondary);">Active Doctors:</span>
                <span id="active-doctors-stat" style="font-weight:700; font-size:14px; color:var(--text-main);">-</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:center; padding: 12px 0; border-bottom: 1px solid var(--border-light);">
                <span style="font-size:13px; color:var(--text-secondary);">Available Slots:</span>
                <span id="available-slots-stat" style="font-weight:700; font-size:14px; color:var(--success-text);">-</span>
              </div>
              <div style="display:flex; justify-content:space-between; align-items:center; padding-top: 12px;">
                <span style="font-size:13px; color:var(--text-secondary);">Total Revenue:</span>
                <span id="total-revenue-stat" style="font-weight:700; font-size:14px; color:var(--primary);">-</span>
              </div>

              <div style="margin-top: 16px; padding-top: 14px; border-top: 1px dashed var(--border-light); display:flex; flex-direction:column; gap:8px;">
                <a href="#calendar" class="btn btn-secondary btn-sm" style="text-align:center; justify-content:center;">
                  🗓️ View Visual Calendar
                </a>
                <a href="#slots" class="btn btn-secondary btn-sm" style="text-align:center; justify-content:center;">
                  ⏱️ Manage Slots Master
                </a>
              </div>
            </div>
          </div>

          <!-- Card: Recent Patients -->
          <div class="card">
            <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
              <span class="card-title">👥 Recent Patients</span>
              <a href="#patients" class="btn btn-secondary btn-sm" style="font-size:12px; padding:4px 10px;">
                Directory →
              </a>
            </div>
            <div class="card-body" id="recent-patients-list" style="padding-top: 8px; padding-bottom: 8px;">
              <div style="color: var(--text-muted); font-size: 13px;">Loading recent patients...</div>
            </div>
          </div>
        </div>
      </div>
    `;

    // Event listeners for quick action buttons
    document.getElementById("dashboard-refresh-btn")?.addEventListener("click", () => this.loadData());
    document.getElementById("quick-book-appt-btn")?.addEventListener("click", () => AppointmentsView.openBookAppointmentModal());
    document.getElementById("quick-add-patient-btn")?.addEventListener("click", () => PatientsView.openAddPatientModal());

    // Auto-refresh when an appointment or patient is updated
    window.addEventListener("crm:appointment-changed", () => {
      if (document.getElementById("view-dashboard")?.classList.contains("active")) {
        this.loadData();
      }
    });
    window.addEventListener("crm:patient-changed", () => {
      if (document.getElementById("view-dashboard")?.classList.contains("active")) {
        this.loadData();
      }
    });

    await this.loadData();
  },

  async loadData() {
    try {
      const [stats, todayAppts, recentPatients, recentApptsRes] = await Promise.all([
        API.getDashboardStats(),
        API.getTodayAppointments(),
        API.getRecentPatients(6),
        API.listAppointments({ page: 1, page_size: 6 }),
      ]);

      this.renderMetrics(stats);
      this.renderTodayAppointments(todayAppts);
      this.renderRecentAppointments(recentApptsRes?.appointments || []);
      this.renderRecentPatients(recentPatients);
    } catch (err) {
      showToast(err.message || "Failed to load dashboard data", "error");
    }
  },

  renderMetrics(stats) {
    const container = document.getElementById("dashboard-metrics-container");
    if (!container || !stats) return;

    container.innerHTML = `
      <!-- 1. Total Patients -->
      <div class="metric-card">
        <div class="metric-card-header">
          <span class="metric-label">Total Patients</span>
          <div class="metric-icon-wrap" style="background:#eff6ff; color:#2563eb;">👥</div>
        </div>
        <div class="metric-value">${stats.total_patients ?? 0}</div>
        <div class="metric-subtext">Registered across records</div>
      </div>

      <!-- 2. Total Appointments -->
      <div class="metric-card">
        <div class="metric-card-header">
          <span class="metric-label">Total Appointments</span>
          <div class="metric-icon-wrap" style="background:#f3e8ff; color:#7e22ce;">📋</div>
        </div>
        <div class="metric-value">${stats.total_appointments ?? 0}</div>
        <div class="metric-subtext">All-time clinic bookings</div>
      </div>

      <!-- 3. Today's Appointments -->
      <div class="metric-card">
        <div class="metric-card-header">
          <span class="metric-label">Today's Appointments</span>
          <div class="metric-icon-wrap" style="background:#ecfdf5; color:#059669;">📅</div>
        </div>
        <div class="metric-value">${stats.today_appointments ?? 0}</div>
        <div class="metric-subtext">${stats.today_date ? formatDate(stats.today_date) : "Today"}</div>
      </div>

      <!-- 4. Upcoming Appointments -->
      <div class="metric-card">
        <div class="metric-card-header">
          <span class="metric-label">Upcoming</span>
          <div class="metric-icon-wrap" style="background:#e0f2fe; color:#0284c7;">⏳</div>
        </div>
        <div class="metric-value">${stats.upcoming_appointments ?? 0}</div>
        <div class="metric-subtext">Scheduled future visits</div>
      </div>

      <!-- 5. Completed Visits -->
      <div class="metric-card">
        <div class="metric-card-header">
          <span class="metric-label">Completed Visits</span>
          <div class="metric-icon-wrap" style="background:#dcfce7; color:#16a34a;">✅</div>
        </div>
        <div class="metric-value">${stats.completed_appointments ?? 0}</div>
        <div class="metric-subtext">Consulted & concluded</div>
      </div>

      <!-- 6. Pending Payments -->
      <div class="metric-card">
        <div class="metric-card-header">
          <span class="metric-label">Pending Payments</span>
          <div class="metric-icon-wrap" style="background:#fef3c7; color:#d97706;">💳</div>
        </div>
        <div class="metric-value">${stats.pending_payments ?? 0}</div>
        <div class="metric-subtext">Awaiting fee collection</div>
      </div>
    `;

    // Side card capacity stats
    const docEl = document.getElementById("active-doctors-stat");
    if (docEl) docEl.textContent = `${stats.active_doctors ?? 0} / ${stats.total_doctors ?? 0}`;

    const slotEl = document.getElementById("available-slots-stat");
    if (slotEl) slotEl.textContent = `${stats.available_slots ?? 0} slots`;

    const revEl = document.getElementById("total-revenue-stat");
    if (revEl) revEl.textContent = formatCurrency(stats.total_revenue ?? 0);

    const dateBadge = document.getElementById("today-date-badge");
    if (dateBadge && stats.today_date) {
      dateBadge.textContent = formatDate(stats.today_date);
    }

    const todayCountBadge = document.getElementById("today-count-badge");
    if (todayCountBadge) {
      todayCountBadge.textContent = `${stats.today_appointments ?? 0} Scheduled`;
    }
  },

  renderTodayAppointments(appts) {
    const tbody = document.getElementById("today-appointments-tbody");
    if (!tbody) return;

    if (!appts || appts.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state-cell" style="padding: 32px 16px; text-align: center;">
            <div style="font-size: 24px; margin-bottom: 8px;">📅</div>
            <div style="font-weight: 600; color: var(--text-main); margin-bottom: 4px;">No appointments scheduled for today</div>
            <div style="font-size: 12.5px; color: var(--text-muted); margin-bottom: 12px;">New appointments booked for today will appear here in real time.</div>
            <button class="btn btn-secondary btn-sm" id="empty-book-today-btn">
              <span>➕</span> Book Today's Appointment
            </button>
          </td>
        </tr>
      `;
      document.getElementById("empty-book-today-btn")?.addEventListener("click", () => AppointmentsView.openBookAppointmentModal());
      return;
    }

    tbody.innerHTML = appts.map((a) => {
      const token = a["Token No"] || a.token_no || "-";
      const name = a.Name || a.patient_name || "-";
      const doctor = a.Doctor || a.doctor || "-";
      const time = a["Appointment Time"] || a.time || "-";
      const status = a["Booking Status"] || a.Status || a.status || "Confirmed";
      const payStatus = a["Payment Status"] || a.payment_status || "Pending";
      const identifier = token !== "-" ? token : (a["Patient ID"] || a.patient_id);

      const canComplete = status.toLowerCase() === "confirmed" || status.toLowerCase() === "pending";

      return `
        <tr>
          <td style="font-weight:600; font-family:monospace;">${escapeHtml(token)}</td>
          <td>${escapeHtml(name)}</td>
          <td>${escapeHtml(doctor)}</td>
          <td>${escapeHtml(formatTime(time))}</td>
          <td>${renderBadge(status)}</td>
          <td>${renderBadge(payStatus)}</td>
          <td>
            ${canComplete ? `
              <button class="btn btn-secondary btn-sm complete-btn" data-id="${escapeHtml(identifier)}" title="Mark Completed">
                ✓ Complete
              </button>
            ` : `<span style="color:var(--text-muted); font-size:12px;">Completed</span>`}
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".complete-btn").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-id");
        await this.markCompleted(id);
      });
    });
  },

  renderRecentAppointments(appts) {
    const tbody = document.getElementById("recent-appointments-tbody");
    if (!tbody) return;

    if (!appts || appts.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state-cell" style="padding: 24px 16px; text-align: center;">
            <div style="color: var(--text-muted); font-size: 13px;">No recent appointments recorded.</div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = appts.map((a) => {
      const token = a["Token No"] || a.token_no || "-";
      const name = a.Name || a.patient_name || a.name || "-";
      const doctor = a.Doctor || a.doctor || "-";
      const date = a["Appointment Date"] || a.appointment_date || a.date || "-";
      const time = a["Appointment Time"] || a.appointment_time || a.time || "-";
      const status = a["Booking Status"] || a.Status || a.status || "Confirmed";
      const payStatus = a["Payment Status"] || a.payment_status || "Pending";

      return `
        <tr>
          <td style="font-weight:600; font-family:monospace;">${escapeHtml(token)}</td>
          <td>${escapeHtml(name)}</td>
          <td>${escapeHtml(doctor)}</td>
          <td>${escapeHtml(formatDate(date))}</td>
          <td>${escapeHtml(formatTime(time))}</td>
          <td>${renderBadge(status)}</td>
          <td>${renderBadge(payStatus)}</td>
        </tr>
      `;
    }).join("");
  },

  renderRecentPatients(patients) {
    const container = document.getElementById("recent-patients-list");
    if (!container) return;

    if (!patients || patients.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 24px 16px; color: var(--text-muted);">
          <div style="font-size: 24px; margin-bottom: 8px;">👥</div>
          <div style="font-weight: 600; color: var(--text-main); margin-bottom: 4px;">No patients found</div>
          <div style="font-size: 12px; margin-bottom: 12px;">Registered patients will appear here.</div>
          <button class="btn btn-secondary btn-sm" id="empty-add-patient-btn">
            <span>➕</span> Register New Patient
          </button>
        </div>
      `;
      document.getElementById("empty-add-patient-btn")?.addEventListener("click", () => PatientsView.openAddPatientModal());
      return;
    }

    container.innerHTML = patients.map((p) => {
      const name = p.Name || p.name || "Patient";
      const phone = p.Phone || p.phone || "-";
      const doctor = p.Doctor || p.doctor || "-";
      const apptDate = p["Appointment Date"] || p.appointment_date || "-";
      const initials = name.split(" ").map((n) => n[0]).join("").substring(0, 2).toUpperCase();

      return `
        <div class="recent-patient-item">
          <div class="recent-patient-info">
            <div class="recent-patient-avatar">${escapeHtml(initials)}</div>
            <div>
              <div style="font-size:13.5px; font-weight:600; color:var(--text-main);">${escapeHtml(name)}</div>
              <div style="font-size:12px; color:var(--text-muted);">${escapeHtml(phone)} • Dr. ${escapeHtml(doctor.replace(/^Dr\.?\s*/i, ""))}</div>
            </div>
          </div>
          <div style="font-size:12px; color:var(--text-secondary); text-align:right;">
            ${formatDate(apptDate)}
          </div>
        </div>
      `;
    }).join("");
  },

  async markCompleted(identifier) {
    if (!confirm(`Mark appointment ${identifier} as Completed?`)) return;
    try {
      await API.updateAppointmentStatus(identifier, "Completed");
      showToast(`Appointment ${identifier} marked as Completed`, "success");
      window.dispatchEvent(new CustomEvent("crm:appointment-changed"));
      await this.loadData();
    } catch (err) {
      showToast(err.message || "Failed to update appointment status", "error");
    }
  },
};

