import React from 'react';

interface Column<T> {
  header: string;
  key: keyof T | string;
  render?: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
  isLoading?: boolean;
}

const DataTable = <T,>({ 
  data, 
  columns, 
  onRowClick, 
  emptyMessage = "No data found",
  isLoading = false 
}: DataTableProps<T>) => {
  return (
    <div className="overflow-x-auto border border-slate-900 bg-black">
      <table className="w-full text-left border-collapse font-mono">
        <thead className="border-b border-slate-900 bg-slate-950/50">
          <tr>
            {columns.map((col, idx) => (
              <th key={idx} className="px-4 py-3 text-[9px] font-bold text-[#ff9d00] uppercase tracking-[0.2em] opacity-80">
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-900/40">
          {isLoading ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-10 text-center text-slate-700 text-[10px] uppercase tracking-widest font-bold">
                _CONNECTING_DATA_STREAM...
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-10 text-center text-slate-800 text-[10px] uppercase tracking-[0.3em]">
                __{emptyMessage.toUpperCase()}__
              </td>
            </tr>
          ) : (
            data.map((item, rowIdx) => (
              <tr 
                key={rowIdx} 
                className={`border-b border-slate-900/30 hover:bg-slate-950/50 transition-colors ${onRowClick ? 'cursor-pointer' : ''}`}
                onClick={() => onRowClick && onRowClick(item)}
              >
                {columns.map((col, colIdx) => (
                  <td key={colIdx} className="px-4 py-3 text-[10px] text-[#ff9d00] font-medium opacity-90">
                    {col.render ? col.render(item) : String(item[col.key as keyof T] || '-')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;
