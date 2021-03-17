
import argparse
import io
import shutil
import sys
import tarfile
import typing
import zipfile
from tqdm import tqdm
from io import BytesIO

import requests
from pathlib import Path, PurePath


#parser = argparse.ArgumentParser(description='Build kodi-stash-addon')
# parser.add_argument('target', )
# parser.add_argument('-o', metavar='FILE', type=Path, help='Addon output file.')
# parser.add_argument('--project', type=Path)


class Dependency(typing.NamedTuple):
    name: str
    version: str
    module_path: str

    def __str__(self) -> str:
        return f'{self.name}={self.version}'

    def module_root(self) -> Path:
        return Path(f'{self.name}-{self.version}/{self.module_path}')


class DependencySourceFile(typing.NamedTuple):
    name: str
    stream: io.BufferedReader


DEPENDENCIES = map(lambda a: Dependency(*a), [
    ('gql', '2.0.0', 'gql'),
    ('graphql-core', '2.3.2', 'graphql'),
    ('promise', '2.3', 'promise'),
    ('Rx', '3.1.1', 'rx')
])

def pypi_dependency_files(dependency: Dependency):
    response = requests.get(f'https://pypi.org/pypi/{dependency.name}/{dependency.version}/json')
    response.raise_for_status()

    package_info = response.json()
    urls = package_info['urls']

    sdists = [u['url'] for u in urls if u['packagetype'] == 'sdist']
    if len(sdists) == 0:
        raise Exception(f'No source dist found for package {dependency}')

    response = requests.get(sdists[0], stream=True)

    module_root = dependency.module_root()

    with tarfile.open(fileobj=response.raw, mode='r|*') as tar:
        for tarinfo in tqdm(tar, unit=' files', desc=str(dependency)):
            if not tarinfo.isfile():
                continue

            tarpath = Path(tarinfo.name)
            if tarpath.is_relative_to(module_root):
                yield DependencySourceFile(
                    name=tarpath.relative_to(module_root.parent),
                    stream=tar.extractfile(tarinfo)
                )


ARCHIVE_CONTENTS = [
    'addon.xml',
    'plugin.py',
    'resources/*'
]


with zipfile.ZipFile('plugin.video.stashapp.zip', 'w') as archive:
    root = Path('plugin.video.stashapp')

    print('adding files...', file=sys.stderr)
    for pattern in ARCHIVE_CONTENTS:
        files = Path('.').glob(pattern)

        for file in tqdm(files, unit=' files', desc=pattern):
            archive.write(file, arcname=str(root / file))

    print('adding dependencies...', file=sys.stderr)

    for dep in DEPENDENCIES:
        dep_files = pypi_dependency_files(dep)

        for dep_file in dep_files:
            with archive.open(str(root / dep_file.name), 'w') as zipitem:
                shutil.copyfileobj(dep_file.stream, zipitem)

