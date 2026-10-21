import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'FrailtyScope | Clinical ML Research Demo',
  description: 'Synthetic-only clinical ML prototype exploring explainable fall risk for older adults. Not for medical use.',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
