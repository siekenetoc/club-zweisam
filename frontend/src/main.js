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
