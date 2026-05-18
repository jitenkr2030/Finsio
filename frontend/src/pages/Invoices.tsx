import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getInvoices } from '../lib/api';
import { FileText, Plus } from 'lucide-react';

export function Invoices() {
  const { data, isLoading, error } = useQuery({ queryKey: ['invoices'], queryFn: getInvoices });
  const invoices = data?.results || data || [];

  return (
    <div className="space-y-6 max-w-6xl mx-auto h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Invoices</h1>
          <p className="text-muted-foreground mt-1 text-sm">Manage billing and receivables</p>
        </div>
        <button className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-md font-medium text-sm transition-colors flex items-center gap-2">
          <Plus className="h-4 w-4" /> Create Invoice
        </button>
      </div>

      <div className="flex-1 rounded-xl bg-card border border-border flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="p-4 space-y-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-16 bg-muted animate-pulse rounded-lg"></div>
              ))}
            </div>
          ) : error ? (
            <div className="p-8 text-center text-danger">Failed to load invoices</div>
          ) : invoices.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground flex flex-col items-center">
              <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
                <FileText className="h-6 w-6" />
              </div>
              <p className="text-lg font-medium text-foreground">No invoices yet</p>
              <p className="text-sm">Create your first invoice to get started</p>
            </div>
          ) : (
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/20 sticky top-0">
                <tr>
                  <th className="px-6 py-3 font-medium">Invoice #</th>
                  <th className="px-6 py-3 font-medium">Customer</th>
                  <th className="px-6 py-3 font-medium">Total</th>
                  <th className="px-6 py-3 font-medium">Due</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Issue Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {invoices.map((inv: any) => (
                  <tr key={inv.id} className="hover:bg-muted/10 transition-colors cursor-pointer">
                    <td className="px-6 py-4 font-mono text-muted-foreground text-xs">{inv.number || inv.id?.split('-')[0]}</td>
                    <td className="px-6 py-4">
                      <div className="font-medium">{inv.customer_name || '—'}</div>
                      {inv.customer_email && (
                        <div className="text-xs text-muted-foreground">{inv.customer_email}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 font-medium">
                      {parseFloat(inv.total || 0).toFixed(2)} {inv.currency || 'USD'}
                    </td>
                    <td className="px-6 py-4 font-medium text-warning">
                      {parseFloat(inv.amount_due || 0).toFixed(2)} {inv.currency || 'USD'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase ${
                        inv.status === 'PAID' ? 'bg-success/20 text-success' :
                        inv.status === 'VOID' || inv.status === 'CANCELLED' ? 'bg-danger/20 text-danger' :
                        'bg-warning/20 text-warning'
                      }`}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-muted-foreground">
                      {inv.issue_date ? new Date(inv.issue_date).toLocaleDateString() : '—'}
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
