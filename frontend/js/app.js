/**
 * Main Application Orchestrator for Clinic CRM Admin & Doctor Portal.
 */

import { Auth } from "./auth.js";
import { API } from "./api.js";
import { Modal, showToast } from "./utils.js";
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
import { DoctorAccountsView } from "./views/doctor_accounts.js";
import { PrescriptionsView } from "./views/prescriptions.js";

// Doctor Portal Views
import { DoctorDashboardView } from "./views/doctor_dashboard.js";
import { DoctorAppointmentsView } from "./views/doctor_appointments.js";
import { DoctorSlotsView } from "./views/doctor_slots.js";
import { DoctorPatientsView } from "./views/doctor_patients.js";
import { DoctorPrescriptionsView } from "./views/doctor_prescriptions.js";
import { ThemeManager } from "./theme.js";

export { ThemeManager };

const DOCTOR_ONLY_ROUTES = new Set([
  "doctor-dashboard",
  "doctor-appointments",
  "doctor-slots",
  "doctor-patients",
  "doctor-prescriptions",
]);

const DOCTOR_ALLOWED_ROUTES = new Set([
  "doctor-dashboard",
  "doctor-appointments",
  "doctor-slots",
  "doctor-patients",
  "doctor-prescriptions",
  "settings",
  "doctor-settings",
]);

const VIEWS = {
  // Admin Views
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
  prescriptions: {
    title: "Prescription Oversight",
    subtitle: "System-wide Clinical Audit & Issued Prescriptions",
    module: PrescriptionsView,
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
  "doctor-accounts": {
    title: "Doctor Accounts",
    subtitle: "Physician Login Credentials & Access Control",
    module: DoctorAccountsView,
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

  // Doctor Views
  "doctor-dashboard": {
    title: "Doctor Dashboard",
    subtitle: "Clinical Consultations & Personal Schedule",
    module: DoctorDashboardView,
  },
  "doctor-appointments": {
    title: "My Appointments",
    subtitle: "Booked Consultations & Patient Visit Records",
    module: DoctorAppointmentsView,
  },
  "doctor-slots": {
    title: "My Availability",
    subtitle: "Manage Working Hours & Consultation Slots",
    module: DoctorSlotsView,
  },
  "doctor-patients": {
    title: "My Patients",
    subtitle: "Patients Assigned to Your Clinical Care",
    module: DoctorPatientsView,
  },
  "doctor-prescriptions": {
    title: "Prescriptions",
    subtitle: "Author, Finalize & Issue Digital Prescriptions",
    module: DoctorPrescriptionsView,
  },
  "doctor-settings": {
    title: "Doctor Settings",
    subtitle: "Profile, Signature & Clinical Credentials",
    module: SettingsView,
  },
};

export function showChangePasswordModal(forced = false) {
  const content = `
    <form id="change-pwd-form" style="display: flex; flex-direction: column; gap: 14px;">
      ${
        forced
          ? '<div style="padding: 10px; background: rgba(245, 158, 11, 0.12); border: 1px solid #f59e0b; border-radius: 6px; font-size: 13px; color: #b45309;">⚠️ First-time login detected. You must change your default password before proceeding.</div>'
          : ""
      }
      <div class="form-group">
        <label class="form-label">Current Password</label>
        <input type="password" id="old-pwd" class="form-control" required autocomplete="current-password" placeholder="Enter existing password" />
      </div>
      <div class="form-group">
        <label class="form-label">New Password (minimum 6 characters)</label>
        <input type="password" id="new-pwd" class="form-control" required minlength="6" autocomplete="new-password" placeholder="Create strong new password" />
      </div>
      <div class="form-group">
        <label class="form-label">Confirm New Password</label>
        <input type="password" id="confirm-pwd" class="form-control" required minlength="6" autocomplete="new-password" placeholder="Repeat new password" />
      </div>
      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px;">
        ${
          !forced
            ? '<button type="button" class="btn btn-secondary" id="change-pwd-cancel-btn">Cancel</button>'
            : ""
        }
        <button type="submit" class="btn btn-primary" id="change-pwd-submit-btn">Update Password</button>
      </div>
    </form>
  `;

  Modal.open("Change Password", content);

  document.getElementById("change-pwd-cancel-btn")?.addEventListener("click", () => {
    Modal.close();
  });

  const form = document.getElementById("change-pwd-form");
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const oldPwd = document.getElementById("old-pwd").value;
    const newPwd = document.getElementById("new-pwd").value;
    const confirmPwd = document.getElementById("confirm-pwd").value;

    if (newPwd !== confirmPwd) {
      showToast("New passwords do not match", "error");
      return;
    }
    if (newPwd.length < 6) {
      showToast("Password must be at least 6 characters", "error");
      return;
    }

    const btn = document.getElementById("change-pwd-submit-btn");
    btn.disabled = true;
    btn.textContent = "Updating...";

    try {
      await API.changePassword(oldPwd, newPwd);
      showToast("Password updated successfully!", "success");
      const u = Auth.getUser();
      if (u) {
        u.must_change_password = false;
        localStorage.setItem("crm_user", JSON.stringify(u));
      }
      Modal.close();
    } catch (err) {
      showToast("Failed to update password: " + err.message, "error");
      btn.disabled = false;
      btn.textContent = "Update Password";
    }
  });
}

