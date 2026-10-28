"""Offline identity verification for the reviewed Dryad version 3 snapshot.

This boundary verifies source bytes only. It does not parse measurements,
reconstruct exclusions or produce simulation parameters.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from pathlib import PurePosixPath
import stat
import zipfile


DRYAD_V3_FILES = (
    {'name': 'bEV_diffusion_host_response_bEV_Characterization_data_clean.csv', 'size_bytes': 1700, 'sha256': 'ad9f38347db942b0089ff49a218c4d854ec6263d85fb888af622ae30325b4a15'},
    {'name': 'bEV_diffusion_host_response_bEV_Characterization_removed_outliers.csv', 'size_bytes': 957, 'sha256': '24eccf7609fe09dc3d20f2ab127230d0397809171c90710c2554d1d2e4083933'},
    {'name': 'bEV_diffusion_host_response_bEV_Cytokine_data_clean.csv', 'size_bytes': 9307, 'sha256': '325b7e795baedae22554f4301f80bace2994be3035c06627ccdb0d090cdbcb38'},
    {'name': 'bEV_diffusion_host_response_bEV_Cytokine_removed_outliers.csv', 'size_bytes': 5631, 'sha256': 'e9a76c436a399fb76f7642b444b5590e7c1c4e4ad232a3e47773018b4a5f4505'},
    {'name': 'bEV_diffusion_host_response_bEV_Histogram_data_clean.csv', 'size_bytes': 52531, 'sha256': '2b6b0a65bf249c1b3db3ab0215ae5212ab73fa2f42ca331eca1184a827094002'},
    {'name': 'bEV_diffusion_host_response_bEV_Histogram_removed_outliers.csv', 'size_bytes': 49309, 'sha256': '5d586e67ab481e31e91f9bc33bbbf4faa9575e6eea538ce851121e7710cf14dc'},
    {'name': 'bEV_diffusion_host_response_bEV_uptake_data_clean.csv', 'size_bytes': 5084, 'sha256': 'd92c03c4dedb4628c94eb573286277cb7b2395a1ac494d32b3be604da88bb802'},
    {'name': 'bEV_diffusion_host_response_bEV_uptake_removed_outliers.csv', 'size_bytes': 2597, 'sha256': '09fb10afb12a6eacb0ba0c8bf2d2c73512ac91173bb7b349841b938451ecb29b'},
    {'name': 'bEV_diffusion_host_response_bEV_viability_data_clean.csv', 'size_bytes': 7472, 'sha256': 'bb3b39561539736eea65b05db400b684e28d5243dd403681394fe91015766894'},
    {'name': 'bEV_diffusion_host_response_bEV_viability_removed_outliers.csv', 'size_bytes': 4816, 'sha256': 'a2b0eb157fc66632c052c759d495696eb1a0be767005432b8293945aaac90e22'},
    {'name': 'bEV_diffusion_host_response_CVM_1sMSD.csv', 'size_bytes': 219034, 'sha256': '51a0e40c634654dfafbe977b5ff3e12dbf6fb7c316358b24c6240efbc753ce22'},
    {'name': 'bEV_diffusion_host_response_CVM_SampleInfo.csv', 'size_bytes': 930, 'sha256': '2b05330a4d5dec361361b06c046771610513b2667130659da21c90eac6b496a2'},
    {'name': 'README.md', 'size_bytes': 4597, 'sha256': 'e538bbc8798c1bcbd8a404ebfa8f018971571e349a5eba75d2529f015688e02c'},
)


def _validate_inventory(actual_names: set[str]) -> None:
    expected_names = {item['name'] for item in DRYAD_V3_FILES}
    missing = sorted(expected_names - actual_names)
    unexpected = sorted(actual_names - expected_names)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f'missing: {", ".join(missing)}')
        if unexpected:
            details.append(f'unexpected: {", ".join(unexpected)}')
        raise ValueError(f'Dryad v3 file inventory mismatch ({"; ".join(details)})')


def _read_directory(directory: Path) -> dict[str, bytes]:
    entries = list(directory.iterdir())
    non_files = sorted(entry.name for entry in entries if entry.is_symlink() or not entry.is_file())
    if non_files:
        raise ValueError(f'Dryad snapshot must contain regular files only: {", ".join(non_files)}')
    _validate_inventory({entry.name for entry in entries})
    expected_sizes = {item['name']: item['size_bytes'] for item in DRYAD_V3_FILES}
    for entry in entries:
        if entry.stat().st_size != expected_sizes[entry.name]:
            raise ValueError(f'{entry.name}: size does not match Dryad v3 metadata')
    return {entry.name: entry.read_bytes() for entry in entries}


def _read_zip(path: Path) -> dict[str, bytes]:
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise ValueError('Dryad snapshot file must be a valid ZIP archive') from exc
    with archive:
        entries = archive.infolist()
        if any(entry.is_dir() for entry in entries):
            raise ValueError('Dryad ZIP must contain regular top-level files only')
        if any(len(PurePosixPath(entry.filename).parts) != 1 for entry in entries):
            raise ValueError('Dryad ZIP must contain regular top-level files only')
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError('Dryad ZIP must not contain duplicate filenames')
        _validate_inventory(set(names))
        if any(entry.flag_bits & 0x1 for entry in entries):
            raise ValueError('Dryad ZIP must not contain encrypted files')
        if any(stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFLNK for entry in entries):
            raise ValueError('Dryad ZIP must contain regular top-level files only')
        expected_sizes = {item['name']: item['size_bytes'] for item in DRYAD_V3_FILES}
        for entry in entries:
            if entry.file_size != expected_sizes[entry.filename]:
                raise ValueError(f'{entry.filename}: size does not match Dryad v3 metadata')
        return {entry.filename: archive.read(entry) for entry in entries}


def verify_dryad_v3_source(path: Path) -> dict[str, object]:
    """Verify an extracted directory or ZIP against Dryad v3 metadata."""
    source = Path(path)
    if source.is_dir():
        raw_files = _read_directory(source)
        container = 'directory'
    elif source.is_file():
        raw_files = _read_zip(source)
        container = 'zip'
    else:
        raise ValueError('Dryad snapshot path must be a directory or ZIP archive')

    verified = []
    for expected in DRYAD_V3_FILES:
        raw = raw_files[expected['name']]
        if len(raw) != expected['size_bytes']:
            raise ValueError(
                f'{expected["name"]}: size does not match Dryad v3 metadata '
                f'({len(raw)} != {expected["size_bytes"]})'
            )
        digest = hashlib.sha256(raw).hexdigest()
        if digest != expected['sha256']:
            raise ValueError(f'{expected["name"]}: SHA-256 does not match Dryad v3 metadata')
        verified.append({
            'name': expected['name'],
            'size_bytes': len(raw),
            'sha256': digest,
        })

    return {
        'schema': 'vesiclescope.dryad-source-verification',
        'version': 1,
        'source': {
            'doi': '10.5061/dryad.cvdncjth8',
            'version_number': 3,
            'version_id': 412881,
            'license': 'CC0-1.0',
        },
        'verified_file_count': len(verified),
        'verified_size_bytes': sum(item['size_bytes'] for item in verified),
        'container': container,
        'verification_scope': 'file inventory, byte size and SHA-256 identity only',
        'ready_for_parameter_fitting': False,
        'limitations': [
            'Source identity does not establish measurement semantics or biological suitability.',
            'Units, replicate hierarchy, exclusions and aggregation remain unaudited.',
            'No measurement is converted into a simulation parameter.',
        ],
        'files': verified,
    }


def verify_dryad_v3_directory(path: Path) -> dict[str, object]:
    """Backward-compatible directory verification entry point."""
    if not Path(path).is_dir():
        raise ValueError('Dryad snapshot path must be a directory')
    return verify_dryad_v3_source(path)
