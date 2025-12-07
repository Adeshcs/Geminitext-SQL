import { GoogleGenAI, Type } from "@google/genai";
import { TableSchema } from "../types";
import { SYSTEM_INSTRUCTION, GEMINI_MODEL } from "../constants";

export class GeminiService {
  private client: GoogleGenAI;

  constructor() {
    this.client = new GoogleGenAI({ apiKey: process.env.API_KEY });
  }

  async generateSQL(userQuery: string, schemas: TableSchema[]): Promise<{ sql: string; explanation: string }> {
    // Construct schema context
    const schemaDesc = schemas.map(s => 
      `Table: ${s.tableName}\nColumns: ${s.columns.map(c => `${c.name} (${c.type})`).join(', ')}`
    ).join('\n\n');

    const prompt = `
    Schema Configuration:
    ${schemaDesc}

    User Question: "${userQuery}"
    
    Dialect: SQLite / AlaSQL.
    Return the JSON object as specified in system instructions.
    `;

    try {
      const response = await this.client.models.generateContent({
        model: GEMINI_MODEL,
        contents: prompt,
        config: {
          systemInstruction: SYSTEM_INSTRUCTION,
          responseMimeType: "application/json",
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              sql: { type: Type.STRING },
              explanation: { type: Type.STRING }
            },
            required: ["sql", "explanation"]
          }
        }
      });

      const text = response.text;
      if (!text) throw new Error("No response from AI");
      
      return JSON.parse(text);
    } catch (error) {
      console.error("Gemini API Error:", error);
      throw new Error("Failed to generate SQL from the prompt.");
    }
  }

  async validateKey(): Promise<boolean> {
    try {
      // Simple test call
      await this.client.models.generateContent({
        model: "gemini-2.5-flash",
        contents: "Test",
      });
      return true;
    } catch {
      return false;
    }
  }
}