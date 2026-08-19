# Professor Workspaces

OpenGrader's dashboard is designed for professors and instructors across
disciplines. Creating an assignment in the dashboard does not require knowledge
of configuration files or command-line tools.

## Academic organization

Every saved assignment belongs to five professor-defined dimensions:

- **Institution** — a school, university, department, program, or training
  organization.
- **Course code** and **course name** — for example `HIST-204` and `Modern
  History`.
- **Academic period** — any local convention, such as `Fall 2026`, `2026–2027`,
  `Trimester 2`, or `第一学期`.
- **Section** — a class, cohort, campus, or meeting group.

These values are deliberately flexible text rather than a fixed North American
semester model. The Assignments workspace groups work by the full academic
context and can filter across institution, period, section, course, and
assignment name.

## Two assignment workflows

### Automated checks

Choose a friendly starting point for Python, JavaScript, C, or a custom
environment. Add one or more evaluation checks with a name, instruction, and
point value. Advanced execution controls—environment image, preparation step,
time, memory, CPU, and process limits—are available but collapsed by default.

When grading starts, OpenGrader generates a validated internal definition on
the API host and creates a normal durable grading job. Professors never need to
author or locate that generated file.

### Written or PDF work

Save the same academic context without execution settings. The PDF grading
workspace can then associate each uploaded student document with the saved
assignment, apply a rubric, add page annotations, finalize the grade, and export
feedback.

## Language support

The dashboard stores a browser-local language preference and supports:

- English (`en`)
- Spanish (`es`)
- Simplified Chinese (`zh-CN`)

The professor workspace, global navigation, assignment builder, job catalog,
PDF intake, audit, billing, and connection settings use the selected language.
Academic values and assignment content remain exactly as the professor enters
them, so multilingual course names and periods are supported without
translation or normalization.

## API and persistence

Assignments are persisted in the same SQLite database as jobs and audit events.
Create, update, delete, and launch operations are authenticated and audited.
Deleting a catalog assignment does not remove historical grading jobs or PDF
submissions. Generated automated definitions are stored below
`OPENGRADER_ASSIGNMENT_STORAGE_ROOT` and are never accepted from a browser path.

See [API.md](API.md) for the HTTP contract and [ASSIGNMENT_FORMAT.md](ASSIGNMENT_FORMAT.md)
for the advanced CLI/server definition format.
