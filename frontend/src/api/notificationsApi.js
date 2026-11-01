import client from './client';

export const notificationsApi = {
  getNotifications: async () => {
    const response = await client.get('/api/v1/notifications');
    return response.data;
  },
  markAsRead: async (id) => {
    const response = await client.patch(`/api/v1/notifications/${id}/read`);
    return response.data;
  },
  markAllRead: async () => {
    const response = await client.post('/api/v1/notifications/mark-all-read');
    return response.data;
  }
};
