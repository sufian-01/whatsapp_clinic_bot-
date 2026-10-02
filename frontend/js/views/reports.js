/**
 * Reports & Analytics View with Sanitized CSV Exports.
 */

import { API } from "../api.js";
import { Toast, formatCurrency, formatDate } from "../utils.js";

export const ReportsView = {
  currentPreset: "this_month",
  startDate: "",
  endDate: "",

  async init() {
    const container = document.getElementById("view-reports");
    if (!container) return;

    container.innerHTML = `
      <div class="view-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 20px;">
        <div class="filter-group" style="display: flex; gap: 8px; flex-wrap: wrap; align-items: center;">
          <span style="font-weight: 600; font-size: 0.875rem; color: var(--text-secondary);">Range:</span>
          <button class="btn btn-sm btn-outline range-btn active" data-preset="this_month">This Month</button>
          <button class="btn btn-sm btn-outline range-btn" data-preset="this_week">This Week</button>
          <button class="btn btn-sm btn-outline range-btn" data-preset="today">Today</button>
          <button class="btn btn-sm btn-outline range-btn" data-preset="last_30_days">Last 30 Days</button>
        </div>
        <div class="custom-range" style="display: flex; gap: 8px; align-items: center;">
          <input type="date" id="report-start-date" class="form-input" style="padding: 4px 8px; font-size: 0.85rem;" />
          <span>to</span>
          <input type="date" id="report-end-date" class="form-input" style="padding: 4px 8px; font-size: 0.85rem;" />
          <button id="report-apply-range-btn" class="btn btn-sm btn-primary">Apply</button>
        </div>
      </div>

      <!-- Operational Metrics Grid -->
      <div id="reports-metrics-container" class="stats-grid" style="margin-bottom: 24px;">
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(14, 165, 233, 0.1); color: #0ea5e9;">📊</div>
          <div class="stat-meta">
            <span class="stat-label">Total Bookings</span>
            <span id="rep-total-appts" class="stat-value">-</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(34, 197, 94, 0.1); color: #22c55e;">✅</div>
          <div class="stat-meta">
            <span class="stat-label">Completed Visits</span>
            <span id="rep-completed-appts" class="stat-value">-</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(16, 185, 129, 0.1); color: #10b981;">💰</div>
          <div class="stat-meta">
            <span class="stat-label">Revenue Collected</span>
            <span id="rep-revenue-collected" class="stat-value">-</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(245, 158, 11, 0.1); color: #f59e0b;">⏳</div>
          <div class="stat-meta">
            <span class="stat-label">Pending Billing</span>
            <span id="rep-pending-revenue" class="stat-value">-</span>
          </div>
        </div>
      </div>

      <!-- Reports & Exports Section -->
      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header" style="border-bottom: 1px solid var(--border-color); padding: 16px 20px;">
          <h3 style="margin: 0; font-size: 1.1rem; font-weight: 600;">📥 Data Export & Compliance Reports</h3>
          <p style="margin: 4px 0 0; font-size: 0.85rem; color: var(--text-secondary);">
            Export sanitized CSV spreadsheets protected against CSV formula injection (CWE-1236).
          </p>
        </div>
        <div class="card-body" style="padding: 20px; display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
          <div class="export-box" style="border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; background: var(--bg-hover);">
            <h4 style="margin: 0 0 6px; font-size: 0.95rem;">📅 Appointments Report</h4>
            <p style="margin: 0 0 12px; font-size: 0.8rem; color: var(--text-secondary);">
              Complete booking details with patient names, doctor, time slot, token numbers, and payment status.
            </p>
            <button id="btn-export-appointments" class="btn btn-sm btn-primary" style="width: 100%;">
              Export Appointments (CSV)
            </button>
          </div>

          <div class="export-box" style="border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; background: var(--bg-hover);">
            <h4 style="margin: 0 0 6px; font-size: 0.95rem;">👥 Patient Directory Report</h4>
            <p style="margin: 0 0 12px; font-size: 0.8rem; color: var(--text-secondary);">
              All registered patients, contact details, total visits, and last consultation date.
            </p>
            <button id="btn-export-patients" class="btn btn-sm btn-outline" style="width: 100%;">
              Export Patients (CSV)
            </button>
          </div>

          <div class="export-box" style="border: 1px solid var(--border-color); border-radius: 8px; padding: 16px; background: var(--bg-hover);">
            <h4 style="margin: 0 0 6px; font-size: 0.95rem;">💳 Payments & Billing Ledger</h4>
            <p style="margin: 0 0 12px; font-size: 0.8rem; color: var(--text-secondary);">
              Fee collections, offline receipts, UPI references, and pending reconciliation balances.
            </p>
            <button id="btn-export-payments" class="btn btn-sm btn-outline" style="width: 100%;">
              Export Payments (CSV)
            </button>
          </div>
        </div>
      </div>

      <!-- Doctor Workload Breakdown Table -->
      <div class="card">
        <div class="card-header" style="border-bottom: 1px solid var(--border-color); padding: 16px 20px;">
          <h3 style="margin: 0; font-size: 1.1rem; font-weight: 600;">👨‍⚕️ Doctor Workload & Consultations in Period</h3>
        </div>
        <div class="card-body" style="padding: 0;">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Doctor</th>
                  <th>Total Appointments</th>
                  <th>Revenue Collected</th>
                </tr>
              </thead>
              <tbody id="reports-doctor-tbody">
                <tr><td colspan="3" class="text-center">Loading workload analytics...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadAnalytics();
  },

  bindEvents() {
    // Preset buttons
    document.querySelectorAll(".range-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        document.querySelectorAll(".range-btn").forEach((b) => b.classList.remove("active"));
        e.target.classList.add("active");
        this.currentPreset = e.target.getAttribute("data-preset");
        this.startDate = "";
        this.endDate = "";
        const sInput = document.getElementById("report-start-date");
        const eInput = document.getElementById("report-end-date");
        if (sInput) sInput.value = "";
        if (eInput) eInput.value = "";
        this.loadAnalytics();
      });
    });

    // Custom date range apply
    document.getElementById("report-apply-range-btn")?.addEventListener("click", () => {
      const sVal = document.getElementById("report-start-date")?.value;
      const eVal = document.getElementById("report-end-date")?.value;
      if (!sVal || !eVal) {
        Toast.error("Please select both start and end dates.");
        return;
      }
      if (sVal > eVal) {
        Toast.error("Start date must be before end date.");
        return;
      }
      document.querySelectorAll(".range-btn").forEach((b) => b.classList.remove("active"));
      this.currentPreset = "";
      this.startDate = sVal;
      this.endDate = eVal;
      this.loadAnalytics();
    });

    // Export buttons
    document.getElementById("btn-export-appointments")?.addEventListener("click", () => {
      this.triggerExport("appointments");
    });
    document.getElementById("btn-export-patients")?.addEventListener("click", () => {
      this.triggerExport("patients");
    });
    document.getElementById("btn-export-payments")?.addEventListener("click", () => {
      this.triggerExport("payments");
    });
  },

  async loadAnalytics() {
    try {
      const params = {};
      if (this.currentPreset) {
        params.preset = this.currentPreset;
      } else if (this.startDate && this.endDate) {
        params.start_date = this.startDate;
        params.end_date = this.endDate;
      } else {
        params.preset = "this_month";
      }

      const data = await API.getAnalytics(params);
      this.renderAnalytics(data);
    } catch (err) {
      Toast.error("Failed to load analytics: " + err.message);
    }
  },

  renderAnalytics(data) {
    const totalEl = document.getElementById("rep-total-appts");
    const compEl = document.getElementById("rep-completed-appts");
    const revEl = document.getElementById("rep-revenue-collected");
    const pendEl = document.getElementById("rep-pending-revenue");

    if (totalEl) totalEl.textContent = data.total_appointments || 0;
    if (compEl) compEl.textContent = data.completed_count || 0;
    if (revEl) revEl.textContent = formatCurrency(data.revenue_collected || 0);
    if (pendEl) pendEl.textContent = formatCurrency(data.pending_revenue || 0);

    // Render doctor workload table
    const tbody = document.getElementById("reports-doctor-tbody");
    if (!tbody) return;

    const docs = data.doctor_workload || [];
    if (docs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="text-center" style="padding: 24px; color: var(--text-secondary);">No consultation records in this period.</td></tr>`;
      return;
    }

    tbody.innerHTML = docs.map((d) => `
      <tr>
        <td style="font-weight: 600;">${d.doctor}</td>
        <td><span class="badge badge-info">${d.count} appointments</span></td>
        <td style="font-weight: 600; color: #10b981;">${formatCurrency(d.revenue)}</td>
      </tr>
    `).join("");
  },

  triggerExport(type) {
    const url = API.getReportExportUrl(type, this.startDate, this.endDate);
    Toast.success(`Generating ${type} report...`);
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.download = `${type}_report.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  },
};
