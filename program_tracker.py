"""Generate an html page that contains all the visit information"""
# use conda environment coron_program_tracker
import sys
import re
from pathlib import Path
import time
from datetime import datetime, date
import inspect
# from requests.sessions import get_environ_proxies
import pandas as pd
from lib import observing_windows as ow
from lib import html



def parse_plan_windows(window, dates=[]):
    """Parse the 'planWindow' field of the observing window results"""
    # if there's more than one window, use recursion to parse them all
    template = pd.Series(
        {
            "planWindow-begin_cal": pd.NA,
            "planWindow-end_cal": pd.NA,
            "planWindow-begin_dec": pd.NA,
            "planWindow-end_dec": pd.NA,
        }
    )
    if isinstance(window, list):
        for w in window:
            parse_plan_windows(w, dates)
    # if it's NA, return NA
    elif pd.isna(window):
        dates.append(template)
    # once you get down to a string, parse the string
    else:
        # find the decimal year string because that's more predictable
        dec_dates_fmt = "\([0-9]{4}\.[0-9]{3}\ \-\ [0-9]{4}\.[0-9]{3}\)"
        dec_dates_span = re.search(dec_dates_fmt, window).span()
        # use the indices to separate the two date formats
        dec_dates = window[dec_dates_span[0] + 1 : dec_dates_span[1] - 1].split(" - ")
        cal_dates = window[: dec_dates_span[0] - 1].split(" - ")
        dates_tmp = template.copy()
        dates_tmp["planWindow-begin_cal"] = cal_dates[0]
        dates_tmp["planWindow-end_cal"] = cal_dates[1]
        dates_tmp["planWindow-begin_dec"] = dec_dates[0]
        dates_tmp["planWindow-end_dec"] = dec_dates[1]
        dates.append(dates_tmp)
    # if the original window was not a list, then don't return a list
    if not isinstance(window, list):
        dates = pd.DataFrame(dates[0]).T
    else:
        dates = pd.concat(list(dates), axis=1).T
    return dates


def add_plan_windows_to_program_df(program_df):
    """
    Given the results of the web crawl for program info, parse the program windows
    into their own columns for beginning and end dates
    Applies the parse_plan_windows() function to the scraper results
    """
    # programs that have already executed do not have a planWindow column
    # if this is the case, add a dummy column
    if "planWindow" not in program_df.columns:
        program_df["planWindow"] = pd.NA

    parsed = {
        i: parse_plan_windows(row["planWindow"], []) for i, row in program_df.iterrows()
    }
    parsed = pd.concat(
        parsed.values(), keys=parsed.keys(), names=["obs_index", "obs_window"], axis=0
    )
    program_df.index.name = "obs_index"
    df = program_df.merge(parsed, how="inner", on="obs_index").set_index(parsed.index)
    df.drop(columns="planWindow", inplace=True)
    return df


def filter_miri(visit_list):
    """Only keep MIRI observations"""
    pop_list = []
    for i, el in enumerate(visit_list):
        # if "MIRI" not in el['configuration'].upper():
        #     pop_list.append(i)
        if el["configuration"].lower() != "miri coronagraphic imaging":
            pop_list.append(i)
    pop_list = sorted(pop_list)[::-1]
    for i in pop_list:
        visit_list.pop(i)
    return visit_list


def prog2df(info, miri_only=True):
    """Turn the visit information into a dataframe"""
    visits = info["visit"]
    # keep only MIRI observations?
    if miri_only == True:
        visits = filter_miri(visits)
    try:
        df = pd.concat([pd.Series(i) for i in visits], axis=1).T
        df.rename(
            columns={"@observation": "observation", "@visit": "visit"}, inplace=True
        )
        # split the planWindow column into something sortable
        df = add_plan_windows_to_program_df(df)
        # add the miri reviewer to the dataframe
        df['Instr. Sci.'] = info['miri_is']
    except ValueError:
        print(f"{info['proposal_id']} failed, no information available")
        df = pd.DataFrame()
    return df


def parse_repeats(repeat_dict):
    """
    Parse the OrderedDict entries of the repeatOf and repeatedBy fields.
    These are used in the Scheduled and Skipped tables

    Parameters
    ----------
    repeat_dict : OrderedDict
      This contains the information about the observation that was/will be repeated
      

    Output
    ------
    repeat_str: str
      the repeat observation information in a nicely formatted string

    """
    if isinstance(repeat_dict, dict):
        repeat_str = ' / '.join(f"{k}: {v}" for k, v in repeat_dict.items())
    else:
        repeat_str = str(repeat_dict)
    return repeat_str


