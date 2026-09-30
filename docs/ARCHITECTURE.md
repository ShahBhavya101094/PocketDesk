# Architecture and request lifecycle

## One database, two interfaces

PocketDesk serves HTML pages and JSON from the same Django project. The `Task` and `Entry` models own the data definitions. Browser forms and API serializers validate their respective inputs. Views and ViewSets decide which records the current user may access.

```text
Browser form                         External API client
    |                                      |
Django URLconf                       DRF router
    |                                      |
Session + CSRF checks                Token or session authentication
    |                                      |
HTML view + ModelForm                ViewSet + Serializer
    |                                      |
    +------ owner-scoped ORM queries -------+
                         |
                SQLite locally
              PostgreSQL on Vercel
```

Authentication answers “who is making the request?” Ownership filtering answers “which records may this user access?” A valid login does not grant access to another user's task ID.

## HTML task creation

1. `GET /tasks/new/` redirects anonymous visitors to login.
2. The view renders `tasks/form.html`, including a hidden CSRF token.
3. The browser sends a POST with the title and completion state.
4. CSRF middleware validates the unsafe request before the view can write data.
5. `TaskForm.is_valid()` checks the data. A short title returns the form with errors and does not create a task.
6. The view assigns `request.user` as owner, saves the row, adds a message, and redirects to the list.
7. The list queries only that user's rows. The template escapes displayed titles.

The redirect after a successful POST avoids accidental resubmission on a normal refresh.

## REST task creation

1. `POST /api/tasks/` carries JSON and a private `Authorization: Token …` header.
2. DRF authenticates the token and checks `IsAuthenticated`.
3. `TaskSerializer` validates the supported fields.
4. `perform_create()` sets the owner on the server.
5. Django inserts the row and DRF returns `201 Created` with its generated ID.

Session-authenticated API writes require CSRF. Header-token requests do not rely on browser cookies and use the token authentication path. Always use HTTPS outside localhost.

## Update, deletion, and isolation

Detail views and ViewSets retrieve from an owner-filtered queryset. A request for another person's ID returns 404 without revealing whether the record exists. The HTML delete URL displays a confirmation on GET and deletes only on POST. The REST DELETE returns 204 with no JSON body.

## Key-value entries

`Entry` contains owner, key, value, and timestamps. Keys are lowercase identifiers using letters, numbers, underscores, or hyphens, up to 80 characters. Values are ordinary text up to 5,000 characters. A database uniqueness constraint covers `(owner, key)`. Two people may each have `course_link`, but one person cannot create it twice.

Form/serializer checks give readable errors. The database constraint also handles simultaneous requests, and the API translates a duplicate conflict into a validation response. The by-key endpoint applies the same owner filter as lookup by numeric ID.

Django does **not** automatically call `full_clean()` when you call `model.save()`. Browser forms and serializers explicitly validate their inputs. If you create records from a new shell command or service, call `full_clean()` before `save()` (or implement equivalent explicit validation). Database uniqueness constraints still apply to every write path. Bulk updates bypass model validation as well.

## Model, template, view: the MTV memory aid

| Component | Real files | Responsibility |
|---|---|---|
| Model | `tasks/models.py`, `entries/models.py` | Data fields, validation, database constraints |
| Template | `templates/tasks/`, `templates/entries/` | Accessible HTML presentation |
| View | `tasks/views.py`, `entries/views.py` | Handle requests, choose rows, validate forms, return responses |
| URLconf | `config/urls.py`, app `urls.py` | Map incoming paths to handlers |
| Serializer | app `serializers.py` | Validate and represent JSON |
| ViewSet | app `api.py` | Standard REST actions using an authorized queryset |

MTV names responsibilities, not the order in which every request executes. An API response can return JSON without a template.

## Production process

Vercel runs the WSGI application. A persistent PostgreSQL service stores records, users, sessions, tokens, and login protection state. The CDN serves collected CSS/JavaScript. No request starts a development server, runs migrations, or seeds demo data.

Use database connection settings appropriate for serverless execution and a provider connection pool. Background jobs, email delivery, file uploads, password recovery, and secret encryption are outside this starter's scope.
