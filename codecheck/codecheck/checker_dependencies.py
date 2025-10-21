#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2021-2025 NXP
#
# SPDX-License-Identifier: BSD-3-Clause
"""Script to list all Python package dependencies and their dependencies."""

import argparse
import csv
import json
import logging
import os
import sys
from abc import abstractmethod
from collections.abc import Iterable
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type
from urllib.parse import urlparse

import packaging
import prettytable
import tomli
from packaging.metadata import Metadata
from packaging.requirements import Requirement
from packaging.version import Version
from typing_extensions import Self, TypeGuard
from yaml import safe_load

THIS_DIR = Path(__file__).parent.resolve()
ROOT_DIR = THIS_DIR.parent
LIBRARY_PATH = Path(packaging.__path__[0]).parent

logger = logging.getLogger(__name__)


def load_pyproject_toml() -> Dict:
    """Load pyproject toml configuration."""
    pyproject_path = Path(os.getcwd(), "pyproject.toml")
    if os.path.exists(pyproject_path):
        with open(pyproject_path, "rb") as f:
            config = tomli.load(f)
            return config
    return {}


def load_spdx_config() -> Dict:
    """Load spdx configuration."""
    spdx = {}
    pyproject_config = load_pyproject_toml()
    spdx = pyproject_config.get("tool", {}).get("checker_dependencies", {}).get("spdx")
    if not spdx:
        default_data = THIS_DIR.joinpath("default_cfg.yaml").read_text(encoding="utf-8")
        spdx = safe_load(default_data)["spdx"]
    return spdx


class LicenseBase:
    """Base class for license."""

    SOURCE = "unknown"

    def __init__(self, license_str: Optional[str] = None) -> None:
        """License base initialization."""
        self.license = license_str
        self.spdx_config = load_spdx_config()

    def is_spdx(self) -> bool:
        """Is license SPDX license."""
        return self.get_spdx() is not None

    def get_spdx(self) -> Optional[str]:
        """Get SPDX version of the given license."""
        if not self.license:
            return None
        if self.license in self.spdx_config:
            return self.license
        for spdx, alternatives in self.spdx_config.items():
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
    def load(cls, data: Dict, **kwargs: Any) -> Optional[Self]:
        """Load license from configuration."""

    def __repr__(self) -> str:
        return f"<License source={self.SOURCE},spdx={self.get_spdx() or 'No'}>"


class ManualLicense(LicenseBase):
    """Manual license record type class."""

    SOURCE = "manual"

    def refresh(self) -> None:
        """Fetch the license from the source."""
        # Nothing to do here, license must be updated manually

    @classmethod
    def load(cls, data: Dict, **kwargs: Any) -> Optional[Self]:
        """Load license from configuration."""
        license_str = data.get(cls.SOURCE, {}).get("license")
        if not license_str:
            return None
        return cls(license_str)

    def to_dict(self) -> Dict:
        """Export license to configuration."""
        if self.license:
            return {"license": self.license}
        return {}


class LocalPackageLicense(LicenseBase):
    """Local packages license record type class."""

    SOURCE = "package"

    def __init__(self, package_name: str, license_str: Optional[str] = None) -> None:
        """Local package license initialization."""
        self.package_name = package_name
        super().__init__(license_str)

    def refresh(self) -> None:
        """Fetch the license from the source."""

        def get_license() -> Optional[str]:
            assert meta
            if meta.license:
                return meta.license
            if meta.license_expression:
                return meta.license_expression
            if meta.classifiers:
                for classifier in meta.classifiers:
                    if "License :: OSI Approved :: " in classifier:
                        return classifier.removeprefix("License :: OSI Approved :: ")
            return None

        meta = get_package_metadata(name=self.package_name)
        if meta is None:
            raise NameError(f"Package {self.package_name} is not installed")
        lic = get_license()
        if not lic:
            raise ValueError(f"Package {self.package_name} doesn't have License in Metadata")
        self.license = lic.split("\n")[0]

    @classmethod
    def load(cls, data: Dict, **kwargs: Any) -> Optional[Self]:
        """Load license from configuration."""
        try:
            name = data[cls.SOURCE]["name"]
            license_str = data[cls.SOURCE].get("license")
        except KeyError:
            logger.info("Package name must be specified")
            return None
        return cls(name, license_str)

    def to_dict(self) -> Dict:
        """Export license to configuration."""
        return {"name": self.package_name, "license": self.license or ""}


