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
