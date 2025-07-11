# General Engineering Rules — Personal Hobby Projects

## 1 · Language & Interpreter Versions
- Pin one exact interpreter version (e.g. `Python 3.13.0`, `Node 20.10.0`) and use it in **development, CI, staging, and production**.
- Never mix interpreter versions across environments.

---

## 2 · Dependencies

### 2.1 Current-Date Awareness
The assistant always knows "today" in ISO format (`YYYY-MM-DD`) and may record it in commit messages or documentation when adding new packages.

### 2.2 Adding a New Dependency
1. Run the package-manager add command (resolves the latest compatible version as of today).
   - Python → `uv add <package>`
   - Node  → `npm install <package>` / `pnpm add <package>` (select one manager per project)
2. Commit **both** the updated manifest and the generated lockfile (`uv.lock`, `package-lock.json`, `pnpm-lock.yaml`, …).

### 2.3 Installing / CI / Production
- Always install **from the lockfile only**.
  - Python → `uv sync --strict`
  - Node  → `npm ci` / `pnpm install --frozen-lockfile`

---

## 3 · Async, Concurrency & Event-Driven Design
- Prefer event-driven patterns (async tasks, callbacks, pub/sub) over polling.
- Use async I/O for external operations expected to exceed 10 ms; never block the main thread or event loop.
- Guard long-running tasks with explicit time-outs and raise appropriate timeout errors.
- Shield critical sections and never swallow cancellation errors.

---

## 4 · Code Organisation & Style
- **Single responsibility** per file; group closely related classes/functions together.
- **Size guardrails**
  - Soft warning at 150 LOC if the file contains ≥ 2 public symbols.
  - Hard review trigger at 300 LOC (override only with justification).
- **Complexity limits**
  - Cyclomatic complexity per file < 15.
  - ≤ 3 public symbols per file, except in designated *domain modules* (≤ 400 LOC and ≤ 5 publics).
- Reuse existing abstractions; eliminate duplication.
- Avoid "god" classes (`manager`, `utils`, `misc`). Focused classes such as `ConnectionManager`, `AudioController` are acceptable.
- Keep the repository tidy—no throw-away scripts.
- Import order: **stdlib → third-party → internal**.

---

## 5 · Security
- Never commit or overwrite `.env`; read secrets via environment variables.
- Never log tokens, secrets, or PII.

---

## 6 · Testing
- Use the language's standard testing framework.
- Maintain ≥ 40 % line coverage on critical logic.
- Linting and type checking must pass in CI.
- Enforce typing gradually; missing stubs are acceptable during early development.

### 6.1 Automatic Hook Installation

**Python (uv)**
```bash
uv add --dev pre-commit
uv run pre-commit install
uv run pre-commit init-templatedir ~/.git-template
git config --global init.templateDir ~/.git-template
```

**Other Languages**
Install pre-commit with the language's package manager and initialise the hooks similarly.

---

## 7 · Logging & Observability
- Emit structured JSON logs containing `event`, `module`, and `elapsed_ms`.
- No metrics endpoints for hobby projects—keep it simple.

---

## 8 · Performance
- Optimise only after profiling shows a pure function consumes > 2 % of total CPU/time.
- Set realistic SLOs; avoid premature optimisation.

---

## 9 · Error Handling
1. Identify potential failure points.
2. Instrument logging at those points.
3. Analyse logs to determine root causes.
4. Address those specific causes.
- Fail fast on invalid input using language-appropriate error types.
- Catch broad exceptions only at process boundaries.
- Fix root causes rather than layering fallbacks.

---

## 10 · General Engineering Principles
- Prefer simple solutions; delete fallback configurations and obsolete paths.
- Adopt new technology only when it fully replaces the old—then remove the old implementation.
- Avoid stubbing or fake data outside tests; never mock production or development data.
- Deliver exactly what is requested; propose enhancements separately.
- Focus on functionality over enterprise-grade features for hobby projects.
- Keep personal project scope manageable.
