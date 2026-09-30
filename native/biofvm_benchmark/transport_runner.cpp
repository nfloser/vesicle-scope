#include "BioFVM.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

#ifndef VESICLESCOPE_PHYSICELL_RELEASE
#error "VESICLESCOPE_PHYSICELL_RELEASE must be supplied by the build"
#endif

#ifndef VESICLESCOPE_PHYSICELL_COMMIT
#error "VESICLESCOPE_PHYSICELL_COMMIT must be supplied by the build"
#endif

#ifndef VESICLESCOPE_BIOFVM_VERSION
#error "VESICLESCOPE_BIOFVM_VERSION must be supplied by the build"
#endif

namespace
{
class ScopedCoutToStderr
{
public:
    ScopedCoutToStderr()
        : previous_(std::cout.rdbuf(std::cerr.rdbuf()))
    {
    }

    ~ScopedCoutToStderr()
    {
        std::cout.rdbuf(previous_);
    }

    ScopedCoutToStderr(const ScopedCoutToStderr&) = delete;
    ScopedCoutToStderr& operator=(const ScopedCoutToStderr&) = delete;

private:
    std::streambuf* previous_;
};

double parse_number(const std::string& text, const std::string& name)
{
    std::size_t consumed = 0;
    double value = 0.0;
    try
    {
        value = std::stod(text, &consumed);
    }
    catch (const std::exception&)
    {
        throw std::invalid_argument(name + " must be numeric");
    }

    if (consumed != text.size() || !std::isfinite(value))
    {
        throw std::invalid_argument(name + " must be a finite number");
    }
    return value;
}

bool has_argument(int argc, char* argv[], const std::string& name)
{
    if ((argc - 1) % 2 != 0)
    {
        throw std::invalid_argument("arguments must be supplied as --name value pairs");
    }

    for (int index = 1; index < argc; index += 2)
    {
        if (name == argv[index])
        {
            return true;
        }
    }
    return false;
}

std::string argument(int argc, char* argv[], const std::string& name)
{
    if ((argc - 1) % 2 != 0)
    {
        throw std::invalid_argument("arguments must be supplied as --name value pairs");
    }

    for (int index = 1; index < argc; index += 2)
    {
        if (name == argv[index])
        {
            return argv[index + 1];
        }
    }
    throw std::invalid_argument("missing required argument " + name);
}

bool integer_multiple(double total, double step)
{
    const double ratio = total / step;
    return std::abs(ratio - std::round(ratio)) <= 1e-9;
}

void require_positive(double value, const std::string& name)
{
    if (value <= 0.0)
    {
        throw std::invalid_argument(name + " must be greater than zero");
    }
}

void require_non_negative(double value, const std::string& name)
{
    if (value < 0.0)
    {
        throw std::invalid_argument(name + " must be non-negative");
    }
}

void print_sample(
    BioFVM::Microenvironment& microenvironment,
    double time_min,
    BioFVM::Basic_Agent* uptake_agent
)
{
    double sum = 0.0;
    double minimum = std::numeric_limits<double>::infinity();
    double maximum = -std::numeric_limits<double>::infinity();

    for (unsigned int index = 0; index < microenvironment.number_of_voxels(); ++index)
    {
        const double value =
            microenvironment.density_vector(static_cast<int>(index))[0];
        sum += value;
        minimum = std::min(minimum, value);
        maximum = std::max(maximum, value);
    }

    const double mean =
        sum / static_cast<double>(microenvironment.number_of_voxels());
    const double internalized =
        uptake_agent == nullptr
            ? 0.0
            : (*(uptake_agent->internalized_substrates))[0];

    std::cout
        << "sample\t"
        << std::setprecision(17) << time_min << '\t'
        << mean << '\t'
        << minimum << '\t'
        << maximum << '\t'
        << internalized << '\n';
}
}

