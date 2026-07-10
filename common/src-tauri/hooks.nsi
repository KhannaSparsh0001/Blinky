!macro NSIS_HOOK_PREINSTALL
  ; Stop any running blinky processes to release file locks on update/overwrite
  DetailPrint "Stopping existing Blinky processes..."
  nsExec::ExecToLog 'powershell -Command "Get-Process -Name blinky -ErrorAction SilentlyContinue | Stop-Process -Force; Get-Process | Where-Object { $_.Path -like ''*AppData\Local\Blinky*'' } | Stop-Process -Force -ErrorAction SilentlyContinue"'
!macroend

!macro NSIS_HOOK_POSTINSTALL
  ; Execute our python addon setup script and wait for it to complete.
  ; $INSTDIR is the installation directory selected by the user.
  ExecWait '"$INSTDIR\python_runtime\Python313\python.exe" "$INSTDIR\common\python\post_install.py"'
!macroend
