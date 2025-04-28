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
            if (cell is not None):
                return cell.row
            return None
        except gspread.exceptions.CellNotFound:
            return None
        
    def append_row(self, row):
        msg_id = row[2]
        row_number = self.find_row_by_cell_value(msg_id) 
        
        if (row_number is not None):
            self.update_row(row_number, row)
            return
        
        self.sheet.append_row(row)

    def update_row(self, row_number, new_row_values):
        cell_list = self.sheet.range(f"A{row_number}:{chr(65 + len(new_row_values) - 1)}{row_number}")
        for cell, value in zip(cell_list, new_row_values):
            cell.value = value
        self.sheet.update_cells(cell_list)

    def delete_row(self, row_number):
        self.sheet.delete_rows(row_number)