'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, getToken, clearToken } from '@/lib/api';
import { AuthUser } from '@/types';

interface AuthContextType {
    user: AuthUser | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (username: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<AuthUser | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const token = getToken();
        if (token) {
            const storedUser = localStorage.getItem('pcop_user');
            if (storedUser) {
                try {
                    setUser(JSON.parse(storedUser));
                } catch {
                    clearToken();
                }
            }
        }
        setIsLoading(false);
    }, []);

    const login = async (username: string, password: string) => {
        const response = await api.login(username, password);
        if (response.user) {
            localStorage.setItem('pcop_user', JSON.stringify(response.user));
            setUser(response.user);
        }
    };

    const logout = () => {
        api.logout();
        localStorage.removeItem('pcop_user');
        setUser(null);
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                isLoading,
                isAuthenticated: !!user,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

export function useRequireRole(allowedRoles: AuthUser['role'][]) {
    const { user, isLoading } = useAuth();
    
    if (!isLoading && user && !allowedRoles.includes(user.role)) {
        if (typeof window !== 'undefined') {
            window.location.href = '/dashboard';
        }
    }
    
    return { user, isLoading, hasAccess: !isLoading && !!user && allowedRoles.includes(user.role) };
}
