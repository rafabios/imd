const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const sync = source.slice(source.indexOf('function syncDownloadDestinations('), source.indexOf('function renderConfigEditor('));
function run(previous, next, audio, soundcloud) {
  const fields = {'#audio-destination': {value: audio}, '#soundcloud-destination': {value: soundcloud}};
  let previews = 0;
  const context = {currentConfig: {paths: {music_dir: previous}}, document: {querySelector: key => fields[key]}, updateAudioDestinationPreview: () => previews++};
  vm.createContext(context);
  vm.runInContext(sync, context);
  context.syncDownloadDestinations({paths: {music_dir: next}});
  assert.equal(previews, 1);
  return Object.values(fields).map(field => field.value);
}
test('changed saved folder updates both populated download screens', () => {
  assert.deepEqual(run('old', 'new', 'old', 'old'), ['new', 'new']);
});
test('unrelated config saves preserve custom download destinations', () => {
  assert.deepEqual(run('default', 'default', 'Samples', 'Tracks'), ['Samples', 'Tracks']);
});
test('empty fields pick up configured folder', () => {
  assert.deepEqual(run('default', 'default', '', ''), ['default', 'default']);
});
test('both save and reload apply the shared config renderer', () => {
  for (const name of ['loadConfig', 'saveConfig']) {
    const body = source.split(`async function ${name}()`)[1].split('\nasync function ')[0];
    assert.match(body, /renderConfigEditor\(data.config\)/);
  }
  assert.match(source, /function renderConfigEditor\(config\)\s*\{\s*syncDownloadDestinations\(config\);\s*currentConfig = config;/);
});
