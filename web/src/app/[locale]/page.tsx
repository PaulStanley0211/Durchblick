import { notFound } from "next/navigation";

import { Home } from "@/components/Home";
import { getDictionary, hasLocale } from "@/dictionaries";

export default async function HomePage({ params }: PageProps<"/[locale]">) {
  const { locale } = await params;
  if (!hasLocale(locale)) notFound();
  const dict = await getDictionary(locale);
  return <Home dict={dict} />;
}
