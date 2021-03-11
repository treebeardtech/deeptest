import json
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, List, cast

import click
from coverage import Coverage, CoverageData
from coverage.misc import NoSource
from junitparser import JUnitXml
from pydantic import BaseModel


class Line(BaseModel):
    passed: List[str]
    failed: List[str]


class File(BaseModel):
    lines: Dict[int, Line]


class Status(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class ContextStatus(BaseModel):
    ctx: str
    status: Status


def norm(context: str):
    return (
        context.split("|")[0].replace(".py::", ".").replace("/", ".").replace("::", ".")
    )


def _get_line(contexts: List[str], status: Dict[str, Status]):
    if contexts == [""]:
        return Line(passed=["ran on startup"], failed=[])

    context_statuses = list(
        map(lambda ctx: ContextStatus(ctx=ctx, status=status[ctx]), contexts)
    )

    return Line(
        passed=[ctxs.ctx for ctxs in context_statuses if ctxs.status == Status.SUCCESS],
        failed=[ctxs.ctx for ctxs in context_statuses if ctxs.status == Status.FAILURE],
    )


def get_file_cov(src: str, coverage: Coverage, coverage_data: CoverageData):
    try:
        missing_lines: Dict[int, Line] = {
            num: Line(passed=[], failed=[]) for num in coverage.analysis2(src)[3]
        }
        lines = cast(Dict[int, List[str]], coverage_data.contexts_by_lineno(src))
        if len(lines) == 0:
            raise NoSource()
        norm_lines = {ln: list(map(norm, lines[ln])) for ln in lines.keys()}
        return (norm_lines, missing_lines)
    except NoSource:
        click.echo(
            json.dumps({"error": f"No coverage data in .coverage for file {src}"})
        )
        sys.exit(2)


@click.command()
@click.argument("source")
def run(source: str):
    """"""
    src = Path(source).as_posix()
    test_results = Path("junit.xml")
    if not test_results.exists():
        click.echo(
            json.dumps(
                {"error": f"{test_results.as_posix()} not present in {os.getcwd()}"}
            )
        )
        sys.exit(1)

    if not Path(".coverage").exists():
        click.echo(json.dumps({"error": f".coverage not present in {os.getcwd()}"}))
        sys.exit(1)

    xml = JUnitXml.fromfile(test_results.as_posix())

    status: Dict[str, Status] = {"": Status.SUCCESS}
    for suite in xml:
        if suite is None:
            continue
        # handle suites
        for testcase in suite:
            key: str = f"{testcase.classname}.{testcase.name}"
            status[key] = (
                Status.SUCCESS if len(testcase.result) == 0 else Status.FAILURE
            )
    coverage = Coverage()
    coverage.load()
    coverage_data = coverage.get_data()
    assert coverage_data is not None
    lines, missing_lines = get_file_cov(src, coverage, coverage_data)

    norm_contexts = {norm(ctx) for ctx in coverage_data.measured_contexts()}
    assert norm_contexts.difference(status.keys()) == set()

    file = File(
        lines={
            **missing_lines,
            **{i: _get_line(lines[i], status) for i in lines.keys()},
        }
    )
    output = json.dumps(file.dict())
    click.echo(output)
