import type {Metadata} from 'next';
import Link from 'next/link';
import '@fontsource-variable/instrument-sans';
import './ui/fs.css';
import SiteHeader from './components/site-header';

export const metadata: Metadata = {
  title: 'FrailtyScope',
  description: 'Machine learning and explainable visual communication for mobility and function in older people. A research demonstrator.',
  robots: {index: false, follow: false},
};

export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>
        <a className="fs-skip" href="#main">Skip to content</a>
        <SiteHeader />
        {children}
        <footer className="fs-footer">
          <div className="fs-wrap fs-footer-in">
            <span>FrailtyScope is a research demonstrator. It is not a medical device and does not score real patients.</span>
            <Link href="/archive">Earlier workspaces</Link>
          </div>
        </footer>
      </body>
    </html>
  );
}
