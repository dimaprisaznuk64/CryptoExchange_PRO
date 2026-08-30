"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { NotificationsBell } from "@/components/NotificationsBell";
import { site } from "@/lib/site";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/trade", label: "Trade" },
  { href: "/wallets", label: "Wallets" },
];

export function Navbar() {
  const { user, isAuthenticated, loading, logout } = useAuth();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navLink = (active: boolean) =>
    cn(
      "rounded-[2px] px-3 py-1.5 text-sm font-medium transition-colors",
      active
        ? "bg-surface-2 text-ink"
        : "text-ink/60 hover:text-ink",
    );

  return (
    <header className="sticky top-0 z-40 border-b border-hairline bg-bg/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-8">
          <Link
            href="/"
            className="flex items-center gap-2 text-base font-bold tracking-tight text-ink"
          >
            <span className="flex size-7 items-center justify-center rounded-[2px] bg-amber text-sm font-black text-bg">
              {site.logoText}
            </span>
            <span className="hidden sm:inline">
              {site.name.replace(site.accentLabel, "")}
              <span className="text-amber">{site.accentLabel}</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={navLink(pathname.startsWith(item.href))}
              >
                {item.label}
              </Link>
            ))}
            {user?.role === "admin" && (
              <>
                <Link href="/admin" className={navLink(pathname === "/admin")}>
                  Dashboard
                </Link>
                <Link
                  href="/admin/users"
                  className={navLink(pathname.startsWith("/admin/users"))}
                >
                  Users
                </Link>
                <Link
                  href="/admin/activity"
                  className={navLink(pathname.startsWith("/admin/activity"))}
                >
                  Activity
                </Link>
              </>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {loading ? null : isAuthenticated && user ? (
            <div className="flex items-center gap-3">
              <div className="hidden text-right sm:block">
                <p className="text-sm font-medium leading-tight text-ink">
                  {user.username}
                </p>
                <p className="text-xs leading-tight text-ink/50">{user.role}</p>
              </div>
              <NotificationsBell />
              <button
                onClick={() => logout()}
                className="cursor-pointer rounded-[2px] border border-hairline px-3 py-1.5 text-xs font-medium text-ink/70 transition-colors hover:bg-surface-2"
              >
                Log out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                href="/login"
                className="rounded-[2px] px-3 py-1.5 text-sm font-medium text-ink/70 transition-colors hover:text-ink"
              >
                Log in
              </Link>
              <Link
                href="/register"
                className="rounded-[2px] bg-amber px-3 py-1.5 text-sm font-medium text-bg transition-colors hover:bg-amber/90"
              >
                Sign up
              </Link>
            </div>
          )}

          <button
            onClick={() => setMobileOpen((o) => !o)}
            className="cursor-pointer rounded-[2px] p-2 text-ink/60 transition-colors hover:text-ink md:hidden"
            aria-label="Toggle navigation"
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              {mobileOpen ? (
                <path d="M6 6l12 12M18 6L6 18" />
              ) : (
                <path d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav className="border-t border-hairline px-4 py-2 md:hidden">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "block rounded-[2px] px-3 py-2 text-sm font-medium transition-colors",
                pathname.startsWith(item.href)
                  ? "bg-surface-2 text-ink"
                  : "text-ink/60 hover:bg-surface-2 hover:text-ink",
              )}
            >
              {item.label}
            </Link>
          ))}
          {user?.role === "admin" && (
            <>
              <Link
                href="/admin"
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "block rounded-[2px] px-3 py-2 text-sm font-medium transition-colors",
                  pathname === "/admin"
                    ? "bg-surface-2 text-ink"
                    : "text-ink/60 hover:bg-surface-2 hover:text-ink",
                )}
              >
                Dashboard
              </Link>
              <Link
                href="/admin/users"
                onClick={() => setMobileOpen(false)}
                className="block rounded-[2px] px-3 py-2 text-sm font-medium text-ink/60 transition-colors hover:bg-surface-2 hover:text-ink"
              >
                Users
              </Link>
              <Link
                href="/admin/activity"
                onClick={() => setMobileOpen(false)}
                className="block rounded-[2px] px-3 py-2 text-sm font-medium text-ink/60 transition-colors hover:bg-surface-2 hover:text-ink"
              >
                Activity
              </Link>
            </>
          )}
        </nav>
      )}
    </header>
  );
}
