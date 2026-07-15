/* ARIVO — Client-side utilities */

/**
 * Show a toast notification.
 */
function showToast(message, duration = 4000) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.classList.remove('hidden');
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => {
    toast.classList.add('hidden');
  }, duration);
}

/**
 * Escape HTML to prevent XSS.
 */
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Toggle an agent panel's expanded state.
 */
function togglePanel(panelId) {
  const panel = document.getElementById(panelId);
  if (panel) {
    panel.classList.toggle('expanded');
  }
}

/**
 * Connect to WebSocket for live pipeline updates.
 */
function connectWebSocket(runId, onEvent) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${window.location.host}/ws/${runId}`);

  ws.onopen = () => {
    console.log(`[ARIVO] WebSocket connected for run ${runId}`);
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onEvent) onEvent(data);
    } catch (e) {
      console.error('[ARIVO] WebSocket parse error:', e);
    }
  };

  ws.onclose = () => {
    console.log(`[ARIVO] WebSocket closed for run ${runId}`);
  };

  ws.onerror = (err) => {
    console.error('[ARIVO] WebSocket error:', err);
  };

  return ws;
}
