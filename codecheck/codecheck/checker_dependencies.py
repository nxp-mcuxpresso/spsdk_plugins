#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2021-2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Script to list all Python package dependencies and their dependencies."""

import argparse
import json
import logging
import os
import sys
from abc import abstractmethod
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, TextIO, Type
from urllib.parse import urlparse

import packaging
import prettytable
import tomli
from mypy_extensions import KwArg
from packaging.metadata import Metadata
from packaging.requirements import Requirement
from packaging.version import Version
from pip import __version__ as pip_version
from typing_extensions import Self, TypeGuard

THIS_DIR = Path(__file__).parent.resolve()
ROOT_DIR = THIS_DIR.parent
APPROVED_PACKAGES_FILE = Path(os.getcwd(), "approved_packages.json")

LIBRARY_PATH = Path(packaging.__path__[0]).parent
MIN_PIP_VERSION = "21.2.0"

logger = logging.getLogger(__name__)


class LicenseBase:
    """Base class for license."""

    SOURCE = "unknown"

    def __init__(self, spdx_licensies: Dict[str, Any], license_str: Optional[str] = None) -> None:
        """License base initialization."""
        self.license = license_str
        self.spdx_licensies = spdx_licensies

    def is_spdx(self) -> bool:
        """Is license SPDX license."""
        return self.get_spdx() is not None

    def get_spdx(self) -> Optional[str]:
        """Get SPDX version of the diven license."""
        if not self.license:
            return None
        if self.license in self.spdx_licensies:
            return self.license
        for spdx, alternatives in self.spdx_licensies.items():
            if self.license in alternatives:
                return spdx
        return None

    @abstractmethod
    def refresh(self) -> None:
        """Fetch the license from the source."""

    @abstractmethod
    def to_dict(self) -> Dict:
        """Export license to configuration."""

    @classmethod
    @abstractmethod
    def load(cls, data: Dict, spdx_licensies: Dict[str, Any], **kwargs: Any) -> Optional[Self]:
        """Load license from configuration."""


class ManualLicense(LicenseBase):
    """Manual license record type class."""

    SOURCE = "manual"

    def refresh(self) -> None:
        """Fetch the license from the source."""

    @classmethod
    def load(cls, data: Dict, spdx_licensies: Dict[str, Any], **kwargs: Any) -> Optional[Self]:
        """Load license from configuration."""
        license_str = data.get(cls.SOURCE, {}).get("license")
        if not license_str:
            return None
        return cls(spdx_licensies, license_str)

    def to_dict(self) -> Dict:
        """Export license to configuration."""
        if self.license:
            return {"license": self.license}
        return {}


class LocalPackageLicense(LicenseBase):
    """Local packages license record type class."""

    SOURCE = "package"

    def __init__(
        self, spdx_licensies: Dict[str, Any], package_name: str, license_str: Optional[str] = None
    ) -> None:
        """Local package license initialization."""
        self.package_name = package_name
        super().__init__(spdx_licensies, license_str)

    def refresh(self) -> None:
        """Fetch the license from the source."""

        def get_license() -> Optional[str]:
            assert meta
            if meta.license:
                return meta.license
            if meta.classifiers:
                for clasifier in meta.classifiers:
                    if "License :: OSI Approved :: " in clasifier:
                        return clasifier.removeprefix("License :: OSI Approved :: ")
            return None

        meta = get_package_metadata(name=self.package_name)
        if meta is None:
            raise NameError(f"Package {self.package_name} is not installed")
        lic = get_license()
        if not lic:
            raise ValueError(f"Package {self.package_name} doesn't have License in Metadata")
        self.license = lic.split("\n")[0]

    @classmethod
    def load(cls, data: Dict, spdx_licensies: Dict[str, Any], **kwargs: Any) -> Optional[Self]:
        """Load license from configuration."""
        try:
            name = data[cls.SOURCE]["name"]
            license_str = data[cls.SOURCE].get("license")
        except KeyError:
            logger.info("Package name must be specified")
            return None
        return cls(spdx_licensies, name, license_str)

    def to_dict(self) -> Dict:
        """Export license to configuration."""
        return {"name": self.package_name, "license": self.license or ""}


