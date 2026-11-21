#!/bin/bash

module load gcc/16.2.0
module load cmake

export CXX=$(which g++)
export CC=$(which gcc)
export CMAKE=$(which cmake)

AUTOPAS_PATH=/dss/dsshome1/0B/ge92hed3/AutoPas

echo "Building ${AUTOPAS_PATH}"

mkdir -p ${AUTOPAS_PATH}/build
cd ${AUTOPAS_PATH}/build

$CMAKE -DMD_FLEXIBLE_USE_MPI=OFF \
    -DCMAKE_C_COMPILER=$CC \
    -DCMAKE_CXX_COMPILER=$CXX \
    -DAUTOPAS_ENABLE_ENERGY_MEASUREMENTS=OFF \
    -DAUTOPAS_ENABLE_DYNAMIC_CONTAINERS=OFF \
    -DAUTOPAS_LOG_ITERATIONS=ON \
    -DAUTOPAS_LOG_LIVEINFO=ON \
    -DAUTOPAS_MIN_LOG_LVL=OFF \
    -DAUTOPAS_ENABLE_RULES_BASED_AND_FUZZY_TUNING=OFF \
    -DAUTOPAS_LOG_TUNINGDATA=ON \
    -DAUTOPAS_LOG_TUNINGRESULTS=ON \
    -DMD_FLEXIBLE_FUNCTOR_AVX=ON \
    ${AUTOPAS_PATH}/
$CMAKE --build ${AUTOPAS_PATH}/build --target md-flexible --parallel 12
