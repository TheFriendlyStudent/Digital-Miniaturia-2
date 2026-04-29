import pandas as pd
import sqlite3
from pathlib import Path

# Load your CSV
df = pd.read_csv('provinces_source.csv')

# 1. Update the SQLite Database
conn = sqlite3.connect('world_data.db')
df.to_sql('provinces', conn, if_exists='replace', index=False)

# 2. Generate Obsidian Wiki Pages
def generate_wiki(row):
    # Create the file path
    path = Path(f"Encyclopedia/Provinces/{row['Name']}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    
    content = f"""---
id: {row['id']}
country: [[{row['Country']}]]
population: {row['Population']}
tags: #province #geo/{row['Geography'].lower()}
---
# {row['Name']}
A province located within the borders of [[{row['Country']}]].

## 📊 Statistics
| Statistic | Value |
| :--- | :--- |
| **Dominant Language** | {row['Language']} |
| **Geography** | {row['Geography']} |
| **Settlement** | Tier {row['Settlement Level']} ({row['Settlement Type']}) |

## 🛠️ Economy & Production
This province is a key producer of resources for [[{row['Country']}]]:
* **Food Production:** {row['Food Production']} units/cycle
* **Fuel Production:** {row['Fuel Production']} units/cycle

---
[[All Provinces]] | [[{row['Country']}#Provinces|View in Country Map]]
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# Apply the function to every row
df.apply(generate_wiki, axis=1)
conn.close()