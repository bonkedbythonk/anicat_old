import "./globals.css";
import Providers from "@/components/Providers";

import AmbientBackground from "@/components/layout/AmbientBackground";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>anicat</title>
        <meta name="description" content="anicat PWA Dashboard — Search, stream, and download anime from your local machine." />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=0" />
        <meta name="theme-color" content="#050505" />
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="icon" href="/logo.png" type="image/png" />
        <link rel="apple-touch-icon" href="/pwa-logo.png?v=4" />
        <script dangerouslySetInnerHTML={{ __html: `
          (function() {
            const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            document.write('<link rel="manifest" href="/manifest.json?v=4">');
            
            // Fast theme injection to prevent light/dark flash on load
            const theme = localStorage.getItem('anicat_theme') || 'system';
            document.documentElement.classList.remove('light', 'dark', 'system');
            document.documentElement.classList.add(theme);
            if (theme === 'light' || (theme === 'system' && !isDark)) {
              document.documentElement.classList.add('light');
            } else {
              document.documentElement.classList.add('dark');
            }
          })();
        ` }} />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://www.youtube-nocookie.com" />
        <link rel="preconnect" href="https://s.ytimg.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-background overflow-hidden relative">
        <AmbientBackground />
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
