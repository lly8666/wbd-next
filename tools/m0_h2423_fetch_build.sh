#!/usr/bin/env bash
set -euo pipefail
: "${GITHUB_SHA:?}" "${GITHUB_REPOSITORY:?}" "${WBD_PLAN029_LINUX_EXPECTED_ARCH:?}"
name="h2423-product-$WBD_PLAN029_LINUX_EXPECTED_ARCH-$GITHUB_SHA"
export ARTIFACT_NAME="$name"
run=""
for i in $(seq 1 100); do
  run=$(gh api "repos/$GITHUB_REPOSITORY/actions/workflows/qa-h2423-build.yml/runs?head_sha=$GITHUB_SHA&event=push&per_page=10" --jq '.workflow_runs | map(select(.head_sha == env.GITHUB_SHA)) | sort_by(.id) | last | .id // empty')
  if [[ -n "$run" ]];then
    artifact=$(gh api "repos/$GITHUB_REPOSITORY/actions/runs/$run/artifacts?per_page=30" --jq '.artifacts[] | select(.name == env.ARTIFACT_NAME and .expired == false) | .id')
    if [[ -n "$artifact" ]];then break;fi
    status=$(gh api "repos/$GITHUB_REPOSITORY/actions/runs/$run" --jq '.status')
    if [[ "$status" == completed ]];then echo "Exact build ended without $name" >&2;exit 1;fi
  fi
  sleep 10
done
test -n "$run" && test -n "${artifact:-}"
mkdir -p h2423-download linux-plan029-public-bundle
gh run download "$run" --repo "$GITHUB_REPOSITORY" --name "$name" --dir h2423-download
tar -xzf h2423-download/h2423-product.tgz -C linux-plan029-public-bundle
(cd linux-plan029-public-bundle && sha256sum -c SHA256SUMS)
python3 - "$run" "$artifact" <<'PY'
import json,os,pathlib,sys
p=pathlib.Path("linux-plan029-public-bundle")
d=json.loads((p/"manifest.json").read_text())
assert d["source_sha"]==os.environ["GITHUB_SHA"]
assert d["architecture"]==os.environ["WBD_PLAN029_LINUX_EXPECTED_ARCH"]
pathlib.Path("h2423-build-identity.json").write_text(json.dumps({"build_run":int(sys.argv[1]),"artifact_id":int(sys.argv[2]),"manifest":d},indent=2)+"\n")
PY
