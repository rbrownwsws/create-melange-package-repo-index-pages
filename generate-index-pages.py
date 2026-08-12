# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "jinja2>=3.1.6",
#     "typer>=0.27.1",
# ]
# ///

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
import typer

SCRIPT_DIR: Final[Path] = Path(__file__).resolve().parent
TEMPLATES_DIR: Final[Path] = SCRIPT_DIR / "templates"


@dataclass(frozen=True, slots=True)
class RootIndex:
    signing_keys: list[str]
    arches: list[str]


@dataclass(frozen=True, slots=True)
class PackageFiles:
    package: str
    attestations: list[str]


@dataclass(frozen=True, slots=True)
class ArchIndex:
    name: str
    apkindex: Optional[str]
    packages: list[PackageFiles]


def find_arches(path: Path) -> list[str]:
    arches = []

    for entry in sorted(path.iterdir()):
        if entry.is_dir() and not entry.name.startswith("."):
            arches.append(entry.name)

    return arches


def find_signing_keys(path: Path) -> list[Path]:
    return map(lambda p: p.name, sorted(path.glob("*.pub")))


def find_package_index(path: Path) -> Optional[str]:
    apkindex = None

    for entry in path.iterdir():
        if entry.name == "APKINDEX.tar.gz":
            apkindex = entry.name
            break

    return apkindex


def find_packages(path: Path) -> list[Path]:
    return sorted(path.glob("*.apk"), reverse=True)


def find_attestations(path: Path, prefix: str) -> list[str]:
    return map(lambda p: p.name, sorted(path.glob(f"{prefix}*.sigstore.json")))


def index_root(repo_root: Path) -> RootIndex:
    arches = find_arches(repo_root)
    signing_keys = find_signing_keys(repo_root)

    return RootIndex(signing_keys=signing_keys, arches=arches)


def index_arch(arch_path: Path) -> ArchIndex:
    apkindex = find_package_index(arch_path)

    packages = find_packages(arch_path)

    package_files = []
    for package in packages:
        attestations = find_attestations(arch_path, package.name)
        package_files.append(
            PackageFiles(package=package.name, attestations=attestations)
        )

    return ArchIndex(name=arch_path.name, apkindex=apkindex, packages=package_files)


def main(repo_root: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html.j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    root_tmpl = env.get_template("root.html.j2")
    arch_tmpl = env.get_template("arch.html.j2")

    # Create the root index page
    print("Creating root index page")
    root_index = index_root(repo_root)

    (repo_root / "index.html").write_text(
        root_tmpl.render(index=root_index), encoding="utf-8"
    )

    # Create the arch index page(s)
    for arch in root_index.arches:
        print(f'Creating arch "{arch}" index page')
        arch_index = index_arch(repo_root / arch)
        (repo_root / arch / "index.html").write_text(
            arch_tmpl.render(index=arch_index), encoding="utf-8"
        )


if __name__ == "__main__":
    typer.run(main)
