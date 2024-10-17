#!/bin/bash

# this doesn't quite work because you have to run kinit *after* setting the environment
# Run ppsdb_schedule.py from bash
# run_schedule() {
#     kinit
#     python ppsdb_schedule.py
# }
# # alias run_schedule="kinit; python ppsdb_schedule"
# conda run -n coron_program_schedule run_schedule
kinit
python ppsdb_schedule.py
