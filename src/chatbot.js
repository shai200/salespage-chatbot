const cannedReplies = [
  {
    match: /price|pricing|cost/i,
    reply: 'Our starter plan begins at $49/month and includes the chatbot, analytics, and lead capture.',
  },
  {
    match: /demo|trial|book/i,
    reply: 'You can book a personalized demo from the call-to-action on the page, and setup usually takes less than a day.',
  },
  {
    match: /feature|features|can it do/i,
    reply: 'The chatbot handles FAQs, captures leads, qualifies prospects, and hands off complex questions to your team.',
  },
  {
    match: /integration|integrations|crm/i,
    reply: 'It is designed to connect with common CRM and scheduling workflows through lightweight API integrations.',
  },
];

function generateReply(message = '') {
  const normalized = String(message).trim();
  if (!normalized) {
    return 'Please enter a question so I can help with pricing, demos, features, or integrations.';
  }

  const match = cannedReplies.find(({ match }) => match.test(normalized));
  return match
    ? match.reply
    : 'Thanks for your question. Share your goals and our team can recommend the right chatbot setup for your sales page.';
}

module.exports = { generateReply };