class GithubLicense(LicenseBase):
    """GitHub license record type class."""

    SOURCE = "github"

    def __init__(
        self,
        spdx_licensies: Dict[str, Any],
        project_name: str,
        github_token: Optional[str] = None,
        license_str: Optional[str] = None,
    ) -> None:
        """Github license initialization."""
        self.project_name = project_name
        self.github_token = github_token
        super().__init__(spdx_licensies, license_str)

    def refresh(self) -> None:
        """Fetch the license from the source."""
        from github import Auth, Github, GithubException  # pylint: disable=import-outside-toplevel

        try:
            auth = Auth.Token(self.github_token) if self.github_token else None
            repo = Github(auth=auth).get_repo(self.project_name)
        except GithubException as exc:
            logger.warning(f"Failed to retrieve data form Github: {exc}")
            return
        spdx_id = getattr(repo.license, "spdx_id", "")
        self.license = spdx_id if spdx_id != "NOASSERTION" else None

    @classmethod
    def load(cls, data: Dict, spdx_licensies: Dict[str, Any], **kwargs: Any) -> Optional[Self]:
        """Load license from configuration."""
        github_data: Optional[Dict] = data.get(cls.SOURCE)
        if not github_data:
            return None
        return cls(
            spdx_licensies,
            github_data["project_name"],
            github_token=kwargs.get("github_token"),
            license_str=github_data.get("license"),
        )

    @classmethod
    def load_from_url(cls, url: str, spdx_licensies: Dict[str, Any]) -> Optional[Self]:
        """Load from project url."""
        parsed_url = urlparse(url)
        if parsed_url.hostname != "github.com":
            return None
        return cls(spdx_licensies=spdx_licensies, project_name=parsed_url.path.strip("/"))

    def to_dict(self) -> Dict:
        """Export license to configuration."""
        return {"project_name": self.project_name, "license": self.license or ""}


# dicitonary of license type priorities
LICENSE_TYPES: Dict[int, Type[LicenseBase]] = {
    1: LocalPackageLicense,
    2: GithubLicense,
    3: ManualLicense,
}


class DependencyInfo:
    """Basic information about a python package."""

    def __init__(
        self,
        name: str,
        home_page: str,
        licenses: Optional[List[LicenseBase]] = None,
    ) -> None:
        """Dependency info initialization."""
        self.name = name
        self.home_page = home_page
        self.licenses = licenses or []

    def __str__(self) -> str:
        license_str = self.get_spdx_license()
        dep_info = f"Name: {self.name}\n"
        dep_info += f"Home page: {self.home_page}\n"
        if license_str:
            dep_info += f"Source: {license_str.SOURCE}"
            dep_info += f"Spdx: {license_str.license}"
        return dep_info

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, self.__class__):
            return NotImplemented
        return self.name.lower() == __value.name.lower()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.name.lower() < other.name.lower()

    def __repr__(self) -> str:
        return f"<DepInfo name={self.name}>"

    def to_dict(self) -> Dict:
        """Export package to configuration."""
        config: Dict = {
            "home_page": self.home_page,
            "name": self.name,
        }
        for license_obj in self.licenses:
            config[license_obj.SOURCE] = license_obj.to_dict()
        return config

    def get_spdx_license(self, refresh: bool = False) -> Optional[LicenseBase]:
        """Get first spdx license from available licenses."""
        for license_obj in self.licenses:
            if refresh:
                license_obj.refresh()
            if license_obj.is_spdx():
                return license_obj
        return None

    def refresh(self) -> None:
        """Refresh licenses."""
        for license_obj in self.licenses:
            license_obj.refresh()


