import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Actuariosa — Panel de Monitoreo Gerencial",
  description:
    "Supervisión ejecutiva en tiempo real del inventario de correos, depuración de empresas Supercias, rendimiento de campañas B2B y prospectos positivos.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" className="dark">
      <body className="bg-[#070a12] text-slate-100 antialiased min-h-screen selection:bg-indigo-500/30 selection:text-indigo-200">
        {children}
      </body>
    </html>
  );
}
