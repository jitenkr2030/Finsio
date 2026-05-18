import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getPayments, getInvoices, getHealth } from '../lib/api';
import { LineChart, Line, ResponsiveContainer, Tooltip } from 'recharts';
import { Activity, CreditCard, DollarSign, FileText } from 'lucide-react';

const mockChartData = [
  { name: 'Mon', revenue: 4000 },
  { name: 'Tue', revenue: 3000 },
  { name: 'Wed', revenue: 5000 },
  { name: 'Thu', revenue: 2780 },
  { name: 'Fri', revenue: 6890 },
  { name: 'Sat', revenue: 2390 },
  { name: 'Sun', revenue: 3490 },
];

function Card({ title, value, icon: Icon, description, loading }: { title: string, value: string | number, icon: any, description?: string, loading?: boolean }) {
  return (
    <div className="p-6 rounded-xl bg-card border border-border flex flex-col gap-2">
      <div className="flex items-center justify-between text-muted-foreground">
        <span className="text-sm font-medium">{title}</span>
        <Icon className="h-4 w-4" />
      </div>
      {loading ? (
        <div className="h-8 bg-muted animate-pulse rounded w-1/2 mt-1"></div>
      ) : (
        <div className="text-3xl font-bold text-foreground">{value}</div>
      )}
      {description && <div className="text-xs text-muted-foreground mt-1">{description}</div>}
    </div>
  );
}

export function Dashboard() {
  const { data: payments, isLoading: paymentsLoading } = useQuery({ queryKey: ['payments'], queryFn: getPayments });
  const { data: invoices, isLoading: invoicesLoading } = useQuery({ queryKey: ['invoices'], queryFn: getInvoices });
  const { data: health, isLoading: healthLoading } = useQuery({ queryKey: ['health'], queryFn: getHealth });

  const totalPayments = payments?.results?.length || payments?.length || 0;
  const pendingInvoices = (invoices?.results || invoices || []).filter((i: any) => i.status === 'PENDING' || i.status === 'DRAFT').length;
  
  const revenue = (payments?.results || payments || []).reduce((acc: number, p: any) => acc + (p.status === 'PAID' ? parseFloat(p.amount) : 0), 0);
  
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-card border border-border">
          <div className={`h-2 w-2 rounded-full ${healthLoading ? 'bg-warning animate-pulse' : (health?.status === 'healthy' ? 'bg-success' : 'bg-danger')}`}></div>
          <span className="text-xs font-medium text-muted-foreground">
            {healthLoading ? 'Checking systems...' : (health?.status === 'healthy' ? 'Systems Operational' : 'System Degraded')}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="Total Revenue" value={`$${revenue.toFixed(2)}`} icon={DollarSign} loading={paymentsLoading} description="From paid payments" />
        <Card title="Total Payments" value={totalPayments} icon={CreditCard} loading={paymentsLoading} />
        <Card title="Pending Invoices" value={pendingInvoices} icon={FileText} loading={invoicesLoading} />
        <Card title="System Health" value={healthLoading ? '-' : (health?.status === 'healthy' ? 'HEALTHY' : health?.status ? 'DEGRADED' : 'UNKNOWN')} icon={Activity} loading={healthLoading} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 p-6 rounded-xl bg-card border border-border">
          <h3 className="text-lg font-medium mb-4">Revenue Trend</h3>
          <div className="h-[300px] w-full" style={{ minHeight: 0 }}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={mockChartData}>
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--card)', borderColor: 'var(--border)', borderRadius: '8px' }}
                  itemStyle={{ color: 'var(--foreground)' }}
                />
                <Line type="monotone" dataKey="revenue" stroke="var(--primary)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        <div className="p-6 rounded-xl bg-card border border-border flex flex-col">
          <h3 className="text-lg font-medium mb-4">Recent Payments</h3>
          <div className="flex-1 overflow-auto space-y-4">
            {paymentsLoading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-12 bg-muted animate-pulse rounded"></div>
              ))
            ) : (payments?.results || payments || []).slice(0, 5).map((p: any) => (
              <div key={p.id} className="flex items-center justify-between pb-4 border-b border-border/50 last:border-0 last:pb-0">
                <div>
                  <div className="text-sm font-medium">{p.id.split('-')[0]}</div>
                  <div className="text-xs text-muted-foreground">{p.processor}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-medium">{p.amount} {p.currency}</div>
                  <div className={`text-[10px] uppercase font-bold tracking-wider ${p.status === 'PAID' ? 'text-success' : p.status === 'FAILED' ? 'text-danger' : 'text-warning'}`}>
                    {p.status}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
