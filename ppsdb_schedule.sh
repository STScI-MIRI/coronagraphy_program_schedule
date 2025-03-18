#!/bin/bash

#today=`date '+%Y%m%d'`
# fname="miri_upcoming_observations-${today}.html"
fname="miri_upcoming_observations.html"
conda run -n coron_program_schedule python ppsdb_schedule.py $fname
open $fname

