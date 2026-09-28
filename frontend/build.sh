#!/bin/sh
set -eu

: "${API_BASE_URL:?Vercel 환경변수 API_BASE_URL이 필요합니다.}"

mkdir -p dist
cp index.html styles.css app.js dist/
sed "s|__API_BASE_URL__|${API_BASE_URL}|g" config.template.js > dist/config.js
