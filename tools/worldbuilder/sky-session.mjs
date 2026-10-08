/** WorldBuilder-only observe -> one action -> refresh adapter for @oai/sky.
 * Import in the computer-use node_repl, passing its initialized `sky` client.
 * Never runs a blind macro, guesses a handle, or falls back to SendInput/Win32.
 */
export class WorldBuilderSession {
  constructor(sky) {
    this.sky = sky;
    this.candidates = [];
    this.window = null;
    this.state = null;
    this.ticket = 0;
    this.journal = [];
  }

  async discover() {
    this.window = this.state = null;
    const windows = await this.sky.list_windows();
    this.candidates = windows.filter(w => /worldbuilder/i.test(w.app));
    return this.candidates;
  }

  async attach(id) {
    const found = this.candidates.filter(w => w.id === id);
    if (found.length !== 1) throw new Error('Select exactly one window returned by discover()');
    this.window = this.state = null;
    this.window = await this.sky.get_window({id: found[0].id, app: found[0].app});
    return this.observe();
  }

  async observe() {
    if (!this.window) throw new Error('Discover and attach WorldBuilder first');
    this.state = null;
    const state = await this.sky.get_window_state({window: this.window, include_screenshot: true, include_text: true});
    this.window = state.window;
    this.state = state;
    this.ticket++;
    return {ticket: this.ticket, window: state.window, accessibility: state.accessibility};
    // sky displays the screenshot. Do not re-emit its payload.
  }

  async act(ticket, action) {
    if (!this.state || ticket !== this.ticket) throw new Error('Stale observation; observe and inspect before acting');
    if (!action.reason?.trim()) throw new Error('Supply the purpose of this single observed action');
    const state = this.state;
    const screenshotId = state.screenshots?.[0]?.id;
    const window = state.window;
    const indexed = action.element_index !== undefined;
    const coords = (...values) => {
      if (!screenshotId || !values.every(Number.isFinite)) throw new Error('Coordinates require the latest screenshot and finite values');
    };
    if (indexed && (!Number.isInteger(action.element_index) || !state.accessibility?.tree)) {
      throw new Error('Indexed actions require the latest accessibility tree');
    }
    let perform;
    switch (action.type) {
      case 'click':
        if (!indexed) coords(action.x, action.y);
        perform = () => this.sky.click(indexed
          ? {window, element_index: action.element_index}
          : {window, screenshotId, x: action.x, y: action.y});
        break;
      case 'key':
        if (typeof action.key !== 'string' || /(^|\+)(meta|windows|win|super|cmd|command|os)(\+|$)/i.test(action.key.replace(/\s/g, ''))) {
          throw new Error('Provide a supported, non-system key chord');
        }
        perform = () => this.sky.press_key({window, key: action.key});
        break;
      case 'text':
        if (!state.accessibility?.focused_element || !action.focusConfirmed || typeof action.text !== 'string') {
          throw new Error('Inspect and explicitly confirm the observed editable focus before typing');
        }
        perform = () => this.sky.type_text({window, text: action.text});
        break;
      case 'value':
        if (!indexed || typeof action.value !== 'string') throw new Error('An observed edit index and string value are required');
        perform = () => this.sky.set_value({window, element_index: action.element_index, value: action.value});
        break;
      case 'drag':
        coords(action.from_x, action.from_y, action.to_x, action.to_y);
        perform = () => this.sky.drag({window, screenshotId, from_x: action.from_x, from_y: action.from_y, to_x: action.to_x, to_y: action.to_y});
        break;
      case 'scroll':
        coords(action.x, action.y, action.scrollX, action.scrollY);
        perform = () => this.sky.scroll({window, screenshotId, x: action.x, y: action.y, scrollX: action.scrollX, scrollY: action.scrollY});
        break;
      default: throw new Error('Unsupported action; use a single documented sky operation');
    }
    this.state = null; // Consume the observation before input, including failed input.
    const entry = {time: new Date().toISOString(), ticket, type: action.type, reason: action.reason, outcome: 'unknown'};
    this.journal.push(entry);
    try {
      await perform();
      const result = await this.observe();
      entry.outcome = 'input_returned_and_refreshed';
      return result; // Agent must inspect before deciding that the action succeeded.
    } catch (error) {
      this.state = null;
      throw new Error('Input or refresh failed; outcome unknown. Reobserve before any retry.', {cause: error});
    }
  }
}
