#!/usr/bin/env python
 
from pathlib import Path
import datetime
import inspect

import pandas as pd

from ppsdb.ppsdb import Connect

from lib import html

pps = Connect()
 
reviewer_ids = {
    20974 : "Bryony Nickson",
    20978 : "Jonathan Aguilar",
    936 : "Dean Hines",
    1947 : "Alberto Noriega Crespo"
}

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


query = """
  SELECT
    program.category,
    bpv.program,
    bpv.observation,
    bpv.visit_id,
    bpv.scheduled_start_time,
    vt.visit_status,
    science_reviewer.person_id,
    science_reviewer.instrument
  FROM baseline_prime_visits as bpv
  # use the visit table to select for the miri coron template
  JOIN visit as v
    ON v.visit_id = bpv.visit_id
  # get the visit status from the visit_track table
  JOIN visit_track as vt
    ON vt.program = bpv.program
    AND vt.observation = bpv.observation
    AND vt.visit = bpv.visit
  # left join - handles the case where there is no science reviewer, like a cal program
  LEFT JOIN science_reviewer
    ON science_reviewer.program = bpv.program
  JOIN program
    ON program.program = bpv.program
  WHERE
    bpv.program > 1000
    AND v.template = 'MIRI Coronagraphic Imaging'
    AND (science_reviewer.instrument IS NULL or science_reviewer.instrument = 'MIRI')
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
    # print("All programs")
    # print(table[['program','observation','scheduled_start_time']].sort_values(by='scheduled_start_time'))
    table['isodate'] = table['scheduled_start_time'].apply(lambda t: datetime.date.fromisoformat(t.split(" ")[0]))
    table['SI'] = table['person_id'].apply(lambda pid: reviewer_ids.get(pid, 'None'))
    table.drop(columns=['person_id'], inplace=True)
    return table

def get_future_programs(
        table : pd.DataFrame,
        window : int = 60
) -> pd.DataFrame:
    """
    Return programs planned to execute in the future, within a certain window of days
    """
    today = datetime.date.today()
    td_window = datetime.timedelta(days=window)
    end_window = today + td_window
    scheduled_programs = table[table['isodate'] >= today]
    scheduled_in_window = scheduled_programs[scheduled_programs['isodate'] <= end_window]
    # replace person_id with name
    # scheduled_in_window['SI'] = scheduled_in_window['person_id'].apply(lambda pid: reviewer_ids.get(pid, 'None'))
    # scheduled_in_window.drop(columns=['person_id'], inplace=True)
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
                print(
                    f"{row['category']:3s}" + " | "\
                    + f"Prog: {prog:4d}" + " | "\
                    + f"Obs: {row['observation']:3d}" + " | "\
                    + f"Start: {row['isodate']}" + " | "\
                    + f"SI: {row['SI']}"
                )
            print("")
        print("\n")


def generate_email_template(
        programs : pd.DataFrame,
        time_window : int = 60
) -> None:
    """
    Generate the email template and write it to disk

    Parameters
    ----------
    programs : pd.DataFrame
      dataframe with the program information

    Output
    ------
    writes email template to "email_template.txt"

    """
    today = datetime.date.today().strftime("%Y-%m-%d")
    print("\n")
    print(f"Subject line: MIRI Coronagraphy - Upcoming Programs {today}" + "\n")
    print("Dear MIRI Coronagraphy Working Group,\n")
    print(f"Here are topics for our tag-up tomorrow: [FILL IN]" + "\n")
    print(f"The following observations are planned to execute within the next {time_window} days:" + "\n")
    
    print_table(programs)

    print("\n" + "Regards," + "\n\n" + "The MIRI Coronagraphy Working Group")


if __name__ == '__main__':
    # get full history of observations
    # Get target_id and target_name for background target.
    all_visits = get_visits_pps()
    window = 60
    observation_statuses = get_future_programs(all_visits, window)
    print_table(observation_statuses)
    ofile = "miri_coron_schedule.html"
    try:
        html_path = Path(ofile)
    except:
        html_path = Path("/Users/jaguilar/Desktop/test.html")
    html.write_html_pps(str(html_path), all_visits)
    print(
        inspect.cleandoc(
            f"""\
            {Path(ofile).absolute()} written. Upload it to the "MIRI Coronagraphy WG Files" folder:
            \t https://stsci.app.box.com/folder/196944163759
            and copy-paste the HTML from {str( ofile )} into the HTML box on the Scheduling page:
            \t https://innerspace.stsci.edu/display/JWST/MIRI+Coronagraphy+Scheduling+Table
            """
        )
    )

    print("Copy and paste this text (email_text.txt) into your program status email:\n")
    generate_email_template(observation_statuses, window)
