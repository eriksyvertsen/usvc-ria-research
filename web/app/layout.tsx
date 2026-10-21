import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "RIA Venture Leads",
  description: "Wealth-channel RIAs screened from SEC Form ADV filings for venture and private-markets fit.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
