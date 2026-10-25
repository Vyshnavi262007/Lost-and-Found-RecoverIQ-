# RecoverIQ - Smart Campus Lost & Found Platform

*Lost Something? Let's Bring It Back.*

A campus-only lost-and-found web app: verified students report lost/found items, an explainable matching engine suggests possible matches, owners submit ownership claims, and authorised staff verify claims and record handovers.

## IMPORTANT - read first: what was and was not verified

This project was generated in a sandbox with **no internet access**, so Django, DRF and the npm packages could not be installed there. Therefore:

| Check | Status |
|---|---|
| Python syntax of every backend file (`compileall`) | Done, passes |
| Crude undefined-name scan of the backend | Done, 0 findings |
| Matching-engine unit tests (`tests/test_matching_engine.py`, pure Python) | **Actually run: 11 tests pass** |
| Django/API tests (auth, permissions, reports, images, search, matching, comments, messages, claims, inventory/handover, notifications, admin) | **Written but NOT run.** Run them yourself (see Testing). |
| Database migrations | **Not generated** (needs Django). `setup-backend.ps1` runs `makemigrations` + `migrate` for you. |
| JSX syntax of all 38 frontend files (TypeScript parser) + import/export check | Done, passes |
| `npm run build` / ESLint | **NOT run** (no npm registry access) |
| Running the app end to end in a browser | **NOT done** |

Expect that a first run may surface small bugs. Run the tests first; they were written to exercise the full acceptance workflow, so failures will point straight at the problem.

## Features

* Roles: Student, Faculty, Campus staff (configurable `can_review_claims` / `can_release_items`), Administrator. Roles are enforced on the backend; the register API ignores any role sent by the client.
* Registration accepts any academic email (`.edu`, `.ac.in`, `.edu.in`, `.ac.uk`, `.edu.au`, ... and their subdomains; fully configurable, `*` allows any address). The sign-up form has an **I am a** selector: Student, Faculty, Campus staff, Administrator. Staff and Administrator are only *requests*: the account works as a normal member until an existing administrator approves it. A real email-verification token flow (dev mode shows the link on screen when SMTP is not configured). Staff access is requested at sign-up and approved by an admin. Admins can also verify accounts manually.
* Lost/found reports with up to 5 validated photos, private identifying details (never in public responses), edit/close, bookmarks, public comments, abuse reports, private messaging.
* Feed with search, category/type/location/date/status filters, newest/relevance sort, pagination, loading skeletons and empty states.
* **Matching engine** (`backend/apps/reports/matching.py`): weighted, configurable, explainable. Category 20%, TF-IDF cosine text 25%, campus-grid location proximity 20%, date proximity 15%, visual 20%. Missing components are dropped and weights renormalised. Excludes same-type, self and incompatible categories; no duplicate matches; recalculated on edit; failures never break report submission. Shown as a "Similarity estimate".
* Visual similarity is **optional and off by default**. It activates only if `torch`/`torchvision` and the pretrained MobileNetV3 weights are available (see below). When inactive the UI/API report `visual: null` and the weight is redistributed.
* Persisted in-app notifications (matches, comments, messages, claims, handovers, status), bell with unread count, mark-read/all.
* Claim workflow: Pending -> Under review -> Approved/Rejected/Withdrawn -> Completed, with timeline, reviewer + timestamp, rejection reason, private evidence (authorised download only), dispute -> admin review, DB constraints preventing two winning claims per item. Items held by staff can be released only by staff/admin with release permission via a recorded handover; a similarity score never releases an item.
* Staff inventory (reference numbers, storage location, claims, handover history, scheduling/confirmation with generated handover reference).
* Admin: real-aggregation dashboard and charts (Recharts), user management, staff approvals, moderation, duplicate detection, abuse queue, disputes, categories, campus locations (with coordinates), audit log viewer, system settings (weights, thresholds, expiry, notification toggles).

## Tech stack

