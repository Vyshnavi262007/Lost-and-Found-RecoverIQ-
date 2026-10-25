export const fmtDate = (d) => (d ? new Date(d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : '');
export const fmtDateTime = (d) => (d ? new Date(d).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '');

export function timeAgo(d) {
  const s = Math.max(0, (Date.now() - new Date(d).getTime()) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  if (s < 86400 * 7) return `${Math.floor(s / 86400)} d ago`;
  return fmtDate(d);
}

export const STATUS_LABELS = {
  open: 'Open', claim_pending: 'Claim approved', returned: 'Returned', closed: 'Closed', expired: 'Expired',
  pending: 'Pending', under_review: 'Under review', approved: 'Approved', rejected: 'Rejected', withdrawn: 'Withdrawn', completed: 'Completed',
  stored: 'In storage', disposed: 'Disposed', scheduled: 'Scheduled', cancelled: 'Cancelled', removed: 'Removed',
};

export const unwrap = (data) => (Array.isArray(data) ? data : data?.results || []);

/** Build FormData from an object, skipping empty values. Arrays/Files are appended per item. */
export function toFormData(values, fileField = 'images', files = []) {
  const fd = new FormData();
  Object.entries(values).forEach(([k, v]) => {
    if (v !== '' && v !== null && v !== undefined) fd.append(k, v);
  });
  files.forEach((f) => fd.append(fileField, f));
  return fd;
}
