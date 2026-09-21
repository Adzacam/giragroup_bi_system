export const getUsers = async () => {
  const response = await fetch('/api/v1/users');
  return response.json();
};

export const createUser = async (data) => {
  const response = await fetch('/api/v1/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return response.json();
};

export const updateUser = async (id, data) => {
  const response = await fetch(`/api/v1/users/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return response.json();
};

export const deleteUser = async (id) => {
  const response = await fetch(`/api/v1/users/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
  return response.json();
};
