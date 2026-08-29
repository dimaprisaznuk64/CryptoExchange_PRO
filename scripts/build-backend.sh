#!/usr/bin/env sh
# Build (and optionally push) the backend Docker image.
#
# Usage:
#   scripts/build-backend.sh                  # build only, tag cryptoexchange/backend
#   REGISTRY=registry.example.com scripts/build-backend.sh --push
set -e

cd "$(dirname "$0")/../backend" || exit 1

IMAGE="${REGISTRY:-}cryptoexchange/backend"
TAG="${TAG:-latest}"
IMAGE_TAG="${IMAGE}:${TAG}"

echo ">> Building ${IMAGE_TAG}"
docker build -t "${IMAGE_TAG}" .

if [ "$1" = "--push" ]; then
  echo ">> Pushing ${IMAGE_TAG}"
  docker push "${IMAGE_TAG}"
fi

echo ">> Done."
