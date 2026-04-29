import os
import re
import sqlite3
import xml.etree.ElementTree as ET

class MapProcessor:
    def __init__(self, source_svg_path):
        self.source_svg_path = source_svg_path
        self.namespace = "http://www.w3.org/2000/svg"
        ET.register_namespace('', self.namespace)
        
        self.paths = {}  # Normalized ID -> XML Element
        self.original_ids = {} # Normalized ID -> Original SVG ID
        self.viewbox = "0 0 1600 1000" # Default fallback
        self._load_source()

    def _normalize(self, text):
        """Standardizes strings for matching (lowercase, no underscores, stripped)."""
        if not text: return ""
        return str(text).lower().replace('_', ' ').strip()

    def _load_source(self):
        """Parses the source SVG and indexes all graphical elements by a normalized ID."""
        if not os.path.exists(self.source_svg_path):
            raise FileNotFoundError(f"Source SVG not found at: {self.source_svg_path}")

        tree = ET.parse(self.source_svg_path)
        root = tree.getroot()
        
        # Capture the original dimensions to maintain scale
        self.viewbox = root.get('viewBox', self.viewbox)

        # Index all elements that have an ID (path, polygon, rect, circle, etc.)
        object_count = 0
        for element in root.iter():
            # Check if element is in the SVG namespace
            if element.tag.endswith('path') or element.tag.endswith('polygon') or \
               element.tag.endswith('rect') or element.tag.endswith('circle') or \
               element.tag.endswith('ellipse') or element.tag.endswith('polyline'):
                
                path_id = element.get('id')
                if path_id:
                    norm_id = self._normalize(path_id)
                    self.paths[norm_id] = element
                    self.original_ids[norm_id] = path_id
                    object_count += 1
        
        print(f"📊 SVG Loaded: Indexed {object_count} graphical objects from '{self.source_svg_path}'")

    def extract_region(self, region_name, province_ids, output_path):
        """
        Creates a new SVG file containing the entire world map, 
        but highlights the specified province IDs.
        """
        # Create the root SVG element
        new_root = ET.Element("svg", {
            "viewBox": self.viewbox,
            "xmlns": self.namespace
        })

        # Add Tactical Styling Definitions
        defs = ET.SubElement(new_root, "defs")
        
        # Glow Filter
        filter_glow = ET.SubElement(defs, "filter", {
            "id": "glow", "x": "-20%", "y": "-20%", "width": "140%", "height": "140%"
        })
        ET.SubElement(filter_glow, "feGaussianBlur", {"stdDeviation": "2.5", "result": "blur"})
        ET.SubElement(filter_glow, "feComposite", {"in": "SourceGraphic", "in2": "blur", "operator": "over"})

        # CSS Styles - Differentiates background provinces from highlighted ones
        style = ET.SubElement(defs, "style")
        style.text = f"""
            svg {{ background-color: #020617; }}
            .province {{ 
                fill: #020617; 
                stroke: #1e293b; 
                stroke-width: 0.4; 
                transition: all 0.3s ease;
            }}
            .province.highlight {{ 
                fill: #0f172a; 
                stroke: #38bdf8; 
                stroke-width: 1.0; 
                filter: url(#glow);
                pointer-events: all;
            }}
            .province.highlight:hover {{ 
                fill: #1e1b4b; 
                stroke: #7dd3fc; 
                stroke-width: 2; 
            }}
            .label {{ 
                fill: #334155; 
                font-family: 'JetBrains Mono', monospace; 
                font-size: 14px; 
                text-transform: uppercase;
            }}
        """

        # Background Rect
        ET.SubElement(new_root, "rect", {"width": "100%", "height": "100%", "fill": "#020617"})

        # Separate layers for background and highlighted provinces
        # Layering ensures highlighted glows aren't obscured by background borders
        bg_group = ET.SubElement(new_root, "g", {"id": "world_background_layer"})
        hl_group = ET.SubElement(new_root, "g", {"id": f"highlight_layer_{region_name.replace(' ', '_')}"})

        highlight_set = {self._normalize(p_id) for p_id in province_ids}
        found_highlight_count = 0

        # Iterate through all indexed paths to build the layered map
        for norm_id, original_element in self.paths.items():
            original_svg_id = self.original_ids[norm_id]
            tag_name = original_element.tag.split('}')[-1]
            
            is_highlight = norm_id in highlight_set
            
            if is_highlight:
                target_group = hl_group
                css_class = "province highlight"
                found_highlight_count += 1
            else:
                target_group = bg_group
                css_class = "province"
            
            # Create the new element in the appropriate layer
            new_element = ET.SubElement(target_group, tag_name, {
                "id": original_svg_id,
                "class": css_class
            })
            
            # Copy geometry and coordinate attributes
            for attr, value in original_element.attrib.items():
                if attr not in ['id', 'class']:
                    new_element.set(attr, value)

        # Add Title Label
        label = ET.SubElement(new_root, "text", {"x": "20", "y": "40", "class": "label"})
        label.text = f"NATIONAL_REGISTRY // {region_name}"

        # Write to file
        tree = ET.ElementTree(new_root)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        return found_highlight_count

    def process_all_countries(self, db_path, output_dir):
        """
        Queries the database for all countries and generates an SVG map for each
        by collecting province shapes based on their IDs and highlighting them 
        against the global background.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        if not os.path.exists(db_path):
            print(f"❌ Database not found at: {db_path}")
            return

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            # Get list of all unique countries
            cursor.execute("SELECT DISTINCT Country FROM provinces")
            countries = [row[0] for row in cursor.fetchall()]

            for country in countries:
                if not country: continue
                
                # Get all IDs for provinces belonging to this country
                cursor.execute("SELECT id FROM provinces WHERE Country = ?", (country,))
                province_ids = [row[0] for row in cursor.fetchall()]
                
                safe_name = country.replace(' ', '_')
                file_path = os.path.join(output_dir, f"Map_{safe_name}.svg")
                
                count = self.extract_region(country, province_ids, file_path)
                if count > 0:
                    print(f"✅ Generated world map for {country} ({count}/{len(province_ids)} provinces highlighted)")
                else:
                    print(f"⚠️  Generated base map for {country} (0 provinces highlighted). Check DB-to-SVG IDs.")

        finally:
            conn.close()

# --- ENTRY POINT ---
if __name__ == "__main__":
    # Project paths
    SOURCE_SVG = "obsidian-vault/Assets/Maps/Map Layer.svg"
    DB_PATH = "world_data.db"
    OUTPUT_DIR = "obsidian-vault/Assets/Maps"

    try:
        processor = MapProcessor(SOURCE_SVG)
        processor.process_all_countries(DB_PATH, OUTPUT_DIR)
    except Exception as e:
        print(f"❌ Error during processing: {e}")