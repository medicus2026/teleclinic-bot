$WS = New-Object -ComObject WScript.Shell
$SC = $WS.CreateShortcut("C:\Users\Thomas\Desktop\TeleClinic Bot.lnk")
$SC.TargetPath = "cmd.exe"
$SC.Arguments = '/c "C:\teleclinic-bot\start_teleclinic_bot.bat"'
$SC.WorkingDirectory = "C:\teleclinic-bot"
$SC.IconLocation = "C:\teleclinic-bot\Logo_Teleclinic_scanner.ico"
$SC.Description = "TeleClinic Bot starten"
$SC.WindowStyle = 1
$SC.Save()
Write-Host "OK: Verknuepfung erstellt auf Desktop"
