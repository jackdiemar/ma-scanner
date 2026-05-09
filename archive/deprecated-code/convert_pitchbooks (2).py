import pandas as pd
import os
from pathlib import Path

def convert_pitchbooks_to_csv(input_folder, output_file='combined_output.csv'):
    """
    Converts multiple Excel files with 'General Information' tab into one CSV.
    Takes vertical data (Field/Value pairs) and converts to horizontal rows.
    """
    
    all_data = []
    
    # Get all Excel files in the folder
    excel_files = list(Path(input_folder).glob('*.xlsx')) + list(Path(input_folder).glob('*.xls'))
    
    print(f"Found {len(excel_files)} Excel files to process...")
    
    for file_path in excel_files:
        try:
            print(f"\nProcessing: {file_path.name}")
            
            # Read the 'General Information' sheet
            df = pd.read_excel(file_path, sheet_name='General Information')
            
            # CRITICAL: Extract PitchBook ID from cell B2 (row index 1, column index 1)
            pitchbook_id = None
            try:
                if len(df) > 1:  # Make sure we have at least 2 rows
                    pitchbook_id = df.iloc[1, 1]  # B2 (row 1, column 1 in 0-indexed)
                    if pd.notna(pitchbook_id):
                        pitchbook_id = str(pitchbook_id).strip()
                        print(f"  Found PitchBook ID: {pitchbook_id}")
                    else:
                        print(f"  WARNING: B2 is empty in {file_path.name}")
            except Exception as e:
                print(f"  WARNING: Could not read B2 from {file_path.name}: {e}")
            
            # The data should have 'Field' in column A and 'Value' in column B
            # Create a dictionary from the Field/Value pairs
            data_dict = {}
            
            # ALWAYS add PitchBook ID as the FIRST item
            if pitchbook_id and pitchbook_id != '':
                data_dict['PitchBook ID'] = pitchbook_id
            else:
                data_dict['PitchBook ID'] = 'MISSING'
                print(f"  ⚠️  WARNING: No PitchBook ID found for {file_path.name}")
            
            for index, row in df.iterrows():
                field = row.iloc[0]  # First column (Field)
                value = row.iloc[1]  # Second column (Value)
                
                # Skip if field is empty or NaN
                if pd.notna(field) and str(field).strip():
                    field_name = str(field).strip()
                    # Don't duplicate PitchBook ID if it's already been added
                    if field_name not in data_dict:
                        data_dict[field_name] = value
            
            # Add the filename as a reference at the end
            data_dict['Source_File'] = file_path.name
            
            all_data.append(data_dict)
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {str(e)}")
            continue
    
    # Convert list of dictionaries to DataFrame
    if all_data:
        result_df = pd.DataFrame(all_data)
        
        # Make sure PitchBook ID is the FIRST column
        if 'PitchBook ID' in result_df.columns:
            cols = ['PitchBook ID'] + [col for col in result_df.columns if col != 'PitchBook ID']
            result_df = result_df[cols]
        
        # Save to CSV
        result_df.to_csv(output_file, index=False)
        print(f"\n✅ Successfully created {output_file}")
        print(f"✅ Total records: {len(result_df)}")
        print(f"✅ Total columns: {len(result_df.columns)}")
    else:
        print("No data was processed!")

if __name__ == "__main__":
    # ==================== INSTRUCTIONS ====================
    # 1. Make sure you have Python installed
    # 2. Install required packages: pip install pandas openpyxl
    #    (or: python3 -m pip install pandas openpyxl)
    # 3. Put this script in the SAME FOLDER as your Excel files
    # 4. Open Terminal (Mac) or Command Prompt (Windows)
    # 5. Navigate to your folder: cd "/path/to/your/folder"
    # 6. Run: python3 convert_pitchbooks.py
    # 7. Your output will be: combined_pitchbooks.csv
    #
    # NOTE: This script extracts the PitchBook ID from cell B2 
    # in the "General Information" tab of each Excel file.
    # ======================================================
    
    # Change this to your folder path:
    folder_path = "."  # Current folder - change if needed (e.g., "/Users/jack/Documents/PitchBooks")
    
    # Output CSV name
    output_csv = "combined_pitchbooks.csv"
    
    convert_pitchbooks_to_csv(folder_path, output_csv)
    
    print("\n✅ Done! Check for", output_csv)
