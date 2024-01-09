### HTML GENERATION ###

from pathlib import Path
from datetime import datetime, date

template_path = Path(__file__).parent / "html_templates"

# top of the HTML file
def head_template():
    with open(template_path / "head_template.txt", "r") as ff:
        template = ff.read()
    return template


# start the body, up to the table
def body_start_template():
    with open(template_path / "body_start_template.txt", "r") as ff:
        template = ff.read()
    today = str(date.today())
    return template.replace("{insert_date_here}", today)


# bottom of the HTML file
def body_end_template(table_keys=[]):
    with open(template_path / "body_end_template.txt", "r") as ff:
        template = ff.read()

    # if there's more than one table to sort, pass the keys
    if table_keys == []:
        pass
    else:
        sort_lines = "\n".join(f"$('#{k}').DataTable();" for k in table_keys)
        template = template.replace("$('#table').DataTable();", sort_lines)
    return template


# start the body, up to the table
def table_start_template(columns, table_name="table"):
    with open(template_path / "table_start_template.txt", "r") as ff:
        template = ff.read()
    template = template.replace('id="{replace_with_table_name}"', f'id="{table_name}"')
    column_props = 'class="align-middle"'
    column_text = "\n".join(f"<th {column_props}>{c}</th>" for c in columns)
    return template.replace("{replace_text_here_with_columns}", column_text)


# bottom of the HTML file
def table_end_template():
    with open(template_path / "table_end_template.txt", "r") as ff:
        template = ff.read()
    return template


def generate_table_rows(database):
    def df2html_row(row):
        text = "\n".join(f'<td class="align-middle">{i}</td>' for i in row)
        text = "<tr>" + text + "</tr>"
        return text

    row_data = ""
    for i, row in database.iterrows():
        row_data = row_data + "\n" + df2html_row(row)
    return row_data


def write_html(outfile, database):
    """write the visit info to html"""
    with open(outfile, "w") as ff:
        ff.write(head_template())

        ff.write(body_start_template())

        tables_gb = database.groupby("status")
        table_keys = sorted(tables_gb.groups.keys())
        print("Generating the following tables:")
        print("\t", ", ".join(table_keys))
        # make a separate table for each kind of visit status
        list_of_tables = []
        for key, group in tables_gb:
            group_dropna = group.dropna(how="all", axis=1)
            ff.write(f"<br><br>Status: {key.title()}<br>\n")
            table_name = f"table_{key}"
            ff.write(table_start_template(group_dropna.columns, table_name))
            list_of_tables.append(table_name)
            row_data = generate_table_rows(group_dropna)
            ff.write(row_data)
            ff.write(table_end_template())

        ff.write(body_end_template(list_of_tables))
