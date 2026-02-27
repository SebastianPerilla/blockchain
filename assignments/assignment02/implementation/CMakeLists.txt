find_package(OpenSSL REQUIRED)

# library
add_library(
  hashLib ../cppfunctions/hash0.cpp ../cppfunctions/hash1.cpp
          ../cppfunctions/sha256.cpp ../cppfunctions/randomGen.cpp ex01.cpp)

target_include_directories(hashLib PUBLIC ${CMAKE_SOURCE_DIR}/include)

target_link_libraries(hashLib PRIVATE OpenSSL::Crypto)

# executable
add_executable(hashingHomework ex01.cpp # main.cpp
)

target_link_libraries(hashingHomework PRIVATE hashLib)
