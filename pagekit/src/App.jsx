import React from "react";
import { Benefits, FAQ, FinalCTA, Footer, Hero, Offer, Problem, Proof } from "./sections.jsx";

export function App({ data }) {
  return (
    <main className="page">
      <Hero {...data.hero} />
      <Problem {...data.problem} />
      <Benefits items={data.benefits} />
      <Proof items={data.proof} />
      <Offer {...data.offer} />
      <FAQ items={data.faq} />
      <FinalCTA {...data.cta} />
      <Footer text={data.footer} />
    </main>
  );
}
