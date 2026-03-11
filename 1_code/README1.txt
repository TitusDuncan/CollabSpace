CollabSpace (Flask + SQLite) — Code + Run Instructions
Author: Titus Duncan
Project Repo: https://github.com/TitusDuncan/CollabSpace

Overview
CollabSpace is a lightweight full-stack information system designed for creatives to stay organized.
It supports:
- Project workspaces
- Asset uploads (image + audio)
- Version history with a clear “current version”
- Presentation pages for client-ready delivery with a shareable link
- Media preview (image viewing + audio playback)

This folder (1_code) contains the complete runnable application source code.

------------------------------------------------------------
1) System Requirements
------------------------------------------------------------
Tested on:
- macOS (works on Windows/Linux with minor path differences)

Required:
- Python 3.x
- pip (Python package manager)
- A modern web browser (Chrome/Safari/Edge)

No external database installation is required.
SQLite is used and stored locally as a .db file.

------------------------------------------------------------
2) Folder Contents (what’s inside 1_code)
------------------------------------------------------------
Key files:
- app.py                 Flask application entry point (routes/controllers)
- models.py              Database models (Projects, Assets, Versions, Presentations)
- requirements.txt       Dependencies list
- README1.txt            This file

Key folders:
- templates/             HTML templates (Jinja2)
- static/                Optional styling assets
- uploads/               Stored media files (images/audio) uploaded through the app

Database:
- collabspace.db         Created automatically on first run (SQLite)

------------------------------------------------------------
3) Setup Instructions (first-time run)
------------------------------------------------------------
Step A — Open a terminal in the 1_code folder
Make sure your terminal working directory is the folder that contains app.py.

Step B — Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

Step C — Install dependencies
pip install -r requirements.txt

------------------------------------------------------------
4) Run the Application
------------------------------------------------------------
python app.py

Then open your browser to:
http://127.0.0.1:5000/

What you should see:
- CollabSpace Dashboard (projects list)

------------------------------------------------------------
5) Core Demo Workflow (what to try)
------------------------------------------------------------
1) Create a new project
   - Dashboard → New Project → Create

2) Upload an image asset
   - Workspace → Upload Asset → choose a PNG/JPG → Upload
   - Confirm: image preview appears on the Asset Detail page

3) Upload an audio asset
   - Workspace → Upload Asset → choose an MP3/M4A → Upload
   - Confirm: audio player appears and plays successfully

4) Add a version to an existing asset
   - Asset Detail → Add Version → upload a new file of the same asset type
   - Confirm: version history updates and current version changes (if selected)

5) Create a presentation page
   - Workspace → New Presentation Page
   - Select asset versions → Publish
   - Confirm: presentation view loads via share link and previews media

------------------------------------------------------------
6) Notes on Storage (uploads + database)
------------------------------------------------------------
Uploads:
- Uploaded files are saved into:
  1_code/uploads/

Database:
- The SQLite database is stored as:
  1_code/collabspace.db

The UI reflects data by reading records back from SQLite after each action:
- Creating a project inserts a Project record and shows it in the dashboard/workspace.
- Uploading creates an Asset record and an initial Version record (v1).
- Adding a version creates a new Version record and can update the asset’s current_version_id.
- Presentation pages store selected asset/version pairs and display them in the client view.

------------------------------------------------------------
7) Troubleshooting
------------------------------------------------------------
If dependencies fail to install:
- Confirm you are in the correct folder (1_code)
- Confirm venv is activated (you should see “(.venv)” in the terminal)
- Re-run: pip install -r requirements.txt

If the server won’t start:
- Ensure no other process is using port 5000
- Stop the server with Ctrl+C and restart

If you get TemplateNotFound:
- Confirm the missing template exists in 1_code/templates/

If uploads are not previewing:
- Confirm the file exists in 1_code/uploads/
- Confirm the /media/<filename> route is present in app.py

------------------------------------------------------------
8) Documentation Folder (submission reference)
------------------------------------------------------------
Required PDFs for the submission package are located in:
5_documentation/

Key documents include:
- System_requriements_documentation.pdf
- Brochure_flyer.pdf
- Presentation_slides.pdf
- User_interface_specification.pdf (if submitted separately for landscape readability)

End of README1.txt