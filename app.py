"""
Main Flask application.

Routes:
  GET  /                          Home / feed
  GET  /watch/<video_id>          Video player
  POST /api/watch_end             Record watch event (called by player.js)
  POST /api/break_complete        Reset stats after break
  GET  /break                     Break screen
  GET  /search                    Search results
  GET  /api/feed                  JSON feed (for infinite scroll)
  GET  /parent                    Parental dashboard
  POST /parent/set_break          Set parent break override
"""

import uuid
from datetime import datetime, timezone

from flask import (
    Flask, render_template, request, session,
    jsonify, redirect, url_for
)

from config import DATABASE_URI, SECRET_KEY, GUARDRAIL_CONFIG
from database.db import init_db
from algorithm.guardrails import record_watch, reset_after_break, get_session_summary
from algorithm.feed import build_feed
from video.embedder import build_embed
from video.search import search_videos


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False  # Set True in production with HTTPS

    init_db(app)

    # ------------------------------------------------------------------
    # Session helper
    # ------------------------------------------------------------------

    def get_session_id() -> str:
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        return session["session_id"]

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        sid = get_session_id()
        feed = build_feed(sid)
        return render_template("index.html", videos=feed)

    @app.route("/watch/<video_id>")
    def watch(video_id: str):
        sid = get_session_id()
        embed = build_embed(video_id)
        if embed is None:
            return render_template("index.html", error="Video not found."), 404

        # Check if a break is pending (set by a previous watch_end call)
        break_pending = session.pop("break_pending", False)
        break_seconds = session.pop("break_seconds", 0)
        break_reason = session.pop("break_reason", "")

        return render_template(
            "watch.html",
            video=embed,
            break_pending=break_pending,
            break_seconds=break_seconds,
            break_reason=break_reason,
        )

    @app.route("/break")
    def break_screen():
        seconds = request.args.get("seconds", 180, type=int)
        reason = request.args.get("reason", "")
        return render_template("break.html", seconds=seconds, reason=reason)

    @app.route("/search")
    def search():
        query = request.args.get("q", "").strip()
        if not query:
            return redirect(url_for("index"))
        results = search_videos(query, max_results=20)
        return render_template("search.html", videos=results, query=query)

    @app.route("/parent")
    def parent_dashboard():
        sid = get_session_id()
        summary = get_session_summary(sid)
        presets = GUARDRAIL_CONFIG.parent_break_presets
        return render_template(
            "parent_dashboard.html",
            summary=summary,
            presets=presets,
        )

    @app.route("/parent/set_break", methods=["POST"])
    def parent_set_break():
        from database.db import db
        from database.models import ParentSettings

        sid = get_session_id()
        seconds = request.form.get("seconds", type=int)

        ps = ParentSettings.query.filter_by(session_id=sid).first()
        if ps is None:
            ps = ParentSettings(session_id=sid)
            db.session.add(ps)

        ps.break_override_seconds = seconds
        db.session.commit()

        return redirect(url_for("parent_dashboard"))

    # ------------------------------------------------------------------
    # API endpoints
    # ------------------------------------------------------------------

    @app.route("/api/watch_end", methods=["POST"])
    def api_watch_end():
        """
        Called by player.js when a video finishes (or the user navigates away).
        Expects JSON body with all watch metrics.
        """
        sid = get_session_id()
        data = request.get_json(force=True) or {}

        result = record_watch(
            session_id=sid,
            video_id=data.get("video_id", ""),
            video_title=data.get("video_title", ""),
            video_hashtags=data.get("video_hashtags", ""),
            watch_time_seconds=float(data.get("watch_time_seconds", 0)),
            video_duration_seconds=float(data.get("video_duration_seconds", 1)),
            liked=bool(data.get("liked", False)),
            disliked=bool(data.get("disliked", False)),
        )

        if result["break_needed"]:
            session["break_pending"] = True
            session["break_seconds"] = result["break_seconds"]
            session["break_reason"] = result["reason"]

        return jsonify(result)

    @app.route("/api/break_complete", methods=["POST"])
    def api_break_complete():
        sid = get_session_id()
        reset_after_break(sid)
        return jsonify({"status": "ok"})

    @app.route("/api/feed")
    def api_feed():
        """JSON endpoint for infinite scroll / AJAX feed refresh."""
        sid = get_session_id()
        feed = build_feed(sid)
        return jsonify(feed)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
