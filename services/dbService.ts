import { TableSchema, QueryResult } from '../types';

// Wrapper for the AlaSQL library loaded from CDN
const getDb = () => {
  if (typeof window !== 'undefined' && window.alasql) {
    // Register Custom Functions for Analytics
    if (!window.alasql.fn.CALC_AGE) {
      window.alasql.fn.CALC_AGE = (dateStr: string) => {
        if (!dateStr) return null;
        const dob = new Date(dateStr);
        if (isNaN(dob.getTime())) return null;
        const diff = Date.now() - dob.getTime();
        const age = new Date(diff);
        return Math.abs(age.getUTCFullYear() - 1970);
      };
    }
    return window.alasql;
  }
  throw new Error("Database engine not initialized");
};

/**
 * Parses a CSV string and creates a table in the in-memory SQL database.
 */
export const loadTableFromCSV = async (tableName: string, csvContent: string): Promise<TableSchema> => {
  const db = getDb();
  
  // 1. Sanitize Table Name
  let safeTableName = tableName.replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '_');
  if (/^[0-9]/.test(safeTableName)) {
    safeTableName = `_${safeTableName}`;
  }
  safeTableName = safeTableName.replace(/_+/g, '_');

  // 2. Parse CSV
  const cleanContent = csvContent.replace(/^\uFEFF/, ''); 
  const rows = parseCSV(cleanContent);
  
  if (rows.length === 0) throw new Error("CSV file is empty or could not be parsed");

  try {
    // 3. Create Table
    db(`DROP TABLE IF EXISTS ${safeTableName}`);
    db(`CREATE TABLE ${safeTableName}`);

    // 4. Insert Data
    if (db.tables && db.tables[safeTableName]) {
        db.tables[safeTableName].data = rows;
    } else {
        db(`SELECT * INTO ${safeTableName} FROM ?`, [rows]);
    }

    // 5. Infer Schema
    const firstRow = rows[0];
    const columns = Object.keys(firstRow).map(key => ({
      name: key,
      type: typeof firstRow[key] === 'number' ? 'NUMBER' : 'STRING'
    }));

    return {
      tableName: safeTableName,
      columns,
      rowCount: rows.length,
      sampleData: rows.slice(0, 3)
    };
  } catch (e: any) {
    console.error("DB Load Error", e);
    throw new Error(`Database error: ${e.message}`);
  }
};

export const executeSQL = (sql: string): QueryResult => {
  const db = getDb();
  try {
    const data = db(sql);
    const rows = Array.isArray(data) ? data : [];
    const normalizedRows = rows.map(r => (typeof r === 'object' && r !== null) ? r : { value: r });
    const columns = normalizedRows.length > 0 ? Object.keys(normalizedRows[0]) : [];
    return { data: normalizedRows, columns, sql };
  } catch (error: any) {
    return { data: [], columns: [], sql, error: error.message };
  }
};

/**
 * Parse CSV with date normalization and number conversion
 */
function parseCSV(text: string): any[] {
  const normalizedText = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const lines = normalizedText.split('\n').filter(l => l.trim() !== '');
  
  if (lines.length < 2) return [];

  const rawHeaders = parseCSVLine(lines[0]);
  const seenHeaders = new Set<string>();
  
  // Sanitize Headers
  const headers = rawHeaders.map((h, i) => {
      let clean = h.trim().replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_]/g, '');
      if (!clean) clean = `col_${i}`;
      if (/^[0-9]/.test(clean)) clean = `_${clean}`;

      // Handle common duplicate headers
      let uniqueName = clean;
      let counter = 1;
      while (seenHeaders.has(uniqueName)) {
          uniqueName = `${clean}_${counter}`;
          counter++;
      }
      seenHeaders.add(uniqueName);
      return uniqueName;
  });
  
  const result = [];
  
  // Parse Rows
  for (let i = 1; i < lines.length; i++) {
    const currentLine = lines[i];
    if (!currentLine.trim()) continue;

    const values = parseCSVLine(currentLine);
    if (values.length === 1 && values[0] === '') continue;

    const obj: any = {};
    
    headers.forEach((header, index) => {
      let val: any = values[index];
      
      if (typeof val === 'string') {
          val = val.trim();
          
          // 1. Numeric Conversion (Handle "86.80 %" or "9.4 CGPA")
          // We remove non-numeric trailing chars if the start is numeric
          const numericClean = val.replace(/[%]/g, '').split('/')[0].trim();
          
          if (numericClean !== '' && !isNaN(Number(numericClean))) {
             // Keep phone numbers as strings (heuristic: 10 digits starting with 6-9)
             if (val.length === 10 && /^[6-9]/.test(val)) {
                // keep as string
             } else {
                val = Number(numericClean);
             }
          } 
          // 2. Date Normalization (Standardize to YYYY-MM-DD for SQL)
          else {
            // Case: 17-Sep-2003
            const dateMatchStr = val.match(/^(\d{1,2})-([A-Za-z]{3})-(\d{2,4})$/);
            if (dateMatchStr) {
               const d = new Date(val);
               if (!isNaN(d.getTime())) {
                 val = d.toISOString().split('T')[0];
               }
            } 
            // Case: 05/01/2001
            else if (/^\d{1,2}\/\d{1,2}\/\d{4}$/.test(val)) {
               const parts = val.split('/');
               // Assume DD/MM/YYYY -> YYYY-MM-DD
               val = `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
            }
          }
      } else {
          val = null;
      }
      
      obj[header] = val;
    });
    result.push(obj);
  }
  return result;
}

function parseCSVLine(line: string): string[] {
    const values: string[] = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        
        if (char === '"') {
            inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
            values.push(current);
            current = '';
        } else {
            current += char;
        }
    }
    values.push(current);
    
    return values.map(v => {
        const trimmed = v.trim();
        if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
            return trimmed.substring(1, trimmed.length - 1).replace(/""/g, '"');
        }
        return v;
    });
}