async function handle(response) {
  if (response.status === 204) return null
  let payload = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }
  if (!response.ok) {
    const detail = payload?.detail
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg || '').join(', ')
      : detail || `Erreur ${response.status}`
    throw new Error(message)
  }
  return payload
}

const send = (method) => (url, body) =>
  fetch(url, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(handle)

const get = (url) => fetch(url).then(handle)
const post = send('POST')
const patch = send('PATCH')
const remove = send('DELETE')

export const api = {
  bootstrap: () => get('/api/bootstrap'),
  setup: (users) => post('/api/setup', { users }),

  updateSettings: (payload) => patch('/api/settings', payload),

  createUser: (payload) => post('/api/users', payload),
  updateUser: (id, payload) => patch(`/api/users/${id}`, payload),
  deleteUser: (id) => remove(`/api/users/${id}`),

  openSession: (userId) => post('/api/session', { user_id: userId }),
  closeSession: () => remove('/api/session'),

  tiles: (section, parentId, sort = 'auto') =>
    get(
      `/api/tiles?section=${section}${parentId ? `&parent_id=${parentId}` : ''}&sort=${sort}`,
    ),
  createTile: (payload) => post('/api/tiles', payload),
  updateTile: (id, payload) => patch(`/api/tiles/${id}`, payload),
  deleteTile: (id) => remove(`/api/tiles/${id}`),
  reorder: (section, parentId, ids) =>
    post('/api/tiles/reorder', { section, parent_id: parentId ?? null, ids }),

  complete: (id) => post(`/api/tiles/${id}/complete`),
  undo: (completionId) => remove(`/api/completions/${completionId}`),

  stats: () => get('/api/stats'),
  history: (limit = 200) => get(`/api/history?limit=${limit}`),
}
