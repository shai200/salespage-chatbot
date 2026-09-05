import React from "react";
import {
  Benefits,
  FAQ,
  FinalCTA,
  Footer,
  Hero,
  LeadModal,
  Offer,
  OfferCountdown,
  Problem,
  Proof,
  ValueStack,
} from "./sections.jsx";

export function App({ data }) {
  return (
    <main className="page">
      <Hero {...data.hero} />
      <Problem {...data.problem} />
      <Benefits items={data.benefits} {...data.benefitVisual} />
      <Proof items={data.proof} />
      <Offer {...data.offer} />
      <FAQ items={data.faq} />
      <ValueStack {...data.valueStack} />
      <OfferCountdown {...data.countdown} />
      <FinalCTA {...data.cta} />
      <LeadModal {...data.leadModal} />
      <Footer text={data.footer} />
    </main>
  );
}
