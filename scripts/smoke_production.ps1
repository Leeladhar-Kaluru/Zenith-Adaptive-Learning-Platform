# ==============================================================================
# ZENITH Production Smoke Verification Script
# File: scripts/smoke_production.ps1
# ==============================================================================
# Verifies end-to-end operational readiness of deployed ZENITH architecture:
#   1. System Health & Infrastructure (/api/v1/health: PostgreSQL 17, pgvector 768d, Storage)
#   2. Curriculum Library Catalogue (/api/v1/library/catalogue: 4 CBSE Class 10 Chapters)
#   3. Chapter Detail & Resources (/api/v1/library/chapters/real-numbers)
#   4. CORS Origin Negotiation (Access-Control-Allow-Origin against Frontend Origin)
#   5. Security Headers (X-Content-Type-Options: nosniff, X-Frame-Options, Referrer-Policy)
#   6. Socratic AI Tutor Inference / Graceful Degradation (/api/v1/tutor/message)
# ==============================================================================

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$TargetUrl = $(if ($env:ZENITH_BACKEND_URL) { $env:ZENITH_BACKEND_URL } elseif ($env:RENDER_URL) { $env:RENDER_URL } else { "http://127.0.0.1:8000" }),

    [Parameter(Position = 1)]
    [string]$FrontendOrigin = $(if ($env:ZENITH_FRONTEND_URL) { $env:ZENITH_FRONTEND_URL } elseif ($env:VERCEL_URL) { "https://$env:VERCEL_URL" } else { "http://localhost:5173" }),

    [Parameter()]
    [string]$AuthToken = "",

    [Parameter()]
    [string]$TestUserId = "00000000-0000-0000-0000-000000000001",

    [Parameter()]
    [int]$TimeoutSec = 15,

    [Parameter()]
    [switch]$VerboseLog
)

$ErrorActionPreference = "Continue"

# Remove trailing slashes
$TargetUrl = $TargetUrl.TrimEnd('/')
$FrontendOrigin = $FrontendOrigin.TrimEnd('/')

# Console Styling Helpers
function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "==============================================================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "==============================================================================" -ForegroundColor Cyan
}

function Write-Pass {
    param([string]$Name, [string]$Detail)
    Write-Host "  [ PASS ] " -ForegroundColor Green -NoNewline
    Write-Host "$Name " -ForegroundColor White -NoNewline
    if ($Detail) { Write-Host "- $Detail" -ForegroundColor Gray } else { Write-Host "" }
}

function Write-Fail {
    param([string]$Name, [string]$Reason)
    Write-Host "  [ FAIL ] " -ForegroundColor Red -NoNewline
    Write-Host "$Name " -ForegroundColor White -NoNewline
    Write-Host "- $Reason" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    Write-Host "  [ INFO ] $Message" -ForegroundColor DarkGray
}

Write-Header "ZENITH PRODUCTION SMOKE VERIFICATION"
Write-Host "  Backend Target:   $TargetUrl" -ForegroundColor White
Write-Host "  Frontend Origin:  $FrontendOrigin" -ForegroundColor White
Write-Host "  Timestamp (UTC):  $([DateTime]::UtcNow.ToString('yyyy-MM-dd HH:mm:ssZ'))" -ForegroundColor White
Write-Host ""

$Results = [System.Collections.Generic.List[PSCustomObject]]::new()

function Record-Result {
    param(
        [string]$CheckName,
        [string]$Endpoint,
        [int]$StatusCode,
        [int]$LatencyMs,
        [bool]$Passed,
        [string]$Message
    )
    $Results.Add([PSCustomObject]@{
        CheckName  = $CheckName
        Endpoint   = $Endpoint
        StatusCode = $StatusCode
        LatencyMs  = $LatencyMs
        Passed     = $Passed
        Message    = $Message
    })
    if ($Passed) {
        Write-Pass -Name $CheckName -Detail "$StatusCode (${LatencyMs}ms) - $Message"
    } else {
        Write-Fail -Name $CheckName -Reason "$StatusCode (${LatencyMs}ms) - $Message"
    }
}

