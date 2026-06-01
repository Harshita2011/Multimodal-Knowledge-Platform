import type { Metadata } from "next";
import { Geist, JetBrains_Mono } from "next/font/google";
import type { ReactNode } from "react";
import { AppProviders } from "@/providers/app-providers";
import "./globals.css";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist"
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono"
});

export const metadata: Metadata = {
  title: "Multimodal Knowledge Platform",
  description: "Grounded answers from uploaded knowledge sources"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geist.variable} ${mono.variable} font-sans antialiased`}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
