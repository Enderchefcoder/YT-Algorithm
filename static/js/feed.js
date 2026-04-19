/**
 * YT-Safe — Feed
 *
 * Infinite scroll: when the user reaches near the bottom,
 * fetch more results from /api/feed and append to the grid.
 */

(function () {
  "use strict";

  const grid   = document.getElementById("feedGrid");
  const loader = document.getElementById("feedLoader");

  if (!grid) return;

  let loading = false;

  function createCard(video) {
    const dur = video.duration || 0;
    const m   = Math.floor(dur / 60);
    const s   = (dur % 60).toString().padStart(2, "0");
    const views = (video.view_count || 0).toLocaleString();
    const thumb = video.thumbnail || "";
    const id    = video.id || "";
    const title = _escape(video.title || "Unknown");
    const uploader = _escape(video.uploader || "Unknown");

    const article = document.createElement("article");
    article.className = "video-card";
    article.innerHTML = `
      <a href="/watch/${id}" class="video-card__thumb-link">
        <div class="video-card__thumb-wrap">
          <img class="video-card__thumb" src="${thumb}"
               alt="${title}" loading="lazy" />
          <span class="video-card__duration">${m}:${s}</span>
        </div>
      </a>
      <div class="video-card__meta">
        <a href="/watch/${id}" class="video-card__title">${title}</a>
        <p class="video-card__uploader">${uploader}</p>
        <p class="video-card__views">${views} views</p>
      </div>
    `;
    return article;
  }

  function _escape(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function loadMore() {
    if (loading) return;
    loading = true;
    loader.classList.add("visible");

    try {
      const resp = await fetch("/api/feed");
      const videos = await resp.json();
      videos.forEach(v => grid.appendChild(createCard(v)));
    } catch (e) {
      console.warn("Feed load error:", e);
    } finally {
      loader.classList.remove("visible");
      loading = false;
    }
  }

  // Intersection Observer for infinite scroll trigger
  const sentinel = document.createElement("div");
  sentinel.style.height = "1px";
  document.querySelector(".feed-layout")?.appendChild(sentinel);

  const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) loadMore();
  }, { rootMargin: "300px" });

  observer.observe(sentinel);

})();
