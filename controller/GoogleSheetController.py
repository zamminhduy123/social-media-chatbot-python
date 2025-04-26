import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

class GoogleSheetController:
    def __init__(self, creds_path, sheet_id, worksheet_name="Sheet1"):
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_file(creds_path, scopes=scope)
        client = gspread.authorize(credentials)
        self.sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)

    def find_row_by_cell_value(self, cell_value):
        try:
            cell = self.sheet.find(str(cell_value))
            return cell.row
        except gspread.exceptions.CellNotFound:
            return None
        
    def append_row(self, row):
        self.sheet.append_row(row)

    def update_row(self, row_number, new_row_values):
        cell_list = self.sheet.range(f"A{row_number}:{chr(65 + len(new_row_values) - 1)}{row_number}")
        for cell, value in zip(cell_list, new_row_values):
            cell.value = value
        self.sheet.update_cells(cell_list)

    def delete_row(self, row_number):
        self.sheet.delete_rows(row_number)