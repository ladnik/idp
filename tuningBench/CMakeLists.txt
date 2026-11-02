cmake_minimum_required(VERSION 3.18 FATAL_ERROR)
project(tuningBench CXX)


set(TUNINGBENCH_AUTOPAS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../AutoPas"
        CACHE PATH "Path to AutoPas source tree.")

if (NOT EXISTS "${TUNINGBENCH_AUTOPAS_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "AutoPas not found at ${TUNINGBENCH_AUTOPAS_DIR}. Set -DTUNINGBENCH_AUTOPAS_DIR=<path>.")
endif ()

set(spdlog_ForceBundled ON CACHE BOOL "")
set(AUTOPAS_ENABLE_ENERGY_MEASUREMENTS OFF CACHE BOOL "")

set(AUTOPAS_BUILD_EXAMPLES OFF CACHE BOOL "")
set(AUTOPAS_BUILD_TESTS OFF CACHE BOOL "")
set(AUTOPAS_BUILD_TOOLS OFF CACHE BOOL "")

add_subdirectory("${TUNINGBENCH_AUTOPAS_DIR}" "${CMAKE_CURRENT_BINARY_DIR}/autopas")

file(GLOB_RECURSE tuningBench_SRC "src/*.cpp" "src/*.h")

if (NOT tuningBench_SRC)
    message(STATUS "tuningBench: no sources in src/")
    return()
endif ()

add_executable(tuningBench ${tuningBench_SRC})
target_include_directories(tuningBench PRIVATE src)
target_link_libraries(tuningBench PRIVATE autopas)
target_compile_features(tuningBench PRIVATE cxx_std_20)
