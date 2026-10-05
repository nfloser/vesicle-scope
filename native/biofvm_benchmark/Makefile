CXX ?= g++
CXXFLAGS ?= -O2 -std=c++11 -fopenmp -Wall -Wextra -Wpedantic -ffunction-sections -fdata-sections
LDFLAGS ?= -Wl,--gc-sections

PIN_FILE := vesiclescope/engines/physicell.env
include $(PIN_FILE)

PHYSICELL_DIR ?= .deps/physicell
BIOFVM_DIR := $(PHYSICELL_DIR)/BioFVM
BUILD_DIR := build/native
BENCHMARK_TARGET := $(BUILD_DIR)/biofvm_diffusion_benchmark
RUNNER_TARGET := $(BUILD_DIR)/biofvm_transport_runner
BENCHMARK_SOURCE := native/biofvm_benchmark/benchmark.cpp
RUNNER_SOURCE := vesiclescope/engines/native/transport_runner.cpp

PIN_DEFINES := \
	-DVESICLESCOPE_PHYSICELL_RELEASE=\"$(PHYSICELL_RELEASE)\" \
	-DVESICLESCOPE_PHYSICELL_COMMIT=\"$(PHYSICELL_COMMIT)\" \
	-DVESICLESCOPE_BIOFVM_VERSION=\"$(BIOFVM_VERSION)\"

# Keep the verification targets limited to the BioFVM components they exercise.
BIOFVM_CORE_SOURCES := \
	$(BIOFVM_DIR)/BioFVM_vector.cpp \
	$(BIOFVM_DIR)/BioFVM_mesh.cpp \
	$(BIOFVM_DIR)/BioFVM_microenvironment.cpp \
	$(BIOFVM_DIR)/BioFVM_solvers.cpp \
	$(BIOFVM_DIR)/BioFVM_utilities.cpp

BIOFVM_AGENT_SOURCES := \
	$(BIOFVM_DIR)/BioFVM_basic_agent.cpp \
	$(BIOFVM_DIR)/BioFVM_agent_container.cpp

.PHONY: benchmark runner run clean

benchmark: $(BENCHMARK_TARGET)

runner: $(RUNNER_TARGET)

$(BENCHMARK_TARGET): $(BENCHMARK_SOURCE) $(BIOFVM_CORE_SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -I$(BIOFVM_DIR) $(BENCHMARK_SOURCE) $(BIOFVM_CORE_SOURCES) $(LDFLAGS) -o $(BENCHMARK_TARGET)

$(RUNNER_TARGET): $(RUNNER_SOURCE) $(BIOFVM_CORE_SOURCES) $(BIOFVM_AGENT_SOURCES) $(PIN_FILE)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) $(PIN_DEFINES) -I$(BIOFVM_DIR) $(RUNNER_SOURCE) $(BIOFVM_CORE_SOURCES) $(BIOFVM_AGENT_SOURCES) $(LDFLAGS) -o $(RUNNER_TARGET)

run: benchmark
	OMP_NUM_THREADS=1 $(BENCHMARK_TARGET)

clean:
	rm -rf $(BUILD_DIR)
