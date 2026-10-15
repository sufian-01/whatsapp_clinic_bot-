/**
 * Patients View Module with Duplicate Checking and Soft Deactivation.
 */

import { API } from "../api.js";
import { debounce, escapeHtml, formatDate, formatCurrency, Modal, renderBadge, showToast } from "../utils.js";

export const PatientsView = {
  container: null,
  searchQuery: "",
  currentPage: 1,
  pageSize: 10,
  totalPages: 1,
  _abortController: null,

  async init() {
    this.container = document.getElementById("view-patients");
    if (!this.container) return;
    this.render();
    await this.loadPatients();
  },

  renderTableSkeletons(cols = 9, rows = 5) {
    let out = "";
    for (let r = 0; r < rows; r++) {
      out += "<tr>";
      for (let c = 0; c < cols; c++) {
        const w = 40 + Math.floor(Math.random() * 45);
        out += `<td><div class="skeleton" style="height:14px; width:${w}%; border-radius:4px;"></div></td>`;
      }
      out += "</tr>";
    }
    return out;
  },

  render() {
    this.container.innerHTML = `
      <div class="filter-bar">
        <div class="filter-left">
          <div class="search-input-wrapper">
            <span class="search-icon">🔍</span>
            <input type="text" id="patients-search-input" class="form-input search-input" placeholder="Search by name, phone, email, ID..." />
          </div>
        </div>
        <div class="filter-right">
          <button id="add-patient-btn" class="btn btn-primary">
            <span>+</span> Register Patient
          </button>
        </div>
      </div>

      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Name</th>
                <th>Phone</th>
                <th>Email</th>
                <th>Age / Gender</th>
                <th>Status</th>
                <th>Total Visits</th>
                <th>Last Visit</th>
                <th style="text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="patients-table-tbody">
              ${this.renderTableSkeletons(9, 5)}
            </tbody>
          </table>
        </div>
        <div class="pagination-container" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 18px; border-top: 1px solid var(--border-light); background: var(--bg-surface);">
          <div id="patients-page-info" style="font-size: 13px; color: var(--text-secondary); font-weight: 500;">Showing 0 of 0 patients</div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <label for="patients-page-size" style="font-size: 12px; color: var(--text-secondary);">Per page:</label>
              <select id="patients-page-size" class="form-select" style="font-size: 12px; padding: 4px 8px; width: auto; height: 32px;">
                <option value="10" selected>10</option>
                <option value="25">25</option>
                <option value="50">50</option>
              </select>
            </div>
            <button id="patients-prev-btn" class="btn btn-secondary btn-sm" disabled style="padding: 4px 12px; font-size: 12.5px;">&larr; Previous</button>
            <span id="patients-page-num" style="font-size: 13px; font-weight: 600; padding: 0 4px; color: var(--text-main);">Page 1 of 1</span>
            <button id="patients-next-btn" class="btn btn-secondary btn-sm" disabled style="padding: 4px 12px; font-size: 12.5px;">Next &rarr;</button>
          </div>
        </div>
      </div>
    `;

    const searchInput = document.getElementById("patients-search-input");
    searchInput?.addEventListener(
      "input",
      debounce((e) => {
        this.searchQuery = e.target.value.trim();
        this.currentPage = 1;
        this.loadPatients();
      }, 300)
    );

    document.getElementById("add-patient-btn")?.addEventListener("click", () => this.openAddPatientModal());

    document.getElementById("patients-page-size")?.addEventListener("change", (e) => {
      this.pageSize = parseInt(e.target.value, 10) || 10;
      this.currentPage = 1;
      this.loadPatients();
    });

    document.getElementById("patients-prev-btn")?.addEventListener("click", () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.loadPatients();
      }
    });

    document.getElementById("patients-next-btn")?.addEventListener("click", () => {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        this.loadPatients();
      }
    });
  },

  async loadPatients() {
    const tbody = document.getElementById("patients-table-tbody");
    if (!tbody) return;

    if (this._abortController) {
      this._abortController.abort();
    }
    this._abortController = new AbortController();

    tbody.innerHTML = this.renderTableSkeletons(9, this.pageSize || 5);

    try {
      const res = await API.listPatients(
        {
          search: this.searchQuery,
          page: this.currentPage,
          page_size: this.pageSize,
        },
        { signal: this._abortController.signal }
      );

      this.totalPages = res.total_pages || 1;
      this.currentPage = res.page || 1;

      const pageInfo = document.getElementById("patients-page-info");
      const pageNum = document.getElementById("patients-page-num");
      if (pageInfo) {
        if (!res.total) {
          pageInfo.textContent = "Showing 0 patients";
        } else {
          const start = (this.currentPage - 1) * this.pageSize + 1;
          const end = Math.min(this.currentPage * this.pageSize, res.total);
          pageInfo.textContent = `Showing ${start} – ${end} of ${res.total} patients`;
        }
      }
      if (pageNum) {
        pageNum.textContent = `Page ${this.currentPage} of ${this.totalPages}`;
      }

      const prevBtn = document.getElementById("patients-prev-btn");
      const nextBtn = document.getElementById("patients-next-btn");
      if (prevBtn) prevBtn.disabled = this.currentPage <= 1;
      if (nextBtn) nextBtn.disabled = this.currentPage >= this.totalPages;

      if (!res.patients || res.patients.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="empty-state-cell">No patients found.</td></tr>`;
        return;
      }

      tbody.innerHTML = res.patients.map((p) => {
        const status = p.status || "Active";
        const isInactive = status.toLowerCase() === "inactive";
        return `
          <tr style="${isInactive ? 'opacity: 0.7; background: rgba(0,0,0,0.02);' : ''}">
            <td style="font-weight:600; font-family:monospace; color:var(--text-secondary);">${escapeHtml(p.patient_id)}</td>
            <td style="font-weight:600;">${escapeHtml(p.name)}</td>
            <td>${escapeHtml(p.phone)}</td>
            <td>${escapeHtml(p.email || "-")}</td>
            <td>${escapeHtml([p.age, p.gender].filter(Boolean).join(" / ") || "-")}</td>
            <td>
              <span class="badge ${isInactive ? 'badge-cancelled' : 'badge-completed'}">
                ${escapeHtml(status)}
              </span>
            </td>
            <td><span class="badge badge-info">${p.appointment_count} visits</span></td>
            <td>${formatDate(p.last_appointment_date)}</td>
            <td style="text-align: right; white-space: nowrap;">
              <button class="btn btn-secondary btn-sm view-patient-btn" data-id="${escapeHtml(p.patient_id)}">
                View Profile
              </button>
            </td>
          </tr>
        `;
      }).join("");

      tbody.querySelectorAll(".view-patient-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const id = e.currentTarget.getAttribute("data-id");
          this.openPatientDetailsModal(id);
        });
      });
    } catch (err) {
      if (err.name === "AbortError") return;
      tbody.innerHTML = `<tr><td colspan="9" class="empty-state-cell" style="padding: 24px; text-align: center;"><div style="color: var(--danger, #ef4444); margin-bottom: 8px; font-weight: 500;">Failed to load patients: ${escapeHtml(err.message || "Unknown error")}</div><button id="patients-retry-btn" class="btn btn-secondary btn-sm" style="display:inline-flex; align-items:center; gap:6px;"><span>🔄</span> Retry</button></td></tr>`;
      document.getElementById("patients-retry-btn")?.addEventListener("click", () => this.loadPatients());
      showToast(err.message || "Failed to load patients", "error");
    }
  },

  async openPatientDetailsModal(patientId) {
    try {
      const [patient, appts, payments, rxsRes] = await Promise.all([
        API.getPatient(patientId),
        API.getPatientAppointments(patientId),
        API.getPatientPayments(patientId),
        API.getAdminPrescriptions({ patient_id: patientId }).catch(() => []),
      ]);

      const prescriptions = Array.isArray(rxsRes) ? rxsRes : (rxsRes.prescriptions || []);
      const isInactive = (patient.status || "Active").toLowerCase() === "inactive";

      const SUB_PAGE_SIZE = 5;
      let apptPage = 1;
      const totalApptPages = Math.ceil(appts.length / SUB_PAGE_SIZE) || 1;

      let rxPage = 1;
      const totalRxPages = Math.ceil(prescriptions.length / SUB_PAGE_SIZE) || 1;

      let payPage = 1;
      const totalPayPages = Math.ceil(payments.length / SUB_PAGE_SIZE) || 1;

      const renderApptRows = (page) => {
        const start = (page - 1) * SUB_PAGE_SIZE;
        const slice = appts.slice(start, start + SUB_PAGE_SIZE);
        if (slice.length === 0) return `<tr><td colspan="5" class="empty-state-cell">No appointments found</td></tr>`;
        return slice.map((a) => `
          <tr>
            <td style="font-family:monospace;">${escapeHtml(a["Token No"] || a.token_no || "-")}</td>
            <td>${formatDate(a["Appointment Date"] || a.date)}</td>
            <td>${escapeHtml(a.Doctor || a.doctor || "-")}</td>
            <td>${renderBadge(a["Booking Status"] || a.status || "Confirmed")}</td>
            <td>${renderBadge(a["Payment Status"] || a.payment_status || "Pending")}</td>
          </tr>
        `).join("");
      };

      const renderRxRows = (page) => {
        const start = (page - 1) * SUB_PAGE_SIZE;
        const slice = prescriptions.slice(start, start + SUB_PAGE_SIZE);
        if (slice.length === 0) return `<tr><td colspan="6" class="empty-state-cell">No prescriptions recorded for this patient</td></tr>`;
        return slice.map((rx) => `
          <tr>
            <td style="font-family:monospace; font-weight:600;">${escapeHtml(rx.prescription_id || rx.id)}</td>
            <td>${formatDate(rx.date || rx.created_at)}</td>
            <td>${escapeHtml(rx.doctor_name || rx.doctor_id || "Doctor")}</td>
            <td>${escapeHtml(rx.diagnosis || "—")}</td>
            <td>${renderBadge(rx.status || "draft")}</td>
            <td style="text-align:right; white-space:nowrap;">
              ${(rx.status === "finalized" || rx.status === "amended") ? `
                <a href="${API.getAdminPrescriptionPdfUrl(rx.prescription_id || rx.id)}" target="_blank" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;">
                  📄 PDF
                </a>
              ` : `<span style="color:var(--text-muted); font-size:11px;">Draft</span>`}
            </td>
          </tr>
        `).join("");
      };

      const renderPayRows = (page) => {
        const start = (page - 1) * SUB_PAGE_SIZE;
        const slice = payments.slice(start, start + SUB_PAGE_SIZE);
        if (slice.length === 0) return `<tr><td colspan="5" class="empty-state-cell">No payments recorded</td></tr>`;
        return slice.map((p) => `
          <tr>
            <td style="font-family:monospace;">${escapeHtml(p.token_no || "-")}</td>
            <td>${formatDate(p.appointment_date)}</td>
            <td style="font-weight:600;">${formatCurrency(p.amount)}</td>
            <td>${escapeHtml(p.payment_method || "Offline")}</td>
            <td>${renderBadge(p.payment_status || "Pending")}</td>
          </tr>
        `).join("");
      };

      const bodyHtml = `
        <div style="display:flex; flex-direction:column; gap:20px;">
          <!-- Patient Summary Card -->
          <div style="background:var(--bg-app); border:1px solid var(--border-light); border-radius:var(--radius-md); padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:8px;">
              <div>
                <h3 style="font-size:16px; font-weight:700; color:var(--text-main); margin:0;">
                  ${escapeHtml(patient.name)}
                  <span class="badge ${isInactive ? 'badge-cancelled' : 'badge-completed'}" style="margin-left:8px; font-size:11px;">
                    ${escapeHtml(patient.status || "Active")}
                  </span>
                </h3>
                <span style="font-family:monospace; font-size:12px; color:var(--text-muted);">${escapeHtml(patient.patient_id)}</span>
              </div>
              <div style="display:flex; gap:8px;">
                <button id="edit-patient-btn" class="btn btn-secondary btn-sm">Edit Details</button>
                ${!isInactive ? `
                  <button id="deactivate-patient-btn" class="btn btn-outline btn-sm" style="color:#ef4444; border-color:#fca5a5;">
                    Deactivate
                  </button>
                ` : `
                  <span style="font-size:12px; color:var(--text-muted); padding:4px 8px;">Deactivated</span>
                `}
              </div>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:12px; font-size:13px;">
              <div><strong>Phone:</strong> ${escapeHtml(patient.phone || "-")}</div>
              <div><strong>Email:</strong> ${escapeHtml(patient.email || "-")}</div>
              <div><strong>Age:</strong> ${escapeHtml(patient.age || "-")}</div>
              <div><strong>Gender:</strong> ${escapeHtml(patient.gender || "-")}</div>
            </div>

            <!-- Financial Summary Bar -->
            <div style="margin-top:14px; padding-top:12px; border-top:1px solid var(--border-light); display:grid; grid-template-columns:repeat(3, 1fr); text-align:center; gap:8px;">
              <div>
                <span style="font-size:11px; color:var(--text-muted); display:block;">Total Billed</span>
                <strong style="font-size:14px;">${formatCurrency(patient.total_billed || 0)}</strong>
              </div>
              <div>
                <span style="font-size:11px; color:var(--text-muted); display:block;">Total Paid</span>
                <strong style="font-size:14px; color:#10b981;">${formatCurrency(patient.total_paid || 0)}</strong>
              </div>
              <div>
                <span style="font-size:11px; color:var(--text-muted); display:block;">Pending Balance</span>
                <strong style="font-size:14px; color:${(patient.pending_balance || 0) > 0 ? '#f59e0b' : '#6b7280'};">
                  ${formatCurrency(patient.pending_balance || 0)}
                </strong>
              </div>
            </div>
          </div>

          <!-- Appointment History -->
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <h4 style="font-size:14px; font-weight:700; margin:0; color:var(--text-main);">Appointment History (${appts.length})</h4>
              <div style="display:flex; gap:6px; align-items:center;">
                <button id="modal-appt-prev" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${apptPage <= 1 ? 'disabled' : ''}>&larr; Prev</button>
                <span id="modal-appt-info" style="font-size:11.5px; font-weight:600; color:var(--text-secondary);">Page 1 of ${totalApptPages}</span>
                <button id="modal-appt-next" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${totalApptPages <= 1 ? 'disabled' : ''}>Next &rarr;</button>
              </div>
            </div>
            <div style="border:1px solid var(--border-light); border-radius:var(--radius-md); overflow:hidden;">
              <table class="data-table" style="font-size:12.5px; margin:0;">
                <thead>
                  <tr>
                    <th>Token</th>
                    <th>Date</th>
                    <th>Doctor</th>
                    <th>Status</th>
                    <th>Payment</th>
                  </tr>
                </thead>
                <tbody id="modal-appt-tbody">
                  ${renderApptRows(1)}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Prescription History -->
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <h4 style="font-size:14px; font-weight:700; margin:0; color:var(--text-main);">Prescription History (${prescriptions.length})</h4>
              <div style="display:flex; gap:6px; align-items:center;">
                <button id="modal-rx-prev" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${rxPage <= 1 ? 'disabled' : ''}>&larr; Prev</button>
                <span id="modal-rx-info" style="font-size:11.5px; font-weight:600; color:var(--text-secondary);">Page 1 of ${totalRxPages}</span>
                <button id="modal-rx-next" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${totalRxPages <= 1 ? 'disabled' : ''}>Next &rarr;</button>
              </div>
            </div>
            <div style="border:1px solid var(--border-light); border-radius:var(--radius-md); overflow:hidden;">
              <table class="data-table" style="font-size:12.5px; margin:0;">
                <thead>
                  <tr>
                    <th>Rx ID</th>
                    <th>Date</th>
                    <th>Doctor</th>
                    <th>Diagnosis</th>
                    <th>Status</th>
                    <th style="text-align:right;">Action</th>
                  </tr>
                </thead>
                <tbody id="modal-rx-tbody">
                  ${renderRxRows(1)}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Payment History -->
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <h4 style="font-size:14px; font-weight:700; margin:0; color:var(--text-main);">Payment Records (${payments.length})</h4>
              <div style="display:flex; gap:6px; align-items:center;">
                <button id="modal-pay-prev" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${payPage <= 1 ? 'disabled' : ''}>&larr; Prev</button>
                <span id="modal-pay-info" style="font-size:11.5px; font-weight:600; color:var(--text-secondary);">Page 1 of ${totalPayPages}</span>
                <button id="modal-pay-next" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${totalPayPages <= 1 ? 'disabled' : ''}>Next &rarr;</button>
              </div>
            </div>
            <div style="border:1px solid var(--border-light); border-radius:var(--radius-md); overflow:hidden;">
              <table class="data-table" style="font-size:12.5px; margin:0;">
                <thead>
                  <tr>
                    <th>Token</th>
                    <th>Date</th>
                    <th>Amount</th>
                    <th>Method</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody id="modal-pay-tbody">
                  ${renderPayRows(1)}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;

      const footerHtml = `
        <button id="modal-close-action-btn" class="btn btn-secondary">Close</button>
      `;

      Modal.open(`Patient Profile`, bodyHtml, footerHtml);

      // Bind Appointment sub-table pagination
      document.getElementById("modal-appt-prev")?.addEventListener("click", () => {
        if (apptPage > 1) {
          apptPage--;
          const tb = document.getElementById("modal-appt-tbody");
          if (tb) tb.innerHTML = renderApptRows(apptPage);
          const info = document.getElementById("modal-appt-info");
          if (info) info.textContent = `Page ${apptPage} of ${totalApptPages}`;
          const p = document.getElementById("modal-appt-prev");
          const n = document.getElementById("modal-appt-next");
          if (p) p.disabled = apptPage <= 1;
          if (n) n.disabled = apptPage >= totalApptPages;
        }
      });
      document.getElementById("modal-appt-next")?.addEventListener("click", () => {
        if (apptPage < totalApptPages) {
          apptPage++;
          const tb = document.getElementById("modal-appt-tbody");
          if (tb) tb.innerHTML = renderApptRows(apptPage);
          const info = document.getElementById("modal-appt-info");
          if (info) info.textContent = `Page ${apptPage} of ${totalApptPages}`;
          const p = document.getElementById("modal-appt-prev");
          const n = document.getElementById("modal-appt-next");
          if (p) p.disabled = apptPage <= 1;
          if (n) n.disabled = apptPage >= totalApptPages;
        }
      });

      // Bind Prescription sub-table pagination
      document.getElementById("modal-rx-prev")?.addEventListener("click", () => {
        if (rxPage > 1) {
          rxPage--;
          const tb = document.getElementById("modal-rx-tbody");
          if (tb) tb.innerHTML = renderRxRows(rxPage);
          const info = document.getElementById("modal-rx-info");
          if (info) info.textContent = `Page ${rxPage} of ${totalRxPages}`;
          const p = document.getElementById("modal-rx-prev");
          const n = document.getElementById("modal-rx-next");
          if (p) p.disabled = rxPage <= 1;
          if (n) n.disabled = rxPage >= totalRxPages;
        }
      });
      document.getElementById("modal-rx-next")?.addEventListener("click", () => {
        if (rxPage < totalRxPages) {
          rxPage++;
          const tb = document.getElementById("modal-rx-tbody");
          if (tb) tb.innerHTML = renderRxRows(rxPage);
          const info = document.getElementById("modal-rx-info");
          if (info) info.textContent = `Page ${rxPage} of ${totalRxPages}`;
          const p = document.getElementById("modal-rx-prev");
          const n = document.getElementById("modal-rx-next");
          if (p) p.disabled = rxPage <= 1;
          if (n) n.disabled = rxPage >= totalRxPages;
        }
      });

      // Bind Payment sub-table pagination
      document.getElementById("modal-pay-prev")?.addEventListener("click", () => {
        if (payPage > 1) {
          payPage--;
          const tb = document.getElementById("modal-pay-tbody");
          if (tb) tb.innerHTML = renderPayRows(payPage);
          const info = document.getElementById("modal-pay-info");
          if (info) info.textContent = `Page ${payPage} of ${totalPayPages}`;
          const p = document.getElementById("modal-pay-prev");
          const n = document.getElementById("modal-pay-next");
          if (p) p.disabled = payPage <= 1;
          if (n) n.disabled = payPage >= totalPayPages;
        }
      });
      document.getElementById("modal-pay-next")?.addEventListener("click", () => {
        if (payPage < totalPayPages) {
          payPage++;
          const tb = document.getElementById("modal-pay-tbody");
          if (tb) tb.innerHTML = renderPayRows(payPage);
          const info = document.getElementById("modal-pay-info");
          if (info) info.textContent = `Page ${payPage} of ${totalPayPages}`;
          const p = document.getElementById("modal-pay-prev");
          const n = document.getElementById("modal-pay-next");
          if (p) p.disabled = payPage <= 1;
          if (n) n.disabled = payPage >= totalPayPages;
        }
      });

      document.getElementById("modal-close-action-btn")?.addEventListener("click", () => Modal.close());
      document.getElementById("edit-patient-btn")?.addEventListener("click", () => {
        this.openEditPatientModal(patient);
      });

      document.getElementById("deactivate-patient-btn")?.addEventListener("click", async () => {
        if (!confirm(`Are you sure you want to deactivate patient "${patient.name}"? Historical visit records will be preserved.`)) {
          return;
        }
        try {
          await API.deactivatePatient(patient.patient_id);
          showToast(`Patient "${patient.name}" deactivated successfully`, "success");
          Modal.close();
          await this.loadPatients();
        } catch (err) {
          showToast(err.message || "Failed to deactivate patient", "error");
        }
      });
    } catch (err) {
      showToast(err.message || "Failed to load patient profile", "error");
    }
  },

  openEditPatientModal(patient) {
    const bodyHtml = `
      <form id="edit-patient-form">
        <div class="form-group">
          <label class="form-label">Full Name</label>
          <input type="text" id="edit-p-name" class="form-input" value="${escapeHtml(patient.name)}" required />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Phone Number</label>
            <input type="tel" id="edit-p-phone" class="form-input" value="${escapeHtml(patient.phone)}" required />
          </div>
          <div class="form-group">
            <label class="form-label">Email Address</label>
            <input type="email" id="edit-p-email" class="form-input" value="${escapeHtml(patient.email || "")}" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Age</label>
            <input type="number" id="edit-p-age" class="form-input" value="${escapeHtml(patient.age || "")}" />
          </div>
          <div class="form-group">
            <label class="form-label">Gender</label>
            <select id="edit-p-gender" class="form-select">
              <option value="">Select Gender</option>
              <option value="Male" ${patient.gender === "Male" ? "selected" : ""}>Male</option>
              <option value="Female" ${patient.gender === "Female" ? "selected" : ""}>Female</option>
              <option value="Other" ${patient.gender === "Other" ? "selected" : ""}>Other</option>
            </select>
          </div>
        </div>
      </form>
    `;

    const footerHtml = `
      <button type="button" class="btn btn-secondary" onclick="window.Modal.close()">Cancel</button>
      <button type="button" id="save-edit-patient-btn" class="btn btn-primary">Save Changes</button>
    `;

    Modal.open(`Edit Patient: ${escapeHtml(patient.patient_id)}`, bodyHtml, footerHtml);

    document.getElementById("save-edit-patient-btn")?.addEventListener("click", async () => {
      const updates = {
        name: document.getElementById("edit-p-name").value.trim(),
        phone: document.getElementById("edit-p-phone").value.trim(),
        email: document.getElementById("edit-p-email").value.trim(),
        age: document.getElementById("edit-p-age").value.trim(),
        gender: document.getElementById("edit-p-gender").value.trim(),
      };

      if (!updates.name || !updates.phone) {
        showToast("Name and phone are required", "error");
        return;
      }

      try {
        await API.updatePatient(patient.patient_id, updates);
        showToast("Patient information updated successfully", "success");
        Modal.close();
        await this.loadPatients();
      } catch (err) {
        showToast(err.message || "Failed to update patient", "error");
      }
    });
  },

  openAddPatientModal() {
    const bodyHtml = `
      <form id="add-patient-form">
        <div id="duplicate-warning-box" style="display:none; background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:12px; margin-bottom:14px; font-size:13px; color:#92400e;">
          <div style="font-weight:700; margin-bottom:4px;">⚠️ Potential Duplicate Patient Detected</div>
          <div id="duplicate-warning-details" style="margin-bottom:8px;"></div>
          <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
            <input type="checkbox" id="add-p-force-checkbox" />
            <span>Register as new patient anyway</span>
          </label>
        </div>

        <div class="form-group">
          <label class="form-label">Full Name *</label>
          <input type="text" id="add-p-name" class="form-input" placeholder="e.g. Rahul Sharma" required />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Phone Number *</label>
            <input type="tel" id="add-p-phone" class="form-input" placeholder="e.g. 9876543210" required />
          </div>
          <div class="form-group">
            <label class="form-label">Email Address</label>
            <input type="email" id="add-p-email" class="form-input" placeholder="e.g. rahul@example.com" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Age</label>
            <input type="number" id="add-p-age" class="form-input" placeholder="e.g. 32" />
          </div>
          <div class="form-group">
            <label class="form-label">Gender</label>
            <select id="add-p-gender" class="form-select">
              <option value="">Select Gender</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Other">Other</option>
            </select>
          </div>
        </div>
      </form>
    `;

    const footerHtml = `
      <button type="button" class="btn btn-secondary" onclick="window.Modal.close()">Cancel</button>
      <button type="button" id="submit-add-patient-btn" class="btn btn-primary">Create Patient</button>
    `;

    Modal.open("Register New Patient", bodyHtml, footerHtml);

    // Live duplicate check on phone input blur
    const phoneInput = document.getElementById("add-p-phone");
    phoneInput?.addEventListener("blur", async (e) => {
      const phoneVal = e.target.value.trim();
      if (phoneVal.length >= 7) {
        try {
          const res = await API.checkPatientDuplicates(phoneVal);
          const warnBox = document.getElementById("duplicate-warning-box");
          const detailsBox = document.getElementById("duplicate-warning-details");
          if (res.has_duplicates && warnBox && detailsBox) {
            const dups = res.duplicates.map(d => `${escapeHtml(d.name)} (${escapeHtml(d.phone)})`).join(", ");
            detailsBox.textContent = `A patient with this phone number already exists: ${dups}.`;
            warnBox.style.display = "block";
          }
        } catch (_) {}
      }
    });

    document.getElementById("submit-add-patient-btn")?.addEventListener("click", async () => {
      const payload = {
        name: document.getElementById("add-p-name").value.trim(),
        phone: document.getElementById("add-p-phone").value.trim(),
        email: document.getElementById("add-p-email").value.trim(),
        age: document.getElementById("add-p-age").value.trim(),
        gender: document.getElementById("add-p-gender").value.trim(),
        booking_status: "Confirmed",
        payment_status: "Pending",
      };

      if (!payload.name || !payload.phone) {
        showToast("Patient name and phone are required", "error");
        return;
      }

      const force = document.getElementById("add-p-force-checkbox")?.checked || false;

      try {
        const res = await API.createPatientWithDedup(payload, force);
        if (res.duplicate_detected && !force) {
          const warnBox = document.getElementById("duplicate-warning-box");
          const detailsBox = document.getElementById("duplicate-warning-details");
          if (warnBox && detailsBox) {
            const dups = (res.duplicates || []).map(d => `${escapeHtml(d.name)} (${escapeHtml(d.phone)})`).join(", ");
            detailsBox.textContent = `Existing record found: ${dups}. Check the box below if you wish to register anyway.`;
            warnBox.style.display = "block";
          }
          showToast("Duplicate patient detected. Please confirm to proceed.", "error");
          return;
        }

        showToast("Patient registered successfully", "success");
        Modal.close();
        window.dispatchEvent(new CustomEvent("crm:patient-changed"));
        await this.loadPatients();
      } catch (err) {
        showToast(err.message || "Failed to create patient", "error");
      }
    });
  },
};
