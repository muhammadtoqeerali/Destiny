import 'server-only';
import { createHmac, timingSafeEqual } from 'node:crypto';
import { cookies } from 'next/headers';

const COOKIE = 'frailtyscope_admin_demo';
const TTL = 8 * 60 * 60 * 1000;
// Public aggregate-metrics demo only. Set BOTH variables in Vercel for private use.
// Never use the demonstration default to guard real patient or HUNT research data.
const password = () => process.env.ADMIN_PORTAL_PASSWORD || '';
const secret = () => process.env.ADMIN_SESSION_SECRET || '';
const configured = () => password().length >= 16 && secret().length >= 32 && password() !== secret();

function signature(expiry: string): string {
  if (!configured()) return '';
  return createHmac('sha256', secret()).update(expiry).digest('hex');
}

export function matchesPassword(input: string): boolean {
  if (!configured()) return false;
  const expected = Buffer.from(password());
  const attempt = Buffer.from(input);
  return expected.length === attempt.length && timingSafeEqual(expected, attempt);
}

export async function openAdminSession() {
  if (!configured()) throw new Error('Admin authentication has not been securely configured');
  const expiry = String(Date.now() + TTL);
  const store = await cookies();
  store.set(COOKIE, expiry + '.' + signature(expiry), {
    httpOnly: true, secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax', path: '/', maxAge: Math.ceil(TTL / 1000)
  });
}

export async function hasAdminSession(): Promise<boolean> {
  if (!configured()) return false;
  const token = (await cookies()).get(COOKIE)?.value || '';
  const [expiry, mac, extra] = token.split('.');
  if (!expiry || !mac || extra || !/^\d+$/.test(expiry) || Number(expiry) < Date.now()) return false;
  const expected = Buffer.from(signature(expiry));
  const received = Buffer.from(mac);
  return expected.length === received.length && timingSafeEqual(expected, received);
}

export async function closeAdminSession() {
  (await cookies()).delete(COOKIE);
}
