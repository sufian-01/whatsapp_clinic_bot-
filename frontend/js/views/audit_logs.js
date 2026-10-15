/**
 * Activity & Audit Logs View for Clinic CMS Compliance.
 */

import { API } from "../api.js";
import { Modal, Toast, formatDateTime } from "../utils.js";

export const AuditLogsView = {
  currentFilterAction: "",
  currentFilterEntity: "",
  page: 1,
  pageSize: 15,
  total: 0,
  totalPages: 1,

  async init() {
    const container = document.getElementById("view-audit-logs");
    if (!container) return;

    container.innerHTML = `
      <div class="card" style="margin-bottom: 20px;">
        <div class="card-header" style="border-bottom: 1px solid var(--border-color); padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
          <div>
            <h3 style="margin: 0; font-size: 1.1rem; font-weight: 600;">🛡️ Immutable Audit & Security Logs</h3>
            <p style="margin: 4px 0 0; font-size: 0.85rem; color: var(--text-secondary);">
              Append-only audit trail recording sensitive clinical actions, bookings, cancellations, and fee transactions.
            </p>
          </div>
          <button id="btn-refresh-audit" class="btn btn-sm btn-outline">🔄 Refresh</button>
        </div>

        <div class="card-body" style="padding: 16px 20px; border-bottom: 1px solid var(--border-color);">
          <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary);">Action:</label>
              <select id="audit-filter-action" class="form-input" style="padding: 6px 10px; font-size: 0.85rem;">
                <option value="">All Actions</option>
                <option value="APPOINTMENT_CREATE">Appointment Booked</option>
                <option value="APPOINTMENT_RESCHEDULE">Appointment Rescheduled</option>
                <option value="APPOINTMENT_CANCEL">Appointment Cancelled</option>
                <option value="APPOINTMENT_STATUS_UPDATE">Appointment Status Changed</option>
                <option value="DOCTOR_CREATE">Doctor Created</option>
                <option value="DOCTOR_UPDATE">Doctor Updated</option>
                <option value="DOCTOR_STATUS_CHANGE">Doctor Status Changed</option>
                <option value="PATIENT_CREATE">Patient Registered</option>
                <option value="PATIENT_UPDATE">Patient Updated</option>
                <option value="PATIENT_DEACTIVATE">Patient Deactivated</option>
                <option value="PAYMENT_RECORD">Payment Recorded</option>
                <option value="PAYMENT_STATUS_UPDATE">Payment Status Updated</option>
              </select>
            </div>

            <div style="display: flex; align-items: center; gap: 6px;">
              <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary);">Entity Type:</label>
              <select id="audit-filter-entity" class="form-input" style="padding: 6px 10px; font-size: 0.85rem;">
                <option value="">All Entities</option>
                <option value="appointment">Appointment</option>
                <option value="patient">Patient</option>
                <option value="doctor">Doctor</option>
                <option value="payment">Payment</option>
                <option value="slot">Slot</option>
              </select>
            </div>
          </div>
        </div>

        <div class="card-body" style="padding: 0;">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Timestamp (UTC)</th>
                  <th>Admin User</th>
                  <th>Action</th>
                  <th>Target Entity</th>
                  <th>Summary</th>
                  <th>Details</th>
                </tr>
              </thead>
              <tbody id="audit-logs-tbody">
                <tr><td colspan="6" class="text-center">Loading audit history...</td></tr>
              </tbody>
            </table>
          </div>

          <!-- Audit Logs Pagination Controls -->
          <div id="audit-pagination-bar" class="pagination-container" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; border-top: 1px solid var(--border-color); background: var(--bg-surface);">
            <div id="audit-page-info" style="font-size: 13px; color: var(--text-secondary); font-weight: 500;">
              Showing 0 logs
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
              <div style="display: flex; align-items: center; gap: 6px;">
                <label for="audit-page-size" style="font-size: 12px; color: var(--text-secondary);">Per page:</label>
                <select id="audit-page-size" class="form-input" style="padding: 4px 8px; font-size: 12px; width: auto; height: 32px;">
                  <option value="15" selected>15</option>
                  <option value="25">25</option>
                  <option value="50">50</option>
                  <option value="100">100</option>
                </select>
              </div>
              <button id="audit-prev-btn" class="btn btn-secondary btn-sm" disabled style="padding: 4px 12px; font-size: 12.5px;">&larr; Previous</button>
              <span id="audit-page-num" style="font-size: 13px; font-weight: 600; padding: 0 4px; color: var(--text-main);">Page 1 of 1</span>
              <button id="audit-next-btn" class="btn btn-secondary btn-sm" disabled style="padding: 4px 12px; font-size: 12.5px;">Next &rarr;</button>
            </div>
          </div>
        </div>
      </div>
    `;

    this.bindEvents();
    await this.loadLogs();
  },

  bindEvents() {
    document.getElementById("btn-refresh-audit")?.addEventListener("click", () => this.loadLogs());

    document.getElementById("audit-filter-action")?.addEventListener("change", (e) => {
      this.currentFilterAction = e.target.value;
      this.page = 1;
      this.loadLogs();
    });

    document.getElementById("audit-filter-entity")?.addEventListener("change", (e) => {
      this.currentFilterEntity = e.target.value;
      this.page = 1;
      this.loadLogs();
    });

    document.getElementById("audit-page-size")?.addEventListener("change", (e) => {
      this.pageSize = parseInt(e.target.value, 10) || 15;
      this.page = 1;
      this.loadLogs();
    });

    document.getElementById("audit-prev-btn")?.addEventListener("click", () => {
      if (this.page > 1) {
        this.page--;
        this.loadLogs();
      }
    });

    document.getElementById("audit-next-btn")?.addEventListener("click", () => {
      if (this.page < this.totalPages) {
        this.page++;
        this.loadLogs();
      }
    });
  },

  async loadLogs() {
    const tbody = document.getElementById("audit-logs-tbody");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="padding: 24px;">Loading audit history...</td></tr>`;

    try {
      const params = {
        page: this.page,
        page_size: this.pageSize,
      };
      if (this.currentFilterAction) params.action = this.currentFilterAction;
      if (this.currentFilterEntity) params.entity_type = this.currentFilterEntity;

      const data = await API.getAuditLogs(params);
      const logs = data.logs || (Array.isArray(data) ? data : []);
      this.total = data.total !== undefined ? data.total : logs.length;
      this.totalPages = data.total_pages || Math.ceil(this.total / this.pageSize) || 1;
      this.page = data.page || this.page;

      this.updatePaginationUI();

      if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="padding: 30px; color: var(--text-secondary);">No audit logs found matching filters.</td></tr>`;
        return;
      }

      tbody.innerHTML = logs.map((log) => {
        const badgeColor = this.getBadgeClass(log.action);
        const detailsSummary = this.getSummaryText(log.details);
        return `
          <tr>
            <td style="font-size: 0.82rem; font-family: monospace; color: var(--text-secondary);">
              ${log.timestamp ? log.timestamp.replace("T", " ").substring(0, 19) : "-"}
            </td>
            <td><span style="font-weight: 600;">${log.user || "admin"}</span></td>
            <td><span class="badge ${badgeColor}">${log.action}</span></td>
            <td>
              <span style="text-transform: capitalize; font-size: 0.85rem;">${log.entity_type}</span>:
              <strong>${log.entity_id}</strong>
            </td>
            <td style="font-size: 0.85rem; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              ${detailsSummary}
            </td>
            <td>
              <button class="btn btn-sm btn-outline btn-audit-detail" data-log-id="${log.id}">
                View
              </button>
            </td>
          </tr>
        `;
      }).join("");

      // Bind modal triggers for detail inspection
      tbody.querySelectorAll(".btn-audit-detail").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const logId = e.currentTarget.getAttribute("data-log-id");
          const log = logs.find((l) => l.id === logId);
          if (log) {
            this.showDetailModal(log);
          }
        });
      });
    } catch (err) {
      Toast.error("Failed to fetch audit logs: " + err.message);
      tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="padding: 24px; color: var(--danger-text);">Failed to load audit history: ${err.message}</td></tr>`;
    }
  },

  updatePaginationUI() {
    const pageInfo = document.getElementById("audit-page-info");
    const pageNum = document.getElementById("audit-page-num");
    const prevBtn = document.getElementById("audit-prev-btn");
    const nextBtn = document.getElementById("audit-next-btn");

    if (pageInfo) {
      if (this.total === 0) {
        pageInfo.textContent = "Showing 0 logs";
      } else {
        const start = (this.page - 1) * this.pageSize + 1;
        const end = Math.min(this.page * this.pageSize, this.total);
        pageInfo.textContent = `Showing ${start} – ${end} of ${this.total} logs`;
      }
    }

    if (pageNum) {
      pageNum.textContent = `Page ${this.page} of ${this.totalPages}`;
    }

    if (prevBtn) {
      prevBtn.disabled = this.page <= 1;
    }

    if (nextBtn) {
      nextBtn.disabled = this.page >= this.totalPages;
    }
  },

  getBadgeClass(action) {
    if (action.includes("CREATE")) return "badge-completed";
    if (action.includes("CANCEL") || action.includes("DEACTIVATE")) return "badge-cancelled";
    if (action.includes("RESCHEDULE")) return "badge-pending";
    if (action.includes("PAYMENT")) return "badge-info";
    return "badge-pending";
  },

  getSummaryText(details) {
    if (!details || Object.keys(details).length === 0) return "-";
    const parts = [];
    for (const [k, v] of Object.entries(details)) {
      if (typeof v === "object") continue;
      parts.push(`${k}: ${v}`);
      if (parts.length >= 3) break;
    }
    return parts.join(", ") || JSON.stringify(details);
  },

  showDetailModal(log) {
    const formattedJson = JSON.stringify(log.details, null, 2);
    Modal.open(
      `Audit Entry: ${log.action}`,
      `
        <div style="font-size: 0.9rem; line-height: 1.6;">
          <p><strong>Log ID:</strong> <code>${log.id}</code></p>
          <p><strong>Timestamp (UTC):</strong> ${log.timestamp}</p>
          <p><strong>Admin Actor:</strong> ${log.user}</p>
          <p><strong>Action:</strong> <span class="badge ${this.getBadgeClass(log.action)}">${log.action}</span></p>
          <p><strong>Target Entity:</strong> ${log.entity_type} (ID: <code>${log.entity_id}</code>)</p>
          <h4 style="margin: 16px 0 8px;">Attributes & Change Diff:</h4>
          <pre style="background: var(--bg-hover); padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 0.82rem; border: 1px solid var(--border-color);">${formattedJson}</pre>
        </div>
      `,
      `
        <button class="btn btn-outline" onclick="window.Modal.close()">Close</button>
      `
    );
  },
};
