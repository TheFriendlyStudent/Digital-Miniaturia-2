import pandas as pd
import sqlite3

# 1. Load your Province CSV
df = pd.read_csv('provinces_source.csv')

# 2. Connect to (or create) your world database
conn = sqlite3.connect('world_data.db')

# 3. Migrate the data to a SQL table
# This automatically creates the schema based on your CSV headers
df.to_sql('provinces', conn, if_exists='replace', index=False)

conn.close()
print("Migration to SQLite complete.")

def generate_obsidian_pages():
    conn = sqlite3.connect('world_data.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM provinces")
    
    # Get column names to map to your template
    columns = [description[0] for description in cursor.description]
    
    for row in cursor.fetchall():
        data = dict(zip(columns, row))
        
        # Format the Markdown content
        content = f"""---
title: {data['province_name']}
country: [[{data['parent_country']}]]
population: {data['population']}
type: province
---
# {data['province_name']}
**Part of:** [[{data['parent_country']}]]

## 📊 Quick Stats
* **Governor:** [[{data['governor']}]]
* **Climate:** {data['climate']}

{data['description']}

**Tags:** #province #encyclopedia
"""
        # Save to your Obsidian Vault folder
        file_name = f"obsidian-vault/Encyclopedia/Provinces/{data['province_name']}.md"
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(content)

    conn.close()