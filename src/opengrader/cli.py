"""OpenGrader command-line interface."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from opengrader import __version__
from opengrader.config import load_assignment
from opengrader.errors import OpenGraderError
from opengrader.grader import grade_assignment
from opengrader.results import GradingResult, write_results
from opengrader.runners import DockerRunner, LocalRunner
from opengrader.submissions import discover_submissions, select_submissions

app = typer.Typer(
    name="opengrader",
    help="Grade folder-based programming submissions locally.",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"OpenGrader {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True),
    ] = None,
) -> None:
    """OpenGrader: a local-first autograding CLI."""


@app.command("run")
def run_command(
    assignment_file: Annotated[
        Path,
        typer.Argument(help="Path to the assignment YAML file."),
    ],
    submissions_dir: Annotated[
        Path,
        typer.Argument(help="Directory containing one folder per submission."),
    ],
    no_docker: Annotated[
        bool,
        typer.Option(
            "--no-docker",
            help="Run on the host. Unsafe for untrusted submissions.",
        ),
    ] = False,
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory for result files."),
    ] = Path("opengrader-results"),
    workers: Annotated[
        int,
        typer.Option(
            "--workers",
            "-j",
            min=1,
            max=64,
            help="Number of submissions to grade concurrently.",
        ),
    ] = 1,
    retries: Annotated[
        int,
        typer.Option(
            "--retries",
            min=0,
            max=10,
            help="Extra attempts for tests that do not earn full credit.",
        ),
    ] = 0,
    submission_patterns: Annotated[
        list[str] | None,
        typer.Option(
            "--submission",
            "-s",
            help="Student ID pattern to include; repeat for multiple patterns.",
        ),
    ] = None,
) -> None:
    """Grade every submission folder using an assignment definition."""

    try:
        assignment = load_assignment(assignment_file)
        submissions = select_submissions(
            discover_submissions(submissions_dir), submission_patterns or []
        )
        if no_docker:
            console.print(
                "[yellow]Warning:[/] local execution is not sandboxed; "
                "only grade trusted code."
            )
            runner = LocalRunner()
            runner_name = "local"
        else:
            runner = DockerRunner()
            runner_name = "docker"

        console.print(
            f"Grading [bold]{len(submissions)}[/] submission(s) for "
            f"[bold]{assignment.name}[/] with {runner_name}..."
        )
        result = grade_assignment(
            assignment,
            submissions,
            runner,
            runner_name,
            workers=workers,
            retries=retries,
        )
        json_path, markdown_path, csv_path = write_results(result, output_dir)
    except OpenGraderError as exc:
        console.print(f"[red]Error:[/] {exc}", highlight=False)
        raise typer.Exit(code=2) from exc

    _print_summary(result)
    console.print(
        f"\nResults: [cyan]{json_path}[/], [cyan]{markdown_path}[/], "
        f"and [cyan]{csv_path}[/]"
    )


def _print_summary(result: GradingResult) -> None:
    table = Table(title="Grading results")
    table.add_column("Submission")
    table.add_column("Score", justify="right")
    table.add_column("Status", justify="center")
    for submission in result.submissions:
        status = {
            "pass": "[green]PASS[/]",
            "partial": "[yellow]PARTIAL[/]",
            "fail": "[red]FAIL[/]",
        }[submission.status]
        table.add_row(
            submission.student_id,
            f"{submission.score:g}/{submission.maximum_score:g}",
            status,
        )
    console.print(table)


if __name__ == "__main__":
    app()
