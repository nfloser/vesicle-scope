# Explicit stored-run uncertainty ensembles

Issue: #67  
Status: first engine-independent uncertainty-propagation boundary

## Research gate

Reviewed before implementation:

- Grossfield et al., *Best Practices for Quantification of Uncertainty and Sampling Quality in Molecular Simulations*, Living Journal of Computational Molecular Science, DOI `10.33011/livecoms.1.1.5067`;
- SALib current documentation: https://salib.readthedocs.io/en/main/

The first VesicleScope uncertainty milestone deliberately separates three concepts:

1. **numerical convergence** asks whether a result changes with numerical resolution or timestep;
2. **uncertainty propagation** asks how an explicitly supplied set of uncertain inputs/runs maps to output variation;
3. **sensitivity analysis** attributes output variation to input factors and requires a sampling/analysis design such as Sobol or Morris.

The existing controlled diffusion × uptake factor experiment is therefore not renamed a global sensitivity analysis.

SALib remains a credible later option for formal sensitivity methods, but it is not required for the first stored-run ensemble summary. Adding its wider scientific Python dependency stack would not improve the semantics of simple descriptive statistics over already completed runs.

## Contract

`summarize_run_ensemble` accepts an explicit ordered tuple of validated `SimulationRunBundle` objects.

It does not:

- generate samples;
- invent parameter bounds;
- assign probability distributions;
- rerun BioFVM;
- infer biological plausibility;
- rank conditions.

Each member therefore keeps its full experiment parameter provenance, engine identity, numerical settings and exact VesicleScope revision in the original run bundle.

Experiment IDs must currently be unique within one ensemble. This keeps member identity auditable for the deterministic v0.2 development line. Repeated stochastic replicas require a future explicit seed/replicate identity contract rather than silently overloading experiment IDs.

## Supported quantities

The first version summarizes the final:

- integrated extracellular quantity;
- internalized quantity.

All member quantity units must agree.

For each quantity the analysis reports:

- member count;
- minimum;
- maximum;
- arithmetic mean;
- median.

For ensembles with at least 40 members, it also reports the empirical 2.5th–97.5th percentile interval using linear interpolation at position `(n - 1) p`.

The 40-member threshold is only a conservative **reporting guard**: it ensures at least one member per nominal 2.5% tail by count. It does **not** establish statistical adequacy.

The interval is explicitly called an **empirical percentile interval**. It is not a confidence interval and does not imply that members were sampled from a probability distribution.

## CLI

Stored bundles can be summarized without rerunning the solver:

```bash
vesiclescope run-bundle ensemble \
  runs/member-01.json \
  runs/member-02.json \
  runs/member-03.json
```

Input order is preserved in the reported member IDs.

For fewer than 40 members, the CLI prints the empirical 95% percentile interval as unavailable rather than manufacturing an unstable interval with stronger-looking semantics.

## Why no random sampler yet

A useful biological distribution requires evidence about the parameter, experimental context and distributional assumptions.

VesicleScope therefore does not provide generic “EV diffusion uncertainty” or “uptake uncertainty” defaults.

A future sampler can reuse this same boundary when:

- the distribution or finite design is explicitly supplied;
- its provenance is recorded;
- a deterministic seed is captured when randomness is used;
- the chosen sampling method is justified for the scientific question.

## Future sensitivity analysis

Sobol, Morris or related indices remain separate work.

If such a milestone is justified, SALib should be reevaluated rather than reimplementing established methods. The future workflow should keep the useful separation:

```text
provenance-bearing input design
        ↓
VesicleScope experiment generation
        ↓
stored run bundles
        ↓
uncertainty summary / sensitivity analysis
```

This preserves the solver-independent analysis boundary and keeps every primary simulation auditable.

## Scientific limits

An ensemble summary describes the supplied runs only.

It does not demonstrate:

- a physiological parameter range;
- a population distribution;
- a confidence interval for biological truth;
- model validity;
- experimental agreement;
- causal parameter importance.

Those claims require additional evidence, model checks and/or appropriate statistical design.
