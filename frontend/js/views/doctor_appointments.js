/**
 * Doctor Appointments View Module.
 * Displays assigned patients and appointments strictly for the logged-in doctor,
 * with priority queue sequencing, payment confirmation gating, and server-side pagination.
 */

import { API } from "../api.js";
import { debounce, escapeHtml, formatDate, formatTime, renderBadge, showToast, Modal } from "../utils.js";
import { DoctorPrescriptionsView } from "./doctor_prescriptions.js";

export const DoctorAppointmentsView = {
  container: null,
  appointments: [],
  currentPage: 1,
  pageSize: 15,
  totalPages: 1,
  totalItems: 0,
  requirePaid: true,
  _abortController: null,

  async init() {
    this.container = document.getElementById("view-doctor-appointments");
    if (!this.container) return;
    await this.render();
  },

  renderTableSkeletons(cols = 10, rows = 4) {
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
          <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">Doctor Consultation Queue & Schedule</h2>
          <p style="font-size: 13px; color: var(--text-secondary);">Chronological patient queue prioritized by payment confirmation and appointment slot timing</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <button id="doc-appt-refresh-btn" class="btn btn-secondary btn-sm">
            <span>🔄</span> Refresh Queue
          </button>
        </div>
      </div>

      <!-- Filters & Priority Toolbar -->
      <div class="filter-bar" style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:16px;">
        <div class="search-input-wrapper" style="min-width:240px; flex:1;">
          <span class="search-icon">🔍</span>
          <input type="text" id="doc-appt-search-input" class="form-input search-input" placeholder="Search patient name, phone, token..." />
        </div>
        <input type="date" id="doc-appt-date-filter" class="form-input" style="max-width:160px;" />
        
        <select id="doc-appt-pay-filter" class="form-select" style="max-width:260px; font-weight:600; color:var(--primary);">
          <option value="true" selected>✓ Confirmed Payments Only (Active Queue)</option>
          <option value="false">All Bookings (Include Unconfirmed)</option>
        </select>

        <select id="doc-appt-status-filter" class="form-select" style="max-width:150px;">
          <option value="">All Statuses</option>
          <option value="Confirmed">Confirmed</option>
          <option value="Completed">Completed</option>
          <option value="Pending">Pending</option>
          <option value="Cancelled">Cancelled</option>
        </select>

        <button id="doc-appt-filter-reset" class="btn btn-secondary btn-sm">Reset</button>
      </div>

      <!-- Appointments Table Card -->
      <div class="card" style="padding:0; overflow:hidden;">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th style="width:90px;">Queue #</th>
                <th>Date & Time</th>
                <th>Token</th>
                <th>Patient Details</th>
                <th>Age / Gender</th>
                <th>Phone</th>
                <th>Booking</th>
                <th>Payment Status</th>
                <th>Prescription</th>
                <th style="text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody id="doc-appt-tbody">
              ${this.renderTableSkeletons(10, 4)}
            </tbody>
          </table>
        </div>

        <!-- Pagination Controls -->
        <div class="pagination-container">
          <div id="doc-appts-page-info">Showing 0 of 0 appointments</div>
          <div class="pagination-controls">
            <button id="doc-appts-prev-btn" class="btn btn-secondary btn-sm" disabled>Previous</button>
            <button id="doc-appts-next-btn" class="btn btn-secondary btn-sm" disabled>Next</button>
          </div>
        </div>
      </div>
    `;

    document.getElementById("doc-appt-refresh-btn")?.addEventListener("click", () => this.loadData());
    document.getElementById("doc-appt-search-input")?.addEventListener("input", debounce(() => {
      this.currentPage = 1;
      this.loadData();
    }, 250));
    document.getElementById("doc-appt-date-filter")?.addEventListener("change", () => {
      this.currentPage = 1;
      this.loadData();
    });
    document.getElementById("doc-appt-pay-filter")?.addEventListener("change", (e) => {
      this.requirePaid = e.target.value === "true";
      this.currentPage = 1;
      this.loadData();
    });
    document.getElementById("doc-appt-status-filter")?.addEventListener("change", () => {
      this.currentPage = 1;
      this.loadData();
    });
    document.getElementById("doc-appt-filter-reset")?.addEventListener("click", () => {
      const search = document.getElementById("doc-appt-search-input");
      const dt = document.getElementById("doc-appt-date-filter");
      const st = document.getElementById("doc-appt-status-filter");
      const pay = document.getElementById("doc-appt-pay-filter");
      if (search) search.value = "";
      if (dt) dt.value = "";
      if (st) st.value = "";
      if (pay) pay.value = "true";
      this.requirePaid = true;
      this.currentPage = 1;
      this.loadData();
    });

    document.getElementById("doc-appts-prev-btn")?.addEventListener("click", () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.loadData();
      }
    });

    document.getElementById("doc-appts-next-btn")?.addEventListener("click", () => {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        this.loadData();
      }
    });

    await this.loadData();
  },

  async loadData() {
    if (this._abortController) {
      this._abortController.abort();
    }
    this._abortController = new AbortController();

    const search = document.getElementById("doc-appt-search-input")?.value.trim() || "";
    const dateVal = document.getElementById("doc-appt-date-filter")?.value || "";
    const statusVal = document.getElementById("doc-appt-status-filter")?.value || "";

    const tbody = document.getElementById("doc-appt-tbody");
    if (tbody) {
      tbody.innerHTML = this.renderTableSkeletons(10, 4);
    }

    try {
      const res = await API.getDoctorAppointments({
        search,
        date: dateVal,
        status: statusVal,
        require_paid: this.requirePaid,
        page: this.currentPage,
        page_size: this.pageSize,
      }, { signal: this._abortController.signal });

      if (Array.isArray(res)) {
        this.appointments = res;
        this.totalItems = res.length;
        this.totalPages = 1;
      } else {
        this.appointments = res.appointments || [];
        this.totalItems = res.total || 0;
        this.totalPages = res.total_pages || 1;
        this.currentPage = res.page || 1;
      }

      const pageInfo = document.getElementById("doc-appts-page-info");
      if (pageInfo) {
        pageInfo.textContent = `Showing ${this.appointments.length} of ${this.totalItems} appointments (Page ${this.currentPage} of ${this.totalPages})`;
      }

      const prevBtn = document.getElementById("doc-appts-prev-btn");
      const nextBtn = document.getElementById("doc-appts-next-btn");
      if (prevBtn) prevBtn.disabled = this.currentPage <= 1;
      if (nextBtn) nextBtn.disabled = this.currentPage >= this.totalPages;

      this.renderTable(this.appointments);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Doctor appointments error:", err);
      showToast(err.message || "Failed to load doctor appointments.", "error");
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="10" style="text-align:center; padding: 28px; color: var(--danger-text);">
              <div style="font-weight: 600; margin-bottom: 6px;">⚠️ Unable to load appointments: ${escapeHtml(err.message || "Error")}</div>
              <button id="doc-appt-retry-btn" class="btn btn-secondary btn-sm" style="margin-top: 6px;">🔄 Retry Loading</button>
            </td>
          </tr>
        `;
        document.getElementById("doc-appt-retry-btn")?.addEventListener("click", () => this.loadData());
      }
    }
  },

  renderTable(appts) {
    const tbody = document.getElementById("doc-appt-tbody");
    if (!tbody) return;

    if (!appts.length) {
      tbody.innerHTML = `<tr><td colspan="10" class="empty-state-cell">No appointments match selected filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = appts.map((a) => {
      let rxBadge = `<span class="badge badge-warning">None</span>`;
      if (a.has_prescription) {
        if (a.prescription_status === "finalized") {
          rxBadge = `<span class="badge badge-completed">Finalized</span>`;
        } else if (a.prescription_status === "amended") {
          rxBadge = `<span class="badge badge-info">Amended</span>`;
        } else {
          rxBadge = `<span class="badge badge-pending">Draft</span>`;
        }
      }

      const ageGenderStr = [a.age ? `${escapeHtml(a.age)} yrs` : "", a.gender ? escapeHtml(a.gender) : ""].filter(Boolean).join(" / ") || "—";
      const tokenStr = a.token_no || a.appointment_id || "";
      const qPos = a.queue_position || "-";
      const isNext = a.queue_position === 1;

      const isPaid = a.is_payment_confirmed || a.payment_status === "Paid" || a.payment_status === "Confirmed";
      const payBadge = isPaid
        ? `<span class="badge badge-completed" title="Payment verified by clinic administration">✓ Confirmed (${escapeHtml(a.payment_method || "Paid")})</span>`
        : `<span class="badge badge-warning" title="Awaiting payment confirmation at reception">⏳ ${escapeHtml(a.payment_status || "Pending")}</span>`;

      return `
        <tr>
          <td>
            <div style="display:flex; align-items:center; gap:6px;">
              <span class="badge" style="background:${isNext ? 'var(--primary-gradient)' : 'var(--bg-surface-secondary)'}; color:${isNext ? '#fff' : 'var(--text-main)'}; font-weight:700; font-size:12px;">#${qPos}</span>
              ${isNext ? '<span class="badge badge-completed" style="font-size:9.5px; padding:2px 5px; font-weight:700;">NEXT</span>' : ''}
            </div>
          </td>
          <td>
            <strong>${escapeHtml(formatDate(a.date))}</strong><br/>
            <small style="color:var(--text-muted);">${escapeHtml(formatTime(a.time))}</small>
          </td>
          <td><code style="font-weight:700;">${escapeHtml(tokenStr)}</code></td>
          <td>
            <strong>${escapeHtml(a.patient_name)}</strong>
            ${a.patient_id ? `<br/><small style="color:var(--text-muted);">ID: ${escapeHtml(a.patient_id)}</small>` : ""}
          </td>
          <td>${ageGenderStr}</td>
          <td>${escapeHtml(a.phone || "-")}</td>
          <td>${renderBadge(a.status)}</td>
          <td>${payBadge}</td>
          <td>${rxBadge}</td>
          <td style="text-align: right;">
            <div style="display:flex; gap:6px; justify-content:flex-end; flex-wrap:wrap;">
              <button class="btn btn-secondary btn-sm doc-view-appt-btn" data-id="${escapeHtml(tokenStr)}">
                Details
              </button>
              <button class="btn btn-primary btn-sm doc-prescribe-btn" data-id="${escapeHtml(tokenStr)}">
                ${a.has_prescription ? "✏️ Edit Rx" : "✍️ Consult & Rx"}
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".doc-view-appt-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.openAppointmentDetails(btn.dataset.id));
    });

    tbody.querySelectorAll(".doc-prescribe-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const token = btn.dataset.id;
        const appt = this.appointments.find((x) => (x.token_no || x.appointment_id) === token);
        if (appt) {
          window.location.hash = "#doctor-prescriptions";
          DoctorPrescriptionsView.openEditorForAppointment(appt);
        }
      });
    });
  },

  async openAppointmentDetails(apptId) {
    try {
      const appt = await API.getDoctorAppointment(apptId);
      const historyHtml = (appt.history || []).length
        ? `<ul style="padding-left:18px; margin-top:8px;">` +
          appt.history.map((h) => `<li>${formatDate(h.date)} at ${h.time} (${h.status}) - Token: ${h.token_no}</li>`).join("") +
          `</ul>`
        : `<p style="color:var(--text-muted); margin-top:8px;">No prior visits recorded with this physician.</p>`;

      const ageGender = [appt.age ? `${escapeHtml(appt.age)} yrs` : "", appt.gender ? escapeHtml(appt.gender) : ""].filter(Boolean).join(" / ") || "—";

      Modal.open({
        title: `Appointment Details — ${appt.token_no || appt.appointment_id}`,
        body: `
          <div style="display:flex; flex-direction:column; gap:16px;">
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; background:var(--bg-surface-secondary); padding:12px; border-radius:6px; font-size:13px;">
              <div><strong>Patient:</strong> ${escapeHtml(appt.patient_name)}</div>
              <div><strong>Patient ID:</strong> <code>${escapeHtml(appt.patient_id || '-')}</code></div>
              <div><strong>Age / Gender:</strong> ${ageGender}</div>
              <div><strong>Contact:</strong> ${escapeHtml(appt.phone || "-")}</div>
              <div><strong>Date & Time:</strong> ${formatDate(appt.date)} at ${appt.time}</div>
              <div><strong>Consultation Fee:</strong> ₹${escapeHtml(appt.amount || "-")}</div>
              <div><strong>Booking Status:</strong> ${renderBadge(appt.status)}</div>
              <div><strong>Payment Status:</strong> ${renderBadge(appt.payment_status)}</div>
            </div>

            <div>
              <h4 style="font-size:14px; font-weight:600; color:var(--text-main);">Clinical Visit History with You:</h4>
              ${historyHtml}
            </div>

            ${appt.prescription ? `
              <div style="border-top:1px solid var(--border-light); padding-top:12px;">
                <h4 style="font-size:14px; font-weight:600; color:var(--text-main);">Prescription (${escapeHtml(appt.prescription.prescription_id)}):</h4>
                <p style="margin-top:4px; font-size:13px;"><strong>Diagnosis:</strong> ${escapeHtml(appt.prescription.diagnosis)}</p>
                <p style="margin-top:2px; font-size:13px;"><strong>Status:</strong> ${renderBadge(appt.prescription.status)}</p>
              </div>
            ` : ""}
          </div>
        `,
      });
    } catch (err) {
      showToast(err.message || "Failed to fetch appointment details.", "error");
    }
  },
};
