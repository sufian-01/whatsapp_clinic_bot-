/**
 * Super Admin Platform Console Client Controller.
 */

(function () {
  const token = localStorage.getItem('super_admin_token');
  if (!token) {
    window.location.href = '/super-admin/login.html';
    return;
  }

  // Parse user info if available
  try {
    const user = JSON.parse(localStorage.getItem('super_admin_user') || '{}');
    const userDisplay = document.getElementById('userDisplay');
    if (userDisplay && user.username) {
      userDisplay.textContent = `User: ${user.username} (Super Admin)`;
    }
  } catch (e) {}

  // Helpers for API requests
  async function api(path, options = {}) {
    const opts = {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    };
    const res = await fetch(path, opts);
    if (res.status === 401) {
      localStorage.removeItem('super_admin_token');
      localStorage.removeItem('super_admin_user');
      window.location.href = '/super-admin/login.html';
      throw new Error('Session expired. Please log in again.');
    }
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'API request failed.');
    }
    return data;
  }

  // View Navigation
  const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
  const viewPanels = {
    'dashboard': document.getElementById('view-dashboard'),
    'tenants': document.getElementById('view-tenants'),
    'audit-logs': document.getElementById('view-audit-logs'),
  };
  const viewTitle = document.getElementById('viewTitle');

  function switchView(viewName) {
    navItems.forEach(item => {
      item.classList.toggle('active', item.dataset.view === viewName);
    });
    Object.keys(viewPanels).forEach(key => {
      const p = viewPanels[key];
      if (p) {
        p.style.display = (key === viewName) ? 'block' : 'none';
      }
    });

    const viewSubTitle = document.getElementById('viewSubTitle');

    if (viewName === 'dashboard') {
      viewTitle.textContent = 'Platform Overview';
      if (viewSubTitle) viewSubTitle.textContent = 'Clinic onboarding, AI feature matrix & dynamic WhatsApp routing';
      loadDashboard();
    } else if (viewName === 'tenants') {
      viewTitle.textContent = 'Clinic Facilities & Tenants';
      if (viewSubTitle) viewSubTitle.textContent = 'Manage registered facilities, subscription plans, AI toggles & RAG documents';
      loadTenants();
    } else if (viewName === 'audit-logs') {
      viewTitle.textContent = 'Platform Audit Log Trail';
      if (viewSubTitle) viewSubTitle.textContent = 'Cryptographic activity trail of all administrative and facility changes';
      loadAuditLogs();
    }
  }

  window.addEventListener('hashchange', () => {
    const hash = window.location.hash.replace('#', '') || 'dashboard';
    switchView(hash);
  });

  // Initial load based on hash
  const initialHash = window.location.hash.replace('#', '') || 'dashboard';
  switchView(initialHash);

  // -------------------------------------------------------------------------
  // Dashboard Metrics
  // -------------------------------------------------------------------------
  async function loadDashboard() {
    try {
      const stats = await api('/api/super-admin/dashboard/stats');
      document.getElementById('statTotalTenants').textContent = stats.total_tenants ?? 0;
      document.getElementById('statActiveTenants').textContent = stats.active_tenants ?? 0;
      document.getElementById('statInactiveTenants').textContent = (stats.inactive_tenants + stats.suspended_tenants) ?? 0;
      document.getElementById('statTotalAdmins').textContent = stats.total_tenant_admins ?? 0;
      document.getElementById('statHealth').textContent = stats.system_health ?? 'HEALTHY';
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    }
  }

  // -------------------------------------------------------------------------
  // Tenants View
  // -------------------------------------------------------------------------
  let allTenants = [];
  const tbody = document.getElementById('tenantsTableBody');
  const searchInput = document.getElementById('tenantSearchInput');

  async function loadTenants() {
    tbody.innerHTML = '<tr><td colspan="6" style="padding: 2rem; text-align:center;">Loading tenants...</td></tr>';
    try {
      allTenants = await api('/api/super-admin/tenants');
      renderTenants(allTenants);
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="padding: 2rem; text-align:center; color: #dc2626;">Error: ${err.message}</td></tr>`;
    }
  }

  const TIER_DEFAULTS = {
    'STARTER': {
      ai_agent: true,
      voice_inbound: false,
      voice_outbound: false,
      interactive_lists: true,
      online_payments: false,
      cancellation: true,
      rescheduling: true,
      rag_knowledge: true,
      report_enquiry: true,
    },
    'PROFESSIONAL': {
      ai_agent: true,
      voice_inbound: true,
      voice_outbound: false,
      interactive_lists: true,
      online_payments: true,
      cancellation: true,
      rescheduling: true,
      rag_knowledge: true,
      report_enquiry: true,
    },
    'ENTERPRISE': {
      ai_agent: true,
      voice_inbound: true,
      voice_outbound: true,
      interactive_lists: true,
      online_payments: true,
      cancellation: true,
      rescheduling: true,
      rag_knowledge: true,
      report_enquiry: true,
    },
  };

  const FEATURE_KEYS = [
    'ai_agent',
    'voice_inbound',
    'voice_outbound',
    'interactive_lists',
    'online_payments',
    'cancellation',
    'rescheduling',
    'rag_knowledge',
    'report_enquiry',
  ];

  function renderTenants(tenants) {
    if (!tenants || tenants.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="padding: 2rem; text-align:center;">No clinics registered yet.</td></tr>';
      return;
    }

    tbody.innerHTML = tenants.map(t => {
      let statusBadge = '<span class="badge badge-success">ACTIVE</span>';
      if (t.status === 'SUSPENDED') {
        statusBadge = '<span class="badge badge-danger">SUSPENDED</span>';
      } else if (t.status === 'INACTIVE') {
        statusBadge = '<span class="badge" style="background:#64748b;color:#fff;">INACTIVE</span>';
      }

      const plan = t.subscription_plan || 'STARTER';
      let planBadgeColor = '#64748b';
      if (plan === 'PROFESSIONAL') planBadgeColor = '#0284c7';
      if (plan === 'ENTERPRISE') planBadgeColor = '#7c3aed';

      return `
        <tr style="border-bottom: 1px solid var(--border-color);">
          <td style="padding: 1rem; font-weight: 600;">
            <code>${t.id}</code>
            <div style="margin-top: 4px;">
              <span class="badge" style="background:${planBadgeColor};color:#fff;font-size:0.65rem;">${plan}</span>
            </div>
          </td>
          <td style="padding: 1rem;">
            <div style="font-weight: 600;">${t.name}</div>
            <div style="font-size: 0.8rem; color: var(--text-secondary);">${t.email || t.phone || 'No contact'}</div>
          </td>
          <td style="padding: 1rem;">
            ${t.whatsapp_phone_number_id 
              ? `<div style="font-weight:600;font-size:0.85rem;"><code>${t.whatsapp_phone_number_id}</code></div>
                 <div style="font-size:0.75rem;color:var(--text-secondary);">${t.whatsapp_phone_number || ''}</div>`
              : `<span style="font-size:0.75rem;color:#f59e0b;font-weight:600;">⚠️ Unconfigured</span>`
            }
          </td>
          <td style="padding: 1rem;">${statusBadge}</td>
          <td style="padding: 1rem; font-size: 0.85rem;">${t.admin_count ?? 0} admins</td>
          <td style="padding: 1rem; text-align: right; white-space:nowrap;">
            <button class="btn btn-primary btn-sm" onclick="window.openManageTenant('${t.id}')">⚙️ Manage</button>
            <button class="btn btn-secondary btn-sm" onclick="window.openAddAdmin('${t.id}')">+ Admin</button>
            ${t.status === 'ACTIVE' 
              ? `<button class="btn btn-secondary btn-sm" style="color:#dc2626;" onclick="window.suspendTenant('${t.id}')">Suspend</button>`
              : `<button class="btn btn-secondary btn-sm" style="color:#16a34a;" onclick="window.activateTenant('${t.id}')">Activate</button>`
            }
          </td>
        </tr>
      `;
    }).join('');
  }

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      const filtered = allTenants.filter(t => 
        (t.name && t.name.toLowerCase().includes(q)) ||
        (t.id && t.id.toLowerCase().includes(q)) ||
        (t.whatsapp_phone_number_id && t.whatsapp_phone_number_id.toLowerCase().includes(q))
      );
      renderTenants(filtered);
    });
  }

  // Tenant Actions
  window.activateTenant = async function(id) {
    if (!confirm(`Activate tenant ${id}?`)) return;
    try {
      await api(`/api/super-admin/tenants/${id}/activate`, { method: 'POST' });
      await loadTenants();
    } catch (err) {
      alert(`Activation failed: ${err.message}`);
    }
  };

  window.suspendTenant = async function(id) {
    const reason = prompt(`Reason for suspending tenant ${id}:`, 'Administrative review');
    if (reason === null) return;
    try {
      await api(`/api/super-admin/tenants/${id}/suspend`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      });
      await loadTenants();
    } catch (err) {
      alert(`Suspension failed: ${err.message}`);
    }
  };

  // -------------------------------------------------------------------------
  // Modals Management
  // -------------------------------------------------------------------------
  const createTenantModal = document.getElementById('createTenantModal');
  const createAdminModal = document.getElementById('createAdminModal');
  const manageTenantModal = document.getElementById('manageTenantModal');

  document.querySelectorAll('.close-modal-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (createTenantModal) createTenantModal.classList.remove('active');
      if (createAdminModal) createAdminModal.classList.remove('active');
      if (manageTenantModal) manageTenantModal.classList.remove('active');
    });
  });

  const openCreateTenantBtn = document.getElementById('openCreateTenantModalBtn');
  const createTenantTopBtn = document.getElementById('createTenantTopBtn');
  if (openCreateTenantBtn) openCreateTenantBtn.onclick = () => createTenantModal.classList.add('active');
  if (createTenantTopBtn) createTenantTopBtn.onclick = () => createTenantModal.classList.add('active');

  // Create Tenant Logo file upload handler
  const createTenantLogoFile = document.getElementById('createTenantLogoFile');
  const createTenantLogoInput = document.getElementById('createTenantLogoInput');
  const createTenantLogoPreviewBox = document.getElementById('createTenantLogoPreviewBox');
  const createTenantLogoPreview = document.getElementById('createTenantLogoPreview');

  if (createTenantLogoFile && createTenantLogoInput) {
    createTenantLogoFile.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (loadEvt) => {
          const dataUri = loadEvt.target.result;
          createTenantLogoInput.value = dataUri;
          if (createTenantLogoPreview) createTenantLogoPreview.src = dataUri;
          if (createTenantLogoPreviewBox) createTenantLogoPreviewBox.style.display = 'block';
        };
        reader.readAsDataURL(file);
      }
    };
    createTenantLogoInput.oninput = () => {
      const val = createTenantLogoInput.value.trim();
      if (val && createTenantLogoPreview && createTenantLogoPreviewBox) {
        createTenantLogoPreview.src = val;
        createTenantLogoPreviewBox.style.display = 'block';
      } else if (createTenantLogoPreviewBox) {
        createTenantLogoPreviewBox.style.display = 'none';
      }
    };
  }

  const createTenantForm = document.getElementById('createTenantForm');
  if (createTenantForm) {
    createTenantForm.onsubmit = async (e) => {
      e.preventDefault();
      const payload = {
        name: createTenantForm.name.value.trim(),
        id: createTenantForm.id.value.trim() || undefined,
        logo: createTenantForm.logo ? createTenantForm.logo.value.trim() : undefined,
        whatsapp_phone_number_id: createTenantForm.whatsapp_phone_number_id.value.trim() || undefined,
        whatsapp_phone_number: createTenantForm.whatsapp_phone_number.value.trim() || undefined,
        whatsapp_waba_id: createTenantForm.whatsapp_waba_id.value.trim() || undefined,
        subscription_plan: createTenantForm.subscription_plan.value || 'STARTER',
        phone: createTenantForm.phone.value.trim() || undefined,
        email: createTenantForm.email.value.trim() || undefined,
        timezone: createTenantForm.timezone.value.trim() || 'Asia/Kolkata',
        currency: createTenantForm.currency.value.trim() || 'INR',
      };
      try {
        await api('/api/super-admin/tenants', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        createTenantModal.classList.remove('active');
        createTenantForm.reset();
        if (createTenantLogoPreviewBox) createTenantLogoPreviewBox.style.display = 'none';
        await loadTenants();
      } catch (err) {
        alert(`Failed to create clinic facility: ${err.message}`);
      }
    };
  }

  window.openAddAdmin = function(tenantId) {
    document.getElementById('adminModalTenantId').value = tenantId;
    document.getElementById('adminModalTenantDisplay').value = tenantId;
    createAdminModal.classList.add('active');
  };

  const createAdminForm = document.getElementById('createAdminForm');
  if (createAdminForm) {
    createAdminForm.onsubmit = async (e) => {
      e.preventDefault();
      const tid = document.getElementById('adminModalTenantId').value;
      const payload = {
        username: createAdminForm.username.value.trim(),
        password: createAdminForm.password.value,
        full_name: createAdminForm.full_name.value.trim(),
        email: createAdminForm.email.value.trim(),
      };
      try {
        await api(`/api/super-admin/tenants/${tid}/admins`, {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        createAdminModal.classList.remove('active');
        createAdminForm.reset();
        alert(`Administrator successfully created for ${tid}`);
        await loadTenants();
      } catch (err) {
        alert(`Failed to create admin: ${err.message}`);
      }
    };
  }

  // -------------------------------------------------------------------------
  // Manage Clinic Drawer & Feature Flags & RAG Ingestion
  // -------------------------------------------------------------------------
  let activeManageTenantId = null;

  // Drawer Tabs switching
  document.querySelectorAll('.drawer-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.drawer-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.drawer-tab-content').forEach(c => c.style.display = 'none');
      btn.classList.add('active');
      const targetId = 'drawer-' + btn.dataset.tab;
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.style.display = 'block';
    });
  });

  window.openManageTenant = async function(tenantId) {
    activeManageTenantId = tenantId;
    const t = allTenants.find(item => item.id === tenantId) || await api(`/api/super-admin/tenants/${tenantId}`);
    
    // Header
    document.getElementById('manageModalClinicName').textContent = t.name;
    document.getElementById('manageModalTenantId').textContent = t.id;
    document.getElementById('manageModalStatusBadge').textContent = t.status || 'ACTIVE';

    // Populate Tab 1: Overview
    document.getElementById('m_clinicName').value = t.name || '';
    document.getElementById('m_waPhoneId').value = t.whatsapp_phone_number_id || '';
    document.getElementById('m_waPhone').value = t.whatsapp_phone_number || '';
    document.getElementById('m_waWaba').value = t.whatsapp_waba_id || '';
    document.getElementById('m_phone').value = t.phone || '';
    document.getElementById('m_email').value = t.email || '';
    document.getElementById('m_address').value = t.address || '';

    const logoVal = t.logo || '';
    const mLogoInput = document.getElementById('m_logo');
    const mLogoPrevBox = document.getElementById('m_logoPreviewBox');
    const mLogoPrev = document.getElementById('m_logoPreview');
    if (mLogoInput) mLogoInput.value = logoVal;
    if (mLogoPrevBox && mLogoPrev) {
      if (logoVal) {
        mLogoPrev.src = logoVal;
        mLogoPrevBox.style.display = 'block';
      } else {
        mLogoPrevBox.style.display = 'none';
      }
    }

    const waStatusBox = document.getElementById('waConnectionStatus');
    if (waStatusBox) waStatusBox.style.display = 'none';

    // Switch to Tab 1 initially
    document.querySelectorAll('.drawer-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === 'tab-overview'));
    document.querySelectorAll('.drawer-tab-content').forEach(c => c.style.display = 'none');
    document.getElementById('drawer-tab-overview').style.display = 'block';

    // Populate Tab 2: Subscription & Feature Flags
    await loadTenantFeatures(tenantId, t.subscription_plan);

    // Populate Tab 3: RAG Documents
    await loadTenantDocuments(tenantId);

    manageTenantModal.classList.add('active');
  };

  async function loadTenantFeatures(tenantId, fallbackPlan) {
    try {
      const data = await api(`/api/super-admin/tenants/${tenantId}/features`);
      const plan = data.subscription_plan || fallbackPlan || 'STARTER';
      document.getElementById('m_subscriptionPlanSelect').value = plan;
      
      const flags = data.feature_flags || {};
      FEATURE_KEYS.forEach(key => {
        const input = document.getElementById(`flag_${key}`);
        if (input) {
          input.checked = !!flags[key];
        }
      });
    } catch (err) {
      console.error('Failed to load features:', err);
    }
  }

  // Apply Plan Defaults Button
  const applyPlanDefaultsBtn = document.getElementById('m_applyPlanDefaultsBtn');
  if (applyPlanDefaultsBtn) {
    applyPlanDefaultsBtn.onclick = () => {
      const selectedPlan = document.getElementById('m_subscriptionPlanSelect').value;
      const defaults = TIER_DEFAULTS[selectedPlan] || TIER_DEFAULTS['STARTER'];
      FEATURE_KEYS.forEach(key => {
        const input = document.getElementById(`flag_${key}`);
        if (input) {
          input.checked = !!defaults[key];
        }
      });
    };
  }

  // Save Plan Button
  const savePlanBtn = document.getElementById('m_savePlanBtn');
  if (savePlanBtn) {
    savePlanBtn.onclick = async () => {
      if (!activeManageTenantId) return;
      const plan = document.getElementById('m_subscriptionPlanSelect').value;
      try {
        await api(`/api/super-admin/tenants/${activeManageTenantId}/subscription`, {
          method: 'PATCH',
          body: JSON.stringify({ subscription_plan: plan }),
        });
        alert(`Subscription plan updated to ${plan} for ${activeManageTenantId}`);
        await loadTenants();
      } catch (err) {
        alert(`Failed to update subscription: ${err.message}`);
      }
    };
  }

  // Save Feature Flags Button
  const saveFlagsBtn = document.getElementById('m_saveFlagsBtn');
  if (saveFlagsBtn) {
    saveFlagsBtn.onclick = async () => {
      if (!activeManageTenantId) return;
      const flags = {};
      FEATURE_KEYS.forEach(key => {
        const input = document.getElementById(`flag_${key}`);
        flags[key] = input ? input.checked : true;
      });
      try {
        await api(`/api/super-admin/tenants/${activeManageTenantId}/features`, {
          method: 'PATCH',
          body: JSON.stringify({ feature_flags: flags }),
        });
        alert(`Feature toggles successfully saved for ${activeManageTenantId}`);
        await loadTenants();
      } catch (err) {
        alert(`Failed to save feature flags: ${err.message}`);
      }
    };
  }

  // Manage Tenant Logo file upload handler
  const mLogoFile = document.getElementById('m_logoFile');
  const mLogoInput = document.getElementById('m_logo');
  const mLogoPreviewBox = document.getElementById('m_logoPreviewBox');
  const mLogoPreview = document.getElementById('m_logoPreview');

  if (mLogoFile && mLogoInput) {
    mLogoFile.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (loadEvt) => {
          const dataUri = loadEvt.target.result;
          mLogoInput.value = dataUri;
          if (mLogoPreview) mLogoPreview.src = dataUri;
          if (mLogoPreviewBox) mLogoPreviewBox.style.display = 'block';
        };
        reader.readAsDataURL(file);
      }
    };
    mLogoInput.oninput = () => {
      const val = mLogoInput.value.trim();
      if (val && mLogoPreview && mLogoPreviewBox) {
        mLogoPreview.src = val;
        mLogoPreviewBox.style.display = 'block';
      } else if (mLogoPreviewBox) {
        mLogoPreviewBox.style.display = 'none';
      }
    };
  }

  // Save Facility Details (Overview & WhatsApp)
  const manageOverviewForm = document.getElementById('manageOverviewForm');
  if (manageOverviewForm) {
    manageOverviewForm.onsubmit = async (e) => {
      e.preventDefault();
      if (!activeManageTenantId) return;
      const payload = {
        name: document.getElementById('m_clinicName').value.trim(),
        logo: document.getElementById('m_logo') ? document.getElementById('m_logo').value.trim() || undefined : undefined,
        whatsapp_phone_number_id: document.getElementById('m_waPhoneId').value.trim(),
        whatsapp_phone_number: document.getElementById('m_waPhone').value.trim(),
        whatsapp_waba_id: document.getElementById('m_waWaba').value.trim(),
        phone: document.getElementById('m_phone').value.trim(),
        email: document.getElementById('m_email').value.trim(),
        address: document.getElementById('m_address').value.trim(),
      };
      try {
        await api(`/api/super-admin/tenants/${activeManageTenantId}`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        });
        alert(`Facility & WhatsApp configuration updated for ${activeManageTenantId}`);
        await loadTenants();
      } catch (err) {
        alert(`Failed to update facility details: ${err.message}`);
      }
    };
  }

  const btnTestWhatsApp = document.getElementById('btnTestWhatsAppConnection');
  if (btnTestWhatsApp) {
    btnTestWhatsApp.onclick = async () => {
      if (!activeManageTenantId) return;
      const phoneId = document.getElementById('m_waPhoneId').value.trim();
      const statusBox = document.getElementById('waConnectionStatus');
      if (!statusBox) return;

      btnTestWhatsApp.disabled = true;
      btnTestWhatsApp.innerHTML = '<span>⏳</span> Testing Meta Connection...';
      statusBox.style.display = 'block';
      statusBox.style.background = 'var(--bg-surface)';
      statusBox.style.borderColor = 'var(--border-light)';
      statusBox.style.color = 'var(--text-secondary)';
      statusBox.innerHTML = 'Pinging Meta Cloud Graph API...';

      try {
        const res = await api(`/api/super-admin/tenants/${activeManageTenantId}/whatsapp/verify`, {
          method: 'POST',
          body: JSON.stringify({ phone_number_id: phoneId }),
        });

        if (res.success && res.data) {
          statusBox.style.background = 'rgba(16, 185, 129, 0.1)';
          statusBox.style.borderColor = 'rgba(16, 185, 129, 0.3)';
          statusBox.style.color = 'var(--success-text)';
          statusBox.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 3px;">✅ Meta WhatsApp Connection Verified</div>
            <div style="font-size: 11.5px; opacity: 0.9;">
              <strong>Name:</strong> ${res.data.verified_name || '-'} | 
              <strong>Display Phone:</strong> ${res.data.display_phone_number || '-'} | 
              <strong>Quality:</strong> <span class="badge badge-completed" style="font-size: 10.5px; padding: 2px 6px;">${res.data.quality_rating || 'GREEN'}</span>
            </div>
          `;
        } else {
          statusBox.style.background = 'rgba(239, 68, 68, 0.1)';
          statusBox.style.borderColor = 'rgba(239, 68, 68, 0.3)';
          statusBox.style.color = 'var(--danger-text)';
          statusBox.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 3px;">⚠️ Connection Test Failed</div>
            <div style="font-size: 11.5px;">${res.error || 'Unable to communicate with Meta Cloud API.'}</div>
          `;
        }
      } catch (err) {
        statusBox.style.background = 'rgba(239, 68, 68, 0.1)';
        statusBox.style.borderColor = 'rgba(239, 68, 68, 0.3)';
        statusBox.style.color = 'var(--danger-text)';
        statusBox.innerHTML = `
          <div style="font-weight: 600; margin-bottom: 3px;">⚠️ Request Error</div>
          <div style="font-size: 11.5px;">${err.message}</div>
        `;
      } finally {
        btnTestWhatsApp.disabled = false;
        btnTestWhatsApp.innerHTML = '<span>⚡</span> Test Meta Connection';
      }
    };
  }

  // RAG Document Management
  async function loadTenantDocuments(tenantId) {
    const tableBody = document.getElementById('m_documentsTableBody');
    tableBody.innerHTML = '<tr><td colspan="5" style="padding: 1.5rem; text-align:center;">Loading indexed documents...</td></tr>';
    try {
      const docs = await api(`/api/super-admin/tenants/${tenantId}/documents`);
      if (!docs || docs.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" style="padding: 1.5rem; text-align:center; color: var(--text-secondary);">No documents indexed yet for this clinic.</td></tr>';
        return;
      }
      tableBody.innerHTML = docs.map(d => {
        const sizeKb = (d.size_bytes / 1024).toFixed(1);
        const dateStr = d.updated_at ? new Date(d.updated_at).toLocaleDateString() : '-';
        return `
          <tr style="border-bottom: 1px solid var(--border-color); font-size: 0.85rem;">
            <td style="padding: 0.75rem 1rem; font-weight: 600;">📄 ${d.filename}</td>
            <td style="padding: 0.75rem 1rem;">${sizeKb} KB</td>
            <td style="padding: 0.75rem 1rem;"><span class="badge" style="background:#e0e7ff;color:#4338ca;">${d.extension || 'DOC'}</span></td>
            <td style="padding: 0.75rem 1rem; color: var(--text-secondary);">${dateStr}</td>
            <td style="padding: 0.75rem 1rem; text-align: right;">
              <button class="btn btn-secondary btn-sm" style="color:#dc2626;" onclick="window.deleteTenantDocument('${tenantId}', '${d.filename}')">Delete</button>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="5" style="padding: 1.5rem; text-align:center; color:#dc2626;">Error: ${err.message}</td></tr>`;
    }
  }

  // Upload Document Form
  const docUploadForm = document.getElementById('m_docUploadForm');
  if (docUploadForm) {
    docUploadForm.onsubmit = async (e) => {
      e.preventDefault();
      if (!activeManageTenantId) return;
      const fileInput = document.getElementById('m_docFileInput');
      if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please select a document file (.pdf, .txt, .md)');
        return;
      }
      const file = fileInput.files[0];
      const statusDiv = document.getElementById('m_uploadStatus');
      statusDiv.style.color = '#4f46e5';
      statusDiv.textContent = `Uploading and vector-indexing "${file.name}"...`;

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch(`/api/super-admin/tenants/${activeManageTenantId}/documents`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        });
        const result = await res.json();
        if (!res.ok) {
          throw new Error(result.detail || 'Upload failed');
        }
        statusDiv.style.color = '#16a34a';
        statusDiv.textContent = `✓ Successfully indexed "${file.name}" (${result.indexed_chunks || 0} chunks in vector index)`;
        fileInput.value = '';
        await loadTenantDocuments(activeManageTenantId);
      } catch (err) {
        statusDiv.style.color = '#dc2626';
        statusDiv.textContent = `✕ Upload failed: ${err.message}`;
      }
    };
  }

  // Delete Document
  window.deleteTenantDocument = async function(tenantId, filename) {
    if (!confirm(`Delete document "${filename}" from this clinic's knowledge base? The vector store will automatically re-index.`)) return;
    try {
      await api(`/api/super-admin/tenants/${tenantId}/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      });
      await loadTenantDocuments(tenantId);
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };


  // -------------------------------------------------------------------------
  // Platform Audit Logs (Paginated)
  // -------------------------------------------------------------------------
  let auditLogsData = [];
  let auditLogsPage = 1;
  const auditLogsPageSize = 15;

  async function loadAuditLogs() {
    const tableBody = document.getElementById('auditTableBody');
    tableBody.innerHTML = '<tr><td colspan="5" style="padding: 2rem; text-align:center;">Loading platform audit logs...</td></tr>';
    try {
      const logs = await api('/api/super-admin/audit-logs');
      auditLogsData = logs || [];
      auditLogsPage = 1;
      renderAuditLogsTable();
    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="5" style="padding: 2rem; text-align:center; color:#dc2626;">Error: ${err.message}</td></tr>`;
    }
  }

  function renderAuditLogsTable() {
    const tableBody = document.getElementById('auditTableBody');
    const pageInfo = document.getElementById('super-audit-info');
    const pageNum = document.getElementById('super-audit-page-num');
    const prevBtn = document.getElementById('super-audit-prev');
    const nextBtn = document.getElementById('super-audit-next');

    if (!auditLogsData || auditLogsData.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="5" style="padding: 2rem; text-align:center;">No platform audit entries recorded yet.</td></tr>';
      if (pageInfo) pageInfo.textContent = 'Showing 0 platform logs';
      if (pageNum) pageNum.textContent = 'Page 1 of 1';
      if (prevBtn) prevBtn.disabled = true;
      if (nextBtn) nextBtn.disabled = true;
      return;
    }

    const total = auditLogsData.length;
    const totalPages = Math.ceil(total / auditLogsPageSize) || 1;
    if (auditLogsPage > totalPages) auditLogsPage = totalPages;
    if (auditLogsPage < 1) auditLogsPage = 1;

    const start = (auditLogsPage - 1) * auditLogsPageSize;
    const pagedLogs = auditLogsData.slice(start, start + auditLogsPageSize);

    tableBody.innerHTML = pagedLogs.map(l => `
      <tr style="border-bottom: 1px solid var(--border-color);">
        <td style="padding: 1rem; font-size: 0.85rem; color: var(--text-secondary);">${new Date(l.timestamp).toLocaleString()}</td>
        <td style="padding: 1rem; font-weight: 600;">${l.user}</td>
        <td style="padding: 1rem;"><span class="badge badge-secondary">${l.action}</span></td>
        <td style="padding: 1rem;"><code>${l.entity_type}:${l.entity_id}</code></td>
        <td style="padding: 1rem; font-size: 0.85rem; color: var(--text-secondary);"><pre style="margin:0;font-size:0.75rem;">${JSON.stringify(l.details || {})}</pre></td>
      </tr>
    `).join('');

    if (pageInfo) {
      const end = Math.min(start + auditLogsPageSize, total);
      pageInfo.textContent = `Showing ${start + 1} – ${end} of ${total} platform logs`;
    }

    if (pageNum) {
      pageNum.textContent = `Page ${auditLogsPage} of ${totalPages}`;
    }

    if (prevBtn) {
      prevBtn.disabled = auditLogsPage <= 1;
      prevBtn.onclick = () => {
        if (auditLogsPage > 1) {
          auditLogsPage--;
          renderAuditLogsTable();
        }
      };
    }

    if (nextBtn) {
      nextBtn.disabled = auditLogsPage >= totalPages;
      nextBtn.onclick = () => {
        if (auditLogsPage < totalPages) {
          auditLogsPage++;
          renderAuditLogsTable();
        }
      };
    }
  }

  // -------------------------------------------------------------------------
  // Sign Out & Theme Toggle
  // -------------------------------------------------------------------------
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.onclick = () => {
      localStorage.removeItem('super_admin_token');
      localStorage.removeItem('super_admin_user');
      window.location.href = '/super-admin/login.html';
    };
  }

  const themeToggleBtn = document.getElementById('themeToggleBtn');
  if (themeToggleBtn) {
    const cur = document.documentElement.getAttribute('data-theme') || 'light';
    themeToggleBtn.textContent = cur === 'dark' ? '☀️' : '🌙';
    themeToggleBtn.onclick = () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('crm_theme', next);
      themeToggleBtn.textContent = next === 'dark' ? '☀️' : '🌙';
    };
  }

  // Mobile navigation drawer toggle
  const mobileToggle = document.getElementById('mobile-menu-toggle');
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (mobileToggle && sidebar && backdrop) {
    mobileToggle.onclick = () => {
      sidebar.classList.toggle('open');
      backdrop.classList.toggle('open');
    };
    backdrop.onclick = () => {
      sidebar.classList.remove('open');
      backdrop.classList.remove('open');
    };
  }
})();
