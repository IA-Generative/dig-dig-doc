#!/usr/bin/env bash
# Régénère sdks/python/openapi.json depuis le backend : à relancer quand un schéma d'API change,
# puis corriger les modèles du SDK que tests/test_contract.py signale.
set -euo pipefail
root="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$root/backend"
VERIFY_TOKEN_MODEL=full-access uv run --group test python -c "
import json
from app.main import app
json.dump(app.openapi(), open('$root/sdks/python/openapi.json', 'w'), indent=1, ensure_ascii=False, sort_keys=True)
"
