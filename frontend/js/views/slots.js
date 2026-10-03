/**
 * Appointment Slots View Module.
 */

import { API } from "../api.js";
import { escapeHtml, formatDate, formatTime, Modal, renderBadge, showToast, renderTableSkeletons } from "../utils.js";

export const SlotsView = {
  container: null,
  dateFilter: "",
  doctorFilter: "",
  statusFilter: "",
  doctorsList: [],
  _abortController: null,

  async init() {
    this.container = document.getElementById("view-slots");
    if (!this.container) return;
    this.render();
    await this.loadDoctors();
    await this.loadSlots();
  },

  render() {
    this.container.innerHTML = `
      <div class="filter-bar">
        <div class="filter-left">
          <input type="date" id="slots-date-filter" class="form-input filter-select" style="width: 140px;" />

          <select id="slots-doctor-filter" class="filter-select" style="min-width: 160px;">
            <option value="">All Doctors</option>
          </select>

          <select id="slots-status-filter" class="filter-select">
            <option value="">All Statuses</option>
            <option value="Available">Available</option>
            <option value="Booked">Booked</option>
            <option value="Unavailable">Unavailable</option>
          </select>

          <button id="slots-reset-btn" class="btn btn-secondary btn-sm">Reset</button>
        </div>

        <div class="filter-right">
          <button id="add-slot-btn" class="btn btn-primary">
            <span>+</span> Create Slot
          </button>
        </div>
      </div>

      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Slot ID</th>
                <th>Doctor</th>
                <th>Date</th>
                <th>Time Range</th>
                <th>Status</th>
                <th>Booking Ref</th>
                <th style="text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="slots-table-tbody">
              ${renderTableSkeletons(7, 5)}
            </tbody>
          </table>
        </div>
      </div>
    `;

    document.getElementById("slots-date-filter")?.addEventListener("change", (e) => {
      this.dateFilter = e.target.value;
      this.loadSlots();
    });

    document.getElementById("slots-doctor-filter")?.addEventListener("change", (e) => {
      this.doctorFilter = e.target.value;
      this.loadSlots();
    });

    document.getElementById("slots-status-filter")?.addEventListener("change", (e) => {
      this.statusFilter = e.target.value;
      this.loadSlots();
    });

    document.getElementById("slots-reset-btn")?.addEventListener("click", () => {
      this.dateFilter = "";
      this.doctorFilter = "";
      this.statusFilter = "";
      const d = document.getElementById("slots-date-filter");
      const doc = document.getElementById("slots-doctor-filter");
      const st = document.getElementById("slots-status-filter");
      if (d) d.value = "";
      if (doc) doc.value = "";
      if (st) st.value = "";
      this.loadSlots();
    });

    document.getElementById("add-slot-btn")?.addEventListener("click", () => this.openAddSlotModal());
  },

  async loadDoctors() {
    try {
      this.doctorsList = await API.listDoctors();
      const select = document.getElementById("slots-doctor-filter");
      if (!select || !this.doctorsList) return;
      this.doctorsList.forEach((d) => {
        const name = d["Doctor Name"] || d.name;
        if (name) {
          const opt = document.createElement("option");
          opt.value = name;
          opt.textContent = name;
          select.appendChild(opt);
        }
      });
    } catch (e) {
      // ignore
    }
  },

  async loadSlots() {
    const tbody = document.getElementById("slots-table-tbody");
    if (!tbody) return;

    if (this._abortController) {
      this._abortController.abort();
    }
    this._abortController = new AbortController();

    tbody.innerHTML = renderTableSkeletons(7, 5);

    try {
      const slots = await API.listSlots({
        date: this.dateFilter,
        doctor: this.doctorFilter,
        status: this.statusFilter,
      }, { signal: this._abortController.signal });

      if (!slots || slots.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty-state-cell">No slots found matching criteria.</td></tr>`;
        return;
      }

      tbody.innerHTML = slots.map((s) => {
        const id = s["Slot ID"] || s.slot_id;
        const doctor = s["Doctor Name"] || s.doctor_name || "-";
        const date = s.Date || s.date || "-";
        const start = s["Start Time"] || s.start_time || "-";
        const end = s["End Time"] || s.end_time || "-";
        const status = s.Status || s.status || "Available";
        const patientId = s["Patient ID"] || s.patient_id || "";
        const token = s["Token No"] || s.token_no || "";
        const bookingRef = token ? `${token}` : (patientId ? `${patientId}` : "-");

        const isBooked = status.toLowerCase() === "booked";
        const isAvail = status.toLowerCase() === "available";

        return `
          <tr>
            <td style="font-weight:600; font-family:monospace; color:var(--text-secondary);">${escapeHtml(id)}</td>
            <td style="font-weight:600;">${escapeHtml(doctor)}</td>
            <td>${formatDate(date)}</td>
            <td>${escapeHtml(formatTime(start))} - ${escapeHtml(formatTime(end))}</td>
            <td>${renderBadge(status)}</td>
            <td style="font-family:monospace; font-size:12px;">${escapeHtml(bookingRef)}</td>
            <td style="text-align: right;">
              ${isBooked ? `
                <span style="font-size:12px; color:var(--text-muted);">Locked (Booked)</span>
              ` : `
                <button class="btn btn-secondary btn-sm toggle-slot-btn" data-id="${escapeHtml(id)}" data-curr="${escapeHtml(status)}">
                  Mark ${isAvail ? 'Unavailable' : 'Available'}
                </button>
              `}
            </td>
          </tr>
        `;
      }).join("");

      tbody.querySelectorAll(".toggle-slot-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          const id = e.currentTarget.getAttribute("data-id");
          const curr = e.currentTarget.getAttribute("data-curr");
          const target = curr.toLowerCase() === "available" ? "Unavailable" : "Available";
          await this.toggleSlotStatus(id, target);
        });
      });
    } catch (err) {
      if (err.name === "AbortError") return;
      tbody.innerHTML = `<tr><td colspan="7" class="empty-state-cell" style="color:var(--danger,#ef4444); padding:32px 16px;">
        <div style="font-size:24px; margin-bottom:8px;">⚠️</div>
        <div style="font-weight:600; margin-bottom:6px;">Failed to load slots</div>
        <div style="font-size:12px; color:var(--text-secondary); margin-bottom:16px;">${escapeHtml(err.message || "Network request failed")}</div>
        <button id="slots-retry-btn" class="btn btn-secondary btn-sm" style="margin:0 auto;">🔄 Retry Loading</button>
      </td></tr>`;
      document.getElementById("slots-retry-btn")?.addEventListener("click", () => this.loadSlots());
      showToast(err.message || "Failed to load slots", "error");
    }
  },

  async toggleSlotStatus(slotId, targetStatus) {
    try {
      await API.setSlotStatus(slotId, targetStatus);
      showToast(`Slot ${slotId} marked as ${targetStatus}`, "success");
      await this.loadSlots();
    } catch (err) {
      showToast(err.message || "Failed to update slot status", "error");
    }
  },

  openAddSlotModal() {
    const today = new Date().toISOString().split("T")[0];
    const docOptions = (this.doctorsList || [])
      .map((d) => {
        const id = d["Doctor ID"] || d.doctor_id;
        const name = d["Doctor Name"] || d.name;
        return `<option value="${escapeHtml(id)}" data-name="${escapeHtml(name)}">${escapeHtml(name)} (${escapeHtml(id)})</option>`;
      })
      .join("");

    const bodyHtml = `
      <form id="create-slot-form">
        <div class="form-group">
          <label class="form-label">Doctor *</label>
          <select id="slot-doc-select" class="form-select" required>
            <option value="">Select a Doctor</option>
            ${docOptions}
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Date *</label>
          <input type="date" id="slot-date-input" class="form-input" value="${today}" required />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Start Time *</label>
            <input type="text" id="slot-start-input" class="form-input" placeholder="e.g. 10:00 AM" required />
          </div>
          <div class="form-group">
            <label class="form-label">End Time *</label>
            <input type="text" id="slot-end-input" class="form-input" placeholder="e.g. 10:30 AM" required />
          </div>
        </div>
      </form>
    `;

    const footerHtml = `
      <button type="button" class="btn btn-secondary" onclick="document.getElementById('app-modal-backdrop').classList.remove('open')">Cancel</button>
      <button type="button" id="submit-create-slot-btn" class="btn btn-primary">Create Slot</button>
    `;

    Modal.open("Create New Appointment Slot", bodyHtml, footerHtml);

    document.getElementById("submit-create-slot-btn")?.addEventListener("click", async () => {
      const docSelect = document.getElementById("slot-doc-select");
      const selectedOpt = docSelect.selectedOptions[0];
      const doctorId = docSelect.value;
      const doctorName = selectedOpt ? selectedOpt.getAttribute("data-name") : "";
      const date = document.getElementById("slot-date-input").value;
      const startTime = document.getElementById("slot-start-input").value.trim();
      const endTime = document.getElementById("slot-end-input").value.trim();

      if (!doctorId || !date || !startTime || !endTime) {
        showToast("Please fill in all slot fields", "error");
        return;
      }

      try {
        await API.createSlot({
          doctor_id: doctorId,
          doctor_name: doctorName,
          date,
          start_time: startTime,
          end_time: endTime,
          status: "Available",
        });
        showToast("Slot created successfully", "success");
        Modal.close();
        await this.loadSlots();
      } catch (err) {
        showToast(err.message || "Failed to create slot", "error");
      }
    });
  },
};
