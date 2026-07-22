# Complete Beginner's Guide to This Project

This explains every concept used in the repo, from zero. Read it alongside
the actual code files — open each file mentioned as you read its section.

---

## 1. The big picture

You're building a small web service that:
1. Receives text (a "prompt")
2. Runs it through some checks (detectors)
3. Returns a JSON decision: allow it, block it, or clean it up (transform)

Three different "front doors" can trigger this: a web API call, a
command-line tool, and a web page (Streamlit UI). All three end up
calling the *same* underlying logic. That reuse is a core software
design idea: **write the logic once, expose it multiple ways.**

---

## 2. Python concepts used

### Functions and type hints
```python
def redact_pii(text: str) -> tuple[str, list[dict]]:
```
`text: str` says "this parameter should be a string" — it's a hint for
humans and tools, Python doesn't enforce it at runtime. `-> tuple[str, list[dict]]`
says "this function returns a tuple: a string, then a list of dicts."
Type hints make code self-documenting and let editors catch mistakes early.

### Regex (regular expressions)
A mini pattern-matching language for text, imported via `import re`.
- `[a-zA-Z0-9._%+-]+` = "one or more of these characters"
- `\d{3}` = "exactly 3 digits"
- `.sub(replacement_function, text)` = "find every match in `text` and
  replace it using `replacement_function`"

Regex is how the PII detector finds emails/phones without needing any
AI — it's pure pattern matching.

### Dicts, lists, tuples
- `{"tag": "pii", "evidence": "..."}` is a **dict** — key/value pairs,
  like a JSON object.
- `[reason1, reason2]` is a **list** — an ordered collection.
- `(sanitized_text, reasons)` is a **tuple** — a fixed-size group of
  values returned together, here used so one function can return two
  things at once.

### Sets
```python
tags = sorted(set(r["tag"] for r in reasons))
```
`set(...)` removes duplicates. If 3 reasons all have `tag: "pii"`, the
set collapses them to just one `"pii"`. `sorted()` then turns it back
into a predictable, ordered list (sets have no guaranteed order).

---

## 3. Pydantic (`app/schemas.py`)

Pydantic models are Python classes that describe **the shape of data**.
```python
class ContextDoc(BaseModel):
    id: str
    text: str
```
This says "a ContextDoc always has a string `id` and a string `text`."
When FastAPI receives JSON like `{"id": "doc-1", "text": "hello"}`, it
automatically converts it into a `ContextDoc` Python object — and if the
JSON is missing a field or has the wrong type, FastAPI rejects the
request automatically with a clear error, before your code even runs.
This is why you don't need to manually write `if "id" not in data: raise
error` checks everywhere — Pydantic does that validation for you.

---

## 4. FastAPI (`app/main.py`)

FastAPI is a Python web framework: it lets you turn Python functions
into HTTP endpoints with a decorator.
```python
@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(request: AnalyzeRequest) -> dict:
    ...
```
- `@app.post("/analyze", ...)` — this **decorator** registers the
  function below it to run whenever someone sends an HTTP POST request
  to `/analyze`.
- `request: AnalyzeRequest` — FastAPI parses the incoming JSON body
  into an `AnalyzeRequest` object automatically (using the Pydantic
  model from schemas.py) and hands it to you as `request`.
- `response_model=AnalyzeResponse` — FastAPI checks that whatever you
  `return` matches this shape, and converts it to JSON for the client.

Run it with:
```bash
uvicorn app.main:app --reload --port 8000
```
`uvicorn` is the actual web server program that runs your FastAPI app.
`app.main:app` means "look in `app/main.py` for a variable called `app`."
`--reload` restarts the server automatically when you edit code (great
for development, remove it for production).

Once running, visit **http://localhost:8000/docs** — FastAPI
auto-generates an interactive page where you can test your endpoints
in the browser without writing any code. Use this constantly while
developing.

---

## 5. pytest (`tests/`)

pytest is a testing framework. Any function starting with `test_` in a
file starting with `test_` gets automatically discovered and run.
```python
def test_pii_detector_finds_email():
    _, reasons = redact_pii("contact me at john@example.com")
    assert any(r["tag"] == "pii" for r in reasons)
