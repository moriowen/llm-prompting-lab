#!/usr/bin/env sh
# Rebuild the page from runs/ and push it live.
#
# Two steps rather than a Vercel build command: building needs python and the whole trace
# corpus, and neither belongs in a static deploy. Vercel only ever receives public/.
set -e
cd "$(dirname "$0")/.."
PYTHONPATH=. python3 -m src.main ui
npx vercel --prod
