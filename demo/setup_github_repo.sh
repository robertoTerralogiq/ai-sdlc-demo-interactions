#!/usr/bin/env bash
# One-time settings that make the AI review a real gate and let PRs merge themselves.
#   bash demo/setup_github_repo.sh owner/repo [enforced|ide]
# Needs admin on the repo. Branch protection on a private repo needs GitHub
# Pro/Team/Enterprise; on the free plan use a public demo repo.
set -euo pipefail
repo="${1:?usage: setup_github_repo.sh owner/repo [enforced|ide]}"
mode="${2:-enforced}"

gh api -X PATCH "repos/$repo" \
  -F allow_auto_merge=true -F delete_branch_on_merge=true -F allow_squash_merge=true >/dev/null

# IDE mode also requires the status the reviewer posts on each commit it reviewed
# from the IDE, so a push nobody reviewed cannot merge.
contexts='"stage-3: merge-gate"'
[[ "$mode" == ide ]] && contexts="$contexts, \"stage-2: ai-review (ide)\""

gh api -X PUT "repos/$repo/branches/main/protection" --input - >/dev/null <<JSON
{
  "required_status_checks": {"strict": false, "contexts": [$contexts]},
  "required_conversation_resolution": true,
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON

gh variable set SDLC_MODE -R "$repo" -b "$mode"
echo "mode $mode; auto-merge on; main requires [$contexts] and resolved conversations"
echo "next: add secret GEMINI_API_KEY, or variables GCP_WIF_PROVIDER / GCP_SERVICE_ACCOUNT / GOOGLE_CLOUD_PROJECT"
