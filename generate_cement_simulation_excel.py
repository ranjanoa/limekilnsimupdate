"""
Script to generate Cement_Kiln_Steady_State_Simulation_280TPH.xlsx
A fully dynamic, rigorous steady-state flowsheet simulation workbook for the Cement Kiln Pyroprocessing System (Kiln 3 / Forno 3).
"""

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_simulation_workbook(filename="Cement_Kiln_Steady_State_Simulation_280TPH.xlsx"):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default blank sheet

    font_family = "Segoe UI"
    
    # Typography
    title_font = Font(name=font_family, size=15, bold=True, color="FFFFFF")
    subtitle_font = Font(name=font_family, size=9, italic=True, color="E0E6ED")
    sec_hdr_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
    tbl_hdr_font = Font(name=font_family, size=10, bold=True, color="FFFFFF")
    bold_font = Font(name=font_family, size=10, bold=True, color="1B365D")
    normal_font = Font(name=font_family, size=10, color="000000")
    italic_font = Font(name=font_family, size=9, italic=True, color="555555")
    kpi_val_font = Font(name=font_family, size=14, bold=True, color="0D3B66")
    kpi_lbl_font = Font(name=font_family, size=9, bold=True, color="5C6B73")

    # Fills
    navy_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
    steel_fill = PatternFill(start_color="2C5E8A", end_color="2C5E8A", fill_type="solid")
    input_fill = PatternFill(start_color="FFF9E6", end_color="FFF9E6", fill_type="solid")      # Warm Ivory / Input
    calc_fill = PatternFill(start_color="F2F6FA", end_color="F2F6FA", fill_type="solid")       # Soft Ice Blue / Calculated
    kpi_card_fill = PatternFill(start_color="EBF3FA", end_color="EBF3FA", fill_type="solid")   # KPI Card
    total_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")      # Table Totals
    good_fill = PatternFill(start_color="E2F0D9", end_color="E2F0D9", fill_type="solid")       # Green Pass / Highlight

    # Borders
    thin_line = Side(border_style="thin", color="B0C4DE")
    thick_line = Side(border_style="medium", color="1B365D")
    double_bottom = Side(border_style="double", color="1B365D")
    input_border_line = Side(border_style="medium", color="D4AC0D")

    table_border = Border(left=thin_line, right=thin_line, top=thin_line, bottom=thin_line)
    header_border = Border(left=thin_line, right=thin_line, top=thick_line, bottom=thick_line)
    total_border = Border(left=thin_line, right=thin_line, top=thin_line, bottom=double_bottom)
    input_border = Border(left=input_border_line, right=input_border_line, top=input_border_line, bottom=input_border_line)

    # Alignments
    left_align = Alignment(horizontal="left", vertical="center")
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")

    def apply_title_banner(ws, title, subtitle, max_col=10):
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_col)
        cell1 = ws.cell(row=1, column=1, value=title)
        cell1.font = title_font
        cell1.fill = navy_fill
        cell1.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[1].height = 26

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max_col)
        cell2 = ws.cell(row=2, column=1, value=subtitle)
        cell2.font = subtitle_font
        cell2.fill = navy_fill
        cell2.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[2].height = 18

    def auto_fit_columns(ws, min_col=1, max_col=None, pad=3):
        ws.views.sheetView[0].showGridLines = True
        if max_col is None:
            max_col = ws.max_column
        for col in range(min_col, max_col + 1):
            col_letter = get_column_letter(col)
            max_len = 0
            for row in range(3, ws.max_row + 1):
                val = ws.cell(row=row, column=col).value
                if val is not None:
                    sval = str(val)
                    if not sval.startswith("="):
                        max_len = max(max_len, len(sval))
                    else:
                        max_len = max(max_len, 10)
            ws.column_dimensions[col_letter].width = max(max_len + pad, 12)

    # =========================================================================
    # SHEET 1: Flowsheet_Dashboard
    # =========================================================================
    ws_dash = wb.create_sheet(title="Flowsheet_Dashboard")
    apply_title_banner(ws_dash, "CEMENT PYROPROCESSING STEADY-STATE FLOWSHEET SIMULATION",
                       "Kiln 3 / Forno 3 Engineering Baseline (Dual-String 4-Stage Preheater, Precalciner, Rotary Kiln, Grate Cooler)",
                       max_col=11)

    # Top KPI Cards
    kpis = [
        ("RAW MEAL FEED", "=Inputs_Setpoints!C6", "t/h (Dry Feed)", "B", "C", "0.00"),
        ("CLINKER PRODUCTION", "=Inputs_Setpoints!C25", "t/h (4,200 tpd)", "D", "E", "0.00"),
        ("SPECIFIC HEAT", "=Inputs_Setpoints!C10", "kcal/kg clinker", "F", "G", "0.0"),
        ("THERMAL POWER", "=Inputs_Setpoints!C29", "MWth (Total Fuel)", "H", "I", "0.00"),
        ("ALT. FUEL SUBST.", "=Inputs_Setpoints!C12", "% CDR Substitution", "J", "K", "0.0%")
    ]
    for title, formula, unit, col1, col2, num_fmt in kpis:
        c1_idx = openpyxl.utils.column_index_from_string(col1)
        c2_idx = openpyxl.utils.column_index_from_string(col2)
        ws_dash.merge_cells(start_row=4, start_column=c1_idx, end_row=4, end_column=c2_idx)
        ws_dash.merge_cells(start_row=5, start_column=c1_idx, end_row=5, end_column=c2_idx)
        ws_dash.merge_cells(start_row=6, start_column=c1_idx, end_row=6, end_column=c2_idx)
        
        c_top = ws_dash.cell(row=4, column=c1_idx, value=title)
        c_top.font = kpi_lbl_font
        c_top.fill = kpi_card_fill
        c_top.alignment = center_align

        c_val = ws_dash.cell(row=5, column=c1_idx, value=formula)
        c_val.font = kpi_val_font
        c_val.fill = kpi_card_fill
        c_val.alignment = center_align
        c_val.number_format = num_fmt

        c_sub = ws_dash.cell(row=6, column=c1_idx, value=unit)
        c_sub.font = italic_font
        c_sub.fill = kpi_card_fill
        c_sub.alignment = center_align

        for r in range(4, 7):
            for c in range(c1_idx, c2_idx + 1):
                ws_dash.cell(row=r, column=c).border = table_border

    # Flowsheet ASCII Diagram
    ws_dash.cell(row=8, column=2, value="PROCESS FLOW DIAGRAM & KEY STREAM ANNOTATIONS").font = bold_font
    diagram_lines = [
        "                     [RAW MEAL FEED: =Inputs_Setpoints!C6 t/h]",
        "                                  |          |",
        "                         50% (140 t/h)      50% (140 t/h)",
        "                                  v          v",
        "                         +------------+  +------------+",
        "                         | STRING N   |  | STRING P   |  <--- Gas Exit: 413 °C, -56 mbar (K3T16/K3P02)",
        "                         | Cycl. 1N   |  | Cycl. 1P   |       Top Flue Gas Flow: 291,500 Nm3/h (385.2 t/h)",
        "                         +------------+  +------------+",
        "                               |               |",
        "                         +------------+  +------------+",
        "                         | Cycl. 2N   |  | Cycl. 2P   |  <--- Gas: 608 - 637 °C",
        "                         +------------+  +------------+",
        "                               \\              /",
        "                                v            v",
        "                         +----------------------------+",
        "                         |   CYCLONE STAGE 3          |  <--- Gas: 762 °C (K3T52)",
        "                         +----------------------------+",
        "                               /              \\",
        "                           40% /              \\ 60%",
        "                              v                v",
        "                         +------------+  +------------+",
        "                         | Cycl. 4N   |  | Cycl. 4P   |",
        "                         +------------+  +------------+",
        "                              |                |",
        "                              | Precalcined    | Precalcined",
        "                              v Meal           v Meal",
        "  +-------------------------------------------------------------------------------+",
        "  | PRECALCINER & MIXING CHAMBER (PC)                                             |",
        "  |  - Fuel Thermal Input: 307.4 GJ/h (85.4 MWth) [54.1% Plant Thermal Split]     |",
        "  |  - Fuels Fired: Petcoke 3.68 t/h + CDR / RDF 10.66 t/h                        |",
        "  |  - Tertiary Air: 105,000 Nm3/h (135.8 t/h) @ 862 °C (K3T60)                   |",
        "  |  - Decarbonation Degree: 92.5% @ 907 °C (K3T62A)                              |",
        "  +-------------------------------------------------------------------------------+",
        "                              | Precalcined Meal (182.4 t/h @ 880-907 °C)",
        "                              v",
        "  +-------------------------------------------------------------------------------+",
        "  | ROTARY KILN (FORNO ROTATIVO - 4.8m Outer Dia x 70m Length)                     |",
        "  |  - Kiln Speed: 3.79 rpm (L3S01), Current: 254 A (L3I01), Filling: 10.96%      |",
        "  |  - Main Burner Heat: 260.8 GJ/h (72.5 MWth) [45.9% Plant Thermal Split]       |",
        "  |  - Secondary Air: 78,000 Nm3/h (100.9 t/h) @ 1000 °C (L3T305)                 |",
        "  |  - Sintering Bed: 1450 °C (TERMO), Kiln Exit Flue Gas: 1050 °C                |",
        "  |  - Clinker Free Lime (CaO_free): 1.30 wt% (Cal Livre)                         |",
        "  +-------------------------------------------------------------------------------+",
        "                              | Molten Clinker @ 1450 °C (175.0 t/h)",
        "                              v",
        "  +-------------------------------------------------------------------------------+",
        "  | CLINKER GRATE COOLER (ARREFECEDOR DE GRELHA)                                  |",
        "  |  - Clinker Production Rate: 175.0 t/h (4,200 tpd)                             |",
        "  |  - Total Cooling Air Inflow: 330,000 Nm3/h (426.7 t/h) @ 25 °C                |",
        "  |  - Secondary Air to Kiln: 78,000 Nm3/h @ 1000 °C (Heat Recup: 106.9 GJ/h)     |",
        "  |  - Tertiary Air to PC: 105,000 Nm3/h @ 862 °C (Heat Recup: 122.9 GJ/h)       |",
        "  |  - Cooler Vent Air to Dedusting Filter: 147,000 Nm3/h @ 258 °C (51.8 GJ/h)    |",
        "  |  - Cooled Clinker Discharge: 175.0 t/h @ 90 °C                                |",
        "  |  - Thermal Recuperation Efficiency: 77.38%                                    |",
        "  +-------------------------------------------------------------------------------+"
    ]
    diag_font = Font(name="Consolas", size=9, color="1B365D")
    diag_fill = PatternFill(start_color="F4F7FA", end_color="F4F7FA", fill_type="solid")
    for idx, dline in enumerate(diagram_lines):
        r = 10 + idx
        ws_dash.merge_cells(start_row=r, start_column=2, end_row=r, end_column=11)
        c = ws_dash.cell(row=r, column=2, value=dline)
        c.font = diag_font
        c.fill = diag_fill
        c.alignment = left_align
        ws_dash.row_dimensions[r].height = 15

    # Overall Battery Limits Audit Table
    r_start = 10 + len(diagram_lines) + 2
    ws_dash.cell(row=r_start, column=2, value="BATTERY LIMIT OVERALL BALANCE AUDIT").font = bold_font
    
    headers_audit = ["Balance Dimension", "Total Inflow", "Total Outflow", "Difference (Delta)", "Closure Error %", "Audit Status"]
    for i, h in enumerate(headers_audit):
        c = ws_dash.cell(row=r_start + 1, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    # Mass Audit Row
    r_mass = r_start + 2
    ws_dash.cell(row=r_mass, column=2, value="Total Plant Mass (t/h)").font = bold_font
    ws_dash.cell(row=r_mass, column=3, value="=Overall_Mass_Heat_Balance!D13").number_format = "0.00"
    ws_dash.cell(row=r_mass, column=4, value="=Overall_Mass_Heat_Balance!G13").number_format = "0.00"
    ws_dash.cell(row=r_mass, column=5, value="=C" + str(r_mass) + "-D" + str(r_mass)).number_format = "0.00"
    ws_dash.cell(row=r_mass, column=6, value="=ABS(E" + str(r_mass) + ")/C" + str(r_mass)).number_format = "0.00%"
    ws_dash.cell(row=r_mass, column=7, value='=IF(F' + str(r_mass) + '<0.02,"PASSED (EXCELLENT)","CHECK I/O")').font = bold_font
    for c in range(2, 8):
        cell = ws_dash.cell(row=r_mass, column=c)
        cell.border = table_border
        cell.fill = calc_fill

    # Thermal Audit Row
    r_heat = r_start + 3
    ws_dash.cell(row=r_heat, column=2, value="Total Plant Energy (GJ/h)").font = bold_font
    ws_dash.cell(row=r_heat, column=3, value="=Overall_Mass_Heat_Balance!C25").number_format = "0.00"
    ws_dash.cell(row=r_heat, column=4, value="=Overall_Mass_Heat_Balance!F25").number_format = "0.00"
    ws_dash.cell(row=r_heat, column=5, value="=C" + str(r_heat) + "-D" + str(r_heat)).number_format = "0.00"
    ws_dash.cell(row=r_heat, column=6, value="=ABS(E" + str(r_heat) + ")/C" + str(r_heat)).number_format = "0.00%"
    ws_dash.cell(row=r_heat, column=7, value='=IF(F' + str(r_heat) + '<0.01,"PASSED (CONSERVED)","CHECK LOSSES")').font = bold_font
    for c in range(2, 8):
        cell = ws_dash.cell(row=r_heat, column=c)
        cell.border = table_border
        cell.fill = calc_fill

    # =========================================================================
    # SHEET 2: Inputs_Setpoints
    # =========================================================================
    ws_inp = wb.create_sheet(title="Inputs_Setpoints")
    apply_title_banner(ws_inp, "PLANT OPERATING INPUTS, SETPOINTS & DERIVED KPIS",
                       "Nominal Base Case: 280.0 t/h Raw Meal (Yellow cells are user-adjustable simulation inputs)",
                       max_col=8)

    ws_inp.cell(row=4, column=2, value="1. PROCESS FEED & OPERATIONAL SETPOINTS (USER INPUTS)").font = sec_hdr_font
    ws_inp.cell(row=4, column=2).fill = navy_fill
    ws_inp.merge_cells("B4:F4")

    input_defs = [
        ("Raw Meal Feed Rate (Dry Basis)", 280.0, "t/h", "Mass flow of dry meal fed to elevator (K3F07)", "0.00"),
        ("Raw Meal Moisture Content", 0.005, "% wt", "Moisture in raw meal before preheater (0.5%)", "0.00%"),
        ("Raw Meal Loss on Ignition (LOI)", 0.3533, "% wt", "Total carbonate decarbonation gasification (35.33%)", "0.00%"),
        ("Meal-to-Clinker Factor", 1.600, "kg/kg", "Ratio of raw meal required per kg clinker", "0.000"),
        ("Target Specific Heat Consumption", 775.6, "kcal/kg", "Specific thermal consumption per kg clinker", "0.0"),
        ("Precalciner Thermal Split", 0.541, "%", "Fraction of fuel energy delivered to Precalciner (54.1%)", "0.00%"),
        ("Alternative Fuel (CDR) Substitution Rate", 0.415, "%", "Thermal substitution of CDR in total fuel (%ST = 41.5%)", "0.00%"),
        ("Precalciner Decarbonation Degree", 0.925, "%", "Fraction of CaCO3 decomposed in Precalciner (92.5%)", "0.00%"),
        ("Clinker Cooler Discharge Temp", 90.0, "°C", "Temperature of cooled clinker sent to transport silo", "0.0"),
        ("Kiln Sintering Bed Temperature", 1450.0, "°C", "Burning zone bed temperature pyrometer (TERMO)", "0.0"),
        ("Kiln Inlet Flue Gas Temperature", 1050.0, "°C", "Kiln back-end smoke chamber gas temperature", "0.0"),
        ("Precalciner Upper Exit Temperature", 907.0, "°C", "Gas/meal suspension leaving PC chamber (K3T62A)", "0.0"),
        ("Preheater Top Exhaust Gas Temp", 413.0, "°C", "Gas leaving top cyclones 1N/1P manifold (K3T16)", "0.0"),
        ("Secondary Air Temperature", 1000.0, "°C", "Secondary combustion air entering kiln from cooler (L3T305)", "0.0"),
        ("Tertiary Air Temperature", 862.0, "°C", "Tertiary combustion air to precalciner (K3T60)", "0.0"),
        ("Cooler Excess Vent Air Temp", 258.0, "°C", "Excess cooler air vented to dedusting filter (L3T324)", "0.0"),
        ("Clinker Free Lime (CaO_free)", 0.0130, "% wt", "Target free lime in produced clinker (Cal Livre = 1.30%)", "0.00%")
    ]

    inp_hdrs = ["Parameter Description", "Setpoint / Input Value", "Engineering Unit", "Process Details & Instrumentation", "Cell Ref"]
    for i, h in enumerate(inp_hdrs):
        c = ws_inp.cell(row=5, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    for idx, (label, val, unit, desc, num_fmt) in enumerate(input_defs):
        r = 6 + idx
        ws_inp.cell(row=r, column=2, value=label).font = bold_font
        c_val = ws_inp.cell(row=r, column=3, value=val)
        c_val.font = bold_font
        c_val.fill = input_fill
        c_val.border = input_border
        c_val.alignment = right_align
        c_val.number_format = num_fmt

        ws_inp.cell(row=r, column=4, value=unit).alignment = center_align
        ws_inp.cell(row=r, column=5, value=desc).alignment = left_align
        ws_inp.cell(row=r, column=6, value=f"C{r}").font = italic_font
        for c in [2, 4, 5, 6]:
            ws_inp.cell(row=r, column=c).border = table_border

    # Derived KPIs Section
    r_kpi_start = 23
    ws_inp.cell(row=r_kpi_start, column=2, value="2. DERIVED PRODUCTION & ENERGY KPIS (FORMULA CALCULATED)").font = sec_hdr_font
    ws_inp.cell(row=r_kpi_start, column=2).fill = navy_fill
    ws_inp.merge_cells(f"B{r_kpi_start}:F{r_kpi_start}")

    kpi_defs = [
        ("Clinker Production Rate (Hourly)", "=C6/C9", "t/h", "Hourly clinker clinkerization yield", "0.00"),
        ("Clinker Production Rate (Daily)", "=C25*24", "t/day (tpd)", "Nominal daily plant capacity", "0.0"),
        ("Target Specific Heat in SI Units", "=C10*4.1868", "kJ/kg clinker", "Specific heat converted (1 kcal = 4.1868 kJ)", "0.0"),
        ("Total Thermal Fuel Power (GJ/h)", "=C25*C27/1000", "GJ/h", "Total plant fuel energy input rate", "0.00"),
        ("Total Thermal Fuel Power (MWth)", "=C28/3.6", "MWth", "Thermal power (1 MW = 3.6 GJ/h)", "0.00"),
        ("Precalciner Thermal Energy Rate", "=C28*C11", "GJ/h", "Heat delivered to precalciner burner", "0.00"),
        ("Kiln Main Burner Thermal Rate", "=C28*(1-C11)", "GJ/h", "Heat delivered to rotary kiln burner", "0.00"),
        ("Precalciner Thermal Power (MWth)", "=C30/3.6", "MWth", "Precalciner burner thermal power", "0.00"),
        ("Kiln Main Burner Power (MWth)", "=C31/3.6", "MWth", "Main burner thermal power", "0.00"),
        ("Annual Clinker Capacity (330 Days)", "=C26*330", "t/year", "Annual capacity at 330 operating days/yr", "#,##0"),
        ("Cooler Heat Recuperation Efficiency", "=(Clinker_Cooler_Balance!E20+Clinker_Cooler_Balance!E21-Clinker_Cooler_Balance!E19)/(Clinker_Cooler_Balance!E16-Clinker_Cooler_Balance!E17)", "%", "Recuperated enthalpy / clinker heat released", "0.00%")
    ]

    for i, h in enumerate(inp_hdrs[:4]):
        c = ws_inp.cell(row=r_kpi_start + 1, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    for idx, (label, formula, unit, desc, num_fmt) in enumerate(kpi_defs):
        r = r_kpi_start + 2 + idx  # Rows 26 to 36
        ws_inp.cell(row=r, column=2, value=label).font = bold_font
        c_val = ws_inp.cell(row=r, column=3, value=formula)
        c_val.font = bold_font
        c_val.fill = calc_fill
        c_val.border = table_border
        c_val.alignment = right_align
        c_val.number_format = num_fmt

        ws_inp.cell(row=r, column=4, value=unit).alignment = center_align
        ws_inp.cell(row=r, column=5, value=desc).alignment = left_align
        for c in [2, 4, 5]:
            ws_inp.cell(row=r, column=c).border = table_border

    # =========================================================================
    # SHEET 3: RawMeal_Clinker
    # =========================================================================
    ws_chem = wb.create_sheet(title="RawMeal_Clinker")
    apply_title_banner(ws_chem, "RAW MEAL & CLINKER CHEMICAL & MINERALOGICAL SIMULATION",
                       "Stoichiometric Decarbonation, Loss on Ignition, and Bogue Mineral Phase Analysis",
                       max_col=8)

    ws_chem.cell(row=4, column=2, value="1. RAW MEAL ASSAY & COMPONENT MASS FLOWS").font = sec_hdr_font
    ws_chem.cell(row=4, column=2).fill = navy_fill
    ws_chem.merge_cells("B4:G4")

    raw_chem_headers = ["Chemical Constituent", "Formula", "Dry wt%", "Mass Flow @ Nominal Feed (t/h)", "Function / Reaction in Process"]
    for i, h in enumerate(raw_chem_headers):
        c = ws_chem.cell(row=5, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    raw_components = [
        ("Calcium Carbonate", "CaCO3", 0.7685, "=Inputs_Setpoints!$C$6*D6", "Endothermic calcination: CaCO3 -> CaO + CO2 (dH = +1782 kJ/kg)"),
        ("Magnesium Carbonate", "MgCO3", 0.0280, "=Inputs_Setpoints!$C$6*D7", "Endothermic calcination: MgCO3 -> MgO + CO2"),
        ("Silicon Dioxide", "SiO2", 0.1350, "=Inputs_Setpoints!$C$6*D8", "Reacts with CaO to form Belite (C2S) and Alite (C3S)"),
        ("Aluminum Oxide", "Al2O3", 0.0335, "=Inputs_Setpoints!$C$6*D9", "Reacts with CaO to form Tricalcium Aluminate (C3A)"),
        ("Iron Oxide", "Fe2O3", 0.0210, "=Inputs_Setpoints!$C$6*D10", "Forms Tetracalcium Aluminoferrite flux (C4AF)"),
        ("Minor Volatiles (SO3, K2O, Na2O, Cl)", "Minor", 0.0140, "=Inputs_Setpoints!$C$6*D11", "Circulating volatile bypass loop elements"),
    ]

    for idx, (name, fmla, wt, flow_fmla, notes) in enumerate(raw_components):
        r = 6 + idx
        ws_chem.cell(row=r, column=2, value=name).font = normal_font
        ws_chem.cell(row=r, column=3, value=fmla).font = italic_font
        c_wt = ws_chem.cell(row=r, column=4, value=wt)
        c_wt.number_format = "0.00%"
        c_wt.alignment = right_align
        c_flw = ws_chem.cell(row=r, column=5, value=flow_fmla)
        c_flw.number_format = "0.00"
        c_flw.alignment = right_align
        ws_chem.cell(row=r, column=6, value=notes).font = italic_font
        for c in range(2, 7):
            ws_chem.cell(row=r, column=c).border = table_border

    # Total row for raw meal
    r_raw_tot = 12
    ws_chem.cell(row=r_raw_tot, column=2, value="Total Dry Raw Meal").font = bold_font
    ws_chem.cell(row=r_raw_tot, column=3, value="").border = total_border
    c_wt_tot = ws_chem.cell(row=r_raw_tot, column=4, value="=SUM(D6:D11)")
    c_wt_tot.number_format = "0.00%"
    c_wt_tot.alignment = right_align
    c_fl_tot = ws_chem.cell(row=r_raw_tot, column=5, value="=SUM(E6:E11)")
    c_fl_tot.number_format = "0.00"
    c_fl_tot.alignment = right_align
    ws_chem.cell(row=r_raw_tot, column=6, value="Baseline feed to kiln line").font = bold_font
    for c in range(2, 7):
        cell = ws_chem.cell(row=r_raw_tot, column=c)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = total_border

    # Decarbonation Stoichiometry Section
    r_decarb_start = 14
    ws_chem.cell(row=r_decarb_start, column=2, value="2. DECARBONATION STOICHIOMETRY & PROCESS CO2 EMISSION").font = sec_hdr_font
    ws_chem.cell(row=r_decarb_start, column=2).fill = navy_fill
    ws_chem.merge_cells(f"B{r_decarb_start}:G{r_decarb_start}")

    decarb_rows = [
        ("CO2 from CaCO3 Calcination (M_CO2/M_CaCO3 = 44.01/100.09)", "=E6*(44.01/100.09)", "t/h", "Theoretical complete CaCO3 decarbonation gas"),
        ("CO2 from MgCO3 Calcination (M_CO2/M_MgCO3 = 44.01/84.31)", "=E7*(44.01/84.31)", "t/h", "Theoretical complete MgCO3 decarbonation gas"),
        ("Total Potential Decarbonation CO2 (100% calcined)", "=C16+C17", "t/h", "Total chemical process CO2 in raw meal (35.25% of feed)"),
        ("Precalciner Decarbonation (92.5% of total CO2)", "=C18*Inputs_Setpoints!$C$13", "t/h", "Process CO2 released inside Precalciner vessel"),
        ("Rotary Kiln Decarbonation (Residual 7.5% of CO2)", "=C18*(1-Inputs_Setpoints!$C$13)", "t/h", "Process CO2 released inside Rotary Kiln bed"),
        ("Theoretical Heat of Calcination (dH = 3,960 kJ/kg CO2)", "=C18*1000*3960/1000000", "GJ/h", "Endothermic heat requirement for decarbonation"),
        ("Theoretical Calcination Power", "=C21/3.6", "MWth", "Theoretical calcination power requirement")
    ]

    for i, h in enumerate(["Reaction / Mass Parameter", "Formula Value", "Unit", "Thermodynamic Description"]):
        c = ws_chem.cell(row=r_decarb_start + 1, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    for idx, (label, formula, unit, desc) in enumerate(decarb_rows):
        r = r_decarb_start + 2 + idx  # Rows 16 to 22
        ws_chem.cell(row=r, column=2, value=label).font = bold_font
        c_val = ws_chem.cell(row=r, column=3, value=formula)
        c_val.font = bold_font
        c_val.fill = calc_fill
        c_val.border = table_border
        c_val.alignment = right_align
        c_val.number_format = "0.00"

        ws_chem.cell(row=r, column=4, value=unit).alignment = center_align
        ws_chem.cell(row=r, column=5, value=desc).alignment = left_align
        for c in [2, 4, 5]:
            ws_chem.cell(row=r, column=c).border = table_border

    # Clinker Mineralogy (Bogue)
    r_bogue_start = 24
    ws_chem.cell(row=r_bogue_start, column=2, value="3. CLINKER OXIDE & BOGUE MINERAL PHASE ANALYSIS").font = sec_hdr_font
    ws_chem.cell(row=r_bogue_start, column=2).fill = navy_fill
    ws_chem.merge_cells(f"B{r_bogue_start}:G{r_bogue_start}")

    bogue_rows = [
        ("Total Calcium Oxide (CaO_total)", 0.6550, "=Inputs_Setpoints!$C$25*C26", "Total lime content in clinker"),
        ("Free Lime (CaO_free)", "=Inputs_Setpoints!$C$22", "=Inputs_Setpoints!$C$25*C27", "Uncombined free lime (Target 1.30%)"),
        ("Combined Calcium Oxide (CaO_comb)", "=C26-C27", "=Inputs_Setpoints!$C$25*C28", "Lime combined in silicates and aluminates"),
        ("Silicon Dioxide (SiO2)", 0.2160, "=Inputs_Setpoints!$C$25*C29", "Silica oxide in clinker"),
        ("Aluminum Oxide (Al2O3)", 0.0536, "=Inputs_Setpoints!$C$25*C30", "Alumina oxide in clinker"),
        ("Iron Oxide (Fe2O3)", 0.0336, "=Inputs_Setpoints!$C$25*C31", "Iron oxide in clinker"),
        ("Alite (C3S = 4.071*CaO_comb - 7.6*SiO2 - 6.718*Al2O3 - 1.43*Fe2O3)", 0.6120, "=Inputs_Setpoints!$C$25*C32", "Primary rapid hardening mineral phase (Alite)"),
        ("Belite (C2S = 2.867*SiO2 - 0.7544*C3S)", 0.1650, "=Inputs_Setpoints!$C$25*C33", "Late strength development phase (Belite)"),
        ("Tricalcium Aluminate (C3A = 2.65*Al2O3 - 1.692*Fe2O3)", 0.0860, "=Inputs_Setpoints!$C$25*C34", "Fast setting phase (Aluminate)"),
        ("Tetracalcium Aluminoferrite (C4AF = 3.043*Fe2O3)", 0.1020, "=Inputs_Setpoints!$C$25*C35", "Flux / liquid sintering phase (Ferrite)"),
        ("Minor Oxides & Sulfates (MgO, SO3, Alkalis)", 0.0220, "=Inputs_Setpoints!$C$25*C36", "Volatiles and minor components"),
    ]

    for i, h in enumerate(["Oxide / Mineral Phase", "Mass Fraction (wt%)", "Mass Flow Rate (t/h)", "Mineralogical Significance"]):
        c = ws_chem.cell(row=r_bogue_start + 1, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    for idx, (label, wt_fmla, flow_fmla, desc) in enumerate(bogue_rows):
        r = r_bogue_start + 2 + idx  # Rows 26 to 36
        ws_chem.cell(row=r, column=2, value=label).font = bold_font
        c_wt = ws_chem.cell(row=r, column=3, value=wt_fmla)
        c_wt.font = bold_font
        c_wt.alignment = right_align
        c_wt.number_format = "0.00%"
        c_wt.border = table_border

        c_flow = ws_chem.cell(row=r, column=4, value=flow_fmla)
        c_flow.font = bold_font
        c_flow.alignment = right_align
        c_flow.number_format = "0.00"
        c_flow.border = table_border
        c_flow.fill = calc_fill

        ws_chem.cell(row=r, column=5, value=desc).alignment = left_align
        ws_chem.cell(row=r, column=5).border = table_border

    # =========================================================================
    # SHEET 4: Fuels_Combustion
    # =========================================================================
    ws_fuel = wb.create_sheet(title="Fuels_Combustion")
    apply_title_banner(ws_fuel, "FUELS CHARACTERIZATION, COMBUSTION STOICHIOMETRY & SPLITS",
                       "Petcoke, Alternative Fuel (CDR / RDF), and Heavy Fuel Oil Specifications",
                       max_col=9)

    ws_fuel.cell(row=4, column=2, value="1. FUEL SUITE PROPERTIES & THERMOCHEMICAL DATA").font = sec_hdr_font
    ws_fuel.cell(row=4, column=2).fill = navy_fill
    ws_fuel.merge_cells("B4:H4")

    fuel_hdrs = ["Fuel Type", "Lower Heating Value (MJ/kg)", "LHV (kcal/kg)", "Ash Content (wt%)", "Moisture (wt%)", "Carbon (C wt%)", "Hydrogen (H wt%)"]
    for i, h in enumerate(fuel_hdrs):
        c = ws_fuel.cell(row=5, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    fuel_specs = [
        ("Pulverized Petroleum Coke (Petcoke)", 31.40, 7500.0, 0.008, 0.007, 0.865, 0.038),
        ("CDR / Refuse Derived Fuel (RDF)", 18.00, 4300.0, 0.113, 0.090, 0.480, 0.065),
        ("Heavy Fuel Oil (Burner Trim)", 41.80, 10000.0, 0.001, 0.005, 0.850, 0.115)
    ]

    for idx, (name, lhv_mj, lhv_kcal, ash, moist, c_frac, h_frac) in enumerate(fuel_specs):
        r = 6 + idx  # Rows 6 to 8
        ws_fuel.cell(row=r, column=2, value=name).font = bold_font
        ws_fuel.cell(row=r, column=3, value=lhv_mj).number_format = "0.00"
        ws_fuel.cell(row=r, column=4, value=lhv_kcal).number_format = "0.0"
        ws_fuel.cell(row=r, column=5, value=ash).number_format = "0.0%"
        ws_fuel.cell(row=r, column=6, value=moist).number_format = "0.0%"
        ws_fuel.cell(row=r, column=7, value=c_frac).number_format = "0.0%"
        ws_fuel.cell(row=r, column=8, value=h_frac).number_format = "0.0%"
        for col_i in range(2, 9):
            ws_fuel.cell(row=r, column=col_i).border = table_border

    # Fuel Allocation Table
    ws_fuel.cell(row=11, column=2, value="2. PROCESS FUEL CONSUMPTION RATES & THERMAL ALLOCATION").font = sec_hdr_font
    ws_fuel.cell(row=11, column=2).fill = navy_fill
    ws_fuel.merge_cells("B11:H11")

    dist_hdrs = ["Firing Location / Stream", "Fuel Type Assigned", "Thermal Split (GJ/h)", "Thermal Split (MW)", "Mass Flow Rate (t/h)", "HMI Feeder Tag", "Notes"]
    for i, h in enumerate(dist_hdrs):
        c = ws_fuel.cell(row=12, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    fuel_allocation = [
        ("Precalciner Alternative Fuel", "CDR (Lines 1 & 2)", "=Inputs_Setpoints!$C$28*Inputs_Setpoints!$C$12*(191.88/235.84)", "=D13/3.6", "=D13/C7", "Z3N218 & Z3N213", "Line 1: 5.33 t/h, Line 2: 5.33 t/h"),
        ("Precalciner Solid Fossil Fuel", "Petcoke", "=Inputs_Setpoints!$C$30-D13", "=D14/3.6", "=D14/C6", "S3F04", "Controlled to maintain 907 °C exit"),
        ("Precalciner Total Heat Input", "Combined PC Fuels", "=D13+D14", "=E13+E14", "=F13+F14", "Precalciner Subtotal", "54.1% Plant Thermal Split"),
        ("Rotary Kiln Alternative Fuel", "CDR (Burner Feeder)", "=Inputs_Setpoints!$C$28*Inputs_Setpoints!$C$12*(43.92/235.84)", "=D16/3.6", "=D16/C7", "Z3N412", "Solid AF pneumatically blown"),
        ("Rotary Kiln Heavy Oil Trim", "Heavy Fuel Oil", 24.04, "=D17/3.6", "=D17/C8", "L3F03", "Flow = 605 l/h @ 0.95 kg/dm3"),
        ("Rotary Kiln Solid Fossil Fuel", "Petcoke", "=Inputs_Setpoints!$C$31-D16-D17", "=D18/3.6", "=D18/C6", "L3F200", "Main flame shaping solid fuel"),
        ("Rotary Kiln Total Heat Input", "Combined Kiln Fuels", "=D16+D17+D18", "=E16+E17+E18", "=F16+F17+F18", "Main Burner Subtotal", "45.9% Plant Thermal Split"),
    ]

    for idx, (loc, f_type, th_gj, th_mw, mass_fmla, tag, notes) in enumerate(fuel_allocation):
        r = 13 + idx  # Rows 13 to 19
        ws_fuel.cell(row=r, column=2, value=loc).font = bold_font
        ws_fuel.cell(row=r, column=3, value=f_type).font = normal_font
        c_gj = ws_fuel.cell(row=r, column=4, value=th_gj)
        c_gj.font = bold_font
        c_gj.number_format = "0.00"
        c_mw = ws_fuel.cell(row=r, column=5, value=th_mw)
        c_mw.font = bold_font
        c_mw.number_format = "0.00"
        c_mass = ws_fuel.cell(row=r, column=6, value=mass_fmla)
        c_mass.font = bold_font
        c_mass.number_format = "0.00"
        c_mass.fill = calc_fill
        ws_fuel.cell(row=r, column=7, value=tag).alignment = center_align
        ws_fuel.cell(row=r, column=8, value=notes).font = italic_font
        for c in range(2, 9):
            ws_fuel.cell(row=r, column=c).border = table_border

    # Grand Total Fuels
    r_f_tot = 20
    ws_fuel.cell(row=r_f_tot, column=2, value="TOTAL PLANT FUEL FIRING").font = bold_font
    ws_fuel.cell(row=r_f_tot, column=3, value="ALL FUELS COMBINED").font = bold_font
    ws_fuel.cell(row=r_f_tot, column=4, value="=D15+D19").number_format = "0.00"
    ws_fuel.cell(row=r_f_tot, column=5, value="=E15+E19").number_format = "0.00"
    ws_fuel.cell(row=r_f_tot, column=6, value="=F15+F19").number_format = "0.00"
    ws_fuel.cell(row=r_f_tot, column=7, value="TOTAL FEEDERS").font = bold_font
    ws_fuel.cell(row=r_f_tot, column=8, value="Conserves total fuel energy").font = bold_font
    for c in range(2, 9):
        cell = ws_fuel.cell(row=r_f_tot, column=c)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = total_border

    # Fuel summary references
    ws_fuel.cell(row=28, column=2, value="SUMMARY REFERENCES FOR SIMULATION ENGINE:").font = bold_font
    ref_labels = [
        ("Total CDR Alternative Fuel (t/h)", "=F13+F16"),
        ("Total Petcoke (t/h)", "=F14+F18"),
        ("Total Heavy Fuel Oil (t/h)", "=F17"),
        ("Total Fuel Mass (t/h)", "=F20")
    ]
    for idx, (rlbl, rfmla) in enumerate(ref_labels):
        ws_fuel.cell(row=29 + idx, column=2, value=rlbl).font = normal_font
        c = ws_fuel.cell(row=29 + idx, column=3, value=rfmla)
        c.font = bold_font
        c.number_format = "0.00"

    # =========================================================================
    # SHEET 5: Clinker_Cooler_Balance
    # =========================================================================
    ws_clr = wb.create_sheet(title="Clinker_Cooler_Balance")
    apply_title_banner(ws_clr, "CLINKER GRATE COOLER MASS & HEAT RECUPERATION BALANCE",
                       "Receives Clinker @ 1450 °C, Secondary Air @ 1000 °C, Tertiary Air @ 862 °C, Clinker Out @ 90 °C",
                       max_col=8)

    ws_clr.cell(row=4, column=2, value="1. CLINKER GRATE COOLER AIR & MASS BALANCE").font = sec_hdr_font
    ws_clr.cell(row=4, column=2).fill = navy_fill
    ws_clr.merge_cells("B4:H4")

    clr_mass_hdrs = ["Stream Identification", "Phase", "Norm. Volume (Nm3/h)", "Mass Flow (t/h)", "Temp (°C)", "Static Press (mbar)", "Process Role"]
    for i, h in enumerate(clr_mass_hdrs):
        c = ws_clr.cell(row=5, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    clr_streams = [
        ("IN: Hot Clinker Discharge from Kiln", "Solid", "-", "=Inputs_Setpoints!$C$25", 1450.0, -0.3, "Molten clinker feed from kiln hood"),
        ("IN: Cooling Ambient Air Fans (Battery)", "Gas", 330000.0, "=D7*1.293/1000", 25.0, 65.0, "Fans L3M330, L3M335, L3M207, L3M433, L3M209"),
        ("OUT: Secondary Combustion Air to Kiln", "Gas", 78000.0, "=D9*1.293/1000", "=Inputs_Setpoints!$C$19", -0.3, "High-temp secondary air to kiln hood"),
        ("OUT: Tertiary Air to Precalciner Duct", "Gas", 105000.0, "=D10*1.293/1000", "=Inputs_Setpoints!$C$20", -3.6, "Recuperated combustion air to PC"),
        ("OUT: Cooler Excess Vent Air to Baghouse", "Gas", "=D7-D9-D10", "=D11*1.293/1000", "=Inputs_Setpoints!$C$21", -4.6, "Excess air discharged via filter fan L3M366"),
        ("OUT: Cooled Clinker Discharge to Silo", "Solid", "-", "=Inputs_Setpoints!$C$25", "=Inputs_Setpoints!$C$14", 0.0, "Discharged to clinker conveyor and silo"),
    ]

    # Rows 6, 7 (Inflows), Rows 9, 10, 11, 12 (Outflows)
    row_map_clr = [6, 7, 9, 10, 11, 12]
    for idx, r in enumerate(row_map_clr):
        sname, sphase, svol, smass, stemp, spress, srole = clr_streams[idx]
        ws_clr.cell(row=r, column=2, value=sname).font = bold_font
        ws_clr.cell(row=r, column=3, value=sphase).alignment = center_align
        
        c_vol = ws_clr.cell(row=r, column=4, value=svol)
        c_vol.number_format = "#,##0" if isinstance(svol, float) or str(svol).startswith("=") else "@"
        c_vol.alignment = right_align

        c_mass = ws_clr.cell(row=r, column=5, value=smass)
        c_mass.number_format = "0.00"
        c_mass.alignment = right_align

        c_temp = ws_clr.cell(row=r, column=6, value=stemp)
        c_temp.number_format = "0.0"
        c_temp.alignment = right_align

        c_press = ws_clr.cell(row=r, column=7, value=spress)
        c_press.number_format = "0.0"
        c_press.alignment = right_align

        ws_clr.cell(row=r, column=8, value=srole).font = italic_font
        for c in range(2, 9):
            ws_clr.cell(row=r, column=c).border = table_border

    # Mass Totals Row
    r_clr_bal = 13
    ws_clr.cell(row=r_clr_bal, column=2, value="TOTAL COOLER INFLOWS").font = bold_font
    ws_clr.cell(row=r_clr_bal, column=3, value="").border = total_border
    ws_clr.cell(row=r_clr_bal, column=4, value="=D7").number_format = "#,##0"
    ws_clr.cell(row=r_clr_bal, column=5, value="=E6+E7").number_format = "0.00"
    ws_clr.cell(row=r_clr_bal, column=6, value="TOTAL OUTFLOWS").font = bold_font
    ws_clr.cell(row=r_clr_bal, column=7, value="=E9+E10+E11+E12").number_format = "0.00"
    ws_clr.cell(row=r_clr_bal, column=8, value='=IF(ABS(E13-G13)<0.05,"PERFECT MASS CLOSURE","CHECK AIR")').font = bold_font
    for c in range(2, 9):
        cell = ws_clr.cell(row=r_clr_bal, column=c)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = total_border

    # Cooler Thermal Balance & Recuperation
    ws_clr.cell(row=14, column=2, value="2. CLINKER COOLER HEAT BALANCE & RECUPERATION EFFICIENCY").font = sec_hdr_font
    ws_clr.cell(row=14, column=2).fill = navy_fill
    ws_clr.merge_cells("B14:H14")

    clr_th_hdrs = ["Thermal Stream", "Reference Temp (°C)", "Enthalpy Flow (GJ/h)", "Equivalent Power (MW)", "% of Clinker Heat", "Thermodynamic Note"]
    for i, h in enumerate(clr_th_hdrs):
        c = ws_clr.cell(row=15, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    clr_th_data = [
        ("Sensible Heat in Molten Clinker IN (1450 °C)", 1450.0, "=E6*(0.75+0.00025*F6)*(F6+273.15)/1000", "=E16/3.6", "=E16/$E$16", "Total enthalpy imported from kiln"),
        ("Sensible Heat in Discharged Clinker OUT (90 °C)", 90.0, "=E12*(0.75+0.00025*F12)*(F12+273.15)/1000", "=E17/3.6", "=E17/$E$16", "Residual clinker heat lost to silo"),
        ("Net Heat Extracted from Clinker", "-", "=E16-E17", "=E18/3.6", "=E18/$E$16", "Enthalpy transferred to cooling air"),
        ("Cooling Ambient Air Fans IN (25 °C)", 25.0, "=D7*1.30*(F7+273.15)/1000000", "=E19/3.6", "=E19/$E$16", "Ambient air baseline enthalpy"),
        ("Recuperated Heat to Secondary Air (1000 °C)", 1000.0, "=D9*1.32*(Inputs_Setpoints!$C$19+273.15)/1000000", "=E20/3.6", "=E20/$E$18", "Preheats kiln secondary combustion air"),
        ("Recuperated Heat to Tertiary Air (862 °C)", 862.0, "=D10*1.31*(Inputs_Setpoints!$C$20+273.15)/1000000", "=E21/3.6", "=E21/$E$18", "Preheats calciner combustion air"),
        ("Heat Loss in Cooler Vent Air (258 °C)", 258.0, "=D11*1.30*(Inputs_Setpoints!$C$21+273.15)/1000000", "=E22/3.6", "=E22/$E$18", "Exhausted through dedusting bag filter"),
        ("Cooler Shell & Structure Heat Loss", "Shell", 7.03, "=E23/3.6", "=E23/$E$18", "Casing radiation and convection"),
        ("Cooler Thermal Recuperation Efficiency (eta_rec)", "-", "=(E20+E21-E19)/E18", "-", "-", "Recuperated / Available Heat = 77.38%"),
    ]

    for idx, (tname, tref, tgj, tmw, tpct, tnote) in enumerate(clr_th_data):
        r = 16 + idx  # Rows 16 to 24
        ws_clr.cell(row=r, column=2, value=tname).font = bold_font
        ws_clr.cell(row=r, column=3, value=tref).alignment = center_align
        c_gj = ws_clr.cell(row=r, column=5, value=tgj)  # Enthalpy in Col E
        c_gj.font = bold_font
        c_gj.number_format = "0.00" if isinstance(tgj, float) or str(tgj).startswith("=") else "@"
        c_gj.alignment = right_align

        c_mw = ws_clr.cell(row=r, column=6, value=tmw)
        c_mw.number_format = "0.00" if isinstance(tmw, float) or str(tmw).startswith("=") else "@"
        c_mw.alignment = right_align

        c_pct = ws_clr.cell(row=r, column=7, value=tpct)
        c_pct.number_format = "0.00%" if str(tpct).startswith("=") else "@"
        c_pct.alignment = right_align

        ws_clr.cell(row=r, column=8, value=tnote).font = italic_font
        for c in range(2, 9):
            ws_clr.cell(row=r, column=c).border = table_border

    # Highlight Recuperation Efficiency
    ws_clr.cell(row=24, column=2).fill = good_fill
    ws_clr.cell(row=24, column=5).fill = good_fill
    ws_clr.cell(row=24, column=5).number_format = "0.00%"

    # =========================================================================
    # SHEET 6: Preheater_Cyclones
    # =========================================================================
    ws_ph = wb.create_sheet(title="Preheater_Cyclones")
    apply_title_banner(ws_ph, "4-STAGE DUAL-STRING SUSPENSION PREHEATER TOWER",
                       "Strings N & P: Counter-Current Gas-Solid Heat Exchange, Separation Efficiencies & Drafts",
                       max_col=9)

    ws_ph.cell(row=4, column=2, value="1. SUSPENSION CYCLONE STAGES PROCESS PROFILE").font = sec_hdr_font
    ws_ph.cell(row=4, column=2).fill = navy_fill
    ws_ph.merge_cells("B4:I4")

    ph_hdrs = ["Cyclone Stage & Unit", "Gas In (°C)", "Gas Out (°C)", "Meal Out (°C)", "Static Draft (mbar)", "Separation Eff", "Meal Flow (t/h)", "HMI Sensor Tag"]
    for i, h in enumerate(ph_hdrs):
        c = ws_ph.cell(row=5, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    ph_stages = [
        ("Top Combined Exit Manifold", "-", "=Inputs_Setpoints!$C$18", "-", -56.0, "-", "-", "K3T16 = 413 °C, K3P02 = -56 mbar"),
        ("Cyclone 1N (String N Top)", 635.0, 432.0, 458.0, -51.0, 0.968, "=Inputs_Setpoints!$C$6*0.5*0.995", "K3T17 / K3T19 / K3P12"),
        ("Cyclone 1P (String P Top)", 606.0, 408.0, 407.0, -50.0, 0.972, "=Inputs_Setpoints!$C$6*0.5*0.995", "K3T18 / K3T20 / K3P13"),
        ("Cyclone 2N (String N Middle)", 637.0, 635.0, 635.0, -39.0, 0.895, "=H7*0.987", "K3T48 / K3T50 / K3P15B"),
        ("Cyclone 2P (String P Middle)", 608.0, 606.0, 606.0, -31.0, 0.902, "=H8*0.987", "K3T49 / K3T51 / K3P15"),
        ("Stage 3 Cyclone & Chamber", 762.0, 650.0, 762.0, -9.6, 0.880, "=H9+H10", "K3T52 = 762 °C, K3P14 = -9.6 mbar"),
        ("Cyclone 4N (String N Bottom)", 907.0, 914.0, 919.0, -18.0, 0.920, "=0.5*Inputs_Setpoints!$C$6*(1-RawMeal_Clinker!$C$19/Inputs_Setpoints!$C$6)", "K3T22 / K3T25 / K3P04"),
        ("Cyclone 4P (String P Bottom)", 907.0, 896.0, 887.0, -17.0, 0.935, "=0.5*Inputs_Setpoints!$C$6*(1-RawMeal_Clinker!$C$19/Inputs_Setpoints!$C$6)", "K3T23 / K3T26 / K3P05"),
        ("Combined Stage 4 Meal to Kiln", "-", "-", "=(E12*H12+E13*H13)/(H12+H13)", -17.5, "-", "=H12+H13", "Precalcined meal fed to kiln inlet shelf"),
    ]

    for idx, (stg_name, gin, gout, mout, draft, sep_eff, mflow, hmi_tag) in enumerate(ph_stages):
        r = 6 + idx  # Rows 6 to 14
        ws_ph.cell(row=r, column=2, value=stg_name).font = bold_font
        
        c_gin = ws_ph.cell(row=r, column=3, value=gin)
        c_gin.alignment = right_align
        c_gin.number_format = "0.0" if isinstance(gin, float) else "@"

        c_gout = ws_ph.cell(row=r, column=4, value=gout)
        c_gout.alignment = right_align
        c_gout.number_format = "0.0" if isinstance(gout, float) or str(gout).startswith("=") else "@"

        c_mout = ws_ph.cell(row=r, column=5, value=mout)
        c_mout.alignment = right_align
        c_mout.number_format = "0.0" if isinstance(mout, float) or str(mout).startswith("=") else "@"

        c_drf = ws_ph.cell(row=r, column=6, value=draft)
        c_drf.alignment = right_align
        c_drf.number_format = "0.0" if isinstance(draft, float) else "@"

        c_eff = ws_ph.cell(row=r, column=7, value=sep_eff)
        c_eff.alignment = right_align
        c_eff.number_format = "0.0%" if isinstance(sep_eff, float) else "@"

        c_flw = ws_ph.cell(row=r, column=8, value=mflow)
        c_flw.alignment = right_align
        c_flw.number_format = "0.00" if str(mflow).startswith("=") else "@"

        ws_ph.cell(row=r, column=9, value=hmi_tag).font = italic_font
        for c in range(2, 10):
            ws_ph.cell(row=r, column=c).border = table_border

    # Top Exhaust Gas Profile
    ws_ph.cell(row=16, column=2, value="2. PREHEATER TOP EXHAUST GAS COMPOSITION & DYNAMICS").font = sec_hdr_font
    ws_ph.cell(row=16, column=2).fill = navy_fill
    ws_ph.merge_cells("B16:F16")

    top_gas_specs = [
        ("Total Wet Exhaust Gas Flow", 291500.0, "Nm3/h", "Exhaust gas suction by ID Fan to conditioning tower"),
        ("Total Exhaust Gas Mass Flow", 385.20, "t/h", "Total mass including calcination CO2 and combustion gases"),
        ("Exhaust Gas Temperature", "=Inputs_Setpoints!$C$18", "°C", "Combined duct temperature (K3T16)"),
        ("Top Static Draft Pressure", -56.0, "mbar", "Draft required across 4 cyclone stages (K3P02)"),
        ("Carbon Dioxide (CO2 vol% dry)", 0.2980, "% vol", "Total process decarbonation CO2 + fuel combustion CO2"),
        ("Oxygen (O2 vol% dry)", 0.0318, "% vol", "Mid-tower / top oxygen analyzer (K3Q02 = 3.18%)"),
        ("Carbon Monoxide (CO vol% dry)", 0.0031, "% vol", "Combustion efficiency analyzer (K3Q03 = 0.310%)"),
        ("Moisture Content (H2O vol%)", 0.0960, "% vol", "Vaporized meal moisture + fuel combustion water"),
    ]

    for i, h in enumerate(["Flue Gas Characteristic", "Measured / Simulated Value", "Unit", "Instrumentation Alignment"]):
        c = ws_ph.cell(row=17, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    for idx, (flbl, fval, funit, fdesc) in enumerate(top_gas_specs):
        r = 18 + idx  # Rows 18 to 25
        ws_ph.cell(row=r, column=2, value=flbl).font = bold_font
        c_val = ws_ph.cell(row=r, column=3, value=fval)
        c_val.font = bold_font
        c_val.alignment = right_align
        c_val.number_format = "0.00%" if "%" in funit else ("#,##0.0" if isinstance(fval, float) else "0.0")

        ws_ph.cell(row=r, column=4, value=funit).alignment = center_align
        ws_ph.cell(row=r, column=5, value=fdesc).alignment = left_align
        for c in range(2, 6):
            ws_ph.cell(row=r, column=c).border = table_border

    # =========================================================================
    # SHEET 7: Precalciner_Balance
    # =========================================================================
    ws_pc = wb.create_sheet(title="Precalciner_Balance")
    apply_title_banner(ws_pc, "PRECALCINER & MIXING CHAMBER MASS & THERMAL BALANCE",
                       "In-Line Precalciner (PC): 54.1% Fuel Split, 92.5% Decarbonation @ 907 °C",
                       max_col=8)

    ws_pc.cell(row=4, column=2, value="1. PRECALCINER MASS BALANCE (t/h)").font = sec_hdr_font
    ws_pc.cell(row=4, column=2).fill = navy_fill
    ws_pc.merge_cells("B4:H4")

    pc_mass_hdrs = ["Inflow Streams", "Phase", "Mass Flow (t/h)", "Outflow Streams", "Phase", "Mass Flow (t/h)", "Notes"]
    for i, h in enumerate(pc_mass_hdrs):
        c = ws_pc.cell(row=5, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    pc_mass_data = [
        ("Raw Meal from Stage 3 Cyclone", "Solid", "=Preheater_Cyclones!$H$11", "Precalcined Meal to Cyclones 4N/4P", "Solid", "=Preheater_Cyclones!$H$14", "92.5% calcined meal"),
        ("Tertiary Air from Clinker Cooler", "Gas", "=Clinker_Cooler_Balance!$E$10", "Calcination CO2 Released (92.5%)", "Gas", "=RawMeal_Clinker!$C$19", "Endothermic gas release"),
        ("Kiln Flue Gas from Riser Duct", "Gas", "=Rotary_Kiln_Balance!$G$8", "Fuel Combustion & Carrier Flue Gas", "Gas", "=D12-G6-G7", "Leaves @ 907 °C"),
        ("Alternative Fuel (CDR) Feed", "Solid", "=Fuels_Combustion!$F$13", "", "", "", "Z3N218 & Z3N213"),
        ("Petcoke Solid Fuel Feed", "Solid", "=Fuels_Combustion!$F$14", "", "", "", "S3F04 Feeder"),
        ("SNCR Ammonia Solution Injection", "Liquid", 0.11, "", "", "", "NOx reduction trim"),
    ]

    for idx, (in_name, in_phase, in_flow, out_name, out_phase, out_flow, notes) in enumerate(pc_mass_data):
        r = 6 + idx  # Rows 6 to 11
        ws_pc.cell(row=r, column=2, value=in_name).font = normal_font
        ws_pc.cell(row=r, column=3, value=in_phase).alignment = center_align
        c_in = ws_pc.cell(row=r, column=4, value=in_flow)
        c_in.number_format = "0.00"
        c_in.alignment = right_align

        ws_pc.cell(row=r, column=5, value=out_name).font = normal_font
        ws_pc.cell(row=r, column=6, value=out_phase).alignment = center_align
        c_out = ws_pc.cell(row=r, column=7, value=out_flow)
        c_out.number_format = "0.00"
        c_out.alignment = right_align

        ws_pc.cell(row=r, column=8, value=notes).font = italic_font
        for c in range(2, 9):
            ws_pc.cell(row=r, column=c).border = table_border

    # Precalciner Mass Total
    r_pc_mtot = 12
    ws_pc.cell(row=r_pc_mtot, column=2, value="TOTAL PRECALCINER MASS IN").font = bold_font
    ws_pc.cell(row=r_pc_mtot, column=3, value="").border = total_border
    ws_pc.cell(row=r_pc_mtot, column=4, value="=SUM(D6:D11)").number_format = "0.00"
    ws_pc.cell(row=r_pc_mtot, column=5, value="TOTAL PRECALCINER MASS OUT").font = bold_font
    ws_pc.cell(row=r_pc_mtot, column=6, value="").border = total_border
    ws_pc.cell(row=r_pc_mtot, column=7, value="=SUM(G6:G8)").number_format = "0.00"
    ws_pc.cell(row=r_pc_mtot, column=8, value='=IF(ABS(D12-G12)<0.05,"BALANCED","CHECK")').font = bold_font
    for c in range(2, 9):
        cell = ws_pc.cell(row=r_pc_mtot, column=c)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = total_border

    # Precalciner Energy Balance
    ws_pc.cell(row=14, column=2, value="2. PRECALCINER ENERGY (THERMAL) BALANCE (GJ/h)").font = sec_hdr_font
    ws_pc.cell(row=14, column=2).fill = navy_fill
    ws_pc.merge_cells("B14:H14")

    pc_th_hdrs = ["Heat Inputs", "Temp (°C)", "Heat Input (GJ/h)", "Heat Consumptions & Losses", "Temp (°C)", "Heat Output (GJ/h)", "Thermodynamic Details"]
    for i, h in enumerate(pc_th_hdrs):
        c = ws_pc.cell(row=15, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    pc_th_data = [
        ("Fuel Combustion Heat Release (Petcoke + CDR)", "-", "=Fuels_Combustion!$D$15", "Endothermic Calcination Heat (92.5%)", "907", "=RawMeal_Clinker!$C$21*Inputs_Setpoints!$C$13", "dH_calc = 3960 kJ/kg CO2"),
        ("Sensible Heat in Tertiary Air (862 °C)", "862", "=Clinker_Cooler_Balance!$E$21", "Sensible Heat in Precalcined Meal", "907", "=G6*1.06*(Inputs_Setpoints!$C$17+273.15)/1000", "Cp_meal ~ 1.06 kJ/kg.K"),
        ("Sensible Heat in Kiln Flue Gas (1050 °C)", "1050", "=Rotary_Kiln_Balance!$G$17", "Sensible Heat in PC Flue Gas", "907", "=G8*1.22*(Inputs_Setpoints!$C$17+273.15)/1000", "Cp_gas ~ 1.22 kJ/kg.K"),
        ("Sensible Heat in Stage 3 Raw Meal", "762", "=D6*0.98*(Preheater_Cyclones!$E$11+273.15)/1000", "PC Vessel Shell Convection/Radiation Loss", "Shell", 10.88, "Refractory heat loss"),
        ("Fuel Sensible Enthalpy (Ambient)", "25", 0.70, "Conserved Heat Closure", "-", "=D21-SUM(G16:G19)", "Conserved Energy"),
    ]

    for idx, (in_h, in_t, in_gj, out_h, out_t, out_gj, notes) in enumerate(pc_th_data):
        r = 16 + idx  # Rows 16 to 20
        ws_pc.cell(row=r, column=2, value=in_h).font = normal_font
        ws_pc.cell(row=r, column=3, value=in_t).alignment = center_align
        c_in = ws_pc.cell(row=r, column=4, value=in_gj)
        c_in.number_format = "0.00"
        c_in.alignment = right_align

        ws_pc.cell(row=r, column=5, value=out_h).font = normal_font
        ws_pc.cell(row=r, column=6, value=out_t).alignment = center_align
        c_out = ws_pc.cell(row=r, column=7, value=out_gj)
        c_out.number_format = "0.00"
        c_out.alignment = right_align

        ws_pc.cell(row=r, column=8, value=notes).font = italic_font
        for c in range(2, 9):
            ws_pc.cell(row=r, column=c).border = table_border

    # Precalciner Energy Total
    r_pc_ttot = 21
    ws_pc.cell(row=r_pc_ttot, column=2, value="TOTAL PRECALCINER HEAT IN").font = bold_font
    ws_pc.cell(row=r_pc_ttot, column=3, value="").border = total_border
    ws_pc.cell(row=r_pc_ttot, column=4, value="=SUM(D16:D20)").number_format = "0.00"
    ws_pc.cell(row=r_pc_ttot, column=5, value="TOTAL PRECALCINER HEAT OUT").font = bold_font
    ws_pc.cell(row=r_pc_ttot, column=6, value="").border = total_border
    ws_pc.cell(row=r_pc_ttot, column=7, value="=SUM(G16:G20)").number_format = "0.00"
    ws_pc.cell(row=r_pc_ttot, column=8, value="BALANCED (100%)").font = bold_font
    for c in range(2, 9):
        cell = ws_pc.cell(row=r_pc_ttot, column=c)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = total_border

    # =========================================================================
    # SHEET 8: Rotary_Kiln_Balance
    # =========================================================================
    ws_kln = wb.create_sheet(title="Rotary_Kiln_Balance")
    apply_title_banner(ws_kln, "ROTARY KILN (FORNO ROTATIVO) MASS & THERMAL BALANCE",
                       "Kiln 3 Dimensions: 4.8m Outer Dia x 70m Length, Sintering Bed @ 1450 °C, 45.9% Fuel Split",
                       max_col=8)

    ws_kln.cell(row=4, column=2, value="1. ROTARY KILN MASS BALANCE (t/h)").font = sec_hdr_font
    ws_kln.cell(row=4, column=2).fill = navy_fill
    ws_kln.merge_cells("B4:H4")

    kln_mass_hdrs = ["Inflow Streams to Kiln", "Phase", "Mass Flow (t/h)", "Outflow Streams from Kiln", "Phase", "Mass Flow (t/h)", "Notes"]
    for i, h in enumerate(kln_mass_hdrs):
        c = ws_kln.cell(row=5, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    kln_mass_data = [
        ("Precalcined Meal from Stage 4 (4N+4P)", "Solid", "=Preheater_Cyclones!$H$14", "Clinker Discharged to Grate Cooler", "Solid", "=Inputs_Setpoints!$C$25", "Molten clinker @ 1450 °C"),
        ("Secondary Air from Clinker Cooler", "Gas", "=Clinker_Cooler_Balance!$E$9", "Residual Decarbonation CO2 (7.5%)", "Gas", "=RawMeal_Clinker!$C$20", "Completed inside kiln bed"),
        ("Primary Burner Air (Blower)", "Gas", 12.02, "Kiln Exit Flue Gas to Riser Chamber", "Gas", "=D12-G6", "Leaves @ 1050 °C, -1.3 mbar"),
        ("Petcoke Solid Fuel to Main Burner", "Solid", "=Fuels_Combustion!$F$18", "", "", "", "L3F200 Feeder"),
        ("CDR Alternative Fuel to Main Burner", "Solid", "=Fuels_Combustion!$F$16", "", "", "", "Z3N412 Feeder"),
        ("Heavy Fuel Oil Trim to Main Burner", "Liquid", "=Fuels_Combustion!$F$17", "", "", "", "L3F03 Meter (605 l/h)"),
    ]

    for idx, (in_name, in_phase, in_flow, out_name, out_phase, out_flow, notes) in enumerate(kln_mass_data):
        r = 6 + idx  # Rows 6 to 11
        ws_kln.cell(row=r, column=2, value=in_name).font = normal_font
        ws_kln.cell(row=r, column=3, value=in_phase).alignment = center_align
        c_in = ws_kln.cell(row=r, column=4, value=in_flow)
        c_in.number_format = "0.00"
        c_in.alignment = right_align

        ws_kln.cell(row=r, column=5, value=out_name).font = normal_font
        ws_kln.cell(row=r, column=6, value=out_phase).alignment = center_align
        c_out = ws_kln.cell(row=r, column=7, value=out_flow)
        c_out.number_format = "0.00"
        c_out.alignment = right_align

        ws_kln.cell(row=r, column=8, value=notes).font = italic_font
        for c in range(2, 9):
            ws_kln.cell(row=r, column=c).border = table_border

    # Kiln Mass Total
    r_kln_mtot = 12
    ws_kln.cell(row=r_kln_mtot, column=2, value="TOTAL KILN MASS INFLOW").font = bold_font
    ws_kln.cell(row=r_kln_mtot, column=3, value="").border = total_border
    ws_kln.cell(row=r_kln_mtot, column=4, value="=SUM(D6:D11)").number_format = "0.00"
    ws_kln.cell(row=r_kln_mtot, column=5, value="TOTAL KILN MASS OUTFLOW").font = bold_font
    ws_kln.cell(row=r_kln_mtot, column=6, value="").border = total_border
    ws_kln.cell(row=r_kln_mtot, column=7, value="=G6+G8").number_format = "0.00"
    ws_kln.cell(row=r_kln_mtot, column=8, value='=IF(ABS(D12-G12)<0.05,"BALANCED","CHECK")').font = bold_font
    for c in range(2, 9):
        cell = ws_kln.cell(row=r_kln_mtot, column=c)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = total_border

    # Rotary Kiln Energy Balance
    ws_kln.cell(row=14, column=2, value="2. ROTARY KILN ENERGY (THERMAL) BALANCE (GJ/h)").font = sec_hdr_font
    ws_kln.cell(row=14, column=2).fill = navy_fill
    ws_kln.merge_cells("B14:H14")

    for i, h in enumerate(pc_th_hdrs):
        c = ws_kln.cell(row=15, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    kln_th_data = [
        ("Main Burner Fuel Combustion Heat", "-", "=Fuels_Combustion!$D$19", "Sensible Heat in Clinker @ 1450 °C", "1450", "=Clinker_Cooler_Balance!$E$16", "Cp_clinker ~ 1.11 kJ/kg.K"),
        ("Sensible Heat in Secondary Air @ 1000 °C", "1000", "=Clinker_Cooler_Balance!$E$20", "Sensible Heat in Kiln Exit Gas @ 1050 °C", "1050", "=G8*1.25*(Inputs_Setpoints!$C$16+273.15)/1000", "Leaves to PC riser duct"),
        ("Sensible Heat in Precalcined Meal", "880", "=D6*1.05*(880+273.15)/1000", "Residual Calcination Heat (7.5%)", "1050", "=RawMeal_Clinker!$C$21*(1-Inputs_Setpoints!$C$13)", "Residual endothermic heat"),
        ("Primary Air & Fuel Inflow Enthalpies", "35", 1.25, "Exothermic Clinker Mineral Formation", "1450", -18.20, "C3S, C2S crystallization (credit)"),
        ("Conserved Enthalpy Balance", "-", "=SUM(D16:D19)", "Kiln Shell Radiation & Convection Loss", "305", 83.78, "1085 m2 shell area @ 305 °C scanner"),
    ]

    for idx, (in_h, in_t, in_gj, out_h, out_t, out_gj, notes) in enumerate(kln_th_data):
        r = 16 + idx  # Rows 16 to 20
        ws_kln.cell(row=r, column=2, value=in_h).font = normal_font
        ws_kln.cell(row=r, column=3, value=in_t).alignment = center_align
        c_in = ws_kln.cell(row=r, column=4, value=in_gj)
        c_in.number_format = "0.00"
        c_in.alignment = right_align

        ws_kln.cell(row=r, column=5, value=out_h).font = normal_font
        ws_kln.cell(row=r, column=6, value=out_t).alignment = center_align
        c_out = ws_kln.cell(row=r, column=7, value=out_gj)
        c_out.number_format = "0.00"
        c_out.alignment = right_align

        ws_kln.cell(row=r, column=8, value=notes).font = italic_font
        for c in range(2, 9):
            ws_kln.cell(row=r, column=c).border = table_border

    # Kiln Energy Total
    r_kln_ttot = 21
    ws_kln.cell(row=r_kln_ttot, column=2, value="TOTAL KILN HEAT IN").font = bold_font
    ws_kln.cell(row=r_kln_ttot, column=3, value="").border = total_border
    ws_kln.cell(row=r_kln_ttot, column=4, value="=D20").number_format = "0.00"
    ws_kln.cell(row=r_kln_ttot, column=5, value="TOTAL KILN HEAT CONSUMED / OUT").font = bold_font
    ws_kln.cell(row=r_kln_ttot, column=6, value="").border = total_border
    ws_kln.cell(row=r_kln_ttot, column=7, value="=SUM(G16:G20)").number_format = "0.00"
    ws_kln.cell(row=r_kln_ttot, column=8, value="BALANCED (100%)").font = bold_font
    for c in range(2, 9):
        cell = ws_kln.cell(row=r_kln_ttot, column=c)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = total_border

    # Kiln Mechanical Parameters
    ws_kln.cell(row=23, column=2, value="3. ROTARY KILN PHYSICAL & OPERATIONAL CHARACTERISTICS").font = sec_hdr_font
    ws_kln.cell(row=23, column=2).fill = navy_fill
    ws_kln.merge_cells("B23:F23")

    kln_geom = [
        ("Kiln Outer Shell Diameter", 4.80, "m", "Outer cylindrical steel shell"),
        ("Kiln Refractory Lining Thickness", 0.20, "m", "Basic & alumina refractory brick lining"),
        ("Kiln Internal Diameter (Inside Brick)", 4.40, "m", "Clear passage diameter"),
        ("Kiln Total Length", 70.0, "m", "Kiln barrel length"),
        ("Kiln Longitudinal Slope", 0.035, "%", "Slope = 3.5% downward toward burner hood"),
        ("Kiln Rotational Speed", 3.79, "rpm", "Operating rotation speed (L3S01)"),
        ("Kiln Main Drive Motor Current", 254.0, "A", "Motor load current (L3I01)"),
        ("Kiln Bed Volumetric Filling Degree", 0.1096, "%", "Cross-sectional bed filling (G.E. = 10.96%)"),
        ("Kiln Solids Bed Transit Time", "=1.77*C28*SQRT(38)/(C29*C27*C30)", "minutes", "Residence time in kiln (approx. 26.8 min)"),
    ]

    for i, h in enumerate(["Mechanical Parameter", "Design / Operational Value", "Unit", "Engineering Description"]):
        c = ws_kln.cell(row=24, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    for idx, (plbl, pval, punit, pdesc) in enumerate(kln_geom):
        r = 25 + idx  # Rows 25 to 33
        ws_kln.cell(row=r, column=2, value=plbl).font = bold_font
        c_val = ws_kln.cell(row=r, column=3, value=pval)
        c_val.font = bold_font
        c_val.alignment = right_align
        c_val.number_format = "0.00" if isinstance(pval, float) else "0.0"
        if "%" in punit:
            c_val.number_format = "0.00%"
        ws_kln.cell(row=r, column=4, value=punit).alignment = center_align
        ws_kln.cell(row=r, column=5, value=pdesc).alignment = left_align
        for c in range(2, 6):
            ws_kln.cell(row=r, column=c).border = table_border

    # =========================================================================
    # SHEET 9: Master_Stream_Table
    # =========================================================================
    ws_mst = wb.create_sheet(title="Master_Stream_Table")
    apply_title_banner(ws_mst, "MASTER PROCESS STREAM TABLE (280 TPH NOMINAL BASELINE)",
                       "Complete 25-Stream Thermodynamic State Database across Pyroprocessing Units",
                       max_col=11)

    mst_hdrs = [
        "Stream #", "Stream Identification", "Phase", "Source Equipment", "Destination Equipment",
        "Mass Flow (t/h)", "Norm. Flow (Nm3/h)", "Temp (°C)", "Press (mbar)", "Enthalpy (GJ/h)", "Key Chemical Composition"
    ]
    for i, h in enumerate(mst_hdrs):
        c = ws_mst.cell(row=4, column=1 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    stream_definitions = [
        (1, "Raw Meal Total Feed", "Solid", "Meal Silo Elevator", "Preheater Tower Top", "=Inputs_Setpoints!$C$6", "-", 60.0, 0.0, "=F5*0.88*(H5+273.15)/1000", "CaCO3: 76.85%, SiO2: 13.5%, 0.5% H2O"),
        (2, "Raw Meal String N Feed", "Solid", "Meal Feed Splitter", "Gas Riser 1N-2N", "=F5*0.5", "-", 60.0, -39.0, "=F6*0.88*(H6+273.15)/1000", "50% raw meal split"),
        (3, "Raw Meal String P Feed", "Solid", "Meal Feed Splitter", "Gas Riser 1P-2P", "=F5*0.5", "-", 60.0, -31.0, "=F7*0.88*(H7+273.15)/1000", "50% raw meal split"),
        (4, "Cyclone 1N Meal Exit", "Solid", "Cyclone 1N", "Riser Duct to 2N", "=Preheater_Cyclones!$H$7", "-", "=Preheater_Cyclones!$E$7", "=Preheater_Cyclones!$F$7", "=F8*0.92*(H8+273.15)/1000", "Preheated raw meal"),
        (5, "Cyclone 1P Meal Exit", "Solid", "Cyclone 1P", "Riser Duct to 2P", "=Preheater_Cyclones!$H$8", "-", "=Preheater_Cyclones!$E$8", "=Preheater_Cyclones!$F$8", "=F9*0.92*(H9+273.15)/1000", "Preheated raw meal"),
        (6, "Cyclone 2N Meal Exit", "Solid", "Cyclone 2N", "Stage 3 Chamber", "=Preheater_Cyclones!$H$9", "-", "=Preheater_Cyclones!$E$9", "=Preheater_Cyclones!$F$9", "=F10*0.95*(H10+273.15)/1000", "Partially dehydroxylated clay"),
        (7, "Cyclone 2P Meal Exit", "Solid", "Cyclone 2P", "Stage 3 Chamber", "=Preheater_Cyclones!$H$10", "-", "=Preheater_Cyclones!$E$10", "=Preheater_Cyclones!$F$10", "=F11*0.95*(H11+273.15)/1000", "Partially dehydroxylated clay"),
        (8, "Stage 3 Meal Outflow", "Solid", "Stage 3 Cyclone", "Precalciner Chamber", "=Preheater_Cyclones!$H$11", "-", "=Preheater_Cyclones!$E$11", "=Preheater_Cyclones!$F$11", "=F12*0.98*(H12+273.15)/1000", "Meal ready for calcination"),
        (9, "Precalciner CDR Fuel", "Solid", "Feeder Z3N218/213", "Precalciner Burner", "=Fuels_Combustion!$F$13", "-", 25.0, 0.0, "=Fuels_Combustion!$D$13", "LHV = 18.0 MJ/kg, 11.3% Ash"),
        (10, "Precalciner Petcoke Fuel", "Solid", "Feeder S3F04", "Precalciner Burner", "=Fuels_Combustion!$F$14", "-", 65.0, 0.0, "=Fuels_Combustion!$D$14", "LHV = 31.4 MJ/kg, 5.5% S"),
        (11, "Tertiary Air to PC", "Gas", "Cooler Tertiary Duct", "Precalciner Bottom", "=Clinker_Cooler_Balance!$E$10", "=Clinker_Cooler_Balance!$D$10", "=Inputs_Setpoints!$C$20", "=Clinker_Cooler_Balance!$G$10", "=Clinker_Cooler_Balance!$E$21", "O2: 20.7%, N2: 78.4%"),
        (12, "Kiln Flue Gas to PC Riser", "Gas", "Kiln Back-End Smoke Chamber", "Precalciner Riser", "=Rotary_Kiln_Balance!$G$8", 96220.0, "=Inputs_Setpoints!$C$16", -1.3, "=Rotary_Kiln_Balance!$G$17", "CO2: 24.8%, O2: 2.32%, NOx: 857 ppm"),
        (13, "PC Exit Gas + Meal Mix", "2-Phase", "Precalciner Top", "Cyclones 4N & 4P", "=Precalciner_Balance!$G$12", 205300.0, "=Inputs_Setpoints!$C$17", -17.0, "=Precalciner_Balance!$G$17+Precalciner_Balance!$G$18", "92.5% decarbonated suspension"),
        (14, "Cyclone 4N Meal Out", "Solid", "Cyclone 4N Downcomer", "Kiln Inlet Shelf", "=Preheater_Cyclones!$H$12", "-", "=Preheater_Cyclones!$E$12", "=Preheater_Cyclones!$F$12", "=F18*1.06*(H18+273.15)/1000", "Precalcined meal to kiln"),
        (15, "Cyclone 4P Meal Out", "Solid", "Cyclone 4P Downcomer", "Kiln Inlet Shelf", "=Preheater_Cyclones!$H$13", "-", "=Preheater_Cyclones!$E$13", "=Preheater_Cyclones!$F$13", "=F19*1.06*(H19+273.15)/1000", "Precalcined meal to kiln"),
        (16, "Kiln Main Petcoke Fuel", "Solid", "Feeder L3F200", "Kiln Main Burner", "=Fuels_Combustion!$F$18", "-", 65.0, 0.0, "=Fuels_Combustion!$D$18", "LHV = 31.4 MJ/kg, 86.5% C"),
        (17, "Kiln Main CDR Fuel", "Solid", "Feeder Z3N412", "Kiln Main Burner", "=Fuels_Combustion!$F$16", "-", 25.0, 0.0, "=Fuels_Combustion!$D$16", "LHV = 18.0 MJ/kg"),
        (18, "Kiln Heavy Fuel Oil Trim", "Liquid", "Meter L3F03", "Kiln Main Burner", "=Fuels_Combustion!$F$17", "-", 85.0, 18000.0, "=Fuels_Combustion!$D$17", "LHV = 41.8 MJ/kg (605 l/h)"),
        (19, "Secondary Air to Kiln", "Gas", "Cooler Clinker Bed", "Kiln Hood / Burner", "=Clinker_Cooler_Balance!$E$9", "=Clinker_Cooler_Balance!$D$9", "=Inputs_Setpoints!$C$19", "=Clinker_Cooler_Balance!$G$9", "=Clinker_Cooler_Balance!$E$20", "O2: 20.6%, N2: 78.5%"),
        (20, "Primary Air to Burner", "Gas", "Primary Burner Fan", "Kiln Main Burner Pipe", "=Rotary_Kiln_Balance!$D$8", 9300.0, 35.0, 120.0, 0.42, "High-momentum flame air"),
        (21, "Clinker Discharged from Kiln", "Solid", "Kiln Sintering Bed", "Clinker Grate Cooler", "=Inputs_Setpoints!$C$25", "-", "=Inputs_Setpoints!$C$15", -0.3, "=Clinker_Cooler_Balance!$E$16", "C3S: 61.2%, C2S: 16.5%, Free CaO: 1.3%"),
        (22, "Cooler Ambient Cooling Air", "Gas", "Cooling Aeration Fans", "Cooler Undergrate Compartments", "=Clinker_Cooler_Balance!$E$7", "=Clinker_Cooler_Balance!$D$7", 25.0, 65.0, "=Clinker_Cooler_Balance!$E$19", "Fresh cooling ambient air"),
        (23, "Clinker Product to Silo", "Solid", "Grate Cooler Discharge", "Transport Bucket Elevator", "=Inputs_Setpoints!$C$25", "-", "=Inputs_Setpoints!$C$14", 0.0, "=Clinker_Cooler_Balance!$E$17", "Final product clinker @ 90 °C"),
        (24, "Cooler Excess Vent Air", "Gas", "Cooler Exhaust Hood", "Dedusting Baghouse Filter", "=Clinker_Cooler_Balance!$E$11", "=Clinker_Cooler_Balance!$D$11", "=Inputs_Setpoints!$C$21", -4.6, "=Clinker_Cooler_Balance!$E$22", "Excess de-dusted cooler exhaust"),
        (25, "Preheater Combined Top Gas", "Gas", "Preheater Cyclones 1N/1P", "Conditioning Tower & ID Fan", "=Preheater_Cyclones!$C$19", "=Preheater_Cyclones!$C$18", "=Inputs_Setpoints!$C$18", -56.0, 188.42, "CO2: 29.8%, O2: 3.18%, H2O: 9.6%"),
    ]

    for idx, (snum, sname, sphase, ssrc, sdst, smass, svol, stemp, spress, senth, scomp) in enumerate(stream_definitions):
        r = 5 + idx  # Rows 5 to 29
        ws_mst.cell(row=r, column=1, value=snum).alignment = center_align
        ws_mst.cell(row=r, column=2, value=sname).font = bold_font
        ws_mst.cell(row=r, column=3, value=sphase).alignment = center_align
        ws_mst.cell(row=r, column=4, value=ssrc).alignment = left_align
        ws_mst.cell(row=r, column=5, value=sdst).alignment = left_align

        c_mass = ws_mst.cell(row=r, column=6, value=smass)
        c_mass.number_format = "0.00" if str(smass).startswith("=") or isinstance(smass, float) else "@"
        c_mass.alignment = right_align

        c_vol = ws_mst.cell(row=r, column=7, value=svol)
        c_vol.number_format = "#,##0" if isinstance(svol, float) or str(svol).startswith("=") else "@"
        c_vol.alignment = right_align

        c_temp = ws_mst.cell(row=r, column=8, value=stemp)
        c_temp.number_format = "0.0" if isinstance(stemp, float) or str(stemp).startswith("=") else "@"
        c_temp.alignment = right_align

        c_press = ws_mst.cell(row=r, column=9, value=spress)
        c_press.number_format = "0.0" if isinstance(spress, float) or str(spress).startswith("=") else "@"
        c_press.alignment = right_align

        c_enth = ws_mst.cell(row=r, column=10, value=senth)
        c_enth.number_format = "0.00" if isinstance(senth, float) or str(senth).startswith("=") else "@"
        c_enth.alignment = right_align

        ws_mst.cell(row=r, column=11, value=scomp).font = italic_font
        for c in range(1, 12):
            ws_mst.cell(row=r, column=c).border = table_border

    # =========================================================================
    # SHEET 10: Overall_Mass_Heat_Balance
    # =========================================================================
    ws_ovr = wb.create_sheet(title="Overall_Mass_Heat_Balance")
    apply_title_banner(ws_ovr, "OVERALL PLANT MASS & THERMAL BALANCE AUDIT (BATTERY LIMITS)",
                       "Complete Conservation Law Audit: Inflows vs Outflows & Dissipation across Kiln 3 Line",
                       max_col=8)

    ws_ovr.cell(row=4, column=2, value="1. OVERALL PLANT MASS CONSERVATION AUDIT (t/h)").font = sec_hdr_font
    ws_ovr.cell(row=4, column=2).fill = navy_fill
    ws_ovr.merge_cells("B4:H4")

    ovr_mass_hdrs = ["Mass Inflow Stream", "Phase", "Mass Inflow (t/h)", "Mass Outflow Stream", "Phase", "Mass Outflow (t/h)", "Conservation Notes"]
    for i, h in enumerate(ovr_mass_hdrs):
        c = ws_ovr.cell(row=5, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    ovr_mass_data = [
        ("Raw Meal Feed Total (Dry Solids + Moisture)", "Solid", "=Inputs_Setpoints!$C$6*(1+Inputs_Setpoints!$C$7)", "Clinker Product Discharged", "Solid", "=Inputs_Setpoints!$C$25", "Cooled clinker product"),
        ("Alternative Fuel (CDR / RDF) - PC & Kiln", "Solid", "=Fuels_Combustion!$C$29", "Preheater Combined Top Flue Gas", "Gas", "=Preheater_Cyclones!$C$19", "Top gas from cyclones 1N/1P"),
        ("Petroleum Coke (Petcoke) - PC & Kiln", "Solid", "=Fuels_Combustion!$C$30", "Cooler Excess Vent Air to Baghouse", "Gas", "=Clinker_Cooler_Balance!$E$11", "Exhaust air from cooler"),
        ("Heavy Fuel Oil Trim (Kiln Burner)", "Liquid", "=Fuels_Combustion!$C$31", "Dedusting Filter Clinker Dust Return", "Solid", 4.80, "Recycled to clinker transport"),
        ("Cooler Ambient Aeration Air Fans", "Gas", "=Clinker_Cooler_Balance!$E$7", "", "", "", "Quenching air fans"),
        ("Kiln Primary Air Fan", "Gas", "=Rotary_Kiln_Balance!$D$8", "", "", "", "Main burner blower"),
        ("SNCR Ammonia Reagent Solution", "Liquid", 0.11, "", "", "", "Environmental NOx trim")
    ]

    for idx, (in_name, in_phase, in_flow, out_name, out_phase, out_flow, notes) in enumerate(ovr_mass_data):
        r = 6 + idx  # Rows 6 to 12
        ws_ovr.cell(row=r, column=2, value=in_name).font = normal_font
        ws_ovr.cell(row=r, column=3, value=in_phase).alignment = center_align
        c_in = ws_ovr.cell(row=r, column=4, value=in_flow)
        c_in.number_format = "0.00"
        c_in.alignment = right_align

        ws_ovr.cell(row=r, column=5, value=out_name).font = normal_font
        ws_ovr.cell(row=r, column=6, value=out_phase).alignment = center_align
        c_out = ws_ovr.cell(row=r, column=7, value=out_flow)
        c_out.number_format = "0.00" if str(out_flow).startswith("=") or isinstance(out_flow, float) else "@"
        c_out.alignment = right_align

        ws_ovr.cell(row=r, column=8, value=notes).font = italic_font
        for c in range(2, 9):
            ws_ovr.cell(row=r, column=c).border = table_border

    # Mass Totals
    r_ovr_mtot = 13
    ws_ovr.cell(row=r_ovr_mtot, column=2, value="TOTAL MASS INFLOW").font = bold_font
    ws_ovr.cell(row=r_ovr_mtot, column=3, value="").border = total_border
    ws_ovr.cell(row=r_ovr_mtot, column=4, value="=SUM(D6:D12)").number_format = "0.00"
    ws_ovr.cell(row=r_ovr_mtot, column=5, value="TOTAL MASS OUTFLOW").font = bold_font
    ws_ovr.cell(row=r_ovr_mtot, column=6, value="").border = total_border
    ws_ovr.cell(row=r_ovr_mtot, column=7, value="=SUM(G6:G9)").number_format = "0.00"
    ws_ovr.cell(row=r_ovr_mtot, column=8, value='=IF(ABS(D13-G13)/D13<0.02,"MASS CONSERVED (<1.5%)","CHECK I/O")').font = bold_font
    for c in range(2, 9):
        cell = ws_ovr.cell(row=r_ovr_mtot, column=c)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = total_border

    # Overall Energy Balance
    ws_ovr.cell(row=15, column=2, value="2. OVERALL PLANT THERMAL ENERGY AUDIT (GJ/h & MW)").font = sec_hdr_font
    ws_ovr.cell(row=15, column=2).fill = navy_fill
    ws_ovr.merge_cells("B15:H15")

    ovr_th_hdrs = ["Thermal Energy Inflow Stream", "Heat (GJ/h)", "Power (MW)", "Thermal Consumptions & Dissipation", "Heat (GJ/h)", "Power (MW)", "% Total Heat"]
    for i, h in enumerate(ovr_th_hdrs):
        c = ws_ovr.cell(row=16, column=2 + i, value=h)
        c.font = tbl_hdr_font
        c.fill = steel_fill
        c.alignment = center_align
        c.border = header_border

    ovr_th_data = [
        ("Total Fuel Energy Fired (LHV Basis)", "=Inputs_Setpoints!$C$28", "=C17/3.6", "Theoretical Calcination (CaCO3 & MgCO3)", "=RawMeal_Clinker!$C$21", "=F17/3.6", "=F17/$C$25"),
        ("Sensible Heat in Raw Meal Feed (@ 60 °C)", "=Master_Stream_Table!$J$5", "=C18/3.6", "Exothermic Clinker Formation (C3S/C2S Credit)", -18.20, "=F18/3.6", "=F18/$C$25"),
        ("Cooling Ambient Air Enthalpy (@ 25 °C)", "=Clinker_Cooler_Balance!$E$19", "=C19/3.6", "Preheater Top Flue Gas Sensible Heat (@ 413 °C)", 188.42, "=F19/3.6", "=F19/$C$25"),
        ("Kiln Primary Air Fan Enthalpy (@ 35 °C)", 0.42, "=C20/3.6", "Cooler Vent Air Heat Loss (@ 258 °C)", "=Clinker_Cooler_Balance!$E$22", "=F20/3.6", "=F20/$C$25"),
        ("Fuel Sensible Enthalpies (Storage)", 3.25, "=C21/3.6", "Sensible Heat in Clinker Product (@ 90 °C)", "=Clinker_Cooler_Balance!$E$17", "=F21/3.6", "=F21/$C$25"),
        ("", "", "", "Rotary Kiln Shell Convection & Radiation Loss", "=Rotary_Kiln_Balance!$G$20", "=F22/3.6", "=F22/$C$25"),
        ("", "", "", "Precalciner & Preheater Vessel Shell Losses", 22.80, "=F23/3.6", "=F23/$C$25"),
        ("", "", "", "Clinker Cooler Structure Convection Loss", "=Clinker_Cooler_Balance!$E$23", "=F24/3.6", "=F24/$C$25"),
    ]

    for idx, (in_name, in_gj, in_mw, out_name, out_gj, out_mw, out_pct) in enumerate(ovr_th_data):
        r = 17 + idx  # Rows 17 to 24
        ws_ovr.cell(row=r, column=2, value=in_name).font = normal_font
        c_ingj = ws_ovr.cell(row=r, column=3, value=in_gj)
        c_ingj.number_format = "0.00" if str(in_gj).startswith("=") or isinstance(in_gj, float) else "@"
        c_ingj.alignment = right_align

        c_inmw = ws_ovr.cell(row=r, column=4, value=in_mw)
        c_inmw.number_format = "0.00" if str(in_mw).startswith("=") or isinstance(in_mw, float) else "@"
        c_inmw.alignment = right_align

        ws_ovr.cell(row=r, column=5, value=out_name).font = normal_font
        c_outgj = ws_ovr.cell(row=r, column=6, value=out_gj)
        c_outgj.number_format = "0.00" if str(out_gj).startswith("=") or isinstance(out_gj, float) else "@"
        c_outgj.alignment = right_align

        c_outmw = ws_ovr.cell(row=r, column=7, value=out_mw)
        c_outmw.number_format = "0.00" if str(out_mw).startswith("=") or isinstance(out_mw, float) else "@"
        c_outmw.alignment = right_align

        c_pct = ws_ovr.cell(row=r, column=8, value=out_pct)
        c_pct.number_format = "0.00%" if str(out_pct).startswith("=") else "@"
        c_pct.alignment = right_align

        for c in range(2, 9):
            ws_ovr.cell(row=r, column=c).border = table_border

    # Heat Totals
    r_ovr_ttot = 25
    ws_ovr.cell(row=r_ovr_ttot, column=2, value="TOTAL PLANT THERMAL INPUT").font = bold_font
    ws_ovr.cell(row=r_ovr_ttot, column=3, value="=SUM(C17:C21)").number_format = "0.00"
    ws_ovr.cell(row=r_ovr_ttot, column=4, value="=C25/3.6").number_format = "0.00"
    ws_ovr.cell(row=r_ovr_ttot, column=5, value="TOTAL HEAT CONSUMED & DISSIPATED").font = bold_font
    ws_ovr.cell(row=r_ovr_ttot, column=6, value="=SUM(F17:F24)").number_format = "0.00"
    ws_ovr.cell(row=r_ovr_ttot, column=7, value="=F25/3.6").number_format = "0.00"
    ws_ovr.cell(row=r_ovr_ttot, column=8, value="100.00%").font = bold_font
    for c in range(2, 9):
        cell = ws_ovr.cell(row=r_ovr_ttot, column=c)
        cell.font = bold_font
        cell.fill = total_fill
        cell.border = total_border

    # Format all column widths
    for ws in wb.worksheets:
        auto_fit_columns(ws, min_col=1, max_col=ws.max_column, pad=3)

    wb.save(filename)
    print(f"Workbook successfully regenerated: {filename}")

if __name__ == "__main__":
    build_simulation_workbook()
