# deploy.ps1
# run 
# .\deploy\agent_insurance.ps1

# Load .env file into environment variables
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.+)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}

# start importing...
Write-Host "`nStarting WXO deployment >agent_insurance...`n" -ForegroundColor Cyan

# import knowledge base "knowledge_base_abc_policy"
orchestrate knowledge-bases import -f knowledge_bases\knowledge_base_abc_policy.yaml

# import tool "tool_send_gmail"
(Get-Content tools\tool_send_an_gmail.yaml) -replace '<FUNCTION_URL_TOOL_SEND_AN_GMAIL>', $env:FUNCTION_URL_TOOL_SEND_AN_GMAIL |
    Set-Content tools\tool_send_an_gmail_resolved.yaml

orchestrate tools import -k openapi -f tools\tool_send_an_gmail_resolved.yaml

Remove-Item tools\tool_send_an_gmail_resolved.yaml

# import tool "tool_update_spreadsheet"
(Get-Content tools\tool_update_spreadsheet.yaml) -replace '<FUNCTION_URL_TOOL_UPDATE_SPREADSHEET>', $env:FUNCTION_URL_TOOL_UPDATE_SPREADSHEET |
    Set-Content tools\tool_update_spreadsheet_resolved.yaml

orchestrate tools import -k openapi -f tools\tool_update_spreadsheet_resolved.yaml

Remove-Item tools\tool_update_spreadsheet_resolved.yaml

# import agent "agent_insurance"
orchestrate agents import -f agents\agent_insurance.yaml