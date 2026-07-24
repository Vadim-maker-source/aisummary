"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChartNoAxesCombined,
  Layers3,
  ListTree,
  Upload,
} from "lucide-react";

const navigation = [
  { href: "/dashboard", label: "Обзор", icon: ChartNoAxesCombined },
  { href: "/dashboard/scenarios", label: "Сценарии", icon: Layers3 },
  { href: "/dashboard/requests", label: "Запросы", icon: ListTree },
  { href: "/imports", label: "Импорт", icon: Upload },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/dashboard" aria-label="Контур — на главную">
          <span className="brand-mark">К</span>
          <span>
            <strong>Контур</strong>
            <small>AI request intelligence</small>
          </span>
        </Link>

        <nav className="sidebar-nav" aria-label="Основная навигация">
          {navigation.map((item) => {
            const active =
              item.href === "/dashboard"
                ? pathname === item.href
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={active ? "nav-link active" : "nav-link"}
                aria-current={active ? "page" : undefined}
              >
                <span className="nav-mark" aria-hidden="true">
                  <item.icon size={17} strokeWidth={1.8} />
                </span>
                {item.label}
              </Link>
            );
          })}
        </nav>

      </aside>

      <div className="main-column">
        <header className="mobile-header">
          <Link className="brand compact" href="/dashboard">
            <span className="brand-mark">К</span>
            <strong>Контур</strong>
          </Link>
          <nav aria-label="Мобильная навигация">
            {navigation.map((item) => {
              const active =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-label={item.label}
                  className={
                    active ? "mobile-nav-link active" : "mobile-nav-link"
                  }
                >
                  <item.icon size={16} strokeWidth={1.8} aria-hidden="true" />
                </Link>
              );
            })}
          </nav>
        </header>
        <main className="page-frame">{children}</main>
      </div>
    </div>
  );
}
