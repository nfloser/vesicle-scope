# BioFVM engine setup

VesicleScope keeps its scientific Python contracts separate from the native BioFVM executable, but the installed product can now verify and build the exact reviewed engine itself.

## Review pin

The engine pin remains repository-controlled in `vesiclescope/engines/physicell.env` and is packaged with VesicleScope.

Current reviewed identity:

- PhysiCell release: `1.14.2`
- PhysiCell commit: `dbd3499250141b27600e91e501c54c46f68f2763`
- BioFVM version: `1.1.7`

`vesiclescope engine build` never treats a branch tip as acceptable. The checkout commit and the BioFVM version reported by source are both verified before compilation.

## Check local readiness

```bash
vesiclescope engine status
```

This is network-free and reports:

- reviewed PhysiCell/BioFVM pin;
- whether `git` and `g++` are available;
- default PhysiCell cache path;
- default compiled runner path;
- whether that runner currently exists.

## Build using the default cache

```bash
vesiclescope engine build
```

If the pinned checkout is absent, this command:

1. clones only the reviewed PhysiCell release from the official MathCancer repository;
2. verifies the exact reviewed commit;
3. reads and verifies the BioFVM source version;
4. compiles VesicleScope's packaged canonical transport runner against the required BioFVM translation units;
5. writes the executable into the VesicleScope user cache.

This path requires network access only when the verified checkout is not already cached.

## Build from an existing checkout

For controlled/offline environments:

```bash
vesiclescope engine build \
  --physicell-dir /path/to/physicell \
  --no-fetch \
  --output /path/to/biofvm_transport_runner
```

The existing checkout is still verified. `--no-fetch` prevents fallback network access.

## Toolchain

The current Linux/native path requires:

- Git for source verification/fetch;
- a C++ compiler available as `g++`;
- OpenMP support compatible with the existing runner build flags.

The builder does not download or execute a prebuilt binary.

## Canonical source

The transport runner source is packaged at:

`vesiclescope/engines/native/transport_runner.cpp`

The repository Makefile and the installed engine builder both compile this same file. There is no second runner implementation for the product installer.

## Third-party obligations

PhysiCell/BioFVM remains a third-party dependency and is not vendored into VesicleScope. Its version, citation and license obligations are recorded separately in `THIRD_PARTY.md`.

Building the runner does not change VesicleScope's own repository licensing policy.
