/**
 * Doctor Slot Management View Module.
 */

import { API } from "../api.js";
import { escapeHtml, formatDate, formatTime, renderBadge, showToast, Modal } from "../utils.js";

export const DoctorSlotsView = {
  container: null,
  page: 1,
  pageSize: 15,
  total: 0,
  totalPages: 1,
  _abortController: null,

  async init() {
    this.container = document.getElementById("view-doctor-slots");
    if (!this.container) return;
    await this.render();
  },

  renderTableSkeletons(cols = 7, rows = 4) {
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
          <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">My Consultation Slots</h2>
          <p style="font-size: 13px; color: var(--text-secondary);">Manage your open clinical availability, block time, and monitor booked appointments</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <button id="doc-slot-add-btn" class="btn btn-primary btn-sm">
            <span>➕</span> Add Available Slot
          </button>
          <button id="doc-slot-refresh-btn" class="btn btn-secondary btn-sm">
            <span>🔄</span> Refresh
          </button>
        </div>
      </div>

      <!-- Filters -->
      <div class="filter-bar" style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:16px;">
        <input type="date" id="doc-slot-date-filter" class="form-input" style="max-width:160px;" />
        <select id="doc-slot-status-filter" class="form-select" style="max-width:160px;">
          <option value="">All Statuses</option>
          <option value="Available">Available</option>
          <option value="Booked">Booked</option>
          <option value="Unavailable">Unavailable</option>
        </select>
        <button id="doc-slot-reset-filter" class="btn btn-secondary btn-sm">Reset</button>
      </div>

      <!-- Slots Table Card -->
      <div class="card" style="padding: 0; overflow: hidden;">
        <div class="table-container" style="max-height: 560px; overflow-y: auto;">
          <table class="data-table">
            <thead>
              <tr>
                <th>Slot ID</th>
                <th>Date</th>
                <th>Start Time</th>
                <th>End Time</th>
                <th>Status</th>
                <th>Patient / Booking</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="doc-slots-tbody">
              ${this.renderTableSkeletons(7, 4)}
            </tbody>
          </table>
        </div>

        <!-- Doctor Slots Pagination Bar -->
        <div id="doc-slots-pagination-bar" class="pagination-container" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 18px; border-top: 1px solid var(--border-light); background: var(--bg-surface);">
          <div id="doc-slots-page-info" style="font-size: 13px; color: var(--text-secondary); font-weight: 500;">
            Showing 0 slots
          </div>
          <div style="display: flex; gap: 10px; align-items: center;">
            <div style="display: flex; align-items: center; gap: 6px;">
              <label for="doc-slots-page-size" style="font-size: 12px; color: var(--text-secondary);">Per page:</label>
              <select id="doc-slots-page-size" class="form-select" style="font-size: 12px; padding: 4px 8px; width: auto; height: 32px;">
                <option value="10">10</option>
                <option value="15" selected>15</option>
                <option value="25">25</option>
                <option value="50">50</option>
              </select>
            </div>
            <button id="doc-slots-prev-btn" class="btn btn-secondary btn-sm" disabled style="padding: 4px 12px; font-size: 12.5px;">&larr; Previous</button>
            <span id="doc-slots-page-num" style="font-size: 13px; font-weight: 600; padding: 0 4px; color: var(--text-main);">Page 1 of 1</span>
            <button id="doc-slots-next-btn" class="btn btn-secondary btn-sm" disabled style="padding: 4px 12px; font-size: 12.5px;">Next &rarr;</button>
          </div>
        </div>
      </div>
    `;

    document.getElementById("doc-slot-refresh-btn")?.addEventListener("click", () => this.loadData());

    document.getElementById("doc-slot-date-filter")?.addEventListener("change", () => {
      this.page = 1;
      this.loadData();
    });

    document.getElementById("doc-slot-status-filter")?.addEventListener("change", () => {
      this.page = 1;
      this.loadData();
    });

    document.getElementById("doc-slots-page-size")?.addEventListener("change", (e) => {
      this.pageSize = parseInt(e.target.value, 10) || 15;
      this.page = 1;
      this.loadData();
    });

    document.getElementById("doc-slots-prev-btn")?.addEventListener("click", () => {
      if (this.page > 1) {
        this.page--;
        this.loadData();
      }
    });

    document.getElementById("doc-slots-next-btn")?.addEventListener("click", () => {
      if (this.page < this.totalPages) {
        this.page++;
        this.loadData();
      }
    });

    document.getElementById("doc-slot-reset-filter")?.addEventListener("click", () => {
      const dt = document.getElementById("doc-slot-date-filter");
      const st = document.getElementById("doc-slot-status-filter");
      if (dt) dt.value = "";
      if (st) st.value = "";
      this.page = 1;
      this.loadData();
    });

    document.getElementById("doc-slot-add-btn")?.addEventListener("click", () => this.openAddSlotModal());

    await this.loadData();
  },

  async loadData() {
    if (this._abortController) {
      this._abortController.abort();
    }
    this._abortController = new AbortController();

    const dateVal = document.getElementById("doc-slot-date-filter")?.value || "";
    const statusVal = document.getElementById("doc-slot-status-filter")?.value || "";

    const tbody = document.getElementById("doc-slots-tbody");
    if (tbody) {
      tbody.innerHTML = this.renderTableSkeletons(7, 4);
    }

    try {
      const res = await API.getDoctorSlots({
        date: dateVal,
        status: statusVal,
        page: this.page,
        page_size: this.pageSize,
      }, { signal: this._abortController.signal });

      let slots = [];
      if (res && res.slots) {
        slots = res.slots;
        this.total = res.total || 0;
        this.page = res.page || this.page;
        this.totalPages = res.total_pages || Math.ceil(this.total / this.pageSize) || 1;
      } else if (Array.isArray(res)) {
        this.total = res.length;
        this.totalPages = Math.ceil(this.total / this.pageSize) || 1;
        const start = (this.page - 1) * this.pageSize;
        slots = res.slice(start, start + this.pageSize);
      }

      this.updatePaginationUI();
      this.renderTable(slots || []);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Doctor slots error:", err);
      showToast(err.message || "Failed to load slots.", "error");
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align:center; padding: 28px; color: var(--danger-text);">
              <div style="font-weight: 600; margin-bottom: 6px;">⚠️ Unable to load slots: ${escapeHtml(err.message || "Error")}</div>
              <button id="doc-slot-retry-btn" class="btn btn-secondary btn-sm" style="margin-top: 6px;">🔄 Retry Loading</button>
            </td>
          </tr>
        `;
        document.getElementById("doc-slot-retry-btn")?.addEventListener("click", () => this.loadData());
      }
    }
  },

  updatePaginationUI() {
    const pageInfo = document.getElementById("doc-slots-page-info");
    const pageNum = document.getElementById("doc-slots-page-num");
    const prevBtn = document.getElementById("doc-slots-prev-btn");
    const nextBtn = document.getElementById("doc-slots-next-btn");

    if (pageInfo) {
      if (this.total === 0) {
        pageInfo.textContent = "Showing 0 slots";
      } else {
        const start = (this.page - 1) * this.pageSize + 1;
        const end = Math.min(this.page * this.pageSize, this.total);
        pageInfo.textContent = `Showing ${start} – ${end} of ${this.total} slots`;
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

  renderTable(slots) {
    const tbody = document.getElementById("doc-slots-tbody");
    if (!tbody) return;

    if (!slots.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state">No slots found for selected filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = slots.map((s) => {
      const isBooked = (s.Status || s.status || "").toLowerCase() === "booked";
      const isAvailable = (s.Status || s.status || "").toLowerCase() === "available";

      let bookingInfo = "-";
      if (isBooked) {
        bookingInfo = `<strong>${escapeHtml(s["Token No"] || s.token_no || "Booked")}</strong><br/><small>Patient: ${escapeHtml(s["Patient ID"] || s.patient_id || "-")}</small>`;
      }

      return `
        <tr>
          <td><code>${escapeHtml(s["Slot ID"] || s.slot_id)}</code></td>
          <td><strong>${escapeHtml(formatDate(s.Date || s.date))}</strong></td>
          <td>${escapeHtml(formatTime(s["Start Time"] || s.start_time))}</td>
          <td>${escapeHtml(formatTime(s["End Time"] || s.end_time))}</td>
          <td>${renderBadge(s.Status || s.status)}</td>
          <td>${bookingInfo}</td>
          <td>
            <div style="display:flex; gap:6px;">
              ${isAvailable ? `
                <button class="btn btn-secondary btn-sm doc-block-slot-btn" data-id="${escapeHtml(s["Slot ID"] || s.slot_id)}">
                  Mark Unavailable
                </button>
              ` : isBooked ? `
                <span style="font-size:12px; color:var(--text-muted);">Protected (Active Booking)</span>
              ` : `
                <button class="btn btn-secondary btn-sm doc-unblock-slot-btn" data-id="${escapeHtml(s["Slot ID"] || s.slot_id)}">
                  Make Available
                </button>
              `}
            </div>
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".doc-block-slot-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.toggleSlotStatus(btn.dataset.id, "Unavailable"));
    });

    tbody.querySelectorAll(".doc-unblock-slot-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.toggleSlotStatus(btn.dataset.id, "Available"));
    });
  },

  openAddSlotModal() {
    const today = new Date().toISOString().split("T")[0];

    Modal.open({
      title: "Add Available Consultation Slot",
      body: `
        <form id="doc-add-slot-form" style="display:flex; flex-direction:column; gap:16px;">
          <div class="form-group">
            <label class="form-label">Slot Date *</label>
            <input type="date" id="new-slot-date" class="form-input" min="${today}" value="${today}" required />
          </div>

          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px;">
            <div class="form-group">
              <label class="form-label">Start Time *</label>
              <input type="text" id="new-slot-start" class="form-input" placeholder="e.g. 10:00 AM" required />
            </div>
            <div class="form-group">
              <label class="form-label">End Time *</label>
              <input type="text" id="new-slot-end" class="form-input" placeholder="e.g. 10:30 AM" required />
            </div>
          </div>

          <div style="font-size:12px; color:var(--text-muted); background:var(--bg-surface-secondary); padding:8px 12px; border-radius:4px;">
            ℹ️ Operating hours: 08:00 AM – 09:00 PM. Slots cannot overlap with existing scheduled appointments.
          </div>

          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button type="button" class="btn btn-secondary" id="doc-add-slot-cancel-btn">Cancel</button>
            <button type="submit" id="new-slot-submit-btn" class="btn btn-primary">Create Slot</button>
          </div>
        </form>
      `,
    });

    document.getElementById("doc-add-slot-cancel-btn")?.addEventListener("click", () => {
      Modal.close();
    });

    document.getElementById("doc-add-slot-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const submitBtn = document.getElementById("new-slot-submit-btn");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Creating...";
      }

      const dateVal = document.getElementById("new-slot-date").value;
      const startTime = document.getElementById("new-slot-start").value.trim();
      const endTime = document.getElementById("new-slot-end").value.trim();

      try {
        await API.createDoctorSlot({
          date: dateVal,
          start_time: startTime,
          end_time: endTime,
        });
        showToast("Slot created successfully!", "success");
        Modal.close();
        await this.loadData();
      } catch (err) {
        showToast(err.message || "Failed to create slot.", "error");
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Create Slot";
        }
      }
    });
  },

  async toggleSlotStatus(slotId, newStatus) {
    try {
      await API.updateDoctorSlot(slotId, { status: newStatus });
      showToast(`Slot status updated to ${newStatus}.`, "success");
      this.loadData();
    } catch (err) {
      showToast(err.message || "Failed to update slot status.", "error");
    }
  },
};

