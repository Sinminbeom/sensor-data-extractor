# Python 및 pybind11 설정
PYTHON_INCLUDE := $(shell python3 -m pybind11 --includes)
PYTHON_LIBS := $(shell python3-config --ldflags)
EXT_SUFFIX := $(shell python3-config --extension-suffix)

# CUDA 설정
CUDA_PATH := /usr/local/cuda
CUDA_INCLUDE := -I$(CUDA_PATH)/include
CUDA_LIBS := -L$(CUDA_PATH)/lib64 -lcudart

# 컴파일러 및 플래그 설정
NVCC := nvcc
ARCH := -gencode=arch=compute_86,code=\"sm_86,compute_86\" -arch=sm_86
CXXFLAGS := -O2 -shared -std=c++17 -Xcompiler "-fPIC"

# 타겟 및 소스 파일
TARGET := cuda_transform$(EXT_SUFFIX)
SRC := cuda_transform.cu

# 빌드 타겟
all: $(TARGET)

$(TARGET): $(SRC)
	$(NVCC) $(ARCH) $(CXXFLAGS) $(PYTHON_INCLUDE) $(CUDA_INCLUDE) -o $@ $(SRC) $(PYTHON_LIBS) $(CUDA_LIBS)

# Clean up
clean:
	rm -f $(TARGET)

# Run the program
# run: $(TARGET)
# 	python3 -c "import cuda_transform; print('CUDA transform module loaded successfully')"
