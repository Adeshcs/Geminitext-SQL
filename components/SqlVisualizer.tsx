import React from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, 
  LineChart, Line, PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis 
} from 'recharts';
import { QueryResult } from '../types';

interface SqlVisualizerProps {
  result: QueryResult;
}

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#6366f1'];

const SqlVisualizer: React.FC<SqlVisualizerProps> = ({ result }) => {
  if (!result.data || result.data.length === 0 || result.error) return null;

  const data = result.data;
  const columns = Object.keys(data[0]);
  
  // Heuristics to determine chart type
  const numericCols = columns.filter(key => typeof data[0][key] === 'number');
  const stringCols = columns.filter(key => typeof data[0][key] === 'string');
  
  let ChartComponent: any = BarChart;
  let renderChart = null;

  // 1. PIE CHART: If asking for "Distribution", "Ratio", "Share" (1 string col, 1 numeric col, small dataset)
  if (data.length <= 10 && stringCols.length === 1 && numericCols.length === 1) {
    const nameKey = stringCols[0];
    const dataKey = numericCols[0];
    
    renderChart = (
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={80}
          fill="#8884d8"
          dataKey={dataKey}
          nameKey={nameKey}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', color: '#f1f5f9' }} />
        <Legend />
      </PieChart>
    );
  }
  // 2. SCATTER CHART: Correlation (2 numeric columns) e.g., "CGPA vs 10th Marks"
  else if (numericCols.length === 2 && data.length > 5) {
     const xKey = numericCols[0];
     const yKey = numericCols[1];
     const zKey = stringCols[0]; // Optional tooltip label

     renderChart = (
      <ScatterChart>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis type="number" dataKey={xKey} name={xKey} stroke="#94a3b8" fontSize={12} />
        <YAxis type="number" dataKey={yKey} name={yKey} stroke="#94a3b8" fontSize={12} />
        <ZAxis type="category" dataKey={zKey} range={[60, 400]} name="Label" />
        <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', color: '#f1f5f9' }} />
        <Legend />
        <Scatter name="Correlation" data={data} fill="#8b5cf6" />
      </ScatterChart>
     );
  }
  // 3. DEFAULT: Bar or Line Chart
  else {
    const isTrend = stringCols[0]?.toLowerCase().includes('date') || stringCols[0]?.toLowerCase().includes('year');
    ChartComponent = isTrend ? LineChart : BarChart;
    const xKey = stringCols[0] || columns[0];
    const bars = numericCols.map((key, index) => (
      isTrend ? 
        <Line key={key} type="monotone" dataKey={key} stroke={COLORS[index % COLORS.length]} strokeWidth={2} /> :
        <Bar key={key} dataKey={key} fill={COLORS[index % COLORS.length]} />
    ));

    renderChart = (
      <ChartComponent data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis dataKey={xKey} stroke="#94a3b8" fontSize={12} tickFormatter={(val) => val?.toString().slice(0, 15)} />
        <YAxis stroke="#94a3b8" fontSize={12} />
        <Tooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#475569', color: '#f1f5f9' }} />
        <Legend />
        {bars}
      </ChartComponent>
    );
  }

  return (
    <div className="w-full h-80 mt-6 bg-slate-800/50 p-4 rounded-xl border border-slate-700">
      <h3 className="text-sm font-semibold text-slate-400 mb-4 flex justify-between">
        <span>Data Visualization</span>
        <span className="text-xs uppercase tracking-wider text-slate-600">
          {numericCols.length === 2 && data.length > 5 ? 'Scatter' : 
           data.length <= 10 && stringCols.length === 1 && numericCols.length === 1 ? 'Pie' : 'Chart'}
        </span>
      </h3>
      <ResponsiveContainer width="100%" height="100%">
        {renderChart}
      </ResponsiveContainer>
    </div>
  );
};

export default SqlVisualizer;