class GithubLicense(LicenseBase):
    """GitHub license record type class."""

    SOURCE = "github"

    def __init__(
        self,
        project_name: str,
        github_token: Optional[str] = None,
        license_str: Optional[str] = None,
    ) -> None:
        """Github license initialization."""
        self.project_name = project_name
        self.github_token = github_token
        super().__init__(license_str)

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
    def load(cls, data: Dict, **kwargs: Any) -> Optional[Self]:
        """Load license from configuration."""
        github_data: Optional[Dict] = data.get(cls.SOURCE)
        if not github_data:
            return None
        return cls(
            github_data["project_name"],
            github_token=kwargs.get("github_token"),
            license_str=github_data.get("license"),
        )

    @classmethod
    def load_from_url(cls, url: str) -> Optional[Self]:
        """Load from project url."""
        parsed_url = urlparse(url)
        if parsed_url.hostname != "github.com":
            return None
        return cls(project_name=parsed_url.path.strip("/"))

    def to_dict(self) -> Dict:
        """Export license to configuration."""
        return {"project_name": self.project_name, "license": self.license or ""}


# dictionary of license type priorities
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
        lic = self.get_spdx_license()
        version = self.get_version()
        dep_info = f"Name: {self.name}\n"
        dep_info += f"Home page: {self.home_page}\n"
        dep_info += f"Version: {version}\n" if version else "Unknown version"
        if lic:
            dep_info += f"Source: {lic.SOURCE}"
            dep_info += f"Spdx: {lic.license}"
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
        version = self.get_version()
        return f"<DepInfo name={self.name},version={version if version else 'Unknown version'}>"

    def to_dict(self) -> Dict:
        """Export package to configuration."""
        config: Dict = {"home_page": self.home_page, "name": self.name}
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

    def get_version(self) -> Optional[Version]:
        """Get package version."""
        meta = get_package_metadata(name=self.name)
        if meta is None:
            return None
        return meta.version


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
    def from_approved_packages(cls, file_path: Path, **kwargs: Any) -> Self:
        """Load dependency info from approved packages."""
        if not os.path.exists(file_path):
            return cls()

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        packages = cls()
        for package_data in data["packages"]:
            licenses = []

            for license_type in dict(sorted(LICENSE_TYPES.items())).values():
                license_obj = license_type.load(package_data, **kwargs)
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
        table = prettytable.PrettyTable(
            ["Name", "Version", "Home Page", "Spdx", "Source", "Need Check"]
        )
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
                    dep.get_version() if dep.get_version() else "Unknown version",
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
    :return: Package metadata
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
        pass
    # some packages such as boolean.py replace dot with underscore
    new_name = name.replace(".", "_")
    gen = Path(LIBRARY_PATH).glob(f"{new_name}-*dist-info/METADATA")
    try:
        meta_file = next(gen)
    except StopIteration:
        # this is for cases where maintainers doesn't use proper casing
        pass

    return (
        Metadata.from_email(meta_file.read_text(encoding="utf-8"), validate=False)
        if meta_file
        else None
    )


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
    logger.warning(f"Package {meta.name} doesn't have homepage in Metadata")
    return None


@dataclass
class CheckerResult:
    """Dependencies checker result."""

    errors: int = 0
    messages: List[str] = field(default_factory=list)


