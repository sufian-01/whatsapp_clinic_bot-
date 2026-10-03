/**
 * Doctor Dashboard View Module - Physician Clinical Command Center.
 */

import { API } from "../api.js";
import { escapeHtml, formatDate, formatTime, renderBadge, showToast, Modal } from "../utils.js";

export const DoctorDashboardView = {
  container: null,

  async init() {
    this.container = document.getElementById("view-doctor-dashboard");
    if (!this.container) return;
    this.render();
    await this.loadData();
  },

  render() {
    this.container.innerHTML = `
      <div class="view-header" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom: 24px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">Doctor Clinical Portal</h2>
          <p style="font-size: 13px; color: var(--text-secondary);">Your personal clinic schedule, active consultations & digital prescriptions</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <a href="#doctor-prescriptions" class="btn btn-primary btn-sm">
            <span>📝</span> New Prescription
          </a>
          <button id="doctor-refresh-btn" class="btn btn-secondary btn-sm" title="Refresh Live Data">
            <span>🔄</span> Refresh
          </button>
        </div>
      </div>

      <!-- Live Doctor Metric Cards -->
      <div id="doctor-metrics-container" class="metrics-grid">
        ${this.renderMetricsSkeletons()}
      </div>

      <!-- Main Columns -->
      <div style="display:grid; grid-template-columns: 2fr 1fr; gap:24px; margin-top:24px;">
        <!-- Left: Today's Consultations -->
        <div class="card">
          <div class="card-header" style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="card-title">📅 Today's Consultations</span>
              <span id="doc-today-badge" class="badge badge-info">Loading...</span>
            </div>
            <a href="#doctor-appointments" class="btn btn-secondary btn-sm">View All</a>
          </div>
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Token</th>
                  <th>Patient</th>
                  <th>Contact</th>
                  <th>Status</th>
                  <th>Payment</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody id="doctor-today-tbody">
                ${this.renderTableSkeletons(7, 3)}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Right: Upcoming Schedule & Clinical Shortcuts -->
        <div style="display:flex; flex-direction:column; gap:24px;">
          <div class="card">
            <div class="card-header">
              <span class="card-title">🕒 Quick Actions</span>
            </div>
            <div style="padding:16px; display:flex; flex-direction:column; gap:10px;">
              <a href="#doctor-slots" class="btn btn-secondary" style="justify-content:flex-start;">
                <span>⏱️</span> Manage My Available Slots
              </a>
              <a href="#doctor-patients" class="btn btn-secondary" style="justify-content:flex-start;">
                <span>👥</span> View My Assigned Patients
              </a>
              <a href="#doctor-prescriptions" class="btn btn-secondary" style="justify-content:flex-start;">
                <span>📋</span> All My Prescriptions
              </a>
            </div>
          </div>

          <div class="card">
            <div class="card-header">
              <span class="card-title">ℹ️ Clinical Notes</span>
            </div>
            <div style="padding:16px; font-size:13px; color:var(--text-secondary); line-height:1.6;">
              <p>• Only patients scheduled with your doctor ID are accessible.</p>
              <p style="margin-top:8px;">• Finalized prescriptions cannot be modified directly; use amendments to preserve medical audit records.</p>
              <p style="margin-top:8px;">• Patients receive confirmed PDF copies upon email dispatch.</p>
            </div>
          </div>
        </div>
      </div>
    `;

    document.getElementById("doctor-refresh-btn")?.addEventListener("click", () => this.loadData());
  },

  renderMetricsSkeletons() {
    const labels = ["Today's Visits", "Upcoming Bookings", "Pending Prescriptions", "Completed Consults", "Available Slots", "My Patient Base"];
    return labels.map(l => `
      <div class="metric-card">
        <div class="metric-label">${l}</div>
        <div class="skeleton" style="height: 32px; width: 50px; margin: 8px 0; border-radius: 4px;"></div>
        <div class="skeleton" style="height: 12px; width: 100px; border-radius: 4px;"></div>
      </div>
    `).join("");
  },

  renderTableSkeletons(cols = 7, rows = 3) {
    let out = "";
    for (let r = 0; r < rows; r++) {
      out += "<tr>";
      for (let c = 0; c < cols; c++) {
        out += `<td><div class="skeleton" style="height: 14px; width: 60%; border-radius: 4px;"></div></td>`;
      }
      out += "</tr>";
    }
    return out;
  },

  async loadData() {
    try {
      const stats = await API.getDoctorDashboard();
      this.renderMetrics(stats);
      this.renderTodaySchedule(stats.today_appointments || []);
    } catch (err) {
      console.error("Doctor dashboard failed to load:", err);
      showToast(err.message || "Failed to load clinical dashboard data.", "error");
      const container = document.getElementById("doctor-metrics-container");
      if (container) {
        container.innerHTML = `
          <div style="grid-column: 1 / -1; background: var(--bg-surface); border: 1px dashed var(--danger-border); border-radius: var(--radius-lg); padding: 20px; text-align: center;">
            <div style="color: var(--danger-text); font-weight: 600; margin-bottom: 6px;">⚠️ Unable to load metrics: ${escapeHtml(err.message || "Error")}</div>
            <button id="retry-doc-stats-btn" class="btn btn-secondary btn-sm" style="margin-top: 6px;">🔄 Retry</button>
          </div>
        `;
        document.getElementById("retry-doc-stats-btn")?.addEventListener("click", () => this.loadData());
      }
      const tbody = document.getElementById("doctor-today-tbody");
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 20px; color: var(--danger-text);">Failed to load schedule.</td></tr>`;
      }
    }
  },

  renderMetrics(stats) {
    const container = document.getElementById("doctor-metrics-container");
    if (!container) return;

    container.innerHTML = `
      <div class="metric-card">
        <div class="metric-label">Today's Visits</div>
        <div class="metric-value" style="color:var(--primary);">${stats.today_appointments_count || 0}</div>
        <div class="metric-subtitle">Awaiting: ${stats.awaiting_consultation_count || 0}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Upcoming Bookings</div>
        <div class="metric-value" style="color:#0284c7;">${stats.upcoming_appointments_count || 0}</div>
        <div class="metric-subtitle">Future scheduled visits</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Pending Prescriptions</div>
        <div class="metric-value" style="color:#ea580c;">${stats.pending_prescriptions_count || 0}</div>
        <div class="metric-subtitle">Awaiting finalization</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Completed Consults</div>
        <div class="metric-value" style="color:#16a34a;">${stats.completed_appointments_count || 0}</div>
        <div class="metric-subtitle">Total completed</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Available Slots</div>
        <div class="metric-value" style="color:#6366f1;">${stats.available_slots || 0}</div>
        <div class="metric-subtitle">Upcoming open slots</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">My Patient Base</div>
        <div class="metric-value" style="color:#8b5cf6;">${stats.total_patients || 0}</div>
        <div class="metric-subtitle">Unique assigned patients</div>
      </div>
    `;

    const badge = document.getElementById("doc-today-badge");
    if (badge) badge.textContent = `${stats.today_appointments_count || 0} Consultations`;
  },

  renderTodaySchedule(appts) {
    const tbody = document.getElementById("doctor-today-tbody");
    if (!tbody) return;

    if (!appts || appts.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="empty-state-cell" style="padding: 28px; text-align: center; color: var(--text-secondary);">
            <div style="font-size: 24px; margin-bottom: 6px;">🩺</div>
            <div style="font-weight: 500;">No patient visits scheduled for today</div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = appts.map((a) => {
      return `
        <tr>
          <td><strong>${escapeHtml(formatTime(a.time))}</strong></td>
          <td><code>${escapeHtml(a.token_no || a.appointment_id)}</code></td>
          <td><strong>${escapeHtml(a.patient_name)}</strong></td>
          <td>${escapeHtml(a.phone || "-")}</td>
          <td>${renderBadge(a.status)}</td>
          <td>${renderBadge(a.payment_status)}</td>
          <td>
            <a href="#doctor-prescriptions" class="btn btn-secondary btn-sm" style="padding:4px 8px; font-size:12px;">
              ${a.has_prescription ? "View Rx" : "Write Rx"}
            </a>
          </td>
        </tr>
      `;
    }).join("");
  },
};

