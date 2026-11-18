# Smoldyn 2.75 artifact-specific license evidence

Issue #91; reviewed 2026-10-06. This narrows issue #83 using primary distribution evidence; it is not a blanket redistribution clearance or a maintainer response.

## Exact artifact inspected

- Official release page: https://www.smoldyn.org/download.html
- Official source archive: https://www.smoldyn.org/smoldyn-2.75.tgz
- Version: 2.75, dated 2025-07-30 on the official download page.
- Downloaded size: 34,008,076 bytes.
- Archive SHA-256: `f7116e207d6ba91d3f709b6839d8054a622383ac6e0c5f81108015d083a2a094`.
- `smoldyn-2.75/License.txt` SHA-256: `71d44b4fdf7443d25ac2748ff89eca8af4838eae3d58e836b291df30e30bdb84`.

The archive was inspected, not installed or executed. No source or binary is copied into VesicleScope.

## Current release recheck (2026-11-15)

The official download page now identifies Smoldyn 2.76, dated 2026-10-21,
as the current release. The matching upstream tag `v2.76` retains the same
license-metadata conflict documented for the development tree. Its annotated
tag object `97de63bc1a4f0c4e42c672a5139d3414bc3b4a64` resolves to peeled commit
`20fbcb965869a79a55a2c4844b35a66d9a2372a3`; all three reviewed blob
identities match that peeled commit:

