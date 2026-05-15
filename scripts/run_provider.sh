#!/usr/bin/env sh
# Shortcut to run a specific provider directly for testing

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

provider_type=$1
provider_name=$2
[ -z "$provider_type" ] && echo "Please specify provider type (e.g. anime/manga)" && exit
[ -z "$provider_name" ] && echo "Please specify provider name (e.g. gogoanime)" && exit

uv run python -m anicat_media.libs.provider.${provider_type}.${provider_name}.provider
