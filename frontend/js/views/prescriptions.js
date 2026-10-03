/**
 * Admin Prescriptions Oversight View Module.
 * Provides system-wide clinical prescription monitoring, multi-factor filtering,
 * full clinical detail review, version history audit trail, and PDF downloads.
 */

import { API } from "../api.js";
import { debounce, escapeHtml, formatDate, formatTime, renderBadge, showToast, Modal } from "../utils.js";

export const PrescriptionsView = {
  container: null,
  prescriptions: [],
  doctors: [],
  filters: {
    search: "",
    status: "",
    doctor_id: "",
    date: "",
  },
  _abortController: null,

  async init() {
    this.container = document.getElementById("view-prescriptions");
    if (!this.container) return;
    await this.render();
  },

  renderTableSkeletons(cols = 9, rows = 5) {
    let out = "";
    for (let r = 0; r < rows; r++) {
      out += "<tr>";
      for (let c = 0; c < cols; c++) {
        const width = 45 + Math.floor(Math.random() * 45);
        out += `<td><div class="skeleton" style="height: 14px; width: ${width}%; border-radius: 4px;"></div></td>`;
      }
      out += "</tr>";
    }
    return out;
  },

  async render() {
    this.container.innerHTML = `
      <div class="view-header" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom: 24px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">Prescription Oversight</h2>
          <p style="font-size: 13px; color: var(--text-secondary);">Clinic-wide administrative audit of all drafted, finalized, and amended medical prescriptions</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <button id="admin-rx-refresh-btn" class="btn btn-secondary btn-sm">
            <span>🔄</span> Refresh
          </button>
        </div>
      </div>

      <!-- Filters & Search Toolbar -->
      <div class="card" style="padding: 16px; margin-bottom: 20px;">
        <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center;">
          <div style="flex: 1; min-width: 220px;">
            <input type="text" id="admin-rx-search" class="form-input" placeholder="Search patient name, ID, doctor, Rx ID, token..." value="${escapeHtml(this.filters.search)}" />
          </div>
          <div style="width: 170px;">
            <select id="admin-rx-doctor-filter" class="form-select">
              <option value="">All Doctors</option>
            </select>
          </div>
          <div style="width: 150px;">
            <select id="admin-rx-status-filter" class="form-select">
              <option value="">All Statuses</option>
              <option value="draft" ${this.filters.status === "draft" ? "selected" : ""}>Draft</option>
              <option value="finalized" ${this.filters.status === "finalized" ? "selected" : ""}>Finalized</option>
              <option value="amended" ${this.filters.status === "amended" ? "selected" : ""}>Amended</option>
            </select>
          </div>
          <div style="width: 150px;">
            <input type="date" id="admin-rx-date-filter" class="form-input" value="${this.filters.date || ''}" />
          </div>
          <div>
            <button id="admin-rx-reset-filter" class="btn btn-secondary btn-sm">Reset</button>
          </div>
        </div>
      </div>

      <!-- Prescriptions Table Card -->
      <div class="card" style="padding: 0; overflow: hidden;">
        <div class="table-container" style="max-height: 620px; overflow-y: auto;">
          <table class="data-table">
            <thead>
              <tr>
                <th>Rx ID</th>
                <th>Patient Details</th>
                <th>Prescribing Doctor</th>
                <th>Clinical Diagnosis</th>
                <th>Version</th>
                <th>Status</th>
                <th>Issued / Date</th>
                <th>Email Delivery</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody id="admin-rx-table-body">
              ${this.renderTableSkeletons(9, 5)}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Load doctors for filter
    try {
      const docs = await API.listDoctors();
      this.doctors = docs || [];
      const docSel = document.getElementById("admin-rx-doctor-filter");
      if (docSel) {
        docSel.innerHTML = `<option value="">All Doctors</option>` +
          this.doctors.map((d) => `<option value="${escapeHtml(d['Doctor ID'] || d.doctor_id)}">${escapeHtml(d['Doctor Name'] || d.name)}</option>`).join("");
      }
    } catch (_) {}

    this.bindEvents();
    await this.loadData();
  },

  bindEvents() {
    const refreshBtn = document.getElementById("admin-rx-refresh-btn");
    const searchInput = document.getElementById("admin-rx-search");
    const doctorSelect = document.getElementById("admin-rx-doctor-filter");
    const statusSelect = document.getElementById("admin-rx-status-filter");
    const dateInput = document.getElementById("admin-rx-date-filter");
    const resetBtn = document.getElementById("admin-rx-reset-filter");

    refreshBtn?.addEventListener("click", () => this.loadData());

    searchInput?.addEventListener("input", debounce((e) => {
      this.filters.search = e.target.value.toLowerCase().trim();
      this.renderRows();
    }, 250));

    doctorSelect?.addEventListener("change", (e) => {
      this.filters.doctor_id = e.target.value;
      this.loadData();
    });

    statusSelect?.addEventListener("change", (e) => {
      this.filters.status = e.target.value;
      this.loadData();
    });

    dateInput?.addEventListener("change", (e) => {
      this.filters.date = e.target.value;
      this.loadData();
    });

    resetBtn?.addEventListener("click", () => {
      this.filters.search = "";
      this.filters.status = "";
      this.filters.doctor_id = "";
      this.filters.date = "";
      if (searchInput) searchInput.value = "";
      if (doctorSelect) doctorSelect.value = "";
      if (statusSelect) statusSelect.value = "";
      if (dateInput) dateInput.value = "";
      this.loadData();
    });
  },

  async loadData() {
    if (this._abortController) {
      this._abortController.abort();
    }
    this._abortController = new AbortController();

    const tbody = document.getElementById("admin-rx-table-body");
    if (tbody) {
      tbody.innerHTML = this.renderTableSkeletons(9, 5);
    }

    try {
      const params = {};
      if (this.filters.status) params.status = this.filters.status;
      if (this.filters.doctor_id) params.doctor_id = this.filters.doctor_id;
      if (this.filters.date) params.date = this.filters.date;

      const res = await API.getAdminPrescriptions(params, { signal: this._abortController.signal });
      this.prescriptions = Array.isArray(res) ? res : (res.prescriptions || []);
      this.renderRows();
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Failed to load admin prescriptions:", err);
      showToast("Error loading prescriptions: " + err.message, "error");
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="9" style="text-align:center; padding: 28px; color: var(--danger-text);">
              <div style="font-weight: 600; margin-bottom: 6px;">⚠️ Unable to load prescriptions: ${escapeHtml(err.message)}</div>
              <button id="admin-rx-retry-btn" class="btn btn-secondary btn-sm" style="margin-top: 6px;">🔄 Retry Loading</button>
            </td>
          </tr>
        `;
        document.getElementById("admin-rx-retry-btn")?.addEventListener("click", () => this.loadData());
      }
    }
  },

  renderRows() {
    const tbody = document.getElementById("admin-rx-table-body");
    if (!tbody) return;

    let items = this.prescriptions;
    if (this.filters.search) {
      const q = this.filters.search;
      items = items.filter(rx => {
        const id = rx.prescription_id || rx.id || "";
        const ptName = rx.patient_name || "";
        const ptId = rx.patient_id || "";
        const docName = rx.doctor_name || rx.doctor_id || "";
        const diag = rx.diagnosis || "";
        const apptId = rx.appointment_id || "";
        return (
          id.toLowerCase().includes(q) ||
          ptName.toLowerCase().includes(q) ||
          ptId.toLowerCase().includes(q) ||
          docName.toLowerCase().includes(q) ||
          diag.toLowerCase().includes(q) ||
          apptId.toLowerCase().includes(q)
        );
      });
    }

    if (!items.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align:center; padding: 40px; color: var(--text-secondary);">
            <div style="font-size: 32px; margin-bottom: 8px;">📋</div>
            <div style="font-weight: 500;">No prescriptions found matching criteria</div>
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = items.map(rx => {
      const rxId = escapeHtml(rx.prescription_id || rx.id || "");
      const patientName = escapeHtml(rx.patient_name || "Unknown Patient");
      const doctorName = escapeHtml(rx.doctor_name || rx.doctor_id || "Doctor");
      const diagnosis = escapeHtml(rx.diagnosis || "—");
      const version = rx.version ? `v${rx.version}` : "v1";
      const statusBadge = renderBadge(rx.status || "draft");
      const dateStr = formatDate(rx.date || rx.created_at);

      let emailStatus = `<span style="color: var(--text-muted); font-size: 11px;">Not sent</span>`;
      if (rx.email_delivery) {
        if (rx.email_delivery.sent) {
          emailStatus = `<span class="badge badge-completed" style="font-size: 11px;" title="Delivered to ${escapeHtml(rx.email_delivery.recipient || '')}">Sent</span>`;
        } else {
          emailStatus = `<span class="badge badge-cancelled" style="font-size: 11px;" title="Failed: ${escapeHtml(rx.email_delivery.error || 'Unknown error')}">Failed</span>`;
        }
      }

      return `
        <tr>
          <td><code style="font-size: 11px; font-weight: 700;">${rxId}</code></td>
          <td>
            <div style="font-weight: 600; color: var(--text-main);">${patientName}</div>
            <div style="font-size: 11px; color: var(--text-secondary);">ID: ${escapeHtml(rx.patient_id || "—")} • Appt: ${escapeHtml(rx.appointment_id || "—")}</div>
          </td>
          <td>
            <div style="font-weight: 500;">${doctorName}</div>
            <div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(rx.doctor_id || "")}</div>
          </td>
          <td style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
            ${diagnosis}
          </td>
          <td>
            <span class="badge" style="background: rgba(99, 102, 241, 0.1); color: var(--primary); font-weight: 600;">${version}</span>
          </td>
          <td>${statusBadge}</td>
          <td style="font-size: 12px; color: var(--text-secondary);">${dateStr}</td>
          <td>${emailStatus}</td>
          <td style="text-align: right; white-space: nowrap;">
            <button class="btn btn-secondary btn-sm admin-view-rx-btn" data-id="${rxId}" title="View Details">
              👁️ View
            </button>
            ${rx.status === "finalized" || rx.status === "amended" ? `
              <a href="${API.getAdminPrescriptionPdfUrl(rx.prescription_id || rx.id)}" target="_blank" class="btn btn-primary btn-sm" title="Download Official PDF">
                📄 PDF
              </a>
            ` : ""}
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".admin-view-rx-btn").forEach(btn => {
      btn.addEventListener("click", () => this.showDetailModal(btn.getAttribute("data-id")));
    });
  },

  async showDetailModal(id) {
    try {
      const rx = await API.getAdminPrescription(id);
      if (!rx) {
        showToast("Prescription not found", "error");
        return;
      }

      const meds = rx.medicines || rx.medications || [];
      const medsHtml = meds.length ? meds.map((m, idx) => `
        <tr>
          <td>${idx + 1}</td>
          <td style="font-weight: 600;">${escapeHtml(m.name || m.drug_name || "")}</td>
          <td>${escapeHtml(m.strength || "—")}</td>
          <td>${escapeHtml(m.dosage || "")}</td>
          <td>${escapeHtml(m.frequency || "")}</td>
          <td>${escapeHtml(m.duration || "")}</td>
          <td>${escapeHtml(m.instructions || "—")}</td>
        </tr>
      `).join("") : `<tr><td colspan="7" style="text-align:center; color: var(--text-secondary);">No medications recorded</td></tr>`;

      const vitals = rx.vitals || {};
      const vitalsStr = Object.entries(vitals).filter(([_, v]) => v).map(([k, v]) => `<strong>${escapeHtml(k.toUpperCase())}:</strong> ${escapeHtml(String(v))}`).join(" | ") || "None recorded";

      const amendments = rx.version_history || rx.amendments || [];
      let amendmentsHtml = "";
      if (amendments.length > 0) {
        amendmentsHtml = `
          <div style="margin-top: 16px; border-top: 1px dashed var(--border-light); padding-top: 12px;">
            <h4 style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">Clinical Amendment Audit Trail</h4>
            <div style="display: flex; flex-direction: column; gap: 8px;">
              ${amendments.map((a, idx) => `
                <div style="background: var(--bg-surface-secondary); padding: 8px 12px; border-radius: 6px; font-size: 12px;">
                  <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-weight: 600;">Amendment #${idx + 1} (v${a.version})</span>
                    <span style="color: var(--text-muted);">${formatDate(a.amended_at || a.created_at)}</span>
                  </div>
                  <div><strong>Reason:</strong> ${escapeHtml(a.amendment_reason || a.reason || "Clinical adjustment")}</div>
                  ${a.amended_by ? `<div><strong>Amended By:</strong> ${escapeHtml(a.amended_by)}</div>` : ""}
                </div>
              `).join("")}
            </div>
          </div>
        `;
      }

      let emailDeliveryHtml = "";
      if (rx.email_delivery) {
        emailDeliveryHtml = `
          <div style="background: var(--bg-surface-secondary); padding: 10px 14px; border-radius: 6px; font-size: 12.5px; border-left: 3px solid ${rx.email_delivery.sent ? 'var(--success)' : 'var(--danger)'};">
            <div><strong>Email Delivery Status:</strong> ${rx.email_delivery.sent ? '<span style="color:var(--success); font-weight:600;">Sent</span>' : '<span style="color:var(--danger); font-weight:600;">Failed</span>'}</div>
            <div><strong>Recipient:</strong> ${escapeHtml(rx.email_delivery.recipient || 'None')}</div>
            <div><strong>Dispatched At:</strong> ${formatDate(rx.email_delivery.timestamp)}</div>
            ${rx.email_delivery.error ? `<div style="color:var(--danger);"><strong>Error:</strong> ${escapeHtml(rx.email_delivery.error)}</div>` : ''}
          </div>
        `;
      }

      const content = `
        <div style="display: flex; flex-direction: column; gap: 16px;">
          <!-- Top summary -->
          <div style="display: flex; justify-content: space-between; align-items: center; background: var(--bg-surface-secondary); padding: 12px 16px; border-radius: 8px;">
            <div>
              <div style="font-size: 12px; color: var(--text-secondary);">Prescription Identifier</div>
              <div style="font-size: 16px; font-weight: 700; color: var(--text-main);">${escapeHtml(rx.prescription_id || rx.id)} (v${rx.version || 1})</div>
            </div>
            <div>
              ${renderBadge(rx.status)}
            </div>
          </div>

          <!-- Metadata grid -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px;">
            <div><strong>Patient:</strong> ${escapeHtml(rx.patient_name || "—")} (ID: ${escapeHtml(rx.patient_id || "—")})</div>
            <div><strong>Prescribing Doctor:</strong> ${escapeHtml(rx.doctor_name || "—")} (${escapeHtml(rx.doctor_id || "")})</div>
            <div><strong>Appointment Ref:</strong> ${escapeHtml(rx.appointment_id || "—")}</div>
            <div><strong>Consultation Date:</strong> ${formatDate(rx.date || rx.created_at)}</div>
            ${rx.chief_complaints ? `<div style="grid-column: span 2;"><strong>Chief Complaints:</strong> ${escapeHtml(rx.chief_complaints)}</div>` : ""}
            <div style="grid-column: span 2;"><strong>Clinical Vitals:</strong> ${vitalsStr}</div>
            <div style="grid-column: span 2;"><strong>Clinical Diagnosis:</strong> ${escapeHtml(rx.diagnosis || "—")}</div>
            ${rx.symptoms ? `<div style="grid-column: span 2;"><strong>Symptoms:</strong> ${escapeHtml(rx.symptoms)}</div>` : ""}
            ${rx.clinical_notes ? `<div style="grid-column: span 2; background:var(--bg-surface-secondary); padding:8px 12px; border-radius:6px;"><strong>Clinical Examination Notes:</strong><div>${rx.clinical_notes}</div></div>` : ""}
          </div>

          <!-- Medication Table -->
          <div>
            <h4 style="font-size: 13px; font-weight: 600; margin-bottom: 8px;">Prescribed Medications</h4>
            <div class="table-container" style="max-height: 200px; overflow-y: auto;">
              <table class="data-table" style="font-size: 12px;">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Medicine</th>
                    <th>Strength</th>
                    <th>Dosage</th>
                    <th>Frequency</th>
                    <th>Duration</th>
                    <th>Instructions</th>
                  </tr>
                </thead>
                <tbody>
                  ${medsHtml}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Investigations & Followup -->
          <div style="font-size: 13px; background: var(--bg-surface-secondary); padding: 12px; border-radius: 6px;">
            ${rx.tests_advised ? `<div><strong>Tests Advised:</strong> ${escapeHtml(rx.tests_advised)}</div>` : ""}
            <div><strong>General Advice:</strong> ${escapeHtml(rx.advice || "None")}</div>
            ${rx.follow_up_date ? `<div style="margin-top: 6px;"><strong>Follow-up:</strong> ${escapeHtml(rx.follow_up_date)}</div>` : ""}
          </div>

          ${emailDeliveryHtml}
          ${amendmentsHtml}

          <!-- Footer Actions inside modal -->
          <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px;">
            ${(rx.status === "finalized" || rx.status === "amended") ? `
              <a href="${API.getAdminPrescriptionPdfUrl(rx.prescription_id || rx.id)}" target="_blank" class="btn btn-primary btn-sm">
                <span>📄</span> Open PDF Document
              </a>
            ` : ""}
            <button class="btn btn-secondary btn-sm" onclick="document.getElementById('app-modal-close-btn').click()">
              Close
            </button>
          </div>
        </div>
      `;

      Modal.open({
        title: "Prescription Details",
        body: content,
      });
    } catch (err) {
      console.error("Failed to load prescription detail:", err);
      showToast("Error loading prescription details: " + err.message, "error");
    }
  }
};

