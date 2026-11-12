// Unit tests for the Worker's request rules (worker/routes.ts). No browser, no Cloudflare:
//   npm run test:worker
import assert from 'node:assert/strict';
import test from 'node:test';
import { apiRoute, isApiPath, MAX_BODY, mentionsInternal, uploadProblem, verifyTurnstile, visitorKey } from '../worker/routes.ts';

const JOB = '0123456789abcdef0123456789abcdef';
const path = (raw) => new URL(raw, 'https://ghostframe.example').pathname;

test('only the engine routes are forwarded', () => {
  assert.equal(apiRoute('GET', '/api/status'), 'status');
  assert.equal(apiRoute('GET', '/api/quota'), 'quota');
  assert.equal(apiRoute('POST', '/api/encode'), 'encode');
  assert.equal(apiRoute('POST', '/api/decode'), 'decode');
  assert.equal(apiRoute('GET', `/api/jobs/${JOB}`), 'job');
  assert.equal(apiRoute('POST', `/api/jobs/${JOB}/cancel`), 'cancel');
  assert.equal(apiRoute('GET', `/api/jobs/${JOB}/marked.png`), 'result');
  assert.equal(apiRoute('GET', `/api/jobs/${JOB}/difference.png`), 'result');
  for (const [method, raw] of [
    ['GET', '/api/internal/limits'], ['POST', '/api/internal/limits'], ['GET', '/api/internal%2Flimits'],
    ['GET', '/api/internal%252Flimits'], ['GET', '/api/%69nternal/limits'], ['GET', '/api/x/../internal/limits'],
    ['GET', '/api/status/'], ['GET', '/api/encode'], ['POST', '/api/status'], ['GET', '/api/jobs/short'],
    ['GET', `/api/jobs/${JOB.toUpperCase()}`], ['GET', `/api/jobs/${JOB}/other.png`], ['GET', `/api/jobs/${JOB}%2Fcancel`],
    ['DELETE', `/api/jobs/${JOB}`], ['GET', '/api/'], ['GET', '/api'], ['GET', '/api/STATUS'], ['HEAD', '/api/status'],
  ]) assert.equal(apiRoute(method, path(raw)), null, `${method} ${raw}`);
});

test('API paths and internal spellings', () => {
  assert.ok(isApiPath('/api') && isApiPath('/api/x') && !isApiPath('/apix') && !isApiPath('/'));
  for (const raw of ['/api/internal/limits', '/api/internal%2Flimits', '/api/internal%252Flimits', '/api/%69nternal/x', '/API//Internal/x', '/api/%E0%A4%A'])
    assert.ok(mentionsInternal(path(raw)), raw);
  assert.ok(!mentionsInternal('/api/status'));
});

test('uploads: multipart with a Content-Length within the limit', () => {
  const h = (o) => new Headers(o);
  const mp = 'multipart/form-data; boundary=x';
  assert.equal(uploadProblem(h({ 'content-type': mp, 'content-length': '1000' })), null);
  assert.equal(uploadProblem(h({ 'content-type': mp, 'content-length': String(MAX_BODY) })), null);
  assert.deepEqual(uploadProblem(h({ 'content-type': mp, 'content-length': String(MAX_BODY + 1) })), [413, 'too_large']);
  assert.deepEqual(uploadProblem(h({ 'content-type': mp })), [411, 'bad_request']);
  assert.deepEqual(uploadProblem(h({ 'content-type': mp, 'content-length': '-1' })), [400, 'bad_request']);
  assert.deepEqual(uploadProblem(h({ 'content-type': 'application/x-www-form-urlencoded', 'content-length': '10' })), [415, 'bad_request']);
  assert.deepEqual(uploadProblem(h({ 'content-length': '10' })), [415, 'bad_request']);
  assert.equal(MAX_BODY, 41 * 1024 * 1024);
});

test('visitors: IPv4 as is, IPv6 by /64', () => {
  assert.equal(visitorKey('192.0.2.7'), '192.0.2.7');
  assert.equal(visitorKey('2001:db8:1:2:aaaa::1'), '2001:db8:1:2::/64');
  assert.equal(visitorKey('2001:DB8:1:2:ffff:ffff:ffff:ffff'), '2001:db8:1:2::/64');
  assert.equal(visitorKey('2001:db8::1'), '2001:db8:0:0::/64');
  assert.equal(visitorKey('::ffff:192.0.2.7'), '192.0.2.7');
  assert.equal(visitorKey('::1'), '0:0:0:0::/64');
  assert.notEqual(visitorKey('2001:db8:1:2::1'), visitorKey('2001:db8:1:3::1'));
});

test('Turnstile fails closed', async () => {
  const check = { token: 't', secret: 's', ip: '192.0.2.7', hostname: 'ghostframe.example', action: 'encode' };
  const reply = (body, status = 200) => async () => new Response(typeof body === 'string' ? body : JSON.stringify(body), { status });
  const good = { success: true, hostname: 'ghostframe.example', action: 'encode' };
  assert.equal(await verifyTurnstile(check, reply(good)), 'ok');
  assert.equal(await verifyTurnstile({ ...check, secret: undefined }, reply(good)), 'unavailable');
  assert.equal(await verifyTurnstile({ ...check, token: null }, reply(good)), 'failed');
  assert.equal(await verifyTurnstile(check, reply({ ...good, success: false })), 'failed');
  assert.equal(await verifyTurnstile(check, reply({ ...good, hostname: 'evil.example' })), 'failed');
  assert.equal(await verifyTurnstile(check, reply({ ...good, action: 'decode' })), 'failed');
  assert.equal(await verifyTurnstile(check, reply(good, 500)), 'unavailable');
  assert.equal(await verifyTurnstile(check, reply('not json')), 'unavailable');
  assert.equal(await verifyTurnstile(check, async () => { throw new Error('network'); }), 'unavailable');
  let sent;
  await verifyTurnstile(check, async (url, init) => { sent = init.body; return new Response(JSON.stringify(good)); });
  assert.equal(sent.get('remoteip'), '192.0.2.7');
  assert.equal(sent.get('secret'), 's');
});
