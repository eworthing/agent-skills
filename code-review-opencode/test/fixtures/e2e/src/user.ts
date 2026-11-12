export type User = { name?: string; email: string }

export function displayName(user: User): string {
  return user.name.toUpperCase()
}
