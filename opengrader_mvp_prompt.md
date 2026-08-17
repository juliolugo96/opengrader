# OpenGrader MVP Codex Prompt

## Overview
This document contains the full Codex prompt to scaffold the OpenGrader MVP, including architecture, requirements, and future roadmap prompts.

---

## Codex Prompt

(See below — copy everything from here into Codex)

---

# OpenGrader MVP Scaffold Prompt

You are scaffolding the first MVP for **OpenGrader**, an open-source, local-first alternative to Gradescope.

OpenGrader lets universities run automatic grading locally, with an eventual premium hosted/self-hosted version that funds infrastructure costs.

## MVP Goal

Build a working CLI-first autograding MVP.

Command:

```
opengrader run assignment.yaml submissions/
```

---

## Preferred Stack

- Python 3.12+
- Typer
- Pydantic
- PyYAML
- pytest
- Docker CLI
- Rich

---

## Repository Structure

```
opengrader/
  README.md
  docs/
  examples/
  src/
  tests/
```

---

## Core Features

### CLI
- Run grading command
- Optional flags

### Assignment Config
- YAML-based
- Validated with Pydantic

### Submission Discovery
- Folder-based detection

### Docker Sandbox
- Isolated execution
- Resource limits

### Grading Engine
- Pass/fail scoring

### Results
- JSON output
- Markdown summary

---

## Premium Strategy (Placeholder)

- Free: local grading
- Paid: hosted + scaling + integrations

---

## Documentation Requirements

- ARCHITECTURE.md
- ROADMAP.md
- MVP_CHECKLIST.md
- FUTURE_MVP_PROMPTS.md
- SECURITY.md
- PREMIUM_STRATEGY.md

---

## Testing

- Unit tests for config, submissions, results

---

## Commands

```
pytest
opengrader run examples/assignment.yaml examples/submissions --no-docker
```

---

## Acceptance Criteria

- CLI works
- Results generated
- Docs included

---

## Future MVP Prompts

### MVP 2: Batch Grading
- Add partial credit
- Improve scoring

### MVP 3: API
- FastAPI backend

### MVP 4: UI
- React dashboard

### MVP 5: PDF Grading
- Annotation system

### MVP 6: Billing
- Stripe integration

### MVP 7: LMS
- Canvas integration

---

## MVP Checklist

- CLI runs
- Config loads
- Submissions parsed
- Docker execution works
- Results generated
- Tests pass
- Docs complete
