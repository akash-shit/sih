import test from 'node:test';
import assert from 'node:assert/strict';
import packageJson from '../package.json' with { type: 'json' };

test('frontend build and test scripts are present', () => {
  assert.equal(typeof packageJson.scripts.build, 'string');
  assert.equal(typeof packageJson.scripts.test, 'string');
});
