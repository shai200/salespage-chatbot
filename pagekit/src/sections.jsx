import React from "react";

function accentuate(headline, accent) {
  if (!headline) return null;
  if (!accent || !headline.includes(accent)) {
    return headline;
  }
  const [before, after] = headline.split(accent);
  return (
    <>
      {before}
      <span className="accent">{accent}</span>
      {after}
    </>
  );
}

export function Hero({ headline, accent, subheadline, ctaLabel, visualLabel }) {
  return (
    <section className="section hero">
      <p className="section-label">Sales page</p>
      <h1 className="display xl">{accentuate(headline, accent)}</h1>
      <p className="lede">{subheadline}</p>
      {ctaLabel ? (
        <p>
          <a className="button" href="#offer">
            {ctaLabel}
          </a>
        </p>
      ) : null}
      <div className="placeholder-visual">{visualLabel || "Visual pending"}</div>
    </section>
  );
}

export function Problem({ title, body }) {
  return (
    <section className="section">
      <p className="section-label">Problem</p>
      <div className="split">
        <h2 className="display lg">{title}</h2>
        <p>{body}</p>
      </div>
    </section>
  );
}

export function Benefits({ items = [] }) {
  return (
    <section className="section">
      <p className="section-label">Benefits</p>
      <div className="benefits">
        {items.map((item) => (
          <article className="benefit" key={item.title}>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function Proof({ items = [] }) {
  return (
    <section className="section">
      <p className="section-label">Proof</p>
      <div className="quotes">
        {items.map((item) => (
          <blockquote key={item.name}>
            {item.quote}
            <footer>— {item.name}</footer>
          </blockquote>
        ))}
      </div>
    </section>
  );
}

export function Offer({ title, body, price, ctaLabel }) {
  return (
    <section className="section" id="offer">
      <p className="section-label">Offer</p>
      <div className="offer-box offer">
        <h3>{title}</h3>
        <p>{body}</p>
        {price ? <p className="price">{price}</p> : null}
        {ctaLabel ? (
          <p>
            <a className="button" href="#cta">
              {ctaLabel}
            </a>
          </p>
        ) : null}
      </div>
    </section>
  );
}

export function FAQ({ items = [] }) {
  return (
    <section className="section">
      <p className="section-label">FAQ</p>
      {items.map((item) => (
        <article className="faq-item" key={item.q}>
          <h3>{item.q}</h3>
          <p>{item.a}</p>
        </article>
      ))}
    </section>
  );
}

export function FinalCTA({ text, label }) {
  return (
    <section className="section final-cta" id="cta">
      <p className="section-label">Call to action</p>
      <h2 className="display lg">{text}</h2>
      {label ? (
        <p>
          <a className="button" href="#offer">
            {label}
          </a>
        </p>
      ) : null}
    </section>
  );
}

export function Footer({ text }) {
  return (
    <footer className="section site-footer">
      <p>{text}</p>
    </footer>
  );
}
