# Assignment Gallery

These definitions demonstrate how one small YAML contract can grade different
languages and artifact types. They are schema-valid reference configurations;
the commands expect each submission folder to contain the files described in
the YAML comments.

| Example | Expected submission | Technique demonstrated |
| --- | --- | --- |
| `minimal-python.yaml` | `solution.py` | The smallest valid assignment and all defaults |
| `python-library.yaml` | `solution.py` exports | Import checks, edge cases, setup, per-test timeout |
| `python-cli.yaml` | `cli.py` | CLI output, stderr, and exit-code behavior |
| `javascript-module.yaml` | `solution.js` | Alternate runtime and inline assertions |
| `c-program.yaml` | `main.c` | Compilation, warnings-as-errors, stdin/stdout |
| `java-program.yaml` | `Main.java` | Compiled JVM submission and argument handling |
| `shell-script.yaml` | `solution.sh` | POSIX syntax and streamed input |
| `sql-query.yaml` | `query.sql` | Ephemeral database fixtures and result assertions |
| `static-web-page.yaml` | `index.html`, `styles.css` | Structural and accessibility checks |
| `custom-rubric-image.yaml` | Course-defined | Private hidden tests and exit-code partial credit |

Validate a definition without executing it:

```sh
python -c "from pathlib import Path; from opengrader.config import load_assignment; print(load_assignment(Path('examples/assignments/c-program.yaml')))"
```

To execute one, arrange visible direct child folders under a submissions root:

```text
submissions/
├── alice/
│   └── main.c
└── bob/
    └── main.c
```

Then run:

```sh
opengrader run examples/assignments/c-program.yaml submissions/
```

Docker must be able to obtain the configured image. Container networking is
disabled during grading, so dependencies and hidden tests must already be in
the image or submission. See the complete [assignment YAML reference](../../docs/ASSIGNMENT_FORMAT.md).
