import os
import secrets
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, send_from_directory, session
)

from models import db, Project, Asset, Version, PresentationPage, PresentationItem, Review


DEFAULT_DEMO_PIN = "1234"  # demo placeholder pin


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "collabspace-dev"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///collabspace.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    ALLOWED_AUDIO = {
        "audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4",
        "audio/x-m4a", "audio/x-wav", "audio/wave"
    }

    def classify_asset_type(mime_type: str) -> str:
        if mime_type in ALLOWED_IMAGE:
            return "image"
        if mime_type in ALLOWED_AUDIO:
            return "audio"
        return "other"

    def store_upload(file_storage):
        from werkzeug.utils import secure_filename
        original = secure_filename(file_storage.filename)
        mime = file_storage.mimetype or "application/octet-stream"
        token = secrets.token_hex(8)
        stored = f"{token}_{original}"
        file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], stored))
        return stored, original, mime

    def get_project_role(project_id: int) -> str:
        key = f"role_project_{project_id}"
        if key not in session:
            # Only set it once, the first time you ever enter the project
            session[key] = session.get("global_role", "Creator")
        return session[key]

    db.init_app(app)

    # ----------------------------
    # Dashboard + Global Role
    # ----------------------------

    @app.route("/")
    def dashboard():
        projects = Project.query.order_by(Project.created_at.desc()).all()
        global_role = session.get("global_role", "Creator")
        return render_template("dashboard.html", projects=projects, global_role=global_role)

    @app.route("/set-global-role", methods=["POST"])
    def set_global_role():
        role = request.form.get("role", "Creator")
        if role not in {"Creator", "Collaborator", "Client"}:
            role = "Creator"
        session["global_role"] = role
        flash(f"Default view set to {role}.", "info")
        return redirect(url_for("dashboard"))

    # ----------------------------
    # Projects + Role
    # ----------------------------

    @app.route("/projects/new", methods=["GET", "POST"])
    def project_new():
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()

            if not title:
                flash("Project title is required.", "error")
                return redirect(url_for("project_new"))

            p = Project(title=title, description=description or None)
            db.session.add(p)
            db.session.commit()

            # initialize per-project role from global_role (sticky)
            session[f"role_project_{p.id}"] = session.get("global_role", "Creator")
            flash("Project created.", "success")
            return redirect(url_for("project_detail", project_id=p.id))

        return render_template("project_new.html")

    @app.route("/projects/<int:project_id>/set-role", methods=["POST"])
    def set_role(project_id):
        project = Project.query.get_or_404(project_id)
        role = request.form.get("role", "Creator")
        if role not in {"Creator", "Collaborator", "Client"}:
            role = "Creator"

        session[f"role_project_{project_id}"] = role
        flash(f"Viewing {project.title} as {role}.", "info")

        # Client role should never land on the workspace; redirect to presentations-only page
        if role == "Client":
            return redirect(url_for("project_presentations", project_id=project_id))

        return redirect(url_for("project_detail", project_id=project_id))

    # ----------------------------
    # Project Workspace
    # ----------------------------

    @app.route("/projects/<int:project_id>")
    def project_detail(project_id):
        project = Project.query.get_or_404(project_id)
        role = get_project_role(project_id)

        # Client must never see workspace
        if role == "Client":
            return redirect(url_for("project_presentations", project_id=project_id))

        q = request.args.get("q", "").strip()
        type_filter = request.args.get("type", "").strip()

        assets_query = Asset.query.filter_by(project_id=project_id)
        if type_filter in {"image", "audio"}:
            assets_query = assets_query.filter(Asset.asset_type == type_filter)

        if q:
            like = f"%{q}%"
            assets_query = assets_query.filter(
                (Asset.title.ilike(like)) |
                (Asset.tags.ilike(like)) |
                (Asset.notes.ilike(like))
            )

        assets = assets_query.order_by(Asset.created_at.desc()).all()
        presentations = PresentationPage.query.filter_by(project_id=project_id).order_by(PresentationPage.created_at.desc()).all()

        current_versions = {}
        for a in assets:
            if a.current_version_id:
                v = Version.query.get(a.current_version_id)
                current_versions[a.id] = v.version_number if v else "-"

        return render_template(
            "project_detail.html",
            project=project,
            role=role,
            global_role=session.get("global_role", "Creator"),
            assets=assets,
            presentations=presentations,
            current_versions=current_versions,
            q=q,
            type_filter=type_filter,
        )

    @app.route("/projects/<int:project_id>/presentations", methods=["GET"])
    def project_presentations(project_id):
        """Client-only view: presentation list for a project. Creator/Collab can still access if desired."""
        project = Project.query.get_or_404(project_id)
        role = get_project_role(project_id)

        presentations = PresentationPage.query.filter_by(project_id=project_id).order_by(PresentationPage.created_at.desc()).all()
        return render_template(
            "project_presentations.html",
            project=project,
            role=role,
            global_role=session.get("global_role", "Creator"),
            presentations=presentations,
        )

    @app.route("/projects/<int:project_id>/toggle-collab-current", methods=["POST"])
    def toggle_collab_current(project_id):
        project = Project.query.get_or_404(project_id)
        role = get_project_role(project_id)

        if role != "Creator":
            flash("Only the Creator can change collaborator permissions.", "error")
            return redirect(url_for("project_detail", project_id=project_id))

        allow = request.form.get("allow_collab_current") == "on"
        project.allow_collaborator_set_current = allow
        db.session.commit()
        flash("Collaborator permission updated.", "success")
        return redirect(url_for("project_detail", project_id=project_id))
    
    @app.route("/projects/<int:project_id>/open")
    def project_open(project_id):
    # Always start as Creator when entering from dashboard
        session[f"role_project_{project_id}"] = "Creator"
        return redirect(url_for("project_detail", project_id=project_id))

    # ----------------------------
    # Media
    # ----------------------------

    @app.route("/media/<path:filename>")
    def media(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)

    # ----------------------------
    # Assets
    # ----------------------------

    @app.route("/projects/<int:project_id>/assets/new", methods=["GET", "POST"])
    def asset_new(project_id):
        project = Project.query.get_or_404(project_id)
        role = get_project_role(project_id)

        if role == "Client":
            flash("Client view cannot upload assets.", "error")
            return redirect(url_for("project_presentations", project_id=project_id))

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            tags = request.form.get("tags", "").strip()
            notes = request.form.get("notes", "").strip()
            file = request.files.get("file")

            if not title:
                flash("Asset title is required.", "error")
                return redirect(url_for("asset_new", project_id=project_id))

            if not file or not file.filename:
                flash("Please choose a file to upload.", "error")
                return redirect(url_for("asset_new", project_id=project_id))

            stored, original, mime = store_upload(file)
            asset_type = classify_asset_type(mime)

            if asset_type not in {"image", "audio"}:
                flash("This MVP supports image and audio only.", "error")
                try:
                    os.remove(os.path.join(app.config["UPLOAD_FOLDER"], stored))
                except OSError:
                    pass
                return redirect(url_for("asset_new", project_id=project_id))

            asset = Asset(
                project_id=project_id,
                title=title,
                asset_type=asset_type,
                tags=tags or None,
                notes=notes or None,
            )
            db.session.add(asset)
            db.session.flush()

            v1 = Version(
                asset_id=asset.id,
                version_number=1,
                status="Draft",
                notes="Initial upload",
                original_filename=original,
                stored_filename=stored,
                mime_type=mime,
            )
            db.session.add(v1)
            db.session.flush()

            asset.current_version_id = v1.id
            db.session.commit()

            flash("Asset uploaded (v1 created).", "success")
            return redirect(url_for("asset_detail", asset_id=asset.id))

        return render_template("asset_new.html", project=project, role=role, global_role=session.get("global_role", "Creator"))

    @app.route("/assets/<int:asset_id>")
    def asset_detail(asset_id):
        asset = Asset.query.get_or_404(asset_id)
        project = Project.query.get(asset.project_id)
        role = get_project_role(asset.project_id)

        # Client cannot see asset details; they must use presentation pages
        if role == "Client":
            return redirect(url_for("project_presentations", project_id=asset.project_id))

        versions = Version.query.filter_by(asset_id=asset_id).order_by(Version.version_number.desc()).all()
        current = Version.query.get(asset.current_version_id) if asset.current_version_id else None

        return render_template(
            "asset_detail.html",
            asset=asset,
            project=project,
            role=role,
            global_role=session.get("global_role", "Creator"),
            versions=versions,
            current=current,
        )

    @app.route("/assets/<int:asset_id>/versions/new", methods=["POST"])
    def version_new(asset_id):
        asset = Asset.query.get_or_404(asset_id)
        project = Project.query.get(asset.project_id)
        role = get_project_role(asset.project_id)

        if role == "Client":
            flash("Client view cannot add versions.", "error")
            return redirect(url_for("project_presentations", project_id=asset.project_id))

        file = request.files.get("file")
        notes = request.form.get("notes", "").strip()
        set_current_flag = request.form.get("set_current") == "on"

        if not file or not file.filename:
            flash("Please choose a file to upload as a new version.", "error")
            return redirect(url_for("asset_detail", asset_id=asset_id))

        stored, original, mime = store_upload(file)
        asset_type = classify_asset_type(mime)

        if asset_type != asset.asset_type:
            flash("File type must match the asset type (image stays image, audio stays audio).", "error")
            try:
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], stored))
            except OSError:
                pass
            return redirect(url_for("asset_detail", asset_id=asset_id))

        latest = Version.query.filter_by(asset_id=asset_id).order_by(Version.version_number.desc()).first()
        next_num = (latest.version_number + 1) if latest else 1

        v = Version(
            asset_id=asset_id,
            version_number=next_num,
            status="Draft",
            notes=notes or None,
            original_filename=original,
            stored_filename=stored,
            mime_type=mime,
        )
        db.session.add(v)
        db.session.flush()

        if set_current_flag:
            allowed = (role == "Creator") or (role == "Collaborator" and project.allow_collaborator_set_current)
            if allowed:
                asset.current_version_id = v.id
            else:
                flash("Creator permission required to set current version.", "error")

        db.session.commit()
        flash(f"Version v{next_num} added.", "success")
        return redirect(url_for("asset_detail", asset_id=asset_id))

    @app.route("/assets/<int:asset_id>/set-current/<int:version_id>", methods=["POST"])
    def set_current(asset_id, version_id):
        asset = Asset.query.get_or_404(asset_id)
        project = Project.query.get(asset.project_id)
        role = get_project_role(asset.project_id)
        v = Version.query.get_or_404(version_id)

        if v.asset_id != asset_id:
            flash("Invalid version selection.", "error")
            return redirect(url_for("asset_detail", asset_id=asset_id))

        allowed = (role == "Creator") or (role == "Collaborator" and project.allow_collaborator_set_current)
        if not allowed:
            flash("Creator permission required to set current version.", "error")
            return redirect(url_for("asset_detail", asset_id=asset_id))

        asset.current_version_id = v.id
        db.session.commit()
        flash(f"Current version set to v{v.version_number}.", "success")
        return redirect(url_for("asset_detail", asset_id=asset_id))

    # ----------------------------
    # Presentations (PIN + Update PIN + Review)
    # ----------------------------

    @app.route("/projects/<int:project_id>/presentations/new", methods=["GET", "POST"])
    def presentation_new(project_id):
        project = Project.query.get_or_404(project_id)
        role = get_project_role(project_id)

        if role != "Creator":
            flash("Only the Creator can publish presentation pages.", "error")
            return redirect(url_for("project_detail", project_id=project_id))

        assets = Asset.query.filter_by(project_id=project_id).order_by(Asset.created_at.desc()).all()
        versions_by_asset = {
            a.id: Version.query.filter_by(asset_id=a.id).order_by(Version.version_number.desc()).all()
            for a in assets
        }

        if request.method == "POST":
            title = request.form.get("title", "").strip()

            # Pin can be blank; use default demo placeholder
            pin_code = request.form.get("pin_code", "").strip() or DEFAULT_DEMO_PIN

            if not title:
                flash("Presentation title is required.", "error")
                return redirect(url_for("presentation_new", project_id=project_id))

            token = secrets.token_urlsafe(12)
            page = PresentationPage(
                project_id=project_id,
                title=title,
                share_token=token,
                pin_code=pin_code
            )
            db.session.add(page)
            db.session.flush()

            added_any = False
            for a in assets:
                key = f"version_for_asset_{a.id}"
                version_id = request.form.get(key)
                if not version_id:
                    continue
                v = Version.query.get(int(version_id))
                if v and v.asset_id == a.id:
                    db.session.add(PresentationItem(
                        presentation_page_id=page.id,
                        asset_id=a.id,
                        version_id=v.id
                    ))
                    added_any = True

            db.session.commit()
            flash("Presentation published.", "success")
            return redirect(url_for("presentation_view", share_token=page.share_token))

        return render_template(
            "presentation_new.html",
            project=project,
            role=role,
            global_role=session.get("global_role", "Creator"),
            assets=assets,
            versions_by_asset=versions_by_asset
        )

    def pin_verified(page: PresentationPage) -> bool:
        """Session stores the exact pin value that was verified. If pin changes, re-entry required."""
        key = f"pin_ok_{page.id}"
        return session.get(key) == (page.pin_code or DEFAULT_DEMO_PIN)

    @app.route("/p/<share_token>")
    def presentation_view(share_token):
        page = PresentationPage.query.filter_by(share_token=share_token).first_or_404()
        project = Project.query.get(page.project_id)
        role = get_project_role(page.project_id)

        required_pin = page.pin_code or DEFAULT_DEMO_PIN

        # Client-only PIN gate
        if role == "Client":
            entered = (request.args.get("pin") or "").strip()

            # allow access if already verified (and pin hasn't changed)
            if session.get(f"pin_ok_{page.id}") != required_pin:
                if entered:
                    if entered == required_pin:
                        session[f"pin_ok_{page.id}"] = required_pin
                        return redirect(url_for("presentation_view", share_token=share_token))
                    else:
                        # wrong pin -> show error message
                        return render_template(
                            "presentation_pin.html",
                            page=page,
                            project=project,
                            role=role,
                            global_role=session.get("global_role", "Creator"),
                            error="Incorrect PIN. Please try again."
                        )
                # no pin entered yet -> show entry page
                return render_template(
                    "presentation_pin.html",
                    page=page,
                    project=project,
                    role=role,
                    global_role=session.get("global_role", "Creator"),
                    error=None
                )

        # If not client, bypass PIN and show presentation
        items = PresentationItem.query.filter_by(presentation_page_id=page.id).all()
        view_items = []
        for it in items:
            asset = Asset.query.get(it.asset_id)
            version = Version.query.get(it.version_id)
            if asset and version:
                view_items.append((asset, version))

        return render_template(
            "presentation_view.html",
            page=page,
            items=view_items,
            project=project,
            role=role,
            global_role=session.get("global_role", "Creator")
        )

    @app.route("/p/<share_token>/update-pin", methods=["POST"])
    def update_presentation_pin(share_token):
        page = PresentationPage.query.filter_by(share_token=share_token).first_or_404()
        project = Project.query.get(page.project_id)
        role = get_project_role(page.project_id)

        if role != "Creator":
            flash("Only the Creator can update the PIN.", "error")
            return redirect(url_for("presentation_view", share_token=share_token))

        new_pin = (request.form.get("pin_code") or "").strip()
        if not new_pin:
            new_pin = DEFAULT_DEMO_PIN

        page.pin_code = new_pin
        db.session.commit()

        # Invalidate any previous verification
        session.pop(f"pin_ok_{page.id}", None)

        flash("PIN updated. Clients must use the new PIN.", "success")
        return redirect(url_for("presentation_view", share_token=share_token))

    @app.route("/p/<share_token>/review", methods=["POST"])
    def submit_review(share_token):
        page = PresentationPage.query.filter_by(share_token=share_token).first_or_404()
        required_pin = page.pin_code or DEFAULT_DEMO_PIN

        project = Project.query.get(page.project_id)
        role = get_project_role(page.project_id)

        # Only clients are required to pass PIN to review
        if role == "Client":
            if session.get(f"pin_ok_{page.id}") != required_pin:
                flash("PIN required before submitting a review.", "error")
                return redirect(url_for("presentation_view", share_token=share_token))

        version_id = request.form.get("version_id", "").strip()
        decision = request.form.get("decision", "").strip().upper()
        note = request.form.get("note", "").strip()

        if not version_id.isdigit():
            flash("Invalid version selected.", "error")
            return redirect(url_for("presentation_view", share_token=share_token))

        if decision not in {"APPROVED", "CHANGES_REQUESTED"}:
            flash("Invalid review action.", "error")
            return redirect(url_for("presentation_view", share_token=share_token))

        v = Version.query.get_or_404(int(version_id))

        r = Review(
            presentation_page_id=page.id,
            version_id=v.id,
            decision=decision,
            note=note or None,
            created_at=datetime.utcnow()
        )
        db.session.add(r)

        v.status = "Approved" if decision == "APPROVED" else "Changes Requested"
        db.session.commit()

        flash("Review submitted. Version status updated.", "success")
        return redirect(url_for("presentation_view", share_token=share_token))

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)