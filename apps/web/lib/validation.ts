// Part E — Meta Ad Library URL validation. Meta의 query parameter 구성은 언제든 달라질 수 있으므로
// 과도하게 strict하게 검증하지 않는다: hostname이 facebook.com 계열이고 경로에 /ads/library가
// 포함되면 통과시킨다.
export function isValidMetaAdLibraryUrl(url: string): boolean {
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  const host = parsed.hostname.toLowerCase();
  if (host !== "facebook.com" && host !== "www.facebook.com") return false;
  return parsed.pathname.includes("/ads/library");
}

export const META_AD_LIBRARY_URL_ERROR = "Meta Ad Library 주소를 확인해주세요.";