int main(int argc, char* argv[])
{
    try
    {
        const double width =
            parse_number(argument(argc, argv, "--width-micron"), "width");
        const double height =
            parse_number(argument(argc, argv, "--height-micron"), "height");
        const double slice_thickness = parse_number(
            argument(argc, argv, "--slice-thickness-micron"),
            "slice thickness"
        );
        const double duration =
            parse_number(argument(argc, argv, "--duration-min"), "duration");
        const double sample_every =
            parse_number(argument(argc, argv, "--sample-every-min"), "sample interval");
        const std::string boundary = argument(argc, argv, "--boundary");
        const double diffusion = parse_number(
            argument(argc, argv, "--diffusion-micron2-per-min"),
            "diffusion coefficient"
        );
        const double decay =
            parse_number(argument(argc, argv, "--decay-per-min"), "decay rate");
        const double initial = parse_number(
            argument(argc, argv, "--initial-concentration"),
            "initial concentration"
        );
        const std::string concentration_unit =
            argument(argc, argv, "--concentration-unit");
        const double grid =
            parse_number(argument(argc, argv, "--grid-spacing-micron"), "grid spacing");
        const double dt =
            parse_number(argument(argc, argv, "--time-step-min"), "time step");

        const bool has_source_x = has_argument(argc, argv, "--source-x-micron");
        const bool has_source_y = has_argument(argc, argv, "--source-y-micron");
        const bool has_source_rate = has_argument(
            argc,
            argv,
            "--source-rate-particle-equivalent-per-min"
        );
        const bool has_source = has_source_x || has_source_y || has_source_rate;
        if (has_source && !(has_source_x && has_source_y && has_source_rate))
        {
            throw std::invalid_argument(
                "localized source requires x, y and release-rate arguments"
            );
        }

        double source_x = 0.0;
        double source_y = 0.0;
        double source_rate = 0.0;
        if (has_source)
        {
            source_x = parse_number(
                argument(argc, argv, "--source-x-micron"),
                "source x"
            );
            source_y = parse_number(
                argument(argc, argv, "--source-y-micron"),
                "source y"
            );
            source_rate = parse_number(
                argument(
                    argc,
                    argv,
                    "--source-rate-particle-equivalent-per-min"
                ),
                "source release rate"
            );
        }

        const bool has_uptake_x = has_argument(argc, argv, "--uptake-x-micron");
        const bool has_uptake_y = has_argument(argc, argv, "--uptake-y-micron");
        const bool has_uptake_volume =
            has_argument(argc, argv, "--uptake-volume-micron3");
        const bool has_uptake_rate =
            has_argument(argc, argv, "--uptake-rate-per-min");
        const bool has_uptake =
            has_uptake_x || has_uptake_y || has_uptake_volume || has_uptake_rate;
        if (
            has_uptake
            && !(has_uptake_x && has_uptake_y && has_uptake_volume && has_uptake_rate)
        )
        {
            throw std::invalid_argument(
                "localized uptake requires x, y, effective volume and uptake-rate arguments"
            );
        }
        double uptake_x = 0.0;
        double uptake_y = 0.0;
        double uptake_volume = 0.0;
        double uptake_rate = 0.0;
        if (has_uptake)
        {
            uptake_x = parse_number(
                argument(argc, argv, "--uptake-x-micron"),
                "uptake x"
            );
            uptake_y = parse_number(
                argument(argc, argv, "--uptake-y-micron"),
                "uptake y"
            );
            uptake_volume = parse_number(
                argument(argc, argv, "--uptake-volume-micron3"),
                "uptake effective volume"
            );
            uptake_rate = parse_number(
                argument(argc, argv, "--uptake-rate-per-min"),
                "uptake rate"
            );
        }

        require_positive(width, "width");
        require_positive(height, "height");
        require_positive(slice_thickness, "slice thickness");
        require_positive(duration, "duration");
        require_positive(sample_every, "sample interval");
        require_positive(grid, "grid spacing");
        require_positive(dt, "time step");
        require_non_negative(diffusion, "diffusion coefficient");
        require_non_negative(decay, "decay rate");
        require_non_negative(initial, "initial concentration");
        if (has_source)
        {
            require_non_negative(source_x, "source x");
            require_non_negative(source_y, "source y");
            require_non_negative(source_rate, "source release rate");
            if (source_x >= width || source_y >= height)
            {
                throw std::invalid_argument("localized source lies outside 2D domain");
            }
            if (concentration_unit != "particle_equivalent/micron^3")
            {
                throw std::invalid_argument(
                    "localized source requires particle_equivalent/micron^3 concentration"
                );
            }
        }
        if (has_uptake)
        {
            require_non_negative(uptake_x, "uptake x");
            require_non_negative(uptake_y, "uptake y");
            require_positive(uptake_volume, "uptake effective volume");
            require_non_negative(uptake_rate, "uptake rate");
            if (uptake_x >= width || uptake_y >= height)
            {
                throw std::invalid_argument("localized uptake lies outside 2D domain");
            }
        }

        if (boundary != "no_flux")
        {
            throw std::invalid_argument("only no_flux boundary is supported");
        }
        if (concentration_unit.find_first_not_of(" \t\r\n") == std::string::npos)
        {
            throw std::invalid_argument("concentration unit must not be blank");
        }
        if (sample_every > duration)
        {
            throw std::invalid_argument("sample interval cannot exceed duration");
        }
        if (!integer_multiple(width, grid) || !integer_multiple(height, grid))
        {
            throw std::invalid_argument("grid spacing must tile the 2D domain exactly");
        }
        if (!integer_multiple(duration, dt) || !integer_multiple(sample_every, dt))
        {
            throw std::invalid_argument(
                "time step must tile duration and sample interval exactly"
            );
        }

        BioFVM::Microenvironment microenvironment;
        microenvironment.name = "VesicleScope transport runner";
        microenvironment.set_density(0, "transport_field", concentration_unit);
        microenvironment.resize_space(
            0.0,
            width,
            0.0,
            height,
            -0.5 * slice_thickness,
            0.5 * slice_thickness,
            grid,
            grid,
            slice_thickness
        );

        microenvironment.spatial_units = "micron";
        microenvironment.time_units = "min";
        microenvironment.mesh.units = "micron";
        microenvironment.diffusion_coefficients[0] = diffusion;
        microenvironment.decay_rates[0] = decay;
        microenvironment.diffusion_decay_solver =
            BioFVM::diffusion_decay_solver__constant_coefficients_LOD_2D;

        for (unsigned int index = 0; index < microenvironment.number_of_voxels(); ++index)
        {
            microenvironment.density_vector(static_cast<int>(index))[0] = initial;
        }

        BioFVM::Agent_Container agent_container;
        BioFVM::Basic_Agent* source_agent = nullptr;
        BioFVM::Basic_Agent* uptake_agent = nullptr;
        if (has_source || has_uptake)
        {
            agent_container.initialize(
                static_cast<int>(microenvironment.number_of_voxels())
            );
            microenvironment.agent_container = &agent_container;
            BioFVM::set_default_microenvironment(&microenvironment);
        }

        BioFVM::default_microenvironment_options
            .track_internalized_substrates_in_each_agent = has_uptake;

        if (has_source)
        {
            source_agent = BioFVM::create_basic_agent();
            source_agent->set_total_volume(1.0);
            if (!source_agent->assign_position(source_x, source_y, 0.0))
            {
                throw std::invalid_argument(
                    "localized source position is invalid in BioFVM mesh"
                );
            }
            (*source_agent->net_export_rates)[0] = source_rate;
            source_agent->set_internal_uptake_constants(dt);
        }

        if (has_uptake)
        {
            uptake_agent = BioFVM::create_basic_agent();
            uptake_agent->set_total_volume(uptake_volume);
            if (!uptake_agent->assign_position(uptake_x, uptake_y, 0.0))
            {
                throw std::invalid_argument(
                    "localized uptake position is invalid in BioFVM mesh"
                );
            }
            (*uptake_agent->uptake_rates)[0] = uptake_rate;
            uptake_agent->set_internal_uptake_constants(dt);
        }

        const long total_steps = std::lround(duration / dt);
        const long sample_steps = std::lround(sample_every / dt);

        std::cout
            << "VESICLESCOPE_BIOFVM_RESULT\t2\n"
            << "engine\tBioFVM\n"
            << "physicell_release\t" << VESICLESCOPE_PHYSICELL_RELEASE << '\n'
            << "physicell_commit\t" << VESICLESCOPE_PHYSICELL_COMMIT << '\n'
            << "biofvm_version\t" << VESICLESCOPE_BIOFVM_VERSION << '\n';

        print_sample(microenvironment, 0.0, uptake_agent);

        for (long step = 1; step <= total_steps; ++step)
        {
            if (source_agent != nullptr)
            {
                source_agent->simulate_secretion_and_uptake(&microenvironment, dt);
            }
            if (uptake_agent != nullptr)
            {
                uptake_agent->simulate_secretion_and_uptake(&microenvironment, dt);
            }
            {
                ScopedCoutToStderr redirect_solver_output;
                microenvironment.simulate_diffusion_decay(dt);
            }
            if (step % sample_steps == 0 || step == total_steps)
            {
                print_sample(
                    microenvironment,
                    static_cast<double>(step) * dt,
                    uptake_agent
                );
            }
        }
    }
    catch (const std::exception& exc)
    {
        std::cerr << "BioFVM transport runner: " << exc.what() << '\n';
        return 2;
    }

    return 0;
}
