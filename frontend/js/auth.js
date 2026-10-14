/**
 * Authentication and session management module.
 */

const TOKEN_KEY = "crm_admin_token";
const USER_KEY = "crm_admin_user";

export const Auth = {
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },

  getUser() {
    try {
      const data = localStorage.getItem(USER_KEY);
      return data ? JSON.parse(data) : null;
    } catch (e) {
      return null;
    }
  },

  setSession(token, user) {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    }
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
  },

  clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  isAuthenticated() {
    return !!this.getToken();
  },

  getRole() {
    const user = this.getUser();
    return (user && user.role) ? String(user.role).toUpperCase() : "";
  },

  isSuperAdmin() {
    const r = this.getRole();
    return r === "SUPER_ADMIN";
  },

  isAdmin() {
    const r = this.getRole();
    return r === "ADMIN" || r === "TENANT_ADMIN" || r === "SUPER_ADMIN";
  },

  isDoctor() {
    const r = this.getRole();
    return r === "DOCTOR";
  },

  isReceptionist() {
    const r = this.getRole();
    return r === "RECEPTIONIST";
  },

  isStaff() {
    const r = this.getRole();
    return r === "STAFF";
  },

  mustChangePassword() {
    const user = this.getUser();
    return user && user.must_change_password === true;
  },

  requireAuth() {
    if (!this.isAuthenticated()) {
      window.location.href = "/admin/login.html";
      return false;
    }
    return true;
  },

  async logout() {
    try {
      const token = this.getToken();
      if (token) {
        await fetch("/api/admin/auth/logout", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });
      }
    } catch (err) {
      console.warn("Logout request failed:", err);
    } finally {
      this.clearSession();
      window.location.href = "/admin/login.html";
    }
  },
};
