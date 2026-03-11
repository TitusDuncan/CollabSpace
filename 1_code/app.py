import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename

from models import db, Project, Asset, Version, PresentationPage

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "collabspace-dev"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///collabspace.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    ALLOWED_AUDIO = {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/x-m4a", "audio/x-wav", "audio/wave"}

    def classify_asset_type(mime_type: str) -> str:
        if mime_type in ALLOWED_IMAGE:
            return "image"
        if mime_type in ALLOWED_AUDIO:
            return "audio"
        return "other"

    def store_upload(file_storage):
        original = secure_filename(file_storage.filename)
        mime = file_storage.mimetype or "application/octet-stream"
        token = secrets.token_hex(8)
        stored = f"{token}_{original}"
        file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], stored))
        return stored, original, mime

    db.init_app(app)

    @app.route("/")
    def dashboard():
        projects = Project.query.order_by(Project.created_at.desc()).all()
        return render_template("dashboard.html", projects=projects)

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
            return redirect(url_for("project_detail", project_id=p.id))

        return render_template("project_new.html")

    @app.route("/projects/<int:project_id>")
    def project_detail(project_id):
        project = Project.query.get_or_404(project_id)

        assets = Asset.query.filter_by(project_id=project_id).order_by(Asset.created_at.desc()).all()
        presentations = PresentationPage.query.filter_by(project_id=project_id).order_by(PresentationPage.created_at.desc()).all()

        # Map asset_id -> current version number (for display)
        current_versions = {}
        for a in assets:
            if a.current_version_id:
                v = Version.query.get(a.current_version_id)
                current_versions[a.id] = v.version_number if v else "-"

        return render_template(
            "project_detail.html",
            project=project,
            assets=assets,
            presentations=presentations,
            current_versions=current_versions,
        )
    
    
    @app.route("/media/<path:filename>")
    def media(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)
    
    @app.route("/projects/<int:project_id>/assets/new", methods=["GET", "POST"])
    def asset_new(project_id):
        project = Project.query.get_or_404(project_id)

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
                flash("Midterm MVP supports image and audio only.", "error")
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
            db.session.flush()  # get asset.id

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

            return redirect(url_for("asset_detail", asset_id=asset.id))

        return render_template("asset_new.html", project=project)
        
    @app.route("/assets/<int:asset_id>")
    def asset_detail(asset_id):
        asset = Asset.query.get_or_404(asset_id)
        versions = Version.query.filter_by(asset_id=asset_id).order_by(Version.version_number.desc()).all()
        current = Version.query.get(asset.current_version_id) if asset.current_version_id else None
        project = Project.query.get(asset.project_id)
        return render_template("asset_detail.html", asset=asset, versions=versions, current=current, project=project)
    
    @app.route("/projects/<int:project_id>/presentations/new", methods=["GET", "POST"])
    def presentation_new(project_id):
        project = Project.query.get_or_404(project_id)
        assets = Asset.query.filter_by(project_id=project_id).order_by(Asset.created_at.desc()).all()

        # Build versions per asset for dropdowns
        versions_by_asset = {
            a.id: Version.query.filter_by(asset_id=a.id).order_by(Version.version_number.desc()).all()
            for a in assets
        }

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            if not title:
                flash("Presentation title is required.", "error")
                return redirect(url_for("presentation_new", project_id=project_id))

            token = secrets.token_urlsafe(12)
            page = PresentationPage(project_id=project_id, title=title, share_token=token)
            db.session.add(page)
            db.session.flush()

            # Create one PresentationItem per selected asset/version
            from models import PresentationItem  # local import avoids circular issues
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

            db.session.commit()
            return redirect(url_for("presentation_view", share_token=page.share_token))

        return render_template(
            "presentation_new.html",
            project=project,
            assets=assets,
            versions_by_asset=versions_by_asset
        )

    @app.route("/p/<share_token>")
    def presentation_view(share_token):
        page = PresentationPage.query.filter_by(share_token=share_token).first_or_404()

        from models import PresentationItem
        items = PresentationItem.query.filter_by(presentation_page_id=page.id).all()

        view_items = []
        for it in items:
            asset = Asset.query.get(it.asset_id)
            version = Version.query.get(it.version_id)
            view_items.append((asset, version))

        return render_template("presentation_view.html", page=page, items=view_items)

    @app.route("/assets/<int:asset_id>/versions/new", methods=["POST"])
    def version_new(asset_id):
        asset = Asset.query.get_or_404(asset_id)

        file = request.files.get("file")
        notes = request.form.get("notes", "").strip()
        set_current = request.form.get("set_current") == "on"

        if not file or not file.filename:
            flash("Please choose a file to upload as a new version.", "error")
            return redirect(url_for("asset_detail", asset_id=asset_id))

        stored, original, mime = store_upload(file)
        asset_type = classify_asset_type(mime)

        # Enforce asset type consistency: image assets stay image; audio assets stay audio
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

        if set_current:
            asset.current_version_id = v.id

        db.session.commit()
        flash(f"Version v{next_num} added.", "success")
        return redirect(url_for("asset_detail", asset_id=asset_id))
    
    @app.route("/assets/<int:asset_id>/set-current/<int:version_id>", methods=["POST"])
    def set_current(asset_id, version_id):
        asset = Asset.query.get_or_404(asset_id)
        v = Version.query.get_or_404(version_id)

        if v.asset_id != asset_id:
            flash("Invalid version selection.", "error")
            return redirect(url_for("asset_detail", asset_id=asset_id))

        asset.current_version_id = v.id
        db.session.commit()
        flash(f"Current version set to v{v.version_number}.", "success")
        return redirect(url_for("asset_detail", asset_id=asset_id))

    return app



if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()  # creates collabspace.db tables if they don't exist
    app.run(debug=True)