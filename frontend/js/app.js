/**
 * SMART LIBRARY MANAGEMENT SYSTEM - MAIN APP LOGIC
 * Manages Patron Dashboard, Circulation, Fines, Room Reservations, and Book Requests.
 */

let currentUser = null;
let currentAppTab = "catalog";

document.addEventListener("DOMContentLoaded", async () => {
  if (!Auth.isAuthenticated()) {
    window.location.href = "login.html";
    return;
  }

  currentUser = Auth.getUser();
  renderUserProfile();

  // Admin visibility logic
  if (currentUser.role === "admin") {
    document.querySelectorAll(".admin-only").forEach(el => el.style.display = "flex");
  } else {
    document.querySelectorAll(".admin-only").forEach(el => el.style.display = "none");
  }

  // Check URL params for active tab
  const params = new URLSearchParams(window.location.search);
  const requestedTab = params.get("tab") || "catalog";
  switchNavTab(requestedTab);
});

function renderUserProfile() {
  if (!currentUser) return;
  const nameEl = document.getElementById("profile-name");
  const cardEl = document.getElementById("profile-card");
  const roleEl = document.getElementById("profile-role");
  const avatarEl = document.getElementById("profile-avatar");

  if (nameEl) nameEl.innerText = currentUser.full_name;
  if (cardEl) cardEl.innerText = `Card: ${currentUser.library_card_no}`;
  if (roleEl) {
    roleEl.innerText = currentUser.role.toUpperCase();
    roleEl.className = `user-role-badge role-${currentUser.role}`;
  }
  if (avatarEl) {
    const initials = currentUser.full_name
      .split(" ")
      .map(n => n[0])
      .join("")
      .substring(0, 2)
      .toUpperCase();
    avatarEl.innerText = initials;
  }
}

function handleLogout() {
  Auth.clear();
  showToast("Logged out successfully.", "info");
  setTimeout(() => {
    window.location.href = "login.html";
  }, 500);
}

function toggleMobileSidebar() {
  const sidebar = document.getElementById("app-sidebar");
  sidebar.classList.toggle("mobile-open");
}

function switchNavTab(tabName) {
  currentAppTab = tabName;

  // Update sidebar links
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.dataset.tab === tabName) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Switch content panes
  document.querySelectorAll(".tab-content").forEach(pane => {
    pane.classList.remove("active");
  });

  const activePane = document.getElementById(`tab-${tabName}`);
  if (activePane) {
    activePane.classList.add("active");
  }

  // Update topbar title
  const titles = {
    catalog: "Library Catalog & Discovery",
    loans: "My Borrowed Books & Active Circulation",
    fines: "Fines & Waitlist Queue",
    rooms: "Study Room Booking",
    requests: "Book Acquisition Voting Board",
    admin: "Librarian Administration & DB Triggers"
  };
  const titleEl = document.getElementById("viewport-title");
  if (titleEl && titles[tabName]) {
    titleEl.innerText = titles[tabName];
  }

  // Close mobile sidebar if open
  const sidebar = document.getElementById("app-sidebar");
  if (sidebar) sidebar.classList.remove("mobile-open");

  // Load relevant tab data
  if (tabName === "catalog") {
    loadDashboardCatalog();
  } else if (tabName === "loans") {
    loadMyLoans();
  } else if (tabName === "fines") {
    loadFinesAndWaitlist();
  } else if (tabName === "rooms") {
    loadStudyRoomsSection();
  } else if (tabName === "requests") {
    loadBookRequests();
  } else if (tabName === "admin" && currentUser.role === "admin") {
    if (typeof loadAdminDashboard === "function") {
      loadAdminDashboard();
    }
  }
}

// ============================================================================
// 1. CATALOG TAB
// ============================================================================
let dashCategory = null;
let dashSort = "title";
let dashDebounce = null;

