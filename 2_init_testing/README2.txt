CollabSpace — Unit Testing (Module 8)

Status:
Unit testing is not implemented at this stage of the project.

Reason:
The current build is focused on delivering an MVP that demonstrates core end-to-end functionality
(UI input → backend processing → SQLite storage → UI updates) for the midterm demo.

Planned unit tests (for the final phase):
1) Asset type validation
   - Confirm only supported media types (image/audio) are accepted by the upload flow
2) Versioning logic
   - Confirm version_number increments correctly per asset
   - Confirm current_version_id updates when “Set as current” is selected
3) Presentation building
   - Confirm a presentation page correctly stores selected asset/version pairs

How unit tests will be run (planned):
- Python unittest or pytest
- Command example:
  pytest
(or python -m unittest)

Notes:
Once unit tests are added, this folder will include the test files and any setup instructions.