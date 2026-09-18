# Render a DOCX to PDF with Microsoft Word (COM), for visual QA of the submission files. Read-only on the DOCX.
#   powershell -File scripts/render_docx_pages.ps1 -Docx <in.docx> -Pdf <out.pdf>
# Fields are updated in the opened copy only; the DOCX on disk is not saved or modified.
param([Parameter(Mandatory = $true)][string]$Docx, [Parameter(Mandatory = $true)][string]$Pdf)
$ErrorActionPreference = "Stop"
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open((Resolve-Path $Docx).Path, $false, $true)   # ConfirmConversions=false, ReadOnly=true
    $null = $doc.Fields.Update()
    $pdfFull = [System.IO.Path]::GetFullPath($Pdf)
    $doc.ExportAsFixedFormat($pdfFull, 17)                                 # 17 = wdExportFormatPDF
    "pages: " + $doc.ComputeStatistics(2)                                  # 2 = wdStatisticPages
    $doc.Close(0)                                                           # 0 = wdDoNotSaveChanges
} finally {
    $word.Quit()
}
