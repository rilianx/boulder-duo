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
# agentes de la competencia para comparar (YOLOBOT: ganador 2015–2018), de GVGAI-ShallowThought
COMP_REV=58ceca601da0c727f837a3d0d35a1a8fdb024111
if [ ! -d vendor/competitors/YOLOBOT ]; then
  rm -rf vendor/shallow && git clone -q https://github.com/UrsaMinorBeta/GVGAI-ShallowThought vendor/shallow
  git -C vendor/shallow checkout -q "$COMP_REV"
  mkdir -p vendor/competitors && cp -r vendor/shallow/gvgai/src/YOLOBOT vendor/competitors/
  sed -i 's/^import core.VGDLViewer;/import core.vgdl.VGDLViewer;/' vendor/competitors/YOLOBOT/Agent.java
fi
find vendor/competitors/YOLOBOT -name "*.java" > vendor/yolobot.txt
javac -nowarn -encoding UTF-8 -d vendor/classes -cp vendor/classes:vendor/GVGAI/gson-2.6.2.jar @vendor/yolobot.txt 2>&1 | grep -v "Picked up\|^Note" || true
echo "listo: $(find vendor/classes -name '*.class' | wc -l) clases"
