# REST API guide

Base URL: `http://127.0.0.1:8000` locally, or your own HTTPS Vercel origin after deployment. All resource paths use a trailing slash.

## Authentication

The configured order is **TokenAuthentication, then SessionAuthentication**, matching the workshop. Without a usable token or session, protected endpoints return **401**. A malformed supplied token fails authentication even if a browser also has a session.

### Browser

Sign in at `/accounts/login/`, then open `/api/`. The browsable API uses the session cookie. Forms and unsafe requests made with that session need a CSRF token. Never disable CSRF to make a request pass.

### Postman, curl, or another application

An administrator provisions a token for an existing account using Django's management command:

```bash
python manage.py drf_create_token asha
```

Send the resulting private token in this header:

```http
Authorization: Token <your-private-token>
```

`Token` is the literal scheme, not `Bearer`. The app intentionally does not expose a password-to-token endpoint. This limits the starter's public authentication surface. The simple DRF token is a long-lived secret with no automatic expiry or per-device separation.

To rotate it, run `python manage.py drf_create_token --reset asha`, then update the intended client securely. To revoke without replacement, remove the user's token through Django admin. A lost password change alone does not revoke this separate token. Production token management must target the production database and an intended production user.

Only localhost may use HTTP for learning. Use HTTPS everywhere else. Never include a real token in shared command history, screenshots, logs, exported collections, or source code.

## Routes and responses

| Method | Route | Meaning | Success |
|---|---|---|---|
| GET | `/api/tasks/` | List your tasks | 200, paginated JSON |
| POST | `/api/tasks/` | Create your task | 201 |
| GET | `/api/tasks/{id}/` | Read your task | 200 |
| PUT | `/api/tasks/{id}/` | Replace supported task data | 200 |
| PATCH | `/api/tasks/{id}/` | Update selected task fields | 200 |
| DELETE | `/api/tasks/{id}/` | Delete your task | 204, empty body |
| GET / POST | `/api/entries/` | List / create your notes | 200 / 201 |
| GET / PUT / PATCH / DELETE | `/api/entries/{id}/` | Read / update / delete your note | 200 / 204 |
| GET | `/api/entries/by-key/?key=course_link` | Read one of your notes by key | 200 |

An unknown ID and someone else's ID both return 404. An invalid title, key, value, or duplicate personal key returns 400. An authenticated browser session making an unsafe request without valid CSRF returns 403. Unsupported methods return 405.

## Task example

Create with `POST /api/tasks/` and `Content-Type: application/json`:

```json
{"title": "Prepare Django demo", "completed": false}
```

The server response includes `id`, `title`, `completed`, `created_at`, and `updated_at`. For example:

```json
{
  "id": 1,
  "title": "Prepare Django demo",
  "completed": false,
  "created_at": "2026-09-30T10:00:00Z",
  "updated_at": "2026-09-30T10:00:00Z"
}
```

The ID and timestamps above are illustrative; use the actual response values. Owner is assigned from the authenticated user and is not included in the public JSON.

Complete that task with `PATCH /api/tasks/{actual-id}/`:

```json
{"completed": true}
```

The title is trimmed and must contain 3–200 characters. `{"title":"Go"}` returns 400 with a title error and does not create or modify a task.

## Key-value example

Create with `POST /api/entries/`:

```json
{"key":"course_link","value":"https://docs.djangoproject.com/en/5.2/"}
```

Read the same record by its key:

```http
GET /api/entries/by-key/?key=course_link
```

Update its text with `PATCH /api/entries/{actual-id}/`:

```json
{"value":"https://www.django-rest-framework.org/"}
```

Keys are trimmed and lowercased. They allow 1–80 ASCII letters, digits, underscores, or hyphens. `Course_Link` becomes `course_link`. Values are trimmed and must contain 1–5,000 characters. A duplicate key for the same owner returns 400, while another owner can use that key independently. A missing or malformed by-key query returns 400; a valid key without an owned record returns 404.

The value is stored as text. A JSON string placed inside a value remains text rather than becoming a separately queryable JSON document. This feature is for ordinary notes, not credentials or encrypted secrets.

## Search, ordering, and pagination

- `/api/tasks/?search=django` searches titles in your records.
- `/api/entries/?search=course` searches your keys and values.
- `/api/tasks/?ordering=-created_at` puts recent records first.
- `/api/entries/?ordering=key&page=2` requests the second page in key order.
- Lists contain at most 10 records per page. Follow the returned `next` URL.

```json
{
  "count": 0,
  "next": null,
  "previous": null,
  "results": []
}
```

The HTML search parameter is `q`; the REST search parameter is `search`. GET queries never change stored records.

## Postman walkthrough

1. Set `base_url` to localhost or your HTTPS deployment.
2. Keep the token in a private secret/environment value, not a shared collection.
3. Add header `Authorization: Token {{token}}`.
4. For POST/PATCH, choose **Body → raw → JSON**, and paste only the JSON object.
5. Send a valid task create request and save its response ID.
6. GET it, PATCH completion, then refresh the browser to see the same record change.
7. Test `Go`, a missing token, another owner's ID, and a duplicate note key.
8. Delete only disposable demo records. A 204 response has no JSON body.

Use a clean cookie jar when testing missing-token behavior. A valid browser session can otherwise authenticate a request through the fallback session method.

Example post-response test for task creation:

```javascript
pm.test("Task created", () => {
  pm.response.to.have.status(201);
  const task = pm.response.json();
  pm.expect(task.completed).to.eql(false);
  pm.collectionVariables.set("task_id", task.id);
});
```

## References

- [DRF authentication](https://www.django-rest-framework.org/api-guide/authentication/)
- [DRF pagination](https://www.django-rest-framework.org/api-guide/pagination/)
- [Django CSRF protection](https://docs.djangoproject.com/en/5.2/ref/csrf/)
