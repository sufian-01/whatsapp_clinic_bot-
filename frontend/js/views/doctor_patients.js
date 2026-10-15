/**
 * Doctor Patients View Module.
 */

import { API } from "../api.js";
import { debounce, escapeHtml, formatDate, renderBadge, showToast, Modal } from "../utils.js";

export const DoctorPatientsView = {
  container: null,
  page: 1,
  pageSize: 10,
  total: 0,
  totalPages: 1,
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

      <!-- Patients Table Card -->
      <div class="card" style="padding: 0; overflow: hidden;">
        <div class="table-container" style="max-height: 560px; overflow-y: auto;">
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

        <!-- Doctor Patients Pagination Bar -->
        <div id="doc-patients-pagination-bar" class="pagination-container" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 18px; border-top: 1px solid var(--border-light); background: var(--bg-surface);">
          <div id="doc-patients-page-info" style="font-size: 13px; color: var(--text-secondary); font-weight: 500;">
            Showing 0 patients
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <label for="doc-patients-page-size" style="font-size: 12px; color: var(--text-secondary);">Per page:</label>
              <select id="doc-patients-page-size" class="form-select" style="font-size: 12px; padding: 4px 8px; width: auto; height: 32px;">
                <option value="10" selected>10</option>
                <option value="20">20</option>
                <option value="50">50</option>
              </select>
            </div>
            <button id="doc-patients-prev-btn" class="btn btn-secondary btn-sm" disabled style="padding: 4px 12px; font-size: 12.5px;">&larr; Previous</button>
            <span id="doc-patients-page-num" style="font-size: 13px; font-weight: 600; padding: 0 4px; color: var(--text-main);">Page 1 of 1</span>
            <button id="doc-patients-next-btn" class="btn btn-secondary btn-sm" disabled style="padding: 4px 12px; font-size: 12.5px;">Next &rarr;</button>
          </div>
        </div>
      </div>
    `;

    document.getElementById("doc-patients-refresh-btn")?.addEventListener("click", () => this.loadData());
    document.getElementById("doc-patient-search")?.addEventListener("input", debounce(() => {
      this.page = 1;
      this.loadData();
    }, 250));
    document.getElementById("doc-patient-paid-only")?.addEventListener("change", () => {
      this.page = 1;
      this.loadData();
    });

    document.getElementById("doc-patients-page-size")?.addEventListener("change", (e) => {
      this.pageSize = parseInt(e.target.value, 10) || 10;
      this.page = 1;
      this.loadData();
    });

    document.getElementById("doc-patients-prev-btn")?.addEventListener("click", () => {
      if (this.page > 1) {
        this.page--;
        this.loadData();
      }
    });

    document.getElementById("doc-patients-next-btn")?.addEventListener("click", () => {
      if (this.page < this.totalPages) {
        this.page++;
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

    const search = document.getElementById("doc-patient-search")?.value.trim() || "";
    const paidOnly = document.getElementById("doc-patient-paid-only")?.checked || false;

    const tbody = document.getElementById("doc-patients-tbody");
    if (tbody) {
      tbody.innerHTML = this.renderTableSkeletons(8, 4);
    }

    try {
      const res = await API.getDoctorPatients({
        search,
        require_paid: paidOnly,
        page: this.page,
        page_size: this.pageSize,
      }, { signal: this._abortController.signal });

      let patients = [];
      if (res && res.patients) {
        patients = res.patients;
        this.total = res.total || 0;
        this.page = res.page || this.page;
        this.totalPages = res.total_pages || Math.ceil(this.total / this.pageSize) || 1;
      } else if (Array.isArray(res)) {
        this.total = res.length;
        this.totalPages = Math.ceil(this.total / this.pageSize) || 1;
        const start = (this.page - 1) * this.pageSize;
        patients = res.slice(start, start + this.pageSize);
      }

      this.updatePaginationUI();
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

  updatePaginationUI() {
    const pageInfo = document.getElementById("doc-patients-page-info");
    const pageNum = document.getElementById("doc-patients-page-num");
    const prevBtn = document.getElementById("doc-patients-prev-btn");
    const nextBtn = document.getElementById("doc-patients-next-btn");

    if (pageInfo) {
      if (this.total === 0) {
        pageInfo.textContent = "Showing 0 patients";
      } else {
        const start = (this.page - 1) * this.pageSize + 1;
        const end = Math.min(this.page * this.pageSize, this.total);
        pageInfo.textContent = `Showing ${start} – ${end} of ${this.total} patients`;
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

      const SUB_PAGE_SIZE = 5;
      let visitPage = 1;
      const totalVisitPages = Math.ceil(visits.length / SUB_PAGE_SIZE) || 1;

      let rxPage = 1;
      const totalRxPages = Math.ceil(rxs.length / SUB_PAGE_SIZE) || 1;

      const renderVisitRows = (page) => {
        const start = (page - 1) * SUB_PAGE_SIZE;
        const slice = visits.slice(start, start + SUB_PAGE_SIZE);
        if (!slice.length) return `<p style="color:var(--text-muted); font-size:12px; padding:6px 0;">No recorded visits.</p>`;
        return slice.map((v) => `
          <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px dashed var(--border-light); font-size:12px;">
            <span><strong>${formatDate(v.date)}</strong> at ${v.time} (Token: ${v.token_no})</span>
            <span>${renderBadge(v.status)} ${renderBadge(v.payment_status)}</span>
          </div>
        `).join("");
      };

      const renderRxRows = (page) => {
        const start = (page - 1) * SUB_PAGE_SIZE;
        const slice = rxs.slice(start, start + SUB_PAGE_SIZE);
        if (!slice.length) return `<p style="color:var(--text-muted); font-size:12px; padding:6px 0;">No prescriptions issued yet.</p>`;
        return slice.map((r) => `
          <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px dashed var(--border-light); font-size:12px;">
            <span><strong>${r.prescription_id}</strong> (${formatDate(r.date)}) - ${escapeHtml(r.diagnosis || "No diagnosis")} [Ver ${r.version}]</span>
            <a href="${API.getDoctorPrescriptionPdfUrl(r.prescription_id)}" target="_blank" class="btn btn-secondary btn-sm" style="font-size:11px; padding:2px 6px;">PDF</a>
          </div>
        `).join("");
      };

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
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <h4 style="font-size:14px; font-weight:600; color:var(--text-main); margin:0;">Consultation Visits with You (${visits.length})</h4>
                <div style="display:flex; gap:6px; align-items:center;">
                  <button id="doc-pt-visit-prev" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${visitPage <= 1 ? 'disabled' : ''}>&larr; Prev</button>
                  <span id="doc-pt-visit-info" style="font-size:11.5px; font-weight:600; color:var(--text-secondary);">Page 1 of ${totalVisitPages}</span>
                  <button id="doc-pt-visit-next" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${totalVisitPages <= 1 ? 'disabled' : ''}>Next &rarr;</button>
                </div>
              </div>
              <div id="doc-pt-visit-container" style="border:1px solid var(--border-light); border-radius:4px; padding:8px 12px; background:var(--bg-surface);">
                ${renderVisitRows(1)}
              </div>
            </div>

            <div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <h4 style="font-size:14px; font-weight:600; color:var(--text-main); margin:0;">Previous Prescriptions (${rxs.length})</h4>
                <div style="display:flex; gap:6px; align-items:center;">
                  <button id="doc-pt-rx-prev" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${rxPage <= 1 ? 'disabled' : ''}>&larr; Prev</button>
                  <span id="doc-pt-rx-info" style="font-size:11.5px; font-weight:600; color:var(--text-secondary);">Page 1 of ${totalRxPages}</span>
                  <button id="doc-pt-rx-next" class="btn btn-secondary btn-sm" style="padding:2px 8px; font-size:11px;" ${totalRxPages <= 1 ? 'disabled' : ''}>Next &rarr;</button>
                </div>
              </div>
              <div id="doc-pt-rx-container" style="border:1px solid var(--border-light); border-radius:4px; padding:8px 12px; background:var(--bg-surface);">
                ${renderRxRows(1)}
              </div>
            </div>
          </div>
        `,
      });

      // Bind Visit pagination
      document.getElementById("doc-pt-visit-prev")?.addEventListener("click", () => {
        if (visitPage > 1) {
          visitPage--;
          const c = document.getElementById("doc-pt-visit-container");
          if (c) c.innerHTML = renderVisitRows(visitPage);
          const info = document.getElementById("doc-pt-visit-info");
          if (info) info.textContent = `Page ${visitPage} of ${totalVisitPages}`;
          const p = document.getElementById("doc-pt-visit-prev");
          const n = document.getElementById("doc-pt-visit-next");
          if (p) p.disabled = visitPage <= 1;
          if (n) n.disabled = visitPage >= totalVisitPages;
        }
      });
      document.getElementById("doc-pt-visit-next")?.addEventListener("click", () => {
        if (visitPage < totalVisitPages) {
          visitPage++;
          const c = document.getElementById("doc-pt-visit-container");
          if (c) c.innerHTML = renderVisitRows(visitPage);
          const info = document.getElementById("doc-pt-visit-info");
          if (info) info.textContent = `Page ${visitPage} of ${totalVisitPages}`;
          const p = document.getElementById("doc-pt-visit-prev");
          const n = document.getElementById("doc-pt-visit-next");
          if (p) p.disabled = visitPage <= 1;
          if (n) n.disabled = visitPage >= totalVisitPages;
        }
      });

      // Bind Rx pagination
      document.getElementById("doc-pt-rx-prev")?.addEventListener("click", () => {
        if (rxPage > 1) {
          rxPage--;
          const c = document.getElementById("doc-pt-rx-container");
          if (c) c.innerHTML = renderRxRows(rxPage);
          const info = document.getElementById("doc-pt-rx-info");
          if (info) info.textContent = `Page ${rxPage} of ${totalRxPages}`;
          const p = document.getElementById("doc-pt-rx-prev");
          const n = document.getElementById("doc-pt-rx-next");
          if (p) p.disabled = rxPage <= 1;
          if (n) n.disabled = rxPage >= totalRxPages;
        }
      });
      document.getElementById("doc-pt-rx-next")?.addEventListener("click", () => {
        if (rxPage < totalRxPages) {
          rxPage++;
          const c = document.getElementById("doc-pt-rx-container");
          if (c) c.innerHTML = renderRxRows(rxPage);
          const info = document.getElementById("doc-pt-rx-info");
          if (info) info.textContent = `Page ${rxPage} of ${totalRxPages}`;
          const p = document.getElementById("doc-pt-rx-prev");
          const n = document.getElementById("doc-pt-rx-next");
          if (p) p.disabled = rxPage <= 1;
          if (n) n.disabled = rxPage >= totalRxPages;
        }
      });
    } catch (err) {
      showToast(err.message || "Failed to load clinical profile.", "error");
    }
  },
};

