import { Nav } from "@/components/sections/nav";
import { Footer } from "@/components/sections/footer";
import { FeedLayer } from "@/components/three/feed-layer";

/** Marketing shell: floating nav, fixed feed field behind, footer. The console has its own shell. */
export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <FeedLayer />
      <Nav />
      <div id="main" tabIndex={-1} className="outline-none">{children}</div>
      <Footer />
    </>
  );
}
