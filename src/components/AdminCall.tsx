import React from 'react';

interface AdminCallProps {
    onCall: () => void;
}

const AdminCall: React.FC<AdminCallProps> = ({ onCall }) => {
    return (
        <button
            onClick={onCall}
            className="fixed right-4 bottom-24 bg-red-600 text-white w-14 h-14 rounded-full shadow-2xl flex items-center justify-center hover:bg-red-700 active:scale-95 transition-all z-40 border-4 border-white"
            title="Вызвать администратора"
        >
            <span className="text-2xl">🆘</span>
        </button>
    );
};

export default AdminCall;