```
`assert <condition>` — if the condition is `False`, the test fails and
pytest tells you exactly which line and why. Run all tests with:
```bash
pytest -q
```
Why test the detectors *and* the API separately? `tests/test_detectors.py`
tests the pure logic directly (fast, no server needed).
`tests/test_api.py` uses FastAPI's `TestClient` to test the actual HTTP
layer (does a bad request really return a 422? does a good one return
200?) — this catches bugs in how the pieces are wired together, not
just the logic itself.

---

## 6. argparse and the CLI (`cli.py`)

`argparse` is Python's standard library for building command-line tools.
```python
parser.add_argument("--input", required=True, help="Path to input JSON file")
```
This means your script accepts `--input somefile.json` on the command
line, and `args.input` gives you that value in code. `required=True`
means the script errors out immediately (with a helpful message) if you
forget to pass it — you get this for free, no manual checking needed.

The CLI uses the `requests` library to make an HTTP call — the exact
same kind of call your browser makes:
```python
response = requests.post(f"{args.api_url}/analyze", json=payload)
```
This is why **the API must already be running** before you use the CLI
— the CLI is a client, not a server.

---

## 7. Streamlit (`ui/streamlit_app.py`)

Streamlit turns a plain Python script into a web page — no HTML/CSS/JS
required. Key mental model: **Streamlit reruns your entire script from
top to bottom every time the user interacts with something** (types
text, clicks a button). There's no persistent "state" by default; each
rerun is fresh.
```python
prompt = st.text_area("Prompt", height=100)
if st.button("Analyze"):
    ...
```
`st.text_area(...)` draws a text box and returns whatever the user
typed. `st.button("Analyze")` draws a button and returns `True` only on
the run where it was just clicked. Inside that `if`, we call the API
with `requests.post`, exactly like the CLI does, and use `st.metric`,
`st.write`, `st.json` etc. to display the result.

Run it with:
```bash
streamlit run ui/streamlit_app.py
```

---

## 8. Docker (`Dockerfile.api`, `Dockerfile.ui`, `docker-compose.yml`)

**The problem Docker solves:** "it works on my machine" — different
Python versions, missing dependencies, OS differences. Docker packages
your app plus everything it needs (Python version, libraries, OS
layer) into an isolated, reproducible **image**, which runs the same
way anywhere.

**Dockerfile** = a recipe for building one image:
```dockerfile
FROM python:3.11-slim          # start from a base image with Python installed
WORKDIR /app                   # set the working directory inside the container
COPY requirements.api.txt ./   # copy this file in
RUN pip install -r requirements.api.txt   # run a command while building
COPY app ./app                 # copy your code in
CMD ["python", "-m", "uvicorn", ...]      # command to run when the container starts
```
Each line creates a new "layer" — Docker caches layers, so if you only
change your code (not requirements.txt), rebuilds are fast because it
reuses the cached dependency-install layer.

**docker-compose.yml** = a recipe for running *multiple* containers
together (here: the API container and the UI container) with one
command:
```bash
docker compose up --build
```
This builds both images and starts both containers. Notice in
`docker-compose.yml`, the UI container gets `API_BASE_URL=http://api:8000`
— inside Docker's internal network, containers reach each other by
**service name** (`api`), not `localhost`. `localhost` inside a
container refers to that container itself, not your machine or the
other container — this trips up almost everyone the first time.

---

## 9. How a single request flows through the whole system

1. You type a prompt in the Streamlit UI and click Analyze.
2. Streamlit sends an HTTP POST to `http://localhost:8000/analyze` (or
   `http://api:8000/analyze` inside Docker) with your prompt as JSON.
3. FastAPI receives it, Pydantic validates the JSON matches `AnalyzeRequest`.
4. `analyze_endpoint()` calls `analyze()` in `detectors.py`.
5. `analyze()` calls each detector function, collects `reasons`,
   computes a `risk_score`, and picks a `decision`.
6. FastAPI serializes the returned dict into JSON matching `AnalyzeResponse`.
7. Streamlit receives the JSON response and displays it with `st.metric`/`st.json`.

The CLI does steps 2, 3-6, and a simplified step 7 (writing to a file
instead of drawing a web page) — same underlying flow.

---

## 10. Suggested order to actually learn this hands-on

1. Run `pytest -q` and watch all tests pass — get comfortable that
   the logic works before touching the web layer.
2. Start the API (`uvicorn app.main:app --reload`) and play with
   `/docs` in your browser — send a few requests manually.
3. Run the CLI against it.
4. Run the Streamlit UI against it.
5. Try `docker compose up --build` and confirm the same behavior works
   in containers.
6. Break something on purpose (e.g. comment out a detector call) and
   watch a test fail — this builds real intuition for how the pieces
   depend on each other.
7. Read through `README.md`'s Design Notes and make sure you could
   explain each tradeoff out loud — that's exactly what interviewers
   will probe on.
