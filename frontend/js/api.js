/**
 * SMART LIBRARY MANAGEMENT SYSTEM - API & CLIENT UTILITIES
 * Centralized API client wrapper with JWT token handling, toast alerts & theme management.
 */

const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1")
  ? window.location.origin
  : "http://localhost:8000";

const Auth = {
  getToken() {
    return localStorage.getItem("lib_token");
  },
  setToken(token) {
    localStorage.setItem("lib_token", token);
  },
  getUser() {
    const raw = localStorage.getItem("lib_user");
    return raw ? JSON.parse(raw) : null;
  },
  setUser(user) {
    localStorage.setItem("lib_user", JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem("lib_token");
    localStorage.removeItem("lib_user");
  },
  isAuthenticated() {
    return !!this.getToken();
  },
  isAdmin() {
    const user = this.getUser();
    return user && user.role === "admin";
  }
};

/**
 * Enhanced fetch wrapper with automatic JWT authorization header injection.
 */
async function apiFetch(endpoint, options = {}) {
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  const token = Auth.getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers
  };

  try {
    const response = await fetch(url, config);

    // Handle 401 Unauthorized
    if (response.status === 401) {
      Auth.clear();
      if (!window.location.pathname.includes("login.html") && !window.location.pathname.includes("index.html")) {
        window.location.href = "login.html";
      }
      const err = await response.json().catch(() => ({ detail: "Unauthorized" }));
      throw new Error(err.detail || "Session expired. Please log in again.");
    }

    // Try parsing JSON
    let data;
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const errorMsg = data && data.detail ? data.detail : `Request failed with status ${response.status}`;
      throw new Error(errorMsg);
    }

    return data;
  } catch (error) {
    console.error("API Error:", error);
    throw error;
  }
}

/**
 * Toast Notification System
 */
function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  
  const icon = type === "success" ? "✓" : type === "error" ? "✕" : type === "warning" ? "⚠" : "ℹ";
  toast.innerHTML = `<span style="font-weight: 700;">${icon}</span> <span>${message}</span>`;
  
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/**
 * Dark / Light Theme Toggle Management
 */
function initTheme() {
  const savedTheme = localStorage.getItem("lib_theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeButtonText(savedTheme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const newTheme = current === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("lib_theme", newTheme);
  updateThemeButtonText(newTheme);
}

function updateThemeButtonText(theme) {
  const btn = document.getElementById("theme-toggle-btn");
  if (btn) {
    btn.innerHTML = theme === "dark" ? "☀️ Light Mode" : "🌙 Dark Mode";
  }
}

// Auto-initialize theme on load
document.addEventListener("DOMContentLoaded", initTheme);

