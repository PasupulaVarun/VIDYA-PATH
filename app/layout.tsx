import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VIDYA-PATH | Tuition, made clear",
  description: "A connected learning space for tuition teachers, students, and parents.",
  applicationName: "VIDYA-PATH",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
