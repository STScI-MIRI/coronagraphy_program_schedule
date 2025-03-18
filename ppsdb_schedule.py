#!/usr/bin/env python
 
import sys
from pathlib import Path
import datetime
import inspect

import pandas as pd

from ppsdb.ppsdb import Connect

from lib import html

pps = Connect()

# Visit statuses, in the order you want them displayed
visit_status_kws = [
    'SCHEDULED',
    'FLIGHT_READY',
    'IMPLEMENTATION',
    'PI',
    'COMPLETED',
    'SKIPPED',
    'FAILED',
    'WITHDRAWN',
]


# lines beginning with '#' will be stripped from this query before it is
# submitted to PPS, so you can use them for comments
query = """
  SELECT
    program.category,
    bvv.program,
    program.title,
    bvv.observation,
    bvv.scheduled_start_time,
    vt.visit_status,
    ev.instrument,
    instruments.prime_si,
    instruments.parallel_si
  # This table combines baseline_prime_visits and baseline_parallel_visits tables
  FROM baseline_visits_view as bvv
  # get the visit status from the visit_track table
  JOIN visit_track as vt
    ON vt.program = bvv.program
    AND vt.observation = bvv.observation AND vt.visit = bvv.visit
  LEFT JOIN program
    ON program.program = bvv.program
  # add the instrument table using the visit_id to match
  JOIN instruments
    ON instruments.visit_id = bvv.visit_id
  # the exposure_view has the instrument information
  JOIN exposure_view as ev
    ON ev.visit_id = bvv.visit_id
  WHERE
    # filter for programs from after commissioning
    bvv.program > 1000
    # filter for MIRI
    AND ev.instrument = 'MIRI'
"""

def get_visits_pps(query=query) -> pd.DataFrame :
    """
    Query PPS to get upcoming coronagraphy programs within the window

    Parameters
    ----------
    window: int = 60
      How far ahead, in days, to report programs

    Output
    ------
    pd.DataFrame, containing program IDs, visits, and start dates

    """
    table = pps.execute(query)
    table = table.to_pandas()
    table['isodate'] = table['scheduled_start_time'].apply(lambda t: datetime.date.fromisoformat(t.split(" ")[0]))
    table.drop(columns='scheduled_start_time', inplace=True)
    return table

def get_future_programs(
        table : pd.DataFrame,
        window : int | None = 60
) -> pd.DataFrame:
    """
    Return programs planned to execute in the future, within a certain window of days
    """
    table = table.sort_values(by='isodate')

    today = datetime.date.today()
    scheduled_programs = table[table['isodate'] >= today]
    if window is None:
        return scheduled_programs
    else:
        td_window = datetime.timedelta(days=window)
        end_window = today + td_window
        scheduled_in_window = scheduled_programs[scheduled_programs['isodate'] <= end_window]
        return scheduled_in_window

def print_table(
        df : pd.DataFrame,
) -> None :
    """
    Print the start day of each observation in the dataframe

    Parameters
    ----------
    df : pd.DataFrame
      dataframe returned by get_visits_pps

    Output
    ------
    None - prints table to screen

    """
    if df.empty == True:
        print("\t[[ no observations found ]]")
    gb_status = df.groupby("visit_status")
    # for status in visit_status_kws:
    #     group = df.query(f"visit_status == '{status}'")
    for status, index in gb_status.groups.items():
        group = df.loc[index]
        unique_obs = group.groupby(['program','observation']).apply(
            lambda group: group.sort_values(by='isodate').iloc[0],
            include_groups=False
        ).reset_index()
        print("\n")
        print(f"Visit status: {status}")
        print(f"------------")
        gb_program = unique_obs.groupby("program")
        for prog in gb_program.groups:
            group = gb_program.get_group(prog)
            for i, row in group.iterrows():
                # print(
                #     f"{row['category']:3s}" + " | "\
                #     + f"Prog: {prog:4d}" + " | "\
                #     + f"Obs: {row['observation']:3d}" + " | "\
                #     + f"Start: {row['isodate']}" + " | "\
                #     + f"SI: {row['SI']}"
                # )
                print(" | ".join(str(v) for v in row.values))
            # print("")
        # print("\n")


if __name__ == '__main__':
    fname = sys.argv[1]
    box_url = "https://stsci.app.box.com/folder/196944163759"
    innerspace_url = "https://innerspace.stsci.edu/display/JWST/MIRI+Coronagraphy+Scheduling+Table"
    # get full history of observations

    # Get target_id and target_name for background target.
    all_visits = get_visits_pps()
    all_observation_statuses = get_future_programs(all_visits, None)
    all_observation_statuses.sort_values(by='isodate', inplace=True)

    # observations in the next 60 days
    window = 60
    window_observation_statuses = get_future_programs(all_visits, window).drop_duplicates()
    # fname = f"miri_upcoming_observations-{today.year}{today.month:02d}{today.day:02d}.html"
    with open(fname, "w") as f:
        f.write(window_observation_statuses.to_html(index=False))
