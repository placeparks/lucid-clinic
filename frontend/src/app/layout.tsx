import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import AuthGate from "@/components/AuthGate";

export const metadata: Metadata = {
  title: "Lucid Clinic",
  description: "Patient Intelligence CRM for Chiropractic Clinics",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 antialiased">
        <AuthGate>
          <div className="flex flex-col md:flex-row min-h-screen">
            <Sidebar />
            <main className="flex-1 p-4 md:p-8 overflow-auto">{children}</main>
          </div>
        </AuthGate>
      </body>
    </html>
  );
}
