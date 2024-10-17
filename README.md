# MIRI Coronagraphy Program Tracker

This program will spit out an interactive HTML page that lists all the MIRI
coronagraphy observations for the programs listed in jwst_programs.txt. The
observations are sorted by planning status, and all columns are sortable.

## How to use

1. Update jwst_programs.txt with the programs you are interested int
2. Run program_tracker.py from the command line
3. Upload miri_coron_schedule.html, the output file, to
   https://stsci.app.box.com/file/1153457899380
4. Copy and paste the HTML into the HTML box at
   https://innerspace.stsci.edu/display/JWST/MIRI+Coronagraphy+Scheduling+Table

Requirements:
- pandas
- requests
- urllib3
- beautifulsoup4
- xmltodict


### PPSDB version

1. Open a terminal
2. Activate python env with `conda activate coron_program_schedule`
3. Run kinit? I think you have to explicitly add a kerberos ticket to this
   terminal instance
4. Run `python ppsdb_schedule.py` (or, `%run ppsdb_schedule.py` from within
   ipython)

You can copy-paste this code block:
```
conda activate coron_program_schedule
kinit
python ppsdb_schedule.py
```

You will be asked to enter a password after running `kinit`.

### TODO
I would like to be able to run it from a script as `./ppsdb_schedule.sh`.
However, to activate a conda evironment in a non-interactive shell, you should
`conda run -n {env_name} {python_script}`. I cannot figure out how to also run
`kinit` with this command *after* the environment has been activated.


## Misc info

Take a look at the table
https://www-int.stsci.edu/dsd/cns/database/r2d2/PPSDB103/plan_window_status.html
. It has information about the long-range plan.
