import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

export default function Dashboard() {
  // Navigation State
  const [activeTab, setActiveTab] = useState('vault');

  // Data State
  const [transactions, setTransactions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Transfer & MFA State
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [transferTo, setTransferTo] = useState('');
  const [transferAmount, setTransferAmount] = useState('');
  const [transferError, setTransferError] = useState('');
  const [transferSuccess, setTransferSuccess] = useState('');
  const [showMfaModal, setShowMfaModal] = useState(false);
  const [mfaCode, setMfaCode] = useState('');
  const [pendingTransfer, setPendingTransfer] = useState(null);

  const navigate = useNavigate();
  const username = localStorage.getItem('username');
  const role = localStorage.getItem('role');

  useEffect(() => {
    if (!localStorage.getItem('token')) {
      navigate('/');
      return;
    }
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === 'vault') {
        const response = await api.get('/transfer/history');
        setTransactions(response.data.transactions);
      } else if (activeTab === 'audit' && role === 'admin') {
        const response = await api.get('/transfer/audit');
        setAuditLogs(response.data.logs);
      }
    } catch (err) {
      setError('Failed to fetch data.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    document.cookie = "mfa_cleared=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    navigate('/');
  };

  // --- ZERO TRUST TRANSFER LOGIC ---
  const executeTransfer = async (targetUser, amount) => {
    setTransferError('');
    setTransferSuccess('');
    try {
      const response = await api.post('/transfer/', {
        to_username: targetUser,
        amount: parseFloat(amount)
      });
      setTransferSuccess(`Successfully sent ₹${amount} to ${targetUser}! (Risk Score: ${response.data.security_score})`);
      setShowTransferModal(false);
      setTransferTo('');
      setTransferAmount('');
      if (activeTab === 'vault') fetchData();
    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      if (status === 401 && detail?.decision === "step_up") {
        setPendingTransfer({ targetUser, amount });
        setShowTransferModal(false);
        setShowMfaModal(true);
        return;
      }
      if (typeof detail === 'string') {
        setTransferError(detail);
      } else if (detail?.reasons) {
        setTransferError(`Security Blocked: ${detail.reasons.join(', ')}`);
      } else {
        setTransferError('An unexpected error occurred.');
      }
    }
  };

  const handleTransferSubmit = (e) => {
    e.preventDefault();
    executeTransfer(transferTo, transferAmount);
  };

  const handleMfaSubmit = (e) => {
    e.preventDefault();
    if (mfaCode.length === 6) {
      document.cookie = "mfa_cleared=true; path=/; max-age=300";
      setShowMfaModal(false);
      setMfaCode('');
      executeTransfer(pendingTransfer.targetUser, pendingTransfer.amount);
    } else {
      alert("Please enter a valid 6-digit code.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        
        {/* Header Section */}
        <div className="flex justify-between items-center bg-white p-6 rounded-xl shadow-sm mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Welcome back, {username}</h1>
            <p className="text-sm text-gray-500 mt-1">
              Access Level: <span className="uppercase font-semibold text-blue-600">{role}</span>
            </p>
          </div>
          <div className="flex space-x-4">
            {role !== 'admin' && (
              <button onClick={() => setShowTransferModal(true)} className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition">
                Send Money
              </button>
            )}
            <button onClick={handleLogout} className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg font-medium hover:bg-gray-300 transition">
              Logout
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex space-x-4 mb-6 border-b border-gray-200 pb-2">
          <button 
            onClick={() => setActiveTab('vault')}
            className={`font-medium px-4 py-2 rounded-t-lg ${activeTab === 'vault' ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Transaction Vault
          </button>
          {role === 'admin' && (
            <button 
              onClick={() => setActiveTab('audit')}
              className={`font-medium px-4 py-2 rounded-t-lg ${activeTab === 'audit' ? 'text-red-600 border-b-2 border-red-600' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Security Audit Logs
            </button>
          )}
        </div>

        {/* Content Area */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="p-6">
            {error && <div className="text-red-500 mb-4">{error}</div>}
            
            {/* VAULT TAB */}
            {activeTab === 'vault' && (
              loading ? <div className="text-center py-8">Loading...</div> :
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">From</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">To</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {transactions.map((tx) => (
                    <tr key={tx.id}>
                      <td className="px-6 py-4 text-sm text-gray-500">{new Date(tx.timestamp).toLocaleString()}</td>
                      <td className="px-6 py-4 text-sm font-mono">{tx.from_account}</td>
                      <td className="px-6 py-4 text-sm font-mono">{tx.to_account}</td>
                      <td className="px-6 py-4 text-sm font-semibold">₹{tx.amount.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {/* SECURITY AUDIT TAB */}
            {activeTab === 'audit' && role === 'admin' && (
              loading ? <div className="text-center py-8">Loading Logs...</div> :
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">IP Address</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk Score</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Decision</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Triggered Policies</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</td>
                      <td className="px-4 py-3 text-sm font-semibold">{log.username}</td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-600">{log.ip}</td>
                      <td className="px-4 py-3 text-sm font-bold">
                        <span className={log.risk_score >= 100 ? 'text-red-600' : log.risk_score >= 50 ? 'text-yellow-600' : 'text-green-600'}>
                          {log.risk_score}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                          log.decision === 'block' ? 'bg-red-100 text-red-800' :
                          log.decision === 'step_up' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {log.decision.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{log.reasons}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Transfer & MFA Modals (Kept exactly the same as Phase 3) */}
      {showTransferModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6">Transfer Funds</h2>
            {transferError && <div className="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">{transferError}</div>}
            <form onSubmit={handleTransferSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Recipient Username</label>
                <input type="text" required className="w-full px-4 py-2 border rounded-md" value={transferTo} onChange={(e) => setTransferTo(e.target.value)} />
              </div>
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount (₹)</label>
                <input type="number" required min="1" step="0.01" className="w-full px-4 py-2 border rounded-md" value={transferAmount} onChange={(e) => setTransferAmount(e.target.value)} />
              </div>
              <div className="flex justify-end space-x-3">
                <button type="button" onClick={() => setShowTransferModal(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">Send Money</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showMfaModal && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-80 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-sm border-t-4 border-red-500">
            <div className="text-center mb-6">
              <h2 className="text-xl font-bold text-gray-900">Security Check Required</h2>
              <p className="text-sm text-gray-500 mt-2">Your risk score is too high. Verify your identity.</p>
            </div>
            <form onSubmit={handleMfaSubmit}>
              <div className="mb-6">
                <input type="text" required maxLength="6" className="w-full text-center text-2xl tracking-widest px-4 py-3 border border-gray-300 rounded-md focus:ring-red-500" value={mfaCode} onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))} placeholder="000000" />
              </div>
              <button type="submit" className="w-full px-4 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 font-bold shadow-lg">Verify & Complete</button>
              <button type="button" onClick={() => setShowMfaModal(false)} className="w-full mt-3 px-4 py-2 text-gray-500 hover:text-gray-700 text-sm">Cancel Transfer</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}