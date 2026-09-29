#!/usr/bin/env bash
# Baja GVGAI en una versión fija, lo compila y compila el puente de Boulder Dúo.
#   bash rl/gvgai/build.sh            → rl/gvgai/vendor/{GVGAI, classes}
set -euo pipefail
cd "$(dirname "$0")"
REV=e58ff6597319155218759cc178931e05b81b524c   # commit de GVGAI con que se probó
mkdir -p vendor
if [ ! -d vendor/GVGAI ]; then
  git clone https://github.com/GAIGResearch/GVGAI vendor/GVGAI
  git -C vendor/GVGAI checkout -q "$REV"
fi
rm -rf vendor/classes && mkdir -p vendor/classes
find vendor/GVGAI/src -name "*.java" > vendor/sources.txt
javac -nowarn -encoding UTF-8 -d vendor/classes -cp vendor/GVGAI/gson-2.6.2.jar @vendor/sources.txt 2>&1 | grep -v "^Note:\|Picked up" || true
javac -nowarn -encoding UTF-8 -d vendor/classes -cp vendor/classes:vendor/GVGAI/gson-2.6.2.jar java/boulderduo/*.java 2>&1 | grep -v "Picked up" || true
echo "listo: $(find vendor/classes -name '*.class' | wc -l) clases"
