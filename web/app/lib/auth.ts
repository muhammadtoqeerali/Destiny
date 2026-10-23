import 'server-only';
import { createHmac, timingSafeEqual } from 'node:crypto';
import { cookies } from 'next/headers';

const COOKIE = 'frailtyscope_admin_demo';
const PUBLIC_DEMO_COOKIE = 'frailtyscope_public_aggregate_demo_v32';
const PUBLIC_DEMO_VALUE = 'aggregate-view-only';
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

/** This fixed passcode is intentionally public and MUST NEVER protect private
 * data, research workflows, APIs, administrative writes or private artifacts.
 * It only opens the static, published-aggregate demonstration dashboard.
 */
export function isPublicDemoPasscode(input: string): boolean {
  return input === 'admin123';
}

export async function openPublicDemoSession(): Promise<void> {
  (await cookies()).set(PUBLIC_DEMO_COOKIE, PUBLIC_DEMO_VALUE, {
    httpOnly: true, secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax', path: '/', maxAge: Math.ceil(TTL / 1000),
  });
}

export async function hasPublicDemoSession(): Promise<boolean> {
  // Intentionally NOT an authorization mechanism: cookie is forgeable by design.
  // Do not use this function for any access other than public aggregate views.
  return (await cookies()).get(PUBLIC_DEMO_COOKIE)?.value === PUBLIC_DEMO_VALUE;
}

export async function canViewPublicDashboard(): Promise<boolean> {
  return await hasAdminSession() || await hasPublicDemoSession();
}

export async function closeAdminSession() {
  const store = await cookies();
  store.delete(COOKIE);
  store.delete(PUBLIC_DEMO_COOKIE);
}
