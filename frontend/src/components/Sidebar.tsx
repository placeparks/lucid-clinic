"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const nav = [
  { href: "/", label: "Dashboard", icon: "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-4 0a1 1 0 01-1-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 01-1 1" },
  { href: "/patients", label: "Patients", icon: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" },
  { href: "/queue", label: "Re-engage Queue", icon: "M4 6h16M4 10h16M4 14h16M4 18h16" },
  { href: "/campaigns", label: "Campaigns", icon: "M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
  { href: "/agent", label: "Agent", icon: "M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Mobile Top Bar */}
      <div className="md:hidden flex items-center justify-between bg-gray-900 text-white p-4">
        <h1 className="font-bold tracking-tight">Lucid Clinic</h1>
        <button
          onClick={() => setIsOpen(true)}
          className="p-1 -mr-1 rounded hover:bg-gray-800"
          aria-label="Open Menu"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>

      {/* Backdrop for Mobile */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-900/50 backdrop-blur-sm md:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 text-white flex flex-col transition-transform duration-300 ease-in-out md:relative md:translate-x-0 ${isOpen ? "translate-x-0" : "-translate-x-full"
          }`}
      >
        <div className="p-6 border-b border-gray-800 flex justify-between items-start">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Lucid Clinic</h1>
            <p className="text-xs text-gray-400 mt-1">Patient Intelligence CRM</p>
          </div>
          {/* Close Menu Button (Mobile Only) */}
          <button
            onClick={() => setIsOpen(false)}
            className="md:hidden p-1 text-gray-400 hover:text-white"
            aria-label="Close Menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {nav.map((item) => {
            const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsOpen(false)} // Close menu on mobile when a link is clicked
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${active
                    ? "bg-indigo-600 text-white"
                    : "text-gray-300 hover:bg-gray-800 hover:text-white"
                  }`}
              >
                <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={item.icon} />
                </svg>
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-gray-800 text-xs text-gray-500">
          Lucid Clinic Inc v0.1
        </div>
      </aside>
    </>
  );
}
