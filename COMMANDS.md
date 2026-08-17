# COMMANDS.md

Every command needed to run **Match Quality Insight** from a clean machine, written for
Windows 10 and 11 with PowerShell.

This file assumes no prior setup and explains what each command does. If you already have
Docker Desktop, jump to [Route A](#route-a-docker) and you will be running in about five
minutes.

For what the project *is* and what it found, see [README.md](README.md) and
[ANALYSIS.md](ANALYSIS.md).

---

## Contents

1. [How the pieces fit together](#1-how-the-pieces-fit-together)
2. [Route A: Docker](#route-a-docker)
3. [Route B: Manual setup](#route-b-manual-setup)
   - [B1. Install the tools](#b1-install-the-tools)
   - [B2. Install PostgreSQL](#b2-install-postgresql)
   - [B3. Create the database and user](#b3-create-the-database-and-user)
   - [B4. Connect the database to the project](#b4-connect-the-database-to-the-project)
   - [B5. Set up the backend](#b5-set-up-the-backend)
   - [B6. Load the data](#b6-load-the-data)
   - [B7. Start the API](#b7-start-the-api)
   - [B8. Start the frontend](#b8-start-the-frontend)
4. [Running the tests](#4-running-the-tests)
5. [Verifying the whole stack](#5-verifying-the-whole-stack)
6. [Stopping everything](#6-stopping-everything)
7. [Resetting and clearing caches](#7-resetting-and-clearing-caches)
8. [Troubleshooting](#8-troubleshooting)
9. [Publishing to GitHub](#9-publishing-to-github)
10. [Command cheat sheet](#10-command-cheat-sheet)

---

## 1. How the pieces fit together

Three processes have to be running, and they start in this order because each depends on
the one before it.

```
  PostgreSQL              Backend API                Frontend
  port 5432       <---    port 8000        <---      port 5173
  the four CSVs           FastAPI: SQL +             React: fetches JSON
  as real tables          statistics, JSON out       and draws the charts
```

| Piece | What it does | How you know it is up |
|---|---|---|
| PostgreSQL | Stores the four CSVs as relational tables | `psql -U mqi -d mqi -c "SELECT 1;"` returns a row |
| Backend API | Runs the SQL, computes AUC / Wilson intervals / PSI, serves JSON | <http://localhost:8000/api/health> returns `{"status":"ok"}` |
| Frontend | Consumes the API and renders the dashboard | <http://localhost:5173> loads with numbers, not errors |

The frontend never touches the database or the CSVs. It only ever talks to the API.

**Two ways to run this.** Route A (Docker) starts all three for you in one command and is
the fastest way to see the dashboard, because it brings its own PostgreSQL, so nothing needs to be
installed locally. Route B (manual) is what you need to run the test suite, use a debugger,
or inspect the database directly. Both use the same credentials, so you can switch between
them freely.

> **The two routes cannot run at the same time.** Both want port 5432. See
> [section 8](#8-troubleshooting) for the one command that resolves it.

---

## Route A: Docker

The only prerequisite is
[Docker Desktop](https://www.docker.com/products/docker-desktop/). Docker Desktop on
Windows needs WSL 2 and hardware virtualisation enabled in your BIOS; its installer walks
you through both.

### A1. Confirm the Docker *engine* is running

This matters more than it sounds. Docker is two separate things: a command-line tool, and a
background engine that does the actual work. Checking the version only proves the tool is
installed and tells you nothing about the engine:

```powershell
docker --version          # NOT a readiness check. This works even with the engine down
```

The real check is:

```powershell
docker info
```

If that prints a block starting with `Server:`, you are ready. If it fails with
`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`, the
engine is not running: **open Docker Desktop from the Start menu**, wait for the whale icon
in the system tray to stop animating, and run `docker info` again.

### A2. Start the stack

From the repository root:

```powershell
docker compose up --build
```

The first run takes a few minutes while the images build. Watch for these lines, which mean
the CSVs loaded successfully:

```
backend-1  | candidates           1500 rows
backend-1  | jobs                   80 rows
backend-1  | applications         6000 rows
backend-1  | recruiter_events    11758 rows
backend-1  | Load complete.
```

Then open:

- Dashboard: <http://localhost:5173>
- Interactive API docs: <http://localhost:8000/docs>

To stop: press `Ctrl+C`, then run `docker compose down`.

> **If you get `port is already allocated` for 5432**, you also have PostgreSQL installed
> natively and its Windows service is running. Stop it and try again:
> `Stop-Service postgresql-x64-18`. The two cannot share the port.

---

## Route B: Manual setup

Everything below is run in **PowerShell**, from the repository root unless a step says
otherwise.

### B1. Install the tools

| Tool | Version | Where |
|---|---|---|
| PostgreSQL | 18 (16 or newer works) | <https://www.postgresql.org/download/windows/> |
| Python | 3.12 or newer | <https://www.python.org/downloads/windows/> |
| Node.js | 20 or newer (LTS) | <https://nodejs.org/> |
| Git | any recent | <https://git-scm.com/download/win> |

Two Windows-specific traps when installing Python:

- Tick **"Add python.exe to PATH"** on the first installer screen. Without it, typing
  `python` opens the Microsoft Store instead of running Python.
- If `python` still opens the Store afterwards, turn off the alias:
  **Settings → Apps → Advanced app settings → App execution aliases**, and switch off
  `python.exe` and `python3.exe`.

Verify all four. Open a **new** PowerShell window first, because PATH changes only apply to
windows opened after the install:

```powershell
python --version    # expect 3.12.x or newer
node --version      # expect v20.x or newer
npm --version
git --version
```

### B2. Install PostgreSQL

Download the EDB installer from the link above, for example
`postgresql-18.6-1-windows-x64.exe`.

> **Run the installer as Administrator.** Right-click the `.exe` → **Run as administrator**.
> Without elevation the installer can copy the program files but fail to register the
> Windows service, which leaves you with a `psql.exe` on disk and no database server
> running. That failure is silent and confusing. See
> [section 8](#no-postgresql-service-was-registered) if it has already happened.

Notes on the screens that matter:

- **Components**: keep *PostgreSQL Server* and *Command Line Tools*. pgAdmin 4 is optional
  but useful for browsing tables visually. Stack Builder is not needed.
- **Installation directory**: default `C:\Program Files\PostgreSQL\18`.
- **Data directory**: default `C:\Program Files\PostgreSQL\18\data`.
- **Password**: the installer asks for a password for the `postgres` superuser.
  **Write it down.** There is no recovery process, and you need it in the next step.
- **Port**: leave it at `5432`.
- **Locale**: leave it at the default.

The installer registers PostgreSQL as a Windows service that starts automatically on boot.
Confirm it exists and is running:

```powershell
Get-Service postgresql*
```

Expected:

```
Status   Name                DisplayName
------   ----                -----------
Running  postgresql-x64-18   postgresql-x64-18 - PostgreSQL Server 18
```

If it says `Stopped`:

```powershell
Start-Service postgresql-x64-18
```

**If the command prints nothing at all**, no service was registered, which is a different
problem from a stopped one, and it is fixable. Go to
[section 8](#no-postgresql-service-was-registered).

Adjust `18` throughout this file if you installed a different major version. The number
always matches the folder name under `C:\Program Files\PostgreSQL\`.

#### Making `psql` available in PowerShell

The installer does **not** add PostgreSQL's tools to your PATH, so typing `psql` gives
`'psql' is not recognized`. Pick one of these:

**Option 1: use the bundled shell.** Search the Start menu for **SQL Shell (psql)**. It
opens a terminal already connected. Press Enter through the four prompts (Server, Database,
Port, Username) to accept the defaults, then enter your `postgres` password. Commands go
after the `postgres=#` prompt and must end with a semicolon.

**Option 2: add it to PATH for the current window only.** Useful for one-off work:

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\18\bin"
```

**Option 3: add it permanently.** Recommended, since you will use `psql` repeatedly:

```powershell
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Program Files\PostgreSQL\18\bin",
    "User"
)
```

Then **close and reopen PowerShell** and verify:

```powershell
psql --version
```

### B3. Create the database and user

PostgreSQL after installation is an empty, locked filing cabinet. You create a dedicated
login for this project and a database that login owns. Using a project-specific user rather
than the superuser is normal practice: the application gets exactly the access it needs and
nothing more.

```powershell
psql -U postgres -c "CREATE USER mqi WITH PASSWORD 'mqi';"
psql -U postgres -c "CREATE DATABASE mqi OWNER mqi;"
```

Each command prompts for the **`postgres` superuser password** you set during installation.
Expected output:

```
CREATE ROLE
CREATE DATABASE
```

Confirm the new user can log in:

```powershell
psql -U mqi -d mqi -c "SELECT version();"
```

This prompts for the **`mqi`** password, which is `mqi`. It should print the PostgreSQL
version banner.

> These credentials match `docker-compose.yml` exactly, which is what lets you move between
> Route A and Route B without editing configuration. They are deliberately trivial because
> this is a local analysis project with no authentication layer and no production
> deployment, per the assignment brief.

To avoid retyping the password on every command in this window:

```powershell
$env:PGPASSWORD = "mqi"
```

That lasts until you close the window.

### B4. Connect the database to the project

The application does not guess where the database is. It reads a file called `.env` in the
repository root. Copy the template:

```powershell
Copy-Item .env.example .env
```

The defaults match the user and database you just created, so no edits are needed. Change
`DATABASE_URL` only if you chose a different port or password:

```
DATABASE_URL=postgresql+psycopg://mqi:mqi@localhost:5432/mqi
                                  ^^^  ^^^           ^^^^  ^^^
                                  user pass          port  database
```

`.env` is listed in `.gitignore` and is never committed, since it can hold real credentials on
other machines. `.env.example` is the committed template.

> **A real environment variable always beats `.env`.** If your PowerShell profile or system
> settings define `DATABASE_URL`, that value wins and the file is silently ignored. Check
> with `Get-ChildItem Env:DATABASE_URL`; clear it for the current window with
> `Remove-Item Env:DATABASE_URL`.

### B5. Set up the backend

A virtual environment is a private folder of Python libraries belonging to this project
only, so its dependencies cannot collide with anything else installed on your machine.

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Your prompt now starts with `(.venv)`. That prefix means the environment is active, and
**every backend command below assumes you can see it.** If you open a new terminal, you
must activate again.

> **If activation fails** with a red *"running scripts is disabled on this system"* error,
> Windows is blocking PowerShell scripts by default. Allow them for this window only:
>
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```
>
> Then run the activation command again. `-Scope Process` means nothing changes permanently.

Install the backend and its dependencies:

```powershell
pip install -e ".[dev]"
```

`-e` installs in editable mode, so your code changes take effect without reinstalling.
`[dev]` adds pytest and scikit-learn, which are used only to cross-check the hand-written
AUC in the tests and are never imported by the running application.

### B6. Load the data

This reads the four CSVs from `data/`, creates the tables defined in `backend/sql/schema.sql`,
and bulk-loads them with PostgreSQL's `COPY`. It drops everything first, so it is safe to
re-run any time you want a clean database.

Still inside `backend`, with `(.venv)` active:

```powershell
python -m scripts.load_data
```

Expected output:

```
candidates           1500 rows
jobs                   80 rows
applications         6000 rows
recruiter_events    11758 rows
Load complete.
```

The brief describes `recruiter_events` as roughly 12,000 rows. The supplied file contains
11,758, and all of them load.

Confirm the data landed, and that the `scored_applications` view every metric query reads
from was created:

```powershell
psql -U mqi -d mqi -c "SELECT count(*) FROM applications;"
psql -U mqi -d mqi -c "SELECT count(*) FROM scored_applications WHERE is_decided;"
```

Expect `6000` and `5496`. On Docker, prefix both with `docker compose exec db`.

### B7. Start the API

```powershell
uvicorn app.main:app --reload
```

`--reload` restarts the server automatically whenever you save a Python file.

**This terminal is now occupied.** The server holds it until you press `Ctrl+C`, and closing
the window stops the API.

Check it in a browser:

- <http://localhost:8000/api/health>: should show `{"status":"ok"}`
- <http://localhost:8000/docs>: interactive documentation where every endpoint can be run
  from the browser

### B8. Start the frontend

Open a **second** PowerShell window. The first one is busy running the API.

```powershell
cd frontend
npm install
npm run dev
```

`npm install` downloads the React and Vite packages into `node_modules`. It takes a minute
or two the first time and is only needed again when `package.json` changes.

Vite prints:

```
  VITE v5.4.x  ready in ... ms

  ➜  Local:   http://localhost:5173/
```

Open <http://localhost:5173>. The Overview tab shows the headline metrics; the Segments tab
is the per-dimension drill-down.

The frontend defaults to `http://localhost:8000` for the API, so no configuration is needed
when both run locally.

---

## 4. Running the tests

From `backend`, with `(.venv)` active:

```powershell
pytest
```

Expected:

```
45 passed in 4.30s
```

The tests need no database and no running API. They exercise the statistics and the
composition layer directly, which is the point of keeping those layers free of SQL. They are
therefore the one part of the project you can run before PostgreSQL is working.

Useful variations. The `cd backend` is repeated deliberately: the two path-based commands
resolve relative to the current folder, so from the repository root they report
`file or directory not found`.

```powershell
cd backend
pytest -v                              # one line per test, with names
pytest tests/test_compute.py           # statistics only: AUC, Wilson, precision@k, PSI
pytest tests/test_service.py           # composition: disagreement, small samples, quality gate
pytest -k "auc"                        # only tests with "auc" in the name
pytest -x                              # stop at the first failure
```

---

## 5. Verifying the whole stack

A quick end-to-end check with both servers running. In PowerShell use `Invoke-RestMethod`
rather than `curl`, because in PowerShell `curl` is an alias for a different command with
different behaviour.

```powershell
# 1. Database is reachable and populated
psql -U mqi -d mqi -c "SELECT count(*) FROM applications;"
```

If you started the stack with Docker (Route A) you will not have `psql` on your machine,
and the command above returns `'psql' is not recognized`. That is expected. Run it inside
the database container instead, which needs nothing installed locally:

```powershell
docker compose exec db psql -U mqi -d mqi -c "SELECT count(*) FROM applications;"
```

```powershell

# 2. API is alive
Invoke-RestMethod http://localhost:8000/api/health

# 3. The headline finding, straight from the API
$overview = Invoke-RestMethod http://localhost:8000/api/overview
$overview.pooled
$overview.excluding_healthcare
```

`pooled` should report a rule AUC near 0.689 against an LLM AUC near 0.724.
`excluding_healthcare` should flip the ranking to roughly 0.782 against 0.729. That
reversal is Finding 1 in [ANALYSIS.md](ANALYSIS.md).

Every endpoint, if you want to check them all:

```powershell
$endpoints = @(
  "health", "overview", "effectiveness", "agreement",
  "segments?dimension=job_family", "segments?dimension=country",
  "segments?dimension=seniority", "segments?dimension=model_version",
  "segments?dimension=profile_band",
  "calibration?scorer=llm", "calibration?scorer=rule",
  "recruiter-behaviour", "quality-gate"
)
foreach ($e in $endpoints) {
  $r = Invoke-WebRequest "http://localhost:8000/api/$e" -UseBasicParsing
  "{0}  /api/{1}" -f $r.StatusCode, $e
}
```

All thirteen should return `200`. An unknown dimension is rejected on purpose:

```powershell
Invoke-RestMethod "http://localhost:8000/api/segments?dimension=bogus"
```

returns HTTP 422, the dimension whitelist refusing an unrecognised value.

---

## 6. Stopping everything

| What | How |
|---|---|
| Backend API | `Ctrl+C` in its terminal |
| Frontend | `Ctrl+C` in its terminal |
| Virtual environment | `deactivate` (the `(.venv)` prefix disappears) |
| PostgreSQL service | `Stop-Service postgresql-x64-18`, required before using Docker |
| Docker stack | `Ctrl+C`, then `docker compose down` |

If `Ctrl+C` does not free a port, find and stop the process holding it:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess
Stop-Process -Id <the number printed above>
```

---

## 7. Resetting and clearing caches

Start at the top and work down. The first two solve almost everything.

### 7.1 Reset the database

The loader drops and recreates every table, so re-running it is the normal reset:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m scripts.load_data
```

For a completely fresh database, for example after editing `schema.sql` in a way that
leaves an orphaned object behind:

```powershell
psql -U postgres -c "DROP DATABASE IF EXISTS mqi;"
psql -U postgres -c "DROP USER IF EXISTS mqi;"
psql -U postgres -c "CREATE USER mqi WITH PASSWORD 'mqi';"
psql -U postgres -c "CREATE DATABASE mqi OWNER mqi;"
cd backend
python -m scripts.load_data
```

Drop the database before the user, because PostgreSQL refuses to drop a role that still owns
objects.

### 7.2 Clear Python caches

Stale `.pyc` files after switching branches, and a confused pytest cache, both produce
puzzling failures:

```powershell
cd backend
Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue
```

Rebuild the virtual environment from scratch if dependencies get into a bad state:

```powershell
deactivate
Remove-Item -Recurse -Force .venv
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

### 7.3 Clear frontend caches

Vite keeps a pre-bundled dependency cache that occasionally goes stale after a dependency
change. Clearing it is the usual fix for "the code is right but the page is wrong":

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules\.vite -ErrorAction SilentlyContinue
npm run dev
```

Full reinstall, if that is not enough:

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
npm cache clean --force
npm ci
```

`npm ci` reinstalls strictly from `package-lock.json`, so you get the exact versions this
project was built against. Leave the lock file in place: it is committed on purpose, and
deleting it would let npm resolve newer versions and quietly change your build.

And in the browser, a normal refresh may serve a cached JavaScript bundle. Force a fresh
one with **`Ctrl+Shift+R`**, or open the dashboard in a private window.

### 7.4 Clear Docker caches

Docker stores the database inside a volume, so stopping containers alone does not remove
the data:

```powershell
docker compose down -v            # stop containers AND delete volumes (the database)
docker compose build --no-cache   # rebuild images, ignoring every cached layer
docker compose up
```

Clear the frontend's dependency cache inside the container:

```powershell
docker compose run --rm frontend rm -rf node_modules/.vite
docker compose up --build frontend
```

Reclaim disk space across **all** Docker projects on the machine. This deletes unused
images and volumes belonging to other work too, so read before running:

```powershell
docker system prune -af --volumes
```

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified` | Docker CLI installed, engine not running | Start **Docker Desktop**, wait for the tray icon to settle, confirm with `docker info` |
| `Port 5432 is already allocated` on `docker compose up` | A native PostgreSQL service holds the port | `Stop-Service postgresql-x64-18`, or change the mapping in `docker-compose.yml` to `"5433:5432"` |
| `Get-Service postgresql*` prints nothing | No PostgreSQL service is registered | [See below](#no-postgresql-service-was-registered) |
| `'psql' is not recognized` | PostgreSQL's `bin` folder is not on PATH | [Add it](#making-psql-available-in-powershell), or use the **SQL Shell (psql)** app |
| `'python' is not recognized`, or the Microsoft Store opens | Python not on PATH, or the app execution alias is on | Reinstall with *Add python.exe to PATH*, or disable the alias in Windows Settings |
| `connection refused` on port 5432 | PostgreSQL service is not running | `Start-Service postgresql-x64-18` |
| `password authentication failed for user "mqi"` | `DATABASE_URL` does not match the user you created | Recheck `.env` against [B3](#b3-create-the-database-and-user); confirm no stray `Env:DATABASE_URL` overrides it |
| `database "mqi" does not exist` | [B3](#b3-create-the-database-and-user) was skipped or the database was dropped | Re-run the two `CREATE` commands |
| `Missing CSVs in <path>` | `DATA_DIR` points somewhere the CSVs are not | Remove the `DATA_DIR` line from `.env`, since the default resolves to `<repo root>\data` from any working directory |
| Loader fails on `relation ... does not exist` | Partially applied schema from an interrupted run | Full reset in [7.1](#71-reset-the-database) |
| `running scripts is disabled on this system` | PowerShell execution policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| `address already in use` on 8000 or 5173 | An earlier server is still running | Find and stop it, see [section 6](#6-stopping-everything) |
| Dashboard loads but every panel errors | The API is not running, or CORS is misconfigured | Check <http://localhost:8000/api/health>; confirm `CORS_ORIGIN` in `.env` is `http://localhost:5173` |
| Dashboard shows zeros everywhere | Tables exist but are empty | Re-run `python -m scripts.load_data` |
| `ModuleNotFoundError: No module named 'app'` | Running the loader from the wrong folder, or `(.venv)` not active | `cd backend`, activate, then `python -m scripts.load_data` |
| Code change has no visible effect | Cached bundle or bytecode | [7.2](#72-clear-python-caches) and [7.3](#73-clear-frontend-caches), then `Ctrl+Shift+R` |
| `docker compose` not recognised | Docker Desktop is not installed, or is an old version using `docker-compose` | Install Docker Desktop; on older versions use `docker-compose` with a hyphen |

### No PostgreSQL service was registered

`Get-Service postgresql*` returning **nothing** is different from returning a row that says
`Stopped`. Nothing means Windows has no such service at all, so there is no database server
to start. The usual cause is an installer that was not run as Administrator: it copied the
program files but could not register the service.

Diagnose first:

```powershell
# Is any PostgreSQL service registered under any name?
Get-Service | Where-Object { $_.DisplayName -like "*PostgreSQL*" } | Format-Table Name, Status, StartType

# Did the program files land?
Test-Path "C:\Program Files\PostgreSQL\18\bin\psql.exe"

# Was the database cluster initialised?
Test-Path "C:\Program Files\PostgreSQL\18\data\PG_VERSION"

# Is anything listening on 5432 regardless?
Get-NetTCPConnection -LocalPort 5432 -State Listen -ErrorAction SilentlyContinue
```

Read the result:

| `psql.exe` | `PG_VERSION` | Meaning | Fix |
|---|---|---|---|
| True | True | Files and cluster are fine, only the service is missing | Repair, or register manually. Both are below |
| True | False | Install did not complete; no cluster was created | Re-run the installer as Administrator |
| False | False | Nothing installed at that path | Re-run the installer as Administrator |

**Fix 1: repair the installation (recommended).** Right-click the installer
(`postgresql-18.6-1-windows-x64.exe`) → **Run as administrator**. It detects the existing
installation and completes the parts that failed. Then:

```powershell
Get-Service postgresql*
Start-Service postgresql-x64-18
```

**Fix 2: register the service by hand.** Only if the table above says files and cluster
are both fine. Open PowerShell **as Administrator**:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe" register `
    -N "postgresql-x64-18" `
    -D "C:\Program Files\PostgreSQL\18\data" `
    -U "NT AUTHORITY\NetworkService" `
    -S auto
Start-Service postgresql-x64-18
```

The `-U "NT AUTHORITY\NetworkService"` matters: PostgreSQL refuses to run under an
administrator account, and that is the low-privilege account the official installer uses. If
the service registers but will not start, the reason is written to
`C:\Program Files\PostgreSQL\18\data\log\`.

### A note on line endings

The four source CSVs use Windows line endings (CRLF). PostgreSQL's `COPY` reads either
style, so the loader is unaffected. Git is the part that needs pinning: on Windows,
`core.autocrlf` defaults to `true`, which rewrites CRLF to LF when a file is committed.
That would leave the datasets in the repository byte for byte different from the ones
supplied with the assignment.

The repository therefore ships a `.gitattributes` at its root:

```
* text=auto
*.csv -text
```

`-text` switches conversion off completely for CSVs, so Git stores and restores their exact
bytes on every platform. Note that `text eol=crlf` would *not* do this: it still normalises
the stored blob to LF and only converts on checkout.

Confirm it is working after your first commit. This lists any file Git considers modified
purely because of line endings, and should print nothing:

```powershell
git add --renormalize .
git status --short
```

---

## 9. Publishing to GitHub

From the repository root, with a repository already created on GitHub:

```powershell
git init
git add .
git commit -m "Match Quality Insight: data layer, metrics API, dashboard, analysis"
git branch -M main
git remote add origin https://github.com/<your-username>/match-quality-insight.git
git push -u origin main
```

Before pushing, check what is being committed:

```powershell
git status
```

- **`.env` must not appear.** It is in `.gitignore`. If it shows up, stop and check the
  ignore file before committing.
- **`node_modules/` and `.venv/` must not appear.** Both are ignored.
- **`frontend/package-lock.json` should appear, and should be committed.** It pins exact
  dependency versions so a reviewer's `npm install` reproduces your build.
- **`data/*.csv` should appear, and should be committed.** The four CSVs are what make the
  project reproducible from a clean clone.

Verify the push worked by cloning into a temporary folder and running Route A against it.
That is exactly what your reviewer will do.

---

## 10. Command cheat sheet

**One-time setup**

```powershell
psql -U postgres -c "CREATE USER mqi WITH PASSWORD 'mqi';"
psql -U postgres -c "CREATE DATABASE mqi OWNER mqi;"
Copy-Item .env.example .env
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m scripts.load_data
cd ..\frontend
npm install
```

**Every time: terminal 1 (API)**

```powershell
cd backend
.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

**Every time: terminal 2 (dashboard)**

```powershell
cd frontend
npm run dev
```

**Tests**

```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest
```

**Docker, all of it**

```powershell
Stop-Service postgresql-x64-18 -ErrorAction SilentlyContinue   # free 5432 if it is in use
docker info                      # confirm the engine is up
docker compose up --build        # start
docker compose down -v           # stop and wipe the database
```

**Reset**

```powershell
python -m scripts.load_data                                                       # database
Get-ChildItem -Path . -Include __pycache__ -Recurse -Directory | Remove-Item -Recurse -Force   # python
Remove-Item -Recurse -Force frontend\node_modules\.vite                           # vite
```

**URLs**

| | |
|---|---|
| Dashboard | <http://localhost:5173> |
| API health | <http://localhost:8000/api/health> |
| API docs | <http://localhost:8000/docs> |