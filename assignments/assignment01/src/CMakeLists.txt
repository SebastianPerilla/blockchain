# library
add_library(hashingLib
    hash0.cpp
    hash1.cpp
)
target_include_directories(hashingLib
    PUBLIC 
        ${CMAKE_SOURCE_DIR}/include
)

# executable
add_executable(hashingHomework
    ex03.cpp
    # main.cpp
)

target_link_libraries(hashingHomework
    PRIVATE
        hashingLib
)