def get_program_table(list_of_programs, verbose=True):
    """Given a list of program IDs, get their visit status information"""
    programs = {}
    for pid in list_of_programs:
        print(str(pid.strip()))
        info = ow.program_info(pid)
        df = prog2df(info)
        if df.empty == True:
            pass
        else:
            programs[info["proposal_id"]] = df#prog2df(info)
        if verbose:
            print(str(pid) + " finished")
    # combine the programs and drop the dummy indices
    programs = pd.concat(programs, names=["pid"]).reset_index()
    programs.drop(columns=["obs_index", "obs_window"], inplace=True)
    # clean up weird columns
    for repeat_col in ['repeatOf', 'repeatedBy']:
        if repeat_col in programs.columns:
            programs[repeat_col] = programs[repeat_col].apply(parse_repeats)
    return programs



def print_columns(items, ncols=4):
    """Take a list of items to print and format them into columns

    Parameters
    ----------
    list_of_items: list-like
      stuff to print in columns
    ncols : int
      number of columns

    Output
    ------
    prints the passed items in the given number of columns
    """
    col_width = max([len(i) for i in items])
    items = [f"{j:{ncols}s}" for j in items]
    nitems = len(items)
    nrows = int(nitems / ncols + (nitems % ncols > 0))
    lines = []
    for r in range(nrows):
        row_items = items[r * ncols : r * ncols + ncols]
        lines.append(" ".join(row_items))
    print("\n".join(lines))


def get_next_month(program_table, time_window=60):
    """
    Get all the programs whose planning or execution windows are scheduled for within a month from today's date.

    Parameters
    ----------
    program_table : pd.DataFrame
      output of get_program_table()
    time_window : int [60]
      the time window, in days, to search for programs

    Output
    ------
    Filtered list of observations that are executing in the given window

    """
    today = date.today()

    def get_time_delta(jdate, time_window=time_window):
        try:
            start_time = time.strptime(str(jdate), "%Y.%j")
        except:
            return False
        start_date = date(start_time.tm_year, start_time.tm_mon, start_time.tm_mday)
        dtime = (start_date - today).days
        in_window = True if dtime <= time_window else False
        if dtime < 0 :
            in_window = False
        return in_window

    program_table["in_next_month"] = program_table["planWindow-begin_dec"].astype(float).apply(
        get_time_delta, args=[time_window]
    )
    return program_table.query("in_next_month == True").copy()


def generate_email_template(
        programs : pd.DataFrame
) -> str :
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
    today = datetime.today().strftime("%Y-%m-%d")
    text = ""
    text += f"Subject line: MIRI Coronagraphy - Upcoming Programs {today}" + "\n"
    text += "\n\n"
    text += "Dear MIRI Coronagraphy Working Group,\n\n"
    text += f"The schedule of MIRI coronagraphic observations has been updated and is available here: https://innerspace.stsci.edu/display/JWST/MIRI+Coronagraphy+Scheduling+Table." + "\n"

    time_window = 60
    text += f"The following observations are planned to execute within the next {time_window} days:" + "\n\n"
    
    next_programs = get_next_month(programs, time_window)
    next_programs["observation"] = next_programs["observation"].apply(int)
    next_programs.sort_values(by=["planWindow-begin_dec", "observation"], inplace=True)

    for key, group in next_programs.groupby("status"):
        text += "Status: " + key + "\n"
        text += "-" * len("Status: " + key) + "\n"
        lines = group.apply(
            lambda row: f"Prog {row['pid']} | Obs {int(row['observation']):3d} | Start: {row['planWindow-begin_cal']} | {row['Instr. Sci.']}",
            axis=1,
        )
        text += "\n".join(lines) + "\n\n"
    text += "\n" + "Regards," + "\n\n" + "The MIRI Coronagraphy Working Group"
    return text



if __name__ == "__main__":
    if len(sys.argv) == 1:
        ifile = "./jwst_programs.txt"
        with open(ifile, "r") as f:
            prog_ids = [i.strip() for i in f.readlines()]
    else:
        prog_ids = sys.argv[1]
        prog_ids = prog_ids.split(" ")
    #     ofile = sys.argv[1]
    ofile = "miri_coron_schedule.html"
    print(f"Generating `{ofile}` from the following {len(prog_ids)} programs:")
    print_columns(prog_ids)
    print("")

    programs = get_program_table(prog_ids)
    try:
        html_path = Path(ofile)
    except:
        html_path = Path("/Users/jaguilar/Desktop/test.html")
    html.write_html(str(html_path), programs)
    print(
        inspect.cleandoc(
            f"""\
            {Path(ofile).absolute()} written. Upload it to the "MIRI Coronagraphy Dump" folder:
            \t https://stsci.app.box.com/folder/196944163759
            and copy-paste the HTML from {str( ofile )} into the HTML box on the Scheduling page:
            \t https://innerspace.stsci.edu/display/JWST/MIRI+Coronagraphy+Scheduling+Table
            """
        )
    )

    # print the programs that are happening in the next month
    print("Copy and paste this text (email_text.txt) into your program status email:\n")
    email_text = generate_email_template(programs)
    print(email_text)
    with open("email_text.txt", "w") as f:
        f.write(email_text)
