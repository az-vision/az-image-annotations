# Specify the folder path where your *.txt files are located
$folderPath = "C:\azvision\batches"

# Get all *.txt files recursively from the folder and its subfolders
$txtFiles = Get-ChildItem -Path $folderPath -Filter *.txt -File -Recurse

# Define a hashtable to map leading digits to their translations
$digitMap = @{
    '0' = '0'
    '1' = '0'
    '2' = '1'
    '3' = '2'
    '4' = '3'
    '5' = ''
}

# Array to hold removed lines (lines with leading digit 5)
$removedLines = @()

# Loop through each text file
foreach ($file in $txtFiles) {
    # Read all lines from the current file
    $lines = Get-Content -Path $file.FullName

    # Array to hold modified lines
    $modifiedLines = @()

    # Process each line in the file
    foreach ($line in $lines) {
        # Split the line into the leading digit and the rest of the line
        if ($line -match '^(\d)\s(.*)$') {
            $leadingDigit = $Matches[1]
            $restOfLine = $Matches[2]

            # Translate the leading digit according to the mapping
            if ($digitMap.ContainsKey($leadingDigit)) {
                $translatedDigit = $digitMap[$leadingDigit]

                # Append to modified lines array if the translated digit is not empty
                if (![string]::IsNullOrEmpty($translatedDigit)) {
                    $modifiedLines += "$translatedDigit $restOfLine"
                } else {
                    # If the translated digit is empty and original digit is 5, add to removed lines
                    if ($leadingDigit -eq '5') {
                        $removedLines += $line
                    }
                }
            }
        }
    }

    # Write the modified lines back to the file, overwriting the original content
    $modifiedLines | Set-Content -Path $file.FullName -Force
}

# Print all removed lines
if ($removedLines.Count -gt 0) {
    Write-Host "Removed lines with leading digit 5:"
    $removedLines
} else {
    Write-Host "No lines with leading digit 5 were removed."
}
