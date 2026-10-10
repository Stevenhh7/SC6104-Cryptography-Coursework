/* Keep diagram nodes in place; animate only the values changed by a step. */
(function () {
  'use strict';
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  const easing = 'cubic-bezier(.22, 1, .36, 1)';
  const targets = '.factor, .equation b, .hub-caption, .euclid-row, .private-key, '
    + '.flow-caption, .node-label, .node-value, .node-rem, .tree-result, .mobile-value, '
    + '.record-n, .prime-label, .case-equation, .case-result, #step-title, #step-copy, '
    + '#step-formula, #side-proof, #scene-tag, #step-number, #progress-text';
  const active = new Set();
  const ghosts = new Set();
  let layer;

  function animate(element, frames, options) {
    const animation = element.animate(frames, {duration: 480, easing, ...options});
    active.add(animation);
    animation.finished.then(() => active.delete(animation), () => active.delete(animation));
    return animation;
  }
  function settle() {
    // Finish at the committed state before taking another snapshot. No delayed
    // callbacks can overwrite a later step, even during rapid navigation.
    for (const animation of active) animation.cancel();
    active.clear();
    for (const ghost of ghosts) ghost.remove();
    ghosts.clear();
  }
  function signature(element) {
    return element.textContent + '|' + element.hasAttribute('hidden') + '|'
      + (element.getAttribute('opacity') || '') + '|' + element.classList.contains('is-pending');
  }
  function visible(element, rect) {
    return rect.width > 0 && rect.height > 0 && getComputedStyle(element).opacity !== '0';
  }
  function capture() {
    settle();
    if (preference.matches) return null;
    const before = new Map();
    document.querySelectorAll(targets).forEach(element => {
      const rect = element.getBoundingClientRect();
      const style = getComputedStyle(element);
      const svg = element.namespaceURI === 'http://www.w3.org/2000/svg';
      const clone = svg ? document.createElement('span') : element.cloneNode(true);
      if (svg) clone.textContent = element.textContent;
      const copyStyle = Object.fromEntries(['font', 'color', 'background-color', 'border', 'border-radius',
        'padding', 'display', 'align-items', 'justify-content', 'gap', 'flex-wrap', 'line-height',
        'letter-spacing', 'text-align', 'box-sizing'].map(name => [name, style.getPropertyValue(name)]));
      if (svg) { copyStyle.color = style.fill; copyStyle['line-height'] = rect.height + 'px'; }
      before.set(element, {rect, signature: signature(element), visible: visible(element, rect),
        clone, style: copyStyle});
    });
    const positions = new Map();
    document.querySelectorAll('.controls, .footer, .notes').forEach(element => {
      positions.set(element, element.getBoundingClientRect());
    });
    return {before, positions};
  }
  function fadePrevious(snapshot) {
    if (!snapshot.clone || !snapshot.visible) return;
    if (!layer) {
      layer = document.createElement('div');
      layer.className = 'motion-layer';
      layer.setAttribute('aria-hidden', 'true');
      layer.setAttribute('inert', '');
      document.body.append(layer);
    }
    const clone = snapshot.clone;
    [clone, ...clone.querySelectorAll('[id]')].forEach(node => node.removeAttribute('id'));
    Object.entries(snapshot.style).forEach(([name, value]) => clone.style.setProperty(name, value));
    Object.assign(clone.style, {position: 'absolute', margin: '0',
      left: snapshot.rect.left + 'px', top: snapshot.rect.top + 'px',
      width: snapshot.rect.width + 'px', height: snapshot.rect.height + 'px'});
    layer.append(clone);
    ghosts.add(clone);
    const animation = animate(clone, [{opacity: 1}, {opacity: 0}], {duration: 160});
    animation.finished.then(() => { clone.remove(); ghosts.delete(clone); }, () => {});
  }
  function play(snapshot) {
    if (!snapshot || preference.matches) return;
    document.querySelectorAll(targets).forEach(element => {
      const old = snapshot.before.get(element);
      const rect = element.getBoundingClientRect();
      if (old && old.signature === signature(element)) return;
      if (old) fadePrevious(old);
      if (!visible(element, rect)) return;
      const svg = element.namespaceURI === 'http://www.w3.org/2000/svg';
      const delay = Number(element.dataset.motionDelay || (svg ? 100 : 45));
      const frames = svg ? [{opacity: 0}, {opacity: 1}]
        : [{opacity: 0, transform: 'translateY(6px)'}, {opacity: 1, transform: 'translateY(0)'}];
      animate(element, frames, {delay, fill: 'backwards'});
    });
    snapshot.positions.forEach((old, element) => {
      const next = element.getBoundingClientRect();
      const dx = old.left - next.left, dy = old.top - next.top;
      if (old.height && next.height && (Math.abs(dx) > .5 || Math.abs(dy) > .5))
        animate(element, [{transform: `translate(${dx}px, ${dy}px)`}, {transform: 'translate(0, 0)'}]);
    });
  }
  function compatible(current, fresh) {
    return current && current.nodeType === fresh.nodeType && current.nodeName === fresh.nodeName
      && current.namespaceURI === fresh.namespaceURI;
  }
  function reconcile(current, fresh) {
    if (current.nodeType === Node.TEXT_NODE || current.nodeType === Node.COMMENT_NODE) {
      if (current.data !== fresh.data) current.data = fresh.data;
      return;
    }
    for (const attribute of [...current.attributes])
      if (!fresh.hasAttribute(attribute.name)) current.removeAttribute(attribute.name);
    for (const attribute of fresh.attributes)
      if (current.getAttribute(attribute.name) !== attribute.value) current.setAttribute(attribute.name, attribute.value);
    if (current.tagName === 'INPUT') current.checked = fresh.hasAttribute('checked');
    reconcileChildren(current, fresh);
  }
  function reconcileChildren(current, fresh) {
    [...fresh.childNodes].forEach((next, index) => {
      const old = current.childNodes[index];
      if (compatible(old, next) && !next.hasAttribute?.('data-transient')) reconcile(old, next);
      else if (old) old.replaceWith(next.cloneNode(true));
      else current.append(next.cloneNode(true));
    });
    while (current.childNodes.length > fresh.childNodes.length) current.lastChild.remove();
  }
  function patch(element, markup) {
    const template = document.createElement('template');
    template.innerHTML = markup;
    reconcileChildren(element, template.content);
  }
  window.addEventListener('resize', settle);
  window.addEventListener('scroll', () => {
    for (const ghost of ghosts) ghost.remove();
    ghosts.clear();
  }, {passive: true});
  preference.addEventListener('change', settle);
  window.RSAMotion = {capture, play, patch};
})();