React 18 + Vite + Tailwind CSS 3 + React Router + Axios + Lucide + Recharts | Django 5.1 + Django REST Framework (token auth) | SQLite for local development, PostgreSQL optional | local media storage.

## Folder structure

```
RecoverIQ/
  README.md  .env.example  .gitignore  docker-compose.yml
  setup-backend.ps1  setup-frontend.ps1
  backend/
    manage.py  requirements.txt  requirements-visual.txt
    config/            settings, urls, wsgi
    apps/
      accounts/        User model (roles), auth API, permissions
      core/            campus, locations, categories, audit log, notifications, site settings, seed_demo, expire_reports
      reports/         reports, images, matches, comments, bookmarks, abuse; matching.py (engine), matching_service.py, visual.py
      messaging/       conversations and messages
      claims/          claims, evidence, inventory, handovers + services.py (all business rules)
      adminapi/        admin APIs, analytics, dashboards
    tests/             Django tests + pure-Python engine tests
    media/             public item photos (dev)   private_media/  claim evidence (never served by URL)
  frontend/
    package.json  vite.config.js  tailwind.config.js
    src/ api/ components/ layouts/ pages/{public,student,staff,admin}/ hooks/ context/ utils/
```

## Windows setup (PowerShell + VS Code)

Prerequisites: **Python 3.11-3.13** (tick "Add python.exe to PATH"), **Node.js 20+ LTS**, VS Code. Docker is NOT required.

