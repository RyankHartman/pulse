import { longDate } from "../format";
import type { AppData } from "../types";

export function Footer({ data }: { data: AppData }) {
  const { dataset } = data.meta;
  return (
    <>
      <section className="block" id="next">
        <div className="wrap">
          <header>
            <p className="eyebrow">05 · What I'd do with real internal data</p>
            <h2>From a demo to a team workflow.</h2>
            <p className="lead">
              This is a public-data prototype. On a product team the same skeleton would run against the real thing,
              and these are the moves that turn it from a report into leverage.
            </p>
          </header>
          <ol className="steps">
            {data.summary.next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
      </section>

      <footer className="site">
        <div className="wrap">
          <p>
            <strong style={{ color: "var(--fg)" }}>Data.</strong> {dataset.title} by {dataset.author}, via Mendeley
            Data, licensed {dataset.license}. <a href={dataset.url}>doi:{dataset.doi}</a>. Hourly top-100 snapshots
            collected through the Steam Web API, May 11, 2018 to Mar 14, 2019. I cleaned, deduplicated, and removed
            frozen snapshots; the original file is unchanged.
          </p>
          <p>
            <strong style={{ color: "var(--fg)" }}>Limits.</strong> Steam counts only players on Steam, titles outside
            the top 100 are invisible, the hour field's time zone is undocumented, and event causes are unknown. The
            forecasting uses simple models on purpose: on this data the plain "same weekday last week" baseline was
            hard to beat, and that is itself a result.
          </p>
          <p>
            Independent learning project, not affiliated with or endorsed by Valve or any game publisher. Built by Ryan
            Hartman. Generated {longDate(data.meta.generated)}.
          </p>
        </div>
      </footer>
    </>
  );
}
