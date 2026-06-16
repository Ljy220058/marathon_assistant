// 用户认证状态管理。
// 存储位置：localStorage["journal-ink-auth-v1"] = {token, user_id, display_name, email}
// 供 apiClient.js 自动携带 X-Marathon-API-Key，供 JournalLayout header 展示用户信息。

(function () {
  const AUTH_KEY = "journal-ink-auth-v1";

  function _escape(str) {
    return String(str || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  const auth = {
    get() {
      try { return JSON.parse(localStorage.getItem(AUTH_KEY) || "null"); } catch { return null; }
    },
    set(data) {
      try { localStorage.setItem(AUTH_KEY, JSON.stringify(data)); } catch {}
    },
    clear() {
      try { localStorage.removeItem(AUTH_KEY); } catch {}
    },
    token() {
      return this.get()?.token || "";
    },
    isLoggedIn() {
      return !!this.token();
    },
  };

  // 渲染 header 右侧用户状态区域
  function renderAuthHeader() {
    const el = document.querySelector("[data-auth-header]");
    if (!el) return;
    const user = auth.get();
    if (user && user.token) {
      const name = user.display_name || user.email || "用户";
      el.innerHTML =
        `<span class="journal-auth-name">${_escape(name)}</span>` +
        `<button class="journal-pill" id="logoutBtn" type="button">退出</button>`;
      document.getElementById("logoutBtn")?.addEventListener("click", () => {
        auth.clear();
        window.location.href = "/login";
      });
    } else {
      el.innerHTML = `<a class="journal-pill is-action" href="/login">登录</a>`;
    }
  }

  window.__auth = auth;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderAuthHeader, { once: true });
  } else {
    renderAuthHeader();
  }
})();
