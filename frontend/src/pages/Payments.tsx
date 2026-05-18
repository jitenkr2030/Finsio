import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getPayments } from '../lib/api';
import { Search, Filter } from 'lucide-react';

export function Payments() {
  const [filter, setFilter] = useState<string>('ALL');
  const { data, isLoading, error } = useQuery({ queryKey: ['payments'], queryFn: getPayments });
  
  const payments = data?.results || data || [];
  const filteredPayments = filter === 'ALL' ? payments : payments.filter((p: any) => p.status === filter);

  return (
    <div className="space-y-6 max-w-6xl mx-auto h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Payments</h1>
          <p className="text-muted-foreground mt-1 text-sm">Manage and track payment statuses</p>
        </div>
        <button className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-md font-medium text-sm transition-colors">
          New Payment
        </button>
      </div>

      <div className="flex-1 rounded-xl bg-card border border-border flex flex-col overflow-hidden">
        <div className="p-4 border-b border-border flex items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Search payments..." 
              className="w-full bg-background border border-border rounded-md pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <select 
              className="bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="ALL">All Statuses</option>
              <option value="NEW">New</option>
              <option value="PREPARED">Prepared</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="PAID">Paid</option>
              <option value="FAILED">Failed</option>
              <option value="REFUNDED">Refunded</option>
            </select>
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="p-4 space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-16 bg-muted animate-pulse rounded-lg"></div>
              ))}
            </div>
          ) : error ? (
            <div className="p-8 text-center text-danger">Failed to load payments</div>
          ) : filteredPayments.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground flex flex-col items-center">
              <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
                <Search className="h-6 w-6" />
              </div>
              <p className="text-lg font-medium text-foreground">No payments found</p>
              <p className="text-sm">Try adjusting your filters</p>
            </div>
          ) : (
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/20 sticky top-0">
                <tr>
                  <th className="px-6 py-3 font-medium">ID</th>
                  <th className="px-6 py-3 font-medium">Amount</th>
                  <th className="px-6 py-3 font-medium">Processor</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredPayments.map((p: any) => (
                  <tr key={p.id} className="hover:bg-muted/10 transition-colors cursor-pointer">
                    <td className="px-6 py-4 font-mono text-muted-foreground">{p.id.split('-')[0]}</td>
                    <td className="px-6 py-4 font-medium">{parseFloat(p.amount).toFixed(2)} {p.currency}</td>
                    <td className="px-6 py-4 capitalize">{p.processor}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase ${
                        p.status === 'PAID' ? 'bg-success/20 text-success' : 
                        p.status === 'FAILED' ? 'bg-danger/20 text-danger' : 
                        'bg-warning/20 text-warning'
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-muted-foreground">
                      {new Date(p.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
