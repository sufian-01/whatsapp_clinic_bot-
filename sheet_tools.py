from langchain_core.tools import tool
from googleapiclient.discovery import build
from google_auth import get_credentials
from typing import List

creds = get_credentials()

sheet_service = build(
    "sheets",
    "v4",
    credentials=creds
)

@tool
def create_spreadsheet(title: str) -> dict:
    """
    Create a new Google Spreadsheet.

    Example:
    title="Expenses"
    """

    spreadsheet = {
        "properties": {
            "title": title
        }
    }

    result = sheet_service.spreadsheets().create(
        body=spreadsheet
    ).execute()

    return {
        "spreadsheet_id": result["spreadsheetId"],
        "title": result["properties"]["title"],
        "url": result["spreadsheetUrl"]
    }

@tool
def read_sheet(
    spreadsheet_id: str,
    range_name: str = "Sheet1!A1:Z100"
):
    """
    Read data from Google Sheet.

    Example:
    spreadsheet_id="xxxxx"
    range_name="Sheet1!A1:C20"
    """

    result = sheet_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    return result.get("values", [])

@tool
def append_row(
    spreadsheet_id: str,
    values: List[str]
):
    """
    Append one row.

    Example:

    values=["Apple",120,5]
    """

    body = {
        "values": [values]
    }

    sheet_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A1",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

    return "Row added successfully."

@tool
def update_cells(
    spreadsheet_id: str,
    range_name: str,
    values: list[str]
):
    """
    Update cells.

    Example:

    range_name="Sheet1!A2:C2"

    values=["Laptop",50000,1]
    """

    body = {
        "values": [values]
    }

    sheet_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()

    return "Sheet updated successfully."
@tool
def search_row_by_value(
    spreadsheet_id: str,
    column_name: str,
    value: str
):
    """
    Search rows by column value.

    Example:

    column_name="Name"

    value="Rahman"
    """

    result = sheet_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A1:Z1000"
    ).execute()

    rows = result.get("values", [])

    if not rows:
        return []

    headers = rows[0]

    if column_name not in headers:
        return f"Column '{column_name}' not found."

    column_index = headers.index(column_name)

    matched = []

    for i, row in enumerate(rows[1:], start=2):

        if len(row) > column_index:

            if row[column_index].lower() == value.lower():

                item = {
                    "row_number": i
                }

                for j, h in enumerate(headers):

                    item[h] = row[j] if j < len(row) else ""

                matched.append(item)

    return matched

@tool
def update_row_by_search(
    spreadsheet_id: str,
    search_column: str,
    search_value: str,
    update_column: str,
    new_value: str
):
    """
    Search a row and update one column.

    Example:

    search_column="Name"

    search_value="Rahman"

    update_column="Status"

    new_value="Selected"
    """

    result = sheet_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A1:Z1000"
    ).execute()

    rows = result.get("values", [])

    if not rows:
        return "Sheet is empty."

    headers = rows[0]

    if search_column not in headers:
        return "Search column not found."

    if update_column not in headers:
        return "Update column not found."

    search_index = headers.index(search_column)
    update_index = headers.index(update_column)

    for i, row in enumerate(rows[1:], start=2):

        if len(row) > search_index:

            if row[search_index].lower() == search_value.lower():

                cell = chr(65 + update_index) + str(i)

                sheet_service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"Sheet1!{cell}",
                    valueInputOption="USER_ENTERED",
                    body={
                        "values": [[new_value]]
                    }
                ).execute()

                return "Row updated successfully."

    return "No matching row found."

@tool
def delete_row_by_search(
    spreadsheet_id: str,
    search_column: str,
    search_value: str
):
    """
    Delete a row by searching a value.

    Example:

    search_column="Name"

    search_value="Rahman"
    """

    spreadsheet = sheet_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    sheet_id = spreadsheet["sheets"][0]["properties"]["sheetId"]

    result = sheet_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A1:Z1000"
    ).execute()

    rows = result.get("values", [])

    if not rows:
        return "Sheet is empty."

    headers = rows[0]

    if search_column not in headers:
        return "Column not found."

    search_index = headers.index(search_column)

    for i, row in enumerate(rows[1:], start=1):

        if len(row) > search_index:

            if row[search_index].lower() == search_value.lower():

                body = {
                    "requests": [
                        {
                            "deleteDimension": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "dimension": "ROWS",
                                    "startIndex": i,
                                    "endIndex": i + 1
                                }
                            }
                        }
                    ]
                }

                sheet_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()

                return "Row deleted successfully."

    return "No matching row found."
@tool
def list_sheet_names(
    spreadsheet_id: str
):
    """
    List all sheet names.
    """

    sheet = sheet_service.spreadsheets().get(
        spreadsheetId=spreadsheet_id
    ).execute()

    names = []

    for s in sheet["sheets"]:
        names.append(
            s["properties"]["title"]
        )

    return names