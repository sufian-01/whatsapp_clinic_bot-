/**
 * Appointments View Module with Manual Booking, Invoice Downloads,
 * Rescheduling, and Cancellation.
 */

import { API } from "../api.js";
import { debounce, escapeHtml, formatCurrency, formatDate, formatTime, getTodayDateStr, Modal, renderBadge, showToast } from "../utils.js";

export const AppointmentsView = {
  container: null,
  searchQuery: "",
  dateFilter: "",
  doctorFilter: "",
  statusFilter: "",
  paymentStatusFilter: "",
  currentPage: 1,
  pageSize: 15,
  totalPages: 1,

  async init() {
    this.container = document.getElementById("view-appointments");
    if (!this.container) return;
    this.render();
    await this.loadAppointments();
  },

  render() {
    this.container.innerHTML = `
      <div class="filter-bar">
        <div class="filter-left">
          <div class="search-input-wrapper">
            <span class="search-icon">🔍</span>
            <input type="text" id="appts-search-input" class="form-input search-input" placeholder="Search patient, phone, token, doctor..." />
          </div>

          <input type="date" id="appts-date-filter" class="form-input filter-select" style="width: 140px;" />

          <select id="appts-status-filter" class="filter-select">
            <option value="">All Statuses</option>
            <option value="Confirmed">Confirmed</option>
            <option value="Pending">Pending</option>
            <option value="Completed">Completed</option>
            <option value="Cancelled">Cancelled</option>
          </select>

          <select id="appts-pay-status-filter" class="filter-select">
            <option value="">All Payments</option>
            <option value="Pending">Payment Pending</option>
            <option value="Paid">Payment Paid</option>
          </select>
        </div>

        <div class="filter-right" style="display: flex; gap: 8px;">
          <button id="appts-reset-btn" class="btn btn-secondary btn-sm">Reset Filters</button>
          <button id="btn-manual-book-appt" class="btn btn-primary btn-sm">
            <span>+</span> Book Appointment
          </button>
        </div>
      </div>

      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Token</th>
                <th>Patient Name</th>
                <th>Phone</th>
                <th>Doctor</th>
                <th>Date & Time</th>
                <th>Fee</th>
                <th>Status</th>
                <th>Payment</th>
                <th style="text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="appts-table-tbody">
              <tr><td colspan="9" class="empty-state-cell">Loading appointments...</td></tr>
            </tbody>
          </table>
        </div>
        <div class="pagination-container">
          <div id="appts-page-info">Showing 0 of 0 appointments</div>
          <div class="pagination-controls">
            <button id="appts-prev-btn" class="btn btn-secondary btn-sm" disabled>Previous</button>
            <button id="appts-next-btn" class="btn btn-secondary btn-sm" disabled>Next</button>
          </div>
        </div>
      </div>
    `;

    document.getElementById("appts-search-input")?.addEventListener(
      "input",
      debounce((e) => {
        this.searchQuery = e.target.value.trim();
        this.currentPage = 1;
        this.loadAppointments();
      }, 300)
    );

    document.getElementById("appts-date-filter")?.addEventListener("change", (e) => {
      this.dateFilter = e.target.value;
      this.currentPage = 1;
      this.loadAppointments();
    });

    document.getElementById("appts-status-filter")?.addEventListener("change", (e) => {
      this.statusFilter = e.target.value;
      this.currentPage = 1;
      this.loadAppointments();
    });

    document.getElementById("appts-pay-status-filter")?.addEventListener("change", (e) => {
      this.paymentStatusFilter = e.target.value;
      this.currentPage = 1;
      this.loadAppointments();
    });

    document.getElementById("appts-reset-btn")?.addEventListener("click", () => {
      this.searchQuery = "";
      this.dateFilter = "";
      this.statusFilter = "";
      this.paymentStatusFilter = "";
      const searchInput = document.getElementById("appts-search-input");
      const dateInput = document.getElementById("appts-date-filter");
      const statusSelect = document.getElementById("appts-status-filter");
      const paySelect = document.getElementById("appts-pay-status-filter");
      if (searchInput) searchInput.value = "";
      if (dateInput) dateInput.value = "";
      if (statusSelect) statusSelect.value = "";
      if (paySelect) paySelect.value = "";
      this.currentPage = 1;
      this.loadAppointments();
    });

    document.getElementById("btn-manual-book-appt")?.addEventListener("click", () => {
      this.openBookAppointmentModal();
    });

    document.getElementById("appts-prev-btn")?.addEventListener("click", () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.loadAppointments();
      }
    });

    document.getElementById("appts-next-btn")?.addEventListener("click", () => {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        this.loadAppointments();
      }
    });
  },

  async loadAppointments() {
    const tbody = document.getElementById("appts-table-tbody");
    if (!tbody) return;

    try {
      const res = await API.listAppointments({
        search: this.searchQuery,
        date: this.dateFilter,
        doctor: this.doctorFilter,
        status: this.statusFilter,
        payment_status: this.paymentStatusFilter,
        page: this.currentPage,
        page_size: this.pageSize,
      });

      this.totalPages = res.total_pages || 1;
      this.currentPage = res.page || 1;

      const pageInfo = document.getElementById("appts-page-info");
      if (pageInfo) {
        pageInfo.textContent = `Showing ${res.appointments.length} of ${res.total} appointments (Page ${this.currentPage} of ${this.totalPages})`;
      }

      const prevBtn = document.getElementById("appts-prev-btn");
      const nextBtn = document.getElementById("appts-next-btn");
      if (prevBtn) prevBtn.disabled = this.currentPage <= 1;
      if (nextBtn) nextBtn.disabled = this.currentPage >= this.totalPages;

      if (!res.appointments || res.appointments.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="empty-state-cell">No appointments match selected filters.</td></tr>`;
        return;
      }

      tbody.innerHTML = res.appointments.map((a) => {
        const token = a.token_no || a.appointment_id || "-";
        const name = a.patient_name || "-";
        const phone = a.phone || "-";
        const doctor = a.doctor || "-";
        const date = a.date || "";
        const time = a.time || "";
        const amount = a.amount || "0";
        const status = a.status || "Confirmed";
        const payStatus = a.payment_status || "Pending";
        const canComplete = status.toLowerCase() === "confirmed" || status.toLowerCase() === "pending";
        const invoiceUrl = API.getAppointmentInvoiceUrl(token);

        return `
          <tr>
            <td style="font-weight:600; font-family:monospace; color:var(--text-secondary);">${escapeHtml(token)}</td>
            <td style="font-weight:600;">${escapeHtml(name)}</td>
            <td>${escapeHtml(phone)}</td>
            <td>${escapeHtml(doctor)}</td>
            <td>
              <div>${formatDate(date)}</div>
              <div style="font-size:11.5px; color:var(--text-muted);">${escapeHtml(formatTime(time))}</div>
            </td>
            <td style="font-weight:600;">${formatCurrency(amount)}</td>
            <td>${renderBadge(status)}</td>
            <td>${renderBadge(payStatus)}</td>
            <td style="text-align: right; white-space: nowrap;">
              <button class="btn btn-secondary btn-sm view-appt-btn" data-id="${escapeHtml(token)}">
                View
              </button>
              <a href="${invoiceUrl}" target="_blank" class="btn btn-outline btn-sm" title="Download PDF Invoice" style="text-decoration:none;">
                📄
              </a>
              ${canComplete ? `
                <button class="btn btn-secondary btn-sm complete-appt-btn" data-id="${escapeHtml(token)}">
                  Complete
                </button>
              ` : ""}
            </td>
          </tr>
        `;
      }).join("");

      tbody.querySelectorAll(".view-appt-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const id = e.currentTarget.getAttribute("data-id");
          this.openAppointmentDetailsModal(id);
        });
      });

      tbody.querySelectorAll(".complete-appt-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          const id = e.currentTarget.getAttribute("data-id");
          await this.completeAppointment(id);
        });
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="9" class="empty-state-cell" style="color:red;">Error: ${escapeHtml(err.message)}</td></tr>`;
      showToast(err.message || "Failed to load appointments", "error");
    }
  },

  async openBookAppointmentModal() {
    try {
      const [doctors, patientsRes] = await Promise.all([
        API.listDoctors({ active_only: true }),
        API.listPatients({ page_size: 100 }),
      ]);

      const activeDoctors = doctors || [];
      const patientList = patientsRes.patients || [];
      const todayStr = getTodayDateStr();

      const bodyHtml = `
        <form id="book-appt-form">
          <div class="form-group">
            <label class="form-label">Patient Selection *</label>
            <div style="display:flex; gap:12px; margin-bottom:8px;">
              <label style="font-size:13px; cursor:pointer;">
                <input type="radio" name="patient-type" value="existing" checked id="pt-type-existing" /> Existing Patient
              </label>
              <label style="font-size:13px; cursor:pointer;">
                <input type="radio" name="patient-type" value="new" id="pt-type-new" /> New Patient
              </label>
            </div>

            <!-- Existing Patient Dropdown -->
            <div id="box-existing-patient">
              <select id="book-select-patient" class="form-select">
                <option value="">Select a registered patient...</option>
                ${patientList.map(p => `
                  <option value="${escapeHtml(p.patient_id)}" data-name="${escapeHtml(p.name)}" data-phone="${escapeHtml(p.phone)}">
                    ${escapeHtml(p.name)} (${escapeHtml(p.phone)}) - ${escapeHtml(p.patient_id)}
                  </option>
                `).join("")}
              </select>
            </div>

            <!-- New Patient Fields Inline -->
            <div id="box-new-patient" style="display:none; background:var(--bg-app); border:1px solid var(--border-light); border-radius:6px; padding:12px;">
              <div class="form-group" style="margin-bottom:8px;">
                <label class="form-label" style="font-size:12px;">Full Name *</label>
                <input type="text" id="book-new-name" class="form-input" placeholder="e.g. Meera Kapoor" />
              </div>
              <div class="form-row" style="margin-bottom:8px;">
                <div class="form-group">
                  <label class="form-label" style="font-size:12px;">Phone Number *</label>
                  <input type="tel" id="book-new-phone" class="form-input" placeholder="e.g. 9876543210" />
                </div>
                <div class="form-group">
                  <label class="form-label" style="font-size:12px;">Email Address</label>
                  <input type="email" id="book-new-email" class="form-input" placeholder="e.g. meera@example.com" />
                </div>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Consulting Doctor *</label>
              <select id="book-select-doctor" class="form-select" required>
                <option value="">Select doctor...</option>
                ${activeDoctors.map(d => `
                  <option value="${escapeHtml(d['Doctor ID'] || d.doctor_id)}" data-name="${escapeHtml(d['Doctor Name'] || d.name)}" data-fee="${escapeHtml(d['Consultation Fee'] || d.fee || '500')}">
                    ${escapeHtml(d['Doctor Name'] || d.name)} (${escapeHtml(d['Specialization'] || d.specialization)}) - ₹${escapeHtml(d['Consultation Fee'] || d.fee || '500')}
                  </option>
                `).join("")}
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Appointment Date *</label>
              <input type="date" id="book-input-date" class="form-input" min="${todayStr}" value="${todayStr}" required />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Available Time Slot *</label>
            <select id="book-select-slot" class="form-select" required>
              <option value="">Select doctor and date to load open slots...</option>
            </select>
            <div id="book-slot-loading" style="display:none; font-size:12px; color:var(--text-muted); margin-top:4px;">Loading slots...</div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Consultation Fee (₹)</label>
              <input type="text" id="book-input-fee" class="form-input" value="500" />
            </div>
            <div class="form-group">
              <label class="form-label">Payment Method</label>
              <select id="book-select-pay-method" class="form-select">
                <option value="Offline">Offline (Pay at Clinic)</option>
                <option value="Cash">Cash</option>
                <option value="UPI">UPI</option>
                <option value="Card">Card</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Payment Status</label>
              <select id="book-select-pay-status" class="form-select">
                <option value="Pending">Pending</option>
                <option value="Paid">Paid</option>
              </select>
            </div>
          </div>
        </form>
      `;

      const footerHtml = `
        <button type="button" class="btn btn-secondary" onclick="window.Modal.close()">Cancel</button>
        <button type="button" id="submit-manual-book-btn" class="btn btn-primary">Confirm Booking</button>
      `;

      Modal.open("Book Clinic Appointment", bodyHtml, footerHtml);

      // Toggle existing vs new patient UI
      const radioExisting = document.getElementById("pt-type-existing");
      const radioNew = document.getElementById("pt-type-new");
      const boxExisting = document.getElementById("box-existing-patient");
      const boxNew = document.getElementById("box-new-patient");

      radioExisting?.addEventListener("change", () => {
        if (boxExisting) boxExisting.style.display = "block";
        if (boxNew) boxNew.style.display = "none";
      });
      radioNew?.addEventListener("change", () => {
        if (boxExisting) boxExisting.style.display = "none";
        if (boxNew) boxNew.style.display = "block";
      });

      // Doctor change updates fee and reloads slots
      const docSelect = document.getElementById("book-select-doctor");
      const dateInput = document.getElementById("book-input-date");
      const feeInput = document.getElementById("book-input-fee");

      const updateSlots = async () => {
        const docId = docSelect?.value;
        const dateVal = dateInput?.value;
        const slotSelect = document.getElementById("book-select-slot");
        const loadingIndicator = document.getElementById("book-slot-loading");

        if (!docId || !dateVal || !slotSelect) return;

        // Update fee
        const opt = docSelect.selectedOptions[0];
        if (opt && feeInput) {
          feeInput.value = opt.getAttribute("data-fee") || "500";
        }

        slotSelect.innerHTML = `<option value="">Loading slots...</option>`;
        if (loadingIndicator) loadingIndicator.style.display = "block";

        try {
          const docName = opt?.getAttribute("data-name") || "";
          const slots = await API.listSlots({
            doctor: docName,
            date: dateVal,
            status: "Available",
          });

          if (!slots || slots.length === 0) {
            slotSelect.innerHTML = `<option value="">No available slots on ${dateVal} for this doctor</option>`;
          } else {
            slotSelect.innerHTML = `<option value="">Select a time slot (${slots.length} available)...</option>` +
              slots.map(s => `
                <option value="${escapeHtml(s['Slot ID'] || s.slot_id)}">
                  ${escapeHtml(formatTime(s['Start Time'] || s.start_time))} - ${escapeHtml(formatTime(s['End Time'] || s.end_time))} (${escapeHtml(s['Slot ID'] || s.slot_id)})
                </option>
              `).join("");
          }
        } catch (e) {
          slotSelect.innerHTML = `<option value="">Failed to load slots</option>`;
        } finally {
          if (loadingIndicator) loadingIndicator.style.display = "none";
        }
      };

      docSelect?.addEventListener("change", updateSlots);
      dateInput?.addEventListener("change", updateSlots);

      // Submit manual appointment booking
      document.getElementById("submit-manual-book-btn")?.addEventListener("click", async () => {
        const slotId = document.getElementById("book-select-slot")?.value;
        if (!slotId) {
          showToast("Please select an available appointment slot", "error");
          return;
        }

        const isNew = radioNew?.checked;
        let payload = {
          slot_id: slotId,
          amount: feeInput?.value?.trim() || "500",
          payment_method: document.getElementById("book-select-pay-method")?.value || "Offline",
          payment_status: document.getElementById("book-select-pay-status")?.value || "Pending",
        };

        if (isNew) {
          const name = document.getElementById("book-new-name")?.value?.trim();
          const phone = document.getElementById("book-new-phone")?.value?.trim();
          const email = document.getElementById("book-new-email")?.value?.trim();
          if (!name || !phone) {
            showToast("New patient name and phone are required", "error");
            return;
          }
          payload.name = name;
          payload.phone = phone;
          payload.email = email;
        } else {
          const patientId = document.getElementById("book-select-patient")?.value;
          if (!patientId) {
            showToast("Please select an existing patient or switch to New Patient", "error");
            return;
          }
          payload.patient_id = patientId;
        }

        const btn = document.getElementById("submit-manual-book-btn");
        if (btn) {
          btn.disabled = true;
          btn.textContent = "Booking Slot...";
        }

        try {
          const res = await API.createAppointment(payload);
          showToast(`Appointment booked successfully! Token: ${res.token_no}`, "success");
          Modal.close();
          window.dispatchEvent(new CustomEvent("crm:appointment-changed"));
          await this.loadAppointments();
        } catch (err) {
          showToast(err.message || "Failed to book appointment", "error");
          if (btn) {
            btn.disabled = false;
            btn.textContent = "Confirm Booking";
          }
        }
      });
    } catch (err) {
      showToast(err.message || "Failed to initialize booking form", "error");
    }
  },

  async openAppointmentDetailsModal(appointmentId) {
    try {
      const appt = await API.getAppointment(appointmentId);
      const isActionable = ["confirmed", "pending"].includes(appt.status.toLowerCase());
      const invoiceUrl = API.getAppointmentInvoiceUrl(appt.token_no || appt.appointment_id);

      const bodyHtml = `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="background:var(--bg-app); border:1px solid var(--border-light); border-radius:var(--radius-md); padding:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
              <div>
                <span style="font-size:12px; color:var(--text-muted);">Token Number</span>
                <h3 style="font-size:18px; font-weight:700; font-family:monospace; color:var(--text-main); margin:0;">
                  ${escapeHtml(appt.token_no || appt.appointment_id)}
                </h3>
              </div>
              <div style="display:flex; gap:8px; align-items:center;">
                <a href="${invoiceUrl}" target="_blank" class="btn btn-outline btn-sm" style="text-decoration:none;">
                  📄 Download PDF Invoice
                </a>
                <div>${renderBadge(appt.status)}</div>
              </div>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:13px;">
              <div><strong>Patient Name:</strong> ${escapeHtml(appt.patient_name)}</div>
              <div><strong>Contact Phone:</strong> ${escapeHtml(appt.phone || "-")}</div>
              <div><strong>Doctor:</strong> ${escapeHtml(appt.doctor)}</div>
              <div><strong>Date & Time:</strong> ${formatDate(appt.date)} at ${escapeHtml(formatTime(appt.time))}</div>
              <div><strong>Consultation Fee:</strong> ${formatCurrency(appt.amount)}</div>
              <div><strong>Payment Status:</strong> ${renderBadge(appt.payment_status)} (${escapeHtml(appt.payment_method || "Offline")})</div>
            </div>
          </div>

          ${!isActionable ? `
            <div style="padding:10px 14px; background:var(--bg-app); border:1px solid var(--border-light); border-radius:var(--radius-md); font-size:12.5px; color:var(--text-secondary);">
              ℹ️ This appointment is <strong>${escapeHtml(appt.status)}</strong> and cannot be rescheduled or cancelled.
            </div>
          ` : ""}
        </div>
      `;

      const footerHtml = `
        <button class="btn btn-secondary" id="modal-close-btn">Close</button>
        ${isActionable ? `
          <button id="modal-reschedule-btn" class="btn btn-secondary">Reschedule</button>
          <button id="modal-cancel-btn" class="btn btn-danger">Cancel Appointment</button>
          <button id="modal-complete-btn" class="btn btn-primary">Mark Completed</button>
        ` : ""}
      `;

      Modal.open(`Appointment Details`, bodyHtml, footerHtml);

      document.getElementById("modal-close-btn")?.addEventListener("click", () => Modal.close());

      document.getElementById("modal-complete-btn")?.addEventListener("click", async () => {
        Modal.close();
        await this.completeAppointment(appt.token_no || appt.appointment_id);
      });

      document.getElementById("modal-reschedule-btn")?.addEventListener("click", () => {
        this.openRescheduleModal(appt);
      });

      document.getElementById("modal-cancel-btn")?.addEventListener("click", () => {
        this.openCancelModal(appt);
      });
    } catch (err) {
      showToast(err.message || "Failed to load appointment details", "error");
    }
  },

  async openRescheduleModal(appt) {
    const todayStr = getTodayDateStr();
    const initialDate = appt.date && appt.date >= todayStr ? appt.date : todayStr;
    let selectedSlot = null;

    const bodyHtml = `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div style="background:var(--bg-app); border:1px solid var(--border-light); border-radius:var(--radius-md); padding:14px; font-size:13px;">
          <div><strong>Patient:</strong> ${escapeHtml(appt.patient_name)} (${escapeHtml(appt.token_no || appt.appointment_id)})</div>
          <div style="margin-top:4px;"><strong>Doctor:</strong> ${escapeHtml(appt.doctor)}</div>
          <div style="margin-top:4px; color:var(--text-muted);">Current Schedule: ${formatDate(appt.date)} at ${escapeHtml(formatTime(appt.time))}</div>
        </div>

        <div>
          <label style="display:block; font-size:12.5px; font-weight:600; margin-bottom:6px;">Select New Date</label>
          <input type="date" id="resched-date-picker" class="form-input" min="${todayStr}" value="${initialDate}" style="width:100%;" />
        </div>

        <div>
          <label style="display:block; font-size:12.5px; font-weight:600; margin-bottom:6px;">Select Available Time Slot</label>
          <div id="resched-slots-container" style="display:grid; grid-template-columns:repeat(auto-fill, minmax(130px, 1fr)); gap:8px; max-height:160px; overflow-y:auto; padding:4px;">
            <div style="color:var(--text-muted); font-size:12px; grid-column:1/-1;">Loading slots...</div>
          </div>
        </div>

        <div id="resched-preview-box" style="display:none; background:#ecfdf5; border:1px solid #a7f3d0; border-radius:var(--radius-md); padding:12px; font-size:12.5px;">
          <div style="font-weight:700; color:#065f46; margin-bottom:4px;">Ready to Reschedule</div>
          <div style="color:#047857;">New Appointment: <strong id="resched-preview-date">-</strong> at <strong id="resched-preview-time">-</strong></div>
        </div>
      </div>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="window.Modal.close()">Cancel</button>
      <button id="resched-confirm-btn" class="btn btn-primary" disabled>Confirm Reschedule</button>
    `;

    Modal.open(`Reschedule Appointment`, bodyHtml, footerHtml);

    const loadSlotsForDate = async (selectedDate) => {
      const container = document.getElementById("resched-slots-container");
      const previewBox = document.getElementById("resched-preview-box");
      const confirmBtn = document.getElementById("resched-confirm-btn");
      if (!container) return;

      selectedSlot = null;
      if (confirmBtn) confirmBtn.disabled = true;
      if (previewBox) previewBox.style.display = "none";

      container.innerHTML = `<div style="color:var(--text-muted); font-size:12px; grid-column:1/-1;">Checking available slots...</div>`;

      try {
        const slots = await API.listSlots({
          doctor: appt.doctor,
          date: selectedDate,
          status: "Available",
        });

        if (!slots || slots.length === 0) {
          container.innerHTML = `<div style="color:var(--text-muted); font-size:12px; grid-column:1/-1; padding:12px 0;">No available slots found for Dr. ${escapeHtml(appt.doctor)} on ${formatDate(selectedDate)}. Please choose another date.</div>`;
          return;
        }

        container.innerHTML = slots.map((s) => {
          const sId = s["Slot ID"] || s.slot_id;
          const sTime = s["Start Time"] || s.start_time;
          return `
            <button type="button" class="btn btn-secondary btn-sm resched-slot-chip" data-slot-id="${escapeHtml(sId)}" data-slot-time="${escapeHtml(sTime)}" style="font-size:12px; text-align:center;">
              ${escapeHtml(formatTime(sTime))}
            </button>
          `;
        }).join("");

        container.querySelectorAll(".resched-slot-chip").forEach((chip) => {
          chip.addEventListener("click", (e) => {
            container.querySelectorAll(".resched-slot-chip").forEach((c) => c.classList.remove("btn-primary"));
            e.currentTarget.classList.add("btn-primary");
            e.currentTarget.classList.remove("btn-secondary");

            selectedSlot = {
              slotId: e.currentTarget.getAttribute("data-slot-id"),
              time: e.currentTarget.getAttribute("data-slot-time"),
              date: selectedDate,
            };

            const prevDateEl = document.getElementById("resched-preview-date");
            const prevTimeEl = document.getElementById("resched-preview-time");
            if (prevDateEl) prevDateEl.textContent = formatDate(selectedDate);
            if (prevTimeEl) prevTimeEl.textContent = formatTime(selectedSlot.time);
            if (previewBox) previewBox.style.display = "block";
            if (confirmBtn) confirmBtn.disabled = false;
          });
        });
      } catch (err) {
        container.innerHTML = `<div style="color:red; font-size:12px; grid-column:1/-1;">Failed to load slots: ${escapeHtml(err.message)}</div>`;
      }
    };

    document.getElementById("resched-date-picker")?.addEventListener("change", (e) => {
      loadSlotsForDate(e.target.value);
    });

    await loadSlotsForDate(initialDate);

    document.getElementById("resched-confirm-btn")?.addEventListener("click", async () => {
      if (!selectedSlot) return;
      const confirmBtn = document.getElementById("resched-confirm-btn");
      if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.textContent = "Rescheduling...";
      }

      try {
        const res = await API.rescheduleAppointment(appt.token_no || appt.appointment_id, {
          new_slot_id: selectedSlot.slotId,
          new_date: selectedSlot.date,
          new_time: selectedSlot.time,
        });

        showToast(res.message || "Appointment successfully rescheduled", "success");
        Modal.close();
        await this.loadAppointments();
      } catch (err) {
        showToast(err.message || "Failed to reschedule appointment", "error");
        if (confirmBtn) {
          confirmBtn.disabled = false;
          confirmBtn.textContent = "Confirm Reschedule";
        }
      }
    });
  },

  openCancelModal(appt) {
    const bodyHtml = `
      <div style="display:flex; flex-direction:column; gap:16px;">
        <div style="background:#fef2f2; border:1px solid #fecaca; border-radius:var(--radius-md); padding:14px; font-size:13px; color:#991b1b;">
          <strong>Warning:</strong> Are you sure you want to cancel this appointment?
          <div style="margin-top:6px; color:#b91c1c;">
            <strong>${escapeHtml(appt.patient_name)}</strong> with <strong>Dr. ${escapeHtml(appt.doctor)}</strong><br/>
            Scheduled for ${formatDate(appt.date)} at ${escapeHtml(formatTime(appt.time))} (Token: ${escapeHtml(appt.token_no || appt.appointment_id)})
          </div>
          <p style="margin:8px 0 0; font-size:12px; color:#7f1d1d;">
            • The slot will be released back to Available.<br/>
            • The appointment record will be preserved with status 'Cancelled'.
          </p>
        </div>

        <div>
          <label style="display:block; font-size:12.5px; font-weight:600; margin-bottom:6px;">Cancellation Reason (Optional)</label>
          <input type="text" id="cancel-reason-input" class="form-input" placeholder="e.g., Patient requested cancellation, unwell, scheduling conflict" style="width:100%;" />
        </div>
      </div>
    `;

    const footerHtml = `
      <button class="btn btn-secondary" onclick="window.Modal.close()">Keep Appointment</button>
      <button id="cancel-confirm-btn" class="btn btn-danger">Confirm Cancellation</button>
    `;

    Modal.open(`Cancel Appointment`, bodyHtml, footerHtml);

    document.getElementById("cancel-confirm-btn")?.addEventListener("click", async () => {
      const confirmBtn = document.getElementById("cancel-confirm-btn");
      if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.textContent = "Cancelling...";
      }

      const reason = document.getElementById("cancel-reason-input")?.value?.trim() || "";

      try {
        const res = await API.cancelAppointment(appt.token_no || appt.appointment_id, { reason });
        showToast(res.message || "Appointment cancelled successfully", "success");
        Modal.close();
        await this.loadAppointments();
      } catch (err) {
        showToast(err.message || "Failed to cancel appointment", "error");
        if (confirmBtn) {
          confirmBtn.disabled = false;
          confirmBtn.textContent = "Confirm Cancellation";
        }
      }
    });
  },

  async completeAppointment(identifier) {
    if (!confirm(`Mark appointment '${identifier}' as Completed?`)) return;
    try {
      await API.updateAppointmentStatus(identifier, "Completed");
      showToast(`Appointment ${identifier} marked as Completed`, "success");
      await this.loadAppointments();
    } catch (err) {
      showToast(err.message || "Failed to complete appointment", "error");
    }
  },
};
