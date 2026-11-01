import client from './client';

export const getUsers = async () => {
  const response = await client.get('/api/v1/users');
  return response.data;
};

export const createUser = async (data) => {
  const response = await client.post('/api/v1/users', data);
  return response.data;
};

export const updateUser = async (id, data) => {
  const response = await client.put(`/api/v1/users/${encodeURIComponent(id)}`, data);
  return response.data;
};

export const deleteUser = async (id) => {
  const response = await client.delete(`/api/v1/users/${encodeURIComponent(id)}`);
  return response.data;
};

export const usersApi = {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
};

export default usersApi;
