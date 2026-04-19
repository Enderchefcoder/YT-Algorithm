/**
 * YT-Safe — Client-side guardrail helpers
 *
 * This file is loaded on every page.
 * Its only job is to make sure the break_pending state
 * (stored in the Flask session) is respected if the user
 * somehow navigates to a new video without going through
 * the normal watch-end flow.
 *
 * No heavy logic here — all guardrail decisions live in
 * the Python backend (algorithm/guardrails.py).
 */

(function () {
  "use strict";

  // If the server has flagged a break pending in the page HTML,
  // it's handled by player.js after the video ends.
  // Nothing extra needed here at the moment — placeholder for
  // future client-side enhancements (e.g., idle detection).

})();
