# app.py - Complete SDS Assistant Web Application
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from flask_socketio import SocketIO, emit
import os
import json
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import PyPDF2
from io import BytesIO
import base64
from werkzeug.utils import secure_filename
import requests
import re
import csv
from dataclasses import dataclass

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sds-assistant-secret-key-2024'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Create necessary directories
for folder in ['static/uploads', 'static/stickers', 'static/exports', 'data', 'templates']:
    Path(folder).mkdir(parents=True, exist_ok=True)

socketio = SocketIO(app, cors_allowed_origins="*")

# US Cities Data (sample - you can expand this)
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
    
    def get_cities_by_state(self, state: str) -> List[str]:
        """Get cities for a specific state"""
        return sorted(US_CITIES_DATA.get(state, []))
    
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
            
            # Generate SVG content
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
            
            # Documents by state
            cursor.execute('''
                SELECT l.state, COUNT(sc.id) as count
                FROM locations l
                LEFT JOIN sds_chunks sc ON l.id = sc.location_id
                WHERE sc.id IS NOT NULL
                GROUP BY l.state
                ORDER BY count DESC
                LIMIT 10
            ''')
            by_state = cursor.fetchall()
            
            conn.close()
            
            return {
                "total_documents": total_documents,
                "active_locations": active_locations,
                "recent_uploads": recent_uploads,
                "hazardous_materials": hazardous_count,
                "recent_searches": [{"query": row[0], "count": row[1]} for row in recent_searches],
                "documents_by_state": [{"state": row[0], "count": row[1]} for row in by_state]
            }
            
        except Exception as e:
            print(f"Error getting dashboard stats: {str(e)}")
            return {
                "total_documents": 0, 
                "active_locations": 0, 
                "recent_uploads": 0, 
                "hazardous_materials": 0,
                "recent_searches": [],
                "documents_by_state": []
            }

# Initialize the assistant
sds_assistant = SDSWebAssistant()

# Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template_string(INDEX_HTML_TEMPLATE)

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

@app.route('/api/cities/<state>')
def get_cities(state):
    """Get cities for a specific state"""
    cities = sds_assistant.get_cities_by_state(state)
    return jsonify(cities)

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

