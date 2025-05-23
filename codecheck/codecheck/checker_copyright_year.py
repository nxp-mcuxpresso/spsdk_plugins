#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2021-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Script used during pre-commit to check if changed files have valid copyright year."""
import argparse
import datetime
import fnmatch
import logging
import os
import re
import sys
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Sequence, Type

import tomli
from jinja2 import Environment

logger = logging.getLogger(__name__)

THIS_YEAR = datetime.datetime.now().year
LAST_YEAR = THIS_YEAR - 1
DEFAULT_COPYRIGHT_TEMPLATE = (
    "Copyright {{ copyright_years }} {{ holder }}\n\nSPDX-License-Identifier: BSD-3-Clause"
)
DEFAULT_HOLDER = "NXP"


class CheckResult(str, Enum):
    """Copyright check result."""

    SUCCEEDED = "File has valid copyright header."
    NO_COPYRIGHT = "File does not contain copyright header."
    INVALID_YEAR = "File does not contain valid copyright year."
    FILE_NOT_FOUND = "File does not exist anymore."


@dataclass
class YearRange:
    """Dataclass holding information about single year range."""

    from_year: int
    to_year: Optional[int] = None

    def is_year_in_range(self, year: int) -> bool:
        """Check if given year is within the year range."""
        if self.to_year is None:
            return self.from_year == year
        return self.from_year <= year <= self.to_year

    def __str__(self) -> str:
        """Year range as a string, such as '2021-2024'."""
        result = str(self.from_year)
        if self.to_year is not None:
            result += f"-{self.to_year}"
        return result


class YearRanges(list[YearRange]):
    """List of year ranges."""

    def __str__(self) -> str:
        """Year ranges as a string, such as '2021-2024,2025' or '2012, 2014, 2016-2017', etc."""
        self.sort(key=lambda x: x.from_year, reverse=False)
        ranges = []
        for year_range in self:
            ranges.append(str(year_range))
        return ",".join(ranges)


class CopyrightChecker:
    """Copyright checker responsible for checking the valid copyright header.

    Multiple source file types are supported, such as py, xml, yaml, c, js etc.
    The default settings can be adjusted in pyproject.toml.
    Supported configuration parameters:
        excluded_files: List of files or patterns matching files in directories such as 'my_dir/*.py'
        template: Copyright template. Following template placeholders are supported :
            - {{ copyright_years }} Place in the copyright text where the copyright years text is entered
            - {{ holder }} Place in the copyright where the the copyright holder is entered
        holder: Copyright holder
        ignored_results: Override default behavior by ignoring specific type of result.
            The default value is SUCCEEDED and FILE_NOT_FOUND
        trailing_newline: Add trailing new line character
    """

    def __init__(self, working_dir: Optional[str] = None) -> None:
        """Copyright checker initialization."""
        self.excluded_files: list[str] = []
        self.template = DEFAULT_COPYRIGHT_TEMPLATE
        self.holder = DEFAULT_HOLDER
        self.ignored_results = [CheckResult.SUCCEEDED, CheckResult.FILE_NOT_FOUND]
        self.working_dir = working_dir or os.getcwd()
        self.trailing_newline = True
        self.load_configuration(self.working_dir)
        # Normalize excluded file paths
        for idx, excluded_file in enumerate(self.excluded_files):
            self.excluded_files[idx] = self._normalize_path(excluded_file)

    def load_configuration(self, project_dir: str) -> None:
        """Load pyproject configuration."""
        pyproject_toml_path = os.path.join(project_dir, "pyproject.toml")
        if not os.path.exists(pyproject_toml_path):
            return
        with open(pyproject_toml_path, "rb") as f_toml:
            toml = tomli.load(f_toml)
            copyright_cfg: Optional[Dict[str, Any]] = toml.get("tool", {}).get("copyright")
            if not copyright_cfg:
                return
            if copyright_cfg.get("excluded_files"):
                self.excluded_files = copyright_cfg["excluded_files"]
            if copyright_cfg.get("template"):
                self.template = copyright_cfg["template"]
            if copyright_cfg.get("holder"):
                self.holder = copyright_cfg["holder"]
            if copyright_cfg.get("ignored_results"):
                self.ignored_results = [
                    CheckResult[result.upper()] for result in copyright_cfg["ignored_results"]
                ]
            if copyright_cfg.get("trailing_newline") is not None:
                self.trailing_newline = bool(copyright_cfg["trailing_newline"])

    def _normalize_path(self, path: str) -> str:
        """Normalize path so it is an absolute path."""
        if not os.path.isabs(path):
            path = os.path.join(self.working_dir, path)
        return os.path.normcase(os.path.normpath(path))

    def check_files(self, file_paths: list[str], silent: bool = False) -> int:
        """Check copyright in list of files.

        :param file_paths: List of files/directories to be checked
        :param silent: If true no text is printed into console
        :return: Number of problems found
        """
        errors = 0
        files = self.collect_files(file_paths)
        for file_path in files:
            result = self.check_file(file_path, silent)
            if not result:
                errors += 1
        return errors

    def check_file(self, file_path: str, silent: bool = False) -> bool:
        """Check copyright in a single file.

        :param file_path: File to be checked
        :param silent: If true no text is printed into console
        :return: True if everything is OK, False otherwise
        """
        file_type = Path(file_path).suffix[1:]
        src_file_type = SourceFile.get_source_file_by_file_type(file_type)
        src_file = src_file_type(file_path, self.template, self.holder)
        result = src_file.check()
        if not silent:
            if result not in self.ignored_results:
                print(f"File: '{file_path}', Result: {result.value}")
        return result in self.ignored_results

    def fix_files(self, file_paths: list[str]) -> None:
        """Fix copyright header in list of files.

        :param file_paths: List of files/directories to be fixed
        """
        files = self.collect_files(file_paths)
        for file_path in files:
            self.fix_file(file_path)

    def fix_file(self, file_path: str) -> None:
        """Fix copyright in a single file.

        :param file_path: File to be fixed
        """
        file_type = Path(file_path).suffix[1:]
        src_file_type = SourceFile.get_source_file_by_file_type(file_type)
        src_file = src_file_type(file_path, self.template, self.holder, self.trailing_newline)
        src_file.fix()

    def collect_files(self, file_paths: Sequence[str]) -> Iterator[str]:
        """Collect all filter files to be checked."""
        for file in file_paths:
            # make absolute path from input file
            if not os.path.isabs(file):
                file = os.path.join(self.working_dir, file)
            if os.path.isdir(file):
                for root, _, sub_files in os.walk(file):
                    yield from self.collect_files([os.path.join(root, f) for f in sub_files])
            else:
                if any(
                    fnmatch.fnmatch(file, excluded_file) for excluded_file in self.excluded_files
                ):
                    continue
                extension = os.path.splitext(file)[1][1:]
                try:
                    SourceFile.get_source_file_by_file_type(extension)
                    yield file
                except ValueError:
                    pass


