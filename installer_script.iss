[Setup]
AppName=TeleClinic Bot
AppVersion=2.0.0
DefaultDirName=C:\teleclinic-bot
DefaultGroupName=TeleClinic Bot
OutputDir=Output
OutputBaseFilename=TeleClinic-Bot-Installer-Full
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
DisableProgramGroupPage=yes

[Files]
; Haupt-Skripte
Source: "C:\teleclinic-bot\tc_main_gui.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\teleclinic-bot\teleclinic_click_from_list_v9d.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\teleclinic-bot\core_scheduler.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\teleclinic-bot\license_system.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\teleclinic-bot\scheduled_patients.py"; DestDir: "{app}"; Flags: ignoreversion

; Konfiguration
Source: "C:\teleclinic-bot\filters.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\teleclinic-bot\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; Logos
Source: "C:\teleclinic-bot\Logo Teleclinic scanner.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\teleclinic-bot\Logo_GIZ_Praxis_neu_ohne_Hintergrund.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\teleclinic-bot\Logo_Teleclinic_scanner.ico"; DestDir: "{app}"; Flags: ignoreversion

; Dokumentation
Source: "C:\teleclinic-bot\INSTALLATION_ANLEITUNG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\teleclinic-bot\Output\SETUP_NEUE_PC.txt"; DestDir: "{app}"; Flags: ignoreversion

; Chrome Debug Starter
Source: "C:\teleclinic-bot\start_chrome_debug.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "C:\teleclinic-bot\start_teleclinic_bot.bat"; DestDir: "{app}"; Flags: ignoreversion

; Leere JSON-Dateien für Laufzeit
Source: "C:\teleclinic-bot\scheduled_slots.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "C:\teleclinic-bot\scheduled_patients.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist

[Icons]
Name: "{group}\TeleClinic Bot"; Filename: "{app}\start_teleclinic_bot.bat"; WorkingDir: "{app}"; IconFilename: "{app}\Logo_Teleclinic_scanner.ico"
Name: "{commondesktop}\TeleClinic Bot"; Filename: "{app}\start_teleclinic_bot.bat"; WorkingDir: "{app}"; Tasks: desktopicon; IconFilename: "{app}\Logo_Teleclinic_scanner.ico"
Name: "{group}\Chrome Debug starten"; Filename: "{app}\start_chrome_debug.bat"; WorkingDir: "{app}"; Comment: "Chrome im Debug-Modus für TeleClinic starten"
Name: "{commondesktop}\Chrome Debug (TeleClinic)"; Filename: "{app}\start_chrome_debug.bat"; WorkingDir: "{app}"; Tasks: chromedebugicon; Comment: "Chrome im Debug-Modus starten"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Icon für TeleClinic Bot erstellen"; GroupDescription: "Zusätzliche Icons:"
Name: "chromedebugicon"; Description: "Desktop-Icon für Chrome Debug-Modus erstellen"; GroupDescription: "Zusätzliche Icons:"

[Run]
; Installiere Python-Abhängigkeiten nach der Installation
Filename: "python"; Parameters: "-m pip install --upgrade pip"; WorkingDir: "{app}"; StatusMsg: "Aktualisiere pip..."; Flags: runhidden waituntilterminated
Filename: "python"; Parameters: "-m pip install -r requirements.txt"; WorkingDir: "{app}"; StatusMsg: "Installiere Python-Abhängigkeiten (ca. 1-2 Min)..."; Flags: runhidden waituntilterminated
Filename: "python"; Parameters: "-m playwright install chromium"; WorkingDir: "{app}"; StatusMsg: "Installiere Playwright Browser (ca. 2-3 Min)..."; Flags: runhidden waituntilterminated
; Starte Programm nach Installation (optional)
Filename: "{app}\start_teleclinic_bot.bat"; Description: "TeleClinic Bot starten"; Flags: nowait postinstall skipifsilent

[Code]
function IsPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function InitializeSetup(): Boolean;
var
  ErrorCode: Integer;
begin
  if not IsPythonInstalled() then
  begin
    if MsgBox('Python wurde nicht gefunden!' + #13#10 + #13#10 +
              'TeleClinic Bot benötigt Python 3.11 oder höher.' + #13#10 + #13#10 +
              'Möchten Sie Python jetzt herunterladen und installieren?' + #13#10 +
              '(Die Python-Installationsseite wird im Browser geöffnet)',
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      ShellExec('open', 'https://www.python.org/downloads/', '', '', SW_SHOW, ewNoWait, ErrorCode);
      MsgBox('Bitte installieren Sie Python und aktivieren Sie dabei die Option:' + #13#10 + #13#10 +
             '"Add Python to PATH"' + #13#10 + #13#10 +
             'Starten Sie diesen Installer danach erneut.',
             mbInformation, MB_OK);
      Result := False;
    end
    else
    begin
      Result := False;
    end;
  end
  else
  begin
    Result := True;
  end;
end;