@app.route('/api/web-search')
def web_search():
    """Simulate web search for SDS documents"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify([])
    
    # Simulate web search results
    mock_results = [
        {
            "title": f"Safety Data Sheet - {query}",
            "url": f"https://example.com/sds/{query.replace(' ', '-')}.pdf",
            "snippet": f"Safety information for {query} including first aid measures, fire fighting procedures, and handling instructions.",
            "source": "Web Search"
        }
    ]
    
    return jsonify(mock_results)

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    session['user_id'] = request.sid
    emit('connected', {'message': 'Connected to SDS Assistant'})

@socketio.on('search_query')
def handle_search(data):
    """Handle real-time search"""
    query = data.get('query', '')
    location_id = data.get('location_id')
    
    if query:
        results = sds_assistant.search_database(query, location_id, session.get('user_id'))
        emit('search_results', {'results': results, 'query': query})

# HTML Template
INDEX_HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SDS Assistant - Safety Data Sheet Management</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.5/socket.io.js"></script>
    <style>
        .gradient-bg { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card-hover:hover { transform: translateY(-2px); transition: transform 0.2s; }
        .loading { opacity: 0.5; pointer-events: none; }
    </style>
</head>
<body class="bg-gray-50 min-h-screen">
    <!-- Navigation -->
    <nav class="gradient-bg shadow-lg">
        <div class="max-w-7xl mx-auto px-4">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <i class="fas fa-flask text-white text-2xl mr-3"></i>
                    <span class="text-white text-xl font-bold">SDS Assistant</span>
                    <span class="text-white text-sm ml-2 opacity-75">Safety Data Sheet Management</span>
                </div>
                <div class="flex items-center space-x-4">
                    <button id="uploadBtn" class="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition">
                        <i class="fas fa-upload mr-2"></i>Upload SDS
                    </button>
                    <button id="webSearchBtn" class="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg transition">
                        <i class="fas fa-globe mr-2"></i>Web Search
                    </button>
                </div>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="max-w-7xl mx-auto px-4 py-8">
        <!-- Dashboard Stats -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="bg-white rounded-lg shadow p-6 card-hover">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-blue-100 text-blue-600">
                        <i class="fas fa-file-alt text-2xl"></i>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-600">Total Documents</p>
                        <p id="totalDocs" class="text-2xl font-bold text-gray-900">0</p>
                    </div>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow p-6 card-hover">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-green-100 text-green-600">
                        <i class="fas fa-map-marker-alt text-2xl"></i>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-600">Active Locations</p>
                        <p id="activeLocations" class="text-2xl font-bold text-gray-900">0</p>
                    </div>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow p-6 card-hover">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-yellow-100 text-yellow-600">
                        <i class="fas fa-clock text-2xl"></i>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-600">Recent Uploads</p>
                        <p id="recentUploads" class="text-2xl font-bold text-gray-900">0</p>
                    </div>
                </div>
            </div>
            
            <div class="bg-white rounded-lg shadow p-6 card-hover">
                <div class="flex items-center">
                    <div class="p-3 rounded-full bg-red-100 text-red-600">
                        <i class="fas fa-exclamation-triangle text-2xl"></i>
                    </div>
                    <div class="ml-4">
                        <p class="text-sm font-medium text-gray-600">Hazardous Materials</p>
                        <p id="hazardousMaterials" class="text-2xl font-bold text-gray-900">0</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Search Section -->
        <div class="bg-white rounded-lg shadow mb-8">
            <div class="p-6">
                <h2 class="text-2xl font-bold text-gray-900 mb-4">
                    <i class="fas fa-search mr-2"></i>Search Safety Data Sheets
                </h2>
                
                <div class="grid grid-cols-1 md:grid-cols-12 gap-4 mb-4">
                    <div class="md:col-span-6">
                        <input 
                            type="text" 
                            id="searchInput" 
                            placeholder="Search for chemicals, first aid measures, hazards..."
                            class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                    </div>
                    <div class="md:col-span-2">
                        <select id="stateFilter" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                            <option value="">All States</option>
                        </select>
                    </div>
                    <div class="md:col-span-3">
                        <select id="locationFilter" class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                            <option value="">All Locations</option>
                        </select>
                    </div>
                    <div class="md:col-span-1">
                        <button id="searchBtn" class="w-full bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition">
                            <i class="fas fa-search"></i>
                        </button>
                    </div>
                </div>
                
                <!-- Quick Search Buttons -->
                <div class="flex flex-wrap gap-2">
                    <button class="quick-search bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded-full text-sm transition" data-query="first aid measures">
                        First Aid Measures
                    </button>
                    <button class="quick-search bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded-full text-sm transition" data-query="fire fighting">
                        Fire Fighting
                    </button>
                    <button class="quick-search bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded-full text-sm transition" data-query="handling and storage">
                        Handling & Storage
                    </button>
                    <button class="quick-search bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded-full text-sm transition" data-query="personal protection">
                        Personal Protection
                    </button>
                    <button class="quick-search bg-gray-100 hover:bg-gray-200 px-3 py-1 rounded-full text-sm transition" data-query="exposure controls">
                        Exposure Controls
                    </button>
                </div>
            </div>
        </div>

        <!-- Search Results -->
        <div id="searchResults" class="hidden bg-white rounded-lg shadow mb-8">
            <div class="p-6">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-xl font-bold text-gray-900">Search Results</h3>
                    <span id="resultsCount" class="text-sm text-gray-500"></span>
                </div>
                <div id="resultsList"></div>
            </div>
        </div>

        <!-- Recent Activity -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Recent Documents -->
            <div class="bg-white rounded-lg shadow">
                <div class="p-6">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-xl font-bold text-gray-900">Recent Documents</h3>
                        <button id="refreshBtn" class="text-blue-600 hover:text-blue-800 transition">
                            <i class="fas fa-refresh mr-1"></i>Refresh
                        </button>
                    </div>
                    <div id="recentDocuments" class="space-y-4">
                        <p class="text-gray-500 text-center py-8">No documents uploaded yet</p>
                    </div>
                </div>
            </div>

            <!-- Popular Searches -->
            <div class="bg-white rounded-lg shadow">
                <div class="p-6">
                    <h3 class="text-xl font-bold text-gray-900 mb-4">Popular Searches</h3>
                    <div id="popularSearches" class="space-y-2">
                        <p class="text-gray-500 text-center py-8">No searches yet</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Upload Modal -->
    <div id="uploadModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden z-50">
        <div class="flex items-center justify-center min-h-screen p-4">
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full">
                <div class="p-6">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold text-gray-900">Upload SDS Document</h3>
                        <button id="closeUploadModal" class="text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <form id="uploadForm" enctype="multipart/form-data">
                        <div class="mb-4">
                            <label class="block text-sm font-medium text-gray-700 mb-2">State</label>
                            <select id="uploadStateSelect" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required>
                                <option value="">Choose a state...</option>
                            </select>
                        </div>
                        
                        <div class="mb-4">
                            <label class="block text-sm font-medium text-gray-700 mb-2">Location</label>
                            <select id="uploadLocationSelect" name="location_id" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required>
                                <option value="">Choose a location...</option>
                            </select>
                        </div>
                        
                        <div class="mb-4">
                            <label class="block text-sm font-medium text-gray-700 mb-2">SDS File</label>
                            <div class="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-lg hover:border-gray-400 transition">
                                <div class="space-y-1 text-center">
                                    <i class="fas fa-cloud-upload-alt text-3xl text-gray-400"></i>
                                    <div class="flex text-sm text-gray-600">
                                        <label for="file-upload" class="relative cursor-pointer bg-white rounded-md font-medium text-blue-600 hover:text-blue-500">
                                            <span>Upload a file</span>
                                            <input id="file-upload" name="file" type="file" class="sr-only" accept=".pdf,.txt,.doc,.docx" required>
                                        </label>
                                        <p class="pl-1">or drag and drop</p>
                                    </div>
                                    <p class="text-xs text-gray-500">PDF, TXT, DOC up to 50MB</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="flex justify-end space-x-3">
                            <button type="button" id="cancelUpload" class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition">
                                Cancel
                            </button>
                            <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
                                <i class="fas fa-upload mr-2"></i>Upload
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <!-- Sticker Generation Modal -->
    <div id="stickerModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden z-50">
        <div class="flex items-center justify-center min-h-screen p-4">
            <div class="bg-white rounded-lg shadow-xl max-w-md w-full">
                <div class="p-6">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="text-lg font-bold text-gray-900">Generate Safety Sticker</h3>
                        <button id="closeStickerModal" class="text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Product Name</label>
                        <input type="text" id="stickerProductName" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="Enter product name...">
                    </div>
                    
                    <div class="flex justify-end space-x-3">
                        <button type="button" id="cancelSticker" class="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition">
                            Cancel
                        </button>
                        <button id="generateNFPA" type="button" class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition">
                            <i class="fas fa-diamond mr-2"></i>NFPA Diamond
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast Notifications -->
    <div id="toast" class="fixed top-4 right-4 z-50 hidden">
        <div class="bg-white rounded-lg shadow-lg border-l-4 p-4 max-w-sm">
            <div class="flex">
                <div class="flex-shrink-0">
                    <i id="toastIcon" class="text-xl"></i>
                </div>
                <div class="ml-3">
                    <p id="toastMessage" class="text-sm font-medium text-gray-900"></p>
                </div>
                <div class="ml-auto pl-3">
                    <button id="closeToast" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Initialize Socket.IO
        const socket = io();
        
        // Global variables
        let currentStates = [];
        let currentLocations = [];
        
        // Initialize app
        document.addEventListener('DOMContentLoaded', function() {
            loadDashboardStats();
            loadStates();
            setupEventListeners();
        });
        
        // Setup event listeners
        function setupEventListeners() {
            // Search functionality
            document.getElementById('searchBtn').addEventListener('click', performSearch);
            document.getElementById('searchInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') performSearch();
            });
            
            // State/Location filters
            document.getElementById('stateFilter').addEventListener('change', function() {
                loadLocationsByState(this.value, 'locationFilter');
            });
            
            document.getElementById('uploadStateSelect').addEventListener('change', function() {
                loadLocationsByState(this.value, 'uploadLocationSelect');
            });
            
            // Quick search buttons
            document.querySelectorAll('.quick-search').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.getElementById('searchInput').value = this.dataset.query;
                    performSearch();
                });
            });
            
            // Modal controls
            document.getElementById('uploadBtn').addEventListener('click', () => showModal('uploadModal'));
            document.getElementById('closeUploadModal').addEventListener('click', () => hideModal('uploadModal'));
            document.getElementById('closeStickerModal').addEventListener('click', () => hideModal('stickerModal'));
            document.getElementById('cancelUpload').addEventListener('click', () => hideModal('uploadModal'));
            document.getElementById('cancelSticker').addEventListener('click', () => hideModal('stickerModal'));
            
            // Form submissions
            document.getElementById('uploadForm').addEventListener('submit', handleFileUpload);
            
            // Sticker generation
            document.getElementById('generateNFPA').addEventListener('click', () => generateSticker('nfpa'));
            
            // Toast close
            document.getElementById('closeToast').addEventListener('click', hideToast);
            
            // Refresh button
            document.getElementById('refreshBtn').addEventListener('click', () => {
                loadDashboardStats();
            });
        }
        
        // Load dashboard statistics
        async function loadDashboardStats() {
            try {
                const response = await fetch('/api/dashboard-stats');
                const stats = await response.json();
                
                document.getElementById('totalDocs').textContent = stats.total_documents;
                document.getElementById('activeLocations').textContent = stats.active_locations;
                document.getElementById('recentUploads').textContent = stats.recent_uploads;
                document.getElementById('hazardousMaterials').textContent = stats.hazardous_materials;
                
                // Update popular searches
                updatePopularSearches(stats.recent_searches);
                
            } catch (error) {
                console.error('Error loading states:', error);
            }
        }
        
        // Load locations by state
        async function loadLocationsByState(state, selectId) {
            if (!state) {
                document.getElementById(selectId).innerHTML = '<option value="">Choose a location...</option>';
                return;
            }
            
            try {
                const response = await fetch(`/api/locations?state=${encodeURIComponent(state)}`);
                const locations = await response.json();
                
                const select = document.getElementById(selectId);
                select.innerHTML = '<option value="">Choose a location...</option>';
                
                locations.forEach(location => {
                    const option = document.createElement('option');
                    option.value = location.id;
                    option.textContent = location.display_name;
                    select.appendChild(option);
                });
                
            } catch (error) {
                console.error('Error loading locations:', error);
            }
        }
        
        // Perform search
        async function performSearch() {
            const query = document.getElementById('searchInput').value.trim();
            const locationId = document.getElementById('locationFilter').value;
            
            if (!query) {
                showToast('Please enter a search query', 'warning');
                return;
            }
            
            // Show loading
            document.getElementById('searchBtn').classList.add('loading');
            
            try {
                const url = `/api/search?q=${encodeURIComponent(query)}${locationId ? `&location_id=${locationId}` : ''}`;
                const response = await fetch(url);
                const results = await response.json();
                
                displaySearchResults(results, query);
                
            } catch (error) {
                console.error('Error performing search:', error);
                showToast('Error performing search', 'error');
            } finally {
                document.getElementById('searchBtn').classList.remove('loading');
            }
        }
        
        // Display search results
        function displaySearchResults(results, query) {
            const container = document.getElementById('resultsList');
            const resultsSection = document.getElementById('searchResults');
            const countElement = document.getElementById('resultsCount');
            
            container.innerHTML = '';
            countElement.textContent = `${results.length} result(s) found`;
            
            if (results.length === 0) {
                container.innerHTML = `
                    <div class="text-center py-8">
                        <i class="fas fa-search text-gray-300 text-4xl mb-4"></i>
                        <p class="text-gray-500">No results found for "${query}"</p>
                        <p class="text-sm text-gray-400 mt-2">Try different keywords or check spelling</p>
                    </div>
                `;
                resultsSection.classList.remove('hidden');
                return;
            }
            
            results.forEach(result => {
                const div = document.createElement('div');
                div.className = 'border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition mb-4';
                div.innerHTML = `
                    <div class="flex justify-between items-start mb-2">
                        <h4 class="font-semibold text-gray-900 text-lg">${result.product_name}</h4>
                        <div class="flex items-center space-x-2">
                            <span class="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">${result.source_type}</span>
                            ${result.hazards.nfpa_health > 0 ? `
                                <span class="px-2 py-1 bg-red-100 text-red-800 text-xs rounded-full">
                                    NFPA ${result.hazards.nfpa_health}-${result.hazards.nfpa_fire}-${result.hazards.nfpa_reactivity}
                                </span>
                            ` : ''}
                            ${result.hazards.ghs_signal_word ? `
                                <span class="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded-full">
                                    ${result.hazards.ghs_signal_word}
                                </span>
                            ` : ''}
                        </div>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                        <div>
                            <p class="text-sm text-gray-600"><strong>Manufacturer:</strong> ${result.manufacturer}</p>
                            <p class="text-sm text-gray-600"><strong>CAS Number:</strong> ${result.cas_number}</p>
                        </div>
                        <div>
                            <p class="text-sm text-gray-600"><strong>Location:</strong> ${result.location.department}, ${result.location.city}, ${result.location.state}</p>
                            <p class="text-sm text-gray-600"><strong>Uploaded:</strong> ${new Date(result.created_at).toLocaleDateString()}</p>
                        </div>
                    </div>
                    <p class="text-sm text-gray-700 mb-3">${result.content}</p>
                    <div class="flex justify-between items-center">
                        <div class="flex space-x-2">
                            <button onclick="generateStickerForProduct('${result.product_name}')" class="text-blue-600 hover:text-blue-800 text-sm">
                                <i class="fas fa-tag mr-1"></i>Generate Sticker
                            </button>
                            <button onclick="viewFullDocument('${result.id}')" class="text-green-600 hover:text-green-800 text-sm">
                                <i class="fas fa-eye mr-1"></i>View Full Document
                            </button>
                        </div>
                        <span class="text-xs text-gray-500">File: ${result.filename}</span>
                    </div>
                `;
                container.appendChild(div);
            });
            
            resultsSection.classList.remove('hidden');
        }
        
        // Handle file upload
        async function handleFileUpload(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const uploadBtn = e.target.querySelector('button[type="submit"]');
            
            // Show loading state
            uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Uploading...';
            uploadBtn.disabled = true;
            
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast(`File uploaded successfully: ${result.product_name}`, 'success');
                    hideModal('uploadModal');
                    e.target.reset();
                    loadDashboardStats();
                } else {
                    showToast(result.message, 'error');
                }
                
            } catch (error) {
                console.error('Error uploading file:', error);
                showToast('Error uploading file', 'error');
            } finally {
                uploadBtn.innerHTML = '<i class="fas fa-upload mr-2"></i>Upload';
                uploadBtn.disabled = false;
            }
        }
        
        // Generate sticker
        async function generateSticker(type) {
            const productName = document.getElementById('stickerProductName').value.trim();
            
            if (!productName) {
                showToast('Please enter a product name', 'warning');
                return;
            }
            
            try {
                const response = await fetch('/api/generate-nfpa', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ product_name: productName })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    showToast(`${type.toUpperCase()} sticker generated successfully`, 'success');
                    hideModal('stickerModal');
                    
                    // Create download link
                    const link = document.createElement('a');
                    link.href = `/api/download-sticker/${result.filename}`;
                    link.download = result.filename;
                    link.click();
                } else {
                    showToast(result.message, 'error');
                }
                
            } catch (error) {
                console.error('Error generating sticker:', error);
                showToast('Error generating sticker', 'error');
            }
        }
        
        // Generate sticker for specific product (from search results)
        function generateStickerForProduct(productName) {
            document.getElementById('stickerProductName').value = productName;
            showModal('stickerModal');
        }
        
        // View full document (placeholder)
        function viewFullDocument(documentId) {
            showToast('Full document viewer coming soon!', 'info');
        }
        
        // Update popular searches
        function updatePopularSearches(searches) {
            const container = document.getElementById('popularSearches');
            container.innerHTML = '';
            
            if (searches.length === 0) {
                container.innerHTML = '<p class="text-gray-500 text-center py-4">No searches yet</p>';
                return;
            }
            
            searches.forEach(search => {
                const div = document.createElement('div');
                div.className = 'flex justify-between items-center p-2 hover:bg-gray-50 rounded cursor-pointer';
                div.innerHTML = `
                    <span class="text-sm">${search.query}</span>
                    <span class="text-xs text-gray-500">${search.count} searches</span>
                `;
                div.addEventListener('click', () => {
                    document.getElementById('searchInput').value = search.query;
                    performSearch();
                });
                container.appendChild(div);
            });
        }
        
        // Modal utilities
        function showModal(modalId) {
            document.getElementById(modalId).classList.remove('hidden');
            if (modalId === 'uploadModal') {
                loadStates();
            }
        }
        
        function hideModal(modalId) {
            document.getElementById(modalId).classList.add('hidden');
        }
        
        // Toast notification utility
        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            const icon = document.getElementById('toastIcon');
            const messageEl = document.getElementById('toastMessage');
            
            messageEl.textContent = message;
            
            // Set icon and color based on type
            const config = {
                success: { icon: 'fas fa-check-circle text-green-500', border: 'border-green-400' },
                error: { icon: 'fas fa-exclamation-circle text-red-500', border: 'border-red-400' },
                warning: { icon: 'fas fa-exclamation-triangle text-yellow-500', border: 'border-yellow-400' },
                info: { icon: 'fas fa-info-circle text-blue-500', border: 'border-blue-400' }
            };
            
            icon.className = config[type].icon;
            toast.querySelector('div > div').className = `bg-white rounded-lg shadow-lg border-l-4 ${config[type].border} p-4 max-w-sm`;
            
            toast.classList.remove('hidden');
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                hideToast();
            }, 5000);
        }
        
        function hideToast() {
            document.getElementById('toast').classList.add('hidden');
        }
        
        // Socket.IO event handlers
        socket.on('connect', function() {
            console.log('Connected to SDS Assistant server');
        });
        
        socket.on('search_results', function(data) {
            displaySearchResults(data.results, data.query);
        });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("🚀 Starting SDS Assistant Web Application...")
    print("📍 Database will be populated with US cities on first run")
    print("🌐 Application will be available at: http://localhost:5000")
    print("📱 Mobile PWA ready - can be installed on phones/tablets")
    print()
    
    # Run the application
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
 (error) {
                console.error('Error loading dashboard stats:', error);
            }
        }
        
        // Load states
        async function loadStates() {
            try {
                const response = await fetch('/api/states');
                currentStates = await response.json();
                
                const stateSelects = [
                    document.getElementById('stateFilter'),
                    document.getElementById('uploadStateSelect')
                ];
                
                stateSelects.forEach(select => {
                    currentStates.forEach(state => {
                        const option = document.createElement('option');
                        option.value = state;
                        option.textContent = state;
                        select.appendChild(option);
                    });
                });
                
            } catch
            