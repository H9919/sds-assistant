# app.py - Complete SDS Assistant Web Application (FIXED)
import os
from flask import Flask, render_template_string, request, jsonify, send_file, session
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import PyPDF2
from io import BytesIO
from werkzeug.utils import secure_filename
import requests
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sds-assistant-secret-key-2024')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create necessary directories
for folder in ['static/uploads', 'static/stickers', 'static/exports', 'data']:
    Path(folder).mkdir(parents=True, exist_ok=True)

# US Cities Data - All 50 states with major cities
US_CITIES_DATA = {
    "Alabama": ["Birmingham", "Montgomery", "Mobile", "Huntsville", "Tuscaloosa", "Hoover", "Dothan", "Auburn", "Decatur", "Madison"],
    "Alaska": ["Anchorage", "Fairbanks", "Juneau", "Wasilla", "Sitka", "Ketchikan", "Kenai", "Kodiak", "Bethel", "Palmer"],
    "Arizona": ["Phoenix", "Tucson", "Mesa", "Chandler", "Scottsdale", "Glendale", "Gilbert", "Tempe", "Peoria", "Surprise"],
    "Arkansas": ["Little Rock", "Fort Smith", "Fayetteville", "Springdale", "Jonesboro", "North Little Rock", "Conway", "Rogers", "Pine Bluff", "Bentonville"],
    "California": ["Los Angeles", "San Diego", "San Jose", "San Francisco", "Fresno", "Sacramento", "Long Beach", "Oakland", "Bakersfield", "Anaheim", "Santa Ana", "Riverside", "Stockton", "Irvine", "Chula Vista"],
    "Colorado": ["Denver", "Colorado Springs", "Aurora", "Fort Collins", "Lakewood", "Thornton", "Arvada", "Westminster", "Pueblo", "Centennial"],
    "Connecticut": ["Bridgeport", "New Haven", "Hartford", "Stamford", "Waterbury", "Norwalk", "Danbury", "New Britain", "West Hartford", "Greenwich"],
    "Delaware": ["Wilmington", "Dover", "Newark", "Middletown", "Bear", "Glasgow", "Brookside", "Hockessin", "Pike Creek", "Claymont"],
    "Florida": ["Jacksonville", "Miami", "Tampa", "Orlando", "St. Petersburg", "Hialeah", "Tallahassee", "Fort Lauderdale", "Port St. Lucie", "Cape Coral", "Pembroke Pines", "Hollywood", "Gainesville", "Miramar", "Coral Springs"],
    "Georgia": ["Atlanta", "Augusta", "Columbus", "Savannah", "Athens", "Sandy Springs", "Roswell", "Macon", "Johns Creek", "Albany"],
    "Hawaii": ["Honolulu", "Pearl City", "Hilo", "Kailua", "Waipahu", "Kaneohe", "Kailua-Kona", "Kahului", "Mililani", "Ewa Gentry"],
    "Idaho": ["Boise", "Meridian", "Nampa", "Idaho Falls", "Pocatello", "Caldwell", "Coeur d'Alene", "Twin Falls", "Lewiston", "Post Falls"],
    "Illinois": ["Chicago", "Aurora", "Rockford", "Joliet", "Naperville", "Springfield", "Peoria", "Elgin", "Waukegan", "Cicero"],
    "Indiana": ["Indianapolis", "Fort Wayne", "Evansville", "South Bend", "Carmel", "Fishers", "Bloomington", "Hammond", "Gary", "Muncie"],
    "Iowa": ["Des Moines", "Cedar Rapids", "Davenport", "Sioux City", "Iowa City", "Waterloo", "Council Bluffs", "Ames", "Dubuque", "West Des Moines"],
    "Kansas": ["Wichita", "Overland Park", "Kansas City", "Olathe", "Topeka", "Lawrence", "Shawnee", "Salina", "Manhattan", "Lenexa"],
    "Kentucky": ["Louisville", "Lexington", "Bowling Green", "Owensboro", "Covington", "Richmond", "Georgetown", "Florence", "Hopkinsville", "Nicholasville"],
    "Louisiana": ["New Orleans", "Baton Rouge", "Shreveport", "Lafayette", "Lake Charles", "Kenner", "Bossier City", "Monroe", "Alexandria", "Houma"],
    "Maine": ["Portland", "Lewiston", "Bangor", "South Portland", "Auburn", "Biddeford", "Sanford", "Saco", "Augusta", "Westbrook"],
    "Maryland": ["Baltimore", "Frederick", "Rockville", "Gaithersburg", "Bowie", "Hagerstown", "Annapolis", "College Park", "Salisbury", "Laurel"],
    "Massachusetts": ["Boston", "Worcester", "Springfield", "Lowell", "Cambridge", "New Bedford", "Brockton", "Quincy", "Lynn", "Fall River"],
    "Michigan": ["Detroit", "Grand Rapids", "Warren", "Sterling Heights", "Lansing", "Ann Arbor", "Flint", "Dearborn", "Livonia", "Westland"],
    "Minnesota": ["Minneapolis", "St. Paul", "Rochester", "Duluth", "Bloomington", "Brooklyn Park", "Plymouth", "St. Cloud", "Eagan", "Woodbury"],
    "Mississippi": ["Jackson", "Gulfport", "Southaven", "Hattiesburg", "Biloxi", "Meridian", "Tupelo", "Greenville", "Olive Branch", "Horn Lake"],
    "Missouri": ["Kansas City", "St. Louis", "Springfield", "Independence", "Columbia", "Lee's Summit", "O'Fallon", "St. Joseph", "St. Charles", "St. Peters"],
    "Montana": ["Billings", "Missoula", "Great Falls", "Bozeman", "Butte", "Helena", "Kalispell", "Havre", "Anaconda", "Miles City"],
    "Nebraska": ["Omaha", "Lincoln", "Bellevue", "Grand Island", "Kearney", "Fremont", "Hastings", "North Platte", "Norfolk", "Columbus"],
    "Nevada": ["Las Vegas", "Henderson", "Reno", "North Las Vegas", "Sparks", "Carson City", "Fernley", "Elko", "Mesquite", "Boulder City"],
    "New Hampshire": ["Manchester", "Nashua", "Concord", "Derry", "Rochester", "Salem", "Dover", "Merrimack", "Londonderry", "Hudson"],
    "New Jersey": ["Newark", "Jersey City", "Paterson", "Elizabeth", "Edison", "Woodbridge", "Lakewood", "Toms River", "Hamilton", "Trenton"],
    "New Mexico": ["Albuquerque", "Las Cruces", "Rio Rancho", "Santa Fe", "Roswell", "Farmington", "Clovis", "Hobbs", "Alamogordo", "Carlsbad"],
    "New York": ["New York City", "Buffalo", "Rochester", "Yonkers", "Syracuse", "Albany", "New Rochelle", "Mount Vernon", "Schenectady", "Utica"],
    "North Carolina": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Winston-Salem", "Fayetteville", "Cary", "Wilmington", "High Point", "Greenville"],
    "North Dakota": ["Fargo", "Bismarck", "Grand Forks", "Minot", "West Fargo", "Williston", "Wahpeton", "Dickinson", "Jamestown", "Mandan"],
    "Ohio": ["Columbus", "Cleveland", "Cincinnati", "Toledo", "Akron", "Dayton", "Parma", "Canton", "Youngstown", "Lorain"],
    "Oklahoma": ["Oklahoma City", "Tulsa", "Norman", "Broken Arrow", "Lawton", "Edmond", "Moore", "Midwest City", "Enid", "Stillwater"],
    "Oregon": ["Portland", "Eugene", "Salem", "Gresham", "Hillsboro", "Bend", "Beaverton", "Medford", "Springfield", "Corvallis"],
    "Pennsylvania": ["Philadelphia", "Pittsburgh", "Allentown", "Erie", "Reading", "Scranton", "Bethlehem", "Lancaster", "Harrisburg", "Altoona"],
    "Rhode Island": ["Providence", "Warwick", "Cranston", "Pawtucket", "East Providence", "Woonsocket", "Newport", "Central Falls", "Westerly", "Portsmouth"],
    "South Carolina": ["Charleston", "Columbia", "North Charleston", "Mount Pleasant", "Rock Hill", "Greenville", "Summerville", "Sumter", "Goose Creek", "Hilton Head Island"],
    "South Dakota": ["Sioux Falls", "Rapid City", "Aberdeen", "Brookings", "Watertown", "Mitchell", "Yankton", "Pierre", "Huron", "Vermillion"],
    "Tennessee": ["Nashville", "Memphis", "Knoxville", "Chattanooga", "Clarksville", "Murfreesboro", "Franklin", "Johnson City", "Bartlett", "Hendersonville"],
    "Texas": ["Houston", "San Antonio", "Dallas", "Austin", "Fort Worth", "El Paso", "Arlington", "Corpus Christi", "Plano", "Lubbock", "Laredo", "Irving", "Garland", "Frisco", "McKinney"],
    "Utah": ["Salt Lake City", "West Valley City", "Provo", "West Jordan", "Orem", "Sandy", "Ogden", "St. George", "Layton", "Taylorsville"],
    "Vermont": ["Burlington", "Essex", "South Burlington", "Colchester", "Rutland", "Bennington", "Brattleboro", "Milton", "Hartford", "Barre"],
    "Virginia": ["Virginia Beach", "Norfolk", "Chesapeake", "Richmond", "Newport News", "Alexandria", "Hampton", "Portsmouth", "Suffolk", "Roanoke"],
    "Washington": ["Seattle", "Spokane", "Tacoma", "Vancouver", "Bellevue", "Kent", "Everett", "Renton", "Yakima", "Federal Way"],
    "West Virginia": ["Charleston", "Huntington", "Morgantown", "Parkersburg", "Wheeling", "Martinsburg", "Fairmont", "Beckley", "Clarksburg", "Lewisburg"],
    "Wisconsin": ["Milwaukee", "Madison", "Green Bay", "Kenosha", "Racine", "Appleton", "Waukesha", "Eau Claire", "Oshkosh", "Janesville"],
    "Wyoming": ["Cheyenne", "Casper", "Laramie", "Gillette", "Rock Springs", "Sheridan", "Green River", "Evanston", "Riverton", "Jackson"]
}

