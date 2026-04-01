import React from 'react';

const Dashboard: React.FC = () => {
  return (
    <div className="dashboard">
      <h1>Dashboard</h1>
      <p>Strategy Performance Summary</p>
      <button onClick={() => window.location.href = '/'}>Back to Landing Page</button>
    </div>
  );
};

export default Dashboard;
