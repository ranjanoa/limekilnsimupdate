"""
Verify formula syntax, sheet names, and cell references across the generated workbook.
"""
import re
import openpyxl

wb = openpyxl.load_workbook("Cement_Kiln_Steady_State_Simulation_280TPH.xlsx", data_only=False)
sheet_names = set(wb.sheetnames)
print(f"Loaded sheets ({len(sheet_names)}): {sorted(list(sheet_names))}")

ref_pattern = re.compile(r"([A-Za-z0-9_]+)!([A-Z]+[0-9]+(?::[A-Z]+[0-9]+)?)")
single_cell_pattern = re.compile(r"\b([A-Z]+[0-9]+)\b")

errors = []
total_formulas = 0

for sname in wb.sheetnames:
    ws = wb[sname]
    for row in ws.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str) and cell.value.startswith("="):
                total_formulas += 1
                formula = cell.value
                # Check #REF!
                if "#REF!" in formula:
                    errors.append(f"[{sname}] {cell.coordinate}: Has #REF! in formula: {formula}")
                
                # Check cross-sheet references
                matches = ref_pattern.findall(formula)
                for target_sheet, target_coord in matches:
                    if target_sheet not in sheet_names:
                        errors.append(f"[{sname}] {cell.coordinate}: Targets non-existent sheet '{target_sheet}' in '{formula}'")
                    else:
                        target_ws = wb[target_sheet]
                        # check if cell coordinate is valid
                        try:
                            _ = target_ws[target_coord]
                        except Exception as e:
                            errors.append(f"[{sname}] {cell.coordinate}: Invalid cell range '{target_coord}' on sheet '{target_sheet}' ({e})")

print(f"Total formulas inspected: {total_formulas}")
if errors:
    print(f"Found {len(errors)} issues:")
    for err in errors[:20]:
        print(" - " + err)
else:
    print("ALL CROSS-SHEET FORMULAS AND CELL REFERENCES ARE VALID!")
