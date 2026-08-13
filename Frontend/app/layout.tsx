import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'mAIntenance & Assistance',
  description: "Votre assistant intelligent pour le support informatique.",
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icons8-help-50.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icons8-help-50.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icons8-help-50.png',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: 'black' },
  ],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="bg-background">
      <body className="antialiased">
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