# pylint: disable=not-an-iterable, no-member
class DependenciesList(List[DependencyInfo]):
    """List of dependencies."""

    def __repr__(self) -> str:
        return f"<DepList len={len(self)}>"

    def names(self) -> List[str]:
        """Get names of all dependencies."""
        return [item.name for item in self]

    def spdx_licenses(self) -> List[str]:
        """Get SPDX licenses of all dependencies."""
        licenses: List[str] = []
        for item in self:
            spdx = item.get_spdx_license()
            if spdx is not None:
                if spdx.license:
                    licenses.append(spdx.license)
        return sorted(list(set(licenses)))

    def get(self, name: str) -> DependencyInfo:
        """Fetch dependency with given `name`."""
        for item in self:
            if item.name == name:
                return item
        raise NameError(f"DependencyInfo({name}) wasn't found!")

    def extend(self, __iterable: Iterable) -> None:
        """Extend current list by new list with dependency records."""
        for other in __iterable:
            self.append(other)

    def append(self, __object: DependencyInfo) -> None:
        """Append a new dependency record."""
        assert isinstance(__object, DependencyInfo)
        if __object not in self:
            super().append(__object)

    @classmethod
    def from_approved_packages(
        cls, file_path: Path = APPROVED_PACKAGES_FILE, **kwargs: Any
    ) -> Self:
        """Load dependency info from approved packages."""
        if not os.path.exists(file_path):
            return cls()

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        packages = cls()
        spdx_licensies = kwargs["spdx"]
        for package_data in data["packages"]:
            licenses = []

            for license_type in dict(sorted(LICENSE_TYPES.items())).values():
                license_obj = license_type.load(package_data, spdx_licensies, **kwargs)
                if license_obj:
                    licenses.append(license_obj)
            packages.append(
                DependencyInfo(
                    name=package_data["name"],
                    home_page=package_data["home_page"],
                    licenses=licenses,
                )
            )
        return packages

    def get_table_string(self) -> str:
        """Get the table of packages."""
        table = prettytable.PrettyTable(["Name", "Home Page", "Spdx", "Source", "Need Check"])
        table.align = "l"
        table.header = True
        table.border = True
        table.hrules = prettytable.ALL
        table.vrules = prettytable.ALL
        table._max_width = {  # pylint: disable=protected-access
            "Name": 20,
            "Home Page": 50,
            "Spdx": 30,
            "Source": 30,
            "Need Check": 3,
        }
        dependencies = sorted(self)
        for dep in dependencies:
            spdx = dep.get_spdx_license()
            table.add_row(
                [
                    dep.name,
                    dep.home_page,
                    spdx.get_spdx() if spdx else "",
                    spdx.SOURCE if spdx else "",
                    ("X" if not spdx or not spdx.get_spdx() or spdx.SOURCE == "manual" else ""),
                ]
            )
        return table.get_string()


def get_package_metadata(name: str) -> Optional[Metadata]:
    """Get Python package metadata.

    :param name: Name of package
    :return: PAckage metadata
    """
    new_name = name.replace("-", "_")
    gen = Path(LIBRARY_PATH).glob(f"{new_name}-*dist-info/METADATA")
    try:
        meta_file = next(gen)
    except StopIteration:
        # this is for cases where maintainers doesn't use proper casing
        pass

    def make_case_ignore(string: str) -> str:
        parts = [f"[{c.lower()}{c.upper()}]" if c.isalpha() else c for c in string]
        return "".join(parts)

    # Case-insensitive glob is available starting 3.12
    new_name = make_case_ignore(new_name)
    gen = Path(LIBRARY_PATH).glob(f"{new_name}-*dist-info/METADATA")
    try:
        meta_file = next(gen)
    except StopIteration:
        return None

    return Metadata.from_email(meta_file.read_text(encoding="utf-8"), validate=False)


def get_homepage(meta: Metadata) -> Optional[str]:
    """Get HomePage from metadata.

    :param meta: Python package metadata
    :return: Home page name if exists.
    """
    if meta.home_page:
        return meta.home_page
    possible_homepage_keys = [
        "Homepage",
        "Home",
        "homepage",
        "Source",
        "Documentation",
        "Source Code",
        "Source code",
        "Docs",
        "Repository",
        "repository",
    ]
    if meta.project_urls:
        for home_key in possible_homepage_keys:
            if home_key in meta.project_urls:
                return meta.project_urls[home_key]

    return None


def get_dependencies(root_package: str) -> List[str]:
    """Get list of dependencies."""
    dependencies = []

    def import_requirement(requirement: Requirement) -> None:
        meta = get_package_metadata(name=requirement.name)
        if meta is None:
            print(f"Package {requirement.name} is not installed")
            return
        if meta.name in dependencies:
            return
        dependencies.append(meta.name)
        requirements = get_requirements(meta=meta, extras=requirement.extras)
        for dep in requirements:
            if dep.name not in dependencies:
                import_requirement(dep)

    import_requirement(Requirement(root_package))
    return dependencies


