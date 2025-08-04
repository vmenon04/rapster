import type { Metadata } from "next";
import RootLayoutClient from "./layout-client";

import "./globals.css";

export const metadata: Metadata = {
  title: "Rapster",
  description: "Created by Vasu and Ansh",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white overflow-x-hidden">
        <RootLayoutClient>
          {children}
        </RootLayoutClient>
      </body>
    </html>
  );
}
  