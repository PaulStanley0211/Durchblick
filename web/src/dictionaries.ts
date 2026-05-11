const dictionaries = {
  de: () => import("../messages/de.json").then((module) => module.default),
  en: () => import("../messages/en.json").then((module) => module.default),
} as const;

export type Locale = keyof typeof dictionaries;

export const locales: readonly Locale[] = Object.keys(dictionaries) as Locale[];

export const defaultLocale: Locale = "de";

export const hasLocale = (locale: string): locale is Locale =>
  locale in dictionaries;

export const getDictionary = async (locale: Locale) =>
  dictionaries[locale]();

export type Dictionary = Awaited<ReturnType<typeof getDictionary>>;
