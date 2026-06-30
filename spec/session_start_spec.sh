#!/usr/bin/env sh

### File: session_start_spec.sh
##
## Validates the Claude Code session-start hook and settings.
##
## Usage:
##
## ------ Text ------
## shellspec spec/session_start_spec.sh
## ------------------

eval "$(shellspec -) exit 1"

HOOK=".claude/hooks/session-start.sh"
SETTINGS=".claude/settings.json"

Describe 'session-start hook'
  Describe 'file'
    Example 'exists'
      When call test -f "${HOOK}"
      The status should eq 0
    End

    Example 'is executable'
      When call test -x "${HOOK}"
      The status should eq 0
    End

    Example 'has valid bash syntax'
      When call bash -n "${HOOK}"
      The status should eq 0
    End
  End

  Describe 'behaviour'
    Example 'exits 0 when not in remote environment'
      When call env -u CLAUDE_CODE_REMOTE bash "${HOOK}"
      The status should eq 0
    End

    Example 'sources CLAUDE_PROJECT_DIR when set'
      When call env CLAUDE_CODE_REMOTE=true CLAUDE_PROJECT_DIR="$(pwd)" bash "${HOOK}"
      The status should eq 0
    End
  End
End

Describe 'settings.json'
  Example 'exists'
    When call test -f "${SETTINGS}"
    The status should eq 0
  End

  Example 'contains SessionStart hook entry'
    When call grep -q 'SessionStart' "${SETTINGS}"
    The status should eq 0
  End

  Example 'references session-start.sh'
    When call grep -q 'session-start.sh' "${SETTINGS}"
    The status should eq 0
  End

  Example 'is valid JSON'
    When call node -e "JSON.parse(require('fs').readFileSync('${SETTINGS}','utf8'))"
    The status should eq 0
  End
End

Describe 'package.json'
  Example 'speckit listed as devDependency'
    When call node -e "const p=JSON.parse(require('fs').readFileSync('package.json','utf8')); process.exit(p.devDependencies && p.devDependencies.speckit ? 0 : 1)"
    The status should eq 0
  End

  Example 'speckit installed in node_modules'
    When call test -d "node_modules/speckit"
    The status should eq 0
  End
End
