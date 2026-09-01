export interface RecoveryRecord {
  id: string;
  customer: string;
  amount: string;
  rootCause: string;
  channel: string;
  retries: string;
  message: string;
  status: 'Recovered' | 'Pending' | 'Unresolved' | 'Stopped';
  promiseCaptured: string;
}
