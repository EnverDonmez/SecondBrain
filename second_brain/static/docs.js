const data = await (await fetch('/api/openapi.json')).json();
const root = document.querySelector('#endpoints');
for (const [path, operations] of Object.entries(data.paths)) {
  for (const [method, operation] of Object.entries(operations)) {
    const panel = document.createElement('section'); panel.className = 'panel';
    const heading = document.createElement('h2'); heading.textContent = method.toUpperCase() + ' ' + path;
    const summary = document.createElement('p'); summary.textContent = operation.summary || '';
    const details = document.createElement('details'); details.className = 'details';
    const label = document.createElement('summary'); label.textContent = 'İstek / yanıt şeması';
    const code = document.createElement('pre'); code.textContent = JSON.stringify(operation, null, 2);
    details.append(label, code); panel.append(heading, summary, details); root.append(panel);
  }
}