class SourceFile:
    """Represent single file with copyright header."""

    FILE_EXTENSIONS: list[str] = []
    YEAR_RANGE_REGEX = r"((?:\d{4}(?:-\d{4})?(?:, ?\d{4}(?:-\d{4})?)*)+)"

    def __init__(
        self,
        file_path: str,
        template: str = DEFAULT_COPYRIGHT_TEMPLATE,
        holder: str = DEFAULT_HOLDER,
        trailing_newline: bool = True,
    ):
        """Source file initialization."""
        self.file_path = file_path
        self.template = template
        self.holder = holder
        self.trailing_newline = trailing_newline

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}: {self.file_path}"

    def get_copyright_index(self) -> int:
        """Get index of existing copyright.

        :raises RuntimeError: The file does not contain copyright
        """
        regex = self.render_copyright_template()
        content = self._load_file()
        matches = re.search(re.compile(regex), content)
        if not matches:
            raise RuntimeError(f"The file {self.file_path} does not contain copyright.")
        return content[: matches.start()].count("\n")

    def calc_copyright_position(self) -> int:
        """Calculate expected position of copyright header to be places in a file."""
        return 0

    @classmethod
    def get_source_file_by_file_type(cls, file_type: str) -> Type["SourceFile"]:
        """Get SourceFile type based on the file type extension."""
        for source_type in SourceFile.__subclasses__():
            if file_type in source_type.FILE_EXTENSIONS:
                return source_type
        raise ValueError(f"Unsupported file type: {file_type}.")

    @classmethod
    @abstractmethod
    def comment_text(cls, text: str) -> str:
        """Create commented text from input string."""

    def add_copyright(self, year_ranges: YearRanges) -> None:
        """Add new copyright to the file."""
        copyright_lines = self.render_copyright_text(str(year_ranges)).splitlines(keepends=True)
        with open(self.file_path, encoding="utf-8") as f:
            content_lines = f.read().splitlines(keepends=True)
        index = self.calc_copyright_position()
        for i, c in enumerate(copyright_lines):
            content_lines.insert(index + i, c)
        # add newline if enabled and not there already
        if self.trailing_newline and content_lines[index + len(copyright_lines)] != "\n":
            content_lines.insert(index + len(copyright_lines), "\n")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("".join(content_lines))

    def update_copyrights_year_range(self, year_ranges: YearRanges) -> None:
        """Update year range of existing copyright."""
        if not self.contains_copyright():
            logger.debug(f"Nothing to update, the file does not contain copyright {self.file_path}")
            return
        new_copyright = self.render_copyright_text(str(year_ranges)).splitlines(keepends=True)
        with open(self.file_path, encoding="utf-8") as f:
            content_lines = f.read().splitlines(keepends=True)
        # first, remove the old copyright
        index = self.get_copyright_index()
        del content_lines[index : index + len(new_copyright)]
        # add new copyright
        for i, c in enumerate(new_copyright):
            content_lines.insert(index + i, c)
        # add newline if enabled and not there already
        if self.trailing_newline and content_lines[index + len(new_copyright)] != "\n":
            content_lines.insert(index + len(new_copyright), "\n")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("".join(content_lines))

    def check(self) -> CheckResult:
        """Run the check on single file.

        :return: Check result enum
        """
        try:
            has_copyright = self.contains_copyright()
        except FileNotFoundError:
            return CheckResult.FILE_NOT_FOUND
        if not has_copyright:
            return CheckResult.NO_COPYRIGHT
        year_ranges = self.get_year_ranges()
        if not year_ranges:
            # has copyright without year_ranges, nothing else to check
            return CheckResult.SUCCEEDED
        for year_range in year_ranges:
            if year_range.is_year_in_range(THIS_YEAR):
                return CheckResult.SUCCEEDED
        return CheckResult.INVALID_YEAR

    def fix(self) -> None:
        """Fix copyright on single file."""
        result = self.check()
        if result == CheckResult.SUCCEEDED:
            return
        if result == CheckResult.FILE_NOT_FOUND:
            logger.info(f"File {self.file_path} does not exist. Skipping fixing.")
            return
        # copyright is missing, add brand new one
        if not self.contains_copyright():
            self.add_copyright(YearRanges([YearRange(from_year=THIS_YEAR)]))
        else:
            year_ranges = self.get_year_ranges()
            if not year_ranges:
                logger.info(
                    "The copyright does not have the year range in the template. Nothing to fix."
                )
                return
            last_entry = year_ranges[-1]
            if (last_entry.to_year is None and last_entry.from_year == THIS_YEAR - 1) or (
                last_entry.to_year == THIS_YEAR - 1
            ):
                # Consecutive year
                last_entry.to_year = THIS_YEAR
            else:
                # New entry for non-consecutive year
                year_ranges.append(YearRange(from_year=THIS_YEAR))
            self.update_copyrights_year_range(year_ranges)

    def contains_copyright(self) -> bool:
        """Returns True if file already contains existing copyright, False otherwise."""
        regex = self.render_copyright_template()
        content = self._load_file()
        matches = re.search(re.compile(regex), content)
        return bool(matches)

    def get_year_ranges(self) -> YearRanges:
        """Get year ranges from copyright text."""
        content = self._load_file()
        regex = self.render_copyright_template()
        matches = re.findall(re.compile(regex), content)
        ranges: YearRanges = YearRanges([])
        for match in matches:
            for part in match.split(","):
                years = part.split("-")
                ranges.append(
                    YearRange(
                        from_year=int(years[0]), to_year=int(years[1]) if len(years) > 1 else None
                    )
                )
        return ranges

    def render_copyright_text(self, copyright_years: str) -> str:
        """Render copyright text from template."""
        template_text = self.comment_text(self.template)
        env = Environment(autoescape=True, keep_trailing_newline=True)
        template = env.from_string(template_text)
        copyright_text = template.render(copyright_years=copyright_years, holder=self.holder)
        copyright_text = self.fix_trailing_newline(copyright_text)
        return copyright_text

    def render_copyright_template(self) -> str:
        """Render the copyright template."""
        copyright_regex = self.comment_text(self.template)
        copyright_regex = self.re_escape(copyright_regex)
        env = Environment(autoescape=True, keep_trailing_newline=True)
        template = env.from_string(copyright_regex)
        return template.render(copyright_years=self.YEAR_RANGE_REGEX, holder=self.holder)

    def re_escape(self, regex: str) -> str:
        """Escape regex special characters."""
        # let's not escape spaces, so we translate it on our own, not using re.escape
        special_chars_map = {i: "\\" + chr(i) for i in b"()[]?*+-|^$\\.&~#\t\n\r\v\f"}
        return regex.translate(special_chars_map)

    @classmethod
    def fix_trailing_newline(cls, text: str) -> str:
        """Add trailing new line character to the text if enabled."""
        # every copyright must end with newline
        if text[-1] != "\n":
            text += "\n"
        return text

    def _load_file(self) -> str:
        if not os.path.isfile(self.file_path):
            raise FileNotFoundError(self.file_path)
        with open(self.file_path, encoding="utf-8") as f:
            return f.read()


