CXX ?= g++
CXXFLAGS ?= -O2 -std=c++11 -fopenmp -Wall -Wextra -Wpedantic -ffunction-sections -fdata-sections
LDFLAGS ?= -Wl,--gc-sections

PHYSICELL_DIR ?= .deps/physicell
BIOFVM_DIR := $(PHYSICELL_DIR)/BioFVM
BUILD_DIR := build/native
TARGET := $(BUILD_DIR)/biofvm_diffusion_benchmark
BENCHMARK_SOURCE := native/biofvm_benchmark/benchmark.cpp

# Keep the verification target limited to the transport implementation it exercises.
# Unused BioFVM I/O, MultiCellDS, agent-container, and XML code are not linked.
BIOFVM_SOURCES := \
	$(BIOFVM_DIR)/BioFVM_vector.cpp \
	$(BIOFVM_DIR)/BioFVM_mesh.cpp \
	$(BIOFVM_DIR)/BioFVM_microenvironment.cpp \
	$(BIOFVM_DIR)/BioFVM_solvers.cpp \
	$(BIOFVM_DIR)/BioFVM_utilities.cpp

.PHONY: benchmark run clean

benchmark: $(TARGET)

$(TARGET): $(BENCHMARK_SOURCE) $(BIOFVM_SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -I$(BIOFVM_DIR) $(BENCHMARK_SOURCE) $(BIOFVM_SOURCES) $(LDFLAGS) -o $(TARGET)

run: benchmark
	OMP_NUM_THREADS=1 $(TARGET)

clean:
	rm -rf $(BUILD_DIR)
