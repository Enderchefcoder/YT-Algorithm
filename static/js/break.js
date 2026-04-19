/**
 * YT-Safe — Break Screen
 *
 * Counts down from BREAK_SECONDS, animates the progress bar,
 * rotates health tips, then enables the Continue button.
 * Calls /api/break_complete when the user continues.
 */

(function () {
  "use strict";

  const TOTAL  = window.BREAK_SECONDS || 180;

  const elMins    = document.getElementById("breakMinutes");
  const elSecs    = document.getElementById("breakSeconds");
  const elBar     = document.getElementById("breakProgressBar");
  const elTip     = document.getElementById("breakTip");
  const elDoneBtn = document.getElementById("breakDoneBtn");

  const TIPS = [
    "Stretch your arms above your head and hold for 10 seconds 🙆",
    "Look at something 20 feet away for 20 seconds 👀",
    "Take 5 slow, deep breaths 🌬️",
    "Get a glass of water 💧",
    "Roll your shoulders backwards 5 times 🔄",
    "Blink rapidly for 10 seconds to re-moisten your eyes 👁️",
    "Stand up and walk around for a minute 🚶",
    "Smile! You're doing great 😊",
  ];

  let tipIndex = 0;
  function rotateTip() {
    elTip.style.opacity = "0";
    setTimeout(() => {
      tipIndex = (tipIndex + 1) % TIPS.length;
      elTip.textContent = TIPS[tipIndex];
      elTip.style.opacity = "1";
    }, 400);
  }

  // Randomise starting tip
  tipIndex = Math.floor(Math.random() * TIPS.length);
  elTip.textContent = TIPS[tipIndex];

  // Start tip rotation every 20 seconds
  const tipInterval = setInterval(rotateTip, 20000);

  // ── Countdown ──────────────────────────────────────────────────

  let remaining = TOTAL;

  function tick() {
    remaining = Math.max(0, remaining - 1);

    const m = Math.floor(remaining / 60);
    const s = remaining % 60;
    elMins.textContent = m.toString();
    elSecs.textContent = s.toString().padStart(2, "0");

    const progress = ((TOTAL - remaining) / TOTAL) * 100;
    elBar.style.width = progress + "%";

    if (remaining <= 0) {
      clearInterval(countdownInterval);
      clearInterval(tipInterval);
      enableContinue();
    }
  }

  // Initialise display immediately
  tick();
  // Force width transition to work by setting after a frame
  requestAnimationFrame(() => { elBar.style.width = "0%"; });

  const countdownInterval = setInterval(tick, 1000);

  // ── Enable continue ────────────────────────────────────────────

  function enableContinue() {
    elDoneBtn.disabled = false;
    elDoneBtn.removeAttribute("aria-disabled");
    elTip.textContent = "Break complete! You can continue now 🎉";
  }

  elDoneBtn.addEventListener("click", async () => {
    elDoneBtn.disabled = true;
    try {
      await fetch("/api/break_complete", { method: "POST" });
    } catch (e) { /* offline */ }
    window.location.href = "/";
  });

})();
