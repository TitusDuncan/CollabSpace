from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assets = db.relationship("Asset", backref="project", cascade="all, delete-orphan")
    presentations = db.relationship("PresentationPage", backref="project", cascade="all, delete-orphan")


class Asset(db.Model):
    __tablename__ = "assets"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)

    title = db.Column(db.String(160), nullable=False)
    asset_type = db.Column(db.String(20), nullable=False)  # image|audio|other
    tags = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    current_version_id = db.Column(db.Integer, db.ForeignKey("versions.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    versions = db.relationship(
        "Version",
        backref="asset",
        cascade="all, delete-orphan",
        foreign_keys="Version.asset_id",
    )


class Version(db.Model):
    __tablename__ = "versions"
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)

    version_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(30), default="Draft")  # Draft/In Review/Approved/Changes Requested
    notes = db.Column(db.Text, nullable=True)

    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PresentationPage(db.Model):
    __tablename__ = "presentation_pages"
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)

    title = db.Column(db.String(160), nullable=False)
    share_token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("PresentationItem", backref="presentation", cascade="all, delete-orphan")


class PresentationItem(db.Model):
    __tablename__ = "presentation_items"
    id = db.Column(db.Integer, primary_key=True)
    presentation_page_id = db.Column(db.Integer, db.ForeignKey("presentation_pages.id"), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=False)
    version_id = db.Column(db.Integer, db.ForeignKey("versions.id"), nullable=False)