async function loadDashboardCatalog() {
  const grid = document.getElementById("dash-books-grid");
  if (!grid) return;

  const searchInput = document.getElementById("dash-catalog-search");
  const searchVal = searchInput ? searchInput.value.trim() : "";
  const availToggle = document.getElementById("dash-avail-toggle");
  const availOnly = availToggle ? availToggle.checked : false;

  let url = `/api/books?sort_by=${dashSort}`;
  if (dashCategory) url += `&category_id=${dashCategory}`;
  if (availOnly) url += `&available_only=true`;
  if (searchVal) url += `&search=${encodeURIComponent(searchVal)}`;

  try {
    const books = await apiFetch(url);
    if (books.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 40px; background-color: var(--bg-surface); border: 1px dashed var(--border); border-radius: var(--radius-lg);">
          <div style="font-size: 2rem;">🔍</div>
          <h4>No matching titles found</h4>
        </div>
      `;
      return;
    }

    grid.innerHTML = books.map(book => {
      const isAvail = book.available_copies > 0;
      const availBadge = isAvail
        ? `<span class="badge-availability badge-available">✓ ${book.available_copies} of ${book.total_copies} Available</span>`
        : `<span class="badge-availability badge-unavailable">✕ 0 of ${book.total_copies} Available</span>`;

      return `
        <div class="book-card" onclick="openBookModal(${book.book_id})">
          <div class="book-cover-container">
            <img src="${book.cover_image_url || 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400&q=80'}" class="book-cover-img" loading="lazy">
            ${availBadge}
            <span class="badge-category">${book.category_name}</span>
          </div>
          <div class="book-content">
            <h3 class="book-title">${book.title}</h3>
            <div class="book-authors">By ${book.authors}</div>
            <p class="book-desc">${book.description || 'No description available.'}</p>
            <div class="book-footer">
              <span class="book-isbn">ISBN: ${book.isbn}</span>
              <button class="btn-view-details" onclick="event.stopPropagation(); openBookModal(${book.book_id})">
                Details & Copies →
              </button>
            </div>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    showToast("Error loading catalog books", "error");
  }
}

function handleDashSearch() {
  clearTimeout(dashDebounce);
  dashDebounce = setTimeout(loadDashboardCatalog, 300);
}

// ============================================================================
// 2. MY BORROWED BOOKS TAB (WITH 1-CLICK RETURN TRIGGER DEMO)
// ============================================================================
async function loadMyLoans() {
  const tbody = document.getElementById("my-loans-table-body");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px;">Loading active loans...</td></tr>`;

  try {
    const loans = await apiFetch("/api/loans/my-loans");
    if (loans.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align: center; padding: 36px; color: var(--text-muted);">
            You have no active or historical loans on your library card.
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = loans.map(l => {
      const isReturned = !!l.return_date;
      const isOverdue = !isReturned && l.loan_state === "OVERDUE";

      let statusBadge = "";
      if (isReturned) {
        statusBadge = `<span class="status-badge badge-returned">Returned</span>`;
      } else if (isOverdue) {
        statusBadge = `<span class="status-badge badge-overdue">⚠ OVERDUE (${l.days_overdue} days)</span>`;
      } else {
        statusBadge = `<span class="status-badge badge-active">On Loan (${l.days_remaining} days left)</span>`;
      }

      let actionBtn = "";
      if (!isReturned) {
        actionBtn = `
          <button class="btn btn-primary btn-sm" onclick="returnLoan(${l.loan_id})">
            ↩ Return Book (Trigger Demo)
          </button>
        `;
      } else {
        actionBtn = `<span style="font-size: 0.78rem; color: var(--text-light);">Completed</span>`;
      }

      return `
        <tr>
          <td>
            <strong>${l.title}</strong>
            <div style="font-size: 0.75rem; color: var(--text-light); font-family: monospace;">ISBN: ${l.isbn}</div>
          </td>
          <td><code>${l.barcode}</code></td>
          <td>${l.shelf_location}</td>
          <td>${l.issue_date.substring(0, 10)}</td>
          <td><strong style="color: ${isOverdue ? 'var(--danger)' : 'var(--text-main)'};">${l.due_date.substring(0, 10)}</strong></td>
          <td>${statusBadge}</td>
          <td>${actionBtn}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function returnLoan(loanId) {
  if (!confirm("Confirm returning this book? This will execute database Trigger 1 (FIFO Waitlist reservation) and Trigger 2 (Automatic Overdue Fine calculation).")) {
    return;
  }

  try {
    const res = await apiFetch(`/api/loans/return/${loanId}`, { method: "POST" });
    showToast(res.message, "success");
    if (res.fine_generated) {
      showToast(res.fine_generated, "warning");
    }
    if (res.inventory_status) {
      showToast(res.inventory_status, "info");
    }
    loadMyLoans();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ============================================================================
// 3. FINES & WAITLIST TAB
// ============================================================================
async function loadFinesAndWaitlist() {
  loadMyFines();
  loadMyWaitlists();
}

async function loadMyFines() {
  const tbody = document.getElementById("my-fines-table-body");
  if (!tbody) return;

  try {
    const fines = await apiFetch("/api/fines/my-fines");
    if (fines.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-muted);">No fines recorded on your account. Clear record!</td></tr>`;
      return;
    }

    tbody.innerHTML = fines.map(f => {
      let badge = "";
      let action = "";

      if (f.payment_status === "unpaid") {
        badge = `<span class="status-badge badge-unpaid">Unpaid</span>`;
        action = `<button class="btn btn-danger btn-sm" onclick="payFine(${f.fine_id}, ${f.amount})">💳 Pay $${f.amount.toFixed(2)}</button>`;
      } else if (f.payment_status === "paid") {
        badge = `<span class="status-badge badge-paid">Paid</span>`;
        action = `<span style="font-size: 0.78rem; color: var(--text-light);">${f.paid_date ? f.paid_date.substring(0, 10) : 'Paid'}</span>`;
      } else {
        badge = `<span class="status-badge badge-waived">Waived by Admin</span>`;
        action = `<span style="font-size: 0.78rem; color: #9333ea; font-weight: 600;">Waived</span>`;
      }

      return `
        <tr>
          <td><strong>${f.book_title}</strong></td>
          <td><strong style="color: var(--danger);">$${f.amount.toFixed(2)}</strong></td>
          <td>${f.overdue_days ? `${f.overdue_days} days` : 'N/A'}</td>
          <td>${badge}</td>
          <td>${action}</td>
        </tr>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function payFine(fineId, amount) {
  if (!confirm(`Confirm paying $${amount.toFixed(2)} overdue fine?`)) return;
  try {
    const res = await apiFetch(`/api/fines/${fineId}/pay`, { method: "POST" });
    showToast(res.message, "success");
    loadMyFines();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadMyWaitlists() {
  const container = document.getElementById("my-waitlist-container");
  if (!container) return;

  try {
    const waitlists = await apiFetch("/api/waitlist/my-waitlists");
    if (waitlists.length === 0) {
      container.innerHTML = `<div style="padding: 24px; color: var(--text-muted); text-align: center;">You have no active book reservations in the waitlist queue.</div>`;
      return;
    }

    container.innerHTML = waitlists.map(w => {
      const isNotified = w.status === "notified";
      return `
        <div class="request-card" style="border-left: 4px solid ${isNotified ? 'var(--success)' : 'var(--accent-gold)'};">
          <img src="${w.cover_image_url || 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=400&q=80'}" style="width: 50px; height: 70px; object-fit: cover; border-radius: var(--radius-sm);">
          <div class="request-details">
            <h4 class="request-title">${w.book_title}</h4>
            <div class="request-meta">
              <span>Requested on: ${w.requested_at.substring(0, 10)}</span>
              <span>ISBN: ${w.isbn}</span>
            </div>
          </div>
          <div>
            ${isNotified
          ? `<span class="status-badge badge-notified" style="font-size: 0.85rem; padding: 6px 14px;">🎉 Ready for Pickup! A copy is reserved for you.</span>`
          : `<span class="status-badge badge-waiting" style="font-size: 0.85rem; padding: 6px 14px;">Queue Position: #${w.current_queue_position}</span>`
        }
          </div>
          <button class="btn btn-secondary btn-sm" onclick="cancelWaitlist(${w.waitlist_id})">Cancel</button>
        </div>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function cancelWaitlist(id) {
  if (!confirm("Cancel your place in the waitlist queue?")) return;
  try {
    const res = await apiFetch(`/api/waitlist/${id}`, { method: "DELETE" });
    showToast(res.message, "info");
    loadMyWaitlists();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// ============================================================================
// 4. STUDY ROOM BOOKING (CONFLICT-FREE SLOT ENGINE)
// ============================================================================
const TIME_SLOTS = [
  { start: "09:00:00", end: "10:00:00", label: "09:00 - 10:00 AM" },
  { start: "10:00:00", end: "11:00:00", label: "10:00 - 11:00 AM" },
  { start: "11:00:00", end: "12:00:00", label: "11:00 - 12:00 PM" },
  { start: "12:00:00", end: "13:00:00", label: "12:00 - 01:00 PM" },
  { start: "13:00:00", end: "14:00:00", label: "01:00 - 02:00 PM" },
  { start: "14:00:00", end: "15:00:00", label: "02:00 - 03:00 PM" },
  { start: "15:00:00", end: "16:00:00", label: "03:00 - 04:00 PM" },
  { start: "16:00:00", end: "17:00:00", label: "04:00 - 05:00 PM" },
  { start: "17:00:00", end: "18:00:00", label: "05:00 - 06:00 PM" }
];

async function loadStudyRoomsSection() {
  const dateInput = document.getElementById("room-booking-date");
  if (!dateInput.value) {
    const today = new Date().toISOString().split("T")[0];
    dateInput.value = today;
  }

  const selectedDate = dateInput.value;
  const container = document.getElementById("study-rooms-container");
  if (!container) return;

  container.innerHTML = `<div style="text-align: center; padding: 40px;">Checking room schedule...</div>`;

  try {
    const [rooms, bookings] = await Promise.all([
      apiFetch("/api/rooms"),
      apiFetch(`/api/rooms/bookings?date_str=${selectedDate}`)
    ]);

    container.innerHTML = rooms.map(room => {
      // Find bookings for this room
      const roomBookings = bookings.filter(b => b.room_id === room.room_id);

      const slotsHtml = TIME_SLOTS.map(slot => {
        // Interval conflict check: start_time < slot.end AND end_time > slot.start
        const isConflict = roomBookings.some(b => {
          return b.start_time < slot.end && b.end_time > slot.start;
        });

        if (isConflict) {
          const booked = roomBookings.find(b => b.start_time < slot.end && b.end_time > slot.start);
          return `
            <div class="slot-btn slot-booked" title="Reserved by ${booked ? booked.booked_by_name : 'Student'}">
              🔒 ${slot.label} (Booked)
            </div>
          `;
        } else {
          return `
            <div class="slot-btn slot-available" onclick="bookRoomSlot(${room.room_id}, '${room.room_name}', '${selectedDate}', '${slot.start}', '${slot.end}')">
              ✓ ${slot.label}
            </div>
          `;
        }
      }).join("");

      return `
        <div class="room-card">
          <div class="room-header">
            <h3 class="room-title">${room.room_name}</h3>
            <span class="amenity-chip" style="font-weight: 700;">Cap: ${room.capacity} Persons</span>
          </div>
          <div class="room-amenities">
            ${room.has_whiteboard ? '<span class="amenity-chip">🖊️ Whiteboard</span>' : ''}
            ${room.has_power_outlets ? '<span class="amenity-chip">⚡ Power Outlets</span>' : ''}
            <span class="amenity-chip">📶 Wi-Fi 6</span>
          </div>
          <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted); margin-bottom: 8px;">
            Available Time Slots (Click green slot to reserve):
          </div>
          <div class="slots-grid">
            ${slotsHtml}
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function bookRoomSlot(roomId, roomName, dateStr, startTime, endTime) {
  if (!confirm(`Confirm booking ${roomName} for ${dateStr} between ${startTime.substring(0, 5)} and ${endTime.substring(0, 5)}?`)) {
    return;
  }

  try {
    const res = await apiFetch("/api/rooms/book", {
      method: "POST",
      body: JSON.stringify({
        room_id: roomId,
        booking_date: dateStr,
        start_time: startTime,
        end_time: endTime
      })
    });
    showToast(res.message, "success");
    loadStudyRoomsSection();
  } catch (err) {
    showToast(err.detail || err.message, "error");
  }
}

// ============================================================================
// 5. CROWDSOURCED BOOK REQUESTS (UPVOTE BOARD)
// ============================================================================
async function loadBookRequests() {
  const container = document.getElementById("book-requests-container");
  if (!container) return;

  try {
    const requests = await apiFetch("/api/requests");
    if (requests.length === 0) {
      container.innerHTML = `<div style="text-align: center; padding: 40px; color: var(--text-muted);">No book requests submitted yet. Be the first to suggest a title!</div>`;
      return;
    }

    container.innerHTML = requests.map(r => {
      let statusBadge = "";
      if (r.status === "open") statusBadge = `<span class="status-badge badge-active">Open for Voting</span>`;
      else if (r.status === "approved") statusBadge = `<span class="status-badge badge-notified">Approved for Purchase</span>`;
      else statusBadge = `<span class="status-badge badge-paid">Purchased & Cataloged</span>`;

      return `
        <div class="request-card">
          <div class="vote-action-col">
            <button class="btn-upvote ${r.has_voted ? 'voted' : ''}" onclick="toggleVote(${r.request_id})">
              <span style="font-size: 1.1rem;">▲</span>
              <span class="vote-count" id="vote-count-${r.request_id}">${r.vote_count}</span>
            </button>
          </div>
          <div class="request-details">
            <h4 class="request-title">${r.title}</h4>
            <div class="request-meta">
              <span>Author: <strong>${r.author}</strong></span>
              ${r.isbn ? `<span>ISBN: <code>${r.isbn}</code></span>` : ''}
              <span>Suggested by: ${r.requester_name}</span>
              ${r.estimated_price ? `<span>Est. Price: $${r.estimated_price.toFixed(2)}</span>` : ''}
            </div>
          </div>
          <div>
            ${statusBadge}
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function toggleVote(requestId) {
  try {
    const res = await apiFetch(`/api/requests/${requestId}/vote`, { method: "POST" });
    showToast(res.message, "info");
    const countEl = document.getElementById(`vote-count-${requestId}`);
    if (countEl) countEl.innerText = res.total_votes;
    loadBookRequests();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function openCreateRequestModal() {
  document.getElementById("modal-request-book").classList.add("active");
}

function closeCreateRequestModal() {
  document.getElementById("modal-request-book").classList.remove("active");
}

async function submitBookRequest(e) {
  e.preventDefault();
  const title = document.getElementById("req-title").value.trim();
  const author = document.getElementById("req-author").value.trim();
  const isbn = document.getElementById("req-isbn").value.trim();
  const price = parseFloat(document.getElementById("req-price").value) || null;

  try {
    const res = await apiFetch("/api/requests", {
      method: "POST",
      body: JSON.stringify({ title, author, isbn, estimated_price: price })
    });
    showToast(res.message, "success");
    closeCreateRequestModal();
    loadBookRequests();
  } catch (err) {
    showToast(err.message, "error");
  }
}

