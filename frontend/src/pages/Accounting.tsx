import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getBalanceSheet, getProfitLoss, getJournalEntries, getLedgerAccounts, runReconciliation } from '../lib/api';
import { RefreshCw, TrendingUp, BookOpen, Layers } from 'lucide-react';

export function Accounting() {
  const [activeTab, setActiveTab] = useState<'balance' | 'pl' | 'journal' | 'ledger'>('balance');

  const { data: balanceSheet, isLoading: isLoadingBS } = useQuery({ queryKey: ['balanceSheet'], queryFn: getBalanceSheet, enabled: activeTab === 'balance' });
  const { data: profitLoss, isLoading: isLoadingPL } = useQuery({ queryKey: ['profitLoss'], queryFn: getProfitLoss, enabled: activeTab === 'pl' });
  const { data: journalEntries, isLoading: isLoadingJE } = useQuery({ queryKey: ['journalEntries'], queryFn: getJournalEntries, enabled: activeTab === 'journal' });
  const { data: ledgerAccounts, isLoading: isLoadingLA } = useQuery({ queryKey: ['ledgerAccounts'], queryFn: getLedgerAccounts, enabled: activeTab === 'ledger' });

  const reconcileMutation = useMutation({
    mutationFn: runReconciliation,
    onSuccess: () => alert('Reconciliation started'),
    onError: () => alert('Reconciliation failed'),
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Accounting</h1>
          <p className="text-muted-foreground mt-1 text-sm">Financial reporting and ledger management</p>
        </div>
        <button 
          onClick={() => reconcileMutation.mutate()}
          disabled={reconcileMutation.isPending}
          className="bg-card border border-border hover:bg-muted text-foreground px-4 py-2 rounded-md font-medium text-sm transition-colors flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${reconcileMutation.isPending ? 'animate-spin' : ''}`} /> 
          Run Reconciliation
        </button>
      </div>

      <div className="flex gap-2 border-b border-border">
        {[
          { id: 'balance', label: 'Balance Sheet', icon: Layers },
          { id: 'pl', label: 'Profit & Loss', icon: TrendingUp },
          { id: 'journal', label: 'Journal Entries', icon: BookOpen },
          { id: 'ledger', label: 'Ledger Accounts', icon: Layers },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 bg-card border border-border rounded-xl p-6 overflow-auto">
        {activeTab === 'balance' && (
          <div>
            <h3 className="text-lg font-medium mb-4">Balance Sheet</h3>
            {isLoadingBS ? <div className="animate-pulse h-32 bg-muted rounded"></div> : (
              <pre className="text-sm font-mono text-muted-foreground bg-background p-4 rounded overflow-auto">
                {JSON.stringify(balanceSheet, null, 2)}
              </pre>
            )}
          </div>
        )}
        
        {activeTab === 'pl' && (
          <div>
            <h3 className="text-lg font-medium mb-4">Profit & Loss</h3>
            {isLoadingPL ? <div className="animate-pulse h-32 bg-muted rounded"></div> : (
               <pre className="text-sm font-mono text-muted-foreground bg-background p-4 rounded overflow-auto">
               {JSON.stringify(profitLoss, null, 2)}
             </pre>
            )}
          </div>
        )}

        {activeTab === 'journal' && (
          <div>
            <h3 className="text-lg font-medium mb-4">Journal Entries</h3>
            {isLoadingJE ? <div className="animate-pulse h-32 bg-muted rounded"></div> : (
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-muted/20">
                  <tr>
                    <th className="px-4 py-2">Date</th>
                    <th className="px-4 py-2">Description</th>
                    <th className="px-4 py-2">Debit</th>
                    <th className="px-4 py-2">Credit</th>
                    <th className="px-4 py-2">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(journalEntries?.results || journalEntries || []).map((je: any) => (
                    <tr key={je.id}>
                      <td className="px-4 py-2 text-muted-foreground">{new Date(je.date).toLocaleDateString()}</td>
                      <td className="px-4 py-2">{je.description}</td>
                      <td className="px-4 py-2 font-mono">{je.debit_account}</td>
                      <td className="px-4 py-2 font-mono">{je.credit_account}</td>
                      <td className="px-4 py-2 font-medium">{je.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {activeTab === 'ledger' && (
          <div>
            <h3 className="text-lg font-medium mb-4">Ledger Accounts</h3>
            {isLoadingLA ? <div className="animate-pulse h-32 bg-muted rounded"></div> : (
               <table className="w-full text-sm text-left">
               <thead className="text-xs text-muted-foreground uppercase bg-muted/20">
                 <tr>
                   <th className="px-4 py-2">Name</th>
                   <th className="px-4 py-2">Type</th>
                   <th className="px-4 py-2">Balance</th>
                 </tr>
               </thead>
               <tbody className="divide-y divide-border">
                 {(ledgerAccounts?.results || ledgerAccounts || []).map((la: any) => (
                   <tr key={la.id}>
                     <td className="px-4 py-2 font-medium">{la.name}</td>
                     <td className="px-4 py-2 text-muted-foreground capitalize">{la.account_type}</td>
                     <td className="px-4 py-2 font-mono">{la.balance} {la.currency}</td>
                   </tr>
                 ))}
               </tbody>
             </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
