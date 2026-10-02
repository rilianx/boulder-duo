#!/usr/bin/env bash
# Compila GVGAI sin límite de tiempo por acción (40/50 ms → 1 hora) en vendor/classes_notime, solo para la
# prueba de referencia determinista (golden.py): con límite, una decisión lenta se reemplaza por "nada" según
# la carga de la máquina y la partida deja de ser reproducible.
set -euo pipefail
cd "$(dirname "$0")"
rm -rf vendor/notime_src vendor/classes_notime && mkdir -p vendor/classes_notime
cp -r vendor/GVGAI/src vendor/notime_src
sed -i 's/ACTION_TIME = 40;/ACTION_TIME = 3600000;/; s/ACTION_TIME_DISQ = 50;/ACTION_TIME_DISQ = 3600000;/' \
  vendor/notime_src/core/competition/CompetitionParameters.java
find vendor/notime_src -name "*.java" > vendor/notime_sources.txt
javac -nowarn -encoding UTF-8 -d vendor/classes_notime -cp vendor/GVGAI/gson-2.6.2.jar @vendor/notime_sources.txt 2>&1 | grep -v "^Note:\|Picked up" || true
javac -nowarn -encoding UTF-8 -d vendor/classes_notime -cp vendor/classes_notime:vendor/GVGAI/gson-2.6.2.jar java/boulderduo/*.java 2>&1 | grep -v "Picked up" || true
echo "listo: $(find vendor/classes_notime -name '*.class' | wc -l) clases"
