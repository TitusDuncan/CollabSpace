CollabSpace — Integration Testing (Module 8)

Status:
Integration testing is not implemented at this stage of the project.

Reason:
The midterm focus is demonstrating integrated system behavior through the live demo:
- Forms and uploads in the UI
- Backend route handling in Flask
- Records stored and retrieved from SQLite
- Media served back for preview in the browser

Planned integration tests (for the final phase):
1) Project creation flow
   - POST /projects/new inserts a Project record and redirects correctly
2) Asset upload flow
   - Upload stores file in uploads/ and creates Asset + Version records in SQLite
3) Add version flow
   - Upload creates a new Version record and updates current_version_id when selected
4) Presentation publish flow
   - Creates PresentationPage and related PresentationItem records
5) Presentation view
   - Loads the correct selected versions and displays playable/visible previews

How integration tests will be run (planned):
- Flask test client + SQLite test database
- Automated route tests verifying DB writes and expected responses

Notes:
Once implemented, this folder will include the test scripts and exact run instructions.