class PythonSourceFile(SourceFile):
    """Represent single Python file with copyright header."""

    FILE_EXTENSIONS = ["py"]

    @classmethod
    def comment_text(cls, text: str) -> str:
        """Create commented text from input string."""
        lines = text.splitlines(keepends=False)
        for i, s in enumerate(lines):
            lines[i] = "#" if not s else f"# {s}"
        return "\n".join(lines)

    def calc_copyright_position(self) -> int:
        """Calculate expected position of copyright header to be places in a file."""
        text = self._load_file()
        lines = text.splitlines(keepends=True)
        index = 0
        for i, s in enumerate(lines):
            # copyright is always placed after first commented line
            if not s.startswith("#"):
                index = i
                break
        return index

    def add_copyright(self, year_ranges: YearRanges) -> None:
        """Add new copyright to the file."""
        copyright_lines = self.render_copyright_text(str(year_ranges)).splitlines(keepends=True)
        with open(self.file_path, encoding="utf-8") as f:
            content_lines = f.read().splitlines(keepends=True)
        index = self.calc_copyright_position()
        # If the copyright isn't first text, we add an empty line
        if index:
            copyright_lines.insert(0, self.comment_text("\n"))
        for i, c in enumerate(copyright_lines):
            content_lines.insert(index + i, c)
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("".join(content_lines))


