# Security Policy

VesicleScope is scientific research software and is not a medical device, diagnostic system or clinical decision tool.

## Supported versions

Security fixes are prioritized for the latest published release and the current `main` development line. Older release lines are supported on a best-effort basis unless a specific security advisory states otherwise.

## Reporting a vulnerability

Please **do not publish exploit details, secrets, private data or a proof of concept in a public issue**.

Preferred reporting route:

1. use GitHub's **Report a vulnerability** / private vulnerability reporting flow on this repository's Security tab when it is available;
2. if private vulnerability reporting is unavailable, contact the repository maintainer through a private contact method listed on the maintainer's GitHub profile;
3. if no private route is available, open a minimal public issue asking for a private contact channel **without including sensitive technical details**.

Include, when possible:

- affected version/commit and platform;
- attack preconditions and realistic impact;
- minimal reproduction information;
- whether the issue affects the loopback UI, workspace/filesystem boundary, native runner/build chain, artifact parsing or dependency supply chain;
- suggested mitigations, if known.

Please allow reasonable time for validation and remediation before public disclosure.

## Security-relevant boundaries

Examples of security issues include:

- escaping the configured workspace or arbitrary file overwrite/read;
- bypassing loopback/Host protections to expose the local UI unexpectedly;
- unsafe handling of untrusted experiment/run documents;
- command or argument injection into native build/execution paths;
- integrity failures that allow tampered run bundles to be accepted as valid;
- dependency/build-chain compromise;
- accidental exposure of credentials or private data.

The local workspace is designed for loopback use. It is **not** an authenticated multi-user web service and should not be exposed directly to untrusted networks.

## Scientific validity is separate

A disagreement about an EV model, parameter, biological interpretation, numerical assumption or external validation is usually **not a security vulnerability**. Those issues are still important: report them as normal scientific/engineering issues with evidence and context, following `CONTRIBUTING.md` and `AGENTS.md`.

If a scientific defect could create a software-security impact (for example, crafted input causing code execution or filesystem escape), use the private security route above.
