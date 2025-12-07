export enum AppView {
  LOGIN = 'LOGIN',
  DASHBOARD = 'DASHBOARD',
}

export interface User {
  username: string;
  role: 'admin' | 'user';
}

export interface TableColumn {
  name: string;
  type: string;
}

export interface TableSchema {
  tableName: string;
  columns: TableColumn[];
  rowCount: number;
  sampleData: any[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type: 'text' | 'sql_result' | 'error';
  sql?: string;
  data?: any[];
  explanation?: string;
  timestamp: number;
}

export interface QueryResult {
  data: any[];
  columns: string[];
  sql: string;
  error?: string;
}

// Declare AlaSQL on window
declare global {
  interface Window {
    alasql: any;
  }
}