#include "BioFVM.h"

#include <cmath>
#include <iomanip>
#include <iostream>

namespace
{
constexpr double domain_length = 1000.0;       // synthetic benchmark, micron
constexpr double domain_width = 100.0;         // synthetic benchmark, micron
constexpr double grid_spacing = 20.0;          // synthetic benchmark, micron
constexpr double diffusion_coefficient = 1000.0; // synthetic benchmark, micron^2/min
constexpr double time_step = 0.1;              // synthetic benchmark, min
constexpr double duration = 60.0;              // synthetic benchmark, min
constexpr double baseline = 1.0;               // synthetic dimensionless field
constexpr double amplitude = 0.5;              // synthetic dimensionless field

constexpr double relative_l2_tolerance = 5e-3;
constexpr double mean_tolerance = 1e-8;
}

int main()
{
    const double pi = std::acos(-1.0);

    BioFVM::Microenvironment microenvironment;
    microenvironment.name = "VesicleScope synthetic diffusion benchmark";
    microenvironment.set_density(0, "synthetic_mode", "dimensionless");

    microenvironment.resize_space(
        0.0,
        domain_length,
        0.0,
        domain_width,
        -0.5 * grid_spacing,
        0.5 * grid_spacing,
        grid_spacing,
        grid_spacing,
        grid_spacing
    );

    microenvironment.spatial_units = "micron";
    microenvironment.time_units = "min";
    microenvironment.mesh.units = "micron";

    if (
        microenvironment.spatial_units != "micron" ||
        microenvironment.time_units != "min" ||
        microenvironment.mesh.units != "micron"
    )
    {
        std::cerr << "BioFVM unit boundary was not set explicitly as expected.\n";
        return 2;
    }

    microenvironment.diffusion_coefficients[0] = diffusion_coefficient;
    microenvironment.decay_rates[0] = 0.0;
    microenvironment.diffusion_decay_solver =
        BioFVM::diffusion_decay_solver__constant_coefficients_LOD_2D;

    for (unsigned int n = 0; n < microenvironment.number_of_voxels(); ++n)
    {
        const double x = microenvironment.mesh.voxels[n].center[0];
        microenvironment.density_vector(static_cast<int>(n))[0] =
            baseline + amplitude * std::cos(pi * x / domain_length);
    }

    const int steps = static_cast<int>(std::lround(duration / time_step));
    for (int step = 0; step < steps; ++step)
    {
        microenvironment.simulate_diffusion_decay(time_step);
    }

    const double simulated_time = steps * time_step;
    const double attenuation = std::exp(
        -diffusion_coefficient *
        (pi / domain_length) *
        (pi / domain_length) *
        simulated_time
    );

    double squared_error = 0.0;
    double squared_reference = 0.0;
    double mean = 0.0;

    for (unsigned int n = 0; n < microenvironment.number_of_voxels(); ++n)
    {
        const double x = microenvironment.mesh.voxels[n].center[0];
        const double expected =
            baseline + amplitude * std::cos(pi * x / domain_length) * attenuation;
        const double actual =
            microenvironment.density_vector(static_cast<int>(n))[0];

        const double error = actual - expected;
        const double reference = expected - baseline;

        squared_error += error * error;
        squared_reference += reference * reference;
        mean += actual;
    }

    mean /= static_cast<double>(microenvironment.number_of_voxels());

    const double relative_l2 = std::sqrt(squared_error / squared_reference);
    const double mean_error = std::abs(mean - baseline);

    std::cout
        << std::setprecision(12)
        << "BioFVM_version=" << BioFVM::BioFVM_Version << '\n'
        << "voxels=" << microenvironment.number_of_voxels() << '\n'
        << "simulated_time_min=" << simulated_time << '\n'
        << "relative_l2_error=" << relative_l2 << '\n'
        << "mean_error=" << mean_error << '\n';

    if (relative_l2 > relative_l2_tolerance)
    {
        std::cerr
            << "Relative L2 error " << relative_l2
            << " exceeds tolerance " << relative_l2_tolerance << ".\n";
        return 1;
    }

    if (mean_error > mean_tolerance)
    {
        std::cerr
            << "Mean conservation error " << mean_error
            << " exceeds tolerance " << mean_tolerance << ".\n";
        return 1;
    }

    return 0;
}
