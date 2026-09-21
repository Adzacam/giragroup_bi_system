import client from './client';

export const loginStep1 = async (email, password) => {
  const response = await client.post('/api/v1/auth/login', { email, password });
  return response.data;
};

export const verifyOTP = async (temp_token, code) => {
  const response = await client.post('/api/v1/auth/verify-otp', { temp_token, code });
  return response.data;
};

export const resendOTP = async (temp_token) => {
  const response = await client.post('/api/v1/auth/resend-otp', { temp_token });
  return response.data;
};

export const authApi = {
  loginStep1,
  verifyOTP,
  resendOTP,
};

export default authApi;
