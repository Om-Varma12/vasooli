export interface RecoveryRecord {
  id: string;
  customer: string;
  amount: string;
  rootCause: string;
  channel: string;
  retries: string;
  message: string;
  status: 'Recovered' | 'Pending' | 'Unresolved' | 'Stopped' | 'Retrying';
  promiseCaptured: string;
  recovery_state?: string;
  next_retry_at?: string;
  last_failure_reason?: string;
}
