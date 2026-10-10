import assert from 'node:assert/strict';
import { WorldBuilderSession } from '../sky-session.mjs';

const window = {id: 42, app: 'D:\\game\\Worldbuilder.exe', title: 'WorldBuilder'};
let inputs = 0;
let failInput = false;
const sky = {
  async list_windows() { return [window, {id: 9, app: 'other.exe'}]; },
  async get_window(input) { assert.equal(input.id, 42); return window; },
  async get_window_state() { return {window, screenshots: [{id: 'fresh'}], accessibility: {tree: '1 button', focused_element: '2 editable field'}}; },
  async click(input) { assert.equal(input.window, window); inputs++; if (failInput) throw new Error('disconnected'); },
  async press_key() { inputs++; },
  async type_text() { inputs++; },
};
const wb = new WorldBuilderSession(sky);
await assert.rejects(wb.observe(), /Discover/);
assert.equal((await wb.discover()).length, 1);
await assert.rejects(wb.attach(9), /exactly one/);
const first = await wb.attach(42);
const second = await wb.act(first.ticket, {type: 'click', x: 12, y: 16, reason: 'Observed map menu'});
assert.equal(inputs, 1);
await assert.rejects(wb.act(first.ticket, {type: 'key', key: 'Return', reason: 'stale'}), /Stale/);
assert.equal(inputs, 1);
await assert.rejects(wb.act(second.ticket, {type: 'key', key: 'Win+r', reason: 'blocked'}), /non-system/);
await assert.rejects(wb.act(second.ticket, {type: 'text', text: 'map', reason: 'unconfirmed focus'}), /confirm/);
assert.equal(inputs, 1);
failInput = true;
await assert.rejects(wb.act(second.ticket, {type: 'click', element_index: 1, reason: 'Failure recovery test'}), /outcome unknown/);
assert.equal(inputs, 2);
await assert.rejects(wb.act(second.ticket, {type: 'click', element_index: 1, reason: 'unsafe retry'}), /Stale/);
assert.equal(inputs, 2);
assert.equal(wb.journal.at(-1).outcome, 'unknown');
const recovered = await wb.observe();
await wb.act(recovered.ticket, {type: 'text', text: 'working map', focusConfirmed: true, reason: 'Observed file-name field'});
assert.equal(inputs, 3);
assert.ok(!JSON.stringify(wb.journal).includes('working map'));
console.log('WorldBuilder session guards passed (mock client; no live UI claim).');
