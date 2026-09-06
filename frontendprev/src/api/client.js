// Use Vite's same-origin development proxy by default. This also works in
// embedded browsers that block direct requests to localhost port 8000.
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
const tokenKey = "pulse_token";

function headers() {
  const token = localStorage.getItem(tokenKey);
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request(path, options = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { ...headers(), ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) logout();
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.status === 204 ? null : response.json();
}

export async function login(email, password) {
  const data = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  localStorage.setItem(tokenKey, data.access_token);
  return data;
}

export function register(email, password) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout() {
  localStorage.removeItem(tokenKey);
}

export function isAuthed() {
  return Boolean(localStorage.getItem(tokenKey));
}

export function getStocks() {
  return request("/stocks");
}

export function getQuote(symbol, refresh = false) {
  return request(
    `/stocks/${encodeURIComponent(symbol)}/quote${refresh ? "?refresh=true" : ""}`,
  );
}

export function getHistory(symbol, limit = 100) {
  return request(
    `/stocks/${encodeURIComponent(symbol)}/history?limit=${limit}`,
  );
}

export function createStock(symbol, name, exchange = null) {
  return request("/stocks", {
    method: "POST",
    body: JSON.stringify({ symbol, name: name || null, exchange: exchange || null }),
  });
}

export function getDefaultWatchlist() {
  return request("/watchlists/default");
}

export function getOverview(id) {
  return request(`/watchlists/${id}/overview`);
}

export function addToWatchlist(id, symbol) {
  return request(`/watchlists/${id}/stocks`, {
    method: "POST",
    body: JSON.stringify({ symbol }),
  });
}

export function removeFromWatchlist(id, symbol) {
  return request(`/watchlists/${id}/stocks/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
  });
}

export function markSeen(symbol) {
  return request(`/changes/${encodeURIComponent(symbol)}/mark-seen`, {
    method: "POST",
  });
}

export function refreshWatchlist(id) {
  return request(`/watchlists/${id}/refresh`, { method: "POST" });
}

export function askAI(question) {
  return request("/ai/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
