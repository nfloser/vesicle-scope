CXX ?= g++
CXXFLAGS ?= -O2 -std=c++11 -fopenmp -Wall -Wextra -Wpedantic

PHYSICELL_DIR ?= .deps/physicell
BIOFVM_DIR := $(PHYSICELL_DIR)/BioFVM
BUILD_DIR := build/native
TARGET := $(BUILD_DIR)/biofvm_diffusion_benchmark
BENCHMARK_SOURCE := native/biofvm_benchmark/benchmark.cpp

BIOFVM_SOURCES := \
	$(BIOFVM_DIR)/BioFVM_vector.cpp \
	$(BIOFVM_DIR)/BioFVM_mesh.cpp \
	$(BIOFVM_DIR)/BioFVM_microenvironment.cpp \
	$(BIOFVM_DIR)/BioFVM_solvers.cpp \
	$(BIOFVM_DIR)/BioFVM_matlab.cpp \
	$(BIOFVM_DIR)/BioFVM_utilities.cpp \
	$(BIOFVM_DIR)/BioFVM_basic_agent.cpp \
	$(BIOFVM_DIR)/BioFVM_MultiCellDS.cpp \
	$(BIOFVM_DIR)/BioFVM_agent_container.cpp \
	$(BIOFVM_DIR)/pugixml.cpp

.PHONY: benchmark run clean

benchmark: $(TARGET)

$(TARGET): $(BENCHMARK_SOURCE) $(BIOFVM_SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -I$(BIOFVM_DIR) $(BENCHMARK_SOURCE) $(BIOFVM_SOURCES) -o $(TARGET)

run: benchmark
	OMP_NUM_THREADS=1 $(TARGET)

clean:
	rm -rf $(BUILD_DIR)
