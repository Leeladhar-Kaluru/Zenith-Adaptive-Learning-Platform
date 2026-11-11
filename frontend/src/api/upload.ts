import { token } from './client';

/** Upload a file as the raw request body (no multipart) so the browser can report real progress. XHR is the only way to get upload progress. */
export function uploadFile<T>(url: string, file: File, onProgress: (f: number) => void, signal: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open('POST', url);
    const t = token.get();
    if (t) x.setRequestHeader('Authorization', `Bearer ${t}`);
    x.setRequestHeader('Content-Type', 'application/octet-stream');
    x.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    x.onload = () => {
      let j: { detail?: string } = {};
      try { j = JSON.parse(x.responseText); } catch { /* not json */ }
      if (x.status >= 200 && x.status < 300) resolve(j as T); else reject(new Error(typeof j.detail === 'string' ? j.detail : 'The upload failed.'));
    };
    x.onerror = () => reject(new Error('You appear to be offline. Try again.'));
    x.onabort = () => reject(new Error('Upload cancelled.'));
    signal.addEventListener('abort', () => x.abort());
    x.send(file);
  });
}
