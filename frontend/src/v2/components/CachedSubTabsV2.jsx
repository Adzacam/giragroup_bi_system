import React, { useState, useEffect, useRef } from 'react';

export default function CachedSubTabsV2({
  tabs = [],
  activeTabId,
  maxCached = 5,
  className = '',
}) {
  const [lruOrder, setLruOrder] = useState(() => (activeTabId ? [activeTabId] : []));
  const panelRefs = useRef({});

  useEffect(() => {
    if (!activeTabId) return;
    setLruOrder((prev) => {
      const filtered = prev.filter((id) => id !== activeTabId);
      const next = [...filtered, activeTabId];
      if (next.length > maxCached) {
        return next.slice(next.length - maxCached);
      }
      return next;
    });

    const activeEl = panelRefs.current[activeTabId];
    if (activeEl && typeof activeEl.focus === 'function') {
      activeEl.focus({ preventScroll: true });
    }
  }, [activeTabId, maxCached]);

  return (
    <div className={`v2-cached-subtabs ${className}`}>
      {tabs
        .filter((tab) => lruOrder.includes(tab.id))
        .map((tab) => {
          const isActive = tab.id === activeTabId;
          return (
            <div
              key={tab.id}
              ref={(el) => {
                if (el) panelRefs.current[tab.id] = el;
              }}
              role="tabpanel"
              tabIndex={-1}
              aria-hidden={!isActive}
              inert={!isActive ? '' : undefined}
              className={`v2-spa-view ${isActive ? 'is-active' : 'inactive'}`}
            >
              {tab.render()}
            </div>
          );
        })}
    </div>
  );
}
