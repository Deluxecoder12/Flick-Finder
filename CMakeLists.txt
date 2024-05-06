cmake_minimum_required(VERSION 3.10.0)

project(Flick-Finder VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/build/bin")

add_executable(Flick-Finder src/main.cpp)
