#!/usr/bin/env bash
# Télécharge jevos-v5 (binaire Linux x64 + modèle OpenVINO INT8) dans jevos/
set -e
cd "$(dirname "$0")"
if [ -x jevos/jev ] && [ -d jevos/model ]; then echo "jevos déjà installé."; exit 0; fi
mkdir -p downloads && cd downloads
BASE=https://github.com/feder-cr/jev/releases/download/jevos-v5
for f in jev-linux-x64.tar.gz jevos-v5-openvino-int8.zip SHA256SUMS.txt; do
  [ -f "$f" ] || curl -fL -o "$f" "$BASE/$f"
done
sha256sum -c SHA256SUMS.txt --ignore-missing
rm -rf jev && tar -xzf jev-linux-x64.tar.gz
(cd jev && unzip -q ../jevos-v5-openvino-int8.zip)
rm -rf ../jevos && mv jev ../jevos
echo "jevos installé dans jevos/. Les archives de downloads/ peuvent être supprimées."