class DependenciesChecker:
    """Dependencies checker."""

    def __init__(self, root_package: Optional[str] = None) -> None:
        """Dependencies checker initialization."""
        self.root_package = self._load_root_pkg_name(root_package)
        self.approved_packages_file = Path(os.getcwd(), "approved_packages.json")

    def _load_root_pkg_name(self, root_package: Optional[str] = None) -> str:
        if root_package:
            return root_package
        pyproject_config = load_pyproject_toml()
        root_package = pyproject_config.get("project", {}).get("name") or pyproject_config.get(
            "tool", {}
        ).get("checker_dependencies", {}).get("root_package")
        if not root_package:
            raise ValueError(
                "Root package name was not found. It must be specified with root_package parameter or in pyproject.toml"
            )

        return root_package

    def get_dependencies(self) -> List[str]:
        """Get list of dependencies."""
        dependencies = []

        def import_requirement(requirement: Requirement) -> None:
            meta = get_package_metadata(name=requirement.name)
            if meta is None:
                raise NameError(f"Package {requirement.name} is not installed")
            if meta.name in dependencies:
                return
            dependencies.append(meta.name)
            requirements = self._get_requirements(meta=meta, extras=requirement.extras)
            for dep in requirements:
                if dep.name not in dependencies:
                    import_requirement(dep)

        import_requirement(Requirement(self.root_package))
        return dependencies

    @staticmethod
    def _get_requirements(meta: Metadata, extras: Optional[Set[str]] = None) -> List[Requirement]:
        """Get list of requirements from metadata."""

        def is_included(req: Requirement) -> TypeGuard[bool]:
            if not req.marker:
                return True
            if not extras:
                return req.marker.evaluate()
            return any(req.marker.evaluate({"extra": e}) for e in extras)

        if not meta.requires_dist:
            return []
        requirements = list(filter(is_included, meta.requires_dist))
        # returning list-filter directly would solve the problem, but this is better for debugging
        return requirements  # type:ignore[return-value]

    def print_dependencies(self, output_file: Optional[str] = None, **kwargs: Any) -> None:
        """Print the dependencies and their licenses."""
        actual_dependencies = self.get_dependencies()
        # keep only the actual dependencies
        dependencies = DependenciesList(
            [
                dep
                for dep in DependenciesList.from_approved_packages(
                    file_path=self.approved_packages_file, **kwargs
                )
                if dep.name in actual_dependencies
            ]
        )
        dependencies_table = dependencies.get_table_string()
        if output_file:
            with open(output_file, mode="w", encoding="utf-8") as file:
                file.write(dependencies_table)
        print(dependencies_table)

    def print_licenses(self, output_file: Optional[str] = None, **kwargs: Any) -> None:
        """Print licenses."""
        approved_list = DependenciesList.from_approved_packages(
            file_path=self.approved_packages_file, **kwargs
        )
        licenses = []
        for lic in approved_list.spdx_licenses():
            licenses.append(lic)
        if output_file:
            with open(output_file, encoding="utf-8", mode="w") as file:
                for lic in licenses:
                    file.write(f"{lic}\n")
        else:
            for lic in licenses:
                print(lic)

    def export_csv(self, output_file: Optional[str] = None, **kwargs: Any) -> None:
        """Export dependencies into csv file."""
        approved_list = DependenciesList.from_approved_packages(
            file_path=self.approved_packages_file, **kwargs
        )
        data = [["Name", "Version", "Home Page", "Spdx", "Spdx Source"]]
        for dependency in self.get_dependencies():
            approved_package = approved_list.get(dependency)
            lic = approved_package.get_spdx_license()
            version = approved_package.get_version()
            data.append(
                [
                    dependency,
                    str(version) if version else "Unknown version",
                    approved_package.home_page,
                    lic.license if lic else "Unknown license",  # type: ignore
                    lic.SOURCE if lic else "No license source",
                ]
            )
        if output_file:
            with open(output_file, encoding="utf-8", mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerows(data)
        else:
            # just print csv into console
            for data_line in data:
                print(",".join(data_line))

    def check_dependencies(self, strict: bool = False, **kwargs: Any) -> CheckerResult:
        """Check if all dependencies are approved.

        :return: Number of violations
        """
        actual_dep_list = self.get_dependencies()
        approved_list = DependenciesList.from_approved_packages(
            file_path=self.approved_packages_file, **kwargs
        )
        approved_names = approved_list.names()
        result = CheckerResult()
        for actual_dep in actual_dep_list:
            if actual_dep not in approved_names:
                result.messages.append(f"Package '{actual_dep}' is not among approved packages!")
                result.errors += 1
                continue
            if not approved_list.get(actual_dep).get_spdx_license():
                result.messages.append(
                    f"Package '{actual_dep}' is among approved packages, but does not have valid license!"
                )
                result.errors += 1
                continue
            if not strict:
                continue

            approved_dependency = approved_list.get(actual_dep)
            license_obj = approved_dependency.get_spdx_license()
            if license_obj and license_obj.SOURCE != "manual":
                approved_license = license_obj.get_spdx()
                license_obj.refresh()
                spdx = license_obj.get_spdx()
                if not spdx:
                    logger.warning(f"Package '{actual_dep}' doesn't have SPDX license")
                    continue
                if spdx != approved_license:
                    result.messages.append(
                        f"Package '{actual_dep}' licenses differs."
                        f"Approved license:{approved_license}, actual SPDX license:{spdx}"
                    )
                    result.errors += 1
                    continue
        result.messages.append(
            f"Licenses of {len(actual_dep_list)} packages checked with {result.errors} problems."
        )
        return result

    def init_approved_file(self, **kwargs: Any) -> None:
        """Initialize the file with approved dependencies."""
        if os.path.isfile(
            self.approved_packages_file,
        ):
            print(f"'{self.approved_packages_file}' already exists.")
            answer = input("Do you want to continue? This will rewrite the file: (y/N): ")
            if answer.lower() != "y":
                return

        approved_packages = DependenciesList.from_approved_packages(
            file_path=self.approved_packages_file, **kwargs
        )
        actual_dependencies = self.get_dependencies()
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
                homepage = get_homepage(meta) or ""
                new_dep = DependencyInfo(
                    name=act_dep,
                    home_page=homepage,
                    licenses=[LocalPackageLicense(package_name=act_dep)],
                )
                new_dep.refresh()
                approved_packages.append(new_dep)

        print(f"Writing packages info to {self.approved_packages_file}")
        approved_packages.sort()
        data = {"packages": [package.to_dict() for package in approved_packages]}

        with open(self.approved_packages_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def fix_dependencies(self, **kwargs: Any) -> CheckerResult:
        """Fix the file with approved dependencies."""
        approved_packages = DependenciesList.from_approved_packages(
            file_path=self.approved_packages_file, **kwargs
        )
        actual_dependencies = self.get_dependencies()
        result = CheckerResult()
        for act_dep in actual_dependencies:
            if act_dep not in approved_packages.names():
                meta = get_package_metadata(act_dep)
                if meta is None:
                    raise ValueError(
                        f"Package {act_dep} is not installed. Can't fix packages metadata."
                    )
                homepage = get_homepage(meta) or ""
                new_dep = DependencyInfo(
                    name=act_dep,
                    home_page=homepage,
                    licenses=[LocalPackageLicense(package_name=act_dep)],
                )
                gh_license = GithubLicense.load_from_url(new_dep.home_page)
                if gh_license:
                    new_dep.licenses.append(gh_license)
                new_dep.refresh()
                approved_packages.append(new_dep)
                # Newly added dependency still needs manual fix
                if not new_dep.get_spdx_license():
                    result.errors += 1
                    result.messages.append(
                        f"Newly added dependency '{act_dep}' does not have spdx license."
                    )
                    continue
            approved_dependency = approved_packages.get(act_dep)
            license_obj = approved_dependency.get_spdx_license()
            if not license_obj:
                # Try to refresh the license
                approved_dependency.refresh()
                if not approved_dependency.get_spdx_license():
                    result.errors += 1
                    result.messages.append(
                        f"Already approved dependency '{act_dep}' does not have spdx license."
                    )
                continue
            if license_obj.SOURCE != "manual":
                license_obj.refresh()
                if not approved_dependency.get_spdx_license():
                    result.errors += 1
                    result.messages.append(
                        f"Already approved dependency '{act_dep}' does lost the spdx license after refresh."
                    )
                    continue
        approved_packages.sort()

        data = {"packages": [package.to_dict() for package in approved_packages]}
        with open(self.approved_packages_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return result


def parse_inputs(input_args: Optional[List[str]] = None) -> dict:
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
    parser.add_argument("-r", "--root-package", help="Main package to investigate")

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
    commands_parser.add_parser("export-csv", help="Export the licenses of dependencies into csv")
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
    handlers: Dict[str, str] = {
        "print": "print_dependencies",
        "print-lic": "print_licenses",
        "export-csv": "export_csv",
        "check": "check_dependencies",
        "init": "init_approved_file",
        "fix": "fix_dependencies",
    }
    args = parse_inputs()

    with redirect_stdout(
        open(args["output"], "w", encoding="utf-8") if args["output"] else sys.stdout
    ):
        checker = DependenciesChecker(args["root_package"])
        handler = getattr(checker, handlers[args["command"]])
        result = handler(**args)
        messages = result.messages if isinstance(result, CheckerResult) else []
        for message in messages:
            print(message)
        exit_code = result.errors if isinstance(result, CheckerResult) else 0
    print(f"Finished with exit code {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
