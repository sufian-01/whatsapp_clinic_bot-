/**
 * Admin Doctor Accounts View Module.
 */

import { API } from "../api.js";
import { escapeHtml, formatDate, renderBadge, showToast, Modal, renderTableSkeletons } from "../utils.js";

export const DoctorAccountsView = {
  container: null,

  async init() {
    this.container = document.getElementById("view-doctor-accounts");
    if (!this.container) return;
    await this.render();
  },

  async render() {
    this.container.innerHTML = `
      <div class="view-header" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom: 24px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">Doctor Login Accounts</h2>
          <p style="font-size: 13px; color: var(--text-secondary);">Manage physician portal access, credentials, and activation states</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <button id="admin-create-doc-acc-btn" class="btn btn-primary btn-sm">
            <span>➕</span> Create Doctor Account
          </button>
          <button id="admin-doc-acc-refresh-btn" class="btn btn-secondary btn-sm">
            <span>🔄</span> Refresh
          </button>
        </div>
      </div>

      <!-- Accounts Table -->
      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Username</th>
                <th>Doctor ID</th>
                <th>Physician Name</th>
                <th>Specialization</th>
                <th>Email</th>
                <th>Status</th>
                <th>Password Reset Req</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="admin-doc-acc-tbody">
              ${renderTableSkeletons(9, 4)}
            </tbody>
          </table>
        </div>
      </div>
    `;

    document.getElementById("admin-doc-acc-refresh-btn")?.addEventListener("click", () => this.loadData());
    document.getElementById("admin-create-doc-acc-btn")?.addEventListener("click", () => this.openCreateAccountModal());

    await this.loadData();
  },

  async loadData() {
    const tbody = document.getElementById("admin-doc-acc-tbody");
    if (tbody) {
      tbody.innerHTML = renderTableSkeletons(9, 4);
    }
    try {
      const accounts = await API.getDoctorAccounts();
      this.renderTable(accounts || []);
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="9" class="empty-state" style="color:var(--danger,#ef4444); padding:32px 16px;">
          <div style="font-size:24px; margin-bottom:8px;">⚠️</div>
          <div style="font-weight:600; margin-bottom:6px;">Failed to load doctor accounts</div>
          <div style="font-size:12px; color:var(--text-secondary); margin-bottom:16px;">${escapeHtml(err.message || "Network request failed")}</div>
          <button id="admin-doc-acc-retry-btn" class="btn btn-secondary btn-sm" style="margin:0 auto;">🔄 Retry Loading</button>
        </td></tr>`;
        document.getElementById("admin-doc-acc-retry-btn")?.addEventListener("click", () => this.loadData());
      }
      showToast(err.message || "Failed to load doctor accounts.", "error");
    }
  },

  renderTable(accounts) {
    const tbody = document.getElementById("admin-doc-acc-tbody");
    if (!tbody) return;

    if (!accounts.length) {
      tbody.innerHTML = `<tr><td colspan="9" class="empty-state">No doctor accounts created yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = accounts.map((a) => {
      const isActive = a.status === "Active";

      return `
        <tr>
          <td><strong>${escapeHtml(a.username)}</strong></td>
          <td><code>${escapeHtml(a.doctor_id)}</code></td>
          <td>${escapeHtml(a.doctor_name || "-")}</td>
          <td>${escapeHtml(a.specialization || "-")}</td>
          <td>${escapeHtml(a.email || "-")}</td>
          <td>${renderBadge(a.status)}</td>
          <td>${a.must_change_password ? '<span class="badge badge-warning">Required</span>' : '<span class="badge badge-completed">Completed</span>'}</td>
          <td>${a.last_login ? escapeHtml(formatDate(a.last_login)) : '<span style="color:var(--text-muted);">Never</span>'}</td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-secondary btn-sm admin-toggle-status-btn" data-username="${escapeHtml(a.username)}" data-status="${isActive ? "Inactive" : "Active"}">
                ${isActive ? "Deactivate" : "Activate"}
              </button>
              <button class="btn btn-secondary btn-sm admin-reset-pwd-btn" data-username="${escapeHtml(a.username)}">
                Reset Pwd
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".admin-toggle-status-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.toggleAccountStatus(btn.dataset.username, btn.dataset.status));
    });

    tbody.querySelectorAll(".admin-reset-pwd-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.openResetPasswordModal(btn.dataset.username));
    });
  },

  async openCreateAccountModal() {
    // Fetch active doctors from Doctor Directory to populate dropdown
    let doctors = [];
    try {
      doctors = await API.getDoctors();
    } catch (e) {
      doctors = [];
    }

    const docOptions = doctors.map((d) => `
      <option value="${escapeHtml(d["Doctor ID"])}">${escapeHtml(d["Doctor ID"])} — ${escapeHtml(d["Doctor Name"])} (${escapeHtml(d["Specialization"])})</option>
    `).join("");

    Modal.open({
      title: "Create Doctor Account",
      body: `
        <form id="create-doc-acc-form" style="display:flex; flex-direction:column; gap:16px;">
          <div class="form-group">
            <label class="form-label">Assign to Physician *</label>
            <select id="new-acc-doc-id" class="form-select" required>
              <option value="">Select Doctor from Directory...</option>
              ${docOptions}
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Username *</label>
            <input type="text" id="new-acc-username" class="form-input" placeholder="e.g. dr_arjun" required />
          </div>

          <div class="form-group">
            <label class="form-label">Initial Password *</label>
            <input type="password" id="new-acc-pwd" class="form-input" placeholder="Min 8 chars or 1234 for demo" required />
          </div>

          <div class="form-group">
            <label class="form-label">Notification Email</label>
            <input type="email" id="new-acc-email" class="form-input" placeholder="doctor@clinic.com" />
          </div>

          <div style="font-size:12px; color:var(--text-muted); background:var(--bg-surface-secondary); padding:8px 12px; border-radius:4px;">
            ℹ️ Doctors are required to change their password upon first portal login. Passwords are securely hashed with PBKDF2-HMAC-SHA256.
          </div>

          <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button type="button" class="btn btn-secondary" onclick="document.getElementById('app-modal-close-btn').click()">Cancel</button>
            <button type="submit" class="btn btn-primary">Create Account</button>
          </div>
        </form>
      `,
    });

    document.getElementById("create-doc-acc-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const docId = document.getElementById("new-acc-doc-id").value;
      const username = document.getElementById("new-acc-username").value.trim();
      const pwd = document.getElementById("new-acc-pwd").value;
      const email = document.getElementById("new-acc-email").value.trim();

      try {
        await API.createDoctorAccount({
          doctor_id: docId,
          username,
          password: pwd,
          email,
        });
        showToast("Doctor account created successfully!", "success");
        Modal.close();
        this.loadData();
      } catch (err) {
        showToast(err.message || "Failed to create doctor account.", "error");
      }
    });
  },

  async toggleAccountStatus(username, newStatus) {
    if (!confirm(`Are you sure you want to mark '${username}' as ${newStatus}?`)) return;

    try {
      await API.setDoctorAccountStatus(username, newStatus);
      showToast(`Account status updated to ${newStatus}.`, "success");
      this.loadData();
    } catch (err) {
      showToast(err.message || "Failed to update account status.", "error");
    }
  },

  openResetPasswordModal(username) {
    const newPwd = prompt(`Enter new password for doctor account '${username}':`);
    if (!newPwd || !newPwd.trim()) return;

    API.resetDoctorPassword(username, newPwd.trim())
      .then(() => {
        showToast(`Password reset successfully for ${username}.`, "success");
        this.loadData();
      })
      .catch((err) => {
        showToast(err.message || "Failed to reset password.", "error");
      });
  },
};

