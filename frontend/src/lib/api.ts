import axios from 'axios'

const INTERNAL_TOKEN = 'TJFw2U66Qu1D3A32hGU9FESGHZhxX8oH8hEfuKF12got1ymP1sy6Ijieu-p-iL8X'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${INTERNAL_TOKEN}`,
  },
})

// Health check (uses /api-health proxy to avoid React route conflict)
export const healthApi = axios.create({
  baseURL: '/',
})

// --- Payments ---
export const getPayments = () => api.get('/payments/').then(r => r.data)
export const getPayment = (id: string) => api.get(`/payments/${id}`).then(r => r.data)
export const getProcessors = () => api.get('/payments/processors').then(r => r.data)
export const preparePayment = (data: object) => api.post('/payments/prepare', data).then(r => r.data)

// --- Invoices ---
export const getInvoices = () => api.get('/invoicing/invoices').then(r => r.data)
export const getInvoice = (id: string) => api.get(`/invoicing/invoices/${id}`).then(r => r.data)
export const createInvoice = (data: object) => api.post('/invoicing/invoices/create', data).then(r => r.data)

// --- Accounting ---
export const getJournalEntries = () => api.get('/accounting/journal-entries').then(r => r.data)
export const createJournalEntry = (data: object) => api.post('/accounting/journal-entries/create', data).then(r => r.data)
export const getBalanceSheet = () => api.get('/accounting/balance-sheet').then(r => r.data)
export const getProfitLoss = () => api.get('/accounting/profit-loss').then(r => r.data)
export const getLedgerAccounts = () => api.get('/accounting/ledger-accounts').then(r => r.data)
export const runReconciliation = () => api.post('/accounting/reconciliation', {}).then(r => r.data)

// --- Health --- (accept 503 so degraded status still returns body data)
export const getHealth = () =>
  api.get('/health/', { validateStatus: (s) => s < 600 }).then(r => r.data)
