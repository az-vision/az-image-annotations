# Define the source and destination folders for stage 1
$sourceFolder = "C:\temp\screenshots"
$stage1Destination = "C:\temp\stage"

# Get all subfolders in the source folder
$subfolders = Get-ChildItem -Path $sourceFolder -Directory

# Create the stage 1 destination folder if it doesn't exist
New-Item -Path $stage1Destination -ItemType Directory -Force

# Loop through each subfolder and copy files to the stage 1 destination folder and rename them
foreach ($subfolder in $subfolders) {
    
    $deviceId = $subfolder.Name.Split('-')[4]
    $folder_date = $subfolder.Name.Split('-')[0, 1, 2] -join '-'
    $jpgFiles = Get-ChildItem -Path $subfolder.FullName -Filter "*.jpg"
    
    $jpgFilesLength = $jpgFiles.Count
    Write-Host "Processing subfolder: $($subfolder.FullName) [$jpgFilesLength]"

    foreach ($file in $jpgFiles) {
        $originalNumber = $file.BaseName.Split('-')[1]
        $newFileName = "{0}-{1}-img{2:D5}.jpg" -f $deviceId, $folder_date, $originalNumber
        Copy-Item -Path $file.FullName -Destination (Join-Path -Path $stage1Destination -ChildPath $newFileName) -Force
    }
}
