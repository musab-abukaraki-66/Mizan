import { ar } from "./ar";
import { en, type Key } from "./en";
import type { Lang } from "../lib/types";

export type { Key };
export const dictionaries: Record<Lang, Record<Key, string>> = { en, ar };
export type TFn = (key: Key, params?: Record<string, string | number>) => string;

const NUMERIC = /^[\d.,+−\-–%\s]+$/;

/** In Arabic text, numeric tokens are wrapped in directional isolates so signs and % never jump around. */
export function makeT(lang: Lang): TFn {
  const dict = dictionaries[lang];
  return (key, params) => {
    let s = dict[key] ?? en[key] ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        const str = String(v);
        const val = lang === "ar" && NUMERIC.test(str) ? `⁦${str}⁩` : str;
        s = s.split(`{${k}}`).join(val);
      }
    }
    return s;
  };
}
