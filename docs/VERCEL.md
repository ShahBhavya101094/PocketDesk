# Vercel deployment guide

This project is deployment-ready source code, not a hosted service. You need your own Vercel account, project, and PostgreSQL database. Nothing here creates accounts, accepts paid plans, uploads credentials, or publishes the application automatically.

## Deployment layout

```text
HTTPS client
    |
Vercel ingress
    +-- /static/  -> collected assets on the CDN
    |
config.wsgi:application
    |
Django views / DRF ViewSets
    |
External PostgreSQL with SSL
    +-- users, tasks, entries
    +-- sessions, API tokens, login-protection records
```

Vercel recognizes `manage.py` and the configured WSGI application. The repository selects Python 3.13 and configures `STATIC_ROOT`; the framework integration runs `collectstatic`. Do not add old `@vercel/python` builds/rewrites examples or a separate development-server process. [Vercel Django documentation](https://vercel.com/docs/frameworks/full-stack/django), [Python runtime configuration](https://vercel.com/docs/functions/runtimes/python).

## 1. Choose the correct root

- If your repository contains this entire workshop workspace, set **Root Directory** to `pocketdesk`.
- If you upload only the `pocketdesk` folder's contents as a standalone repository, use the repository root.
- The selected directory must contain `manage.py`, `requirements.txt`, `pyproject.toml`, and `config/`.
- Use Vercel's Django framework detection. Leave Build Command and Output Directory at the framework defaults.
- No custom build command runs database migrations in this project.

The `.vercelignore` excludes local environments, databases, tests, and documentation assets from deployment uploads. Keep the full documentation and PPTX in your source repository or local bundle.

## 2. Prepare PostgreSQL

Use an external PostgreSQL service compatible with your network and deployment region. Select its SSL connection string and use a pooled runtime connection if the provider offers one. Do not use the development SQLite file on Vercel.

Set separate databases or isolated provider branches for **Preview** and **Production**. Preview code and pull requests must never receive production database credentials. Some transaction poolers require a direct connection for migrations; follow your database provider's DDL guidance.

The app uses request-scoped connections (`CONN_MAX_AGE=0`), a connection timeout, and no server-side cursors. Production accepts PostgreSQL only and requires `sslmode=require` or stronger. Prefer `verify-full` with the appropriate CA configuration when your provider supports it.

Production does not automatically copy local SQLite records. Create intended production accounts separately. Plan and validate a deliberate data transfer if you need existing data.

## 3. Configure environment variables

Set these in the Vercel project's **Settings → Environment Variables** for the intended environment. Replace every example domain. Never copy a demonstration signing key into production.

| Variable | Production value / purpose |
|---|---|
| `DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | A new random value of at least 50 characters |
| `DATABASE_URL` | Your PostgreSQL SSL connection string |
| `DJANGO_ALLOWED_HOSTS` | Exact hosts, comma-separated, without scheme or path |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Exact matching HTTPS origins, comma-separated, without a trailing slash |
| `PUBLIC_SIGNUP_ENABLED` | `False` until you deliberately open registration |

For example, a custom domain and stable project domain could be configured as:

```text
DJANGO_ALLOWED_HOSTS=pocketdesk.example.com,your-project.vercel.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://pocketdesk.example.com,https://your-project.vercel.app
```

These are placeholders, not working deployments. Wildcards such as `*` and `.vercel.app` are intentionally rejected. For a preview, add its exact authorized hostname and origin or assign a stable protected preview domain. Do not broaden the host policy just to silence a 400 response.

Generate a signing key locally, then copy it privately into Vercel:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Do not project that terminal or share its output. Treat the signing key and database URL as secrets. Do not set `DJANGO_SETTINGS_MODULE=config.test_settings` on Vercel. The WSGI entrypoint uses production-capable `config.settings`.

Vercel supplies `VERCEL=1`; the app uses that boundary for proxy trust and refuses debug mode on the platform. It does not automatically trust arbitrary `*.vercel.app` hosts.

## 4. Link the CLI, if using terminal deployment

Install a current official Vercel CLI using your normal Node.js environment. From the `pocketdesk` directory:

```bash
npm install --global vercel
vercel login
vercel link
```

Choose the intended account/team and project. These commands may create or link external resources; review their prompts and any costs yourself. You may instead connect a Git repository in the Vercel dashboard.

Activate the Python virtual environment and install project dependencies before running remote-environment management commands locally. The terminal machine must also be able to reach your PostgreSQL service.

## 5. Review and apply migrations deliberately

First inspect your linked project and the environment being targeted. A production command below writes to the production database. Take a backup first when it already contains data.

```bash
vercel env run -e production -- python manage.py check --deploy
vercel env run -e production -- python manage.py showmigrations
vercel env run -e production -- python manage.py migrate --plan
```

After reviewing the plan and confirming the database target:

```bash
vercel env run -e production -- python manage.py migrate
```

The CLI injects the linked environment's variables without requiring a secrets file. [Vercel CLI environment commands](https://vercel.com/docs/cli/env).

Use the corresponding `-e preview` commands for a separate preview database. For an established application, use backward-compatible schema changes so the old and new deployments can coexist during rollout. Dropping columns or reversing migrations is not an automatic rollback strategy. Never run migrations in a view, WSGI import, or every preview build.

The Django deploy check intentionally reports HSTS subdomain/preload warnings: the starter uses a short HSTS policy and does not commit all subdomains to permanent HTTPS. Review those flags for your actual domain before enabling them. See the current validation report/check output rather than assuming every warning applies identically to every host.

## 6. Deploy and provision accounts

```bash
vercel deploy
```

Verify the preview against its own database. Then, when ready to publish production:

```bash
vercel deploy --prod
```

With production signup disabled, provision intended users through an administrator. Create your private administrator once:

```bash
vercel env run -e production -- python manage.py createsuperuser
```

Use `/admin/` to create normal users without staff/superuser permissions. Give each user a unique strong password through an appropriate private onboarding process. Do not reuse the local demo account or publish a shared administrator login.

Provision a token only for a client that needs it:

```bash
vercel env run -e production -- python manage.py drf_create_token intended_username
```

The output is a secret. Deliver it privately and rotate/revoke when no longer needed. The user must log in with a production account, because SQLite users and tokens do not transfer automatically.

## 7. Production smoke check

Use fictional disposable records and two ordinary accounts:

- `/healthz/` responds with the liveness result. It intentionally does not test the database.
- Login displays CSS correctly and accepts the intended account.
- An anonymous visit to `/tasks/` redirects to login.
- Create, edit, complete, search, and delete a task.
- Create `course_link`, then fetch it through the token-authenticated by-key endpoint.
- Invalid form/API data produces errors without writing a row.
- The second user cannot list, read, edit, or delete the first user's records.
- Logout uses POST and ends the browser session.
- Refresh and revisit after a new deployment to confirm PostgreSQL persistence.
- HTTP redirects to HTTPS, cookies use Secure/HttpOnly as appropriate, and debug pages are absent.

If you cannot confirm these on the hosted URL, do not describe the deployment as verified.

## Troubleshooting

| Symptom | Check |
|---|---|
| Startup configuration error | Exact environment names, secret length, hosts, origins and PostgreSQL URL |
| HTTP 400 / DisallowedHost | Exact hostname in `DJANGO_ALLOWED_HOSTS`, not a full URL |
| CSRF 403 after login | Exact HTTPS origin, proxy scheme and cookies; never disable middleware |
| Missing database table | Correct environment's migration status, not the local SQLite database |
| Missing CSS | Framework detection, `STATIC_ROOT`, collectstatic build output and `static/` files |
| API 401 | Correct `Token` scheme, active user and a token from this environment |
| Browser works without API token | SessionAuthentication is authenticating the logged-in browser |
| 429 after failed logins | Wait 15 minutes; investigate rather than weakening production protection |
| Data disappears | Confirm PostgreSQL target; do not use SQLite or runtime local files |
| Redirect loop | Vercel proxy trust, HTTPS forwarding and the actual deployment platform |

Request logs provide a generated `X-Request-ID`, method, status and duration. They intentionally omit URLs, queries, body content, usernames and credentials. Vercel/provider-level logs have separate retention and access controls that you must review.

## Security and operational limitations

- This is a small educational application with explicit production safeguards, not a complete enterprise identity platform.
- Registration defaults to closed in production. Before opening it, add email verification, abuse controls, recovery, and an appropriate user policy.
- Login lockouts use shared database state. Configure edge rate limits for login, signup, token clients and excessive API traffic as appropriate. Lockout alone does not prevent distributed abuse, credential stuffing, or denial of service.
- Simple DRF tokens are long-lived. Consider expiring/OAuth-based credentials for a broader rollout. Password changes do not automatically invalidate these tokens.
- Note values are readable by administrators/database operators. Database/provider encryption at rest is not end-to-end encryption of each note.
- Backups, restoration drills, spending limits, monitoring, incident response, and dependency patching remain operational responsibilities.
- No email/password-reset workflow, file uploads, background workers, or end-to-end note encryption is included.
- Clean up expired sessions and aged login-attempt rows through reviewed periodic management commands. Do not expose maintenance URLs publicly.
- Review HTTPS, host policy and domain-specific HSTS settings against the [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

Documentation checked: 30 September 2026. Provider dashboards and capabilities can change; use the linked official pages when deploying.
