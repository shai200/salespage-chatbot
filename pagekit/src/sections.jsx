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

export function Hero({ headline, accent, subheadline, ctaLabel, visualLabel, src }) {
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
      {src ? (
        <img className="hero-visual" src={src} alt={visualLabel || ""} />
      ) : (
        <div className="placeholder-visual">{visualLabel || "Visual pending"}</div>
      )}
    </section>
  );
}

export function Problem({ title, body, visualLabel, src }) {
  return (
    <section className="section">
      <p className="section-label">Problem</p>
      <div className="split">
        <h2 className="display lg">{title}</h2>
        <p>{body}</p>
      </div>
      {src ? (
        <img className="section-visual" src={src} alt={visualLabel || ""} />
      ) : null}
    </section>
  );
}

export function Benefits({ items = [], visualLabel, src }) {
  return (
    <section className="section">
      <p className="section-label">Benefits</p>
      {src ? (
        <img className="section-visual" src={src} alt={visualLabel || ""} />
      ) : null}
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

export function Offer({ title, body, price, ctaLabel, visualLabel, src }) {
  return (
    <section className="section" id="offer">
      <p className="section-label">Offer</p>
      <div className="offer-box offer">
        <h3>{title}</h3>
        <p>{body}</p>
        {price ? <p className="price">{price}</p> : null}
        {src ? (
          <img className="section-visual" src={src} alt={visualLabel || ""} />
        ) : null}
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

export function ValueStack({
  title,
  items = [],
  totalWorth,
  compareAtPrice,
  price,
  label,
  totalLabel,
  bonusLabel,
}) {
  if (!items.length && !price && !compareAtPrice) {
    return null;
  }
  return (
    <section className="section value-stack" id="value">
      <p className="section-label">{label || "What you get"}</p>
      {title ? <h2 className="display lg">{title}</h2> : null}
      {items.length ? (
        <ul className="stack-list">
          {items.map((item) => (
            <li className={item.bonus ? "stack-bonus" : undefined} key={item.name}>
              <span>
                {item.bonus ? <span className="bonus-tag">{bonusLabel || "Bonus"}</span> : null}
                {item.name}
              </span>
              {item.worth ? <span className="stack-worth">{item.worth}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {totalWorth ? (
        <p className="stack-total">
          <span>{totalLabel || "Total value"}</span>
          <strong>{totalWorth}</strong>
        </p>
      ) : null}
      {compareAtPrice || price ? (
        <p className="stack-price">
          {compareAtPrice ? <s className="compare-at">{compareAtPrice}</s> : null}
          {price ? <span className="final-price">{price}</span> : null}
        </p>
      ) : null}
    </section>
  );
}

export function OfferCountdown({
  endsAt,
  hours,
  minutes,
  seconds,
  label,
  expiredLabel,
  hoursLabel,
  minutesLabel,
  secondsLabel,
}) {
  if (!endsAt) {
    return null;
  }
  return (
    <section className="section offer-countdown" data-offer-ends={endsAt}>
      <p className="section-label">{label || "Discount ends in"}</p>
      <div className="countdown-face" dir="ltr">
        <div>
          <span data-unit="h">{hours || "24"}</span>
          <small>{hoursLabel || "Hours"}</small>
        </div>
        <div>
          <span data-unit="m">{minutes || "00"}</span>
          <small>{minutesLabel || "Minutes"}</small>
        </div>
        <div>
          <span data-unit="s">{seconds || "00"}</span>
          <small>{secondsLabel || "Seconds"}</small>
        </div>
      </div>
      <p className="countdown-expired" hidden>
        {expiredLabel || "This discount has ended"}
      </p>
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
