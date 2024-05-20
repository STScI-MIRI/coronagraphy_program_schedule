#!/usr/bin/env python
 
import datetime
import pandas as pd
from ppsdb.ppsdb import Connect
 
ppsdb = Connect()
 
reviewer_ids = {
    20974 : "Bryony Nickson",
    20978 : "Jonathan Aguilar",
    936 : "Dean Hines",
    1947 : "Alberto Noriega Crespo"
}

def get_visits_pps(
        window : int = 60,
) -> pd.DataFrame :
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
    query = """
      SELECT
        program.category,
        obpv.program,
        obpv.observation,
        obpv.visit_id,
        obpv.scheduled_start_time,
        vt.visit_status,
        science_reviewer.person_id,
        science_reviewer.instrument
      FROM opgs_baseline_prime_visits as obpv
      # use the visit table to select for the miri coron template
      JOIN visit as v
        ON v.visit_id = obpv.visit_id
      # get the visit status from the visit_track table
      JOIN visit_track as vt
        ON vt.program = obpv.program
        AND vt.observation = obpv.observation
        AND vt.visit = obpv.visit
      # left join - handles the case where there is no science reviewer, like a cal program
      LEFT JOIN science_reviewer
        ON science_reviewer.program = obpv.program
      JOIN program
        ON program.program = obpv.program
      WHERE
        obpv.program > 1000
        AND v.template = 'MIRI Coronagraphic Imaging'
        AND (science_reviewer.instrument IS NULL or science_reviewer.instrument = 'MIRI')
    """
    table = ppsdb.execute(query)
    table = table.to_pandas()
    table['iso'] = table['scheduled_start_time'].apply(lambda t: datetime.date.fromisoformat(t.split(" ")[0]))
    today = datetime.date.today()
    td_window = datetime.timedelta(days=6)
    end_window = today + td_window

    scheduled_programs = table[table['iso'] >= today]
    scheduled_in_window = scheduled_programs[scheduled_programs['iso'] <= end_window]
    # replace person_id with name
    scheduled_in_window['SI'] = scheduled_in_window['person_id'].apply(lambda pid: reviewer_ids.get(pid, 'None'))
    scheduled_in_window.drop(columns=['person_id'], inplace=True)
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
    for status, index in gb_status.groups.items():
        group = df.loc[index]
        unique_obs = group.groupby(['program','observation']).apply(
            lambda group: group.sort_values(by='iso').iloc[0],
            include_groups=False
        ).reset_index()
        print("\n")
        print(f"Visit status: {status}")
        print(f"------------")
        gb_program = unique_obs.groupby("program")
        for prog in gb_program.groups:
            group = gb_program.get_group(prog)
            for i, row in group.iterrows():
                print(f"{row['category']:3s} | Prog: {prog:4d} | Obs: {row['observation']:3d} | Start: {row['iso']} | SI: {row['SI']}")
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
    print(f"Subject line: MIRI Coronagraphy - Upcoming Programs {today}" + "\n")
    print("\n")
    print("Dear MIRI Coronagraphy Working Group,\n")
    print(f"Here are topics for our tag-up tomorrow: [FILL IN]" + "\n")
    print(f"The following observations are planned to execute within the next {time_window} days:" + "\n")
    
    print_table(programs)

    print("\n" + "Regards," + "\n\n" + "The MIRI Coronagraphy Working Group")


if __name__ == '__main__':
    # find observations of targets with background = 'Y'.
    # Get target_id and target_name for background target.
    window = 60
    observation_statuses = get_visits_pps(window=window)
    # print_table(observation_statuses)
    generate_email_template(observation_statuses, window)