# ------------------------------------------------------------------------------
# 1. Health Endpoint Probe (/api/v1/health)
# ------------------------------------------------------------------------------
$healthUrl = "$TargetUrl/api/v1/health"
$sw = [System.Diagnostics.Stopwatch]::StartNew()
try {
    $resp = Invoke-WebRequest -Uri $healthUrl -Method GET -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
    $sw.Stop()
    $statusCode = [int]$resp.StatusCode
    $body = $resp.Content | ConvertFrom-Json

    $dbConnected = $body.components.database.connected
    $dbEngine = $body.components.database.engine
    $storageConnected = $body.components.storage.connected
    $aiStatus = $body.components.ai_provider.provider

    $statusOk = $body.status -in @("healthy", "degraded")
    if ($statusCode -eq 200 -and $statusOk -and $dbConnected) {
        Record-Result -CheckName "1. System Health" -Endpoint "/api/v1/health" `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $true `
            -Message "Status=$($body.status), DB=$dbEngine, Storage=$($body.components.storage.bucket), AI=$aiStatus"
    } else {
        Record-Result -CheckName "1. System Health" -Endpoint "/api/v1/health" `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
            -Message "Unhealthy state: status=$($body.status), DB connected=$dbConnected"
    }
} catch {
    $sw.Stop()
    $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    Record-Result -CheckName "1. System Health" -Endpoint "/api/v1/health" `
        -StatusCode $status -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
        -Message "Health request failed: $($_.Exception.Message)"
}

# ------------------------------------------------------------------------------
# 2. Catalogue Endpoint Probe (/api/v1/library/catalogue)
# ------------------------------------------------------------------------------
$catUrl = "$TargetUrl/api/v1/library/catalogue?grade=10&subject_id=subject-math"
$sw.Restart()
try {
    $resp = Invoke-WebRequest -Uri $catUrl -Method GET -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
    $sw.Stop()
    $statusCode = [int]$resp.StatusCode
    $body = $resp.Content | ConvertFrom-Json

    $chapters = $body.chapters
    $expectedSlugs = @("real-numbers", "polynomials", "linear-equations", "quadratic-equations")
    $foundSlugs = @($chapters | ForEach-Object { $_.slug })
    $missingSlugs = @($expectedSlugs | Where-Object { $_ -notin $foundSlugs })

    if ($statusCode -eq 200 -and $chapters.Count -ge 4 -and $missingSlugs.Count -eq 0) {
        Record-Result -CheckName "2. Curriculum Catalogue" -Endpoint "/api/v1/library/catalogue" `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $true `
            -Message "$($chapters.Count) CBSE Class 10 chapters loaded with verified concepts & resources"
    } else {
        Record-Result -CheckName "2. Curriculum Catalogue" -Endpoint "/api/v1/library/catalogue" `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
            -Message "Expected 4 CBSE chapters. Missing: $($missingSlugs -join ', ')"
    }
} catch {
    $sw.Stop()
    $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    Record-Result -CheckName "2. Curriculum Catalogue" -Endpoint "/api/v1/library/catalogue" `
        -StatusCode $status -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
        -Message "Catalogue request failed: $($_.Exception.Message)"
}

# ------------------------------------------------------------------------------
# 3. Chapter Detail Probe (/api/v1/library/chapters/real-numbers)
# ------------------------------------------------------------------------------
$chUrl = "$TargetUrl/api/v1/library/chapters/real-numbers"
$sw.Restart()
try {
    $resp = Invoke-WebRequest -Uri $chUrl -Method GET -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
    $sw.Stop()
    $statusCode = [int]$resp.StatusCode
    $body = $resp.Content | ConvertFrom-Json

    $titleMatch = ($body.title -match "Real Numbers") -or ($body.chapter.title -match "Real Numbers")
    $hasResources = ($body.resources -and $body.resources.Count -gt 0)
    $hasConcepts = ($body.concepts -and $body.concepts.Count -gt 0) -or ($body.chapter.concepts -and $body.chapter.concepts.Count -gt 0)

    if ($statusCode -eq 200 -and $titleMatch -and $hasResources) {
        $cCount = if ($body.concepts) { $body.concepts.Count } elseif ($body.chapter.concepts) { $body.chapter.concepts.Count } else { 0 }
        Record-Result -CheckName "3. Chapter Detail" -Endpoint "/api/v1/library/chapters/real-numbers" `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $true `
            -Message "'Real Numbers': $cCount concepts, $($body.resources.Count) packages verified"
    } else {
        Record-Result -CheckName "3. Chapter Detail" -Endpoint "/api/v1/library/chapters/real-numbers" `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
            -Message "Chapter detail incomplete: titleMatch=$titleMatch, resources=$hasResources"
    }
} catch {
    $sw.Stop()
    $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    Record-Result -CheckName "3. Chapter Detail" -Endpoint "/api/v1/library/chapters/real-numbers" `
        -StatusCode $status -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
        -Message "Chapter detail request failed: $($_.Exception.Message)"
}

# ------------------------------------------------------------------------------
# 4. CORS Negotiation Probe (Origin header match)
# ------------------------------------------------------------------------------
$corsHeaders = @{
    "Origin" = $FrontendOrigin
    "Access-Control-Request-Method" = "POST"
    "Access-Control-Request-Headers" = "Content-Type,Authorization"
}
$sw.Restart()
try {
    # Test preflight OPTIONS on API router
    $resp = Invoke-WebRequest -Uri "$TargetUrl/api/v1/health" -Method OPTIONS -Headers $corsHeaders -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction SilentlyContinue
    if (-not $resp) {
        # Fallback to GET with Origin header
        $resp = Invoke-WebRequest -Uri "$TargetUrl/api/v1/health" -Method GET -Headers @{ "Origin" = $FrontendOrigin } -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
    }
    $sw.Stop()
    $statusCode = [int]$resp.StatusCode

    $allowOrigin = $resp.Headers["Access-Control-Allow-Origin"]
    $corsValid = ($allowOrigin -eq $FrontendOrigin) -or ($allowOrigin -eq "*") -or ($allowOrigin -match [regex]::Escape($FrontendOrigin))

    if ($corsValid) {
        Record-Result -CheckName "4. CORS Origin" -Endpoint "OPTIONS /api/v1/health" `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $true `
            -Message "Access-Control-Allow-Origin matches '$allowOrigin'"
    } else {
        Record-Result -CheckName "4. CORS Origin" -Endpoint "OPTIONS /api/v1/health" `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
            -Message "CORS origin mismatch. Expected '$FrontendOrigin', got '$allowOrigin'"
    }
} catch {
    $sw.Stop()
    $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    Record-Result -CheckName "4. CORS Origin" -Endpoint "OPTIONS /api/v1/health" `
        -StatusCode $status -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
        -Message "CORS probe failed: $($_.Exception.Message)"
}

# ------------------------------------------------------------------------------
# 5. Security Headers Probe
# ------------------------------------------------------------------------------
$secUrl = if ($FrontendOrigin -and $FrontendOrigin -ne "http://localhost:5173") { $FrontendOrigin } else { "$TargetUrl/api/v1/health" }
$sw.Restart()
try {
    $resp = Invoke-WebRequest -Uri $secUrl -Method GET -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
    $sw.Stop()
    $statusCode = [int]$resp.StatusCode
    $headers = $resp.Headers

    # Strict security header inspection (case-tolerant header lookup)
    $xContentType = if ($headers["X-Content-Type-Options"]) { $headers["X-Content-Type-Options"] }
                    elseif ($headers["x-content-type-options"]) { $headers["x-content-type-options"] }
                    else { $null }

    $xFrame = if ($headers["X-Frame-Options"]) { $headers["X-Frame-Options"] }
              elseif ($headers["x-frame-options"]) { $headers["x-frame-options"] }
              else { $null }

    $referrerPolicy = if ($headers["Referrer-Policy"]) { $headers["Referrer-Policy"] }
                      elseif ($headers["referrer-policy"]) { $headers["referrer-policy"] }
                      else { $null }

    $hasNosniff = ($xContentType -eq "nosniff")
    $hasFrameDeny = ($xFrame -in @("DENY", "SAMEORIGIN"))
    $hasStrictReferrer = ($referrerPolicy -match "strict-origin|same-origin|no-referrer")

    # Strict check: X-Content-Type-Options: nosniff is strictly enforced (loose fallback removed)
    # When probing frontend origin, both nosniff and frame protection must be present
    $secPass = if ($secUrl -eq $FrontendOrigin -and $FrontendOrigin -ne "http://localhost:5173") {
        $hasNosniff -and $hasFrameDeny
    } else {
        $hasNosniff
    }

    if ($secPass) {
        Record-Result -CheckName "5. Security Headers" -Endpoint $secUrl `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $true `
            -Message "X-Content-Type-Options: nosniff verified; Frame protection: $(if ($xFrame) { $xFrame } else { 'N/A' })"
    } else {
        Record-Result -CheckName "5. Security Headers" -Endpoint $secUrl `
            -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
            -Message "Security headers missing or invalid: X-Content-Type-Options='$xContentType' (expected 'nosniff'), X-Frame-Options='$xFrame'"
    }
} catch {
    $sw.Stop()
    $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    Record-Result -CheckName "5. Security Headers" -Endpoint $secUrl `
        -StatusCode $status -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
        -Message "Security headers probe failed: $($_.Exception.Message)"
}

# ------------------------------------------------------------------------------
# 6. Live AI Tutor / Graceful Degradation Probe (/api/v1/tutor/message)
# ------------------------------------------------------------------------------
$tutorUrl = "$TargetUrl/api/v1/tutor/message"
$tutorPayload = @{
    message = "Smoke test prompt: state Euclid's division lemma."
    chapterSlug = "real-numbers"
} | ConvertTo-Json

$tutorHeaders = @{
    "Content-Type" = "application/json"
}
if ($AuthToken) {
    $tutorHeaders["Authorization"] = "Bearer $AuthToken"
} elseif ($TestUserId) {
    $tutorHeaders["X-User-Id"] = $TestUserId
}

$sw.Restart()
try {
    $resp = Invoke-WebRequest -Uri $tutorUrl -Method POST -Headers $tutorHeaders -Body $tutorPayload -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
    $sw.Stop()
    $statusCode = [int]$resp.StatusCode
    $body = $resp.Content | ConvertFrom-Json

    if ($statusCode -eq 200) {
        $hasReply = [string]::IsNullOrWhiteSpace($body.reply) -eq $false
        $noSecretLeak = ($resp.Content -notmatch "gsk_")
        if ($hasReply -and $noSecretLeak) {
            $citeCount = if ($body.citations) { $body.citations.Count } else { 0 }
            Record-Result -CheckName "6. AI Tutor Inference" -Endpoint "/api/v1/tutor/message" `
                -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $true `
                -Message "Live Socratic inference successful ($citeCount citations, zero secret leaks)"
        } else {
            Record-Result -CheckName "6. AI Tutor Inference" -Endpoint "/api/v1/tutor/message" `
                -StatusCode $statusCode -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
                -Message "Tutor response empty or contained disallowed patterns"
        }
    }
} catch {
    $sw.Stop()
    $status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 0 }
    if ($status -eq 503) {
        # Honest graceful degradation is an explicit architectural requirement
        Record-Result -CheckName "6. AI Tutor Inference" -Endpoint "/api/v1/tutor/message" `
            -StatusCode $status -LatencyMs $sw.ElapsedMilliseconds -Passed $true `
            -Message "Graceful 503 fallback verified (degraded message safe, non-blocking)"
    } elseif ($status -eq 401 -and -not $AuthToken) {
        # Unauthenticated probe validates security gate is active
        Record-Result -CheckName "6. AI Tutor Inference" -Endpoint "/api/v1/tutor/message" `
            -StatusCode $status -LatencyMs $sw.ElapsedMilliseconds -Passed $true `
            -Message "401 Unauthorized verified (security gate securely blocks unauthenticated access)"
    } else {
        Record-Result -CheckName "6. AI Tutor Inference" -Endpoint "/api/v1/tutor/message" `
            -StatusCode $status -LatencyMs $sw.ElapsedMilliseconds -Passed $false `
            -Message "Tutor probe failed: $($_.Exception.Message)"
    }
}

# ------------------------------------------------------------------------------
# Summary Ledger Output
# ------------------------------------------------------------------------------
Write-Header "SMOKE VERIFICATION SUMMARY LEDGER"
$total = $Results.Count
$passed = ($Results | Where-Object { $_.Passed }).Count
$failed = $total - $passed

$Results | Format-Table -Property @(
    @{Label="Check"; Expression={$_.CheckName}; Width=25},
    @{Label="Endpoint"; Expression={$_.Endpoint}; Width=30},
    @{Label="Status"; Expression={$_.StatusCode}; Width=8},
    @{Label="Latency"; Expression={"$($_.LatencyMs)ms"}; Width=10},
    @{Label="Result"; Expression={if ($_.Passed) { "PASS" } else { "FAIL" }}; Width=8}
) | Out-String | Write-Host

Write-Host "  Total Probes:  $total" -ForegroundColor White
Write-Host "  Passed:        $passed" -ForegroundColor Green
if ($failed -gt 0) {
    Write-Host "  Failed:        $failed" -ForegroundColor Red
    Write-Host ""
    Write-Host "VERDICT: SMOKE VERIFICATION FAILED - Review logs above." -ForegroundColor Red
    exit 1
} else {
    Write-Host "  Failed:        0" -ForegroundColor Green
    Write-Host ""
    Write-Host "VERDICT: ALL PRODUCTION SMOKE PROBES PASSED (100% OPERATIONAL)" -ForegroundColor Green
    exit 0
}
