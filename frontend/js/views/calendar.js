/**
 * Calendar View Module.
 */

import { API } from "../api.js";
import { escapeHtml, formatDate, formatTime, Modal, renderBadge, showToast } from "../utils.js";

export const CalendarView = {
  container: null,
  currentDate: new Date(),
  viewMode: "month", // "month" | "week" | "day"
  doctorFilter: "",
  events: [],

  async init() {
    this.container = document.getElementById("view-calendar");
    if (!this.container) return;
    this.render();
    await this.loadDoctorsForFilter();
    await this.loadCalendarData();
  },

  render() {
    this.container.innerHTML = `
      <div class="calendar-controls">
        <div class="calendar-nav-group">
          <button id="cal-prev-btn" class="btn btn-secondary btn-icon" title="Previous">◀</button>
          <button id="cal-today-btn" class="btn btn-secondary btn-sm">Today</button>
          <button id="cal-next-btn" class="btn btn-secondary btn-icon" title="Next">▶</button>
          <div id="cal-period-label" class="calendar-period-label" style="margin-left: 10px;">-</div>
        </div>

        <div style="display:flex; align-items:center; gap: 12px;">
          <select id="cal-doctor-filter" class="filter-select" style="min-width: 160px;">
            <option value="">All Doctors</option>
          </select>

          <div class="view-mode-tabs">
            <button class="view-mode-tab active" data-mode="month">Month</button>
            <button class="view-mode-tab" data-mode="week">Week</button>
            <button class="view-mode-tab" data-mode="day">Day</button>
          </div>
        </div>
      </div>

      <div id="cal-body-container">
        <!-- Rendered Calendar View -->
      </div>
    `;

    document.getElementById("cal-prev-btn")?.addEventListener("click", () => {
      this.navigate(-1);
    });

    document.getElementById("cal-next-btn")?.addEventListener("click", () => {
      this.navigate(1);
    });

    document.getElementById("cal-today-btn")?.addEventListener("click", () => {
      this.currentDate = new Date();
      this.loadCalendarData();
    });

    document.querySelectorAll(".view-mode-tab").forEach((tab) => {
      tab.addEventListener("click", (e) => {
        document.querySelectorAll(".view-mode-tab").forEach((t) => t.classList.remove("active"));
        e.currentTarget.classList.add("active");
        this.viewMode = e.currentTarget.getAttribute("data-mode");
        this.renderView();
      });
    });

    document.getElementById("cal-doctor-filter")?.addEventListener("change", (e) => {
      this.doctorFilter = e.target.value;
      this.loadCalendarData();
    });
  },

  async loadDoctorsForFilter() {
    try {
      const doctors = await API.listDoctors();
      const select = document.getElementById("cal-doctor-filter");
      if (!select || !doctors) return;
      doctors.forEach((d) => {
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

  navigate(direction) {
    if (this.viewMode === "month") {
      this.currentDate.setMonth(this.currentDate.getMonth() + direction);
    } else if (this.viewMode === "week") {
      this.currentDate.setDate(this.currentDate.getDate() + direction * 7);
    } else if (this.viewMode === "day") {
      this.currentDate.setDate(this.currentDate.getDate() + direction);
    }
    this.loadCalendarData();
  },

  getRange() {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();

    if (this.viewMode === "month") {
      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);

      // Extend to full week bounds
      const start = new Date(firstDay);
      start.setDate(start.getDate() - start.getDay());

      const end = new Date(lastDay);
      end.setDate(end.getDate() + (6 - end.getDay()));

      return {
        startDate: this.formatIso(start),
        endDate: this.formatIso(end),
      };
    } else if (this.viewMode === "week") {
      const start = new Date(this.currentDate);
      start.setDate(start.getDate() - start.getDay());
      const end = new Date(start);
      end.setDate(end.getDate() + 6);
      return {
        startDate: this.formatIso(start),
        endDate: this.formatIso(end),
      };
    } else {
      const dateStr = this.formatIso(this.currentDate);
      return {
        startDate: dateStr,
        endDate: dateStr,
      };
    }
  },

  formatIso(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  },

  async loadCalendarData() {
    const { startDate, endDate } = this.getRange();
    try {
      this.events = await API.getCalendarEvents(startDate, endDate, this.doctorFilter);
      this.renderView();
    } catch (err) {
      showToast(err.message || "Failed to load calendar events", "error");
    }
  },

  renderView() {
    const label = document.getElementById("cal-period-label");
    const container = document.getElementById("cal-body-container");
    if (!label || !container) return;

    if (this.viewMode === "month") {
      label.textContent = this.currentDate.toLocaleDateString("en-IN", { month: "long", year: "numeric" });
      this.renderMonthView(container);
    } else if (this.viewMode === "week") {
      const { startDate, endDate } = this.getRange();
      label.textContent = `Week: ${formatDate(startDate)} - ${formatDate(endDate)}`;
      this.renderWeekView(container);
    } else {
      label.textContent = this.currentDate.toLocaleDateString("en-IN", { weekday: "long", month: "short", day: "numeric", year: "numeric" });
      this.renderDayView(container);
    }
  },

  renderMonthView(container) {
    const year = this.currentDate.getFullYear();
    const month = this.currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    const start = new Date(firstDay);
    start.setDate(start.getDate() - start.getDay());

    const days = [];
    const curr = new Date(start);
    while (days.length < 35 || (curr.getMonth() === month && days.length < 42)) {
      days.push(new Date(curr));
      curr.setDate(curr.getDate() + 1);
      if (days.length === 35 && curr.getMonth() !== month) break;
    }

    const todayStr = this.formatIso(new Date());

    const daysHeaders = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    container.innerHTML = `
      <div class="calendar-month-grid">
        ${daysHeaders.map((h) => `<div class="calendar-day-header">${h}</div>`).join("")}
        ${days.map((d) => {
          const iso = this.formatIso(d);
          const isOtherMonth = d.getMonth() !== month;
          const isToday = iso === todayStr;
          const dayEvents = this.events.filter((e) => e.date === iso);

          return `
            <div class="calendar-cell ${isOtherMonth ? 'other-month' : ''} ${isToday ? 'today' : ''}">
              <span class="calendar-day-number">${d.getDate()}</span>
              <div class="calendar-events-container">
                ${dayEvents.map((ev) => `
                  <div class="calendar-event-pill status-${ev.status.toLowerCase()}" data-id="${escapeHtml(ev.id)}" title="${escapeHtml(ev.title)} (${escapeHtml(ev.time)})">
                    <strong>${escapeHtml(ev.time)}</strong> ${escapeHtml(ev.patient_name)}
                  </div>
                `).join("")}
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;

    container.querySelectorAll(".calendar-event-pill").forEach((pill) => {
      pill.addEventListener("click", (e) => {
        const id = e.currentTarget.getAttribute("data-id");
        this.openEventDetails(id);
      });
    });
  },

  renderWeekView(container) {
    const { startDate } = this.getRange();
    const start = new Date(startDate);
    const weekDays = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(start);
      d.setDate(d.getDate() + i);
      weekDays.push(d);
    }

    const todayStr = this.formatIso(new Date());

    container.innerHTML = `
      <div class="calendar-month-grid" style="grid-template-columns: repeat(7, 1fr);">
        ${weekDays.map((d) => {
          const iso = this.formatIso(d);
          const isToday = iso === todayStr;
          const dayName = d.toLocaleDateString("en-IN", { weekday: "short" });
          const dayEvents = this.events.filter((e) => e.date === iso);

          return `
            <div class="calendar-cell ${isToday ? 'today' : ''}" style="min-height: 380px;">
              <div style="text-align:center; padding-bottom: 6px; border-bottom: 1px solid var(--border-light); margin-bottom: 6px;">
                <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">${dayName}</div>
                <div class="calendar-day-number" style="margin: 0 auto;">${d.getDate()}</div>
              </div>
              <div class="calendar-events-container">
                ${dayEvents.map((ev) => `
                  <div class="calendar-event-pill status-${ev.status.toLowerCase()}" data-id="${escapeHtml(ev.id)}" style="padding: 4px 6px;">
                    <div><strong>${escapeHtml(ev.time)}</strong> - ${escapeHtml(ev.patient_name)}</div>
                    <div style="font-size:10px; opacity:0.85;">${escapeHtml(ev.doctor)}</div>
                  </div>
                `).join("")}
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;

    container.querySelectorAll(".calendar-event-pill").forEach((pill) => {
      pill.addEventListener("click", (e) => {
        const id = e.currentTarget.getAttribute("data-id");
        this.openEventDetails(id);
      });
    });
  },

  renderDayView(container) {
    const iso = this.formatIso(this.currentDate);
    const dayEvents = this.events.filter((e) => e.date === iso);

    container.innerHTML = `
      <div class="card">
        <div class="card-header">
          <span class="card-title">Schedule for ${formatDate(iso)}</span>
          <span class="badge badge-completed">${dayEvents.length} Appointments</span>
        </div>
        <div class="card-body">
          ${dayEvents.length === 0 ? `<div style="text-align:center; padding: 40px; color:var(--text-muted);">No appointments booked for this day.</div>` : `
            <div style="display:flex; flex-direction:column; gap:10px;">
              ${dayEvents.map((ev) => `
                <div style="display:flex; align-items:center; justify-content:space-between; padding:12px; border:1px solid var(--border-light); border-radius:var(--radius-md); background:var(--bg-surface);">
                  <div>
                    <span style="font-weight:700; color:var(--primary); font-size:14px; margin-right:12px;">${escapeHtml(ev.time)}</span>
                    <strong style="color:var(--text-main); font-size:14px;">${escapeHtml(ev.patient_name)}</strong>
                    <span style="color:var(--text-muted); font-size:12px; margin-left:8px;">(${escapeHtml(ev.doctor)})</span>
                  </div>
                  <div style="display:flex; align-items:center; gap:10px;">
                    ${renderBadge(ev.status)}
                    <button class="btn btn-secondary btn-sm cal-view-btn" data-id="${escapeHtml(ev.id)}">Details</button>
                  </div>
                </div>
              `).join("")}
            </div>
          `}
        </div>
      </div>
    `;

    container.querySelectorAll(".cal-view-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const id = e.currentTarget.getAttribute("data-id");
        this.openEventDetails(id);
      });
    });
  },

  async openEventDetails(appointmentId) {
    try {
      const appt = await API.getAppointment(appointmentId);
      const bodyHtml = `
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:13px;">
          <div><strong>Token:</strong> <span style="font-family:monospace;">${escapeHtml(appt.token_no || appt.appointment_id)}</span></div>
          <div><strong>Status:</strong> ${renderBadge(appt.status)}</div>
          <div><strong>Patient:</strong> ${escapeHtml(appt.patient_name)}</div>
          <div><strong>Phone:</strong> ${escapeHtml(appt.phone || "-")}</div>
          <div><strong>Doctor:</strong> ${escapeHtml(appt.doctor)}</div>
          <div><strong>Date & Time:</strong> ${formatDate(appt.date)} at ${escapeHtml(formatTime(appt.time))}</div>
          <div><strong>Payment:</strong> ${renderBadge(appt.payment_status)}</div>
        </div>
      `;
      Modal.open(`Appointment Details`, bodyHtml, `<button class="btn btn-secondary" onclick="document.getElementById('app-modal-backdrop').classList.remove('open')">Close</button>`);
    } catch (e) {
      showToast(e.message || "Failed to load appointment details", "error");
    }
  },
};
