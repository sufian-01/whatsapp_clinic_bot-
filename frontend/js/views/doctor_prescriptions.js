/**
 * Doctor Prescriptions View & Clinical Prescription Editor Module.
 * Provides a dedicated, professional medical prescription pad experience
 * with rich formatting, dynamic medications, vitals, print/PDF/email workflows,
 * and cross-doctor isolation safeguards.
 */

import { API } from "../api.js";
import { debounce, escapeHtml, formatDate, formatTime, renderBadge, showToast, Modal } from "../utils.js";

export const DoctorPrescriptionsView = {
  container: null,
  mode: "list", // "list" | "editor"
  prescriptions: [],
  currentRx: null,
  doctorProfile: null,
  isDirty: false,
  lastSavedText: "",
  patientHistory: [],
  _abortController: null,

  async init() {
    this.container = document.getElementById("view-doctor-prescriptions");
    if (!this.container) return;

    // Load doctor profile once
    try {
      this.doctorProfile = await API.getDoctorProfile();
    } catch (_) {
      this.doctorProfile = { doctor_name: "Doctor", Specialization: "General Physician" };
    }

    // Attach unsaved changes protection
    window.removeEventListener("beforeunload", this._beforeUnloadHandler);
    this._beforeUnloadHandler = (e) => {
      if (this.mode === "editor" && this.isDirty) {
        e.preventDefault();
        e.returnValue = "You have unsaved prescription changes. Are you sure you want to leave?";
        return e.returnValue;
      }
    };
    window.addEventListener("beforeunload", this._beforeUnloadHandler);

    if (this.mode === "editor" && this.currentRx) {
      await this.renderEditor();
    } else {
      this.mode = "list";
      await this.renderList();
    }
  },

  renderTableSkeletons(cols = 8, rows = 4) {
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

  // =========================================================================
  // LIST VIEW
  // =========================================================================

  async renderList() {
    this.mode = "list";
    this.isDirty = false;

    this.container.innerHTML = `
      <div class="view-header" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom: 24px;">
        <div>
          <h2 style="font-size: 20px; font-weight: 700; color: var(--text-main); margin-bottom: 4px;">Prescription Management</h2>
          <p style="font-size: 13px; color: var(--text-secondary);">Author, review, finalize, print, and dispatch digital medical prescriptions</p>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <button id="doc-new-rx-btn" class="btn btn-primary btn-sm">
            <span>➕</span> New Prescription
          </button>
          <button id="doc-rx-refresh-btn" class="btn btn-secondary btn-sm">
            <span>🔄</span> Refresh
          </button>
        </div>
      </div>

      <!-- Filters Toolbar -->
      <div class="filter-bar" style="display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:16px;">
        <input type="text" id="doc-rx-search" class="form-input" placeholder="Search patient, diagnosis, Rx ID, token..." style="max-width:320px;" />
        <select id="doc-rx-status-filter" class="form-select" style="max-width:160px;">
          <option value="">All Statuses</option>
          <option value="draft">Drafts Only</option>
          <option value="finalized">Finalized</option>
          <option value="amended">Amended</option>
        </select>
        <button id="doc-rx-reset-filter" class="btn btn-secondary btn-sm">Reset</button>
      </div>

      <!-- Prescriptions Table Card -->
      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Rx ID</th>
                <th>Date</th>
                <th>Token</th>
                <th>Patient Details</th>
                <th>Clinical Diagnosis</th>
                <th>Status</th>
                <th>Version</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="doc-rx-tbody">
              ${this.renderTableSkeletons(8, 4)}
            </tbody>
          </table>
        </div>
      </div>
    `;

    document.getElementById("doc-rx-refresh-btn")?.addEventListener("click", () => this.loadData());
    document.getElementById("doc-rx-search")?.addEventListener("input", debounce(() => this.loadData(), 250));
    document.getElementById("doc-rx-status-filter")?.addEventListener("change", () => this.loadData());
    document.getElementById("doc-rx-reset-filter")?.addEventListener("click", () => {
      const q = document.getElementById("doc-rx-search");
      const st = document.getElementById("doc-rx-status-filter");
      if (q) q.value = "";
      if (st) st.value = "";
      this.loadData();
    });

    document.getElementById("doc-new-rx-btn")?.addEventListener("click", () => {
      this.openEditor(null);
    });

    await this.loadData();
  },

  async loadData() {
    if (this._abortController) {
      this._abortController.abort();
    }
    this._abortController = new AbortController();

    const search = document.getElementById("doc-rx-search")?.value.trim() || "";
    const statusVal = document.getElementById("doc-rx-status-filter")?.value || "";

    const tbody = document.getElementById("doc-rx-tbody");
    if (tbody) {
      tbody.innerHTML = this.renderTableSkeletons(8, 4);
    }

    try {
      const list = await API.getDoctorPrescriptions({
        search,
        status: statusVal,
      }, { signal: this._abortController.signal });
      this.prescriptions = Array.isArray(list) ? list : (list.prescriptions || []);
      this.renderTable(this.prescriptions);
    } catch (err) {
      if (err.name === "AbortError") return;
      console.error("Doctor prescriptions error:", err);
      showToast(err.message || "Failed to load prescriptions.", "error");
      if (tbody) {
        tbody.innerHTML = `
          <tr>
            <td colspan="8" style="text-align:center; padding: 28px; color: var(--danger-text);">
              <div style="font-weight: 600; margin-bottom: 6px;">⚠️ Unable to load prescriptions: ${escapeHtml(err.message || "Error")}</div>
              <button id="doc-rx-retry-btn" class="btn btn-secondary btn-sm" style="margin-top: 6px;">🔄 Retry Loading</button>
            </td>
          </tr>
        `;
        document.getElementById("doc-rx-retry-btn")?.addEventListener("click", () => this.loadData());
      }
    }
  },

  renderTable(rxs) {
    const tbody = document.getElementById("doc-rx-tbody");
    if (!tbody) return;

    if (!rxs.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No prescriptions found. Click "+ New Prescription" or visit "My Appointments" to prescribe.</td></tr>`;
      return;
    }

    tbody.innerHTML = rxs.map((r) => {
      const isFinalized = r.status === "finalized" || r.status === "amended";
      let statusBadge = `<span class="badge badge-pending">Draft</span>`;
      if (r.status === "finalized") statusBadge = `<span class="badge badge-completed">Finalized</span>`;
      if (r.status === "amended") statusBadge = `<span class="badge badge-info">Amended</span>`;

      return `
        <tr>
          <td><code style="font-weight:700;">${escapeHtml(r.prescription_id)}</code></td>
          <td>${escapeHtml(formatDate(r.date))}</td>
          <td><code>${escapeHtml(r.appointment_id)}</code></td>
          <td>
            <strong>${escapeHtml(r.patient_name)}</strong>
            ${r.patient_id ? `<br/><small style="color:var(--text-muted);">ID: ${escapeHtml(r.patient_id)}</small>` : ""}
          </td>
          <td>${escapeHtml(r.diagnosis || "Clinical Evaluation")}</td>
          <td>${statusBadge}</td>
          <td><span class="badge badge-info">v${r.version || 1}</span></td>
          <td>
            <div style="display:flex; gap:6px; flex-wrap:wrap;">
              <button class="btn btn-secondary btn-sm doc-open-rx-btn" data-id="${escapeHtml(r.prescription_id)}">
                ${isFinalized ? "👁️ View / Print" : "✏️ Edit Draft"}
              </button>
              ${isFinalized ? `
                <a href="${API.getDoctorPrescriptionPdfUrl(r.prescription_id)}" target="_blank" class="btn btn-secondary btn-sm" title="Download Official PDF">
                  📄 PDF
                </a>
                <button class="btn btn-primary btn-sm doc-share-rx-btn" data-id="${escapeHtml(r.prescription_id)}" title="Share Prescription">
                  ✉️ Share
                </button>
              ` : ""}
            </div>
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll(".doc-open-rx-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const rx = await API.getDoctorPrescription(btn.dataset.id);
          this.openEditor(rx);
        } catch (err) {
          showToast(err.message || "Failed to load prescription.", "error");
        }
      });
    });

    tbody.querySelectorAll(".doc-share-rx-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.openShareModal(btn.dataset.id));
    });
  },

  // =========================================================================
  // PRESCRIPTION EDITOR (MEDICAL PAD)
  // =========================================================================

  async openEditor(rx = null) {
    this.currentRx = rx;
    this.mode = "editor";
    this.isDirty = false;
    this.lastSavedText = rx ? `Last saved: ${formatTime(rx.updated_at || rx.created_at)}` : "";

    // Load past patient history if patient_id is available
    this.patientHistory = [];
    if (rx && rx.patient_id) {
      try {
        const past = await API.getDoctorPrescriptions({ patient_id: rx.patient_id });
        const list = Array.isArray(past) ? past : (past.prescriptions || []);
        this.patientHistory = list.filter((p) => p.prescription_id !== rx.prescription_id);
      } catch (_) {}
    }

    await this.renderEditor();
  },

  async openEditorForAppointment(appt) {
    // If appointment already has prescription, load it
    if (appt.has_prescription && appt.prescription_id) {
      try {
        const rx = await API.getDoctorPrescription(appt.prescription_id);
        this.openEditor(rx);
        return;
      } catch (_) {}
    }

    // Otherwise create draft prefilled with appointment demographics
    const today = new Date().toISOString().split("T")[0];
    const draft = {
      prescription_id: "",
      appointment_id: appt.token_no || appt.appointment_id || "",
      patient_id: appt.patient_id || "",
      patient_name: appt.patient_name || "",
      patient_phone: appt.phone || "",
      patient_email: appt.email || "",
      patient_age: appt.age || "",
      patient_gender: appt.gender || "",
      date: appt.date || today,
      chief_complaints: "",
      symptoms: "",
      diagnosis: "",
      vitals: { bp: "", pulse: "", temp: "", weight: "", spo2: "" },
      clinical_notes: "",
      medicines: [{ name: "", strength: "", dosage: "", frequency: "", duration: "", instructions: "" }],
      tests_advised: "",
      advice: "",
      follow_up_date: "",
      status: "draft",
      version: 1,
    };

    this.openEditor(draft);
  },

  async renderEditor() {
    const rx = this.currentRx || {};
    const isNew = !rx.prescription_id;
    const isFinalized = rx.status === "finalized" || rx.status === "amended";
    const today = new Date().toISOString().split("T")[0];

    const doc = this.doctorProfile || {};
    const docName = doc.doctor_name || doc["Doctor Name"] || "Doctor";
    const docSpec = doc.Specialization || doc.specialization || "General Physician";
    const docQual = doc.Qualification || doc.qualification || rx.doctor_qualification || "MBBS";
    const docReg = doc["Registration Number"] || doc.registration_number || doc.reg_no || rx.doctor_reg_no || "REG-MED-2024";

    let medicines = (rx.medicines && rx.medicines.length)
      ? JSON.parse(JSON.stringify(rx.medicines))
      : [{ name: "", strength: "", dosage: "", frequency: "", duration: "", instructions: "" }];

    const vitals = rx.vitals || {};

    this.container.innerHTML = `
      <!-- Editor Action Bar -->
      <div class="rx-action-bar no-print" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:20px; background:var(--bg-surface); padding:12px 18px; border-radius:var(--radius-lg); border:1px solid var(--border-light); box-shadow:var(--shadow-sm);">
        <div style="display:flex; align-items:center; gap:12px;">
          <button id="rx-back-btn" class="btn btn-secondary btn-sm" title="Back to prescription list">
            ← Back to List
          </button>
          <div>
            <span style="font-weight:700; font-size:15px; color:var(--text-main);">
              ${isNew ? "New Medical Prescription" : `Prescription ${escapeHtml(rx.prescription_id)}`}
            </span>
            <span class="badge ${isFinalized ? 'badge-completed' : 'badge-pending'}" style="margin-left:6px;">
              ${rx.status ? rx.status.toUpperCase() : "DRAFT"} (v${rx.version || 1})
            </span>
          </div>
          <span id="rx-saved-indicator" style="font-size:12px; color:var(--text-muted); margin-left:6px;">
            ${escapeHtml(this.lastSavedText)}
          </span>
        </div>

        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <button id="rx-print-btn" class="btn btn-secondary btn-sm" title="Print prescription pad">
            🖨️ Print
          </button>

          ${isFinalized ? `
            <a href="${API.getDoctorPrescriptionPdfUrl(rx.prescription_id)}" target="_blank" class="btn btn-secondary btn-sm" title="Download official PDF">
              📄 Download PDF
            </a>
            <button id="rx-share-btn" class="btn btn-primary btn-sm" title="Share via Email">
              ✉️ Share Prescription
            </button>
            <button id="rx-amend-btn" class="btn btn-warning btn-sm" title="Create audited new version">
              ✏️ Amend
            </button>
          ` : `
            <button id="rx-save-draft-btn" class="btn btn-secondary btn-sm" title="Save draft without finalizing">
              💾 Save Draft
            </button>
            <button id="rx-finalize-btn" class="btn btn-primary btn-sm" title="Lock and finalize prescription">
              ✅ Finalize Prescription
            </button>
          `}
        </div>
      </div>

      <!-- Main Medical Prescription Pad Document -->
      <div id="prescription-pad" class="prescription-pad" style="background:#ffffff; color:#0f172a; border-radius:8px; border:1px solid #cbd5e1; box-shadow:0 4px 16px rgba(0,0,0,0.06); max-width:880px; margin:0 auto 40px auto; padding:36px; font-family:'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;">
        
        <!-- Pad Header: Clinic & Doctor Details -->
        <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom:2px solid #0284c7; padding-bottom:16px; margin-bottom:20px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px;">
              <span style="font-size:26px;">🏥</span>
              <div>
                <h1 style="font-size:22px; font-weight:800; color:#0369a1; margin:0; line-height:1.2;">XYZ CLINIC & HEALTHCARE</h1>
                <p style="font-size:12px; color:#475569; margin:2px 0 0 0;">Multi-Specialty Clinical Center & Digital Care</p>
              </div>
            </div>
            <div style="font-size:11.5px; color:#64748b; margin-top:6px; line-height:1.4;">
              123 Health Avenue, Medical Enclave • Phone: +91 6200126662<br/>
              Emergency Helpline & Appointments: contact@xyzclinic.com
            </div>
          </div>

          <!-- Doctor Credentials -->
          <div style="text-align:right; display:flex; flex-direction:column; align-items:flex-end;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
              <div style="width:40px; height:40px; border-radius:50%; background:#e0f2fe; color:#0369a1; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:16px; border:1px solid #bae6fd;">
                ${escapeHtml(docName.replace('Dr.', '').trim().charAt(0) || 'D')}
              </div>
              <div style="text-align:right;">
                <h3 style="font-size:16px; font-weight:700; color:#0f172a; margin:0;">
                  ${docName.startsWith('Dr.') ? escapeHtml(docName) : `Dr. ${escapeHtml(docName)}`}
                </h3>
                <span style="font-size:12px; color:#0284c7; font-weight:600;">${escapeHtml(docSpec)}</span>
              </div>
            </div>
            <div style="font-size:11px; color:#475569; line-height:1.3;">
              <strong>Qual:</strong> ${escapeHtml(docQual)}<br/>
              <strong>Reg No:</strong> <code style="font-family:monospace; color:#0369a1;">${escapeHtml(docReg)}</code>
            </div>
          </div>
        </div>

        <!-- Patient Demographics Strip -->
        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:12px 16px; margin-bottom:20px; font-size:12.5px;">
          <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:10px;">
            <div>
              <span style="color:#64748b;">Patient Name:</span>
              <input type="text" id="rx-pt-name" class="rx-inline-input" style="font-weight:700; width:60%;" value="${escapeHtml(rx.patient_name || "")}" placeholder="Patient Name *" ${isFinalized ? 'disabled' : ''} />
            </div>
            <div>
              <span style="color:#64748b;">Patient ID:</span>
              <input type="text" id="rx-pt-id" class="rx-inline-input" style="font-family:monospace; width:55%;" value="${escapeHtml(rx.patient_id || "")}" placeholder="P-ID *" ${isFinalized ? 'disabled' : ''} />
            </div>
            <div>
              <span style="color:#64748b;">Token / Appt:</span>
              <input type="text" id="rx-appt-id" class="rx-inline-input" style="font-family:monospace; width:55%;" value="${escapeHtml(rx.appointment_id || "")}" placeholder="Token *" ${isFinalized ? 'disabled' : ''} />
            </div>
            <div>
              <span style="color:#64748b;">Age / Gender:</span>
              <input type="text" id="rx-pt-age" class="rx-inline-input" style="width:25%;" value="${escapeHtml(rx.patient_age || "")}" placeholder="Age" ${isFinalized ? 'disabled' : ''} />
              /
              <input type="text" id="rx-pt-gender" class="rx-inline-input" style="width:30%;" value="${escapeHtml(rx.patient_gender || "")}" placeholder="Gender" ${isFinalized ? 'disabled' : ''} />
            </div>
            <div>
              <span style="color:#64748b;">Phone:</span>
              <input type="text" id="rx-pt-phone" class="rx-inline-input" style="width:65%;" value="${escapeHtml(rx.patient_phone || "")}" placeholder="Contact Phone" ${isFinalized ? 'disabled' : ''} />
            </div>
            <div>
              <span style="color:#64748b;">Date:</span>
              <input type="date" id="rx-date" class="rx-inline-input" style="width:60%;" value="${rx.date || today}" ${isFinalized ? 'disabled' : ''} />
            </div>
            <div style="grid-column: 1 / -1;">
              <span style="color:#64748b;">Email Address:</span>
              <input type="email" id="rx-pt-email" class="rx-inline-input" style="width:50%;" value="${escapeHtml(rx.patient_email || "")}" placeholder="patient@example.com (used for PDF delivery)" ${isFinalized ? 'disabled' : ''} />
            </div>
          </div>
        </div>

        <!-- Prior Patient Prescriptions Accordion (if any) -->
        ${this.patientHistory.length > 0 ? `
          <div class="no-print" style="margin-bottom:16px; border:1px dashed #cbd5e1; border-radius:6px; padding:10px 14px; background:#f1f5f9;">
            <div style="display:flex; justify-content:space-between; align-items:center; cursor:pointer;" onclick="const el=document.getElementById('rx-history-box'); el.style.display=el.style.display==='none'?'block':'none';">
              <span style="font-size:12.5px; font-weight:600; color:#0369a1;">
                📁 Patient Prior Prescription History (${this.patientHistory.length} previous visits)
              </span>
              <span style="font-size:12px; color:#64748b;">Click to view ▾</span>
            </div>
            <div id="rx-history-box" style="display:none; margin-top:10px; font-size:12px;">
              ${this.patientHistory.map((h) => `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-top:1px solid #e2e8f0;">
                  <span><strong>${formatDate(h.date)}</strong> — ${escapeHtml(h.diagnosis || 'Clinical visit')} (<code>${escapeHtml(h.prescription_id)}</code>)</span>
                  <button type="button" class="btn btn-secondary btn-sm rx-history-view-btn" data-id="${escapeHtml(h.prescription_id)}" style="font-size:11px; padding:2px 8px;">View</button>
                </div>
              `).join("")}
            </div>
          </div>
        ` : ''}

        <!-- Clinical Consultation Section -->
        <div style="margin-bottom:18px;">
          <!-- Vitals Strip -->
          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:10px 14px; margin-bottom:14px;">
            <span style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:#64748b; display:block; margin-bottom:6px;">
              Patient Vitals
            </span>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap:10px; font-size:12px;">
              <div>
                <label style="color:#64748b; font-size:11px;">BP (mmHg):</label>
                <input type="text" id="rx-vital-bp" class="form-input rx-compact-input" placeholder="120/80" value="${escapeHtml(vitals.bp || '')}" ${isFinalized ? 'disabled' : ''} />
              </div>
              <div>
                <label style="color:#64748b; font-size:11px;">Pulse (bpm):</label>
                <input type="text" id="rx-vital-pulse" class="form-input rx-compact-input" placeholder="72" value="${escapeHtml(vitals.pulse || '')}" ${isFinalized ? 'disabled' : ''} />
              </div>
              <div>
                <label style="color:#64748b; font-size:11px;">Temp (°F):</label>
                <input type="text" id="rx-vital-temp" class="form-input rx-compact-input" placeholder="98.6" value="${escapeHtml(vitals.temp || '')}" ${isFinalized ? 'disabled' : ''} />
              </div>
              <div>
                <label style="color:#64748b; font-size:11px;">Weight (kg):</label>
                <input type="text" id="rx-vital-weight" class="form-input rx-compact-input" placeholder="68" value="${escapeHtml(vitals.weight || '')}" ${isFinalized ? 'disabled' : ''} />
              </div>
              <div>
                <label style="color:#64748b; font-size:11px;">SpO2 (%):</label>
                <input type="text" id="rx-vital-spo2" class="form-input rx-compact-input" placeholder="99" value="${escapeHtml(vitals.spo2 || '')}" ${isFinalized ? 'disabled' : ''} />
              </div>
            </div>
          </div>

          <!-- Complaints, Symptoms & Diagnosis -->
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:12px;">
            <div class="form-group" style="margin-bottom:0;">
              <label class="form-label" style="font-size:12px; font-weight:600; color:#334155;">Chief Complaints</label>
              <textarea id="rx-complaints" class="form-input" rows="2" style="font-size:12.5px; resize:vertical;" placeholder="e.g. Fever, persistent cough for 3 days" ${isFinalized ? 'disabled' : ''}>${escapeHtml(rx.chief_complaints || '')}</textarea>
            </div>
            <div class="form-group" style="margin-bottom:0;">
              <label class="form-label" style="font-size:12px; font-weight:600; color:#334155;">Clinical Symptoms & Findings</label>
              <textarea id="rx-symptoms" class="form-input" rows="2" style="font-size:12.5px; resize:vertical;" placeholder="e.g. Throbbing frontal headache, mild congestion" ${isFinalized ? 'disabled' : ''}>${escapeHtml(rx.symptoms || '')}</textarea>
            </div>
          </div>

          <div class="form-group" style="margin-bottom:14px;">
            <label class="form-label" style="font-size:12px; font-weight:700; color:#0369a1;">Clinical Diagnosis *</label>
            <input type="text" id="rx-diagnosis" class="form-input" style="font-weight:600; font-size:13px; border-color:#93c5fd;" placeholder="e.g. Acute Viral Upper Respiratory Infection" value="${escapeHtml(rx.diagnosis || '')}" required ${isFinalized ? 'disabled' : ''} />
          </div>

          <!-- Clinical Notes with Word-like Rich Text Toolbar -->
          <div style="margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <label class="form-label" style="font-size:12px; font-weight:600; color:#334155; margin:0;">
                Clinical Notes & Examination Details
              </label>
              <!-- Rich Text Toolbar -->
              ${!isFinalized ? `
                <div class="rx-editor-toolbar no-print" style="display:flex; gap:3px; background:#f1f5f9; padding:2px 6px; border-radius:4px; border:1px solid #cbd5e1;">
                  <button type="button" class="rx-format-btn" data-cmd="bold" title="Bold"><b>B</b></button>
                  <button type="button" class="rx-format-btn" data-cmd="italic" title="Italic"><i>I</i></button>
                  <button type="button" class="rx-format-btn" data-cmd="underline" title="Underline"><u>U</u></button>
                  <span style="border-left:1px solid #cbd5e1; margin:0 2px;"></span>
                  <button type="button" class="rx-format-btn" data-cmd="insertUnorderedList" title="Bulleted List">• List</button>
                  <button type="button" class="rx-format-btn" data-cmd="insertOrderedList" title="Numbered List">1. List</button>
                  <span style="border-left:1px solid #cbd5e1; margin:0 2px;"></span>
                  <button type="button" class="rx-format-btn" data-cmd="undo" title="Undo">↶</button>
                  <button type="button" class="rx-format-btn" data-cmd="redo" title="Redo">↷</button>
                  <button type="button" class="rx-format-btn" data-cmd="removeFormat" title="Clear Formatting">⌫ Clear</button>
                </div>
              ` : ''}
            </div>
            <div id="rx-notes-editor" contenteditable="${!isFinalized}" class="rx-rich-editor" style="min-height:75px; max-height:160px; overflow-y:auto; border:1px solid #cbd5e1; border-radius:6px; padding:10px; font-size:12.5px; line-height:1.5; background:${isFinalized ? '#f8fafc' : '#ffffff'}; outline:none;">
              ${rx.clinical_notes || '<p style="color:#94a3b8; margin:0;">Enter detailed clinical examination observations, findings, and medical notes...</p>'}
            </div>
          </div>
        </div>

        <!-- Dynamic Medications Table (Rx) -->
        <div style="margin-bottom:20px;">
          <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1.5px solid #0284c7; padding-bottom:6px; margin-bottom:8px;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="font-size:22px; font-weight:800; font-family:serif; color:#0369a1;">℞</span>
              <h3 style="font-size:14px; font-weight:700; color:#0f172a; margin:0; text-transform:uppercase; letter-spacing:0.04em;">Medications Advised</h3>
            </div>
            ${!isFinalized ? `
              <button type="button" id="rx-add-med-row" class="btn btn-secondary btn-sm no-print" style="font-size:12px; padding:3px 10px;">
                <span>➕</span> Add Medicine
              </button>
            ` : ''}
          </div>

          <div style="overflow-x:auto;">
            <table class="rx-table" style="width:100%; border-collapse:collapse; font-size:12px; text-align:left;">
              <thead>
                <tr style="background:#f1f5f9; border-bottom:1px solid #cbd5e1; color:#475569;">
                  <th style="padding:8px 6px; width:28%;">Medicine Name *</th>
                  <th style="padding:8px 6px; width:12%;">Strength</th>
                  <th style="padding:8px 6px; width:14%;">Dosage *</th>
                  <th style="padding:8px 6px; width:14%;">Frequency *</th>
                  <th style="padding:8px 6px; width:12%;">Duration *</th>
                  <th style="padding:8px 6px; width:16%;">Special Instructions</th>
                  <th style="padding:8px 6px; width:4%; text-align:center;" class="no-print"></th>
                </tr>
              </thead>
              <tbody id="rx-meds-tbody">
                ${medicines.map((m, idx) => this.renderMedRowHtml(m, idx, isFinalized)).join("")}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Investigations, Advice & Follow-Up -->
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:24px;">
          <div>
            <label class="form-label" style="font-size:12px; font-weight:600; color:#334155;">Diagnostic Tests Advised</label>
            <textarea id="rx-tests" class="form-input" rows="2" style="font-size:12px;" placeholder="e.g. Complete Blood Count (CBC), Serum Creatinine" ${isFinalized ? 'disabled' : ''}>${escapeHtml(rx.tests_advised || '')}</textarea>
          </div>
          <div>
            <label class="form-label" style="font-size:12px; font-weight:600; color:#334155;">General Advice & Lifestyle Guidelines</label>
            <textarea id="rx-advice" class="form-input" rows="2" style="font-size:12px;" placeholder="e.g. Adequate hydration, low-sodium diet, avoid exertion" ${isFinalized ? 'disabled' : ''}>${escapeHtml(rx.advice || '')}</textarea>
          </div>
          <div style="grid-column:1 / -1; display:flex; align-items:center; gap:12px;">
            <label class="form-label" style="font-size:12px; font-weight:600; color:#334155; margin:0;">Recommended Follow-Up Date:</label>
            <input type="date" id="rx-follow-up" class="form-input" style="max-width:200px; font-size:12.5px;" value="${rx.follow_up_date || ''}" ${isFinalized ? 'disabled' : ''} />
          </div>
        </div>

        <!-- Doctor Signature Footer -->
        <div style="display:flex; justify-content:space-between; align-items:flex-end; border-top:1px solid #cbd5e1; padding-top:20px; margin-top:20px;">
          <div style="font-size:11px; color:#64748b; line-height:1.4;">
            <em>This digital prescription is generated and digitally verified by the authorized attending physician.<br/>
            Valid for dispensing across certified pharmacies.</em>
          </div>
          <div style="text-align:center; min-width:180px;">
            <div style="font-family:'Brush Script MT', cursive, sans-serif; font-size:22px; color:#0369a1; border-bottom:1px solid #0f172a; padding-bottom:4px; margin-bottom:4px;">
              ${escapeHtml(docName)}
            </div>
            <div style="font-size:11.5px; font-weight:700; color:#0f172a;">${escapeHtml(docName)}</div>
            <div style="font-size:10.5px; color:#64748b;">${escapeHtml(docSpec)} • Reg: ${escapeHtml(docReg)}</div>
          </div>
        </div>

        <!-- Version Audit Trail (if amended) -->
        ${(rx.version_history && rx.version_history.length > 0) ? `
          <div class="no-print" style="margin-top:24px; border-top:1px dashed #cbd5e1; padding-top:14px; font-size:11.5px; color:#475569;">
            <strong style="color:#0f172a;">Audit Version Trail:</strong>
            <ul style="padding-left:18px; margin-top:4px;">
              ${rx.version_history.map((vh) => `
                <li>v${vh.version} (Amended by ${escapeHtml(vh.amended_by)} on ${formatDate(vh.amended_at)}): <em>"${escapeHtml(vh.amendment_reason)}"</em></li>
              `).join("")}
            </ul>
          </div>
        ` : ''}

      </div>
    `;

    this.bindEditorEvents(isFinalized);
  },

  renderMedRowHtml(m, idx, isFinalized) {
    return `
      <tr class="rx-med-row" data-idx="${idx}" style="border-bottom:1px solid #e2e8f0;">
        <td style="padding:6px;">
          <input type="text" class="form-input rx-compact-input med-name" value="${escapeHtml(m.name || "")}" placeholder="e.g. Paracetamol" required ${isFinalized ? 'disabled' : ''} />
        </td>
        <td style="padding:6px;">
          <input type="text" class="form-input rx-compact-input med-strength" value="${escapeHtml(m.strength || "")}" placeholder="500 mg" ${isFinalized ? 'disabled' : ''} />
        </td>
        <td style="padding:6px;">
          <input type="text" class="form-input rx-compact-input med-dosage" value="${escapeHtml(m.dosage || "")}" placeholder="1 tab" required ${isFinalized ? 'disabled' : ''} />
        </td>
        <td style="padding:6px;">
          <input type="text" class="form-input rx-compact-input med-freq" value="${escapeHtml(m.frequency || "")}" placeholder="1-0-1" required ${isFinalized ? 'disabled' : ''} />
        </td>
        <td style="padding:6px;">
          <input type="text" class="form-input rx-compact-input med-duration" value="${escapeHtml(m.duration || "")}" placeholder="5 days" required ${isFinalized ? 'disabled' : ''} />
        </td>
        <td style="padding:6px;">
          <input type="text" class="form-input rx-compact-input med-instr" value="${escapeHtml(m.instructions || "")}" placeholder="After food" ${isFinalized ? 'disabled' : ''} />
        </td>
        <td style="padding:6px; text-align:center;" class="no-print">
          ${!isFinalized ? `
            <button type="button" class="btn-icon remove-rx-med-btn" data-idx="${idx}" title="Remove medicine" style="cursor:pointer; font-size:12px; color:#ef4444;">❌</button>
          ` : '-'}
        </td>
      </tr>
    `;
  },

  bindEditorEvents(isFinalized) {
    // Track dirty changes
    const markDirty = () => {
      if (!isFinalized) {
        this.isDirty = true;
        const ind = document.getElementById("rx-saved-indicator");
        if (ind) ind.textContent = "● Unsaved changes";
      }
    };

    this.container.querySelectorAll("input, textarea, select").forEach((input) => {
      input.addEventListener("input", markDirty);
    });

    const notesEditor = document.getElementById("rx-notes-editor");
    if (notesEditor && !isFinalized) {
      notesEditor.addEventListener("input", markDirty);
      // Clear placeholder on focus if initial placeholder present
      notesEditor.addEventListener("focus", () => {
        if (notesEditor.textContent.includes("Enter detailed clinical examination")) {
          notesEditor.innerHTML = "";
        }
      });
    }

    // Rich Text Toolbar
    this.container.querySelectorAll(".rx-format-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const cmd = btn.getAttribute("data-cmd");
        if (cmd) {
          document.execCommand(cmd, false, null);
          notesEditor?.focus();
          markDirty();
        }
      });
    });

    // Add medication row
    document.getElementById("rx-add-med-row")?.addEventListener("click", () => {
      const tbody = document.getElementById("rx-meds-tbody");
      if (!tbody) return;
      const count = tbody.querySelectorAll(".rx-med-row").length;
      const tr = document.createElement("tr");
      tr.className = "rx-med-row";
      tr.setAttribute("data-idx", count);
      tr.style.borderBottom = "1px solid #e2e8f0";
      tr.innerHTML = this.renderMedRowHtml({ name: "", strength: "", dosage: "", frequency: "", duration: "", instructions: "" }, count, false);
      tbody.appendChild(tr);
      this.bindMedRowRemoves();
      tr.querySelectorAll("input").forEach((inp) => inp.addEventListener("input", markDirty));
      markDirty();
    });

    this.bindMedRowRemoves();

    // Past history button clicks
    this.container.querySelectorAll(".rx-history-view-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          const pastRx = await API.getDoctorPrescription(btn.dataset.id);
          this.openEditor(pastRx);
        } catch (err) {
          showToast(err.message || "Failed to load past prescription.", "error");
        }
      });
    });

    // Back button
    document.getElementById("rx-back-btn")?.addEventListener("click", () => {
      if (this.isDirty) {
        if (!confirm("You have unsaved changes in this prescription draft. Discard and return to list?")) {
          return;
        }
      }
      this.renderList();
    });

    // Print button
    document.getElementById("rx-print-btn")?.addEventListener("click", () => {
      window.print();
    });

    // Save Draft button
    document.getElementById("rx-save-draft-btn")?.addEventListener("click", async () => {
      await this.saveDraftAction();
    });

    // Finalize button
    document.getElementById("rx-finalize-btn")?.addEventListener("click", async () => {
      await this.finalizeAction();
    });

    // Share button
    document.getElementById("rx-share-btn")?.addEventListener("click", () => {
      if (this.currentRx && this.currentRx.prescription_id) {
        this.openShareModal(this.currentRx.prescription_id);
      }
    });

    // Amend button
    document.getElementById("rx-amend-btn")?.addEventListener("click", async () => {
      await this.amendAction();
    });
  },

  bindMedRowRemoves() {
    this.container.querySelectorAll(".remove-rx-med-btn").forEach((btn) => {
      btn.onclick = () => {
        const row = btn.closest(".rx-med-row");
        if (row) {
          row.remove();
          this.isDirty = true;
          const ind = document.getElementById("rx-saved-indicator");
          if (ind) ind.textContent = "● Unsaved changes";
        }
      };
    });
  },

  getFormData() {
    const rx = this.currentRx || {};
    const rows = this.container.querySelectorAll(".rx-med-row");
    const meds = [];
    rows.forEach((r) => {
      const name = r.querySelector(".med-name")?.value.trim() || "";
      const strength = r.querySelector(".med-strength")?.value.trim() || "";
      const dosage = r.querySelector(".med-dosage")?.value.trim() || "";
      const frequency = r.querySelector(".med-freq")?.value.trim() || "";
      const duration = r.querySelector(".med-duration")?.value.trim() || "";
      const instructions = r.querySelector(".med-instr")?.value.trim() || "";
      if (name) {
        meds.push({ name, strength, dosage, frequency, duration, instructions });
      }
    });

    const notesEditor = document.getElementById("rx-notes-editor");
    let notesHtml = notesEditor ? notesEditor.innerHTML.trim() : "";
    if (notesHtml.includes("Enter detailed clinical examination observations")) {
      notesHtml = "";
    }

    const vitals = {
      bp: document.getElementById("rx-vital-bp")?.value.trim() || "",
      pulse: document.getElementById("rx-vital-pulse")?.value.trim() || "",
      temp: document.getElementById("rx-vital-temp")?.value.trim() || "",
      weight: document.getElementById("rx-vital-weight")?.value.trim() || "",
      spo2: document.getElementById("rx-vital-spo2")?.value.trim() || "",
    };

    return {
      prescription_id: rx.prescription_id || "",
      appointment_id: document.getElementById("rx-appt-id")?.value.trim() || "",
      patient_id: document.getElementById("rx-pt-id")?.value.trim() || "",
      patient_name: document.getElementById("rx-pt-name")?.value.trim() || "",
      patient_phone: document.getElementById("rx-pt-phone")?.value.trim() || "",
      patient_email: document.getElementById("rx-pt-email")?.value.trim() || "",
      patient_age: document.getElementById("rx-pt-age")?.value.trim() || "",
      patient_gender: document.getElementById("rx-pt-gender")?.value.trim() || "",
      date: document.getElementById("rx-date")?.value || "",
      chief_complaints: document.getElementById("rx-complaints")?.value.trim() || "",
      symptoms: document.getElementById("rx-symptoms")?.value.trim() || "",
      diagnosis: document.getElementById("rx-diagnosis")?.value.trim() || "",
      vitals,
      clinical_notes: notesHtml,
      medicines: meds,
      tests_advised: document.getElementById("rx-tests")?.value.trim() || "",
      advice: document.getElementById("rx-advice")?.value.trim() || "",
      follow_up_date: document.getElementById("rx-follow-up")?.value || "",
    };
  },

  async saveDraftAction() {
    const data = this.getFormData();
    if (!data.appointment_id || !data.patient_id || !data.patient_name) {
      showToast("Appointment Token, Patient ID, and Patient Name are required.", "warning");
      return;
    }

    try {
      showToast("Saving prescription draft...", "info");
      const saved = await API.savePrescriptionDraft(data);
      this.currentRx = saved;
      this.isDirty = false;
      this.lastSavedText = `Draft saved at ${formatTime(saved.updated_at)}`;
      showToast("Prescription draft saved successfully.", "success");
      const ind = document.getElementById("rx-saved-indicator");
      if (ind) ind.textContent = this.lastSavedText;
      if (!data.prescription_id && saved.prescription_id) {
        // Re-render to show generated ID and fresh state
        await this.renderEditor();
      }
    } catch (err) {
      showToast(err.message || "Failed to save prescription draft.", "error");
    }
  },

  async finalizeAction() {
    const data = this.getFormData();
    if (!data.appointment_id || !data.patient_id || !data.patient_name) {
      showToast("Appointment Token, Patient ID, and Patient Name are required.", "warning");
      return;
    }
    if (!data.diagnosis) {
      showToast("Clinical Diagnosis is required before finalizing prescription.", "warning");
      return;
    }
    if (!data.medicines.length) {
      showToast("At least one prescribed medication is required before finalization.", "warning");
      return;
    }

    if (!confirm("Are you sure you want to finalize this prescription? Once finalized, medications and clinical findings are locked and marked completed.")) {
      return;
    }

    try {
      showToast("Finalizing prescription...", "info");
      // 1. Save draft first to commit all latest form changes
      const saved = await API.savePrescriptionDraft(data);
      // 2. Finalize
      const finalized = await API.finalizePrescription(saved.prescription_id);
      this.currentRx = finalized;
      this.isDirty = false;
      showToast("Prescription finalized and verified successfully!", "success");
      await this.renderEditor();
    } catch (err) {
      showToast(err.message || "Failed to finalize prescription.", "error");
    }
  },

  async amendAction() {
    const rx = this.currentRx;
    if (!rx || !rx.prescription_id) return;

    const reason = prompt("Enter clinical justification / reason for amending this finalized prescription:");
    if (!reason || !reason.trim()) {
      showToast("Amendment reason is required to audit modifications.", "warning");
      return;
    }

    // Unlock inputs for editing
    this.container.querySelectorAll("input, textarea").forEach((inp) => inp.removeAttribute("disabled"));
    const notesEditor = document.getElementById("rx-notes-editor");
    if (notesEditor) notesEditor.setAttribute("contenteditable", "true");

    const amendBtn = document.getElementById("rx-amend-btn");
    if (amendBtn) {
      amendBtn.textContent = "💾 Commit Amendment";
      amendBtn.className = "btn btn-primary btn-sm";
      amendBtn.onclick = async () => {
        const data = this.getFormData();
        try {
          showToast("Recording prescription amendment...", "info");
          const amended = await API.amendPrescription(rx.prescription_id, {
            amendment_reason: reason.trim(),
            chief_complaints: data.chief_complaints,
            symptoms: data.symptoms,
            diagnosis: data.diagnosis,
            vitals: data.vitals,
            clinical_notes: data.clinical_notes,
            medicines: data.medicines,
            tests_advised: data.tests_advised,
            advice: data.advice,
            follow_up_date: data.follow_up_date,
          });
          this.currentRx = amended;
          this.isDirty = false;
          showToast("Prescription amendment saved as a new version!", "success");
          await this.renderEditor();
        } catch (err) {
          showToast(err.message || "Failed to record amendment.", "error");
        }
      };
    }
  },

  // =========================================================================
  // SHARE PRESCRIPTION MODAL
  // =========================================================================

  async openShareModal(prescriptionId) {
    let rx = this.currentRx;
    if (!rx || rx.prescription_id !== prescriptionId) {
      try {
        rx = await API.getDoctorPrescription(prescriptionId);
      } catch (err) {
        showToast(err.message || "Failed to load prescription.", "error");
        return;
      }
    }

    const patientEmail = rx.patient_email || "";
    const adminEmail = "admin@clinic.com";

    Modal.open({
      title: "Share Digital Prescription",
      body: `
        <div style="display:flex; flex-direction:column; gap:16px;">
          <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:12px;">
            <div style="font-size:13px; font-weight:700; color:#0f172a; margin-bottom:4px;">
              Prescription Ref: <code>${escapeHtml(rx.prescription_id)}</code> (v${rx.version || 1})
            </div>
            <div style="font-size:12px; color:#475569;">
              Patient: <strong>${escapeHtml(rx.patient_name)}</strong> (ID: ${escapeHtml(rx.patient_id || '-')})<br/>
              Diagnosis: <em>${escapeHtml(rx.diagnosis || 'Clinical evaluation')}</em>
            </div>
          </div>

          <!-- Share Target Selection -->
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label" style="font-weight:600;">Select Recipient *</label>
            <div style="display:flex; flex-direction:column; gap:8px; margin-top:6px;">
              <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-size:13px;">
                <input type="radio" name="share-target" id="share-target-patient" value="patient" checked />
                <span><strong>Share with Patient</strong> (${patientEmail ? escapeHtml(patientEmail) : 'No email on record'})</span>
              </label>
              <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-size:13px;">
                <input type="radio" name="share-target" id="share-target-admin" value="admin" />
                <span><strong>Share with Clinic Administration</strong> (${escapeHtml(adminEmail)})</span>
              </label>
            </div>
          </div>

          <!-- Recipient Email Input -->
          <div class="form-group" style="margin-bottom:0;">
            <label class="form-label" style="font-weight:600;">Destination Email Address *</label>
            <input type="email" id="share-email-input" class="form-input" value="${escapeHtml(patientEmail)}" placeholder="recipient@example.com" required />
          </div>

          <!-- Confidentiality Warning Banner -->
          <div style="background:#fffbeb; border:1px solid #fde68a; border-radius:6px; padding:10px 12px; font-size:12px; color:#92400e; line-height:1.4;">
            <strong>⚠️ Medical Privacy Notice:</strong> This action will dispatch protected patient health records and official digital prescription PDF to the specified recipient. Please verify the destination address carefully.
          </div>

          <!-- Explicit Confirmation Checkbox -->
          <label style="display:flex; align-items:flex-start; gap:8px; cursor:pointer; font-size:12.5px; color:#334155;">
            <input type="checkbox" id="share-confirm-checkbox" style="margin-top:2px;" />
            <span>I confirm that this clinical record is verified and ready for external transmission.</span>
          </label>

          <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:8px;">
            <button type="button" class="btn btn-secondary" onclick="document.getElementById('app-modal-close-btn').click()">Cancel</button>
            <button type="button" id="share-dispatch-btn" class="btn btn-primary">✉️ Send Prescription</button>
          </div>
        </div>
      `,
    });

    const targetPatient = document.getElementById("share-target-patient");
    const targetAdmin = document.getElementById("share-target-admin");
    const emailInput = document.getElementById("share-email-input");

    targetPatient?.addEventListener("change", () => {
      if (emailInput) emailInput.value = patientEmail;
    });

    targetAdmin?.addEventListener("change", () => {
      if (emailInput) emailInput.value = adminEmail;
    });

    document.getElementById("share-dispatch-btn")?.addEventListener("click", async () => {
      const email = emailInput?.value.trim() || "";
      const isConfirmed = document.getElementById("share-confirm-checkbox")?.checked;
      const targetType = targetAdmin?.checked ? "admin" : "patient";

      if (!email) {
        showToast("Recipient email address is required.", "warning");
        return;
      }
      if (!isConfirmed) {
        showToast("Please acknowledge the medical privacy confirmation checkbox.", "warning");
        return;
      }

      try {
        showToast("Dispatching official prescription PDF via email...", "info");
        const res = await API.emailPrescription(prescriptionId, email, targetType);
        if (res.success) {
          showToast(res.message || `Prescription successfully emailed to ${email}.`, "success");
          Modal.close();
          if (this.mode === "list") this.loadData();
        } else {
          showToast(res.error || "Email delivery failed. Please check clinic mail settings.", "error");
        }
      } catch (err) {
        showToast(err.message || "Failed to dispatch prescription email.", "error");
      }
    });
  },
};

