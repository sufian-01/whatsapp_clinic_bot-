/**
 * Settings View Module: Clinic Branding, Razorpay Gateway, & Doctor Profile/Signature.
 */

import { API } from "../api.js";
import { Auth } from "../auth.js";
import { escapeHtml, showToast } from "../utils.js";
import { ThemeManager } from "../theme.js";

export const SettingsView = {
  container: null,
  currentRole: null,
  currentUser: null,

  async init() {
    this.container = document.getElementById("view-settings");
    if (!this.container) return;
    this.container.innerHTML = `
      <div style="max-width: 780px;">
        <div style="color:var(--text-muted); padding: 20px;">Loading settings & configuration...</div>
      </div>
    `;
    await this.loadSettings();
  },

  async loadData() {
    await this.loadSettings();
  },

  async loadSettings() {
    try {
      const me = await API.getMe();
      this.currentUser = me;
      this.currentRole = (me.role || "").toLowerCase();

      if (this.currentRole === "doctor") {
        await this.renderDoctorSettings(me);
      } else {
        await this.renderAdminSettings(me);
      }
    } catch (err) {
      this.container.innerHTML = `
        <div class="card" style="max-width: 780px;">
          <div class="card-body" style="color: var(--danger, #ef4444);">
            Failed to load settings: ${escapeHtml(err.message || String(err))}
          </div>
        </div>
      `;
      showToast(err.message || "Failed to load settings", "error");
    }
  },

  // -------------------------------------------------------------------------
  // DOCTOR SETTINGS: Profile, Photo, & Digital Signature
  // -------------------------------------------------------------------------
  async renderDoctorSettings(me) {
    let docProfile = {};
    try {
      docProfile = await API.getDoctorProfile();
    } catch (e) {
      console.warn("Could not fetch detailed doctor profile:", e);
      docProfile = {
        name: me.doctor_name || me.username,
        qualification: "",
        registration_no: "",
        phone: "",
        email: "",
        photo: "",
        signature: "",
      };
    }

    const docName = docProfile.name || docProfile["Doctor Name"] || me.doctor_name || me.username;
    const docSpec = docProfile.specialization || docProfile["Specialization"] || "";
    const docQual = docProfile.qualification || docProfile["Qualification"] || "";
    const docReg = docProfile.registration_no || docProfile["Registration No"] || "";
    const docPhone = docProfile.phone || docProfile["Phone"] || "";
    const docEmail = docProfile.email || docProfile["Email"] || "";
    const docBio = docProfile.bio || docProfile["Bio"] || "";
    const docPhoto = docProfile.photo || docProfile["Photo"] || "";
    const docSign = docProfile.signature || docProfile["Signature"] || "";

    this.container.innerHTML = `
      <div style="max-width: 780px; display: flex; flex-direction: column; gap: 20px;">
        
        <!-- Doctor Account Info -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">👨‍⚕️ Doctor Profile & Clinical Settings</span>
          </div>
          <div class="card-body">
            <form id="doc-profile-form" style="display: flex; flex-direction: column; gap: 16px;">
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                  <label class="form-label">Doctor Full Name *</label>
                  <input type="text" id="doc-name-input" class="form-control" value="${escapeHtml(docName)}" required />
                </div>
                <div class="form-group">
                  <label class="form-label">Clinical Specialization</label>
                  <input type="text" id="doc-spec-input" class="form-control" placeholder="e.g. Cardiologist, General Physician" value="${escapeHtml(docSpec)}" />
                </div>
              </div>

              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                  <label class="form-label">Medical Qualifications</label>
                  <input type="text" id="doc-qual-input" class="form-control" placeholder="e.g. MBBS, MD (Cardiology)" value="${escapeHtml(docQual)}" />
                </div>
                <div class="form-group">
                  <label class="form-label">Medical Registration / License No.</label>
                  <input type="text" id="doc-reg-input" class="form-control" placeholder="e.g. MCI-2018-93821" value="${escapeHtml(docReg)}" />
                  <div class="form-text" style="font-size: 11.5px; color: var(--text-muted); margin-top: 4px;">Prints on finalized digital prescription headers.</div>
                </div>
              </div>

              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                  <label class="form-label">Direct Phone</label>
                  <input type="text" id="doc-phone-input" class="form-control" placeholder="e.g. +91 9876543210" value="${escapeHtml(docPhone)}" />
                </div>
                <div class="form-group">
                  <label class="form-label">Official Email</label>
                  <input type="email" id="doc-email-input" class="form-control" placeholder="e.g. doctor@clinic.com" value="${escapeHtml(docEmail)}" />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Professional Bio / About Doctor</label>
                <textarea id="doc-bio-input" class="form-control" rows="3" placeholder="Brief clinical background, special interests, and medical experience...">${escapeHtml(docBio)}</textarea>
                <div class="form-text" style="font-size: 11.5px; color: var(--text-muted); margin-top: 4px;">Visible in Clinic CRM Doctor Directory and patient records.</div>
              </div>

              <div class="form-group">
                <label class="form-label">Doctor Photo (Avatar / ID Photo)</label>
                <div style="display: flex; gap: 12px; align-items: center;">
                  <input type="text" id="doc-photo-input" class="form-control" placeholder="Image URL or upload file below" value="${escapeHtml(docPhoto.startsWith('data:') ? '[Uploaded Image File]' : docPhoto)}" style="flex: 1;" />
                  <label class="btn btn-secondary" style="margin: 0; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;">
                    📷 Upload Photo
                    <input type="file" id="doc-photo-file" accept="image/*" style="display: none;" />
                  </label>
                </div>
                <div id="doc-photo-preview-wrap" style="margin-top: 10px; ${docPhoto ? '' : 'display: none;'}">
                  <img id="doc-photo-preview" src="${docPhoto || ''}" alt="Doctor Photo" style="width: 80px; height: 80px; object-fit: cover; border-radius: 50%; border: 2px solid var(--border-color, #cbd5e1); box-shadow: 0 1px 3px rgba(0,0,0,0.1);" />
                </div>
              </div>

              <!-- Digital Signature Section -->
              <div class="form-group" style="background: var(--bg-surface-secondary, #f8fafc); padding: 16px; border-radius: 8px; border: 1px solid var(--border-light, #e2e8f0);">
                <label class="form-label" style="font-weight: 700; color: var(--primary, #0284c7); margin-bottom: 6px;">
                  ✍️ Digital Signature (Appears on Finalized Prescriptions)
                </label>
                <div style="font-size: 12.5px; color: var(--text-secondary); margin-bottom: 12px;">
                  Draw your digital signature below or upload an image with your signature. This will be automatically embedded onto every official prescription PDF you finalize.
                </div>

                <div style="display: flex; flex-direction: column; gap: 10px;">
                  <div style="border: 2px dashed #94a3b8; border-radius: 6px; background: #ffffff; width: 100%; max-width: 480px; height: 160px; position: relative;">
                    <canvas id="signature-canvas" width="480" height="160" style="display: block; width: 100%; height: 100%; cursor: crosshair; touch-action: none;"></canvas>
                  </div>
                  <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                    <button type="button" id="clear-sig-btn" class="btn btn-secondary btn-sm">Clear Signature Pad</button>
                    <label class="btn btn-secondary btn-sm" style="margin: 0; cursor: pointer;">
                      📁 Upload Signature Image
                      <input type="file" id="doc-sig-file" accept="image/*" style="display: none;" />
                    </label>
                    <span id="sig-status-label" style="font-size: 12px; color: var(--text-muted);">
                      ${docSign ? '✓ Signature loaded' : 'No signature recorded yet'}
                    </span>
                  </div>
                  <input type="hidden" id="doc-sig-input" value="${escapeHtml(docSign)}" />
                  <div id="doc-sig-preview-wrap" style="margin-top: 6px; ${docSign ? '' : 'display: none;'}">
                    <span style="font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 4px;">Current Signature Preview:</span>
                    <img id="doc-sig-preview" src="${docSign || ''}" alt="Digital Signature" style="max-height: 60px; max-width: 240px; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px; background: #fff;" />
                  </div>
                </div>
              </div>

              <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 10px;">
                <button type="submit" id="save-doc-profile-btn" class="btn btn-primary" style="padding: 10px 24px;">
                  Save Settings & Signature
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- Appearance & Session -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">🎨 Appearance & Session</span>
          </div>
          <div class="card-body">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 16px;">
              <div>
                <strong style="display:block; margin-bottom:4px;">Theme</strong>
                <span style="font-size:13px; color:var(--text-secondary);">Switch between light and dark mode</span>
              </div>
              <div style="display:flex; align-items:center; gap:10px;">
                <span id="theme-label" style="font-size:13.5px; font-weight:500;"></span>
                <button id="settings-theme-toggle" class="btn btn-secondary">Toggle Theme</button>
              </div>
            </div>
            <hr style="border: 0; border-top: 1px solid var(--border-light, #e2e8f0); margin: 16px 0;" />
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <strong style="display:block; margin-bottom:4px;">Sign Out</strong>
                <span style="font-size:13px; color:var(--text-secondary);">End active doctor session</span>
              </div>
              <button id="settings-logout-btn" class="btn btn-danger">
                Sign Out
              </button>
            </div>
          </div>
        </div>

      </div>
    `;

    this.bindCommonEvents();
    this.initSignaturePad(docSign);

    // Doctor photo file handler
    const photoFileInput = document.getElementById("doc-photo-file");
    const photoUrlInput = document.getElementById("doc-photo-input");
    const photoPreview = document.getElementById("doc-photo-preview");
    const photoPreviewWrap = document.getElementById("doc-photo-preview-wrap");

    if (photoFileInput) {
      photoFileInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (loadEvt) => {
            const dataUri = loadEvt.target.result;
            photoUrlInput.value = dataUri;
            photoPreview.src = dataUri;
            photoPreviewWrap.style.display = "block";
          };
          reader.readAsDataURL(file);
        }
      };
    }

    // Doctor signature file handler
    const sigFileInput = document.getElementById("doc-sig-file");
    const sigInput = document.getElementById("doc-sig-input");
    const sigPreview = document.getElementById("doc-sig-preview");
    const sigPreviewWrap = document.getElementById("doc-sig-preview-wrap");
    const sigStatusLabel = document.getElementById("sig-status-label");

    if (sigFileInput) {
      sigFileInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (loadEvt) => {
            const dataUri = loadEvt.target.result;
            sigInput.value = dataUri;
            sigPreview.src = dataUri;
            sigPreviewWrap.style.display = "block";
            sigStatusLabel.textContent = "✓ Signature file attached";
            // Also draw onto canvas
            const img = new Image();
            img.onload = () => {
              const canvas = document.getElementById("signature-canvas");
              if (canvas) {
                const ctx = canvas.getContext("2d");
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
              }
            };
            img.src = dataUri;
          };
          reader.readAsDataURL(file);
        }
      };
    }

    // Save profile form submission
    const profileForm = document.getElementById("doc-profile-form");
    if (profileForm) {
      profileForm.onsubmit = async (e) => {
        e.preventDefault();
        const saveBtn = document.getElementById("save-doc-profile-btn");
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";

        const payload = {
          name: document.getElementById("doc-name-input").value.trim(),
          specialization: document.getElementById("doc-spec-input").value.trim() || undefined,
          qualification: document.getElementById("doc-qual-input").value.trim() || undefined,
          registration_no: document.getElementById("doc-reg-input").value.trim() || undefined,
          phone: document.getElementById("doc-phone-input").value.trim() || undefined,
          email: document.getElementById("doc-email-input").value.trim() || undefined,
          bio: document.getElementById("doc-bio-input").value.trim() || undefined,
          photo: photoUrlInput.value.trim() || undefined,
          signature: sigInput.value.trim() || undefined,
        };

        try {
          const res = await API.updateDoctorProfile(payload);
          const updatedName = res?.name || payload.name;
          const nameEl = document.getElementById("header-user-name");
          if (nameEl && updatedName) nameEl.textContent = updatedName;
          const user = Auth.getUser();
          if (user) {
            user.doctor_name = updatedName;
            Auth.setUser(user);
          }
          showToast("Doctor settings & digital signature updated successfully!", "success");
        } catch (err) {
          showToast(`Failed to update settings: ${err.message}`, "error");
        } finally {
          saveBtn.disabled = false;
          saveBtn.textContent = "Save Settings & Signature";
        }
      };
    }
  },

  // -------------------------------------------------------------------------
  // Canvas Signature Pad Setup
  // -------------------------------------------------------------------------
  initSignaturePad(existingSig) {
    const canvas = document.getElementById("signature-canvas");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    ctx.lineWidth = 2.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.strokeStyle = "#0f172a";

    let drawing = false;

    // Load existing signature if present
    if (existingSig && existingSig.startsWith("data:")) {
      const img = new Image();
      img.onload = () => ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      img.src = existingSig;
    }

    const getPos = (evt) => {
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;
      if (evt.touches && evt.touches.length > 0) {
        return {
          x: (evt.touches[0].clientX - rect.left) * scaleX,
          y: (evt.touches[0].clientY - rect.top) * scaleY,
        };
      }
      return {
        x: (evt.clientX - rect.left) * scaleX,
        y: (evt.clientY - rect.top) * scaleY,
      };
    };

    const startDraw = (evt) => {
      evt.preventDefault();
      drawing = true;
      const pos = getPos(evt);
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
    };

    const drawMove = (evt) => {
      if (!drawing) return;
      evt.preventDefault();
      const pos = getPos(evt);
      ctx.lineTo(pos.x, pos.y);
      ctx.stroke();
    };

    const endDraw = (evt) => {
      if (!drawing) return;
      drawing = false;
      const sigData = canvas.toDataURL("image/png");
      const sigInput = document.getElementById("doc-sig-input");
      const sigPreview = document.getElementById("doc-sig-preview");
      const sigPreviewWrap = document.getElementById("doc-sig-preview-wrap");
      const sigStatusLabel = document.getElementById("sig-status-label");

      if (sigInput) sigInput.value = sigData;
      if (sigPreview) sigPreview.src = sigData;
      if (sigPreviewWrap) sigPreviewWrap.style.display = "block";
      if (sigStatusLabel) sigStatusLabel.textContent = "✓ Drawn signature captured";
    };

    canvas.addEventListener("mousedown", startDraw);
    canvas.addEventListener("mousemove", drawMove);
    window.addEventListener("mouseup", endDraw);

    canvas.addEventListener("touchstart", startDraw, { passive: false });
    canvas.addEventListener("touchmove", drawMove, { passive: false });
    window.addEventListener("touchend", endDraw);

    const clearBtn = document.getElementById("clear-sig-btn");
    if (clearBtn) {
      clearBtn.onclick = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const sigInput = document.getElementById("doc-sig-input");
        const sigPreviewWrap = document.getElementById("doc-sig-preview-wrap");
        const sigStatusLabel = document.getElementById("sig-status-label");
        if (sigInput) sigInput.value = "";
        if (sigPreviewWrap) sigPreviewWrap.style.display = "none";
        if (sigStatusLabel) sigStatusLabel.textContent = "Signature cleared";
      };
    }
  },

  // -------------------------------------------------------------------------
  // ADMIN SETTINGS: Clinic Branding, Logo, & Razorpay Gateway Setup
  // -------------------------------------------------------------------------
  async renderAdminSettings(me) {
    let settings = {};
    try {
      settings = await API.getClinicSettings();
    } catch (e) {
      console.warn("Could not fetch clinic settings:", e);
      settings = {
        clinic_name: me.clinic_name || "City Health Clinic",
        support_phone: "",
        clinic_address: "",
        logo: "",
        razorpay_key_id: "",
        razorpay_key_secret: "",
        upi_id: "clinic@upi",
      };
    }

    const clinicLogo = settings.logo || "";

    this.container.innerHTML = `
      <div style="max-width: 780px; display: flex; flex-direction: column; gap: 20px;">
        
        <!-- Administrator Profile -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">👤 Administrator Profile</span>
          </div>
          <div class="card-body">
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; font-size:13.5px;">
              <div><strong>Username:</strong> ${escapeHtml(me.username)}</div>
              <div><strong>Role:</strong> <span class="badge badge-completed">${escapeHtml(me.role)}</span></div>
              <div><strong>Facility:</strong> ${escapeHtml(me.clinic_name || settings.clinic_name)}</div>
              <div><strong>Security:</strong> Session Token (Encrypted)</div>
            </div>
          </div>
        </div>

        <!-- Clinic Branding & Hospital Logo -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">🏥 Facility Profile & Prescription Branding</span>
          </div>
          <div class="card-body">
            <form id="clinic-branding-form" style="display: flex; flex-direction: column; gap: 16px;">
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                <div class="form-group">
                  <label class="form-label">Facility / Clinic Name *</label>
                  <input type="text" id="clinic-name-input" class="form-control" value="${escapeHtml(settings.clinic_name || '')}" required />
                </div>
                <div class="form-group">
                  <label class="form-label">Contact / Support Phone</label>
                  <input type="text" id="clinic-phone-input" class="form-control" placeholder="e.g. +91 6200126662" value="${escapeHtml(settings.support_phone || '')}" />
                </div>
              </div>

              <div class="form-group">
                <label class="form-label">Physical Address</label>
                <input type="text" id="clinic-address-input" class="form-control" placeholder="Street, City, Pin Code" value="${escapeHtml(settings.clinic_address || '')}" />
                <div class="form-text" style="font-size: 11.5px; color: var(--text-muted); margin-top: 4px;">Appears on official patient prescription headers.</div>
              </div>

              <div class="form-group">
                <label class="form-label">Hospital / Clinic Logo</label>
                <div style="display: flex; gap: 12px; align-items: center;">
                  <input type="text" id="clinic-logo-input" class="form-control" placeholder="Logo image URL or upload image file" value="${escapeHtml(clinicLogo.startsWith('data:') ? '[Uploaded Image File]' : clinicLogo)}" style="flex: 1;" />
                  <label class="btn btn-secondary" style="margin: 0; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; white-space: nowrap;">
                    📁 Upload Logo
                    <input type="file" id="clinic-logo-file" accept="image/*" style="display: none;" />
                  </label>
                </div>
                <div class="form-text" style="font-size: 11.5px; color: var(--text-muted); margin-top: 4px;">Embedded automatically at the top header of all patient Prescription PDFs.</div>
                <div id="clinic-logo-preview-wrap" style="margin-top: 10px; ${clinicLogo ? '' : 'display: none;'}">
                  <span style="font-size: 11px; color: var(--text-muted); display: block; margin-bottom: 4px;">Header Logo Preview:</span>
                  <img id="clinic-logo-preview" src="${clinicLogo || ''}" alt="Clinic Logo" style="max-height: 60px; max-width: 180px; object-fit: contain; border-radius: 4px; border: 1px solid #cbd5e1; padding: 4px; background: #fff;" />
                </div>
              </div>

              <!-- Razorpay Online Payment Gateway Setup -->
              <div class="form-group" style="background: var(--bg-surface-secondary, #f8fafc); padding: 18px; border-radius: 8px; border: 1px solid var(--border-light, #e2e8f0); margin-top: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                  <div>
                    <label class="form-label" style="font-weight: 700; color: var(--primary, #0284c7); margin-bottom: 4px;">
                      💳 Razorpay & UPI Online Payment Gateway Setup
                    </label>
                    <div style="font-size: 12.5px; color: var(--text-secondary);">
                      Configure credentials to enable online payments on WhatsApp booking and automatic confirmation.
                    </div>
                  </div>
                  <button type="button" id="fill-test-rzp-btn" class="btn btn-secondary btn-sm" style="font-size: 11.5px; white-space: nowrap;">
                    🧪 Fill Test Credentials
                  </button>
                </div>

                <div style="display: flex; flex-direction: column; gap: 14px;">
                  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div>
                      <label class="form-label" style="font-size: 12px;">Razorpay Key ID</label>
                      <input type="text" id="rzp-key-id" class="form-control" placeholder="e.g. rzp_test_sampleKeyId123" value="${escapeHtml(settings.razorpay_key_id || '')}" />
                    </div>
                    <div>
                      <label class="form-label" style="font-size: 12px;">Razorpay Key Secret</label>
                      <div style="display: flex; gap: 6px;">
                        <input type="password" id="rzp-key-secret" class="form-control" placeholder="${settings.razorpay_key_secret_configured ? '•••••••• (Configured)' : 'e.g. sampleSecret123'}" value="${settings.razorpay_key_secret && !settings.razorpay_key_secret.includes('***') ? escapeHtml(settings.razorpay_key_secret) : ''}" />
                        <button type="button" id="toggle-secret-btn" class="btn btn-secondary btn-sm" title="Toggle visibility">👁️</button>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label class="form-label" style="font-size: 12px;">Default Clinic UPI ID</label>
                    <input type="text" id="rzp-upi-id" class="form-control" placeholder="e.g. clinic@okhdfcbank or clinic@upi" value="${escapeHtml(settings.upi_id || 'clinic@upi')}" />
                    <div class="form-text" style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Used for generating instant UPI deep links on WhatsApp bookings.</div>
                  </div>
                </div>
              </div>

              <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 10px;">
                <button type="submit" id="save-clinic-settings-btn" class="btn btn-primary" style="padding: 10px 24px;">
                  Save Branding & Payment Settings
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- System & Diagnostics -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">🖥️ System & Multi-Tenant Status</span>
          </div>
          <div class="card-body" style="font-size: 13.5px; line-height: 1.6;">
            <div style="display:flex; flex-direction:column; gap:10px;">
              <div><strong>Backend API Status:</strong> <span id="health-status-badge" class="badge badge-completed">Operational (Healthy)</span></div>
              <div><strong>Messaging Architecture:</strong> Meta WhatsApp Cloud API (Multi-Tenant Routing)</div>
              <div><strong>Payment Gateways:</strong> Razorpay Online + Offline Clinic UPI Desk Collections</div>
              <div><strong>Prescription Engine:</strong> High-Resolution ReportLab PDF with Auto-Header Logo & Doctor Signature</div>
            </div>
          </div>
        </div>

        <!-- Appearance & Security -->
        <div class="card">
          <div class="card-header">
            <span class="card-title">🎨 Appearance & Session</span>
          </div>
          <div class="card-body">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 16px;">
              <div>
                <strong style="display:block; margin-bottom:4px;">Theme</strong>
                <span style="font-size:13px; color:var(--text-secondary);">Switch between light and dark mode</span>
              </div>
              <div style="display:flex; align-items:center; gap:10px;">
                <span id="theme-label" style="font-size:13.5px; font-weight:500;"></span>
                <button id="settings-theme-toggle" class="btn btn-secondary">Toggle Theme</button>
              </div>
            </div>
            <hr style="border: 0; border-top: 1px solid var(--border-light, #e2e8f0); margin: 16px 0;" />
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <strong style="display:block; margin-bottom:4px;">Sign Out</strong>
                <span style="font-size:13px; color:var(--text-secondary);">End active administrative session</span>
              </div>
              <button id="settings-logout-btn" class="btn btn-danger">
                Sign Out
              </button>
            </div>
          </div>
        </div>

      </div>
    `;

    this.bindCommonEvents();

    // Logo file reader handler
    const logoFileInput = document.getElementById("clinic-logo-file");
    const logoUrlInput = document.getElementById("clinic-logo-input");
    const logoPreview = document.getElementById("clinic-logo-preview");
    const logoPreviewWrap = document.getElementById("clinic-logo-preview-wrap");

    if (logoFileInput) {
      logoFileInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (loadEvt) => {
            const dataUri = loadEvt.target.result;
            logoUrlInput.value = dataUri;
            logoPreview.src = dataUri;
            logoPreviewWrap.style.display = "block";
          };
          reader.readAsDataURL(file);
        }
      };
    }

    // Fill test credentials button
    const fillTestBtn = document.getElementById("fill-test-rzp-btn");
    if (fillTestBtn) {
      fillTestBtn.onclick = () => {
        document.getElementById("rzp-key-id").value = "rzp_test_sampleKeyId123";
        document.getElementById("rzp-key-secret").value = "sampleSecret123";
        document.getElementById("rzp-upi-id").value = "clinic@upi";
        showToast("Test sandbox Razorpay credentials loaded!", "info");
      };
    }

    // Toggle password visibility for secret
    const toggleSecretBtn = document.getElementById("toggle-secret-btn");
    const secretInput = document.getElementById("rzp-key-secret");
    if (toggleSecretBtn && secretInput) {
      toggleSecretBtn.onclick = () => {
        if (secretInput.type === "password") {
          secretInput.type = "text";
        } else {
          secretInput.type = "password";
        }
      };
    }

    // Save clinic branding form
    const brandingForm = document.getElementById("clinic-branding-form");
    if (brandingForm) {
      brandingForm.onsubmit = async (e) => {
        e.preventDefault();
        const saveBtn = document.getElementById("save-clinic-settings-btn");
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving...";

        const payload = {
          clinic_name: document.getElementById("clinic-name-input").value.trim(),
          support_phone: document.getElementById("clinic-phone-input").value.trim(),
          clinic_address: document.getElementById("clinic-address-input").value.trim(),
          logo: logoUrlInput.value.trim() || undefined,
          razorpay_key_id: document.getElementById("rzp-key-id").value.trim() || undefined,
          razorpay_key_secret: secretInput.value.trim() || undefined,
          upi_id: document.getElementById("rzp-upi-id").value.trim() || undefined,
        };

        try {
          const res = await API.updateClinicSettings(payload);
          const newName = res?.clinic_name || payload.clinic_name;
          const newLogo = res?.logo !== undefined ? res.logo : payload.logo;
          window.App?.updateBranding(newName, newLogo);
          showToast("Clinic branding and Razorpay settings updated successfully!", "success");
        } catch (err) {
          showToast(`Failed to update clinic settings: ${err.message}`, "error");
        } finally {
          saveBtn.disabled = false;
          saveBtn.textContent = "Save Branding & Payment Settings";
        }
      };
    }
  },

  // -------------------------------------------------------------------------
  // Common Utilities
  // -------------------------------------------------------------------------
  bindCommonEvents() {
    document.getElementById("settings-logout-btn")?.addEventListener("click", () => {
      if (confirm("Are you sure you want to sign out?")) {
        Auth.logout();
      }
    });

    const updateThemeLabel = () => {
      const label = document.getElementById("theme-label");
      if (label) {
        label.textContent = ThemeManager.getTheme() === "dark" ? "Dark Mode" : "Light Mode";
      }
    };

    updateThemeLabel();

    document.getElementById("settings-theme-toggle")?.addEventListener("click", () => {
      ThemeManager.toggle();
      updateThemeLabel();
    });
  },
};
