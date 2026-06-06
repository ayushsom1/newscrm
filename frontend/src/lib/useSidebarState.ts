import { useCallback, useEffect, useState } from "react";

const KEY = "news_crm_sidebar_collapsed";

function read(): boolean {
  try {
    return localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function useSidebarState() {
  const [collapsed, setCollapsed] = useState<boolean>(() => read());

  useEffect(() => {
    try {
      localStorage.setItem(KEY, collapsed ? "1" : "0");
    } catch {
      /* private mode / quota — ignore */
    }
  }, [collapsed]);

  const toggle = useCallback(() => setCollapsed((v) => !v), []);

  return { collapsed, toggle, setCollapsed };
}
