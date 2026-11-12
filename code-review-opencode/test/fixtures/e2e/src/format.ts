// Intentional fixture: this default export exercises the conventions angle.
export default function formatMoney(value: number): string {
  return value.toFixed(2)
}
