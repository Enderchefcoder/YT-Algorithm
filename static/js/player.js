/**
 * YT-Safe — Video Player
 *
 * Responsibilities:
 *  1. Custom HTML5 video controls (play/pause, seek, volume, fullscreen)
 *  2. Track watch_time_seconds accurately (pauses don't count)
 *  3. Track liked / disliked state
 *  4. On video end: POST to /api/watch_end with all metrics
 *  5. Handle break_pending: show overlay, redirect to /break on end
 */

(function () {
  "use strict";

  const CONFIG = window.YT_SAFE || {};

  // ── Element refs ─────────────────────────────────────────────────
  const video        = document.getElementById("mainVideo");
  const container    = document.getElementById("playerContainer");
  const controls     = document.getElementById("playerControls");
  const playPauseBtn = document.getElementById("playPauseBtn");
  const rewindBtn    = document.getElementById("rewindBtn");
  const forwardBtn   = document.getElementById("forwardBtn");
  const progressBar  = document.getElementById("progressBar");
  const progressFill = document.getElementById("progressFill");
  const progressThumb= document.getElementById("progressThumb");
  const playerTime   = document.getElementById("playerTime");
  const muteBtn      = document.getElementById("muteBtn");
  const volumeSlider = document.getElementById("volumeSlider");
  const fullscreenBtn= document.getElementById("fullscreenBtn");
  const likeBtn      = document.getElementById("likeBtn");
  const dislikeBtn   = document.getElementById("dislikeBtn");
  const breakOverlay = document.getElementById("breakOverlay");

  if (!video) return;   // Guard: not on watch page

  // ── State ──────────────────────────────────────────────────────
  let watchStart     = null;      // Date when play started
  let totalWatched   = 0;         // Accumulated seconds
  let liked          = false;
  let disliked       = false;
  let controlsTimer  = null;
  let watchEndSent   = false;

  // ── Helpers ────────────────────────────────────────────────────

  function formatTime(sec) {
    sec = Math.floor(sec || 0);
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  }

  function updateProgress() {
    if (!video.duration) return;
    const pct = (video.currentTime / video.duration) * 100;
    progressFill.style.width = pct + "%";
    progressThumb.style.left  = pct + "%";
    playerTime.textContent =
      formatTime(video.currentTime) + " / " + formatTime(video.duration);
  }

  function showControls() {
    container.classList.add("controls-visible");
    clearTimeout(controlsTimer);
    controlsTimer = setTimeout(() => {
      if (!video.paused) container.classList.remove("controls-visible");
    }, 2500);
  }

  // ── Watch time tracking ────────────────────────────────────────

  function onPlay() {
    watchStart = Date.now();
    playPauseBtn.textContent = "⏸";
  }

  function onPause() {
    if (watchStart !== null) {
      totalWatched += (Date.now() - watchStart) / 1000;
      watchStart = null;
    }
    playPauseBtn.textContent = "▶";
  }

  // ── Send watch event ───────────────────────────────────────────

  async function sendWatchEnd() {
    if (watchEndSent) return;
    watchEndSent = true;

    // Flush any remaining active time
    if (watchStart !== null) {
      totalWatched += (Date.now() - watchStart) / 1000;
      watchStart = null;
    }

    const payload = {
      video_id:              CONFIG.videoId        || "",
      video_title:           CONFIG.videoTitle      || "",
      video_hashtags:        CONFIG.videoHashtags   || "",
      watch_time_seconds:    Math.round(totalWatched),
      video_duration_seconds:CONFIG.videoDuration   || video.duration || 0,
      liked:                 liked,
      disliked:              disliked,
    };

    let breakNeeded    = CONFIG.breakPending || false;
    let breakSeconds   = CONFIG.breakSeconds || 180;
    let breakReason    = "";

    try {
      const resp = await fetch("/api/watch_end", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload),
      });
      const data = await resp.json();
      if (data.break_needed) {
        breakNeeded  = true;
        breakSeconds = data.break_seconds;
        breakReason  = encodeURIComponent(data.reason || "");
      }
    } catch (e) {
      // Offline / error — still respect pre-existing break flag
    }

    if (breakNeeded) {
      window.location.href =
        `/break?seconds=${breakSeconds}&reason=${breakReason}`;
    } else {
      window.location.href = "/";
    }
  }

  // ── Controls ───────────────────────────────────────────────────

  playPauseBtn.addEventListener("click", () => {
    video.paused ? video.play() : video.pause();
  });

  rewindBtn.addEventListener("click",  () => { video.currentTime -= 10; });
  forwardBtn.addEventListener("click", () => { video.currentTime += 10; });

  video.addEventListener("play",  onPlay);
  video.addEventListener("pause", onPause);

  video.addEventListener("timeupdate", updateProgress);
  video.addEventListener("loadedmetadata", updateProgress);

  // Progress bar seeking
  progressBar.addEventListener("click", (e) => {
    const rect = progressBar.getBoundingClientRect();
    const pct  = (e.clientX - rect.left) / rect.width;
    video.currentTime = pct * video.duration;
  });

  // Volume
  muteBtn.addEventListener("click", () => {
    video.muted = !video.muted;
    muteBtn.textContent = video.muted ? "🔇" : "🔊";
  });
  volumeSlider.addEventListener("input", () => {
    video.volume = volumeSlider.value;
    video.muted  = video.volume === 0;
    muteBtn.textContent = video.muted ? "🔇" : "🔊";
  });

  // Fullscreen
  fullscreenBtn.addEventListener("click", () => {
    if (!document.fullscreenElement) {
      container.requestFullscreen();
      fullscreenBtn.textContent = "⊡";
    } else {
      document.exitFullscreen();
      fullscreenBtn.textContent = "⛶";
    }
  });

  // Show controls on interaction
  container.addEventListener("mousemove", showControls);
  container.addEventListener("touchstart", showControls, { passive: true });
  container.addEventListener("click", showControls);

  // ── Like / Dislike ─────────────────────────────────────────────

  likeBtn.addEventListener("click", () => {
    liked    = !liked;
    disliked = false;
    likeBtn.setAttribute("aria-pressed",    liked.toString());
    dislikeBtn.setAttribute("aria-pressed", "false");
  });

  dislikeBtn.addEventListener("click", () => {
    disliked = !disliked;
    liked    = false;
    dislikeBtn.setAttribute("aria-pressed", disliked.toString());
    likeBtn.setAttribute("aria-pressed",    "false");
  });

  // ── Video end ─────────────────────────────────────────────────

  video.addEventListener("ended", sendWatchEnd);

  // Also send when navigating away (best-effort)
  window.addEventListener("beforeunload", () => {
    if (!watchEndSent && totalWatched > 5) {
      // Synchronous beacon for unload
      const payload = JSON.stringify({
        video_id:              CONFIG.videoId        || "",
        video_title:           CONFIG.videoTitle      || "",
        video_hashtags:        CONFIG.videoHashtags   || "",
        watch_time_seconds:    Math.round(totalWatched),
        video_duration_seconds:CONFIG.videoDuration   || video.duration || 0,
        liked,
        disliked,
      });
      navigator.sendBeacon("/api/watch_end", new Blob([payload],
        { type: "application/json" }));
    }
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT") return;
    if (e.key === " " || e.key === "k") {
      e.preventDefault();
      video.paused ? video.play() : video.pause();
    } else if (e.key === "ArrowLeft"  || e.key === "j") {
      video.currentTime -= 10;
    } else if (e.key === "ArrowRight" || e.key === "l") {
      video.currentTime += 10;
    } else if (e.key === "m") {
      video.muted = !video.muted;
      muteBtn.textContent = video.muted ? "🔇" : "🔊";
    } else if (e.key === "f") {
      fullscreenBtn.click();
    }
  });

  // Autoplay attempt
  video.play().catch(() => {
    // Browsers may block autoplay — user needs to click play
  });

})();
