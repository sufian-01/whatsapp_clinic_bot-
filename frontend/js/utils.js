/**
 * UI Utilities, Toast alerts, Date formatting, and Modal helpers.
 */

export function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function formatCurrency(amount) {
  if (amount === null || amount === undefined || amount === "") return "₹0";
  const num = parseFloat(String(amount).replace(/[^0-9.-]+/g, ""));
  if (isNaN(num)) return `₹${amount}`;
  return "₹" + num.toLocaleString("en-IN");
}

export function formatDate(dateStr) {
  if (!dateStr) return "-";
  try {
    const parts = dateStr.split("T")[0].split("-");
    if (parts.length === 3) {
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const d = new Date(year, month, day);
      return d.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    }
    const d = new Date(dateStr);
    if (!isNaN(d.getTime())) {
      return d.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
    }
  } catch (e) {
    // fallback
  }
  return dateStr;
}

export function formatTime(timeStr) {
  if (!timeStr) return "-";
  return timeStr;
}

export function formatDateTime(dateStr) {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    if (!isNaN(d.getTime())) {
      return d.toLocaleString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    }
  } catch (e) {
    // fallback
  }
  return dateStr;
}

export function getTodayDateStr() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function renderBadge(status) {
  if (!status) return "";
  const s = String(status).trim();
  const normalized = s.toLowerCase();
  let badgeClass = `badge-${normalized}`;
  return `<span class="badge ${badgeClass}"><span class="badge-dot"></span>${escapeHtml(s)}</span>`;
}

export function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;

  let icon = "ℹ️";
  if (type === "success") icon = "✓";
  if (type === "error") icon = "✕";
  if (type === "warning") icon = "⚠️";

  toast.innerHTML = `<span>${icon}</span> <span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 200ms ease";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

export const Toast = {
  info(msg) { showToast(msg, "info"); },
  success(msg) { showToast(msg, "success"); },
  error(msg) { showToast(msg, "error"); },
  warning(msg) { showToast(msg, "warning"); },
};

export function debounce(func, delay = 300) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => func.apply(this, args), delay);
  };
}

export const Modal = {
  open(title, bodyHtml, footerHtml = "") {
    const backdrop = document.getElementById("app-modal-backdrop");
    const titleEl = document.getElementById("app-modal-title");
    const bodyEl = document.getElementById("app-modal-body");
    const footerEl = document.getElementById("app-modal-footer");

    if (!backdrop || !titleEl || !bodyEl) return;

    titleEl.innerHTML = title;
    bodyEl.innerHTML = bodyHtml;

    if (footerEl) {
      if (footerHtml) {
        footerEl.innerHTML = footerHtml;
        footerEl.style.display = "flex";
      } else {
        footerEl.innerHTML = "";
        footerEl.style.display = "none";
      }
    }

    backdrop.classList.add("open");
  },

  close() {
    const backdrop = document.getElementById("app-modal-backdrop");
    if (backdrop) {
      backdrop.classList.remove("open");
    }
  },
};

export function renderTableSkeletons(cols = 6, rows = 5) {
  let out = "";
  for (let r = 0; r < rows; r++) {
    out += "<tr>";
    for (let c = 0; c < cols; c++) {
      const width = 45 + Math.floor(Math.random() * 45);
      out += `<td><div class="skeleton" style="height: 14px; width: ${width}%; border-radius: 4px;"></div></td>`;
    }
    out += "</tr>";
  }
  return out;
}
