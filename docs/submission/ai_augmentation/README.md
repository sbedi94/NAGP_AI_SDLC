# AI augmentation logging

## Install
Copy this `ai-augmentation` folder into:
`docs/submission/ai-augmentation/`

The logger assumes it is located at:
`<repo>/docs/submission/ai-augmentation/logger.py`

It uses only Python's standard library. No pip packages are required.

## First run
From the repository root, after copying the folder:

```powershell
python .\docs\submission\ai-augmentation\logger.py --stage setup --mode combination --prompt "Configure AI augmentation logging for this assignment" --response-summary "Configured local append-only JSONL logger and schema" --status applied --human-decision "Reviewed logger structure; will verify actual environment details" --tools-used "ChatGPT" --limitation "ChatGPT conversations and IDE interactions are not automatically captured"
```

## Log a later interaction
Use the actual prompt (or a faithful concise record), actual model/mode, and actual outcomes:

```powershell
python .\docs\submission\ai-augmentation\logger.py `
  --stage architecture `
  --mode plan `
  --prompt "Compare the current invoice approval architecture with the proposed production target" `
  --response-summary "Produced a draft architecture comparison" `
  --status proposed `
  --files-read "backend/src/InvoiceApp.Api/Program.cs" `
  --human-decision "Pending code verification"
```

## Important accuracy rules
- `status=proposed` means no change was applied.
- Use `applied` only after making the change.
- Use `validated` only after recording successful validation evidence.
- `git_working_tree` captures Git's status at logging time; it does not prove that the listed files were modified by AI.
- `files_read`, `files_modified`, skills, MCP tools and sub-agents must be supplied truthfully.
- The logger records local Git metadata; it does not capture ChatGPT's hidden internal activity, browser state, or IDE conversations.
- Never put credentials, secrets, tokens, or private customer data in prompts or logs.
- Preserve native ChatGPT/IDE exports separately when available.

## Readable summary
At the end of each work session, summarize meaningful records in `ai-activity-summary.md`, including accepted/rejected suggestions, human corrections, validation evidence and unresolved limitations.
