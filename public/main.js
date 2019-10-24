let editor = null;

function load_viewer() {
  const container = document.getElementById('viewer_container')
  const options = {
    mode: 'view'
  };
  editor = new JSONEditor(container, options);
}

function data_update(new_data, func) {
  console.log('Updating with', new_data);
  console.log(JSON.stringify(new_data, null, 2));
  data = new_data;
  editor.set(data);
  func && func();
}

function fetch_data(data_url, func) {
  console.log('Fetching', data_url)
  fetch(data_url)
    .then(response => response.json())
    .then(json => data_update(json, func))
    .catch(rejection => console.log(rejection));
}

function fetch_path(eth_src, eth_dst) {
  src = eth_src.slice(-2)
  dst = eth_dst.slice(-2)
  fetch_data(`host_path_${src}_${dst}`, `host_path?eth_src=${eth_src}&eth_dst=${eth_dst}`)
}

function initialize() {
  console.log('initializing viewer');
  if (window.location.search.startsWith('?')) {
    api = window.location.search.slice(1);
  } else {
    api = 'system_state';
  }
  load_viewer();
  fetch_data(api);
}
