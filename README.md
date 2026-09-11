# Legacy Tool API-less Extraction & Audit Automation

Automated a multi-vendor network configuration audit that previously required
manually clicking through a legacy internal reporting tool, one submarket and
one report at a time. The tool exposes no public API, so this project
reverse-engineers the request shape and session token directly from the
browser's own network traffic using the Chrome DevTools Protocol (CDP), then
replays those requests programmatically across every submarket.

## The problem

The legacy tool is a browser-only application with no documented API. Pulling
a full audit meant manually selecting each report, clicking "Generate," and
downloading the result -- repeated across dozens of submarkets and report
types. There was no vendor cooperation available to add an API, and no
realistic path to migrating off the tool in the short term.

## The approach

1. **Capture, don't guess.** Rather than reverse-engineering the request format
   by trial and error, `extract_payload.py` attaches to a running Chrome
   instance via CDP and passively listens for the exact network request the
   tool's own UI fires when a report is generated. It captures the request
   body (`payload.json`) and the session's auth token (`token.txt`) straight
   from real browser traffic.
2. **Parameterize per submarket.** `create_submarket_payloads.py` takes the
   captured payload templates (one per report type) and stamps out a
   ready-to-send payload for every submarket, injecting the correct market
   list, submarket name, and run date into each one.
3. **Replay directly against the backend.** `automate_report_extraction.py`
   uses the captured token to POST each submarket's payloads straight to the
   tool's internal report-generation endpoint -- skipping the UI entirely --
   and handles both ZIP and CSV response formats. It also detects and
   automatically re-runs any payload that didn't produce a report.
4. **Orchestrate the full audit.** `run_audit_pipeline.py` ties it together:
   pick one submarket or all of them, and it runs the full
   precheck -> extract -> validate -> exception-report chain in order,
   stopping immediately if any stage fails.

## Why this approach

- **No API, no problem.** CDP lets you treat any browser-based tool as a data
  source, since you're reading the same requests the tool's own frontend
  already sends -- no scraping the rendered page, no fragile screen-scraping.
- **One token, full reuse.** A single captured session token drives requests
  across every submarket and report type in one run, rather than
  re-authenticating per report.
- **Self-healing.** The pipeline detects missing reports (failed requests,
  empty responses) and automatically retries just those, rather than
  requiring a manual re-check of the full output.

## Tech stack

Python · Chrome DevTools Protocol (CDP) · `websocket-client` · `requests` ·
JSON-based request templating · subprocess-based pipeline orchestration

## Note on this repository

The scripts here are generalized from an internal tool used at my employer.
Internal hostnames, endpoint paths, and organization-specific report/field
names have been replaced with placeholders (e.g. `your-legacy-tool.internal`,
`report_type_a`/`report_type_b`). The underlying technique --
capture-via-CDP, template-per-segment, replay-and-validate -- is unchanged
and is what this repo is meant to demonstrate.
