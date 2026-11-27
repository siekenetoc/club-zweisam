import "./style.css";

import Alpine from "alpinejs";
import htmx from "htmx.org";

window.htmx = htmx;
window.Alpine = Alpine;

Alpine.data("challengeTimer", (startedAt, durationMinutes) => ({
  remaining: "–",
  finished: false,
  intervalId: null,
  init() {
    const end = new Date(startedAt).getTime() + durationMinutes * 60000;
    const tick = () => {
      const diff = end - Date.now();
      this.finished = diff <= 0;
      const remaining = Math.max(0, diff);
      const minutes = Math.floor(remaining / 60000);
      const seconds = Math.floor((remaining % 60000) / 1000);
      this.remaining = `${minutes}:${String(seconds).padStart(2, "0")}`;
    };
    tick();
    this.intervalId = setInterval(tick, 1000);
  },
  destroy() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  },
}));

Alpine.start();

(function () {
  const shield = document.getElementById("privacy-shield");
  if (!shield) {
    return;
  }

  const SALT_KEY = "czShieldSalt";
  const HASH_KEY = "czShieldHash";
  const authenticated = document.body.dataset.authenticated === "1";

  const setupBox = document.getElementById("shield-setup");
  const setupPin = document.getElementById("shield-setup-pin");
  const setupConfirm = document.getElementById("shield-setup-confirm");
  const setupSave = document.getElementById("shield-setup-save");
  const setupError = document.getElementById("shield-setup-error");
  const unlockBox = document.getElementById("shield-unlock");
  const unlockPin = document.getElementById("shield-pin-input");
  const unlockButton = document.getElementById("shield-unlock-button");
  const unlockError = document.getElementById("shield-unlock-error");
  const activateButton = document.getElementById("shield-activate");

  const settingsPin = document.getElementById("shield-settings-pin");
  const settingsConfirm = document.getElementById("shield-settings-confirm");
  const settingsSave = document.getElementById("shield-settings-save");
  const settingsStatus = document.getElementById("shield-settings-status");

  let active = false;
  let previousTitle = document.title;
  let syncTimer = null;
  let lastEscape = 0;

  function bytesToHex(bytes) {
    return Array.from(bytes)
      .map((value) => value.toString(16).padStart(2, "0"))
      .join("");
  }

  async function digest(text) {
    const encoded = new TextEncoder().encode(text);
    const hash = await crypto.subtle.digest("SHA-256", encoded);
    return bytesToHex(new Uint8Array(hash));
  }

  async function storePin(pin) {
    const salt = bytesToHex(crypto.getRandomValues(new Uint8Array(16)));
    const hash = await digest(`${salt}:${pin}`);
    localStorage.setItem(SALT_KEY, salt);
    localStorage.setItem(HASH_KEY, hash);
  }

  async function verifyPin(pin) {
    const salt = localStorage.getItem(SALT_KEY);
    const hash = localStorage.getItem(HASH_KEY);
    if (!salt || !hash) {
      return false;
    }
    return (await digest(`${salt}:${pin}`)) === hash;
  }

  function hasPin() {
    return Boolean(localStorage.getItem(SALT_KEY) && localStorage.getItem(HASH_KEY));
  }

  function syncSafeMode(value) {
    if (!authenticated) {
      return;
    }
    const token = document.querySelector('meta[name="csrf-token"]');
    fetch("/lounge/safe-mode/sync/", {
      method: "POST",
      credentials: "same-origin",
      keepalive: true,
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": token ? token.content : "",
      },
      body: `active=${value}`,
    }).catch(() => {});
  }

  function showShield() {
    if (active) {
      return;
    }
    active = true;
    previousTitle = document.title;
    document.title = "Notizen";
    shield.hidden = false;

    if (hasPin()) {
      setupBox.hidden = true;
      unlockBox.hidden = false;
    } else {
      setupBox.hidden = false;
      unlockBox.hidden = true;
    }

    if (syncTimer) {
      clearTimeout(syncTimer);
    }
    syncTimer = setTimeout(() => syncSafeMode("1"), 1500);
  }

  function hideShield() {
    active = false;
    shield.hidden = true;
    document.title = previousTitle;
    if (syncTimer) {
      clearTimeout(syncTimer);
      syncTimer = null;
    }
    syncSafeMode("0");
  }

  async function setupNewPin(pin, confirmPin, errorNode) {
    if (pin.length < 4 || pin !== confirmPin) {
      if (errorNode) {
        errorNode.hidden = false;
      }
      return false;
    }
    await storePin(pin);
    if (errorNode) {
      errorNode.hidden = true;
    }
    return true;
  }

  if (setupSave) {
    setupSave.addEventListener("click", async () => {
      const saved = await setupNewPin(setupPin.value, setupConfirm.value, setupError);
      if (saved) {
        setupBox.hidden = true;
        unlockBox.hidden = false;
        unlockPin.focus();
      }
    });
  }

  if (unlockButton) {
    unlockButton.addEventListener("click", async () => {
      if (await verifyPin(unlockPin.value)) {
        unlockPin.value = "";
        unlockError.hidden = true;
        hideShield();
      } else {
        unlockError.hidden = false;
      }
    });
  }

  if (settingsSave) {
    settingsSave.addEventListener("click", async () => {
      const saved = await setupNewPin(
        settingsPin.value,
        settingsConfirm.value,
        settingsStatus
      );
      settingsPin.value = "";
      settingsConfirm.value = "";
      if (settingsStatus) {
        settingsStatus.hidden = false;
        settingsStatus.textContent = saved
          ? "PIN lokal gespeichert. Esc zweimal aktiviert den Shield."
          : "PINs stimmen nicht überein oder sind zu kurz.";
        settingsStatus.classList.toggle("text-red-300", !saved);
        settingsStatus.classList.toggle("text-emerald-300", saved);
      }
    });
  }

  if (activateButton) {
    activateButton.addEventListener("click", showShield);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || active) {
      return;
    }
    const now = Date.now();
    if (now - lastEscape < 800) {
      lastEscape = 0;
      showShield();
    } else {
      lastEscape = now;
    }
  });
})();


if ("serviceWorker" in navigator && window.isSecureContext) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}


const unreadElement = document.getElementById("app-unread-count");
if (unreadElement && "setAppBadge" in navigator) {
  const unread = Number(unreadElement.dataset.count || "0");
  if (unread > 0) {
    navigator.setAppBadge(unread).catch(() => {});
  } else {
    navigator.clearAppBadge().catch(() => {});
  }
}
