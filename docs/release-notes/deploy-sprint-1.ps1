# ECOSYSTEM-SPRINT-1 deployment script
# Extracts the Sprint-1 deliverables into E:\alagf-ecosystem
# and stages commits according to the "one logical unit per commit" rule.
#
# Usage:
#   Open PowerShell in the directory containing sprint-1-package.zip.
#   Run: .\deploy-sprint-1.ps1
#
# Requires: git available on PATH, repo root at E:\alagf-ecosystem.

param(
    [string]$RepoRoot = "E:\alagf-ecosystem",
    [string]$ZipPath  = ".\sprint-1-package.zip"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

# --- Preflight checks -------------------------------------------------------

Write-Step "Preflight: validating repo root"
if (-not (Test-Path $RepoRoot)) {
    throw "Repo root not found: $RepoRoot"
}
if (-not (Test-Path "$RepoRoot\.git")) {
    throw "$RepoRoot is not a git repository."
}
if (-not (Test-Path $ZipPath)) {
    throw "Sprint-1 package not found: $ZipPath"
}

Write-Step "Preflight: checking working tree is clean"
Push-Location $RepoRoot
try {
    $status = git status --porcelain
    # Allow untracked scratch dumps from the Sprint-1 diagnostics session.
    $relevant = $status | Where-Object {
        $_ -notmatch "_v\d_schemas_dump" -and
        $_ -notmatch "~\$" -and
        $_ -notmatch "^\?\? demo/ledger/?$"
    }
    if ($relevant) {
        Write-Host "Working tree is not clean. Review and stash or commit before deploying:" -ForegroundColor Yellow
        $status | ForEach-Object { Write-Host "  $_" }
        $confirm = Read-Host "Proceed anyway? (y/N)"
        if ($confirm -ne "y") { throw "Aborted by user." }
    }
} finally {
    Pop-Location
}

# --- Extract package --------------------------------------------------------

Write-Step "Extracting Sprint-1 package to $RepoRoot"
$zipFull = Resolve-Path $ZipPath
Expand-Archive -Path $zipFull -DestinationPath $RepoRoot -Force
Write-Host "Extraction complete."

# --- Install Python dependencies -------------------------------------------

Write-Step "Installing Python dependencies"
Push-Location $RepoRoot
try {
    python -m pip install jsonschema fastapi "pydantic>=2" pytest httpx
} finally {
    Pop-Location
}

# --- Run the test suite -----------------------------------------------------

Write-Step "Running Sprint-1 test suite"
Push-Location $RepoRoot
try {
    python -m pytest multiagent/tests/ -v
    if ($LASTEXITCODE -ne 0) {
        throw "Test suite failed. Do not commit until green."
    }
} finally {
    Pop-Location
}

# --- Commit guidance --------------------------------------------------------

Write-Step "Tests passed. Recommended commit sequence (one logical unit per commit)"

$commitPlan = @"
Suggested commit sequence:

1. Exception taxonomy
   git add multiagent/exceptions.py
   git commit -m "ECOSYSTEM-SPRINT-1: exception taxonomy"

2. Event payload and envelope schemas
   git add multiagent/ledger/hash_chain/event_schemas/
   git commit -m "ECOSYSTEM-SPRINT-1: v2 LedgerEvent envelope and event payload schemas"

3. Contract validator
   git add multiagent/artifacts/ContractValidator.py multiagent/artifacts/__init__.py multiagent/__init__.py
   git commit -m "ECOSYSTEM-SPRINT-1: ContractValidator"

4. AgentIdentity factory
   git add multiagent/artifacts/AgentIdentity/
   git commit -m "ECOSYSTEM-SPRINT-1: AgentIdentity factory with Invariant 1 runtime enforcement"

5. Ledger writer
   git add multiagent/ledger/
   git commit -m "ECOSYSTEM-SPRINT-1: append-only hash-chained ledger writer"

6. Orchestrator lifecycle functions
   git add multiagent/orchestrator/agent_lifecycle/
   git commit -m "ECOSYSTEM-SPRINT-1: agent lifecycle orchestrator"

7. API layer
   git add multiagent/orchestrator/api.py multiagent/orchestrator/__init__.py
   git commit -m "ECOSYSTEM-SPRINT-1: FastAPI endpoints for AgentIdentity lifecycle"

8. Test suite
   git add multiagent/tests/
   git commit -m "ECOSYSTEM-SPRINT-1: invariant acceptance tests and agent boundary tests"

9. Documentation
   git add multiagent/README.md multiagent/docs/ docs/release-notes/
   git commit -m "ECOSYSTEM-SPRINT-1: changelog and Sprint-0 reconciliation record"

10. Push
    git push origin main
"@

Write-Host $commitPlan
Write-Host ""
Write-Step "Deployment complete. Review the commit plan above and execute it manually."
Write-Host "Note: the deploy script does not auto-commit. Human authority remains in the loop." -ForegroundColor Green
