/**
 * Doctor Patients View Module.
 */

import { API } from "../api.js";
import { debounce, escapeHtml, formatDate, renderBadge, showToast, Modal } from "../utils.js";

export const DoctorPatientsView = {
  container: null,
  _abortController: null,

  async init() {
    this.container = document.getElementById("view-doctor-patients");
    if (!this.container) return;
    await this.render();
  },

  renderTableSkeletons(cols = 8, rows = 4) {
    let out = "";
    for (let r = 0; r < rows; r++) {
      out += "<tr>";
      for (let c = 0; c < cols; c++) {
        const width = 50 + Math.floor(Math.random() * 40);
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
          <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">My Assigned Patients</h2>
          <p style="font-size: 13px; color: var(--text-secondary);">Direct clinical patient directory for patients booked under your care</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <button id="doc-patients-refresh-btn" class="btn btn-secondary btn-sm">
            <span>🔄</span> Refresh
          </button>
        </div>
      </div>

      <!-- Search & Filters -->
      <div class="filter-bar" style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:16px;">
        <input type="text" id="doc-patient-search" class="form-input" placeholder="Search by patient name, phone, ID..." style="max-width:320px;" />
        <label style="display:flex; align-items:center; gap:6px; font-size:13px; cursor:pointer;">
          <input type="checkbox" id="doc-patient-paid-only" />
          Verified Paid Only
        </label>
      </div>

      <!-- Patients Table -->
      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Name</th>
                <th>Contact</th>
                <th>Visits with You</th>
                <th>Last Visit</th>
                <th>Last Status</th>
                <th>Payment</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="doc-patients-tbody">
              ${this.renderTableSkeletons(8, 4)}
            </tbody>
          </table>
        </div>
      </div>
    `;

    document.getElementById("doc-patients-refresh-btn")?.addEventListener("click", () => this.loadData());
    document.getElementById("doc-patient-search")?.addEventListener("input", debounce(() => this.loadData(), 250));
    document.getElementById("doc-patient-paid-only")?.addEventListener("change", () => this.loadData());

    await this.loadData();
  },

  async loadData() {
    if (this._abortController) {
      this._abortController.abort();
    }
    this._abortController = new AbortController();

    const search = document.getElementById("doc-patient-search")?.value.trim() || "";
    const paidOnly = document.getElementById("doc-patient-paid-only")?.checked || false;

    const tbody = document.getElementById("doc-patients-tbody");
    if (tbody) {
      tbody.innerHTML = this.renderTableSkeletons(8, 4);
    }

    try {
      const patients = await API.getDoctorPatients({
        search,
        require_paid: paidOnly,
      }, { signal: this._abortController.signal });
      this.renderTable(patients || []);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Doctor patients error:", err);
      showToast(err.message || "Failed to load assigned patients.", "error");
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="8" style="text-align:center; padding: 28px; color: var(--danger-text);">
              <div style="font-weight: 600; margin-bottom: 6px;">⚠️ Unable to load patients: ${escapeHtml(err.message || "Error")}</div>
              <button id="doc-pt-retry-btn" class="btn btn-secondary btn-sm" style="margin-top: 6px;">🔄 Retry Loading</button>
            </td>
          </tr>
        `;
        document.getElementById("doc-pt-retry-btn")?.addEventListener("click", () => this.loadData());
      }
    }
  },

  renderTable(patients) {
    const tbody = document.getElementById("doc-patients-tbody");
    if (!tbody) return;

    if (!patients.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No assigned patients found.</td></tr>`;
      return;
    }

    tbody.innerHTML = patients.map((p) => `
      <tr>
        <td><code>${escapeHtml(p.patient_id || "-")}</code></td>
        <td><strong>${escapeHtml(p.name)}</strong></td>
        <td>${escapeHtml(p.phone || "-")}</td>
        <td><span class="badge badge-info">${p.appointment_count} visit(s)</span></td>
        <td>${escapeHtml(formatDate(p.last_appointment_date))}</td>
        <td>${renderBadge(p.last_status)}</td>
        <td>${renderBadge(p.payment_status)}</td>
        <td>
          <button class="btn btn-secondary btn-sm doc-patient-history-btn" data-id="${escapeHtml(p.patient_id)}">
            Clinical History
          </button>
        </td>
      </tr>
    `).join("");

    tbody.querySelectorAll(".doc-patient-history-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.openPatientClinicalProfile(btn.dataset.id));
    });
  },

  async openPatientClinicalProfile(patientId) {
    try {
      const profile = await API.getDoctorPatientDetail(patientId);
      const pt = profile.patient || {};
      const visits = profile.visits || [];
      const rxs = profile.prescriptions || [];

      const visitsHtml = visits.length
        ? `<div style="max-height:150px; overflow-y:auto; border:1px solid var(--border-light); border-radius:4px; padding:8px;">` +
          visits.map((v) => `
            <div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px dashed var(--border-light); font-size:12px;">
              <span><strong>${formatDate(v.date)}</strong> at ${v.time} (Token: ${v.token_no})</span>
              <span>${renderBadge(v.status)} ${renderBadge(v.payment_status)}</span>
            </div>
          `).join("") +
          `</div>`
        : `<p style="color:var(--text-muted); font-size:12px;">No recorded visits.</p>`;

      const rxHtml = rxs.length
        ? `<div style="max-height:150px; overflow-y:auto; border:1px solid var(--border-light); border-radius:4px; padding:8px;">` +
          rxs.map((r) => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:4px 0; border-bottom:1px dashed var(--border-light); font-size:12px;">
              <span><strong>${r.prescription_id}</strong> (${formatDate(r.date)}) - ${escapeHtml(r.diagnosis || "No diagnosis")} [Ver ${r.version}]</span>
              <a href="${API.getDoctorPrescriptionPdfUrl(r.prescription_id)}" target="_blank" class="btn btn-secondary btn-sm" style="font-size:11px; padding:2px 6px;">PDF</a>
            </div>
          `).join("") +
          `</div>`
        : `<p style="color:var(--text-muted); font-size:12px;">No prescriptions issued yet.</p>`;

      Modal.open({
        title: `Clinical Profile — ${pt.name || patientId}`,
        body: `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; background:var(--bg-surface-secondary); padding:12px; border-radius:6px; font-size:13px;">
              <div><strong>Patient ID:</strong> ${escapeHtml(pt.patient_id || "-")}</div>
              <div><strong>Full Name:</strong> ${escapeHtml(pt.name || "-")}</div>
              <div><strong>Phone:</strong> ${escapeHtml(pt.phone || "-")}</div>
              <div><strong>Email:</strong> ${escapeHtml(pt.email || "-")}</div>
            </div>

            <div>
              <h4 style="font-size:14px; font-weight:600; color:var(--text-main); margin-bottom:6px;">Consultation Visits with You</h4>
              ${visitsHtml}
            </div>

            <div>
              <h4 style="font-size:14px; font-weight:600; color:var(--text-main); margin-bottom:6px;">Previous Prescriptions</h4>
              ${rxHtml}
            </div>
          </div>
        `,
      });
    } catch (err) {
      showToast(err.message || "Failed to load clinical profile.", "error");
    }
  },
};

