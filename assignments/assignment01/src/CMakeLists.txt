# library
add_library(hashing 
    sha256.cpp
)
target_include_directories(hashing 
    PUBLIC 
        ${CMAKE_SOURCE_DIR}/include
)

# executable
add_executable(hashing
    main.cpp
)

target_link_libraries(main 
    PRIVATE
                hashing
)
