/**
 * Doctors View Module.
 */

import { API } from "../api.js";
import { debounce, escapeHtml, formatCurrency, Modal, renderBadge, showToast } from "../utils.js";

export const DoctorsView = {
  container: null,
  searchQuery: "",
  doctorsList: [],

  async init() {
    this.container = document.getElementById("view-doctors");
    if (!this.container) return;
    this.render();
    await this.loadDoctors();
  },

  render() {
    this.container.innerHTML = `
      <div class="filter-bar">
        <div class="filter-left">
          <div class="search-input-wrapper">
            <span class="search-icon">🔍</span>
            <input type="text" id="doctors-search-input" class="form-input search-input" placeholder="Search by doctor name or specialty..." />
          </div>
        </div>
        <div class="filter-right">
          <button id="add-doctor-btn" class="btn btn-primary">
            <span>+</span> Add Doctor
          </button>
        </div>
      </div>

      <div id="doctors-grid-container" class="doctors-grid">
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
          Loading clinic doctors...
        </div>
      </div>
    `;

    const searchInput = document.getElementById("doctors-search-input");
    searchInput?.addEventListener(
      "input",
      debounce((e) => {
        this.searchQuery = e.target.value.trim();
        this.loadDoctors();
      }, 300)
    );

    document.getElementById("add-doctor-btn")?.addEventListener("click", () => this.openAddDoctorModal());
  },

  async loadDoctors() {
    const grid = document.getElementById("doctors-grid-container");
    if (!grid) return;

    try {
      const doctors = await API.listDoctors({
        search: this.searchQuery,
      });

      this.doctorsList = doctors;

      if (!doctors || doctors.length === 0) {
        grid.innerHTML = `
          <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
            No doctors found matching criteria.
          </div>
        `;
        return;
      }

      grid.innerHTML = doctors.map((d) => {
        const id = d["Doctor ID"] || d.doctor_id || "";
        const name = d["Doctor Name"] || d.name || "";
        const spec = d["Specialization"] || d.specialization || "";
        const days = d["Available Days"] || d.available_days || "";
        const start = d["Start Time"] || d.start_time || "";
        const end = d["End Time"] || d.end_time || "";
        const fee = d["Consultation Fee"] || d.fee || "";
        const status = d["Status"] || d.status || "Active";
        const isActive = status.toLowerCase() === "active";

        return `
          <div class="doctor-card">
            <div>
              <div class="doctor-top">
                <div class="doctor-meta">
                  <h3>${escapeHtml(name)}</h3>
                  <div class="doctor-specialty">${escapeHtml(spec)}</div>
                </div>
                ${renderBadge(status)}
              </div>

              <div class="doctor-info-list">
                <div class="doctor-info-item">
                  <span>🆔</span>
                  <span><strong>ID:</strong> <code style="font-size:12px;">${escapeHtml(id)}</code></span>
                </div>
                <div class="doctor-info-item">
                  <span>📅</span>
                  <span><strong>Days:</strong> ${escapeHtml(days || "Flexible")}</span>
                </div>
                <div class="doctor-info-item">
                  <span>⏰</span>
                  <span><strong>Hours:</strong> ${escapeHtml(start)} - ${escapeHtml(end)}</span>
                </div>
                <div class="doctor-info-item">
                  <span>💵</span>
                  <span><strong>Fee:</strong> ${formatCurrency(fee)}</span>
                </div>
              </div>
            </div>

            <div class="doctor-actions">
              <button class="btn btn-secondary btn-sm slots-doc-btn" data-id="${escapeHtml(id)}" data-name="${escapeHtml(name)}">
                View Slots
              </button>
              <button class="btn btn-secondary btn-sm edit-doc-btn" data-id="${escapeHtml(id)}">
                Edit
              </button>
              <button class="btn ${isActive ? 'btn-outline-danger' : 'btn-primary'} btn-sm toggle-status-btn" data-id="${escapeHtml(id)}" data-status="${escapeHtml(status)}">
                ${isActive ? 'Deactivate' : 'Activate'}
              </button>
            </div>
          </div>
        `;
      }).join("");

      grid.querySelectorAll(".edit-doc-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const id = e.currentTarget.getAttribute("data-id");
          const doc = this.doctorsList.find((d) => (d["Doctor ID"] || d.doctor_id) === id);
          if (doc) this.openEditDoctorModal(doc);
        });
      });

      grid.querySelectorAll(".toggle-status-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          const id = e.currentTarget.getAttribute("data-id");
          const curr = e.currentTarget.getAttribute("data-status");
          const next = curr.toLowerCase() === "active" ? "Inactive" : "Active";
          await this.toggleDoctorStatus(id, next);
        });
      });

      grid.querySelectorAll(".slots-doc-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const id = e.currentTarget.getAttribute("data-id");
          const name = e.currentTarget.getAttribute("data-name");
          this.openDoctorSlotsModal(id, name);
        });
      });
    } catch (err) {
      grid.innerHTML = `<div style="grid-column: 1 / -1; color: red; text-align: center;">Error: ${escapeHtml(err.message)}</div>`;
      showToast(err.message || "Failed to load doctors", "error");
    }
  },

  async toggleDoctorStatus(doctorId, nextStatus) {
    if (nextStatus.toLowerCase() === "inactive") {
      try {
        const safety = await API.checkDoctorDeactivation(doctorId);
        if (!safety.safe_to_deactivate) {
          const proceed = confirm(
            `⚠️ Safety Warning: Dr. ${safety.doctor_name || doctorId} has ${safety.upcoming_appointments_count} upcoming active appointment(s).\n\nDeactivating this doctor will prevent new bookings while preserving existing appointments.\n\nDo you want to proceed with deactivation?`
          );
          if (!proceed) return;
        } else {
          if (!confirm(`Are you sure you want to deactivate Dr. (${doctorId})?`)) return;
        }
      } catch (_) {
        if (!confirm(`Are you sure you want to set Dr. (${doctorId}) status to ${nextStatus}?`)) return;
      }
    } else {
      if (!confirm(`Are you sure you want to activate Dr. (${doctorId})?`)) return;
    }

    try {
      await API.setDoctorStatus(doctorId, nextStatus);
      showToast(`Doctor status updated to ${nextStatus}`, "success");
      await this.loadDoctors();
    } catch (err) {
      showToast(err.message || "Failed to change doctor status", "error");
    }
  },

  openAddDoctorModal() {
    const bodyHtml = `
      <form id="add-doctor-form">
        <div class="form-group">
          <label class="form-label">Doctor Name *</label>
          <input type="text" id="add-doc-name" class="form-input" placeholder="e.g. Dr. Arjun Mehta" required />
        </div>
        <div class="form-group">
          <label class="form-label">Specialization *</label>
          <input type="text" id="add-doc-spec" class="form-input" placeholder="e.g. General Physician" required />
        </div>
        <div class="form-group">
          <label class="form-label">Available Days</label>
          <input type="text" id="add-doc-days" class="form-input" value="Monday, Wednesday, Friday" />
          <div class="form-helper">Comma separated days (e.g. Monday, Wednesday, Friday)</div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Start Time</label>
            <input type="text" id="add-doc-start" class="form-input" value="10:00 AM" />
          </div>
          <div class="form-group">
            <label class="form-label">End Time</label>
            <input type="text" id="add-doc-end" class="form-input" value="1:00 PM" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Consultation Fee (₹) *</label>
            <input type="number" id="add-doc-fee" class="form-input" value="500" required />
          </div>
          <div class="form-group">
            <label class="form-label">Status</label>
            <select id="add-doc-status" class="form-select">
              <option value="Active" selected>Active</option>
              <option value="Inactive">Inactive</option>
            </select>
          </div>
        </div>
      </form>
    `;

    const footerHtml = `
      <button type="button" class="btn btn-secondary" onclick="document.getElementById('app-modal-backdrop').classList.remove('open')">Cancel</button>
      <button type="button" id="submit-add-doc-btn" class="btn btn-primary">Add Doctor</button>
    `;

    Modal.open("Add New Doctor", bodyHtml, footerHtml);

    document.getElementById("submit-add-doc-btn")?.addEventListener("click", async () => {
      const payload = {
        name: document.getElementById("add-doc-name").value.trim(),
        specialization: document.getElementById("add-doc-spec").value.trim(),
        available_days: document.getElementById("add-doc-days").value.trim(),
        start_time: document.getElementById("add-doc-start").value.trim(),
        end_time: document.getElementById("add-doc-end").value.trim(),
        consultation_fee: document.getElementById("add-doc-fee").value.trim(),
        status: document.getElementById("add-doc-status").value,
      };

      if (!payload.name || !payload.specialization || !payload.consultation_fee) {
        showToast("Name, specialization, and consultation fee are required", "error");
        return;
      }

      try {
        await API.createDoctor(payload);
        showToast("Doctor added successfully", "success");
        Modal.close();
        await this.loadDoctors();
      } catch (err) {
        showToast(err.message || "Failed to add doctor", "error");
      }
    });
  },

  openEditDoctorModal(doctor) {
    const id = doctor["Doctor ID"] || doctor.doctor_id;
    const name = doctor["Doctor Name"] || doctor.name || "";
    const spec = doctor["Specialization"] || doctor.specialization || "";
    const days = doctor["Available Days"] || doctor.available_days || "";
    const start = doctor["Start Time"] || doctor.start_time || "";
    const end = doctor["End Time"] || doctor.end_time || "";
    const fee = doctor["Consultation Fee"] || doctor.fee || "";
    const status = doctor["Status"] || doctor.status || "Active";

    const bodyHtml = `
      <form id="edit-doctor-form">
        <div class="form-group">
          <label class="form-label">Doctor Name</label>
          <input type="text" id="edit-doc-name" class="form-input" value="${escapeHtml(name)}" required />
        </div>
        <div class="form-group">
          <label class="form-label">Specialization</label>
          <input type="text" id="edit-doc-spec" class="form-input" value="${escapeHtml(spec)}" required />
        </div>
        <div class="form-group">
          <label class="form-label">Available Days</label>
          <input type="text" id="edit-doc-days" class="form-input" value="${escapeHtml(days)}" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Start Time</label>
            <input type="text" id="edit-doc-start" class="form-input" value="${escapeHtml(start)}" />
          </div>
          <div class="form-group">
            <label class="form-label">End Time</label>
            <input type="text" id="edit-doc-end" class="form-input" value="${escapeHtml(end)}" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Consultation Fee (₹)</label>
            <input type="number" id="edit-doc-fee" class="form-input" value="${escapeHtml(fee)}" required />
          </div>
          <div class="form-group">
            <label class="form-label">Status</label>
            <select id="edit-doc-status" class="form-select">
              <option value="Active" ${status === "Active" ? "selected" : ""}>Active</option>
              <option value="Inactive" ${status === "Inactive" ? "selected" : ""}>Inactive</option>
            </select>
          </div>
        </div>
      </form>
    `;

    const footerHtml = `
      <button type="button" class="btn btn-secondary" onclick="document.getElementById('app-modal-backdrop').classList.remove('open')">Cancel</button>
      <button type="button" id="save-edit-doc-btn" class="btn btn-primary">Save Changes</button>
    `;

    Modal.open(`Edit Doctor: ${escapeHtml(name)}`, bodyHtml, footerHtml);

    document.getElementById("save-edit-doc-btn")?.addEventListener("click", async () => {
      const updates = {
        name: document.getElementById("edit-doc-name").value.trim(),
        specialization: document.getElementById("edit-doc-spec").value.trim(),
        available_days: document.getElementById("edit-doc-days").value.trim(),
        start_time: document.getElementById("edit-doc-start").value.trim(),
        end_time: document.getElementById("edit-doc-end").value.trim(),
        consultation_fee: document.getElementById("edit-doc-fee").value.trim(),
        status: document.getElementById("edit-doc-status").value,
      };

      try {
        await API.updateDoctor(id, updates);
        showToast("Doctor details updated successfully", "success");
        Modal.close();
        await this.loadDoctors();
      } catch (err) {
        showToast(err.message || "Failed to update doctor", "error");
      }
    });
  },

  async openDoctorSlotsModal(doctorId, doctorName) {
    try {
      const slots = await API.getDoctorAvailability(doctorId);
      const bodyHtml = `
        <div style="margin-bottom: 12px;">
          <p style="font-size:13px; color:var(--text-secondary);">Upcoming open slots in Google Sheets for <strong>${escapeHtml(doctorName)}</strong>:</p>
        </div>
        <div style="max-height: 250px; overflow-y:auto; border:1px solid var(--border-light); border-radius:var(--radius-md);">
          <table class="data-table" style="font-size:12.5px;">
            <thead>
              <tr>
                <th>Slot ID</th>
                <th>Date</th>
                <th>Time Range</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${!slots || slots.length === 0 ? `<tr><td colspan="4" class="empty-state-cell">No open slots found for this doctor.</td></tr>` : 
                slots.map((s) => `
                  <tr>
                    <td style="font-family:monospace;">${escapeHtml(s["Slot ID"] || s.slot_id)}</td>
                    <td>${escapeHtml(s.Date || s.date)}</td>
                    <td>${escapeHtml(s["Start Time"] || s.start_time)} - ${escapeHtml(s["End Time"] || s.end_time)}</td>
                    <td>${renderBadge(s.Status || s.status || "Available")}</td>
                  </tr>
                `).join("")}
            </tbody>
          </table>
        </div>
      `;

      Modal.open(`Doctor Availability: ${escapeHtml(doctorName)}`, bodyHtml, `<button class="btn btn-secondary" onclick="document.getElementById('app-modal-backdrop').classList.remove('open')">Close</button>`);
    } catch (err) {
      showToast(err.message || "Failed to fetch doctor availability", "error");
    }
  },
};
