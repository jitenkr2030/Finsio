import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getHealth } from '../lib/api';
import { Activity, Database, Server, Clock } from 'lucide-react';

export function Health() {
  const { data, isLoading, error } = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 5000 });

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Health</h1>
        <p className="text-muted-foreground mt-1 text-sm">Real-time status of Finsio services</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-6 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-3 mb-4">
            <Activity className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-medium">Overall Status</h3>
          </div>
          {isLoading ? <div className="h-6 w-32 bg-muted animate-pulse rounded"></div> : error ? (
            <span className="text-danger font-medium">Error connecting to gateway</span>
          ) : (
            <div className="flex items-center gap-3">
              <div className={`h-3 w-3 rounded-full ${data?.status === 'healthy' ? 'bg-success' : 'bg-danger'}`}></div>
              <span className="text-xl font-bold capitalize">{data?.status || 'Unknown'}</span>
            </div>
          )}
        </div>

        <div className="p-6 rounded-xl bg-card border border-border">
          <div className="flex items-center gap-3 mb-4">
            <Clock className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-medium">Timestamp</h3>
          </div>
          {isLoading ? <div className="h-6 w-48 bg-muted animate-pulse rounded"></div> : (
            <div className="text-lg font-medium font-mono">
              {data?.timestamp ? new Date(data.timestamp).toLocaleString() : 'N/A'}
            </div>
          )}
        </div>
      </div>

      <div className="p-6 rounded-xl bg-card border border-border">
        <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
          <Server className="h-5 w-5 text-muted-foreground" />
          Detailed Components
        </h3>
        
        {isLoading ? (
          <div className="space-y-4">
            <div className="h-12 bg-muted animate-pulse rounded"></div>
            <div className="h-12 bg-muted animate-pulse rounded"></div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg bg-background border border-border">
              <div className="flex items-center gap-3">
                <Database className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium">Database (PostgreSQL)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${data?.database === 'ok' ? 'bg-success' : 'bg-danger'}`}></div>
                <span className="text-sm font-medium uppercase tracking-wide">{data?.database || 'Unknown'}</span>
              </div>
            </div>
            
            <div className="flex items-center justify-between p-4 rounded-lg bg-background border border-border">
              <div className="flex items-center gap-3">
                <Server className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium">Redis Cache</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${data?.redis === 'ok' ? 'bg-success' : 'bg-danger'}`}></div>
                <span className="text-sm font-medium uppercase tracking-wide">{data?.redis || 'Unknown'}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
