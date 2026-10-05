#include "BioFVM.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

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

int parse_non_negative_integer(const std::string& text, const std::string& name)
{
    std::size_t consumed = 0;
    int value = 0;
    try
    {
        value = std::stoi(text, &consumed);
    }
    catch (const std::exception&)
    {
        throw std::invalid_argument(name + " must be an integer");
    }

    if (consumed != text.size() || value < 0)
    {
        throw std::invalid_argument(name + " must be a non-negative integer");
    }
    return value;
}

struct SourceComponentConfig
{
    double x;
    double y;
    double rate;
};

struct SourceConfig
{
    std::string kind;
    double x;
    double y;
    double radius;
    double rate;
    std::vector<SourceComponentConfig> components;
};

struct UptakeComponentConfig
{
    double x;
    double y;
    double volume;
};

struct UptakeConfig
{
    std::string kind;
    double x;
    double y;
    double radius;
    double volume;
    double rate;
    std::vector<UptakeComponentConfig> components;
};

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
    const std::vector<std::vector<BioFVM::Basic_Agent*>>& uptake_recipients
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

    double total_internalized = 0.0;
    for (const auto& recipient_agents : uptake_recipients)
    {
        for (BioFVM::Basic_Agent* uptake_agent : recipient_agents)
        {
            total_internalized += (*(uptake_agent->internalized_substrates))[0];
        }
    }

    std::cout
        << "sample\t"
        << std::setprecision(17) << time_min << '\t'
        << mean << '\t'
        << minimum << '\t'
        << maximum << '\t'
        << total_internalized << '\n';

    std::cout << "field\t" << std::setprecision(17) << time_min;
    for (unsigned int index = 0; index < microenvironment.number_of_voxels(); ++index)
    {
        std::cout
            << '\t'
            << microenvironment.density_vector(static_cast<int>(index))[0];
    }
    std::cout << '\n';

    for (std::size_t index = 0; index < uptake_recipients.size(); ++index)
    {
        double recipient_internalized = 0.0;
        for (BioFVM::Basic_Agent* uptake_agent : uptake_recipients[index])
        {
            recipient_internalized += (*(uptake_agent->internalized_substrates))[0];
        }
        std::cout
            << "recipient_uptake\t"
            << std::setprecision(17) << time_min << '\t'
            << index << '\t'
            << recipient_internalized
            << '\n';
    }

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

        const bool has_source = has_argument(argc, argv, "--source-kind");
        SourceConfig source_config;
        if (has_source)
        {
            source_config.kind = argument(argc, argv, "--source-kind");
            source_config.x = parse_number(
                argument(argc, argv, "--source-x-micron"),
                "source x"
            );
            source_config.y = parse_number(
                argument(argc, argv, "--source-y-micron"),
                "source y"
            );
            source_config.radius = parse_number(
                argument(argc, argv, "--source-radius-micron"),
                "source footprint radius"
            );
            source_config.rate = parse_number(
                argument(
                    argc,
                    argv,
                    "--source-rate-particle-equivalent-per-min"
                ),
                "source release rate"
            );

            const int source_component_count = parse_non_negative_integer(
                argument(argc, argv, "--source-component-count"),
                "source component count"
            );
            if (source_component_count <= 0)
            {
                throw std::invalid_argument(
                    "source component count must be greater than zero"
                );
            }
            source_config.components.reserve(
                static_cast<std::size_t>(source_component_count)
            );
            for (int component_index = 0;
                 component_index < source_component_count;
                 ++component_index)
            {
                const std::string component_prefix =
                    "--source-component-" + std::to_string(component_index);
                SourceComponentConfig component;
                component.x = parse_number(
                    argument(argc, argv, component_prefix + "-x-micron"),
                    "source component x"
                );
                component.y = parse_number(
                    argument(argc, argv, component_prefix + "-y-micron"),
                    "source component y"
                );
                component.rate = parse_number(
                    argument(
                        argc,
                        argv,
                        component_prefix + "-rate-particle-equivalent-per-min"
                    ),
                    "source component release rate"
                );
                source_config.components.push_back(component);
            }
        }

        const int uptake_count = parse_non_negative_integer(
            argument(argc, argv, "--uptake-count"),
            "uptake count"
        );
        std::vector<UptakeConfig> uptake_configs;
        uptake_configs.reserve(static_cast<std::size_t>(uptake_count));

        for (int index = 0; index < uptake_count; ++index)
        {
            const std::string prefix = "--uptake-" + std::to_string(index);
            UptakeConfig config;
            config.kind = argument(argc, argv, prefix + "-kind");
            config.x = parse_number(
                argument(argc, argv, prefix + "-x-micron"),
                "uptake x"
            );
            config.y = parse_number(
                argument(argc, argv, prefix + "-y-micron"),
                "uptake y"
            );
            config.radius = parse_number(
                argument(argc, argv, prefix + "-radius-micron"),
                "uptake footprint radius"
            );
            config.volume = parse_number(
                argument(argc, argv, prefix + "-volume-micron3"),
                "uptake effective volume"
            );
            config.rate = parse_number(
                argument(argc, argv, prefix + "-rate-per-min"),
                "uptake rate"
            );
            const int component_count = parse_non_negative_integer(
                argument(argc, argv, prefix + "-component-count"),
                "uptake component count"
            );
            if (component_count <= 0)
            {
                throw std::invalid_argument(
                    "uptake component count must be greater than zero"
                );
            }
            config.components.reserve(static_cast<std::size_t>(component_count));
            for (int component_index = 0;
                 component_index < component_count;
                 ++component_index)
            {
                const std::string component_prefix =
                    prefix + "-component-" + std::to_string(component_index);
                UptakeComponentConfig component;
                component.x = parse_number(
                    argument(argc, argv, component_prefix + "-x-micron"),
                    "uptake component x"
                );
                component.y = parse_number(
                    argument(argc, argv, component_prefix + "-y-micron"),
                    "uptake component y"
                );
                component.volume = parse_number(
                    argument(argc, argv, component_prefix + "-volume-micron3"),
                    "uptake component volume"
                );
                config.components.push_back(component);
            }
            uptake_configs.push_back(config);
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
            if (
                source_config.kind != "point"
                && source_config.kind != "circle"
            )
            {
                throw std::invalid_argument("unsupported source geometry kind");
            }
            require_non_negative(source_config.x, "source x");
            require_non_negative(source_config.y, "source y");
            require_non_negative(source_config.radius, "source footprint radius");
            require_non_negative(source_config.rate, "source release rate");
            if (source_config.x >= width || source_config.y >= height)
            {
                throw std::invalid_argument("localized source lies outside 2D domain");
            }
            if (source_config.kind == "point")
            {
                if (
                    source_config.radius != 0.0
                    || source_config.components.size() != 1
                )
                {
                    throw std::invalid_argument(
                        "point release source requires zero radius and one component"
                    );
                }
            }
            else
            {
                require_positive(
                    source_config.radius,
                    "circular source footprint radius"
                );
                if (
                    source_config.x - source_config.radius < 0.0
                    || source_config.x + source_config.radius > width
                    || source_config.y - source_config.radius < 0.0
                    || source_config.y + source_config.radius > height
                )
                {
                    throw std::invalid_argument(
                        "circular source footprint must lie fully inside domain"
                    );
                }
            }

            double component_rate_sum = 0.0;
            for (const SourceComponentConfig& component : source_config.components)
            {
                require_non_negative(component.x, "source component x");
                require_non_negative(component.y, "source component y");
                require_non_negative(component.rate, "source component release rate");
                if (component.x >= width || component.y >= height)
                {
                    throw std::invalid_argument(
                        "source component lies outside 2D domain"
                    );
                }
                component_rate_sum += component.rate;
            }
            const double release_tolerance =
                std::max(1e-12, std::abs(source_config.rate) * 1e-12);
            if (
                std::abs(component_rate_sum - source_config.rate)
                > release_tolerance
            )
            {
                throw std::invalid_argument(
                    "source component release rates must sum to declared source rate"
                );
            }

            if (concentration_unit != "particle_equivalent/micron^3")
            {
                throw std::invalid_argument(
                    "localized source requires particle_equivalent/micron^3 concentration"
                );
            }
        }
        if (!integer_multiple(width, grid) || !integer_multiple(height, grid))
        {
            throw std::invalid_argument("grid spacing must tile the 2D domain exactly");
        }

        if (has_source)
        {
            if (source_config.kind == "point")
            {
                const SourceComponentConfig& component =
                    source_config.components.front();
                if (
                    std::abs(component.x - source_config.x) > 1e-12
                    || std::abs(component.y - source_config.y) > 1e-12
                )
                {
                    throw std::invalid_argument(
                        "point source component must match declared source position"
                    );
                }
            }
            else
            {
                const int nx = static_cast<int>(std::lround(width / grid));
                const int ny = static_cast<int>(std::lround(height / grid));
                const double radius_tolerance =
                    std::max(1e-12, source_config.radius * 1e-12);
                std::set<int> expected_source_voxels;

                for (int y_index = 0; y_index < ny; ++y_index)
                {
                    const double y =
                        (static_cast<double>(y_index) + 0.5) * grid;
                    for (int x_index = 0; x_index < nx; ++x_index)
                    {
                        const double x =
                            (static_cast<double>(x_index) + 0.5) * grid;
                        if (
                            std::hypot(
                                x - source_config.x,
                                y - source_config.y
                            )
                            <= source_config.radius + radius_tolerance
                        )
                        {
                            expected_source_voxels.insert(
                                y_index * nx + x_index
                            );
                        }
                    }
                }

                if (
                    source_config.components.size()
                    != expected_source_voxels.size()
                )
                {
                    throw std::invalid_argument(
                        "circular source component count does not match footprint"
                    );
                }

                std::set<int> declared_source_voxels;
                for (const SourceComponentConfig& component :
                     source_config.components)
                {
                    const int x_index =
                        static_cast<int>(std::floor(component.x / grid));
                    const int y_index =
                        static_cast<int>(std::floor(component.y / grid));
                    const double voxel_center_x =
                        (static_cast<double>(x_index) + 0.5) * grid;
                    const double voxel_center_y =
                        (static_cast<double>(y_index) + 0.5) * grid;

                    if (
                        std::abs(component.x - voxel_center_x) > 1e-12
                        || std::abs(component.y - voxel_center_y) > 1e-12
                    )
                    {
                        throw std::invalid_argument(
                            "circular source components must lie on voxel centers"
                        );
                    }

                    const int voxel_key = y_index * nx + x_index;
                    if (
                        expected_source_voxels.find(voxel_key)
                        == expected_source_voxels.end()
                    )
                    {
                        throw std::invalid_argument(
                            "circular source component does not match declared footprint rasterization"
                        );
                    }
                    if (!declared_source_voxels.insert(voxel_key).second)
                    {
                        throw std::invalid_argument(
                            "circular source contains a duplicate rasterized voxel"
                        );
                    }
                }

                if (declared_source_voxels != expected_source_voxels)
                {
                    throw std::invalid_argument(
                        "circular source components do not match declared footprint rasterization"
                    );
                }
            }
        }

        for (const UptakeConfig& uptake : uptake_configs)
        {
            if (uptake.kind != "point" && uptake.kind != "circle")
            {
                throw std::invalid_argument("unsupported uptake geometry kind");
            }
            require_non_negative(uptake.x, "uptake x");
            require_non_negative(uptake.y, "uptake y");
            require_non_negative(uptake.radius, "uptake footprint radius");
            require_positive(uptake.volume, "uptake effective volume");
            require_non_negative(uptake.rate, "uptake rate");
            if (uptake.x >= width || uptake.y >= height)
            {
                throw std::invalid_argument("localized uptake lies outside 2D domain");
            }

            if (uptake.kind == "point")
            {
                if (uptake.radius != 0.0 || uptake.components.size() != 1)
                {
                    throw std::invalid_argument(
                        "point uptake requires zero radius and one component"
                    );
                }
            }
            else
            {
                require_positive(uptake.radius, "circular uptake footprint radius");
                if (
                    uptake.x - uptake.radius < 0.0
                    || uptake.x + uptake.radius > width
                    || uptake.y - uptake.radius < 0.0
                    || uptake.y + uptake.radius > height
                )
                {
                    throw std::invalid_argument(
                        "circular uptake footprint must lie fully inside domain"
                    );
                }

                const int nx = static_cast<int>(std::lround(width / grid));
                const int ny = static_cast<int>(std::lround(height / grid));
                std::size_t expected_component_count = 0;
                const double radius_tolerance =
                    std::max(1e-12, uptake.radius * 1e-12);
                for (int y_index = 0; y_index < ny; ++y_index)
                {
                    const double y = (static_cast<double>(y_index) + 0.5) * grid;
                    for (int x_index = 0; x_index < nx; ++x_index)
                    {
                        const double x =
                            (static_cast<double>(x_index) + 0.5) * grid;
                        if (
                            std::hypot(x - uptake.x, y - uptake.y)
                            <= uptake.radius + radius_tolerance
                        )
                        {
                            ++expected_component_count;
                        }
                    }
                }
                if (uptake.components.size() != expected_component_count)
                {
                    throw std::invalid_argument(
                        "circular uptake component count does not match footprint"
                    );
                }
            }

            const double expected_component_volume =
                uptake.volume / static_cast<double>(uptake.components.size());
            double component_volume_sum = 0.0;
            for (const UptakeComponentConfig& component : uptake.components)
            {
                require_non_negative(component.x, "uptake component x");
                require_non_negative(component.y, "uptake component y");
                require_positive(component.volume, "uptake component volume");
                if (component.x >= width || component.y >= height)
                {
                    throw std::invalid_argument(
                        "uptake component lies outside 2D domain"
                    );
                }

                if (uptake.kind == "point")
                {
                    if (
                        std::abs(component.x - uptake.x) > 1e-12
                        || std::abs(component.y - uptake.y) > 1e-12
                    )
                    {
                        throw std::invalid_argument(
                            "point uptake component must match recipient position"
                        );
                    }
                }
                else
                {
                    const double distance = std::hypot(
                        component.x - uptake.x,
                        component.y - uptake.y
                    );
                    if (distance > uptake.radius + std::max(1e-12, uptake.radius * 1e-12))
                    {
                        throw std::invalid_argument(
                            "circular uptake component lies outside footprint"
                        );
                    }
                    const double voxel_center_x =
                        (std::floor(component.x / grid) + 0.5) * grid;
                    const double voxel_center_y =
                        (std::floor(component.y / grid) + 0.5) * grid;
                    if (
                        std::abs(component.x - voxel_center_x) > 1e-12
                        || std::abs(component.y - voxel_center_y) > 1e-12
                    )
                    {
                        throw std::invalid_argument(
                            "circular uptake components must lie on voxel centers"
                        );
                    }
                }
                const double component_volume_tolerance =
                    std::max(1e-12, uptake.volume * 1e-12);
                if (
                    std::abs(component.volume - expected_component_volume)
                    > component_volume_tolerance
                )
                {
                    throw std::invalid_argument(
                        "uptake component volume must match equal recipient share"
                    );
                }
                component_volume_sum += component.volume;
            }

            if (
                std::abs(component_volume_sum - uptake.volume)
                > std::max(1e-9, uptake.volume * 1e-12)
            )
            {
                throw std::invalid_argument(
                    "uptake component volumes must sum to recipient effective volume"
                );
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
        std::vector<BioFVM::Basic_Agent*> source_agents;
        std::vector<std::vector<BioFVM::Basic_Agent*>> uptake_recipients;
        if (has_source || !uptake_configs.empty())
        {
            agent_container.initialize(
                static_cast<int>(microenvironment.number_of_voxels())
            );
            microenvironment.agent_container = &agent_container;
            BioFVM::set_default_microenvironment(&microenvironment);
        }

        BioFVM::default_microenvironment_options
            .track_internalized_substrates_in_each_agent = !uptake_configs.empty();

        if (has_source)
        {
            std::set<int> source_voxel_indices;
            source_agents.reserve(source_config.components.size());
            for (const SourceComponentConfig& component : source_config.components)
            {
                BioFVM::Basic_Agent* source_agent =
                    BioFVM::create_basic_agent();
                source_agent->set_total_volume(1.0);
                if (!source_agent->assign_position(component.x, component.y, 0.0))
                {
                    throw std::invalid_argument(
                        "source component position is invalid in BioFVM mesh"
                    );
                }
                if (!source_voxel_indices.insert(
                    source_agent->get_current_voxel_index()
                ).second)
                {
                    throw std::invalid_argument(
                        "one source maps multiple components to one BioFVM voxel"
                    );
                }
                (*source_agent->net_export_rates)[0] = component.rate;
                source_agent->set_internal_uptake_constants(dt);
                source_agents.push_back(source_agent);
            }
        }

        std::map<int, std::size_t> uptake_voxel_owner;
        uptake_recipients.reserve(uptake_configs.size());
        for (std::size_t recipient_index = 0;
             recipient_index < uptake_configs.size();
             ++recipient_index)
        {
            const UptakeConfig& uptake = uptake_configs[recipient_index];
            std::set<int> recipient_voxel_indices;
            std::vector<BioFVM::Basic_Agent*> recipient_agents;
            recipient_agents.reserve(uptake.components.size());

            for (const UptakeComponentConfig& component : uptake.components)
            {
                BioFVM::Basic_Agent* uptake_agent = BioFVM::create_basic_agent();
                uptake_agent->set_total_volume(component.volume);
                if (!uptake_agent->assign_position(component.x, component.y, 0.0))
                {
                    throw std::invalid_argument(
                        "uptake component position is invalid in BioFVM mesh"
                    );
                }

                const int voxel_index = uptake_agent->get_current_voxel_index();
                if (!recipient_voxel_indices.insert(voxel_index).second)
                {
                    throw std::invalid_argument(
                        "one recipient maps multiple uptake components to one BioFVM voxel"
                    );
                }
                const auto existing = uptake_voxel_owner.find(voxel_index);
                if (
                    existing != uptake_voxel_owner.end()
                    && existing->second != recipient_index
                )
                {
                    throw std::invalid_argument(
                        "multiple uptake recipients map to the same BioFVM voxel"
                    );
                }
                uptake_voxel_owner[voxel_index] = recipient_index;

                (*uptake_agent->uptake_rates)[0] = uptake.rate;
                uptake_agent->set_internal_uptake_constants(dt);
                recipient_agents.push_back(uptake_agent);
            }

            uptake_recipients.push_back(recipient_agents);
        }

        const long total_steps = std::lround(duration / dt);
        const long sample_steps = std::lround(sample_every / dt);

        std::cout
            << "VESICLESCOPE_BIOFVM_RESULT\t5\n"
            << "engine\tBioFVM\n"
            << "physicell_release\t" << VESICLESCOPE_PHYSICELL_RELEASE << '\n'
            << "physicell_commit\t" << VESICLESCOPE_PHYSICELL_COMMIT << '\n'
            << "biofvm_version\t" << VESICLESCOPE_BIOFVM_VERSION << '\n'
            << "grid\t"
            << microenvironment.mesh.x_coordinates.size() << '\t'
            << microenvironment.mesh.y_coordinates.size() << '\t'
            << std::setprecision(17) << microenvironment.mesh.dx << '\t'
            << microenvironment.mesh.dz << '\t'
            << "x_fastest_then_y\n";

        for (std::size_t index = 0; index < uptake_configs.size(); ++index)
        {
            const UptakeConfig& uptake = uptake_configs[index];
            std::cout
                << "recipient\t" << index << '\t'
                << uptake.kind << '\t'
                << std::setprecision(17) << uptake.x << '\t'
                << uptake.y << '\t'
                << uptake.radius << '\t'
                << uptake.volume << '\t'
                << uptake.rate << '\t'
                << uptake.components.size() << '\n';
        }

        print_sample(microenvironment, 0.0, uptake_recipients);

        for (long step = 1; step <= total_steps; ++step)
        {
            if (!source_agents.empty())
            {
                const bool track_internalized =
                    BioFVM::default_microenvironment_options
                        .track_internalized_substrates_in_each_agent;
                BioFVM::default_microenvironment_options
                    .track_internalized_substrates_in_each_agent = false;
                for (BioFVM::Basic_Agent* source_agent : source_agents)
                {
                    source_agent->simulate_secretion_and_uptake(
                        &microenvironment,
                        dt
                    );
                }
                BioFVM::default_microenvironment_options
                    .track_internalized_substrates_in_each_agent = track_internalized;
            }
            for (const auto& recipient_agents : uptake_recipients)
            {
                for (BioFVM::Basic_Agent* uptake_agent : recipient_agents)
                {
                    uptake_agent->simulate_secretion_and_uptake(&microenvironment, dt);
                }
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
                    uptake_recipients
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
