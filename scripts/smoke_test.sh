#!/usr/bin/env bash
# Smoke-test an OntoIt deployment end-to-end.
# Usage: ./scripts/smoke_test.sh [BASE_URL]
# Defaults to http://localhost:8000 when called with no argument.
set -euo pipefail

BASE="${1:-http://localhost:8000}"
COOKIES="$(mktemp)"
PASS=0
FAIL=0

pass() { echo "PASS  $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL  $1"; FAIL=$((FAIL + 1)); }

# -- 1. Health probe --------------------------------------------------------
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/health")
BODY=$(curl -s "$BASE/health")
if [ "$STATUS" = "200" ] && echo "$BODY" | grep -q '"ok"'; then
    pass "/health → 200 ok"
else
    fail "/health → expected 200 ok, got HTTP $STATUS: $BODY"
fi

# -- 2. POST /session/sample ------------------------------------------------
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -c "$COOKIES" -b "$COOKIES" \
    "$BASE/session/sample")
if [ "$STATUS" = "200" ]; then
    pass "POST /session/sample → 200"
else
    fail "POST /session/sample → expected 200, got $STATUS"
fi

# -- 3. GET /stream (SSE greeting) -----------------------------------------
SSE=$(curl -s -N --max-time 15 \
    -c "$COOKIES" -b "$COOKIES" \
    "$BASE/stream")
if echo "$SSE" | grep -q "event: assistant" && echo "$SSE" | grep -q "event: done"; then
    pass "GET /stream → SSE assistant + done events received"
else
    fail "GET /stream → expected assistant and done events; got: $(echo "$SSE" | head -5)"
fi

# -- 4a. POST /message → first turn (filing status) ------------------------
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d '{"text":"single"}' \
    -c "$COOKIES" -b "$COOKIES" \
    "$BASE/message")
if [ "$STATUS" = "200" ]; then
    pass "POST /message {text:single} → 200"
else
    fail "POST /message {text:single} → expected 200, got $STATUS"
fi

# -- 4b. POST /message → second turn (dependents) --------------------------
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d '{"text":"no kids"}' \
    -c "$COOKIES" -b "$COOKIES" \
    "$BASE/message")
if [ "$STATUS" = "200" ]; then
    pass "POST /message {text:\"no kids\"} → 200"
else
    fail "POST /message {text:\"no kids\"} → expected 200, got $STATUS"
fi

# -- 5. GET /download (filled 1040 PDF) ------------------------------------
PDF_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -c "$COOKIES" -b "$COOKIES" \
    "$BASE/download")
PDF_CT=$(curl -s -o /dev/null -w "%{content_type}" \
    -c "$COOKIES" -b "$COOKIES" \
    "$BASE/download")
PDF_SIZE=$(curl -s -w "%{size_download}" -o /dev/null \
    -c "$COOKIES" -b "$COOKIES" \
    "$BASE/download")
if [ "$PDF_STATUS" = "200" ] && echo "$PDF_CT" | grep -q "application/pdf" && [ "${PDF_SIZE:-0}" -gt 1000 ]; then
    pass "GET /download → 200 application/pdf (${PDF_SIZE} bytes)"
else
    fail "GET /download → expected 200 application/pdf >1 KB; got HTTP $PDF_STATUS ct=$PDF_CT size=${PDF_SIZE:-0}"
fi

# -- Summary ----------------------------------------------------------------
rm -f "$COOKIES"
echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
