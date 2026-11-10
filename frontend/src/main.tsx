import '@fontsource-variable/bricolage-grotesque/wght.css';
import '@fontsource-variable/plus-jakarta-sans/wght.css';
import '@fontsource/kalam/400.css';
import '@fontsource/kalam/700.css';
import '@fontsource-variable/noto-sans-devanagari/wght.css';
import '@fontsource-variable/noto-sans-telugu/wght.css';
import './styles/tokens.css';
import './styles/global.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './ui/kit';
import { FxProvider } from './fx/fx';
import { IconDefs } from './icons/Icon';
import { startSync } from './offline/sync';
import { startTracker } from './track/tracker';
import { startVitals } from './lib/vitals';
import { prefetch } from './api/useApi';
import { TOKEN_KEY } from './api/client';

startSync();
startTracker();
startVitals();
// A returning student lands on /home: ask for their day at the same time as their profile instead of after it.
if (localStorage.getItem(TOKEN_KEY) && ['/', '/home'].includes(location.pathname)) prefetch('/today');

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <FxProvider>
            <IconDefs />
            <App />
          </FxProvider>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
