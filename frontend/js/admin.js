/**
 * SMART LIBRARY MANAGEMENT SYSTEM - LIBRARIAN & ADMIN DESK
 * Handles Top KPI Stats, ACID Checkout Desk, Inventory, Fine Waiving & DB Trigger Audit Logs.
 */

async function loadAdminDashboard() {
  loadAdminKPIs();
  loadAllCirculationLoans();
  loadAdminFinesTable();
  loadAuditLogsViewer();
  loadCategoriesDropdown();
  loadAdminRequestsList();
}

// ============================================================================
// 1. KPI STATS CARDS
// ============================================================================
async function loadAdminKPIs() {
  try {
    const stats = await apiFetch("/api/admin/stats");
    const elBooks = document.getElementById("kpi-books");
    const elCopies = document.getElementById("kpi-copies");
    const elActive = document.getElementById("kpi-active-loans");
    const elOverdue = document.getElementById("kpi-overdue-loans");
    const elFines = document.getElementById("kpi-unpaid-fines");
    const elStudents = document.getElementById("kpi-students");

    if (elBooks) elBooks.innerText = stats.total_books;
    if (elCopies) elCopies.innerText = stats.total_copies;
    if (elActive) elActive.innerText = stats.active_loans;
    if (elOverdue) elOverdue.innerText = stats.overdue_loans;
    if (elFines) elFines.innerText = `$${stats.unpaid_fines.toFixed(2)}`;
    if (elStudents) elStudents.innerText = stats.total_students;
  } catch (err) {
    console.error("Failed to load admin stats:", err);
  }
}

// ============================================================================
// 2. ACID CHECKOUT DESK (ISSUE BOOK TRANSACTION)
// ============================================================================
async function handleIssueBook(e) {
  e.preventDefault();
  const cardInput = document.getElementById("issue-card-no");
  const barcodeInput = document.getElementById("issue-barcode");
  const daysInput = document.getElementById("issue-days");
  const btn = document.getElementById("btn-issue-submit");

  const library_card_no = cardInput.value.trim();
  const barcode = barcodeInput.value.trim();
  const due_days = parseInt(daysInput.value) || 14;

  btn.disabled = true;
  btn.innerText = "Executing ACID Transaction...";

  try {
    const res = await apiFetch("/api/loans/issue", {
      method: "POST",
      body: JSON.stringify({ library_card_no, barcode, due_days })
    });

    showToast(`✓ ${res.message} (Due: ${res.due_date.substring(0, 10)})`, "success");
    cardInput.value = "";
    barcodeInput.value = "";
    loadAdminKPIs();
    loadAllCirculationLoans();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    btn.disabled = false;
    btn.innerText = "Execute Issue Transaction";
  }
}

