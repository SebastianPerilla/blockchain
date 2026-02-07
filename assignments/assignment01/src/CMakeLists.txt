# library
add_library(hashingLib
    # sha256.cpp
    hash0.cpp
)
target_include_directories(hashingLib
    PUBLIC 
        ${CMAKE_SOURCE_DIR}/include
)

# executable
add_executable(hashingHomework
    main.cpp
)

target_link_libraries(hashingHomework 
    PRIVATE
        hashingLib
)