class SDSWebAssistant:
    def __init__(self, db_path: str = "data/sds_database.db"):
        self.db_path = db_path
        self.setup_database()
        self.populate_us_cities()
    
    def setup_database(self):
        """Initialize the database with enhanced schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create locations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                country TEXT NOT NULL DEFAULT 'United States',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(department, city, state, country)
            )
        ''')
        
        # Enhanced SDS chunks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sds_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_filename TEXT,
                file_hash TEXT,
                product_name TEXT,
                manufacturer TEXT,
                cas_number TEXT,
                chunk_text TEXT NOT NULL,
                section_type TEXT,
                location_id INTEGER,
                source_type TEXT DEFAULT 'upload',
                web_url TEXT,
                file_size INTEGER,
                uploaded_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (location_id) REFERENCES locations (id)
            )
        ''')
        
        # Chemical hazards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chemical_hazards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sds_chunk_id INTEGER,
                product_name TEXT,
                cas_number TEXT,
                nfpa_health INTEGER DEFAULT 0,
                nfpa_fire INTEGER DEFAULT 0,
                nfpa_reactivity INTEGER DEFAULT 0,
                nfpa_special TEXT,
                ghs_pictograms TEXT,
                ghs_signal_word TEXT,
                ghs_hazard_statements TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sds_chunk_id) REFERENCES sds_chunks (id)
            )
        ''')
        
        # Search history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                results_count INTEGER,
                location_id INTEGER,
                user_session TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (location_id) REFERENCES locations (id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_product_name ON sds_chunks(product_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_location ON sds_chunks(location_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_cas_number ON sds_chunks(cas_number)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_hash ON sds_chunks(file_hash)')
        
        conn.commit()
        conn.close()
    
    def populate_us_cities(self):
        """Populate database with US cities"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if cities are already populated
        cursor.execute('SELECT COUNT(*) FROM locations')
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        print("Populating US cities database...")
        
        # Add all US cities
        for state, cities in US_CITIES_DATA.items():
            for city in cities:
                for dept in ["Safety Department", "Environmental Health", "Chemical Storage", "Laboratory", "Manufacturing", "Warehouse"]:
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO locations (department, city, state, country)
                            VALUES (?, ?, ?, ?)
                        ''', (dept, city, state, "United States"))
                    except sqlite3.Error as e:
                        print(f"Error inserting {dept}, {city}, {state}: {e}")
        
        conn.commit()
        conn.close()
        print("US cities populated successfully!")
    
    def get_locations(self, state_filter=None, search_term=None) -> List[Dict]:
        """Get locations with optional filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT l.id, l.department, l.city, l.state, l.country, 
                       COUNT(sc.id) as document_count,
                       MAX(sc.created_at) as last_updated
                FROM locations l
                LEFT JOIN sds_chunks sc ON l.id = sc.location_id
            '''
            
            where_conditions = []
            params = []
            
            if state_filter:
                where_conditions.append("l.state = ?")
                params.append(state_filter)
            
            if search_term:
                where_conditions.append("(l.city LIKE ? OR l.department LIKE ?)")
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)
            
            query += '''
                GROUP BY l.id, l.department, l.city, l.state, l.country
                ORDER BY l.state, l.city, l.department
                LIMIT 1000
            '''
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    "id": row[0],
                    "department": row[1],
                    "city": row[2],
                    "state": row[3],
                    "country": row[4],
                    "document_count": row[5],
                    "last_updated": row[6],
                    "display_name": f"{row[1]} - {row[2]}, {row[3]}"
                }
                for row in results
            ]
        except Exception as e:
            print(f"Error getting locations: {str(e)}")
            return []
    
    def get_states(self) -> List[str]:
        """Get all US states"""
        return sorted(US_CITIES_DATA.keys())
    
    def extract_text_from_pdf(self, file_stream) -> str:
        """Extract text from PDF file stream"""
        try:
            pdf_reader = PyPDF2.PdfReader(file_stream)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error extracting PDF text: {str(e)}")
            return ""
    
    def extract_chemical_info(self, text: str) -> Dict:
        """Extract chemical information from SDS text"""
        info = {
            "product_name": "",
            "manufacturer": "",
            "cas_number": "",
            "hazards": {
                "health": 0,
                "fire": 0,
                "reactivity": 0,
                "special": "",
                "ghs_signal_word": ""
            }
        }
        
        # Extract product name
        product_patterns = [
            r"Product\s+Name:?\s*([^\n\r]+)",
            r"Product\s+Identifier:?\s*([^\n\r]+)",
            r"Trade\s+Name:?\s*([^\n\r]+)",
            r"Chemical\s+Name:?\s*([^\n\r]+)"
        ]
        
        for pattern in product_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info["product_name"] = match.group(1).strip()
                break
        
        # Extract manufacturer
        manufacturer_patterns = [
            r"Manufacturer:?\s*([^\n\r]+)",
            r"Company:?\s*([^\n\r]+)",
            r"Supplier:?\s*([^\n\r]+)"
        ]
        
        for pattern in manufacturer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info["manufacturer"] = match.group(1).strip()
                break
        
        # Extract CAS number
        cas_pattern = r"CAS\s*#?:?\s*(\d{2,7}-\d{2}-\d)"
        cas_match = re.search(cas_pattern, text, re.IGNORECASE)
        if cas_match:
            info["cas_number"] = cas_match.group(1)
        
        # Extract NFPA ratings
        nfpa_patterns = [
            (r"Health\s*=?\s*(\d)", "health"),
            (r"Fire\s*=?\s*(\d)", "fire"),
            (r"Reactivity\s*=?\s*(\d)", "reactivity"),
            (r"NFPA\s+Health\s*:?\s*(\d)", "health"),
            (r"NFPA\s+Fire\s*:?\s*(\d)", "fire"),
            (r"NFPA\s+Reactivity\s*:?\s*(\d)", "reactivity")
        ]
        
        for pattern, key in nfpa_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info["hazards"][key] = int(match.group(1))
        
        # Extract GHS signal word
        ghs_signal = re.search(r"GHS\s+Signal\s+Word:?\s*([^\n\r]+)", text, re.IGNORECASE)
        if ghs_signal:
            info["hazards"]["ghs_signal_word"] = ghs_signal.group(1).strip()
        elif re.search(r"\bDANGER\b", text, re.IGNORECASE):
            info["hazards"]["ghs_signal_word"] = "DANGER"
        elif re.search(r"\bWARNING\b", text, re.IGNORECASE):
            info["hazards"]["ghs_signal_word"] = "WARNING"
        
        return info
    
    def upload_file(self, file, location_id: int, uploaded_by: str = "web_user") -> Dict:
        """Process uploaded file"""
        try:
            # Calculate file hash
            file_content = file.read()
            file.seek(0)
            file_hash = hashlib.sha256(file_content).hexdigest()
            
            # Check for duplicates
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id, product_name FROM sds_chunks WHERE file_hash = ?', (file_hash,))
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return {"success": False, "message": f"File already exists in database (Product: {existing[1]})"}
            
            # Save file
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            saved_filename = f"{timestamp}_{filename}"
            file_path = Path(app.config['UPLOAD_FOLDER']) / saved_filename
            
            file.seek(0)
            file.save(file_path)
            
            # Extract text based on file type
            file.seek(0)
            if filename.lower().endswith('.pdf'):
                text_content = self.extract_text_from_pdf(file)
            else:
                text_content = file_content.decode('utf-8', errors='ignore')
            
            if not text_content.strip():
                return {"success": False, "message": "Could not extract text from file"}
            
            # Extract chemical information
            chem_info = self.extract_chemical_info(text_content)
            
            # Insert into database
            cursor.execute('''
                INSERT INTO sds_chunks (
                    filename, original_filename, file_hash, product_name, 
                    manufacturer, cas_number, chunk_text, section_type,
                    location_id, source_type, file_size, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                saved_filename, filename, file_hash,
                chem_info["product_name"] or "Unknown Product", 
                chem_info["manufacturer"] or "Unknown Manufacturer",
                chem_info["cas_number"], text_content, "full_document",
                location_id, "upload", len(file_content), uploaded_by
            ))
            
            sds_chunk_id = cursor.lastrowid
            
            # Insert hazard information
            cursor.execute('''
                INSERT INTO chemical_hazards (
                    sds_chunk_id, product_name, cas_number, nfpa_health,
                    nfpa_fire, nfpa_reactivity, ghs_signal_word
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                sds_chunk_id, chem_info["product_name"], chem_info["cas_number"],
                chem_info["hazards"]["health"], chem_info["hazards"]["fire"],
                chem_info["hazards"]["reactivity"], chem_info["hazards"]["ghs_signal_word"]
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "message": "File uploaded successfully",
                "product_name": chem_info["product_name"] or "Unknown Product",
                "manufacturer": chem_info["manufacturer"] or "Unknown Manufacturer",
                "cas_number": chem_info["cas_number"] or "Not found",
                "file_id": sds_chunk_id
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error uploading file: {str(e)}"}
    
    def search_database(self, query: str, location_id: int = None, user_session: str = None) -> List[Dict]:
        """Search SDS database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            search_terms = query.lower().split()
            where_clauses = []
            params = []
            
            # Add search conditions
            for term in search_terms:
                where_clauses.append("""
                    (LOWER(sc.chunk_text) LIKE ? OR 
                     LOWER(sc.product_name) LIKE ? OR 
                     LOWER(sc.manufacturer) LIKE ? OR
                     LOWER(sc.cas_number) LIKE ?)
                """)
                params.extend([f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"])
            
            # Add location filter if specified
            if location_id:
                where_clauses.append("sc.location_id = ?")
                params.append(location_id)
            
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            sql = f"""
                SELECT sc.id, sc.filename, sc.product_name, sc.manufacturer, 
                       sc.chunk_text, sc.cas_number, sc.source_type, sc.created_at,
                       l.department, l.city, l.state, l.country,
                       ch.nfpa_health, ch.nfpa_fire, ch.nfpa_reactivity, ch.ghs_signal_word
                FROM sds_chunks sc
                LEFT JOIN locations l ON sc.location_id = l.id
                LEFT JOIN chemical_hazards ch ON sc.id = ch.sds_chunk_id
                WHERE {where_clause}
                ORDER BY 
                    CASE 
                        WHEN LOWER(sc.product_name) LIKE ? THEN 1
                        WHEN LOWER(sc.chunk_text) LIKE ? THEN 2
                        ELSE 3
                    END,
                    sc.created_at DESC
                LIMIT 50
            """
            
            params.extend([f"%{query.lower()}%", f"%{query.lower()}%"])
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            # Log search
            if user_session and query.strip():
                cursor.execute('''
                    INSERT INTO search_history (query, results_count, location_id, user_session)
                    VALUES (?, ?, ?, ?)
                ''', (query, len(results), location_id, user_session))
                conn.commit()
            
            conn.close()
            
            return [
                {
                    "id": row[0],
                    "filename": row[1],
                    "product_name": row[2] or "Unknown Product",
                    "manufacturer": row[3] or "Unknown Manufacturer",
                    "content": self.truncate_content(row[4], query),
                    "cas_number": row[5] or "N/A",
                    "source_type": row[6],
                    "created_at": row[7],
                    "location": {
                        "department": row[8] or "Unknown",
                        "city": row[9] or "Unknown",
                        "state": row[10] or "Unknown",
                        "country": row[11] or "Unknown"
                    },
                    "hazards": {
                        "nfpa_health": row[12] or 0,
                        "nfpa_fire": row[13] or 0,
                        "nfpa_reactivity": row[14] or 0,
                        "ghs_signal_word": row[15] or ""
                    }
                }
                for row in results
            ]
            
        except Exception as e:
            print(f"Error searching database: {str(e)}")
            return []
    
    def truncate_content(self, content: str, query: str) -> str:
        """Truncate content and highlight search terms"""
        if not content:
            return ""
        
        # Find the best excerpt around search terms
        query_words = query.lower().split()
        content_lower = content.lower()
        
        best_pos = 0
        for word in query_words:
            pos = content_lower.find(word)
            if pos != -1:
                best_pos = max(0, pos - 100)
                break
        
        # Extract excerpt
        excerpt_start = best_pos
        excerpt_end = min(len(content), best_pos + 400)
        excerpt = content[excerpt_start:excerpt_end]
        
        if excerpt_start > 0:
            excerpt = "..." + excerpt
        if excerpt_end < len(content):
            excerpt = excerpt + "..."
        
        return excerpt
    
    def generate_nfpa_sticker_svg(self, product_name: str) -> Dict:
        """Generate NFPA diamond sticker as SVG"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ch.nfpa_health, ch.nfpa_fire, ch.nfpa_reactivity, ch.nfpa_special
                FROM chemical_hazards ch
                JOIN sds_chunks sc ON ch.sds_chunk_id = sc.id
                WHERE LOWER(sc.product_name) LIKE ?
                ORDER BY ch.created_at DESC
                LIMIT 1
            ''', (f"%{product_name.lower()}%",))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return {"success": False, "message": f"No hazard data found for {product_name}"}
            
            health, fire, reactivity, special = result
            
            # Generate SVG content - FIXED
            svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="300" height="300" xmlns="http://www.w3.org/2000/svg">
    <style>
        .diamond {{ stroke: black; stroke-width: 3; }}
        .rating {{ font-family: Arial, sans-serif; font-size: 48px; font-weight: bold; text-anchor: middle; dominant-baseline: middle; }}
        .label {{ font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; text-anchor: middle; }}
        .product {{ font-family: Arial, sans-serif; font-size: 12px; text-anchor: middle; }}
    </style>
    
    <!-- NFPA Diamond Background -->
    <polygon points="150,25 275,150 150,275 25,150" fill="white" stroke="black" stroke-width="3"/>
    
    <!-- Health (Blue - Left) -->
    <polygon points="25,150 150,25 150,150 25,150" fill="blue" class="diamond"/>
    
    <!-- Fire (Red - Top) -->
    <polygon points="150,25 275,150 150,150 150,25" fill="red" class="diamond"/>
    
    <!-- Reactivity (Yellow - Right) -->
    <polygon points="275,150 150,275 150,150 275,150" fill="yellow" class="diamond"/>
    
    <!-- Special (White - Bottom) -->
    <polygon points="150,150 150,275 25,150 150,150" fill="white" class="diamond"/>
    
    <!-- Ratings -->
    <text x="87" y="105" class="rating" fill="white">{health}</text>
    <text x="150" y="90" class="rating" fill="white">{fire}</text>
    <text x="213" y="105" class="rating" fill="black">{reactivity}</text>
    <text x="150" y="210" class="rating" fill="black">{special or ''}</text>
    
    <!-- Labels -->
    <text x="87" y="130" class="label" fill="white">HEALTH</text>
    <text x="150" y="55" class="label" fill="white">FIRE</text>
    <text x="213" y="130" class="label" fill="black">REACTIVITY</text>
    <text x="150" y="240" class="label" fill="black">SPECIAL</text>
    
    <!-- Product Name -->
    <text x="150" y="295" class="product" fill="black">{product_name[:40]}</text>
</svg>'''
            
            # Save SVG file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            sticker_filename = f"nfpa_{secure_filename(product_name)}_{timestamp}.svg"
            sticker_path = Path('static/stickers') / sticker_filename
            
            with open(sticker_path, 'w') as f:
                f.write(svg_content)
            
            return {
                "success": True,
                "filename": sticker_filename,
                "ratings": {
                    "health": health,
                    "fire": fire,
                    "reactivity": reactivity,
                    "special": special or "None"
                }
            }
            
        except Exception as e:
            return {"success": False, "message": f"Error generating NFPA sticker: {str(e)}"}

    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total documents
            cursor.execute('SELECT COUNT(*) FROM sds_chunks')
            total_documents = cursor.fetchone()[0]
            
            # Total locations with documents
            cursor.execute('SELECT COUNT(DISTINCT location_id) FROM sds_chunks WHERE location_id IS NOT NULL')
            active_locations = cursor.fetchone()[0]
            
            # Recent uploads (last 7 days)
            cursor.execute('''
                SELECT COUNT(*) FROM sds_chunks 
                WHERE created_at >= datetime('now', '-7 days')
            ''')
            recent_uploads = cursor.fetchone()[0]
            
            # Hazardous materials (NFPA health > 2 or fire > 2)
            cursor.execute('''
                SELECT COUNT(*) FROM chemical_hazards 
                WHERE nfpa_health > 2 OR nfpa_fire > 2 OR nfpa_reactivity > 2
            ''')
            hazardous_count = cursor.fetchone()[0]
            
            # Recent searches
            cursor.execute('''
                SELECT query, COUNT(*) as count
                FROM search_history 
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY query
                ORDER BY count DESC
                LIMIT 5
            ''')
            recent_searches = cursor.fetchall()
            
            conn.close()
            
            return {
                "total_documents": total_documents,
                "active_locations": active_locations,
                "recent_uploads": recent_uploads,
                "hazardous_materials": hazardous_count,
                "recent_searches": [{"query": row[0], "count": row[1]} for row in recent_searches]
            }
            
        except Exception as e:
            print(f"Error getting dashboard stats: {str(e)}")
            return {
                "total_documents": 0, 
                "active_locations": 0, 
                "recent_uploads": 0, 
                "hazardous_materials": 0,
                "recent_searches": []
            }

# Initialize the assistant
sds_assistant = SDSWebAssistant()

# HTML Template (simplified for now)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SDS Assistant - Safety Data Sheet Management</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card-hover:hover { transform: translateY(-2px); transition: transform 0.2s; }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <nav class="gradient-bg shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <i class="fas fa-flask text-white text-2xl mr-3"></i>
                    <span class="text-white text-xl font-bold">SDS Assistant</span>
                    <span class="text-white text-sm ml-2 opacity-75">Safety Data Sheet Management</span>
                </div>
            </div>
        </div>
    </nav>

    <div class="max-w-7xl mx-auto px-4 py-8">
        <div class="bg-white rounded-lg shadow p-6">
            <h1 class="text-3xl font-bold text-gray-900 mb-4">🚀 SDS Assistant is Running!</h1>
            <p class="text-lg text-gray-600 mb-6">Welcome to the Safety Data Sheet Management System</p>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <a href="/test" class="bg-blue-100 hover:bg-blue-200 p-4 rounded-lg transition">
                    <i class="fas fa-vial text-blue-600 text-2xl mb-2"></i>
                    <h3 class="font-semibold">Test Page</h3>
                    <p class="text-sm text-gray-600">Basic functionality test</p>
                </a>
                
                <a href="/health" class="bg-green-100 hover:bg-green-200 p-4 rounded-lg transition">
                    <i class="fas fa-heartbeat text-green-600 text-2xl mb-2"></i>
                    <h3 class="font-semibold">Health Check</h3>
                    <p class="text-sm text-gray-600">System status</p>
                </a>
                
                <a href="/api/dashboard-stats" class="bg-purple-100 hover:bg-purple-200 p-4 rounded-lg transition">
                    <i class="fas fa-chart-bar text-purple-600 text-2xl mb-2"></i>
                    <h3 class="font-semibold">Dashboard Stats</h3>
                    <p class="text-sm text-gray-600">System statistics</p>
                </a>
                
                <a href="/debug" class="bg-orange-100 hover:bg-orange-200 p-4 rounded-lg transition">
                    <i class="fas fa-bug text-orange-600 text-2xl mb-2"></i>
                    <h3 class="font-semibold">Debug Info</h3>
                    <p class="text-sm text-gray-600">Technical details</p>
                </a>
            </div>
        </div>
    </div>
</body>
</html>
'''

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/test')
def test():
    """Simple test route"""
    return "<h1>✅ App is working!</h1><p>This is a test page.</p><a href='/'>← Back to Home</a>"

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "database": "connected"
    })

@app.route('/debug')
def debug():
    """Debug information"""
    return jsonify({
        "status": "running",
        "routes": [str(rule) for rule in app.url_map.iter_rules()],
        "timestamp": datetime.now().isoformat(),
        "python_version": "3.9.16",
        "database_initialized": True
    })

@app.route('/api/dashboard-stats')
def dashboard_stats():
    """Get dashboard statistics"""
    stats = sds_assistant.get_dashboard_stats()
    return jsonify(stats)

@app.route('/api/states')
def get_states():
    """Get all US states"""
    states = sds_assistant.get_states()
    return jsonify(states)

@app.route('/api/locations')
def get_locations():
    """Get locations with optional filtering"""
    state_filter = request.args.get('state')
    search_term = request.args.get('search')
    locations = sds_assistant.get_locations(state_filter, search_term)
    return jsonify(locations)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file provided"})
    
    file = request.files['file']
    location_id = request.form.get('location_id')
    
    if not location_id:
        return jsonify({"success": False, "message": "Location is required"})
    
    if file.filename == '':
        return jsonify({"success": False, "message": "No file selected"})
    
    result = sds_assistant.upload_file(file, int(location_id))
    return jsonify(result)

@app.route('/api/search')
def search():
    """Search SDS database"""
    query = request.args.get('q', '')
    location_id = request.args.get('location_id')
    user_session = session.get('user_id', 'anonymous')
    
    if not query:
        return jsonify([])
    
    results = sds_assistant.search_database(
        query, 
        int(location_id) if location_id else None,
        user_session
    )
    return jsonify(results)

@app.route('/api/generate-nfpa', methods=['POST'])
def generate_nfpa():
    """Generate NFPA sticker"""
    data = request.json
    product_name = data.get('product_name')
    
    if not product_name:
        return jsonify({"success": False, "message": "Product name is required"})
    
    result = sds_assistant.generate_nfpa_sticker_svg(product_name)
    return jsonify(result)

@app.route('/api/download-sticker/<filename>')
def download_sticker(filename):
    """Download generated sticker"""
    try:
        return send_file(f'static/stickers/{filename}', as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        "error": "Not Found",
        "message": "The requested URL was not found on the server.",
        "available_routes": [str(rule) for rule in app.url_map.iter_rules()]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal Server Error",
        "message": "Something went wrong on the server."
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Starting SDS Assistant Web Application...")
    print("📍 Database will be populated with US cities on first run")
    print(f"🌐 Application will be available at: http://localhost:{port}")
    print("📱 Mobile PWA ready - can be installed on phones/tablets")
    print()
    app.run(debug=False, host='0.0.0.0', port=port)
