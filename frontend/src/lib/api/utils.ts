export async function createQueryString(
  params: Record<string, string | string[] | undefined>
): Promise<string> {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined) return;

    if (Array.isArray(value)) {
      // Append each value for array-type params
      value.forEach((v) => searchParams.append(key, v));
    } else {
      searchParams.set(key, value);
    }
  });

  return searchParams.toString();
}