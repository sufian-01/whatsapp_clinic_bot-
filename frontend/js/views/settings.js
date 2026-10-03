/**
 * Settings View Module.
 */

import { API } from "../api.js";
import { Auth } from "../auth.js";
import { escapeHtml, showToast } from "../utils.js";
import { ThemeManager } from "../app.js";

export const SettingsView = {
  container: null,

  async init() {
    this.container = document.getElementById("view-settings");
    if (!this.container) return;
    this.render();
    await this.loadSettings();
  },

  render() {
    this.container.innerHTML = `
      <div style="max-width: 720px;">
        <!-- Admin Profile -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">👤 Administrator Profile</span>
          </div>
          <div class="card-body">
            <div id="settings-profile-container">
              <div style="color:var(--text-muted);">Loading profile information...</div>
            </div>
          </div>
        </div>
        
        <!-- Appearance -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">🎨 Appearance</span>
          </div>
          <div class="card-body">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <strong style="display:block; margin-bottom:4px;">Theme</strong>
                <span style="font-size:13px; color:var(--text-secondary);">Switch between light and dark mode</span>
              </div>
              <div style="display:flex; align-items:center; gap:10px;">
                <span id="theme-label" style="font-size:13.5px; font-weight:500;"></span>
                <button id="settings-theme-toggle" class="btn btn-secondary">Toggle Theme</button>
              </div>
            </div>
          </div>
        </div>

        <!-- System & Clinic Details -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">🏥 System & Clinic Environment</span>
          </div>
          <div class="card-body" style="font-size: 13.5px; line-height: 1.6;">
            <div style="display:flex; flex-direction:column; gap:10px;">
              <div><strong>Backend API Status:</strong> <span id="health-status-badge" class="badge badge-completed">Checking...</span></div>
              <div><strong>Google Sheets Source:</strong> Connected as clinic database</div>
              <div><strong>Telegram Bot Service:</strong> Active webhook listener</div>
              <div><strong>Email Service:</strong> Google Gmail API delivery</div>
              <div><strong>Payment Processing:</strong> Offline UPI QR with manual clinic verification</div>
            </div>
          </div>
        </div>

        <!-- Session Actions -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">🔒 Session & Security</span>
          </div>
          <div class="card-body">
            <p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">
              You are securely logged into the administrative portal. Click below to terminate your session.
            </p>
            <button id="settings-logout-btn" class="btn btn-danger">
              Sign Out of CRM
            </button>
          </div>
        </div>
      </div>
    `;

    document.getElementById("settings-logout-btn")?.addEventListener("click", () => {
      if (confirm("Are you sure you want to sign out?")) {
        Auth.logout();
      }
    });

    const updateThemeLabel = () => {
      const label = document.getElementById("theme-label");
      if (label) {
        label.textContent = ThemeManager.getTheme() === 'dark' ? 'Dark Mode' : 'Light Mode';
      }
    };
    
    updateThemeLabel();
    
    document.getElementById("settings-theme-toggle")?.addEventListener("click", () => {
      ThemeManager.toggle();
      updateThemeLabel();
    });
  },

  async loadSettings() {
    try {
      const me = await API.getMe();
      const profileContainer = document.getElementById("settings-profile-container");
      if (profileContainer) {
        profileContainer.innerHTML = `
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; font-size:13.5px;">
            <div><strong>Username:</strong> ${escapeHtml(me.username)}</div>
            <div><strong>Role:</strong> <span class="badge badge-completed">${escapeHtml(me.role)}</span></div>
            <div><strong>Clinic:</strong> ${escapeHtml(me.clinic_name)}</div>
            <div><strong>Authentication:</strong> Session Token (Bearer / Cookie)</div>
          </div>
        `;
      }

      // Check health
      try {
        const healthRes = await fetch("/health");
        const healthData = await healthRes.json();
        const badge = document.getElementById("health-status-badge");
        if (badge && healthData.status === "ok") {
          badge.textContent = "Operational (Healthy)";
        }
      } catch (e) {
        // ignore
      }
    } catch (err) {
      showToast(err.message || "Failed to load profile", "error");
    }
  },
};