def get_requirements(meta: Metadata, extras: Optional[Set[str]] = None) -> List[Requirement]:
    """Get list of requirements from metadata."""

    def is_included(req: Requirement) -> TypeGuard[bool]:
        if not req.marker:
            return True
        if not extras:
            return req.marker.evaluate()
        return any(req.marker.evaluate({"extra": e}) for e in extras)

    if not meta.requires_dist:
        return []
    reqs = list(filter(is_included, meta.requires_dist))
    # returning list-filter directly would solve the problem, but this is better for debugging
    return reqs  # type:ignore[return-value]


def print_dependencies(**kwargs: Any) -> int:
    """Print dependencies and their licenses."""
    approved_list = DependenciesList.from_approved_packages(**kwargs)
    print(approved_list.get_table_string())
    return 0


def print_licenses(**kwargs: Any) -> int:
    """Print licenses."""
    approved_list = DependenciesList.from_approved_packages(**kwargs)
    for lic in approved_list.spdx_licenses():
        print(lic)
    return 0


def check_dependencies(strict: bool = False, **kwargs: Any) -> int:
    """Check if all dependencies are approved.

    :return: Number of violations
    """
    actual_dep_list = get_dependencies(kwargs["root_package"])
    approved_list = DependenciesList.from_approved_packages(**kwargs)
    approved_names = approved_list.names()
    issues_counter = 0
    for actual_dep in actual_dep_list:
        if actual_dep not in approved_names:
            print(f"Package '{actual_dep}' is not among approved packages!")
            issues_counter += 1
            continue
        if not approved_list.get(actual_dep).get_spdx_license():
            print(
                f"Package '{actual_dep}' is among approved packages, but does not have valid license!"
            )
            issues_counter += 1
            continue
        if not strict:
            continue

        approved_dependency = approved_list.get(actual_dep)
        license_obj = approved_dependency.get_spdx_license()
        if license_obj and license_obj.SOURCE != "manual":
            approved_license = license_obj.get_spdx()
            license_obj.refresh()
            if license_obj.get_spdx() != approved_license:
                print(f"Package '{actual_dep}' licenses differs.")
                issues_counter += 1
                continue
    return issues_counter


