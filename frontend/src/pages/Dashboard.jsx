import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

export default function Dashboard() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Transfer State
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [transferTo, setTransferTo] = useState('');
  const [transferAmount, setTransferAmount] = useState('');
  const [transferError, setTransferError] = useState('');
  const [transferSuccess, setTransferSuccess] = useState('');

  // MFA Step-Up State
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
    fetchHistory();
  }, [navigate]);

  const fetchHistory = async () => {
    try {
      const response = await api.get('/transfer/history');
      setTransactions(response.data.transactions);
    } catch (err) {
      setError('Failed to load transaction history.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    // Clear the MFA cookie on logout for safety
    document.cookie = "mfa_cleared=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    navigate('/');
  };

  // --- THE ZERO TRUST TRANSFER LOGIC ---
  const executeTransfer = async (targetUser, amount) => {
    setTransferError('');
    setTransferSuccess('');

    try {
      const response = await api.post('/transfer/', {
        to_username: targetUser,
        amount: parseFloat(amount)
      });

      // If we get here, OPA allowed the transfer!
      setTransferSuccess(`Successfully sent ₹${amount} to ${targetUser}! (Risk Score: ${response.data.security_score})`);
      setShowTransferModal(false);
      setTransferTo('');
      setTransferAmount('');
      
      // Refresh the table to show the new transaction
      fetchHistory();

    } catch (err) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;

      // 1. THE INTERCEPTOR: Did OPA demand Step-Up MFA?
      if (status === 401 && detail?.decision === "step_up") {
        console.log("High Risk Detected! Triggering MFA...");
        setPendingTransfer({ targetUser, amount });
        setShowTransferModal(false);
        setShowMfaModal(true);
        return;
      }

      // 2. Was it a hard block or a database error?
      if (typeof detail === 'string') {
        setTransferError(detail); // e.g. "Insufficient funds"
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
    // 1. In a real app, we'd verify this code with the backend. 
    // For the capstone, we simulate a successful verification.
    if (mfaCode.length === 6) {
      // 2. Set the magical Zero Trust cookie (expires in 5 minutes)
      document.cookie = "mfa_cleared=true; path=/; max-age=300";
      
      // 3. Hide MFA modal and retry the exact same transfer
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
            <button 
              onClick={() => setShowTransferModal(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition"
            >
              Send Money
            </button>
            <button 
              onClick={handleLogout}
              className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg font-medium hover:bg-gray-300 transition"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Success Message Alert */}
        {transferSuccess && (
          <div className="mb-6 bg-green-50 text-green-700 p-4 rounded-lg border border-green-200 shadow-sm flex justify-between items-center">
            <span>{transferSuccess}</span>
            <button onClick={() => setTransferSuccess('')} className="font-bold text-xl">&times;</button>
          </div>
        )}

        {/* Transaction History Table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="px-6 py-5 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">Recent Transactions</h3>
          </div>
          <div className="p-6">
            {error && <div className="text-red-500 mb-4">{error}</div>}
            {loading ? (
              <div className="text-gray-500 text-center py-8">Loading vault data...</div>
            ) : transactions.length === 0 ? (
              <div className="text-gray-500 text-center py-8">No transactions found.</div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">From</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">To</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(tx.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">{tx.from_account}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">{tx.to_account}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                        ₹{tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          {tx.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

      </div>

      {/* --- STANDARD TRANSFER MODAL --- */}
      {showTransferModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-md">
            <h2 className="text-2xl font-bold mb-6">Transfer Funds</h2>
            {transferError && <div className="bg-red-50 text-red-700 p-3 rounded mb-4 text-sm">{transferError}</div>}
            
            <form onSubmit={handleTransferSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">Recipient Username</label>
                <input 
                  type="text" required 
                  className="w-full px-4 py-2 border rounded-md"
                  value={transferTo} onChange={(e) => setTransferTo(e.target.value)} 
                  placeholder="e.g. manager1"
                />
              </div>
              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-1">Amount (₹)</label>
                <input 
                  type="number" required min="1" step="0.01"
                  className="w-full px-4 py-2 border rounded-md"
                  value={transferAmount} onChange={(e) => setTransferAmount(e.target.value)}
                  placeholder="50.00"
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button type="button" onClick={() => setShowTransferModal(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md">Cancel</button>
                <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">Send Money</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- MFA STEP-UP MODAL (THE ZERO TRUST TRAP) --- */}
      {showMfaModal && (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-80 flex items-center justify-center z-50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-sm border-t-4 border-red-500">
            <div className="text-center mb-6">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                <svg className="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-gray-900">Security Check Required</h2>
              <p className="text-sm text-gray-500 mt-2">
                Your risk score is too high for this transaction. Please verify your identity.
              </p>
            </div>
            
            <form onSubmit={handleMfaSubmit}>
              <div className="mb-6">
                <input 
                  type="text" required maxLength="6"
                  className="w-full text-center text-2xl tracking-widest px-4 py-3 border border-gray-300 rounded-md focus:ring-red-500 focus:border-red-500"
                  value={mfaCode} onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ''))} 
                  placeholder="000000"
                />
                <p className="text-xs text-center text-gray-400 mt-2">Enter any 6 digits for this demo</p>
              </div>
              <button type="submit" className="w-full px-4 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 font-bold shadow-lg">
                Verify & Complete Transfer
              </button>
              <button type="button" onClick={() => setShowMfaModal(false)} className="w-full mt-3 px-4 py-2 text-gray-500 hover:text-gray-700 text-sm">
                Cancel Transfer
              </button>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}