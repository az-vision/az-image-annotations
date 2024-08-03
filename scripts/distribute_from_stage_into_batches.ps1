# Define the source and destination folders for stage 2
$stage2Source = "C:\temp\stage"
$stage2Destination = "C:\temp\batches"

# Get all jpg files in the stage 1 destination folder
$filesToDistribute = Get-ChildItem -Path $stage2Source -File -Filter "*.jpg"

# Initialize batch variables
$batchCount = 1
$filesInBatch = 0

# Create the destination folder if it doesn't exist
New-Item -Path $stage2Destination -ItemType Directory -Force

# Initialize hashtable to keep track of files already processed for each deviceid-folder_date combination
$processedFiles = @{}

# Initialize array to store files from each source folder
$filesByFolder = @{}


# Group files by source folder
foreach ($file in $filesToDistribute) {
    # Extract the source folder name from the file name
    $folder = $file.Name.Split('-')[0, 1, 2, 3] -join '-'

    # Check if the filesByFolder hashtable already contains a key for the source folder
    if (-not $filesByFolder.ContainsKey($folder)) {
        # If not, initialize an empty array for that folder
        $filesByFolder[$folder] = @()
    }

    # Add the current file to the array associated with its source folder
    $filesByFolder[$folder] += $file
}


# Loop through files and distribute them into batch folders
while ($filesByFolder.Values.Count -gt 0) {
    # Create a copy of the keys to avoid modifying the collection while iterating over it
    $foldersToProcess = @($filesByFolder.Keys)

    foreach ($folder in $foldersToProcess) {
        $filesInFolder = $filesByFolder[$folder]

        if ($filesInFolder.Count -gt 0) {
            # Take the first file from the folder
            $file = $filesInFolder[0]

            # Move the file to the appropriate batch folder
            $batchFolder = Join-Path -Path $stage2Destination -ChildPath ("batch-{0:D3}" -f $batchCount)
            if (-not (Test-Path $batchFolder)) {
                Write-Host "Creating new batch folder: $batchFolder"
                New-Item -Path $batchFolder -ItemType Directory -Force
            }

            $destinationFileName = Join-Path -Path $batchFolder -ChildPath $file.Name
            Write-Host "Moving file: $($file.FullName) to: $destinationFileName"
            Move-Item -Path $file.FullName -Destination $destinationFileName -Force
            $filesInBatch++

            # If the batch contains 1000 files, create a new batch folder
            if ($filesInBatch -eq 1000) {
                $batchCount++
                $filesInBatch = 0
            }

            # Update processedFiles hashtable
            $deviceId = $file.BaseName.Split('-')[0]
            $folder_date = $file.BaseName.Split('-')[1, 2, 3] -join '-'
            $fileKey = "$deviceId-$folder_date"
            $processedFiles[$fileKey] = $true

            # Remove processed file from the list
            $filesByFolder[$folder] = $filesInFolder | Select-Object -Skip 1
        }
    }
}

