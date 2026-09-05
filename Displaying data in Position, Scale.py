#Display data


import pandas as pd

# Load your Excel file
df = pd.read_excel("Data Extraction and Multileaders Sample Coordinates.xlsx")


# Example: show only Position and Scale columns
print("Position and Scale columns")
PosAndScale = df[['Position X', 'Position Y', 'Position Z', 'Scale X', 'Scale Y', 'Scale Z']]
print(PosAndScale)

PosAndScale.to_csv("Data Extraction and Multileaders Sample Coordinates.csv", index=False)
