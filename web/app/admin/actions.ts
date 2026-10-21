'use server';
import { redirect } from 'next/navigation';
import { matchesPassword, openAdminSession, closeAdminSession } from '../lib/auth';

export async function signIn(formData: FormData): Promise<void> {
  const password = formData.get('password');
  if (typeof password !== 'string' || !matchesPassword(password)) {
    redirect('/admin/login?error=invalid');
  }
  await openAdminSession();
  redirect('/admin');
}

export async function signOut(): Promise<void> {
  await closeAdminSession();
  redirect('/doctor');
}