// ============================================================================
// 3. DESK RETURNS SCANNER
// ============================================================================
async function handleReturnByBarcode(e) {
  e.preventDefault();
  const barcodeInput = document.getElementById("return-barcode-input");
  const barcode = barcodeInput.value.trim();

  try {
    const res = await apiFetch("/api/loans/return-by-barcode", {
      method: "POST",
      body: JSON.stringify({ barcode })
    });

    showToast(res.message, "success");
    if (res.fine_generated) showToast(res.fine_generated, "warning");
    if (res.inventory_status) showToast(res.inventory_status, "info");

    barcodeInput.value = "";
    loadAdminKPIs();
    loadAllCirculationLoans();
    loadAuditLogsViewer();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ============================================================================
// 4. CIRCULATION LOANS VIEWER
// ============================================================================
async function loadAllCirculationLoans() {
  const tbody = document.getElementById("admin-loans-table-body");
  if (!tbody) return;

  try {
    const loans = await apiFetch("/api/loans/all");
    if (loans.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px;">No active loans found.</td></tr>`;
      return;
    }

    tbody.innerHTML = loans.map(l => {
      const isReturned = !!l.return_date;
      const isOverdue = l.display_status === "OVERDUE";

      let statusBadge = "";
      if (isReturned) {
        statusBadge = `<span class="status-badge badge-returned">Returned</span>`;
      } else if (isOverdue) {
        statusBadge = `<span class="status-badge badge-overdue">⚠ OVERDUE (${l.days_overdue}d)</span>`;
      } else {
        statusBadge = `<span class="status-badge badge-active">On Loan</span>`;
      }

      return `
        <tr>
          <td>
            <strong>${l.patron_name}</strong>
            <div style="font-size: 0.74rem; color: var(--text-light); font-family: monospace;">${l.library_card_no}</div>
          </td>
          <td><strong>${l.book_title}</strong></td>
          <td><code>${l.barcode}</code></td>
          <td>${l.shelf_location}</td>
          <td>${l.issue_date.substring(0, 10)}</td>
          <td><strong style="color: ${isOverdue ? 'var(--danger)' : 'var(--text-main)'};">${l.due_date.substring(0, 10)}</strong></td>
          <td>${statusBadge}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ============================================================================
// 5. FINES WAIVER DESK (TRIGGERS DB TRIGGER 3A)
// ============================================================================
async function loadAdminFinesTable() {
  const tbody = document.getElementById("admin-fines-table-body");
  if (!tbody) return;

  try {
    const fines = await apiFetch("/api/fines/all");
    if (fines.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 20px;">No fines in database.</td></tr>`;
      return;
    }

    tbody.innerHTML = fines.map(f => {
      let badge = "";
      let action = "";

      if (f.payment_status === "unpaid") {
        badge = `<span class="status-badge badge-unpaid">Unpaid</span>`;
        action = `
          <button class="btn btn-secondary btn-sm" onclick="waiveFineAdmin(${f.fine_id})">
            ⚖ Waive Fine (Trigger Audit)
          </button>
        `;
      } else if (f.payment_status === "paid") {
        badge = `<span class="status-badge badge-paid">Paid</span>`;
        action = `<span style="font-size: 0.78rem; color: var(--text-light);">${f.paid_date ? f.paid_date.substring(0, 10) : 'Paid'}</span>`;
      } else {
        badge = `<span class="status-badge badge-waived">Waived</span>`;
        action = `<span style="font-size: 0.78rem; color: var(--accent-gold-dark); font-weight: 700;">Audited in DB</span>`;
      }

      return `
        <tr>
          <td>
            <strong>${f.patron_name}</strong>
            <div style="font-size: 0.74rem; color: var(--text-light);">${f.library_card_no}</div>
          </td>
          <td>${f.book_title}</td>
          <td><strong style="color: var(--danger);">$${f.amount.toFixed(2)}</strong></td>
          <td>${badge}</td>
          <td>${f.due_date ? f.due_date.substring(0, 10) : 'N/A'}</td>
          <td>${action}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function waiveFineAdmin(fineId) {
  if (!confirm(`Confirm waiving fine #${fineId}? This will automatically invoke database Trigger 3A (trg_fine_waived_audit) to record the transaction.`)) {
    return;
  }

  try {
    const res = await apiFetch(`/api/fines/${fineId}/waive`, { method: "POST" });
    showToast(res.message, "success");
    if (res.audit_recorded) {
      showToast("Trigger 3A: Audit log entry automatically inserted into audit_logs table!", "info");
    }
    loadAdminFinesTable();
    loadAdminKPIs();
    loadAuditLogsViewer();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ============================================================================
// 6. INVENTORY: ADD BOOK & PHYSICAL COPY
// ============================================================================
async function loadCategoriesDropdown() {
  const sel = document.getElementById("new-book-category");
  if (!sel || sel.children.length > 1) return;

  try {
    const cats = await apiFetch("/api/books/categories");
    cats.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.category_id;
      opt.innerText = c.category_name;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.error("Failed to load categories for dropdown:", err);
  }
}

async function handleAddNewBook(e) {
  e.preventDefault();
  const isbn = document.getElementById("new-book-isbn").value.trim();
  const title = document.getElementById("new-book-title").value.trim();
  const subtitle = document.getElementById("new-book-subtitle").value.trim() || null;
  const authorsStr = document.getElementById("new-book-authors").value.trim();
  const publisher_name = document.getElementById("new-book-publisher").value.trim() || null;
  const category_id = parseInt(document.getElementById("new-book-category").value);
  const publication_year = parseInt(document.getElementById("new-book-year").value) || null;
  const edition = document.getElementById("new-book-edition").value.trim() || "1st Edition";
  const pages = parseInt(document.getElementById("new-book-pages").value) || null;
  const description = document.getElementById("new-book-description").value.trim() || null;
  const cover_image_url = document.getElementById("new-book-cover").value.trim() || null;

  const authors = authorsStr.split(",").map(a => a.trim()).filter(Boolean);

  try {
    const res = await apiFetch("/api/books", {
      method: "POST",
      body: JSON.stringify({
        isbn, title, subtitle, authors, publisher_name, category_id,
        publication_year, edition, pages, description, cover_image_url
      })
    });

    showToast(res.message, "success");
    document.getElementById("form-add-book").reset();
    loadAdminKPIs();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleAddPhysicalCopy(e) {
  e.preventDefault();
  const bookId = parseInt(document.getElementById("copy-book-id").value);
  const barcode = document.getElementById("copy-barcode").value.trim();
  const shelf_location = document.getElementById("copy-shelf").value.trim();
  const condition = document.getElementById("copy-condition").value;

  try {
    const res = await apiFetch(`/api/books/${bookId}/copies`, {
      method: "POST",
      body: JSON.stringify({ barcode, shelf_location, condition })
    });

    showToast(res.message, "success");
    document.getElementById("form-add-copy").reset();
    loadAdminKPIs();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ============================================================================
// 7. BOOK REQUEST APPROVALS
// ============================================================================
async function loadAdminRequestsList() {
  const container = document.getElementById("admin-requests-container");
  if (!container) return;

  try {
    const requests = await apiFetch("/api/requests");
    container.innerHTML = requests.map(r => {
      return `
        <div class="request-card" style="padding: 14px 18px;">
          <div class="request-details">
            <h4 class="request-title" style="font-size: 0.95rem;">${r.title}</h4>
            <div class="request-meta">
              <span>Author: ${r.author}</span>
              <span>Votes: <strong>${r.vote_count}</strong></span>
              <span>Status: <strong>${r.status.toUpperCase()}</strong></span>
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            ${r.status === 'open' ? `
              <button class="btn btn-primary btn-sm" onclick="updateRequestStatus(${r.request_id}, 'approved')">Approve</button>
            ` : ''}
            ${r.status !== 'purchased' ? `
              <button class="btn btn-success btn-sm" onclick="updateRequestStatus(${r.request_id}, 'purchased')">Mark Purchased</button>
            ` : '<span style="font-size: 0.8rem; color: var(--success); font-weight: 700;">Purchased ✓</span>'}
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("Failed to load requests:", err);
  }
}

async function updateRequestStatus(reqId, status) {
  try {
    const res = await apiFetch(`/api/requests/${reqId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    });
    showToast(res.message, "success");
    loadAdminRequestsList();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ============================================================================
// 8. TAMPER-PROOF DATABASE TRIGGER AUDIT LOG VIEWER
// ============================================================================
async function loadAuditLogsViewer() {
  const tbody = document.getElementById("audit-logs-table-body");
  if (!tbody) return;

  const filterSelect = document.getElementById("audit-filter-table");
  const targetTable = filterSelect ? filterSelect.value : "";

  let url = "/api/admin/audit-logs";
  if (targetTable) url += `?target_table=${targetTable}`;

  try {
    const logs = await apiFetch(url);
    if (logs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px;">No audit log records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = logs.map(l => {
      let actionBadge = `<span class="status-badge badge-active">${l.action_type}</span>`;
      if (l.action_type === "FINE_WAIVED") {
        actionBadge = `<span class="status-badge badge-waived">FINE_WAIVED</span>`;
      } else if (l.action_type === "BOOK_DELETED") {
        actionBadge = `<span class="status-badge badge-unpaid">BOOK_DELETED</span>`;
      }

      const oldVal = l.old_value ? `<div class="code-diff code-diff-old">${l.old_value}</div>` : '<em style="color:var(--text-light)">null</em>';
      const newVal = l.new_value ? `<div class="code-diff code-diff-new">${l.new_value}</div>` : '<em style="color:var(--text-light)">null</em>';

      return `
        <tr>
          <td><strong>#${l.log_id}</strong></td>
          <td>${l.timestamp}</td>
          <td>${actionBadge}</td>
          <td><code>${l.target_table}</code> (ID: ${l.target_record_id})</td>
          <td>${l.actor_name || 'System Trigger'}</td>
          <td>${oldVal}</td>
          <td>${newVal}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