def init_approved_file(**kwargs: Any) -> int:
    """Initialize the file with approved dependencies."""
    if os.path.isfile(APPROVED_PACKAGES_FILE):
        print(f"'{APPROVED_PACKAGES_FILE}' already exists.")
        answer = input("Do you want to continue? This will rewrite the file: (y/N): ")
        if answer.lower() != "y":
            return 0

    approved_packages = DependenciesList.from_approved_packages(**kwargs)
    actual_dependencies = get_dependencies(kwargs["root_package"])
    for act_dep in actual_dependencies:
        print(f"Processing the actual dependency {act_dep}")
        if act_dep in approved_packages.names():
            approved_packages.get(act_dep).refresh()
        else:
            meta = get_package_metadata(act_dep)
            if meta is None:
                raise ValueError(
                    f"Package {act_dep} is not installed. Can't initialize packages metadata."
                )
            homepage = get_homepage(meta)
            if not homepage:
                raise ValueError(f"Package {act_dep} doesn't have homepage in Metadata")
            new_dep = DependencyInfo(
                name=act_dep,
                home_page=homepage,
                licenses=[LocalPackageLicense(spdx_licensies=kwargs["spdx"], package_name=act_dep)],
            )
            new_dep.refresh()
            approved_packages.append(new_dep)

    print(f"Writing packages info to {APPROVED_PACKAGES_FILE}")
    approved_packages.sort()
    data = {"packages": [package.to_dict() for package in approved_packages]}

    with open(APPROVED_PACKAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return 0


def fix_dependencies(strict: bool = False, **kwargs: Any) -> int:
    """Fix the file with approved dependencies."""
    approved_packages = DependenciesList.from_approved_packages(**kwargs)
    actual_dependencies = get_dependencies(kwargs["root_package"])
    issues_counter = 0
    for act_dep in actual_dependencies:
        if act_dep not in approved_packages.names():
            meta = get_package_metadata(act_dep)
            if meta is None:
                raise ValueError(
                    f"Package {act_dep} is not installed. Can't fix packages metadata."
                )
            homepage = get_homepage(meta)
            if not homepage:
                raise ValueError(f"Package {act_dep} doesn't have homepage in Metadata")
            new_dep = DependencyInfo(
                name=act_dep,
                home_page=homepage,
                licenses=[LocalPackageLicense(spdx_licensies=kwargs["spdx"], package_name=act_dep)],
            )
            gh_license = GithubLicense.load_from_url(
                new_dep.home_page, spdx_licensies=kwargs["spdx"]
            )
            if gh_license:
                new_dep.licenses.append(gh_license)
            new_dep.refresh()
            approved_packages.append(new_dep)
            # Newly added dependency still needs manual fix
            lic = new_dep.get_spdx_license()
            if not lic:
                print(f"Newly added dependency '{act_dep}' does not have spdx license.")
                issues_counter += 1
                continue
        if not strict:
            continue

        approved_dependency = approved_packages.get(act_dep)
        license_obj = approved_dependency.get_spdx_license()
        if not license_obj:
            # Try to refresh the license
            approved_dependency.refresh()
            if not approved_dependency.get_spdx_license():
                print(f"Already approved dependency '{act_dep}' does not have spdx license.")
                issues_counter += 1
            continue
        if license_obj.SOURCE != "manual":
            license_obj.refresh()
            if not approved_dependency.get_spdx_license():
                print(
                    f"Already approved dependency '{act_dep}' does lost the spdx license after refresh."
                )
                issues_counter += 1
                continue
    approved_packages.sort()

    data = {"packages": [package.to_dict() for package in approved_packages]}
    with open(APPROVED_PACKAGES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return issues_counter


def parse_inputs(root_package: str, input_args: Optional[List[str]] = None) -> dict:
    """Parse user input parameters."""
    parser = argparse.ArgumentParser(
        description="Utility for checking licenses of all dependencies",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output",
        help="Path to output file.",
    )
    parser.add_argument(
        "--github_token",
        help="Github authorization token.",
    )
    parser.add_argument(
        "-r", "--root-package", default=root_package, help="Main package to investigate"
    )

    commands_parser = parser.add_subparsers(dest="command", metavar="SUB-COMMAND", required=True)
    check_parser = commands_parser.add_parser(
        "check", help="Check whether all dependencies are approved"
    )
    check_parser.add_argument(
        "--strict",
        action="store_true",
        help="License name in package must match string in database",
    )
    commands_parser.add_parser("print", help="Only print dependencies and their licenses")
    commands_parser.add_parser("print-lic", help="Only print licenses of dependencies")
    commands_parser.add_parser("init", help="Initialize the approved licenses list file")
    fix_parser = commands_parser.add_parser("fix", help="Fix the approved packaged licenses files")
    fix_parser.add_argument(
        "--strict",
        action="store_true",
        help="Fix the license name in database if changed.",
    )
    args = vars(parser.parse_args(input_args))
    return args


def main() -> int:
    """Main function."""
    if Version(pip_version) < Version(MIN_PIP_VERSION):
        print("Please install newer version of pip")
        print(f"Minimum version required: {MIN_PIP_VERSION}, you have: {pip_version}")
        print("To update pip run: 'python -m pip install --upgrade pip'")
        return 1

    handlers: Dict[str, Callable[[KwArg(Any)], int]] = {
        "print": print_dependencies,
        "print-lic": print_licenses,
        "check": check_dependencies,
        "init": init_approved_file,
        "fix": fix_dependencies,
    }

    spdx = {}
    toml = {}
    root_package = "codecheck"

    pyproject_toml_path = os.path.join(os.getcwd(), "pyproject.toml")
    if os.path.exists(pyproject_toml_path):
        with open(pyproject_toml_path, "rb") as f:
            toml = tomli.load(f)

    if toml.get("project") and toml["project"].get("name"):
        root_package = toml["project"]["name"]

    if toml.get("tool") and toml["tool"].get("checker_depencecies"):
        root_package = toml["tool"]["checker_depencecies"].get("root_package", root_package)
        spdx = toml["tool"]["checker_depencecies"].get("spdx", {})

    args = parse_inputs(root_package)
    args["spdx"] = spdx

    file = None
    original_stdout = None
    # redirect the output to file
    if args["output"]:
        original_stdout = sys.stdout
        sys.stdout = open(  # pylint: disable=consider-using-with
            args["output"], "w", encoding="utf-8"
        )
    try:
        handler = handlers[args["command"]]
        exit_code = handler(**args)
        print(f"Finished with exit code {exit_code}")
    finally:
        if file and isinstance(original_stdout, TextIO):
            file.close()
            sys.stdout = original_stdout
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
