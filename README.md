# MIRI Coronagraphy Program Tracker

This program will spit out an interactive HTML page that lists all the MIRI coronagraphy observations for the programs listed in jwst_programs.txt.
The observations are sorted by planning status, and all columns are sortable.

## How to use

1. Update jwst_programs.txt with the programs you are interested int
2. Run program_tracker.py from the command line
3. Upload miri_coron_schedule.html, the output file, to https://stsci.app.box.com/file/1153457899380
4. Copy and paste the HTML into the HTML box at https://innerspace.stsci.edu/display/JWST/MIRI+Coronagraphy+Scheduling+Table

Requirements:
- pandas
- requests
- urllib3
- beautifulsoup4
- xmltodict


### PPSDB version

1. Open a terminal
2. Activate python env with `conda activate coron_program_schedule`
3. Run kinit?
4. Run `python ppsdb_schedule.py` (or, `%run ppsdb_schedule.py` from within ipython)
