import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { getBalanceSheet, getProfitLoss, getJournalEntries, getLedgerAccounts, runReconciliation } from '../lib/api';
import { RefreshCw, TrendingUp, BookOpen, Layers, List, CheckCircle, AlertCircle } from 'lucide-react';

const tabs = [
  { id: 'balance', label: 'Balance Sheet', icon: Layers },
  { id: 'pl',      label: 'Profit & Loss', icon: TrendingUp },
  { id: 'journal', label: 'Journal Entries', icon: BookOpen },
  { id: 'ledger',  label: 'Ledger Accounts', icon: List },
] as const;

type TabId = typeof tabs[number]['id'];

function EmptyState({ message, sub }: { message: string; sub?: string }) {
  return (
    <div className="p-12 text-center text-muted-foreground flex flex-col items-center">
      <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
        <Layers className="h-6 w-6" />
      </div>
      <p className="text-base font-medium text-foreground">{message}</p>
      {sub && <p className="text-sm mt-1">{sub}</p>}
    </div>
  );
}

function JsonBlock({ data }: { data: unknown }) {
  if (!data) return <EmptyState message="No data available" sub="No records have been returned by the API." />;
  if (typeof data === 'object' && data !== null && 'detail' in (data as any)) {
    return <EmptyState message="Data unavailable" sub={(data as any).detail} />;
  }
  return (
    <pre className="text-sm font-mono text-muted-foreground bg-background p-4 rounded-lg overflow-auto border border-border">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export function Accounting() {
  const [activeTab, setActiveTab] = useState<TabId>('balance');
  const [reconcileStatus, setReconcileStatus] = useState<'idle' | 'ok' | 'err'>('idle');

  const { data: balanceSheet, isLoading: isLoadingBS } = useQuery({
    queryKey: ['balanceSheet'],
    queryFn: getBalanceSheet,
    enabled: activeTab === 'balance',
    retry: false,
  });
  const { data: profitLoss, isLoading: isLoadingPL } = useQuery({
    queryKey: ['profitLoss'],
    queryFn: getProfitLoss,
    enabled: activeTab === 'pl',
    retry: false,
  });
  const { data: journalEntries, isLoading: isLoadingJE } = useQuery({
    queryKey: ['journalEntries'],
    queryFn: getJournalEntries,
    enabled: activeTab === 'journal',
    retry: false,
  });
  const { data: ledgerAccounts, isLoading: isLoadingLA } = useQuery({
    queryKey: ['ledgerAccounts'],
    queryFn: getLedgerAccounts,
    enabled: activeTab === 'ledger',
    retry: false,
  });

  const reconcileMutation = useMutation({
    mutationFn: runReconciliation,
    onSuccess: () => {
      setReconcileStatus('ok');
      setTimeout(() => setReconcileStatus('idle'), 4000);
    },
    onError: () => {
      setReconcileStatus('err');
      setTimeout(() => setReconcileStatus('idle'), 4000);
    },
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Accounting</h1>
          <p className="text-muted-foreground mt-1 text-sm">Financial reporting and ledger management</p>
        </div>
        <div className="flex items-center gap-3">
          {reconcileStatus === 'ok' && (
            <span className="flex items-center gap-1.5 text-sm text-success">
              <CheckCircle className="h-4 w-4" /> Reconciliation started
            </span>
          )}
          {reconcileStatus === 'err' && (
            <span className="flex items-center gap-1.5 text-sm text-danger">
              <AlertCircle className="h-4 w-4" /> Reconciliation failed
            </span>
          )}
          <button
            onClick={() => reconcileMutation.mutate()}
            disabled={reconcileMutation.isPending}
            className="bg-card border border-border hover:bg-muted text-foreground px-4 py-2 rounded-md font-medium text-sm transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${reconcileMutation.isPending ? 'animate-spin' : ''}`} />
            Run Reconciliation
          </button>
        </div>
      </div>

      <div className="flex gap-0 border-b border-border">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 bg-card border border-border rounded-xl p-6 overflow-auto min-h-0">
        {activeTab === 'balance' && (
          <div>
            <h3 className="text-lg font-medium mb-4">Balance Sheet</h3>
            {isLoadingBS ? (
              <div className="animate-pulse h-32 bg-muted rounded-lg" />
            ) : (
              <JsonBlock data={balanceSheet} />
            )}
          </div>
        )}

        {activeTab === 'pl' && (
          <div>
            <h3 className="text-lg font-medium mb-4">Profit & Loss</h3>
            {isLoadingPL ? (
              <div className="animate-pulse h-32 bg-muted rounded-lg" />
            ) : (
              <JsonBlock data={profitLoss} />
            )}
          </div>
        )}

        {activeTab === 'journal' && (
          <div>
            <h3 className="text-lg font-medium mb-4">Journal Entries</h3>
            {isLoadingJE ? (
              <div className="animate-pulse h-32 bg-muted rounded-lg" />
            ) : (
              (() => {
                const entries = journalEntries?.results || journalEntries || [];
                if (!Array.isArray(entries) || entries.length === 0) {
                  return <EmptyState message="No journal entries" sub="Entries will appear here once transactions are recorded." />;
                }
                return (
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-muted-foreground uppercase bg-muted/20">
                      <tr>
                        <th className="px-4 py-3 font-medium">Date</th>
                        <th className="px-4 py-3 font-medium">Description</th>
                        <th className="px-4 py-3 font-medium">Debit</th>
                        <th className="px-4 py-3 font-medium">Credit</th>
                        <th className="px-4 py-3 font-medium">Amount</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {entries.map((je: any) => (
                        <tr key={je.id} className="hover:bg-muted/10 transition-colors">
                          <td className="px-4 py-3 text-muted-foreground">
                            {je.date ? new Date(je.date).toLocaleDateString() : '—'}
                          </td>
                          <td className="px-4 py-3">{je.description || '—'}</td>
                          <td className="px-4 py-3 font-mono text-xs">{je.debit_account || '—'}</td>
                          <td className="px-4 py-3 font-mono text-xs">{je.credit_account || '—'}</td>
                          <td className="px-4 py-3 font-medium">{je.amount}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                );
              })()
            )}
          </div>
        )}

        {activeTab === 'ledger' && (
          <div>
            <h3 className="text-lg font-medium mb-4">Ledger Accounts</h3>
            {isLoadingLA ? (
              <div className="animate-pulse h-32 bg-muted rounded-lg" />
            ) : (
              (() => {
                const accounts = ledgerAccounts?.results || ledgerAccounts || [];
                if (!Array.isArray(accounts) || accounts.length === 0) {
                  return <EmptyState message="No ledger accounts" sub="Create an entity and chart of accounts to get started." />;
                }
                return (
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs text-muted-foreground uppercase bg-muted/20">
                      <tr>
                        <th className="px-4 py-3 font-medium">Name</th>
                        <th className="px-4 py-3 font-medium">Type</th>
                        <th className="px-4 py-3 font-medium">Balance</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {accounts.map((la: any) => (
                        <tr key={la.id} className="hover:bg-muted/10 transition-colors">
                          <td className="px-4 py-3 font-medium">{la.name}</td>
                          <td className="px-4 py-3 text-muted-foreground capitalize">{la.account_type}</td>
                          <td className="px-4 py-3 font-mono">{la.balance} {la.currency}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                );
              })()
            )}
          </div>
        )}
      </div>
    </div>
  );
}
