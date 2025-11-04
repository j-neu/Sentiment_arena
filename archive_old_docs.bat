@echo off
REM Archive old phase completion documentation
REM Run this to move all PHASE_*.md files to archive/ directory

echo.
echo ============================================
echo  Archiving Phase Completion Documents
echo ============================================
echo.

REM Move PHASE_* files
move "PHASE_2.1_COMPLETE.md" "archive\" 2>nul
move "PHASE_2.2_COMPLETE.md" "archive\" 2>nul
move "PHASE_3_COMPLETE.md" "archive\" 2>nul
move "PHASE_3_SUMMARY.md" "archive\" 2>nul
move "PHASE_3.5.1_COMPLETE.md" "archive\" 2>nul
move "PHASE_3.5.2_COMPLETE.md" "archive\" 2>nul
move "PHASE_3.5.3_COMPLETE.md" "archive\" 2>nul
move "PHASE_3.5.4_COMPLETE.md" "archive\" 2>nul
move "PHASE_3.5.5_COMPLETE.md" "archive\" 2>nul
move "PHASE_4_COMPLETE.md" "archive\" 2>nul
move "PHASE_5_COMPLETE.md" "archive\" 2>nul
move "PHASE_6_COMPLETE.md" "archive\" 2>nul
move "PHASE_6_ENHANCEMENTS.md" "archive\" 2>nul
move "PHASE_8.2.1_FIXES.md" "archive\" 2>nul
move "PHASE_8.2.1_VALIDATION.md" "archive\" 2>nul
move "PHASE_8.2.2_DYNAMIC_DISCOVERY.md" "archive\" 2>nul

REM Move INTEGRATION_* files
move "INTEGRATION_3.5_COMPLETE.md" "archive\" 2>nul

REM Move other historical documents
move "MODELS_UPDATED.md" "archive\" 2>nul
move "DEPLOYMENT_SUMMARY.md" "archive\" 2>nul

echo.
echo ✓ All historical documentation moved to archive/
echo.
echo Current documentation structure:
echo   - DEVELOPMENT_HISTORY.md  (replaces all PHASE_*.md files)
echo   - PROJECT_STATUS.md       (current system status)
echo   - README.md               (project overview)
echo   - QUICKSTART.md           (setup guide)
echo   - TASKS.md                (roadmap)
echo   - DEPLOYMENT_LOCAL.md     (deployment guide)
echo   - CLAUDE.md               (architecture)
echo   - RESEARCH_QUALITY.md     (research design)
echo   - PROMPT_TEMPLATES.md     (trading prompts)
echo.
echo Historical documents are in archive/ directory
echo.
pause
