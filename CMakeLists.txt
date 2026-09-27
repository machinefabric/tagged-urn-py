# The package's native part: the program lungo generated from the proved model in ../formal,
# which the module tagged_urn._formal loads. Built by scikit-build-core when the package is.
cmake_minimum_required(VERSION 3.20)
project(tagged_urn LANGUAGES C)
add_subdirectory(src/tagged_urn/_formal)
