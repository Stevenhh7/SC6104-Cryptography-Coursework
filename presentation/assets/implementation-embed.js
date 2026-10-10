(() => {
  'use strict';
  if (document.body.dataset.embedded !== 'true' || window.parent === window) return;

  document.addEventListener('keydown', event => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey ||
        document.querySelector('dialog[open]') ||
        event.target.closest('input,select,textarea,[contenteditable]')) return;
    let delta;
    if (event.key === 'ArrowRight' || event.key === 'PageDown') delta = 1;
    else if (event.key === 'ArrowLeft' || event.key === 'PageUp') delta = -1;
    else return;
    event.preventDefault();
    window.parent.postMessage({type: 'rsa-presentation:turn', delta}, '*');
  });

  window.addEventListener('message', event => {
    if (event.source !== window.parent || event.origin !== window.location.origin ||
        event.data?.type !== 'rsa-presentation:visibility' || event.data.active !== false) return;
    document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
  });
})();