- the root `LICENSE` remains [GPL v3](https://github.com/ssandrews/Smoldyn/blob/v2.76/LICENSE)
  (blob `f288702d2fa16d3cdf0035b15a9fcbc552cd88e7`);
- the tagged [`CMakeLists.txt`](https://github.com/ssandrews/Smoldyn/blob/v2.76/CMakeLists.txt)
  still labels Smoldyn project files LGPL (blob
  `b965a96d94f69700fc68a089217fbc89dd64a399`);
- the tagged [Python package metadata](https://github.com/ssandrews/Smoldyn/blob/v2.76/source/python/pyproject.toml.in)
  declares `LGPL-3.0-or-later` (blob
  `d28c7ff52d7f75409be07f83f8358edd05a36cff`).

This recheck does not replace the hash-verified 2.75 candidate. At the time of
the recheck, VesicleScope had not recorded an official 2.76 archive hash or
archive-level comparison. The later artifact comparison below closes that
identity gap but not the maintainer/legal clarification or component-license
gaps. The separate-process boundary and all existing blockers remain unchanged.

## Pinned 2.76 tag-tree inventory (2026-11-17)

The [Git commit API](https://api.github.com/repos/ssandrews/Smoldyn/git/commits/20fbcb965869a79a55a2c4844b35a66d9a2372a3)
maps the peeled commit above to root tree
`6c71c605a52972a4296b1c696ba8bb25c2bb6fbe`. A recursive Git tree request for
that [immutable object](https://api.github.com/repos/ssandrews/Smoldyn/git/trees/6c71c605a52972a4296b1c696ba8bb25c2bb6fbe?recursive=1)
returned a complete, non-truncated Git tree containing
365 directory objects and 4,727 blobs totalling 249,277,100 bytes. The largest
source subtrees are:

| Pinned subtree | Files | Bytes |
| --- | ---: | ---: |
| `source/NextSubVolume` | 1,398 files | 9,491,127 |
| `source/pybind11` | 372 files | 3,647,799 |
| `source/MSVClibs` | 17 files | 2,314,690 |
| `source/Smoldyn` | 24 files | 1,639,107 |
| `source/BioNetGen` | 79 files | 1,246,215 |
| `source/libSteve` | 59 files | 786,632 |
| `source/python` | 24 files | 279,775 |
| `source/vcell` | 7 files | 129,542 |

A conservative filename search found six license-like files: `LICENSE`,
`License.txt`, `source/BioNetGen/LICENSE.txt`,
`source/libSteve/SFMT/LICENSE.txt`, `source/pybind11/LICENSE` and
`windows/_freeglut/Copying.txt`. This is an inventory result, not a conclusion
that every other file shares one license. In particular, upstream
[`License.txt`](https://github.com/ssandrews/Smoldyn/blob/20fbcb965869a79a55a2c4844b35a66d9a2372a3/License.txt)
expressly names separately authored NextSubVolume, BioNetGen, filament and
Python-binding code.

The same tree contains 536 files with common binary or packaged-document
extensions, totalling 38,689,522 bytes, including payloads below `Mac`,
`windows`, `source`, `docs` and `examples`. The tagged
[`CMakeLists.txt`](https://github.com/ssandrews/Smoldyn/blob/20fbcb965869a79a55a2c4844b35a66d9a2372a3/CMakeLists.txt)
defaults also enable
NextSubVolume, Python, OpenGL and LibTIFF, while always adding `libSteve` and the
Smoldyn core targets. A future build decision therefore needs explicit CMake
flags and a build-output manifest; a repository tag alone does not identify the
components of an installed executable.

The earlier pinned inventory alone does not substitute for an official 2.76
archive hash or prove that the Git tree and download archive are
byte-equivalent. The artifact comparison below now demonstrates that they are
not content-equivalent. Neither result changes the 2.75 candidate or approves
any 2.76 use.

## Official 2.76 source-archive comparison (2026-11-18)

The official download page identifies
[`smoldyn-2.76.tgz`](https://www.smoldyn.org/smoldyn-2.76.tgz) as the complete
2.76 distribution with source code and no pre-compiled code. The downloaded
archive is 39,339,615 bytes with SHA-256
`10fd440dece77ae7304b019943256e08cc87ccef796db33eaf7461fcfb326fd7`.
It was inspected without installing or executing Smoldyn, and no archive
content is copied into VesicleScope.

All archive member paths were checked before inspection: none was absolute,
contained `..`, or escaped the single `smoldyn-2.76/` prefix. A deterministic
manifest of every regular file records the normalized relative path, byte size
and SHA-256, sorted by path. Its SHA-256 is
`3d5ba87ac75ac60f06455affbbaff6cb34fef0e204392d9db70086c5a97c570a`.
The equivalent manifest for peeled Git commit
`20fbcb965869a79a55a2c4844b35a66d9a2372a3` is
`4b6a1f477a0142280704faa2b5857bf8b4d8e3c7875976e396377b3b24680d12`.

The archive contains 3,965 regular files totalling 74,010,835 bytes; the Git
tree contains 4,727 regular files totalling 249,277,100 bytes. Comparing the
normalized path and content hash yields 2,465 path-and-content matches, 1,499
archive-only files, 2,261 Git-only files and one differing common file
(`docs/Smoldyn/SmoldynCodeDoc.pdf`). The dominant differences are 1,414
archive-only generated documentation files and 2,104 Git-only example files.
The archive also contains four AppleDouble metadata files.

The distribution retains `License.txt`, whose content matches the tagged file,
but does not contain the tagged root `LICENSE` that states GPL v3. Therefore the
official source archive is not content-equivalent to the pinned Git tree, and
the tag cannot serve as a file-level substitute for the distributed artifact.
This result identifies the release artifact and makes the metadata discrepancy
more precise; it does not decide which terms apply, inventory every component's
obligations, approve installation or redistribution, or supersede the separate
2.75 native-process candidate.

## Component-specific result

The official page distinguishes LGPL author-owned core, GPL v3 Python bindings, LGPL Next Subvolume code, and public-domain reaction/surface parameter files. The archive's `License.txt` expressly places the author-owned compiled program, source and documentation under LGPL, while enumerating third-party exceptions. It includes LGPL v3 and GPL v3 license texts; the presence of both texts alone does not classify every file.

Core and CMake headers support the LGPL statement. The archive also contains BioNetGen GPL v3 material and other independently copyrighted components. Python binding metadata in the development repository cannot override these component-specific official release statements.

The reviewed development commit `e21d6dd2c0411f5624b6da88c323597d6a92ee92` still has a GPL v3 root LICENSE alongside LGPL metadata. That discrepancy remains for development/Python/container artifacts; do not silently substitute them for the release archive.

## Integration decision

The documented candidate is now the exact official **2.75 native standalone program, supplied by the user and invoked as a separate process**. This avoids VesicleScope distributing, linking or automatically installing Smoldyn. It is a technically and documentarily better-defined path, not proof that any combination of components is cleared for redistribution.

For a prospective native build, `OPTION_PYTHON` must be OFF (the archive defaults it ON). Disabling Python does not remove all third-party obligations: native build sources include BioNetGen integration, and Next Subvolume and other options need an actual component/build inventory. A source-tarball hash does not establish the identity or license inventory of an arbitrary installed binary.

Do not add a required dependency, distribute a wheel/container/native binary, vendor source, or link a library on the strength of this review. Any bundled distribution needs exact build provenance, notices, source/compliance obligations and resolution of component exceptions. The project's own license remains unchanged.

## Remaining clarification

No maintainer was contacted and no legal approval is claimed. A precise upstream question would ask which terms apply to the exact 2.75 native executable and its enabled components, and how the official LGPL statement relates to the development repository GPL root and Python metadata. Ask separately about redistribution; invoking an independently installed executable is a different proposed operation.

The [scientific comparison gate](smoldyn-particle-comparison-gate.md) still requires diffusion-only matching, particle-count/timestep convergence, seeds and output provenance. License evidence does not establish mathematical agreement or EV biology.
