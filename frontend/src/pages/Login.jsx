import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { jwtDecode } from 'jwt-decode';
import axios from 'axios'; // Import standard axios for the Keycloak call
import api from '../api/axios'; // Your custom instance for backend calls

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // 1. Talk DIRECTLY to Keycloak to get the Token
      const formData = new URLSearchParams();
      formData.append('client_id', 'fastapi-backend');
      formData.append('username', username);
      formData.append('password', password);
      formData.append('grant_type', 'password');

      // POST to Keycloak's exact URL
      const response = await axios.post(
        'http://localhost:8080/realms/banking/protocol/openid-connect/token',
        formData,
        {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
        }
      );

      const { access_token } = response.data;
      
      // 2. Decode the Keycloak token
      localStorage.setItem('token', access_token);
      const decoded = jwtDecode(access_token);
      
      // Extract roles correctly from Keycloak's JWT structure
      const roles = decoded.realm_access?.roles || [];
      const rolePriority = ["admin", "manager", "teller", "customer"];
      let primaryRole = "customer";
      for (const r of rolePriority) {
        if (roles.includes(r)) {
          primaryRole = r;
          break;
        }
      }

      localStorage.setItem('username', decoded.preferred_username);
      localStorage.setItem('role', primaryRole);

      // 3. Route to dashboard
      navigate('/dashboard');

    } catch (err) {
      console.error(err);
      // Keycloak usually sends errors in error_description
      setError(err.response?.data?.error_description || 'Invalid Keycloak credentials');
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-extrabold text-gray-900">Zero Trust Vault</h2>
          <p className="text-gray-500 mt-2">Sign in to your account</p>
        </div>

        {error && (
          <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm mb-4 text-center border border-red-200">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700">Username</label>
            <input
              type="text"
              required
              className="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="customer1"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              required
              className="mt-1 block w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            {loading ? 'Authenticating...' : 'Secure Login'}
          </button>
        </form>
      </div>
    </div>
  );
}