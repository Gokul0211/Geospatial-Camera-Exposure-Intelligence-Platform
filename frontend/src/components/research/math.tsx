import katex from "katex";
import "katex/dist/katex.min.css";

/** KaTeX typeset at build time from trusted static strings (spec 13). */
export function Tex({ tex, block = false }: { tex: string; block?: boolean }) {
  const html = katex.renderToString(tex, { displayMode: block, throwOnError: false, output: "htmlAndMathml", strict: "ignore" });
  const Tag = block ? "div" : "span";
  return <Tag className={block ? "my-4 overflow-x-auto py-1" : undefined} dangerouslySetInnerHTML={{ __html: html }} />;
}
