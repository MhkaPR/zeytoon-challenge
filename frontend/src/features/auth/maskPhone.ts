/**
 * Masks the middle digits of an Iranian mobile number so the header only shows a
 * recognizable prefix and suffix (e.g. ``0912***6789``). Accepts local (``09…``), ``9…``,
 * ``+98…`` and ``0098…`` forms; anything else is returned unchanged.
 */
export function maskPhone(phone: string): string {
  let local = phone.trim();
  if (local.startsWith("+98")) local = `0${local.slice(3)}`;
  else if (local.startsWith("0098")) local = `0${local.slice(4)}`;
  else if (/^9\d{9}$/.test(local)) local = `0${local}`;
  return local.replace(/^(\d{4})\d{3}(\d{4})$/, "$1***$2");
}
