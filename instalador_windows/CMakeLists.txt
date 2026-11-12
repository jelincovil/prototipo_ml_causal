cmake_minimum_required(VERSION 3.20)
project(PuenteCausal VERSION 1.0.2 LANGUAGES CXX RC)

if(NOT WIN32)
  message(FATAL_ERROR "PuenteCausal solo se compila para Windows.")
endif()

set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

add_executable(PuenteCausal WIN32
  PuenteCausal.cpp
  PuenteCausal.rc
)

# El manifiesto se incorpora desde PuenteCausal.rc; no generar otro al enlazar.
set_target_properties(PuenteCausal PROPERTIES LINK_FLAGS "/MANIFEST:NO")

target_compile_features(PuenteCausal PRIVATE cxx_std_20)
target_compile_definitions(PuenteCausal PRIVATE
  UNICODE
  _UNICODE
  WIN32_LEAN_AND_MEAN
  NOMINMAX
)

if(MSVC)
  target_compile_options(PuenteCausal PRIVATE /W4 /permissive- /utf-8 /EHsc)
else()
  target_compile_options(PuenteCausal PRIVATE -Wall -Wextra -Wpedantic)
endif()

target_link_libraries(PuenteCausal PRIVATE
  advapi32
  bcrypt
  comctl32
  shell32
  user32
  winhttp
)

enable_testing()
add_test(NAME autoevaluacion_lanzador COMMAND PuenteCausal --self-test)
