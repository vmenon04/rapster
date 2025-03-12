"use client";

import Link from "next/link";

export default function Navbar() {
  return (
    <nav className="fixed top-0 left-0 w-full bg-white dark:bg-neutral-900 shadow-md p-4 z-50">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 text-black dark:text-white text-lg font-medium">
          <div className="h-6 w-6 bg-black dark:bg-white rounded-lg" />
          Music App
        </Link>

        {/* Navigation Links */}
        <div className="flex space-x-6">
          <Link href="/dashboard" className="text-sm text-black dark:text-white hover:opacity-80">
            Dashboard
          </Link>

          <Link href="/upload" className="text-sm text-black dark:text-white hover:opacity-80">
              Upload
            </Link>
        </div>
      </div>
    </nav>
  );
}
