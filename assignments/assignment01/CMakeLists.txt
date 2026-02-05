cmake_minimum_required(VERSION 3.20)
project(ASSIGNMENT1BLOCKCHAIN) 

set(CMAKE_CXX_STANDARD 23)

set(CMAKE_CXX_STANDARD_REQUIRED TRUE)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

include_directories(${CMAKE_SOURCE_DIR}/include)

enable_testing()

add_subdirectory(src)
# add_subdirectory(include)
# add_subdirectory(tests)