1. Extract `RecoverIQ.zip` (right-click -> Extract All), open the `RecoverIQ` folder in VS Code (File -> Open Folder), then Terminal -> New Terminal.
2. **Terminal 1 - backend** (one-time setup, then run):
```powershell
powershell -ExecutionPolicy Bypass -File .\setup-backend.ps1
cd backend
.\.venv\Scripts\python.exe manage.py runserver
```
   The setup script creates the virtual environment, installs requirements, copies `.env.example` to `backend\.env`, runs `makemigrations` + `migrate`, and loads demo data. (Manual equivalent: `python -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, `pip install -r requirements.txt`, `python manage.py makemigrations accounts core reports messaging claims adminapi`, `python manage.py migrate`, `python manage.py seed_demo`.)
3. **Terminal 2 - frontend** (open a second terminal):
```powershell
cd frontend
npm install
npm run dev
```
4. Open **http://localhost:5173** (frontend). API: **http://127.0.0.1:8000/api/** . Django admin: http://127.0.0.1:8000/django-admin/ (admin account below).

If PowerShell blocks scripts: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Demo logins (development only, fictional data)

| Role | Email | Password |
|---|---|---|
| Administrator | admin@campus.example.edu | `RecoverIQ-Admin-2026!` |
| Staff (can review + release) | security@campus.example.edu | `RecoverIQ-Demo-2026!` |
| Staff (review only, cannot release) | warden@campus.example.edu | `RecoverIQ-Demo-2026!` |
| Faculty | prof.iyer@campus.example.edu | `RecoverIQ-Demo-2026!` |
| Students | asha@ / ravi@ / meera@ / kiran@ `students.campus.example.edu` | `RecoverIQ-Demo-2026!` |

Change the passwords with `DEMO_ADMIN_PASSWORD` / `DEMO_USER_PASSWORD` in `.env` before seeding. `seed_demo` is idempotent (safe to re-run). A pending staff request (`hk.request@campus.example.edu`) demonstrates the approval queue.

## Try the core workflow

1. Log in as **asha**: a lost "Black leather wallet" already exists with a computed match to the staff-held found wallet (open *Smart matches*). Or submit your own lost report with a photo.
2. Log in as another student (or `security@`) and submit a matching found report. The matching runs synchronously and creates a match + notification for the owner.
3. As the owner, open the found report -> **This is mine - claim item** and answer the questions.
4. A reviewer (`security@` for items held at the desk; the finder for peer-held items; or admin) opens the claim, compares answers with the hidden details, and approves or rejects.
5. For desk-held items: `security@` schedules a handover on the claim page, then **Confirm item handed over**. For peer items the finder clicks **Confirm I handed the item over**.
6. The student dashboard ("Items recovered") and the admin analytics update from the database.

## Testing

```powershell
cd backend
.\.venv\Scripts\python.exe manage.py test tests -v 2     # Django + API tests (written, not yet run by the author)
.\.venv\Scripts\python.exe -m unittest tests.test_matching_engine -v   # engine tests (run and passing)
cd ..\frontend
npm run build                                           # production build check
```
Covered: registration/login/password hashing/change-password, role access to student/staff/admin endpoints, report creation, image validation, server-side validation, search/filter/pagination, private-field protection, comment and message permissions, matching (scoring, same-type exclusion, category exclusion, no duplicates, dismiss, recalculation), the full claim -> approval -> handover -> returned workflow, conflicting-claim prevention, evidence privacy, held-item release authorisation, notifications, analytics reflecting changes.

## Optional: image-embedding visual similarity

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-visual.txt
```
Needs roughly 1 GB of disk for PyTorch, runs on CPU, and downloads MobileNetV3-Small weights (~10 MB) on first use (internet needed once). If anything is missing, the feature stays disabled automatically. This path has not been executed by the author.

## Configuration notes

* Allowed email domains: `ALLOWED_COLLEGE_EMAIL_DOMAINS` (comma-separated; each entry also matches subdomains, so `edu` accepts `student.mit.edu` and `ac.in` accepts `x.iitb.ac.in`). Domain checks alone do not prove identity, which is why email verification (or manual admin verification) is required before login.
* Emails: with no SMTP configured, emails print to the backend console and nothing claims to have been delivered. In notifications, only in-app notifications exist.
* Matching weights/thresholds, expiry days and notification toggles: Admin -> System settings. Schedule `python manage.py expire_reports` daily to expire old open reports.
* PostgreSQL: `docker compose up -d`, then set `DB_ENGINE=postgres` and the `POSTGRES_*` values in `.env`, and re-run `migrate` and `seed_demo`.

## Troubleshooting

* *"Cannot reach the server"* in the browser: the backend is not running on port 8000.
* *`makemigrations` says "No changes"* after the first run: normal; the migrations now exist.
* *Images do not appear*: the Vite dev server proxies `/media` to Django; make sure `DJANGO_DEBUG=True` locally.
* *403 "email_unverified" on login*: use the dev link shown after registering, or Admin -> Users -> "Verify manually".
* *Port in use*: `runserver 8001` and start Vite with `$env:VITE_BACKEND_URL="http://127.0.0.1:8001"; npm run dev`.

## Production deployment notes

Set `DJANGO_DEBUG=False`, a strong `DJANGO_SECRET_KEY`, real `DJANGO_ALLOWED_HOSTS`, `FRONTEND_ORIGINS`, `DEV_EXPOSE_VERIFICATION_LINK=False`, SMTP settings and PostgreSQL. Serve Django with gunicorn/uvicorn behind HTTPS, build the frontend (`npm run build`) and serve `dist/` from a web server that also proxies `/api` and `/media`. Public item photos should move to object storage (e.g. S3 via `django-storages`: set `DEFAULT_FILE_STORAGE`/`STORAGES["default"]`); keep `private_media` (claim evidence) on private, non-public storage and keep serving it only through the authorised download endpoint. Run `expire_reports` on a schedule and back up the database.

## Security notes and limitations

* Token auth is stored in `localStorage` (simple, not CSRF-prone, but readable by injected scripts). Consider httpOnly-cookie sessions for stricter deployments.
* Rate limiting uses DRF throttles with the default per-process cache; use Redis/Memcached when running several workers.
* Matching runs synchronously in the request (adequate for campus scale); move it to a task queue for very large datasets.
* Not implemented: user-to-user blocking, abuse-reporting of individual private messages, email notifications, draft saving on the server (drafts are kept in the browser), automatic image-model download management, a full accessibility audit.
* Privacy/Terms pages are templates and need legal review.
