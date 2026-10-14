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

    if (viewName === 'dashboard') {
      viewTitle.textContent = 'Platform Overview';
      loadDashboard();
    } else if (viewName === 'tenants') {
      viewTitle.textContent = 'Clinic Facilities & Tenants';
      loadTenants();
    } else if (viewName === 'audit-logs') {
      viewTitle.textContent = 'Platform Audit Log Trail';
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

      return `
        <tr style="border-bottom: 1px solid var(--border-color);">
          <td style="padding: 1rem; font-weight: 600;"><code>${t.id}</code></td>
          <td style="padding: 1rem;">
            <div style="font-weight: 600;">${t.name}</div>
            <div style="font-size: 0.8rem; color: var(--text-secondary);">${t.email || t.phone || 'No contact'}</div>
          </td>
          <td style="padding: 1rem;">${statusBadge}</td>
          <td style="padding: 1rem;">${t.admin_count ?? 0} admins</td>
          <td style="padding: 1rem; font-size: 0.85rem;">${t.timezone || 'Asia/Kolkata'}</td>
          <td style="padding: 1rem; text-align: right;">
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
        (t.id && t.id.toLowerCase().includes(q))
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

  document.querySelectorAll('.close-modal-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      createTenantModal.classList.remove('active');
      createAdminModal.classList.remove('active');
    });
  });

  const openCreateTenantBtn = document.getElementById('openCreateTenantModalBtn');
  const createTenantTopBtn = document.getElementById('createTenantTopBtn');
  if (openCreateTenantBtn) openCreateTenantBtn.onclick = () => createTenantModal.classList.add('active');
  if (createTenantTopBtn) createTenantTopBtn.onclick = () => createTenantModal.classList.add('active');

  const createTenantForm = document.getElementById('createTenantForm');
  if (createTenantForm) {
    createTenantForm.onsubmit = async (e) => {
      e.preventDefault();
      const payload = {
        name: createTenantForm.name.value.trim(),
        id: createTenantForm.id.value.trim() || undefined,
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
        await loadTenants();
      } catch (err) {
        alert(`Failed to create clinic: ${err.message}`);
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
  // Platform Audit Logs
  // -------------------------------------------------------------------------
  async function loadAuditLogs() {
    const tableBody = document.getElementById('auditTableBody');
    tableBody.innerHTML = '<tr><td colspan="5" style="padding: 2rem; text-align:center;">Loading platform audit logs...</td></tr>';
    try {
      const logs = await api('/api/super-admin/audit-logs');
      if (!logs || logs.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" style="padding: 2rem; text-align:center;">No platform audit entries recorded yet.</td></tr>';
        return;
      }
      tableBody.innerHTML = logs.map(l => `
        <tr style="border-bottom: 1px solid var(--border-color);">
          <td style="padding: 1rem; font-size: 0.85rem; color: var(--text-secondary);">${new Date(l.timestamp).toLocaleString()}</td>
          <td style="padding: 1rem; font-weight: 600;">${l.user}</td>
          <td style="padding: 1rem;"><span class="badge badge-secondary">${l.action}</span></td>
          <td style="padding: 1rem;"><code>${l.entity_type}:${l.entity_id}</code></td>
          <td style="padding: 1rem; font-size: 0.85rem; color: var(--text-secondary);"><pre style="margin:0;font-size:0.75rem;">${JSON.stringify(l.details || {})}</pre></td>
        </tr>
      `).join('');
    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="5" style="padding: 2rem; text-align:center; color:#dc2626;">Error: ${err.message}</td></tr>`;
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
    themeToggleBtn.onclick = () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('crm_theme', next);
    };
  }
})();
