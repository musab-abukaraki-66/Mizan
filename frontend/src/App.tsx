import { Footer, ProvenanceStrip, TopBar } from "./components/Shell";
import { Walkthrough } from "./components/Walkthrough";
import { useApp } from "./context";
import { Arena } from "./views/Arena";
import { Methods } from "./views/Methods";
import { Overview } from "./views/Overview";
import { Quality } from "./views/Quality";
import { Studio } from "./views/Studio";

export function App() {
  const { route, t } = useApp();
  return (
    <>
      <a className="skip" href="#content">
        {t("skip")}
      </a>
      <TopBar />
      <ProvenanceStrip />
      <main className="main" id="content" tabIndex={-1}>
        {route === "overview" && <Overview />}
        {route === "studio" && <Studio />}
        {route === "arena" && <Arena />}
        {route === "quality" && <Quality />}
        {route === "methods" && <Methods />}
      </main>
      <Footer />
      <Walkthrough />
    </>
  );
}
