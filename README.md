# 📋 KanMind — Boards & Tasks API (Django + DRF)

> A clean, token-authenticated backend for **boards**, **tasks**, and **comments**. Built with 🐍 **Django** & ⚙️ **Django REST Framework**.

<p align="left">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.13+-3776AB" />
  <img alt="Django" src="https://img.shields.io/badge/Django-5.2+-092E20" />
  <img alt="DRF" src="https://img.shields.io/badge/DRF-3.15+-e23e57" />
  <img alt="License" src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

---

## 🧭 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Quickstart](#-quickstart)
- [Authentication](#-authentication)
- [API at a Glance](#-api-at-a-glance)
- [Permissions & Rules](#-permissions--rules)
- [Data Model](#-data-model-simplified)
- [Project Structure](#-project-structure-excerpt)
- [Environment & Settings](#-environment--settings)
- [Development Tips](#-development-tips)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

- 🔐 **Auth**
  - `POST /api/registration/` – create user, returns **Token**
  - `POST /api/login/` – login via email + password, returns **Token**
  - Token **or** session auth supported
- 🗂️ **Boards**
  - List, create, detail, update (title/members), delete (owner-only)
- ✅ **Tasks**
  - Create with status/priority, assign & review (must be board members)
  - “Assigned to me” and “Reviewing” listings
  - Detail, update, delete (creator or board owner)
- 💬 **Comments**
  - List & create under a task; delete by author
- 👤 **Users**
  - `GET /api/email-check/?email=...` – returns minimal user info if found

---

## 🛠 Tech Stack

- **Python** 3.13+
- **Django** 5.2+
- **Django REST Framework** 3.15+
- **DRF Token Auth** (`rest_framework.authtoken`)
- **SQLite** for dev (PostgreSQL ready)

---

## ⚡ Quickstart

```bash
# 1) Clone & enter
git clone <https://github.com/JoCro/KanMindBackend.git>
cd KanMind

# 2) Create & activate venv
python3 -m venv env
source env/bin/activate   # Windows: env\Scripts\activate

# 3) Install deps
pip install -r requirements.txt

# 4) Migrate DB
python manage.py migrate

# 5) (Optional) Create superuser
python manage.py createsuperuser

# 6) Run server
python manage.py runserver
```

> Browsable API login at `/api-auth/login/` (if `rest_framework.urls` is included).

---

## 🔑 Authentication

We use **Token Authentication** (plus SessionAuth for the browsable API).

**Register**

```http
POST /api/registration/
{
  "fullname": "Example User",
  "email": "example@mail.de",
  "password": "StrongPassword!",
  "repeated_password": "StrongPassword!"
}
```

**Response 201**

```json
{
  "token": "<token>",
  "fullname": "Example User",
  "email": "example@mail.de",
  "user_id": 123
}
```

**Login**

```http
POST /api/login/
{
  "email": "example@mail.de",
  "password": "StrongPassword!"
}
```

Use the token on subsequent requests:

```
Authorization: Token <token>
```

---

## 🔎 API at a Glance

### 🗂️ Boards

- **List** – `GET /api/boards/`
  - Boards where you are **owner or member**
- **Create** – `POST /api/boards/`
  ```json
  { "title": "Project X", "members": [12, 5, 54] }
  ```
- **Detail** – `GET /api/boards/{id}/` (includes members + tasks)
- **Update** – `PATCH /api/boards/{id}/`
  ```json
  { "title": "Changed title", "members": [1, 54] }
  ```
- **Delete** – `DELETE /api/boards/{id}/` _(owner only; cascades tasks & comments)_

### ✅ Tasks

- **Create** – `POST /api/tasks/`
  ```json
  {
    "board": 12,
    "title": "Code review",
    "description": "Review PR",
    "status": "review", // to-do | in-progress | review | done
    "priority": "medium", // low | medium | high
    "assignee_id": 13,
    "reviewer_id": 1,
    "due_date": "2025-02-27"
  }
  ```
- **Assigned to me** – `GET /api/tasks/assigned-to-me/`
- **Reviewer (me)** – `GET /api/tasks/reviewing/`
- **Detail/Update/Delete** – `GET|PATCH|PUT|DELETE /api/tasks/{id}/`
  - Read & update by board **members/owner**; **delete** by **creator** or **board owner**

### 💬 Comments

- **List & Create** – `GET|POST /api/tasks/{task_id}/comments/`
  ```json
  { "content": "This needs a follow-up." }
  ```
- **Delete** – `DELETE /api/tasks/{task_id}/comments/{comment_id}/` _(author only)_

### 👤 Users

- **Email check** – `GET /api/email-check/?email=foo@bar.com` _(auth required)_

---

## 🛡 Permissions & Rules

- Public: `registration`, `login`
- Boards: owner/member can view; **owner only** can delete
- Tasks: create/update if **member/owner** of the board; delete by **creator** or **board owner**
- Assignee/Reviewer **must** be board members
- Comments: list/create by **board owner/members**; delete by **comment author**

---

## 🧱 Data Model (simplified)

- **User** – Django auth user
- **Board**: `id`, `title`, `owner(FK:User)`, `members(M2M:User)`, `created_at`
- **Task**: `id`, `board(FK)`, `title`, `description`, `status`, `priority`, `assignee(FK?)`, `reviewer(FK?)`, `due_date`, `created_by(FK)`, `created_at`
- **TaskComment**: `id`, `task(FK)`, `author(FK)`, `content`, `created_at`

---

## 🗂 Project Structure (excerpt)

```
KanMind/
├─ kanmind_hub/                  # project settings & urls
├─ kanmind_app/
│  ├─ models.py                  # Board, Task, TaskComment
│  ├─ api/
│  │  ├─ serializers.py          # board/task/comment serializers
│  │  ├─ views.py                # endpoints
│  │  └─ urls.py                 # /api/boards, /api/tasks, ...
├─ user_auth_app/
│  ├─ api/
│  │  ├─ serializers.py          # registration/login
│  │  ├─ views.py                # /api/registration, /api/login
│  │  └─ urls.py
├─ requirements.txt
├─ manage.py
└─ README.md
```

---

## ⚙️ Environment & Settings

- Add to `INSTALLED_APPS`: `rest_framework`, `rest_framework.authtoken`
- Recommended DRF settings:

```python
REST_FRAMEWORK = {
  "DEFAULT_AUTHENTICATION_CLASSES": [
    "rest_framework.authentication.TokenAuthentication",
    "rest_framework.authentication.SessionAuthentication",
  ],
}
```

- Browsable API login in project urls:

```python
path("/api-auth/", include("rest_framework.urls"))
```

---

## 🧪 Development Tips

- Lock deps: `pip freeze > requirements.txt`
- Run migrations early & often: `python manage.py migrate`
- Don’t commit secrets: use `.env`, ignore `db.sqlite3`
- Add tests when endpoints stabilize: `pytest` / `pytest-django`

---

## 🤝 Contributing

PRs and issues are welcome! Please describe your change and include minimal steps to reproduce.

---

## 📄 License

MIT (or your preferred license). Replace this section as needed.
