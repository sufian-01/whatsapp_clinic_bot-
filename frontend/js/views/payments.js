/**
 * Payments & Billing View Module with Manual Payment Recording & PDF Invoices.
 */

import { API } from "../api.js";
import { debounce, escapeHtml, formatCurrency, formatDate, Modal, renderBadge, showToast, renderTableSkeletons } from "../utils.js";

export const PaymentsView = {
  container: null,
  searchQuery: "",
  statusFilter: "",
  currentPage: 1,
  pageSize: 15,
  totalPages: 1,
  _abortController: null,

  async init() {
    this.container = document.getElementById("view-payments");
    if (!this.container) return;
    this.render();
    await this.loadPayments();
  },

  render() {
    this.container.innerHTML = `
      <div class="filter-bar">
        <div class="filter-left">
          <div class="search-input-wrapper">
            <span class="search-icon">🔍</span>
            <input type="text" id="payments-search-input" class="form-input search-input" placeholder="Search patient, phone, token, doctor..." />
          </div>

          <select id="payments-status-filter" class="filter-select">
            <option value="">All Payment Statuses</option>
            <option value="Pending">Pending (Unpaid)</option>
            <option value="Paid">Paid (Collected)</option>
          </select>
        </div>

        <div class="filter-right">
          <button id="payments-refresh-btn" class="btn btn-secondary btn-sm">Refresh Payments</button>
        </div>
      </div>

      <div class="card">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Token</th>
                <th>Patient Name</th>
                <th>Phone</th>
                <th>Doctor</th>
                <th>Appointment Date</th>
                <th>Amount</th>
                <th>Method</th>
                <th>Status</th>
                <th style="text-align: right;">Action</th>
              </tr>
            </thead>
            <tbody id="payments-table-tbody">
              ${renderTableSkeletons(9, 5)}
            </tbody>
          </table>
        </div>
        <div class="pagination-container">
          <div id="payments-page-info">Showing 0 of 0 payments</div>
          <div class="pagination-controls">
            <button id="payments-prev-btn" class="btn btn-secondary btn-sm" disabled>Previous</button>
            <button id="payments-next-btn" class="btn btn-secondary btn-sm" disabled>Next</button>
          </div>
        </div>
      </div>
    `;

    document.getElementById("payments-search-input")?.addEventListener(
      "input",
      debounce((e) => {
        this.searchQuery = e.target.value.trim();
        this.currentPage = 1;
        this.loadPayments();
      }, 300)
    );

    document.getElementById("payments-status-filter")?.addEventListener("change", (e) => {
      this.statusFilter = e.target.value;
      this.currentPage = 1;
      this.loadPayments();
    });

    document.getElementById("payments-refresh-btn")?.addEventListener("click", () => {
      this.loadPayments();
    });

    document.getElementById("payments-prev-btn")?.addEventListener("click", () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.loadPayments();
      }
    });

    document.getElementById("payments-next-btn")?.addEventListener("click", () => {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        this.loadPayments();
      }
    });
  },

  async loadPayments() {
    const tbody = document.getElementById("payments-table-tbody");
    if (!tbody) return;

    if (this._abortController) {
      this._abortController.abort();
    }
    this._abortController = new AbortController();

    tbody.innerHTML = renderTableSkeletons(9, 5);

    try {
      const res = await API.listPayments({
        search: this.searchQuery,
        status: this.statusFilter,
        page: this.currentPage,
        page_size: this.pageSize,
      }, { signal: this._abortController.signal });

      this.totalPages = res.total_pages || 1;
      this.currentPage = res.page || 1;

      const pageInfo = document.getElementById("payments-page-info");
      if (pageInfo) {
        pageInfo.textContent = `Showing ${res.payments.length} of ${res.total} payments (Page ${this.currentPage} of ${this.totalPages})`;
      }

      const prevBtn = document.getElementById("payments-prev-btn");
      const nextBtn = document.getElementById("payments-next-btn");
      if (prevBtn) prevBtn.disabled = this.currentPage <= 1;
      if (nextBtn) nextBtn.disabled = this.currentPage >= this.totalPages;

      if (!res.payments || res.payments.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="empty-state-cell">No payment records match filters.</td></tr>`;
        return;
      }

      tbody.innerHTML = res.payments.map((p) => {
        const id = p.token_no || p.payment_id || "-";
        const name = p.patient_name || "-";
        const phone = p.phone || "-";
        const doctor = p.doctor || "-";
        const date = p.appointment_date || "-";
        const amount = p.amount || "0";
        const method = p.payment_method || "Offline";
        const status = p.payment_status || "Pending";
        const isPaid = status.toLowerCase() === "paid";
        const invoiceUrl = API.getAppointmentInvoiceUrl(id);

        return `
          <tr>
            <td style="font-weight:600; font-family:monospace; color:var(--text-secondary);">${escapeHtml(id)}</td>
            <td style="font-weight:600;">${escapeHtml(name)}</td>
            <td>${escapeHtml(phone)}</td>
            <td>${escapeHtml(doctor)}</td>
            <td>${formatDate(date)}</td>
            <td style="font-weight:700;">${formatCurrency(amount)}</td>
            <td>${renderBadge(method)}</td>
            <td>${renderBadge(status)}</td>
            <td style="text-align: right; white-space: nowrap;">
              <button class="btn btn-secondary btn-sm view-pay-btn" data-id="${escapeHtml(id)}">
                Receipt
              </button>
              <a href="${invoiceUrl}" target="_blank" class="btn btn-outline btn-sm" title="Download PDF Invoice" style="text-decoration:none;">
                📄 Invoice
              </a>
              ${!isPaid ? `
                <button class="btn btn-primary btn-sm record-pay-modal-btn" data-id="${escapeHtml(id)}" data-amount="${escapeHtml(amount)}" data-name="${escapeHtml(name)}">
                  Collect
                </button>
              ` : `
                <span style="font-size:12px; color:#10b981; font-weight:600; margin-left: 8px;">✓ Settled</span>
              `}
            </td>
          </tr>
        `;
      }).join("");

      tbody.querySelectorAll(".view-pay-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const id = e.currentTarget.getAttribute("data-id");
          this.openPaymentReceiptModal(id);
        });
      });

      tbody.querySelectorAll(".record-pay-modal-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const id = e.currentTarget.getAttribute("data-id");
          const amt = e.currentTarget.getAttribute("data-amount");
          const name = e.currentTarget.getAttribute("data-name");
          this.openRecordPaymentModal(id, amt, name);
        });
      });
    } catch (err) {
      if (err.name === "AbortError") return;
      tbody.innerHTML = `<tr><td colspan="9" class="empty-state-cell" style="color:var(--danger,#ef4444); padding:32px 16px;">
        <div style="font-size:24px; margin-bottom:8px;">⚠️</div>
        <div style="font-weight:600; margin-bottom:6px;">Failed to load payments</div>
        <div style="font-size:12px; color:var(--text-secondary); margin-bottom:16px;">${escapeHtml(err.message || "Network request failed")}</div>
        <button id="payments-retry-btn" class="btn btn-secondary btn-sm" style="margin:0 auto;">🔄 Retry Loading</button>
      </td></tr>`;
      document.getElementById("payments-retry-btn")?.addEventListener("click", () => this.loadPayments());
      showToast(err.message || "Failed to load payments", "error");
    }
  },

  openRecordPaymentModal(identifier, defaultAmount, patientName) {
    const cleanAmt = (defaultAmount || "500").replace("₹", "").replace(",", "").trim();

    const bodyHtml = `
      <form id="record-payment-form">
        <div style="background:var(--bg-app); border:1px solid var(--border-light); border-radius:6px; padding:12px; margin-bottom:14px; font-size:13px;">
          <div><strong>Appointment Token:</strong> <code>${escapeHtml(identifier)}</code></div>
          <div><strong>Patient:</strong> ${escapeHtml(patientName || "-")}</div>
        </div>

        <div class="form-group">
          <label class="form-label">Payment Amount Collected (₹) *</label>
          <input type="number" id="pay-input-amount" class="form-input" value="${cleanAmt}" required />
        </div>

        <div class="form-group">
          <label class="form-label">Payment Method *</label>
          <select id="pay-select-method" class="form-select">
            <option value="Cash">Cash (Front Desk)</option>
            <option value="UPI">UPI (QR / GooglePay / PhonePe)</option>
            <option value="Card">Debit / Credit Card (POS Terminal)</option>
            <option value="Net Banking">Net Banking / Transfer</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">Transaction Reference / Receipt No</label>
          <input type="text" id="pay-input-ref" class="form-input" placeholder="e.g. UPI-987654 or POS-102" />
        </div>

        <div class="form-group">
          <label class="form-label">Notes (Optional)</label>
          <input type="text" id="pay-input-notes" class="form-input" placeholder="e.g. Paid in full at desk" />
        </div>
      </form>
    `;

    const footerHtml = `
      <button type="button" class="btn btn-secondary" onclick="window.Modal.close()">Cancel</button>
      <button type="button" id="submit-record-payment-btn" class="btn btn-primary">Confirm & Mark Paid</button>
    `;

    Modal.open("Record Payment Collection", bodyHtml, footerHtml);

    document.getElementById("submit-record-payment-btn")?.addEventListener("click", async () => {
      const amount = document.getElementById("pay-input-amount")?.value?.trim();
      const method = document.getElementById("pay-select-method")?.value || "Cash";
      const ref = document.getElementById("pay-input-ref")?.value?.trim() || "";
      const notes = document.getElementById("pay-input-notes")?.value?.trim() || "";

      if (!amount) {
        showToast("Amount is required", "error");
        return;
      }

      try {
        await API.recordPayment(identifier, {
          amount,
          payment_method: method,
          transaction_ref: ref,
          notes,
        });
        showToast(`Payment of ₹${amount} recorded as Paid for Token ${identifier}`, "success");
        Modal.close();
        await this.loadPayments();
      } catch (err) {
        showToast(err.message || "Failed to record payment", "error");
      }
    });
  },

  async openPaymentReceiptModal(identifier) {
    try {
      const p = await API.getPayment(identifier);
      const invoiceUrl = API.getAppointmentInvoiceUrl(identifier);

      const bodyHtml = `
        <div style="background:var(--bg-app); border:1px solid var(--border-light); border-radius:var(--radius-md); padding:16px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid var(--border-light); padding-bottom:8px;">
            <div>
              <span style="font-size:11px; text-transform:uppercase; color:var(--text-muted);">Payment Receipt</span>
              <h3 style="font-size:16px; font-weight:700; color:var(--text-main); font-family:monospace; margin:0;">
                ${escapeHtml(p.token_no || p.payment_id)}
              </h3>
            </div>
            <div>${renderBadge(p.payment_status)}</div>
          </div>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:13px;">
            <div><strong>Patient:</strong> ${escapeHtml(p.patient_name)}</div>
            <div><strong>Phone:</strong> ${escapeHtml(p.phone || "-")}</div>
            <div><strong>Consulting Doctor:</strong> ${escapeHtml(p.doctor)}</div>
            <div><strong>Appointment Date:</strong> ${formatDate(p.appointment_date)}</div>
            <div><strong>Amount:</strong> <span style="font-size:15px; font-weight:700; color:var(--primary);">${formatCurrency(p.amount)}</span></div>
            <div><strong>Payment Mode:</strong> ${escapeHtml(p.payment_method || "Offline")}</div>
            <div><strong>Booking Status:</strong> ${renderBadge(p.booking_status)}</div>
          </div>
        </div>
      `;

      const footerHtml = `
        <a href="${invoiceUrl}" target="_blank" class="btn btn-primary" style="text-decoration:none;">📄 Download PDF Invoice</a>
        <button class="btn btn-secondary" onclick="window.Modal.close()">Close</button>
      `;

      Modal.open("Payment Details", bodyHtml, footerHtml);
    } catch (e) {
      showToast(e.message || "Failed to load receipt details", "error");
    }
  },
};
