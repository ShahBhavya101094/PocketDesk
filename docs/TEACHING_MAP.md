# Presentation-to-code map

Slide references below use the **70-slide revised workshop deck**. The live-project appendix follows it in the new presentation. Earlier workshop snippets intentionally omit surrounding code to focus on individual concepts.

| Workshop slides | Topic | Runnable implementation |
|---|---|---|
| 4–5, 34–36 | Login and account flow | `config/urls.py`, `accounts/`, `templates/registration/login.html` |
| 10–13 | Setup and project structure | `manage.py`, `config/`, `.env.example`, `requirements.txt` |
| 14–15 | MVT/MTV and request lifecycle | App models, views, templates; `docs/ARCHITECTURE.md` |
| 16–19 | Task model, migration, ORM and SQL | `tasks/models.py`, `tasks/migrations/` |
| 20 | Django admin | `tasks/admin.py`, `entries/admin.py`, `/admin/` |
| 21–24 | List view, template and inheritance | `tasks/views.py`, `templates/tasks/list.html`, `templates/base.html` |
| 25 | Key-value data | `entries/models.py`, `entries/migrations/` |
| 26–33 | Forms and CRUD | App `forms.py`, `views.py`, `urls.py`, form/delete templates |
| 37–41 | Ownership, CSRF, sessions and middleware | Owner-scoped queries, config middleware, app security tests |
| 43–48 | REST methods, serializers and ViewSets | `tasks/api.py`, `tasks/serializers.py`, `config/urls.py` |
| 49–52 | Token client and API tests | `drf_create_token`, `docs/API.md`, app API tests |
| 53–54 | Entry API | `entries/api.py`, `entries/serializers.py` |
| 55–57 | Git and repository hygiene | `.gitignore`, `.env.example`, `.vercelignore` |
| 58–63 | Production configuration and Vercel | `config/settings.py`, `vercel.json`, `docs/VERCEL.md` |
| 64 | Troubleshooting | `docs/VERCEL.md`, `docs/VERIFICATION.md` |
| 65–67 | Practical review and final lab | Entire project and tests |

## Deliberate extensions beyond the teaching excerpts

- `entries` is a separate app instead of another class in `tasks`. The separation makes ownership of each feature clear.
- The notes browser screens are implemented, not just illustrated.
- Both resources include creation/update timestamps and paginated API output.
- Entry keys use an explicit lowercase identifier policy, independent of database collation.
- Shared validation and database constraints protect both browser and REST paths.
- Production uses strict environment configuration and database-backed login protection.
- Production signup defaults to disabled. Provision real users deliberately.
- The JSON list response is a pagination object containing `results`, not a bare array.
- The first introductory “PocketDesk is running” route becomes a redirect to the real task list in the integrated application.

The earlier slides remain a teaching progression. Use the repository and implementation appendix as the source of truth when running or deploying the finished app.

## Suggested live demonstration

1. Create two fictional local accounts, Asha and Bob, using different passwords.
2. As Asha, create a task and a `course_link` note.
3. Submit the title `Go` to show the form validation error.
4. Use Asha's API token to list the same task, then PATCH its completion state.
5. Refresh the browser and observe the shared database change.
6. As Bob, request Asha's record ID and observe 404.
7. Create `course_link` for Bob and show that the two accounts have independent values.
8. Show the migration, an ORM query, and the corresponding SQL explanation.
9. Explain the Vercel configuration and PostgreSQL migration step without exposing real credentials.

Never project real passwords, token values, database URLs, or provider account screens containing secrets.
