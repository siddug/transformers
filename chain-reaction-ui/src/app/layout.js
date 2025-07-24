import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";


export const metadata = {
  title: "Chain Reaction UI",
  description: "UI for Chain Reaction API",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body
        className={``}
      >
        <Sidebar />
        <div className="ml-64">
          <main className="p-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
