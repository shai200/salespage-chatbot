const test = require('node:test');
const assert = require('node:assert/strict');
const { generateReply } = require('./chatbot');

test('returns pricing guidance for pricing questions', () => {
  assert.match(generateReply('What is your pricing?'), /\$49\/month/);
});

test('returns a fallback for unknown questions', () => {
  assert.match(generateReply('Do you support multilingual humor?'), /recommend the right chatbot setup/i);
});

test('returns a prompt for empty messages', () => {
  assert.match(generateReply('   '), /Please enter a question/i);
});
