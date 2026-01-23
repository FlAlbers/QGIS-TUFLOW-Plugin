# Run SWMM - GPKG or INP

Run a SWMM inp file using a SWMM executable.

## Inputs
- SWMM Input File (Inp): Optional if a GPKG is provided.
- SWMM GeoPackage Input File (optional): Generates the inp first, then runs SWMM.
- SWMM Executable (optional): Path to `runswmm.exe`. Leave blank if `runswmm.exe` is in a standard location. 
- Report File (RPT): Optional; defaults next to the inp.
- Output File (OUT): Optional; defaults next to the inp.

## Outputs
- Report File (RPT)
- Output File (OUT)

## Notes
- After the run completes, the report is scanned and up to 10 lines containing
  `ERROR` or `WARNING` are sent to the QGIS log. If more exist, the log is truncated.
- Typically the default path search for the SWMM Excecutable should be enough. If multiple SWMM installations are present the latest version is picked by default.