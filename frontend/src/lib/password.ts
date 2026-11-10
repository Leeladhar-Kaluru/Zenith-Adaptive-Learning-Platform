/** Plain-language reasons a password is not acceptable yet. Empty array means it is fine. */
export function passwordProblems(pw: string): string[] {
  const out: string[] = [];
  if (pw.length < 8) out.push('At least 8 characters');
  if (!/[A-Za-z]/.test(pw)) out.push('At least one letter');
  if (!/\d/.test(pw)) out.push('At least one number');
  return out;
}
