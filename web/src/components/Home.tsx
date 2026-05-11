import type { Dictionary } from "@/dictionaries";

export function Home({ dict }: { dict: Dictionary }) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 text-center">
      <h1 className="text-4xl font-semibold tracking-tight">{dict.home.title}</h1>
      <p className="mt-4 max-w-md text-lg text-zinc-600 dark:text-zinc-400">{dict.home.tagline}</p>
    </main>
  );
}