class YamlSourceFile(SourceFile):
    """Represent single YAML file with copyright header."""

    FILE_EXTENSIONS = ["yml", "yaml"]

    @classmethod
    def comment_text(cls, text: str) -> str:
        """Create commented text from input string."""
        lines = text.splitlines(keepends=False)
        for i, s in enumerate(lines):
            lines[i] = "#" if not s else f"# {s}"
        return "\n".join(lines)


class XmlSourceFile(SourceFile):
    """Represent single XML file with copyright header."""

    FILE_EXTENSIONS = ["xml"]

    @classmethod
    def comment_text(cls, text: str) -> str:
        """Create commented text from input string."""
        lines = text.splitlines(keepends=False)
        for i, s in enumerate(lines):
            lines[i] = f"  {s}"
        lines.insert(0, "<!--")
        lines.append("-->")
        return "\n".join(lines)

    def calc_copyright_position(self) -> int:
        """Calculate expected position of copyright header to be places in a file."""
        text = self._load_file()
        lines = text.splitlines(keepends=True)
        return 1 if re.match(r"<\?xml version.*\?>", lines[0]) else 0


class CSourceFile(SourceFile):
    """Represent single C source file with copyright header."""

    FILE_EXTENSIONS = ["c"]

    @classmethod
    def comment_text(cls, text: str) -> str:
        """Create commented text from input string."""
        lines = text.splitlines(keepends=False)
        for i, s in enumerate(lines):
            lines[i] = f" * {s}" if s else " *"
        # lines.insert(0, "/*")
        # lines.append(" */")
        return "\n".join(lines)

    def calc_copyright_position(self) -> int:
        """Calculate expected position of copyright header to be places in a file."""
        text = self._load_file()
        lines = text.splitlines(keepends=True)
        index = 0
        for i, s in enumerate(lines):
            # copyright is always placed after first commented line
            if re.match(string=s, pattern=r"^ *?\n"):  # Empty lines
                continue
            if s.startswith("/*"):  # Found comment at beginning of file
                index = i
                break
            # No comments before code!
            index = 0
            break
        return index

    def add_copyright(self, year_ranges: YearRanges) -> None:
        """Add new copyright to the file."""
        copyright_lines = self.render_copyright_text(str(year_ranges)).splitlines(keepends=True)
        index = self.calc_copyright_position()
        if index == 0:
            copyright_lines.insert(0, "/*\n")
            copyright_lines.append(" */\n")
        else:
            copyright_lines.append(" *")
        with open(self.file_path, encoding="utf-8") as f:
            content_lines = f.read().splitlines(keepends=True)
        for i, c in enumerate(copyright_lines):
            content_lines.insert(index + i, c)
        # add newline if enabled and not there already
        if self.trailing_newline and content_lines[index + len(copyright_lines)] != "\n":
            content_lines.insert(index + len(copyright_lines), "\n")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("".join(content_lines))


