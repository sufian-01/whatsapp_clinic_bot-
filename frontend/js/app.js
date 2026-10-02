/**
 * Main Application Orchestrator for Clinic CRM Admin.
 */

import { Auth } from "./auth.js";
import { Modal } from "./utils.js";
import { DashboardView } from "./views/dashboard.js";
import { AppointmentsView } from "./views/appointments.js";
import { CalendarView } from "./views/calendar.js";
import { PatientsView } from "./views/patients.js";
import { DoctorsView } from "./views/doctors.js";
import { SlotsView } from "./views/slots.js";
import { PaymentsView } from "./views/payments.js";
import { ReportsView } from "./views/reports.js";
import { AuditLogsView } from "./views/audit_logs.js";
import { SettingsView } from "./views/settings.js";

const VIEWS = {
  dashboard: {
    title: "Dashboard",
    subtitle: "Clinic Operations & Metrics",
    module: DashboardView,
  },
  appointments: {
    title: "Appointments",
    subtitle: "Patient Bookings & Schedules",
    module: AppointmentsView,
  },
  calendar: {
    title: "Calendar",
    subtitle: "Day, Week, and Month Visual Schedule",
    module: CalendarView,
  },
  patients: {
    title: "Patient Directory",
    subtitle: "Patient Profiles & Medical Visit History",
    module: PatientsView,
  },
  doctors: {
    title: "Doctor Directory",
    subtitle: "Clinical Specialists, Schedules & Consultation Fees",
    module: DoctorsView,
  },
  slots: {
    title: "Appointment Slots",
    subtitle: "Google Sheets Slot Master & Booking Safeguards",
    module: SlotsView,
  },
  payments: {
    title: "Billing & Payments",
    subtitle: "Offline UPI & Clinic Fee Reconciliations",
    module: PaymentsView,
  },
  reports: {
    title: "Reports & Analytics",
    subtitle: "Operational Metrics & CSV Exports",
    module: ReportsView,
  },
  "audit-logs": {
    title: "Activity & Audit Logs",
    subtitle: "Immutable Administrative & Clinical Audit Trail",
    module: AuditLogsView,
  },
  settings: {
    title: "Clinic Settings",
    subtitle: "System Status & Admin Account",
    module: SettingsView,
  },
};

class App {
  constructor() {
    this.currentView = null;
  }

  init() {
    // 1. Guard route
    if (!Auth.requireAuth()) {
      return;
    }

    // 2. Setup user metadata in UI
    this.setupUserInfo();

    // 3. Setup global UI events (sidebar, modals, logout)
    this.setupGlobalEvents();

    // 4. Setup routing
    window.addEventListener("hashchange", () => this.handleHashChange());

    // 5. Initial route
    this.handleHashChange();
  }

  setupUserInfo() {
    const user = Auth.getUser();
    if (user) {
      const nameEl = document.getElementById("header-user-name");
      const clinicEl = document.getElementById("header-clinic-name");
      const avatarEl = document.getElementById("sidebar-user-avatar");

      if (nameEl) nameEl.textContent = user.username || "Admin";
      if (clinicEl && user.clinic_name) clinicEl.textContent = user.clinic_name;
      if (avatarEl) {
        avatarEl.textContent = (user.username || "A").substring(0, 1).toUpperCase();
      }
    }
  }

  setupGlobalEvents() {
    // Mobile sidebar toggle
    const toggleBtn = document.getElementById("mobile-menu-toggle");
    const sidebar = document.getElementById("app-sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");

    toggleBtn?.addEventListener("click", () => {
      sidebar?.classList.toggle("open");
      backdrop?.classList.toggle("active");
    });

    backdrop?.addEventListener("click", () => {
      sidebar?.classList.remove("open");
      backdrop?.classList.remove("active");
    });

    // Close modal on backdrop or close button click
    const modalBackdrop = document.getElementById("app-modal-backdrop");
    const modalCloseBtn = document.getElementById("app-modal-close-btn");

    modalCloseBtn?.addEventListener("click", () => Modal.close());
    modalBackdrop?.addEventListener("click", (e) => {
      if (e.target === modalBackdrop) {
        Modal.close();
      }
    });

    // Logout button in header
    document.getElementById("header-logout-btn")?.addEventListener("click", () => {
      if (confirm("Are you sure you want to sign out?")) {
        Auth.logout();
      }
    });
  }

  handleHashChange() {
    const rawHash = window.location.hash.replace(/^#\/?/, "").toLowerCase();
    const viewKey = VIEWS[rawHash] ? rawHash : "dashboard";

    this.loadView(viewKey);
  }

  async loadView(viewKey) {
    if (this.currentView === viewKey) return;
    this.currentView = viewKey;

    const config = VIEWS[viewKey];
    if (!config) return;

    // Update active nav links
    document.querySelectorAll(".nav-item").forEach((el) => {
      if (el.getAttribute("data-view") === viewKey) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    });

    // Update Header titles
    const headingEl = document.getElementById("view-heading");
    const subheadingEl = document.getElementById("view-subheading");
    if (headingEl) headingEl.textContent = config.title;
    if (subheadingEl) subheadingEl.textContent = config.subtitle;

    // Toggle view containers
    document.querySelectorAll(".view-container").forEach((el) => {
      el.classList.remove("active");
    });

    const targetContainer = document.getElementById(`view-${viewKey}`);
    if (targetContainer) {
      targetContainer.classList.add("active");
    }

    // Close mobile sidebar if open
    document.getElementById("app-sidebar")?.classList.remove("open");
    document.getElementById("sidebar-backdrop")?.classList.remove("active");

    // Initialize View Module
    if (config.module && typeof config.module.init === "function") {
      await config.module.init();
    }
  }
}

// Bootstrap application on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  const app = new App();
  app.init();
});
