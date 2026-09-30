# Verification and release checklist

Verified locally on **30 September 2026**, using Python 3.13.5. This is a working educational application, not a claim of a completed Vercel deployment or a production security certification.

## Completed checks

| Check | Result |
| --- | --- |
| Django test suite | **89 tests passed** |
| `python manage.py check` | No issues |
| `python manage.py makemigrations --check --dry-run` | No migration drift |
| Ruff 0.16.9 lint and format checks | Passed across 57 Python files |
| Coverage 7.16.2 | 94.80% combined statement/branch coverage |
| Statement coverage | 598 of 621 statements, 96.30% |
| Branch coverage | 95 of 110 branches, 86.36% |
| Local schema and fictional demo data | Migrated and seeded successfully |
| Browser walkthrough | Sign in, task list, saved notes, invalid-title response, session-authenticated REST response, and POST sign-out observed |
| Screenshots | Captured from the local running app; fictional records only |

Coverage measures `accounts`, `config`, `tasks`, and `entries`. It excludes tests, migrations, test settings, and the WSGI entrypoint. Initializer tests run in the suite but the initializer is not included in this coverage percentage. Coverage is not proof that every defect or security issue has been eliminated.

The tests include cross-user access denial, owner assignment, HTML and REST mutations, validation, duplicate keys, CSRF, login lockout/cool-off, password-field scrubbing in failed-login metadata, production configuration rules, and private local environment initialization.

## Reproduce the checks

From the project directory with the virtual environment activated:

```bash
python -m pip install -r requirements-dev.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --settings=config.test_settings
ruff check .
ruff format --check .
coverage run manage.py test --settings=config.test_settings
coverage report
python -m pip check
pip-audit -r requirements.txt
```

Do not interpret the last two commands as completed checks here: the limitations below apply. Never point the test configuration at a live customer database.

## Environment limitations

- PyPI/CDN connectivity was unavailable in the authoring environment. Local tests used the exact pinned packages from official upstream GitHub releases/sources where needed. Those temporary source paths and the local virtual environment are **not** included in the delivered ZIP.
- A clean, ordinary `pip install -r requirements-dev.txt` from PyPI still needs to be verified on a network-enabled machine or deployment build. The project contains standard dependency declarations, not the temporary local source workaround.
- `pip check` did **not** pass in the source-assisted local environment: source overrides lacked complete distribution metadata and temporary build dependencies were incomplete. This is an unresolved environment verification item, not a passed dependency-integrity check.
- A vulnerability audit (`pip-audit`) was **not performed**. Run it against the pinned runtime dependencies before public deployment and review its results.
- PostgreSQL, the psycopg binary wheel, database-provider pooling, and production TLS were **not integration-tested**. Unit tests use isolated SQLite; production configuration checks are not a substitute for a real PostgreSQL test.
- No Vercel account, project, database, paid resource, or public URL was created. Hosting, account permissions, platform limits, and persistence across deployments remain to be verified.

## Staging release gate

Use a separate staging database and fictional accounts. Follow [VERCEL.md](VERCEL.md) before proceeding.

- [ ] Install the locked runtime dependencies normally; run `pip check` and a vulnerability audit.
- [ ] Confirm the intended environment, exact hostnames, secure origins, strong private signing key, PostgreSQL SSL, and signup policy.
- [ ] Back up the intended database; review and apply migrations deliberately.
- [ ] Run Django deployment checks and review warnings. The deliberately short HSTS duration and disabled subdomain/preload options require a domain-specific decision.
- [ ] Sign in, create/edit/complete a task, save/edit a note, refresh, and verify persisted values.
- [ ] Use a private token over HTTPS to list/create/update/delete only the intended account's records.
- [ ] Confirm missing credentials are rejected and a second user gets 404 for another user's record.
- [ ] Confirm browser CSRF protection, logout, lockout recovery, and ordinary validation.
- [ ] Check static assets, error pages, database connections, and persistence after a new deployment.
- [ ] Revoke test tokens; configure backups, monitoring, retention, traffic controls, and account-recovery procedures before broader use.

## Logging and login protection

The application request logger records a generated request ID, method, status, and duration—not query strings, request bodies, passwords, or authorization headers. Platform/access logs have their own retention and access policies and need separate review.

Django Axes stores failed-login records in the database, including username/IP and scrubbed form metadata. Successful-login access logging is disabled. The username **or** IP lockout rule can affect multiple workshop participants sharing a network. In a disposable local lab, `python manage.py axes_reset` clears all failed attempts; in production, investigate the cause and use a targeted administrator recovery procedure instead of routinely clearing all protection state.

## Screenshot provenance

`screenshots/login.png`, `tasks.png`, `entries.png`, `validation.png`, and `api.png` show the real local application using fictional Asha demo records. They contain no real login password, API token, production database URL, or deployment credentials. Window size may limit the visible lower portion of a page; screenshots document the visible state, not a complete API schema.

The updated presentation keeps the original 70 workshop slides and appends an eight-slide implementation guide. Earlier conceptual screens and code excerpts are teaching illustrations; the implementation appendix uses these actual local screenshots. See [TEACHING_MAP.md](TEACHING_MAP.md) for intentional differences between the teaching excerpts and the delivered project.
