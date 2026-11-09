#!/usr/bin/env bash
# Legt die Dummy-Testmedien des Handtest-Parcours in .runtime-test/media-run an (Repo-Root als Arbeitsverzeichnis).
# Voraussetzung: scripts/orbstack-test.sh init (bzw. reset) wurde ausgeführt; ffmpeg ist installiert.
set -euo pipefail
M=".runtime-test/media-run"
mk() { ffmpeg -loglevel error -y -f lavfi -i color=c=black:s=320x240:d=1 -f lavfi -i anullsrc=r=44100:cl=mono -t 1 -c:v libx264 -preset ultrafast -c:a aac -shortest "$1"; }
mkdir -p "$M/Input" "$M/Output"
mk "$M/Input/Matrix.1999.German.1080p.mkv"
mk "$M/Input/Jaws.1975.German.mkv"
mk "$M/Input/Das.Boot.1981.German.mkv"
mkdir -p "$M/Input/Alien.1979" && mk "$M/Input/Alien.1979/Alien.1979.mkv"
printf '<?xml version="1.0" encoding="UTF-8"?>\n<movie>\n  <title>Alien Bestands-NFO (Test)</title>\n  <year>1979</year>\n  <plot>Bestandstext, soll bei F-5 beobachtet werden.</plot>\n</movie>\n' > "$M/Input/Alien.1979/Alien.1979.nfo"
mkdir -p "$M/Input/Breaking.Bad" && mk "$M/Input/Breaking.Bad/Breaking.Bad.S01E01.mkv" && mk "$M/Input/Breaking.Bad/Breaking.Bad.S01E02.mkv"
mk "$M/Input/Planet.Erde.2006.Doku.mkv"
mkdir -p "$M/Filme/Matrix Reloaded (2003)" && mk "$M/Filme/Matrix Reloaded (2003)/Matrix Reloaded (2003).mkv"
echo "Testmedien angelegt unter $M"
