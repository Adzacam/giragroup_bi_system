import client from './client';

export const loginStep1 = async (email, password, device_token = null, remember_device = false) => {
  const response = await client.post('/api/v1/auth/login', { email, password, device_token, remember_device });
  return response.data;
};

export const verifyOTP = async (temp_token, code, remember_device = false) => {
  const response = await client.post('/api/v1/auth/verify-otp', { temp_token, code, remember_device });
  return response.data;
};

export const resendOTP = async (temp_token) => {
  const response = await client.post('/api/v1/auth/resend-otp', { temp_token });
  return response.data;
};

export const changePassword = async (current_password, new_password, confirm_password) => {
  const response = await client.post('/api/v1/auth/change-password', {
    current_password,
    new_password,
    confirm_password
  });
  return response.data;
};

export const authApi = {
  loginStep1,
  verifyOTP,
  resendOTP,
  changePassword,
};

export default authApi;