class JavaScriptSourceFile(SourceFile):
    """Represent single Javascript file with copyright header."""

    FILE_EXTENSIONS = ["js"]

    @classmethod
    def comment_text(cls, text: str) -> str:
        """Create commented text from input string."""
        lines = text.splitlines(keepends=False)
        for i, s in enumerate(lines):
            lines[i] = f" * {s}" if s else " *"
        # lines.insert(0, "/*")
        # lines.append(" */")
        return "\n".join(lines)

    def calc_copyright_position(self) -> int:
        """Calculate expected position of copyright header to be places in a file."""
        text = self._load_file()
        lines = text.splitlines(keepends=True)
        index = 0
        for i, s in enumerate(lines):
            # copyright is always placed after first commented line
            if re.match(string=s, pattern=r"^ *?\n"):  # Empty lines
                continue
            if s.startswith("/*"):  # Found comment at beginning of file
                index = i
                break
            # No comments before code!
            index = 0
            break
        return index

    def add_copyright(self, year_ranges: YearRanges) -> None:
        """Add new copyright to the file."""
        copyright_lines = self.render_copyright_text(str(year_ranges)).splitlines(keepends=True)
        index = self.calc_copyright_position()
        if index == 0:
            copyright_lines.insert(0, "/*\n")
            copyright_lines.append(" */\n")
        else:
            copyright_lines.append(" *")
        with open(self.file_path, encoding="utf-8") as f:
            content_lines = f.read().splitlines(keepends=True)
        for i, c in enumerate(copyright_lines):
            content_lines.insert(index + i, c)
        # add newline if enabled and not there already
        if self.trailing_newline and content_lines[index + len(copyright_lines)] != "\n":
            content_lines.insert(index + len(copyright_lines), "\n")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("".join(content_lines))


class TypeScriptSourceFile(SourceFile):
    """Represent single TypeScript file with copyright header."""

    FILE_EXTENSIONS = ["ts"]

    @classmethod
    def comment_text(cls, text: str) -> str:
        """Create commented text from input string."""
        lines = text.splitlines(keepends=False)
        for i, s in enumerate(lines):
            lines[i] = f" * {s}" if s else " *"
        # lines.insert(0, "/*")
        # lines.append(" */")
        return "\n".join(lines)

    def calc_copyright_position(self) -> int:
        """Calculate expected position of copyright header to be places in a file."""
        text = self._load_file()
        lines = text.splitlines(keepends=True)
        index = 0
        for i, s in enumerate(lines):
            # copyright is always placed after first commented line
            if re.match(string=s, pattern=r"^ *?\n"):  # Empty lines
                continue
            if s.startswith("/*"):  # Found comment at beginning of file
                index = i
                break
            # No comments before code!
            index = 0
            break
        return index

    def add_copyright(self, year_ranges: YearRanges) -> None:
        """Add new copyright to the file."""
        copyright_lines = self.render_copyright_text(str(year_ranges)).splitlines(keepends=True)
        index = self.calc_copyright_position()
        if index == 0:
            copyright_lines.insert(0, "/*\n")
            copyright_lines.append(" */\n")
        else:
            copyright_lines.append(" *")
        with open(self.file_path, encoding="utf-8") as f:
            content_lines = f.read().splitlines(keepends=True)
        for i, c in enumerate(copyright_lines):
            content_lines.insert(index + i, c)
        # add newline if enabled and not there already
        if self.trailing_newline and content_lines[index + len(copyright_lines)] != "\n":
            content_lines.insert(index + len(copyright_lines), "\n")
        with open(self.file_path, "w", encoding="utf-8") as f:
            f.write("".join(content_lines))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="""Check whether "files" have the current year in Copyright."""
    )
    parser.add_argument("files", nargs="*", help="Files to analyze")
    parser.add_argument("--fix", action="store_true", help="Fix the copyright in files")
    args = parser.parse_args(argv)
    checker = CopyrightChecker()
    ret_val = checker.check_files(args.files)
    if args.fix:
        checker.fix_files(args.files)
    return ret_val


if __name__ == "__main__":
    sys.exit(main())
