import { applyDiscount } from "./discount"

export function reportTotal(total: number, percent: number): string {
  return `Total: ${applyDiscount(total, percent).toFixed(2)}`
}
