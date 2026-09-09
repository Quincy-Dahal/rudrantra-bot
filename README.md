# Rudrantra Chatbot Backend — "Gyaan"

Django REST API backend for **Gyaan**, the AI customer support chatbot for [Rudrantra](https://rudranntra.com), an online store selling Rudraksha beads. Gyaan answers customer questions about products, prices, meanings, and store policies using **Qwen3**, an open-source AI model running locally via **Ollama** — no per-message API costs.

The frontend chat widget lives in a separate repo: `rudrantra-chat`.

---

## Requirements

- Python 3.13+
- PostgreSQL
- [Ollama](https://ollama.com/download) (runs the AI model locally)

---

## Setup

1. **Clone the repo and set up a virtual environment**
   ```
   git clone https://github.com/Quincy-Dahal/rudrantra-bot.git
   cd rudrantra-bot
   python -m venv venv
   venv\Scripts\activate        # Windows
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Install Ollama and pull the model**
   ```
   ollama pull # Rudrantra Chatbot Backend — "Gyaan"

Django REST API backend for **Gyaan**, the AI customer support chatbot for [Rudrantra](https://rudranntra.com), an online store selling Rudraksha beads. Gyaan answers customer questions about products, prices, meanings, and store policies using **Qwen3**, an open-source AI model running locally via **Ollama** — no per-message API costs.

The frontend chat widget lives in a separate repo: `rudrantra-chat`.

---

## Requirements

- Python 3.13+
- PostgreSQL
- [Ollama](https://ollama.com/download) (runs the AI model locally)

---

## Setup

1. **Clone the repo and set up a virtual environment**
   ```
   git clone https://github.com/Quincy-Dahal/rudrantra-bot.git
   cd rudrantra-bot
   python -m venv venv
   venv\Scripts\activate        # Windows
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Install Ollama and pull the model**
   ```
   ollama pull qwen3:1.7b
   ```
   Confirm it landed: `ollama list`

4. **Set up PostgreSQL** — create a database for this project (matches whatever you put in `DATABASE_URL` below).

5. **Create your `.env` file** — copy `.env example` to `.env` and fill in real values (see [Environment Variables](#environment-variables) below). **Never commit `.env`** — it's already in `.gitignore`.

6. **Run migrations**
   ```
   python manage.py migrate
   ```

7. **Load the initial product catalog**
   ```
   python manage.py load_initial_products
   ```
   Should report: `Loaded 22 products with 79 variants across 3 categories.`

8. **Create an admin account**
   ```
   python manage.py createsuperuser
   ```

9. **Run the server**
   ```
   python manage.py runserver
   ```
   Visit `http://127.0.0.1:8000/api/docs/` for interactive API documentation (Swagger).

---

## Environment Variables

All read from `.env` via `django-environ`. See `.env example` for a template with safe placeholder values.

| Variable | Purpose | Example |
|---|---|---|
| `SECRET_KEY` | Django's cryptographic secret key | `django-insecure-...` |
| `DEBUG` | Debug mode toggle | `True` (dev), `False` (production) |
| `ALLOWED_HOSTS` | Comma-separated hosts Django will serve | `127.0.0.1,localhost` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@localhost:5432/dbname` |
| `OLLAMA_BASE_URL` | Where Ollama is running | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Which model to use | `qwen3:4b` |
| `OLLAMA_TIMEOUT` | Max seconds to wait for a reply | `300` |
| `OLLAMA_KEEP_ALIVE` | How long Ollama keeps the model loaded in RAM | `10m` |
| `OLLAMA_NUM_THREAD` | CPU threads for Ollama to use (match physical cores, not logical) | `4` |
| `OLLAMA_TEMPERATURE` | Response randomness (lower = more consistent) | `0.3` |
| `CORS_ALLOWED_ORIGINS` | Frontend origin(s) allowed to call this API | `http://localhost:3000` |

---

## Project Structure

```
core/       - Talks to Ollama; holds the system prompt and static brand/FAQ/contact info
chat/       - Conversation & Message models, the send-message endpoint, feedback endpoint
products/   - The product catalog (database-backed, editable via Django admin)
myproject/  - Django settings, root URL config
```

**Why products are in the database, not hardcoded:** adding, editing, or hiding a product happens through `/admin/` and takes effect on the very next chat message — no code change or redeploy needed.

---

## API Endpoints

Full interactive docs at `/api/docs/`. Key endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/conversations/send-message/` | Send a message, get a reply. Include `conversation_id` from a prior response to continue that conversation. |
| `GET` | `/api/conversations/` | List all conversations |
| `GET` | `/api/conversations/<id>/` | Get one conversation with its full message history |
| `PATCH` | `/api/messages/<id>/feedback/` | Rate a specific bot reply: `{"feedback": "up"}`, `{"feedback": "down"}`, or `{"feedback": null}` to clear |

---

## Managing the Product Catalog

Go to `/admin/`, log in, and open **Products**. Add, edit, or uncheck "Is active" to hide a product — changes are live immediately, no restart needed. Each product can have multiple **Variants** (different sizes/prices).

---

## Known Limitations

- **Response time:** 2-5 minutes on CPU-only hardware with no dedicated GPU. This is a hardware constraint, not a bug — moving to real server hosting (with more CPU headroom, or a GPU) is the actual fix.
- **Occasional "thinking" leakage:** `qwen3:4b` has a known Ollama bug where its internal reasoning can leak into visible replies instead of staying hidden. Mitigated via `core/llm.py`'s `_strip_thinking()` and a generous token cap, but not fully eliminated for every possible question.
- **Shipping and return policy content** isn't available yet (doesn't exist on the live site either). The bot is instructed to redirect these questions to the team rather than guess.

---

## Git Workflow

All work happens on a feature branch, then goes through a Pull Request for review. Nothing is pushed directly to `main`.
   ```
   Confirm it landed: `ollama list`

4. **Set up PostgreSQL** — create a database for this project (matches whatever you put in `DATABASE_URL` below).

5. **Create your `.env` file** — copy `.env example` to `.env` and fill in real values (see [Environment Variables](#environment-variables) below). **Never commit `.env`** — it's already in `.gitignore`.

6. **Run migrations**
   ```
   python manage.py migrate
   ```

7. **Load the initial product catalog**
   ```
   python manage.py load_initial_products
   ```
   Should report: `Loaded 22 products with 79 variants across 3 categories.`

8. **Create an admin account**
   ```
   python manage.py createsuperuser
   ```

9. **Run the server**
   ```
   python manage.py runserver
   ```
   Visit `http://127.0.0.1:8000/api/docs/` for interactive API documentation (Swagger).

---

## Environment Variables

All read from `.env` via `django-environ`. See `.env example` for a template with safe placeholder values.

| Variable | Purpose | Example |
|---|---|---|
| `SECRET_KEY` | Django's cryptographic secret key | `django-insecure-...` |
| `DEBUG` | Debug mode toggle | `True` (dev), `False` (production) |
| `ALLOWED_HOSTS` | Comma-separated hosts Django will serve | `127.0.0.1,localhost` |
| `DATABASE_URL` | PostgreSQL connection string | `postgres://user:pass@localhost:5432/dbname` |
| `OLLAMA_BASE_URL` | Where Ollama is running | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | Which model to use | `qwen3:4b` |
| `OLLAMA_TIMEOUT` | Max seconds to wait for a reply | `300` |
| `OLLAMA_KEEP_ALIVE` | How long Ollama keeps the model loaded in RAM | `10m` |
| `OLLAMA_NUM_THREAD` | CPU threads for Ollama to use (match physical cores, not logical) | `4` |
| `OLLAMA_TEMPERATURE` | Response randomness (lower = more consistent) | `0.3` |
| `CORS_ALLOWED_ORIGINS` | Frontend origin(s) allowed to call this API | `http://localhost:3000` |

---

## Project Structure

```
core/       - Talks to Ollama; holds the system prompt and static brand/FAQ/contact info
chat/       - Conversation & Message models, the send-message endpoint, feedback endpoint
products/   - The product catalog (database-backed, editable via Django admin)
myproject/  - Django settings, root URL config
```

