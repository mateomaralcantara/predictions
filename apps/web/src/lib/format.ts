const fechaFmt = new Intl.DateTimeFormat("es-DO", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

export function fecha(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(`${iso}T00:00:00Z`);
  return Number.isNaN(d.getTime()) ? iso : fechaFmt.format(d);
}

export const dos = (n: number) => String(n).padStart(2, "0");

export const miles = (n: number) => n.toLocaleString("es-DO");