class App {
  constructor() {
    this.currentView = null;
    this.initializedViews = new Set();
  }

  init() {
    ThemeManager.init();

    // 1. Guard route
    if (!Auth.requireAuth()) {
      return;
    }

    // 1b. Super Admin has platform scope; redirect to dedicated Platform Console
    if (Auth.isSuperAdmin()) {
      window.location.href = "/super-admin/";
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

    // 6. Check forced password change
    if (Auth.mustChangePassword()) {
      setTimeout(() => {
        showChangePasswordModal(true);
      }, 300);
    }
  }

  setupUserInfo() {
    const user = Auth.getUser();
    if (!user) return;

    const nameEl = document.getElementById("header-user-name");
    const roleEl = document.getElementById("header-user-role");
    const clinicEl = document.getElementById("header-clinic-name");
    const portalLabelEl = document.getElementById("header-portal-label");
    const avatarEl = document.getElementById("sidebar-user-avatar");
    const adminNav = document.getElementById("nav-section-admin");
    const docNav = document.getElementById("nav-section-doctor");

    if (Auth.isDoctor()) {
      if (adminNav) adminNav.style.display = "none";
      if (docNav) docNav.style.display = "block";
      if (portalLabelEl) portalLabelEl.textContent = "Doctor Portal";
      if (nameEl) nameEl.textContent = user.doctor_name || user.username || "Doctor";
      if (roleEl) roleEl.textContent = "Physician / Doctor";
      if (avatarEl) avatarEl.textContent = "Dr";
    } else {
      if (adminNav) adminNav.style.display = "block";
      if (docNav) docNav.style.display = "none";
      if (portalLabelEl) portalLabelEl.textContent = "Admin CRM";
      if (nameEl) nameEl.textContent = user.username || "Admin";
      if (roleEl) roleEl.textContent = "Administrator";
      if (avatarEl) {
        avatarEl.textContent = (user.username || "A").substring(0, 1).toUpperCase();
      }
    }

    this.updateBranding(user.clinic_name, user.clinic_logo);

    // Fetch fresh clinic branding from server to ensure latest logo and name apply everywhere
    API.getClinicSettings()
      .then((settings) => {
        if (settings) {
          const cName = settings.clinic_name || settings.name || user.clinic_name;
          const cLogo = settings.logo !== undefined ? settings.logo : user.clinic_logo;
          this.updateBranding(cName, cLogo);
        }
      })
      .catch((err) => console.debug("Could not refresh clinic branding:", err));
  }

  updateBranding(clinicName, clinicLogo) {
    const clinicEl = document.getElementById("header-clinic-name");
    const brandIconEl = document.getElementById("sidebar-brand-icon") || document.querySelector(".sidebar-header .brand-icon");
    if (clinicEl && clinicName) {
      clinicEl.textContent = clinicName;
      document.title = `${clinicName} - Portal`;
    }
    if (brandIconEl) {
      if (clinicLogo && typeof clinicLogo === "string" && clinicLogo.trim()) {
        brandIconEl.innerHTML = `<img id="sidebar-clinic-logo-img" src="${clinicLogo}" alt="Logo" style="width: 100%; height: 100%; object-fit: contain; border-radius: var(--radius-md); background: #ffffff; padding: 2px;" />`;
        brandIconEl.style.background = "transparent";
        brandIconEl.style.boxShadow = "none";
      } else {
        brandIconEl.innerHTML = "⚕";
        brandIconEl.style.background = "";
        brandIconEl.style.boxShadow = "";
      }
    }
    const user = Auth.getUser();
    if (user) {
      let changed = false;
      if (clinicName && user.clinic_name !== clinicName) {
        user.clinic_name = clinicName;
        changed = true;
      }
      if (clinicLogo !== undefined && user.clinic_logo !== clinicLogo) {
        user.clinic_logo = clinicLogo;
        changed = true;
      }
      if (changed) {
        Auth.setUser(user);
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

    // Theme toggle button
    const themeToggleBtn = document.getElementById("header-theme-toggle");
    if (themeToggleBtn) {
      themeToggleBtn.textContent = ThemeManager.getTheme() === "dark" ? "☀️" : "🌙";
      themeToggleBtn.addEventListener("click", () => {
        const next = ThemeManager.toggle();
        themeToggleBtn.textContent = next === "dark" ? "☀️" : "🌙";
      });
    }

    // Doctor Change Password Nav button
    document.getElementById("doctor-change-password-nav-btn")?.addEventListener("click", () => {
      showChangePasswordModal(false);
    });
  }

  handleHashChange() {
    const rawHash = window.location.hash.replace(/^#\/?/, "").toLowerCase();
    const isDoc = Auth.isDoctor();

    let viewKey;
    if (isDoc) {
      // Doctor role: allow doctor routes and settings
      const normalized = (rawHash === "doctor-settings" || rawHash === "settings") ? "settings" : rawHash;
      if (DOCTOR_ALLOWED_ROUTES.has(rawHash) || DOCTOR_ALLOWED_ROUTES.has(normalized)) {
        viewKey = normalized;
      } else {
        viewKey = "doctor-dashboard";
        if (window.location.hash !== "#doctor-dashboard") {
          window.location.hash = "#doctor-dashboard";
          return;
        }
      }
    } else {
      // Admin role: default to dashboard; redirect out of doctor-only routes
      if (DOCTOR_ONLY_ROUTES.has(rawHash)) {
        viewKey = "dashboard";
        window.location.hash = "#dashboard";
        return;
      } else {
        viewKey = VIEWS[rawHash] ? rawHash : "dashboard";
      }
    }

    this.loadView(viewKey);
  }

  async loadView(viewKey) {
    if (this.currentView === viewKey && this.initializedViews.has(viewKey)) return;
    this.currentView = viewKey;

    const config = VIEWS[viewKey];
    if (!config) return;

    // Update active nav links
    document.querySelectorAll(".nav-item").forEach((el) => {
      const dataView = el.getAttribute("data-view");
      if (dataView === viewKey || (viewKey === "settings" && dataView === "doctor-settings") || (viewKey === "doctor-settings" && dataView === "settings")) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    });

    // Update Header titles
    const headingEl = document.getElementById("view-heading");
    const subheadingEl = document.getElementById("view-subheading");
    if (headingEl) {
      headingEl.textContent = (viewKey === "settings" && Auth.isDoctor()) ? "Doctor Settings" : config.title;
    }
    if (subheadingEl) {
      subheadingEl.textContent = (viewKey === "settings" && Auth.isDoctor()) ? "Profile, Signature & Clinical Credentials" : config.subtitle;
    }

    // Toggle view containers
    document.querySelectorAll(".view-container").forEach((el) => {
      el.classList.remove("active");
    });

    const targetContainerId = (viewKey === "doctor-settings") ? "view-settings" : `view-${viewKey}`;
    const targetContainer = document.getElementById(targetContainerId);
    if (targetContainer) {
      targetContainer.classList.add("active");
    }

    // Close mobile sidebar if open
    document.getElementById("app-sidebar")?.classList.remove("open");
    document.getElementById("sidebar-backdrop")?.classList.remove("active");

    // Initialize View Module safely
    if (config.module) {
      try {
        if (!this.initializedViews.has(viewKey) || typeof config.module.loadData !== "function") {
          await config.module.init();
          this.initializedViews.add(viewKey);
        } else if (typeof config.module.loadData === "function") {
          await config.module.loadData();
        }
      } catch (err) {
        console.error(`Failed to load view '${viewKey}':`, err);
        showToast(`Failed to load ${config.title}: ${err.message}`, "error");
      }
    }
  }
}

function bootstrap() {
  const app = new App();
  window.App = app;
  app.init();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", bootstrap);
} else {
  bootstrap();
}

